import mysql.connector
from fastapi import APIRouter, HTTPException
import os
from dotenv import load_dotenv

router =APIRouter(tags=["/ventas"],responses={404: {"Mensaje":"No encontrado"}})
load_dotenv() # Carga de credenciales .env

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

@router.get("/ventas/{f1}/{f2}")
async def consultar_ventas(f1: str, f2: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # Usamos dictionary=True para que devuelva claves como 'sku'
    
    query = "SELECT * FROM ventasRegistro WHERE DATE(fecha_registro) BETWEEN %s AND %s"
    
    try:
        cursor.execute(query,(f1, f2))
        ventas = cursor.fetchall()
        
        if not ventas:
            raise HTTPException(status_code=404, detail="No se han encontrado registro de ventas")
            
        return ventas # FastAPI lo convierte automáticamente a JSON

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {err}")
    
    finally:
        cursor.close()
        conn.close()
        
@router.get("/verifica-venta/{norden}")
async def verificar_venta(norden: str):
    conn = get_db_connection()
    # Usamos buffered=True para descargar el resultado de inmediato
    cursor = conn.cursor(dictionary=True, buffered=True)

    query = "SELECT id FROM ventasRegistro WHERE id_ventas = %s"

    try:
        cursor.execute(query, (norden,))
        existe = cursor.fetchone()

        # Consumimos cualquier otro resultado pendiente por seguridad
        while cursor.nextset():
            pass

        # Validamos después de asegurar que el cursor terminó su trabajo
        if not existe:
            # Cerramos antes del raise para liberar la conexión en AWS de inmediato
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="El registro de venta no existe")
        
        return existe
    
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {err}")
    
    finally:
        # El bloque finally solo actuará si no entró en el if not existe
        if conn.is_connected():
            cursor.close()
            conn.close()

@router.get("/ventas-credito") # Enpoint para mostrar clientes a credito
async def verificar_venta():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT id_ventas, sku, producto, cantidad, nombreComprador, saldo_pendiente, fecha, fecha_vencimiento FROM ventasRegistro WHERE saldo_pendiente > 0 "

    try:
        cursor.execute(query)
        existe = cursor.fetchall()

        if not existe:
            raise HTTPException(status_code=404, detail="El registro de venta no existe")
        
        return existe
    
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {err}")
    
    finally:
        cursor.close()
        conn.close()