import mysql.connector, requests
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import Optional
import os
from dotenv import load_dotenv
from datetime import date
import mov_reg

router =APIRouter(tags=["/pendientes"],responses={404: {"Mensaje":"No encontrado"}})
load_dotenv()

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

@router.get("/pendientes-registro")
async def pendientes(estado: str):
    """
    Traigo los pendientes con su estado y prioridad.
    """
    conn = get_db_connection()
    # Uso dictionary=True para devolver llaves nombradas y armar el JSON directo
    cursor = conn.cursor(dictionary=True)

    # JOIN por el FK id_ventas: del pendiente saco el saldo pendiente, de la venta el resto
    query = """
        SELECT * FROM pendientes WHERE estado = %s ORDER BY fecha ASC LIMIT 100
    """

    try:
        cursor.execute(query, (estado,))
        res = cursor.fetchall()        
        return res

    except mysql.connector.Error as err:
        print(f"Error DB pendientes: {err}")
        raise HTTPException(status_code=500, detail="Error interno en DB")  
    
    finally:
        cursor.close()
        conn.close()

class registro(BaseModel):
    usuario: str
    actividad: str
    prioridad: str  
    estado: str
    observaciones: Optional[str] = None
    fecha_promesa: Optional[date] = None

@router.post("/pendientes-agregar")
async def agregar_pendiente(registro: registro):
    """
    Agrego un registro a la tabla pendientes.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        INSERT INTO pendientes (usuario, actividad, prioridad, estado, observaciones, fecha_promesa)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    try:
        cursor.execute(query, (registro.usuario, registro.actividad, registro.prioridad, registro.estado, registro.observaciones, registro.fecha_promesa))
        conn.commit()
        r = requests.post("https://n8n-n8n.i4mjht.easypanel.host/webhook/zeutica-pendientes", json={"usuario": registro.usuario, "actividad": registro.actividad, "prioridad": registro.prioridad, "estado": registro.estado, "observaciones": registro.observaciones, "fecha_promesa": str(registro.fecha_promesa)})
        if r.status_code != 200:
            print(f"Error al enviar webhook: {r.status_code} - {r.text}")
        mov_reg.registrar_movimiento(registro.usuario, "agregar", f"Actividad: {registro.actividad}, Prioridad: {registro.prioridad}, Estado: {registro.estado}, Observaciones: {registro.observaciones}, Fecha Promesa: {registro.fecha_promesa}")
        return {"mensaje": "Registro agregado exitosamente."}        

    except mysql.connector.Error as err:
        print(f"Error DB agregar registro: {err}")
        raise HTTPException(status_code=500, detail="Error interno en DB")  
    
    finally:
        cursor.close()
        conn.close()

@router.patch("/pendientes-actualizar/{id_pendiente}")
async def actualizar_pendiente(id_pendiente: int, registro: registro):
    """
    Actualizo un registro en la tabla pendientes.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        UPDATE pendientes
        SET usuario = %s, actividad = %s, prioridad = %s, estado = %s, observaciones = %s, fecha_promesa = %s
        WHERE id = %s
    """

    try:
        cursor.execute(query, (registro.usuario, registro.actividad, registro.prioridad, registro.estado, registro.observaciones, registro.fecha_promesa, id_pendiente))
        conn.commit()
        r = requests.post("https://n8n-n8n.i4mjht.easypanel.host/webhook/zeutica-pendientes", json={"usuario": registro.usuario, "actividad": registro.actividad, "prioridad": registro.prioridad, "estado": registro.estado, "observaciones": registro.observaciones, "fecha_promesa": str(registro.fecha_promesa)})
        if r.status_code != 200:
            print(f"Error al enviar webhook: {r.status_code} - {r.text}")
        mov_reg.registrar_movimiento(registro.usuario, "actualizar", f"Actividad: {registro.actividad}, Prioridad: {registro.prioridad}, Estado: {registro.estado}, Observaciones: {registro.observaciones}, Fecha Promesa: {registro.fecha_promesa}")
        return {"mensaje": "Pendiente actualizado exitosamente."}

    except mysql.connector.Error as err:
        print(f"Error DB actualizar pendiente: {err}")
        raise HTTPException(status_code=500, detail="Error interno en DB")  
    
    finally:
        cursor.close()
        conn.close()

@router.delete("/pendientes-eliminar/{id_pendiente}")
async def eliminar_pendiente(id_pendiente: int):
    """
    Elimino un registro de la tabla pendientes.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        DELETE FROM pendientes WHERE id = %s
    """

    try:
        cursor.execute(query, (id_pendiente,))
        conn.commit()
        mov_reg.registrar_movimiento("gerencia", "eliminar", f"ID: {id_pendiente}")
        return {"mensaje": "Pendiente eliminado exitosamente."}

    except mysql.connector.Error as err:
        print(f"Error DB eliminar pendiente: {err}")
        raise HTTPException(status_code=500, detail="Error interno en DB")  
    
    finally:
        cursor.close()
        conn.close()