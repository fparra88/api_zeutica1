# fichero api de productos
import mysql.connector
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import os
from dotenv import load_dotenv

router =APIRouter(prefix="/zeutica",tags=["/productos"],responses={404: {"Mensaje":"No encontrado"}})
load_dotenv() # Carga de credenciales .env

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# Definimos un modelo para recibir los datos en JSON (Body)
class VentaSchema(BaseModel):
    id_venta: int
    sku: str
    producto: str
    cantidad: int
    fecha: str
    nombreComprador: str
    otros: str
    plataforma: str


@router.get("/productos")
async def consultar_inventario_completo():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # Usamos dictionary=True para que devuelva claves como 'sku'
    
    query = "SELECT id, sku, nombre, cantidad, stock_full, precio, precio_2, precio_3 FROM productos"
    
    try:
        cursor.execute(query) 
        productos = cursor.fetchall()
        
        if not productos:
            raise HTTPException(status_code=404, detail="No se han encontrado productos")
            
        return productos # FastAPI lo convierte automáticamente a JSON

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {err}")
    
    finally:
        cursor.close()
        conn.close()
        

@router.get("/producto/sku/{sku}") # Consulta a DB por sku de producto
async def obtener_producto_por_sku(sku: str):  
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  
    # Usamos %s para prevenir inyección SQL
    query = "SELECT id, sku, nombre, cantidad, stock_full, precio FROM productos WHERE sku = %s"
    try:
        cursor.execute(query, (sku,))    
        resultado = cursor.fetchone()
        if not resultado:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    
        # Mapeamos el resultado a un diccionario para mayor claridad
        return {
            "id": resultado['id'],
            "sku": resultado['sku'],            
            "nombre": resultado['nombre'],
            "cantidad": resultado['cantidad'],
            "stock_full": resultado['stock_full'],
            "precio": resultado['precio']
            }
    
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {err}")
    
    finally:
        # 4. Siempre cerrar recursos
        cursor.close()
        conn.close()

@router.post("/producto/venta")
async def registrar_venta(venta: VentaSchema):
    connection = get_db_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            
            # A. Verificar stock
            sql_check = "SELECT cantidad FROM productos WHERE sku = %s"
            cursor.execute(sql_check, (venta.sku,))
            resultado = cursor.fetchone()

            if not resultado:
                raise HTTPException(status_code=404, detail="Producto no encontrado")
            
            if resultado['cantidad'] < venta.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente. Solo hay {resultado['cantidad']}")
        
            # B. Aplicar el descuento al inventario
            sql_restar = "UPDATE productos SET cantidad = cantidad - %s WHERE sku = %s" 
            cursor.execute(sql_restar, (venta.cantidad, venta.sku))

            # C. Registrar venta en el historial
            # CORRECCIÓN IMPORTANTE: Antes usabas 'query' aquí por error
            sql_insert = "INSERT INTO ventasRegistro (id_ventas, sku, producto, cantidad, fecha, nombreComprador, otros, plataforma) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            valores = (venta.id_venta, venta.sku, venta.producto, venta.cantidad, venta.fecha, venta.nombreComprador, venta.otros, venta.plataforma)
            cursor.execute(sql_insert, valores)

            # D. Confirmar cambios
            connection.commit()

            return {
                "message": "Venta aplicada exitosamente", 
                "sku": venta.sku, 
                "nuevo_stock": resultado['cantidad'] - venta.cantidad
            }

    except mysql.connector.Error as err:
        connection.rollback()
        print(f"Error SQL: {err}") # Imprimir en consola para depurar
        raise HTTPException(status_code=500, detail=f"Error en base de datos: {err}")
    
    finally:
        if connection.is_connected():
            connection.close()