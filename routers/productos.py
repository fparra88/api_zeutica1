# fichero api de productos
import mysql.connector
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import os
from dotenv import load_dotenv

router =APIRouter(tags=["/productos"],responses={404: {"Mensaje":"No encontrado"}})

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
    stock_bodega: int
    precio: float
    fecha: str
    nombreComprador: str
    otros: str
    plataforma: str
    usuario: str

class ProdEditSchema(BaseModel):
    """Modelo para recibir productos editados desde el frontend"""
    productos: list[dict]


class ProdNuevoSchema(BaseModel):
    """Modelo para crear un producto nuevo desde Streamlit"""
    sku: str
    nombre: str
    categoria: str
    medida: str
    ubicacion: str
    stock_minimo: int
    numero_referencia: float
    costo_total: float
    precio: float
    precio_2: float
    precio_3: float


@router.get("/productos")
async def consultar_inventario_completo():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # Usamos dictionary=True para que devuelva claves como 'sku'
    
    query = "SELECT sku, nombre, categoria, medida, ubicacion, stock_minimo, stock_bodega, stock_full, stock_fba, stock_clean, stock_total, numero_referencia, costo_total, precio, precio_2, precio_3, precio_amazon, precio_clean FROM productos"
    
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
    query = "SELECT id, sku, nombre, stock_bodega, stock_full, stock_fba, stock_clean, stock_total, precio, precio_2, precio_3 FROM productos WHERE sku = %s"
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
            "stock_bodega": resultado['stock_bodega'],
            "stock_full": resultado['stock_full'],
            "stock_fba": resultado['stock_fba'],
            "stock_clean":resultado['stock_clean'],
            "stock_total": resultado['stock_total'],
            "precio": resultado['precio'],
            "precio_2": resultado['precio_2'],
            "precio_3": resultado['precio_3']
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
            sql_check = "SELECT stock_bodega FROM productos WHERE sku = %s"
            cursor.execute(sql_check, (venta.sku,))
            resultado = cursor.fetchone()

            if not resultado:
                raise HTTPException(status_code=404, detail="Producto no encontrado")
            
            if resultado['stock_bodega'] < venta.stock_bodega:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente. Solo hay {resultado['stock_bodega']}")
        
            # B. Aplicar el descuento al inventario
            sql_restar = "UPDATE productos SET stock_bodega = stock_bodega - %s WHERE sku = %s" 
            cursor.execute(sql_restar, (venta.stock_bodega, venta.sku))

            # C. Registrar venta en el historial            
            sql_insert = "INSERT INTO ventasRegistro (id_ventas, sku, producto, cantidad, precio, fecha, nombreComprador, otros, plataforma, usuario) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            valores = (venta.id_venta, venta.sku, venta.producto, venta.stock_bodega, venta.precio, venta.fecha, venta.nombreComprador, venta.otros, venta.plataforma, venta.usuario)
            cursor.execute(sql_insert, valores)

            # D. Confirmar cambios
            connection.commit()

            return {
                "message": "Venta aplicada exitosamente", 
                "sku": venta.sku, 
                "nuevo_stock": resultado['stock_bodega'] - venta.stock_bodega
            }

    except mysql.connector.Error as err:
        connection.rollback()
        print(f"Error SQL: {err}") # Imprimir en consola para depurar
        raise HTTPException(status_code=500, detail=f"Error en base de datos: {err}")
    
    finally:
        if connection.is_connected():
            connection.close()


@router.post("/productos/editados")
async def actualizar_productos(datos: ProdEditSchema):
    """
    Recibo una lista de productos editados desde el frontend.
    Actualizo los precios y stocks en la BD según lo que me manden.
    """
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Guardo los resultados para devolverlos
        res_actualizados = []
        res_errores = []
        
        # Itero cada producto de la lista
        for prod in datos.productos:
            try:
                # Verifico que el producto tenga los datos necesarios
                if "nombre" not in prod or "sku" not in prod:
                    res_errores.append({
                        "problema": "Faltan datos: necesito 'nombre' y 'sku'",
                        "producto": prod
                    })
                    continue
                
                # Construyo la consulta dinámicamente según qué campos vinieron
                columnas_protegidas = ["id", "sku", "in_full", "stock_total"]
                campos_actualizar = []
                valores = []
                
                for columna, valor in prod.items():
                    # Solo agregamos si la columna no está en la lista negra
                    if columna not in columnas_protegidas:
                        campos_actualizar.append(f"{columna} = %s")
                        valores.append(valor)
                
                # Si no hay campos para actualizar, lo salto
                if campos_actualizar:                   
                
                    # Armo el UPDATE SQL con los campos dinámicos
                    sql_update = f"UPDATE productos SET {', '.join(campos_actualizar)} WHERE sku = %s"
                    valores.append(prod.get("sku"))
                
                cursor.execute(sql_update, valores)
                
                # Verifico que se actualizó algo
                if cursor.rowcount > 0:
                    res_actualizados.append({
                        "sku": prod["sku"],
                        "nombre": prod["nombre"],
                        "estado": "actualizado"
                    })
                else:
                    res_errores.append({
                        "sku": prod["sku"],
                        "nombre": prod["nombre"],
                        "problema": "Producto no encontrado en BD"
                    })
            
            except Exception as e:
                # Si algo truena en un producto, lo registro pero continúo
                res_errores.append({
                    "producto": prod,
                    "error": str(e)
                })
        
        # Confirmo todos los cambios de una vez
        conn.commit()
        
        return {
            "mensaje": "Actualización completada",
            "actualizados": len(res_actualizados),
            "errores": len(res_errores),
            "detalle_actualizados": res_actualizados,
            "detalle_errores": res_errores
        }
    
    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Error fatal en BD: {err}")
        raise HTTPException(status_code=500, detail=f"Error en base de datos: {err}")
    
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@router.post("/producto/nuevo")
async def crear_producto(prod: ProdNuevoSchema):
    """
    Creo un producto nuevo con los datos que vienen de Streamlit.
    Inserto todos los campos en la tabla productos.
    """
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # Primero verifico si el SKU ya existe (no dejo duplicados)
        sql_check = "SELECT sku FROM productos WHERE sku = %s"
        cursor.execute(sql_check, (prod.sku,))
        existe = cursor.fetchone()
        
        if existe:
            raise HTTPException(status_code=400, detail=f"El SKU '{prod.sku}' ya existe en la BD")
        
        # Inserto el nuevo producto
        # Nota: stock_bodega, stock_full, stock_fba y stock_total empiezan en 0
        sql_insert = """
            INSERT INTO productos 
            (sku, nombre, categoria, medida, ubicacion, stock_minimo, numero_referencia, 
             costo_total, precio, precio_2, precio_3, stock_bodega, stock_full, stock_fba)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0)
        """
        
        valores = (
            prod.sku,
            prod.nombre,
            prod.categoria,
            prod.medida,
            prod.ubicacion,
            prod.stock_minimo,
            prod.numero_referencia,
            prod.costo_total,
            prod.precio,
            prod.precio_2,
            prod.precio_3
        )
        
        cursor.execute(sql_insert, valores)
        conn.commit()
        
        return {
            "mensaje": "Producto creado exitosamente",
            "sku": prod.sku,
            "nombre": prod.nombre,
            "categoria": prod.categoria,
            "estado": "creado"
        }
    
    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Error en inserción: {err}")
        raise HTTPException(status_code=500, detail=f"Error en base de datos: {err}")
    
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()