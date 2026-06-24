import mysql.connector
from fastapi import APIRouter, HTTPException
import os
from dotenv import load_dotenv

router =APIRouter(tags=["/consulta_registros"],responses={404: {"Mensaje":"No encontrado"}})
load_dotenv()

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

@router.get("/consulta-registros")
async def consulta_registros():
    """
    Traigo todos los registros de la tabla movimientos_registro.
    """
    conn = get_db_connection()
    # Uso dictionary=True para devolver llaves nombradas y armar el JSON directo
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM movimientos_registro order by fecha desc LIMIT 100"  # Limito a 100 registros para no saturar la respuestas

    try:
        cursor.execute(query)
        res = cursor.fetchall()        
        return res

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error al consultar registros: {err}")
    
    finally:
        cursor.close()
        conn.close()