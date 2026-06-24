# Funcion para registrar movimientos a DB
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def registrar_movimiento(nombre_usuario: str, movimiento: str, seccion: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO movimientos_registro (nombre_usuario, movimiento, seccion)
        VALUES (%s, %s, %s)
    """
    try:
        cursor.execute(query, (nombre_usuario, movimiento, seccion))
        conn.commit()
        return {"message": "Movimiento registrado exitosamente"}

    except mysql.connector.Error as err:
        
        print(f"Error al registrar movimiento: {err}")
        raise
    
    finally:
        cursor.close()
        conn.close()

def registrar_edicionUbi(sku: str, warehouse_id: str, cama: str, cantidad: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO ubicaciones_editadas (sku, warehouse_id, cama, cantidad)
        VALUES (%s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (sku, warehouse_id, cama, cantidad))
        conn.commit()
        return {"message": "Ubicación editada exitosamente"}

    except mysql.connector.Error as err:
        
        print(f"Error al registrar edición de ubicación: {err}")
        raise
    
    finally:
        cursor.close()
        conn.close()