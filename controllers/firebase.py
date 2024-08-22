import os
import requests
import json
import logging
import traceback

from dotenv import load_dotenv
from fastapi import HTTPException, Depends
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from utils.database import fetch_query_as_json, get_db_connection
from models.UserRegister import UserRegister
from models.UserLogin import UserLogin

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Inicializar la app de Firebase Admin
cred = credentials.Certificate("secrets/admin-firebasesdk.json")
firebase_admin.initialize_app(cred)


async def register_user_firebase(user: UserRegister):
    try:
        # Crear usuario en Firebase Authentication
        user_record = firebase_auth.create_user(
            email=user.correo, password=user.password
        )

        conn = await get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO Usuarios (TipoUsuarioID, Primer_Nombre, Segundo_Nombre, Primer_Apellido, Segundo_Apellido, Correo) VALUES (?, ?, ?, ?, ?, ?)",
                1,  # TipoUsuarioID por defecto es 1 (Cliente)
                user.primer_nombre,
                user.segundo_nombre,
                user.primer_apellido,
                user.segundo_apellido,
                user.correo,
            )
            conn.commit()
            return {"success": True, "message": "Usuario registrado exitosamente"}
        except Exception as e:
            firebase_auth.delete_user(user_record.uid)
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al registrar usuario: {e}")


async def login_user_firebase(user: UserLogin):
    try:
        print(f"Payload recibido: {user.json()}")
        # Autenticar usuario con Firebase Authentication usando la API REST
        api_key = os.getenv("FIREBASE_API_KEY")
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": user.email,
            "password": user.password,
            "returnSecureToken": True,
        }
        response = requests.post(url, json=payload)
        response_data = response.json()
        print(f"Respuesta de Firebase: {response_data}")

        if "error" in response_data:
            raise HTTPException(
                status_code=400,
                detail=f"Error al autenticar usuario: {response_data['error']['message']}",
            )

        query = f"SELECT * FROM Usuarios WHERE Correo = '{user.email}'"
        result_json = await fetch_query_as_json(query)

        # Asegúrate de manejar la deserialización de JSON aquí si es necesario
        result_dict = json.loads(result_json)
        return {
            "message": "Usuario autenticado exitosamente",
            "idToken": response_data["idToken"],
        }

    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
