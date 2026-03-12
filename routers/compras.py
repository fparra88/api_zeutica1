from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import mysql.connector

router = APIRouter(tags=["/compras"],responses={404: {"Mensaje":"No encontrado"}})

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# Modelo para recibir datos de compra
class CompraModel(BaseModel):
    sku: str  # Identificador del producto
    nombre: str
    stock_bodega: int
    costo_total: float
    usuario: str

    class Config:
        json_schema_extra = {
            "example": {
                "sku": "PROD001",
                "nombre": "Display LED 32 pulgadas",
                "stock_bodega": 10,
                "costo_total": 5500.50,
                "usuario": "ventas"
            }
        }

@router.post("/compras")
async def recibir_compra(compra: CompraModel):    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Busco si el producto ya existe por SKU
        cursor.execute(
            "SELECT stock_bodega FROM productos WHERE sku = %s",
            (compra.sku,)
        )
        res_existe = cursor.fetchone()

        if res_existe:
            # Si existe, sumo el stock que me llega con lo que hay en BD
            stock_actual = res_existe[0]
            stock_nuevo = stock_actual + compra.stock_bodega

            cursor.execute(
                "UPDATE productos SET stock_bodega = %s, costo_total = %s WHERE sku = %s",
                (stock_nuevo, compra.costo_total, compra.sku)
            )

            sql_insert = "INSERT INTO compras (sku, nombre, stock_bodega, costo_total, usuario) VALUES (%s, %s, %s, %s, %s)"
            valores = (compra.sku, compra.nombre, compra.stock_bodega, compra.costo_total, compra.usuario)
            cursor.execute(sql_insert, valores)
            
            conn.commit()
            return {
                "msg": "Compra actualizada",
                "sku": compra.sku,
                "stock_anterior": stock_actual,
                "stock_nuevo": stock_nuevo
            }
        else:
            return {
                "mensaje": "El producto no existe revisa el SKU"
            }

    except mysql.connector.Error as err:
        # Si la base de datos truena, me entero qué pasó
        print(f"Error en BD: {err}")
        raise HTTPException(status_code=500, detail="Error al procesar la compra en BD")

    finally:
        # Siempre cierro la puerta al salir
        if conn.is_connected():
            cursor.close()
            conn.close()
