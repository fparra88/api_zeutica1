import mysql.connector
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import List
from decimal import Decimal
import datetime
import os
from dotenv import load_dotenv
from typing import Optional

router =APIRouter(tags=["/cotizaciones"],responses={404: {"Mensaje":"No encontrado"}})
load_dotenv() # Cargar credenciales .env

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

from pydantic import BaseModel # Bases clase para recibir la informacion de pdf
from typing import List

class ItemCotizacion(BaseModel):
    sku: str
    nombre_producto: str
    cantidad: int
    precio_unitario: float
    total_linea: float

class CotizacionSchema(BaseModel):
    codigo_cotizacion: str
    empresa: str
    atencion: str    
    email: str
    domicilio: Optional[str] = None
    telefono: str
    subtotal: float
    iva: float    
    total: float
    costo_envio: float  # Cambié de int a float para aceptar decimales
    forma_pago: str
    comentarios: str
    usuario: str
    items: List[ItemCotizacion]

# Creamos el "molde" para los datos que enviará Streamlit
class VinculoFactura(BaseModel):
    codigo_cotizacion: str  
    relacion_factura: Optional[str] = None

@router.get("/cotizaciones/nuevo-codigo")
async def obtener_nuevo_codigo():
    connection = get_db_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT codigo_cotizacion FROM cotizaciones ORDER BY id DESC LIMIT 1")
            ultimo = cursor.fetchone()
            
            prefijo = "ZTC-"
            # Si no hay registros previos, empezamos en ZTC-001
            if not ultimo:
                return {"nuevo_codigo": f"{prefijo}001"}
            
            # Extraer el número de "ZTC-239" -> 239 y sumar 1
            ultimo_codigo = ultimo['codigo_cotizacion']
            numero_actual = int(ultimo_codigo.replace(prefijo, ""))
            nuevo_numero = numero_actual + 1
            
            # Formateamos con ceros a la izquierda (ej: ZTC-240)
            nuevo_codigo = f"{prefijo}{nuevo_numero:03d}"
            return {"nuevo_codigo": nuevo_codigo}
    except mysql.connector.Error as err:
        print(f"Error BD en nuevo-codigo: {err}")
        raise HTTPException(status_code=500, detail=f"Error BD: {str(err)}")
    finally:
        connection.close()

@router.post("/cotizaciones/guardar")
async def guardar_cotizacion(cot: CotizacionSchema):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. Insertar en la tabla principal (Maestro)
            sql_maestro = """
                INSERT INTO cotizaciones 
                (codigo_cotizacion, empresa, atencion, email, domicilio, telefono, subtotal, iva, total, costo_envio, forma_pago, comentarios, usuario) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Convierto valores monetarios a float para evitar problemas de tipo
            valores_maestro = (
                cot.codigo_cotizacion, cot.empresa, cot.atencion, cot.email, 
                cot.domicilio, cot.telefono, float(cot.subtotal), float(cot.iva), 
                float(cot.total), float(cot.costo_envio), cot.forma_pago, cot.comentarios, cot.usuario
            )
            cursor.execute(sql_maestro, valores_maestro)
            
            # Obtenemos el ID generado para vincular los productos
            cotizacion_id = cursor.lastrowid
            
            # 2. Insertar los productos (Detalle)
            sql_detalle = """
                INSERT INTO cotizacion_items 
                (cotizacion_id, sku, nombre_producto, cantidad, precio_unitario, total_linea) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            # Preparamos una lista de tuplas para insertar todo de golpe (eficiencia)
            items_data = [
                (cotizacion_id, i.sku, i.nombre_producto, i.cantidad, float(i.precio_unitario), float(i.total_linea))
                for i in cot.items
            ]
            cursor.executemany(sql_detalle, items_data)
            
            connection.commit()
            return {"status": "success", "id": cotizacion_id}
            
    except mysql.connector.Error as err:
        connection.rollback()
        print(f"Error BD al guardar cotización: {err}")
        raise HTTPException(status_code=500, detail=f"Error BD: {str(err)}")
    except Exception as e:
        connection.rollback()
        print(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

@router.get("/consulta/cotizacion")
async def consulta_cotizacion():
    connection = get_db_connection()
    try:
        # 1. Agregamos dictionary=True para que el JSON sea compatible con Streamlit
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM cotizaciones")
            
            cotizaciones = cursor.fetchall() 

            if not cotizaciones:
                raise HTTPException(status_code=404, detail="No se encontraron cotizaciones")

            # 3. ¡Truco vital!: Convertimos Decimales a float para evitar el Error 500
            for c in cotizaciones:
                for key, value in c.items():
                    if isinstance(value, (Decimal, datetime.date)):
                        c[key] = str(value) # O float(value) si es dinero

            return {"cotizaciones": cotizaciones}

    except Exception as e:
        # Esto imprimirá el error REAL en tu consola de AWS para que sepas qué pasó
        print(f"Error detectado: {e}") 
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")
    finally:
        connection.close()


@router.post("/relacionFactura")
async def vincular_factura(vinculos: List[VinculoFactura]):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Recorremos cada cotización modificada que llegó desde Streamlit
            for v in vinculos:
                # Actualizamos el registro. 
                # IMPORTANTE: Revisa si tu tabla se llama 'cotizaciones' y si la llave primaria es 'codigo'
                sql = "UPDATE cotizaciones SET relacion_factura = %s WHERE codigo_cotizacion = %s"
                cursor.execute(sql, (v.relacion_factura, v.codigo_cotizacion))
            
            # Guardamos los cambios
            connection.commit()
            
        return {"status": "success", "mensaje": "Facturas vinculadas"}
        
    except Exception as e:
        connection.rollback()
        print(f"Error al vincular factura: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@router.get("/cotizacion/{cotizacion_id}") # Endpoint para items de cotizacion
async def obtener_items_cotizacion(cotizacion_id: int):
    connection = get_db_connection()
    
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM cotizacion_items WHERE cotizacion_id = %s", (cotizacion_id,))
            
            # ¡AQUÍ ESTÁ EL CAMBIO CLAVE! Usamos fetchall()
            items = cursor.fetchall() 
            
        if not items:
            return []
            
        return items
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener items: {str(e)}"
        )
    finally:
        connection.close()