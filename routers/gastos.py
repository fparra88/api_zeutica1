import mysql.connector
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import os
from dotenv import load_dotenv

router =APIRouter(prefix="/zeutica",tags=["/gastos"],responses={404: {"Mensaje":"No encontrado"}})
load_dotenv()

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# Definimos un modelo para recibir los datos en JSON (Body)
class Gasto(BaseModel):
    descripcion: str
    costo: float
    cantidad: int

@router.post("/gastos") # Endpoint para registrar gastos operativos
async def registrar_gasto(gasto: Gasto):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "INSERT INTO gastos (descripcion, costo, cantidad) VALUES (%s, %s, %s)"
    values = (gasto.descripcion, gasto.costo, gasto.cantidad)

    try:
        cursor.execute(query, values)
        conn.commit()
        return {"mensaje": "Gasto registrado exitosamente"}
    
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {err}")
    
    finally:
        cursor.close()
        conn.close()