import mysql.connector
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import Optional
import os
from dotenv import load_dotenv

router =APIRouter(prefix="/zeutica",tags=["/clientes"],responses={404: {"Mensaje":"No encontrado"}})
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
class Cliente(BaseModel):    
    nombre: str
    email: Optional[str] = None
    empresa: str
    contacto: str
    telefono: int
    direccion: Optional[str] = None

class clienteRfc(Cliente): # molde con herencia para cliente factura
    rfc: Optional[str] = None
    cp: Optional[int] = None
    regimen: Optional[str] = None
    usocdfi: Optional[str] = None
    
@router.get("/clientes") #Endpoint para consultar clientes en base de datos
async def obtener_clientes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) 

    query = "SELECT * FROM clientes"

    try:
        cursor.execute(query)
        clientes = cursor.fetchall() 

        if not clientes:
            raise HTTPException(status_code=404, detail="No se han encontrado clientes en la base de datos.")  
        
        return clientes
    
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {err}")
    
    finally:
        cursor.close()
        conn.close()


@router.post("/clientenuevo") # Enpoint para agregar cliente a la base de datos
async def cliente_nuevo(cliente: clienteRfc):
    conn = get_db_connection()
    cursor = conn.cursor() 

    # El Query de inserción
    query = """
        INSERT INTO clientes (nombre, email, empresa,contacto, telefono, direccion, rfc, cp, regimen, usocfdi) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    # Extraemos los valores del objeto cliente
    valores = (cliente.nombre, cliente.email, cliente.empresa, cliente.contacto, cliente.telefono, cliente.direccion, cliente.rfc, cliente.cp, cliente.regimen, cliente.usocdfi)

    try:
        cursor.execute(query, valores)
        conn.commit() # ¡Vital para guardar en MySQL!
        return {"mensaje": "Cliente agregado con éxito ", "id ": cursor.lastrowid}
    
    except mysql.connector.Error as err:
        conn.rollback() # Si falla, cancelamos la operación
        raise HTTPException(status_code=500, detail=f"Error en DB: {err}")
    
    finally:
        cursor.close()
        conn.close()

