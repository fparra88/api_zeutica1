import mysql.connector
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import Optional
import os
from dotenv import load_dotenv
from datetime import date

router =APIRouter(tags=["/cleanest"],responses={404: {"Mensaje":"No encontrado"}})
load_dotenv()

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

class OrdenModel(BaseModel):
    numero_orden: str
    sku: str
    cantidad: int
    fecha_promesa: date
    status: str
    envio1: int
    envio2: int
    envio3: int

@router.post("/ordenes")
async def crear_orden(orden: OrdenModel):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = """
            INSERT INTO cleanestChoice (numero_orden, sku, cantidad, fecha_promesa, status, envio1, envio2, envio3)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            orden.numero_orden,
            orden.sku,
            orden.cantidad,
            orden.fecha_promesa,
            orden.status,
            orden.envio1,
            orden.envio2,
            orden.envio3
        )
        cursor.execute(sql, valores)
        conn.commit()
        return {"msg": "Orden creada", "numero_orden": orden.numero_orden}
    except mysql.connector.Error as err:
        print(f"Error en BD: {err}")
        raise HTTPException(status_code=500, detail="Error al guardar la orden en BD")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@router.get("/cleanest")
async def obtener_pedidos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM cleanestChoice")
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error en BD: {err}")
        raise HTTPException(status_code=500, detail="Error al obtener las órdenes")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

class EfirmaModel(BaseModel):
    numero_orden: str
    firma_base64: str
    fecha_firma: str
    usuario: str

@router.post("/efirma")
async def efirma(payload: EfirmaModel):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "UPDATE cleanestChoice SET firma_digital = %s, fecha_firma = %s, usuario = %s WHERE numero_orden = %s"
        cursor.execute(query, (payload.firma_base64,  payload.fecha_firma, payload.usuario, payload.numero_orden))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        return {"msg": "Firma registrada", "ticket_id": payload.numero_orden}
    except mysql.connector.Error as err:
        print(f"Error en BD: {err}")
        raise HTTPException(status_code=500, detail="Error al guardar la firma")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@router.get("/obtener-firma")
async def obtener_firma(numero_orden: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Busco la firma de esa orden puntual
        cursor.execute(
            "SELECT firma_digital, fecha_firma FROM cleanestChoice WHERE numero_orden = %s",
            (numero_orden,)
        )
        res = cursor.fetchone()

        if not res:
            raise HTTPException(status_code=404, detail="Orden no encontrada")

        # Si no tiene firma todavía, lo digo claro
        if res["firma_digital"] is None:
            raise HTTPException(status_code=404, detail="La orden no tiene firma registrada")

        return {"numero_orden": numero_orden, "firma_digital": res["firma_digital"], "fecha_firma":res["fecha_firma"]}

    except mysql.connector.Error as err:
        print(f"Error en BD: {err}")
        raise HTTPException(status_code=500, detail="Error al obtener la firma")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


class OrdenUpdateModel(BaseModel):
    numero_orden: Optional[str] = None
    sku: Optional[str] = None
    cantidad: Optional[int] = None
    fecha_promesa: Optional[date] = None
    status: Optional[str] = None
    envio1: Optional[int] = None
    envio2: Optional[int] = None
    envio3: Optional[int] = None

@router.patch("/cleanest/{pedido_id}")
async def actualizar_pedido(pedido_id: int, payload: OrdenUpdateModel):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        campos = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not campos:
            raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")
        set_clause = ", ".join(f"{k} = %s" for k in campos)
        valores = list(campos.values()) + [pedido_id]
        cursor.execute(f"UPDATE cleanestChoice SET {set_clause} WHERE id = %s", valores)
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        return {"msg": "Orden actualizada", "id": pedido_id}
    except mysql.connector.Error as err:
        print(f"Error en BD: {err}")
        raise HTTPException(status_code=500, detail="Error al actualizar la orden")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()