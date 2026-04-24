import mysql.connector
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import Optional
import os
from dotenv import load_dotenv

router =APIRouter(tags=["/creditos"],responses={404: {"Mensaje":"No encontrado"}})
load_dotenv()

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

class abono(BaseModel):
    id_ventas: int
    saldo_abonado: float

@router.post("/abonos") # Enpoint para agregar cliente a la base de datos
async def cliente_nuevo(abono: abono):
    conn = get_db_connection()
    cursor = conn.cursor() 

    # El Query de inserción
    query = """
        INSERT INTO abonos (id_ventas, saldo_abonado ) 
        VALUES (%s, %s)
    """

    # Extraemos los valores del objeto cliente
    valores = (abono.id_ventas, abono.saldo_abonado)

    try:
        # Primero meto el abono al historial
        cursor.execute(query, valores)

        # Ahora le resto lo abonado al saldo pendiente de la venta
        cursor.execute(
            "UPDATE ventasRegistro SET saldo_pendiente = saldo_pendiente - %s WHERE id_ventas = %s",
            (abono.saldo_abonado, abono.id_ventas)
        )

        # Consulto el saldo que quedó para saber si ya quedó a mano
        cursor.execute(
            "SELECT saldo_pendiente FROM ventasRegistro WHERE id_ventas = %s",
            (abono.id_ventas,)
        )
        res = cursor.fetchone()

        conn.commit()

        if res is None:
            raise HTTPException(status_code=404, detail="Venta no encontrada en ventasregistro")

        saldo_restante = res[0]

        if saldo_restante <= 0:
            return {"mensaje": "Deuda saldada", "saldo_pendiente": 0}

        return {"mensaje": "Abono registrado", "saldo_pendiente": saldo_restante}

    except mysql.connector.Error as err:
        conn.rollback() # Si la DB truena, deshago todo
        raise HTTPException(status_code=500, detail=f"Error en DB: {err}")

    finally:
        cursor.close()
        conn.close()
