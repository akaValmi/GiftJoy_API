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
from utils.security import create_jwt_token
from models.Userlogin import UserRegister

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
            email=user.email,
            password=user.password
        )

        conn = await get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "EXEC otd.create_user @username = ?, @name = ?, @email = ?",
                user_record.uid,
                user.name,
                user.email
            )
            conn.commit()
            return {
                "success": True,
                "message": "Usuario registrado exitosamente"
            }
        except Exception as e:
            firebase_auth.delete_user(user_record.uid)
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error al registrar usuario: {e}"
        )

async def login_user_firebase(user: UserRegister):
    try:
        # Autenticar usuario con Firebase Authentication usando la API REST
        api_key = os.getenv("FIREBASE_API_KEY")  # Reemplaza esto con tu apiKey de Firebase
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": user.email,
            "password": user.password,
            "returnSecureToken": True
        }
        response = requests.post(url, json=payload)
        response_data = response.json()

        if "error" in response_data:
            raise HTTPException(
                status_code=400,
                detail=f"Error al autenticar usuario: {response_data['error']['message']}"
            )

        query = f"SELECT active FROM otd.users WHERE email = '{user.email}'"

        try:
            logger.info(f"QUERY LIST")
            result_json = await fetch_query_as_json(query)
            result_dict = json.loads(result_json)
            return {
                "message": "Usuario autenticado exitosamente",
                "idToken": create_jwt_token(
                    user.email,
                    result_dict[0]["active"]
                )
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    except Exception as e:
        error_detail = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(
            status_code=400,
            detail=f"Error al registrar usuario: {error_detail}"
        )