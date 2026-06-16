import mysql.connector
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import os
from dotenv import load_dotenv
from typing import List, Optional
from datetime import datetime

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

class Notificacion(BaseModel):
    id: int
    titulo: str
    mensaje: str
    tipo: str
    leido: bool
    fecha_creacion: datetime
    fecha_lectura: Optional[datetime] = None

from fastapi import APIRouter, HTTPException
import mysql.connector
# Asumiendo que importas tu get_db_connection y tus schemas

@router.get("/empleados/{empleado_id}/notificaciones", response_model=List[Notificacion])
async def obtener_notificaciones(empleado_id: str):
    """
    Obtiene el historial de notificaciones de un empleado específico,
    ordenadas de la más reciente a la más antigua.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # El query ordena por fecha descendente (DESC) para mostrar lo más nuevo arriba.
    # Agregamos un LIMIT 50 como buena práctica para no saturar la memoria si hay miles de registros.
    query = """
        SELECT 
            id, 
            titulo, 
            mensaje, 
            tipo, 
            leido, 
            fecha_creacion, 
            fecha_lectura 
        FROM notificaciones 
        WHERE empleado_id = %s AND leido = 0
        ORDER BY fecha_creacion DESC
        LIMIT 50
    """
    
    try:
        cursor.execute(query, (empleado_id,))
        notificaciones = cursor.fetchall()
        
        # Sanitizamos el booleano para asegurar que JSX reciba true/false y no 1/0
        for notif in notificaciones:
            notif["leido"] = bool(notif["leido"])
            
        # Si no hay notificaciones, devolverá una lista vacía [] en lugar de null,
        # lo cual es la mejor práctica en APIs para que los map() en el frontend no arrojen error.
        return notificaciones

    except mysql.connector.Error as err:
        # Registramos el error internamente (podrías usar un logger aquí en el futuro)
        print(f"Error interno DB: {err}")
        # Retornamos un error genérico 500 al cliente
        raise HTTPException(status_code=500, detail="Error al consultar las notificaciones.")
        
    finally:
        cursor.close()
        conn.close()

@router.post("/notificaciones/marcar-leida/{notificacion_id}")
async def marcar_notificacion_leida(notificacion_id: int):
    """
    Marca una notificación como leída, actualizando su estado en la base de datos.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "UPDATE notificaciones SET leido = 1, fecha_lectura = NOW() WHERE id = %s"
    
    try:
        cursor.execute(query, (notificacion_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Notificación no encontrada.")
        
        return {"mensaje": "Notificación marcada como leída."}

    except mysql.connector.Error as err:
        print(f"Error interno DB: {err}")
        raise HTTPException(status_code=500, detail="Error al actualizar la notificación.")
        
    finally:
        cursor.close()
        conn.close()