# fichero para backend
import bcrypt
from fastapi import FastAPI, HTTPException
from routers import cotizacionesBack, productos, ventas, clientes, traspaso, gastos
import mysql.connector
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

app = FastAPI(prefix="/zeutica",tags=["/login"],responses={404: {"Mensaje":"No encontrado"}})  # Instancia de main

app.include_router(productos.router) # Router para api productos
app.include_router(ventas.router) # Router para api ventas
app.include_router(clientes.router) #Router para clientes
app.include_router(traspaso.router) # Router para traspasos
app.include_router(cotizacionesBack.router) # Router para cotizaciones
app.include_router(gastos.router) # Router para gastos operativos

app.add_middleware(  # Middleware para controlar accesos.
    CORSMiddleware,
    allow_origins=["*"], # En producción, pon aquí la URL de tu Streamlit
    allow_methods=["*"],
    allow_headers=["*"],
)
load_dotenv() # Carga de credenciales .env

# Configuración de la conexión
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

      # // AUTENTICACION DE USUARIOS PARA INGRESO AL SOFTWARE // 
# Función para encriptar al crear un usuario
def hash_password(password: str) -> str:
    # Generamos la sal y el hash
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

# Función para verificar al hacer login
def verify_password(plano_password: str, hashed_password: str) -> bool:
    pwd_bytes = plano_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)

@app.get("/")
async def test_server():
    return {"Servidor Conectado..."}

@app.post("/login") # Endpoint para autenticar usuarios
async def login(datos: dict):
    usuario = datos.get("usuario")
    password_ingresado = datos.get("password")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Buscamos el usuario en MySQL
    query = "SELECT password_hash FROM usuarios WHERE nombre_usuario = %s"
    cursor.execute(query, (usuario,))
    resultado = cursor.fetchone()
    
    if resultado:
        # 2. Verificamos la contraseña con bcrypt
        hash_guardado = resultado['password_hash']
        
        if verify_password(password_ingresado, hash_guardado):
            return {"auth": True, "mensaje": "Acceso exitoso"}
    
    # Si no existe el usuario o la contraseña no coincide
    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")


# Documentacion ip.server/docs (swagger)
# Docuementacion ip.server/redoc (redocly)