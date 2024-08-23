import os
import secrets
import hashlib
import base64
import jwt

from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from dotenv import load_dotenv
from functools import wraps
import firebase_admin
from firebase_admin import auth

from utils.database import get_db_connection

load_dotenv()


# Cargar la clave secreta desde las variables de entorno
SECRET_KEY = os.getenv("SECRET_KEY")


def generate_pkce_verifier() -> str:
    """
    Genera un código PKCE (Proof Key for Code Exchange) Verifier.
    """
    return secrets.token_urlsafe(32)


def generate_pkce_challenge(verifier: str) -> str:
    """
    Genera un desafío PKCE basado en el Verifier.
    """
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def create_jwt_token(firstname: str, lastname: str, email: str, active: bool):
    expiration = datetime.utcnow() + timedelta(hours=1)  # El token expira en 1 hora
    token = jwt.encode(
        {
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "active": active,
            "exp": expiration,
            "iat": datetime.utcnow(),
        },
        SECRET_KEY,
        algorithm="HS256",
    )
    return token


def validate(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request:
            raise HTTPException(status_code=400, detail="Request object not found")

        authorization: str = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=400, detail="Authorization header missing")

        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=400, detail="Invalid authentication scheme"
                )

            # Verificar el token usando Firebase Admin SDK
            decoded_token = auth.verify_id_token(token)
            email = decoded_token.get("email")
            if email is None:
                raise HTTPException(status_code=400, detail="Invalid token")

            # Conectar a la base de datos SQL Server y obtener más datos del usuario
            conn = await get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT UsuarioID, TipoUsuarioID, Primer_Nombre, Segundo_Nombre, Primer_Apellido, Segundo_Apellido, active FROM Usuarios WHERE Correo = ?",
                (email,),
            )
            user_data = cursor.fetchone()

            if not user_data:
                raise HTTPException(
                    status_code=404, detail="User not found in the database"
                )

            # Asignar los datos a request.state
            request.state.email = email
            request.state.usuario_id = user_data[0]
            request.state.tipo_usuario_id = user_data[1]
            request.state.firstname = user_data[2]
            request.state.secondname = user_data[3]
            request.state.lastname = user_data[4]
            request.state.secondlastname = user_data[5]
            request.state.active = user_data[6]

        except ValueError as ve:
            raise HTTPException(
                status_code=400, detail=f"Invalid token format: {str(ve)}"
            )
        except firebase_admin.auth.InvalidIdTokenError as it:
            raise HTTPException(
                status_code=401, detail=f"Invalid token or expired token: {str(it)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Internal Server Error: {str(e)}"
            )

        return await func(*args, **kwargs)

    return wrapper


def validate_func(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request:
            raise HTTPException(status_code=400, detail="Request object not found")

        authorization: str = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=403, detail="Authorization header missing")

        if authorization != SECRET_KEY_FUNC:
            raise HTTPException(status_code=403, detail="Wrong function key")

        return await func(*args, **kwargs)

    return wrapper
