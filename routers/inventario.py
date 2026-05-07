import mysql.connector
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import List
import os
from dotenv import load_dotenv

router = APIRouter(tags=["/inventario"], responses={404: {"Mensaje": "No encontrado"}})
load_dotenv()

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

class ConteoItem(BaseModel):
    sku: str
    conteo: int

# usuario va arriba, no repetido en cada producto
class ConteoPayload(BaseModel):
    usuario: str
    productos: List[ConteoItem]

@router.post("/inventario/conteo")
async def registrar_conteo(payload: ConteoPayload):
    conn = None
    res_items = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for item in payload.productos:
            # Verifico que el SKU exista antes de registrar
            cursor.execute("SELECT sku FROM productos WHERE sku = %s", (item.sku,))
            res_existe = cursor.fetchone()

            if not res_existe:
                res_items.append({"sku": item.sku, "msg": "SKU no encontrado, se omitió"})
                continue

            cursor.execute(
                "UPDATE productos SET conteo = %s, usuario = %s WHERE sku = %s",
                (item.conteo, payload.usuario, item.sku)
            )
            res_items.append({"sku": item.sku, "msg": "OK"})

        conn.commit()
        return {"mensaje": "Conteo registrado exitosamente", "items": res_items}

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        print(f"Error en BD: {err}")
        raise HTTPException(status_code=500, detail="Error al registrar conteo en BD")

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()