import mysql.connector
from fastapi import APIRouter, HTTPException
import os
from dotenv import load_dotenv

router =APIRouter(prefix="/zeutica",tags=["/ventas"],responses={404: {"Mensaje":"No encontrado"}})
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
        