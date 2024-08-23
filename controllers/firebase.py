import os
import requests
import json
import logging
from dotenv import load_dotenv
from fastapi import HTTPException
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from azure.storage.queue import (
    QueueServiceClient,
    BinaryBase64EncodePolicy,
    BinaryBase64DecodePolicy,
)
from utils.database import fetch_query_as_json, get_db_connection
from models.UserRegister import UserRegister
from models.UserLogin import UserLogin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Inicializar la app de Firebase Admin
cred = credentials.Certificate("secrets/admin-firebasesdk.json")
firebase_admin.initialize_app(cred)


async def register_user_firebase(user: UserRegister):
    conn = None
    cursor = None
    user_record = None
    try:
        api_key = os.getenv("FIREBASE_API_KEY")
        if not api_key:
            raise ValueError("FIREBASE_API_KEY no está configurada")

        # Crear usuario en Firebase Authentication
        user_record = firebase_auth.create_user(
            email=user.correo, password=user.password
        )
        if not user_record:
            raise ValueError("No se pudo crear el usuario en Firebase")

        logger.info(f"Usuario creado en Firebase: {user_record.uid}")

        # Establecer conexión con la base de datos
        conn = await get_db_connection()
        cursor = conn.cursor()

        # Validar cadena de conexión de la cola
        queue_connection_string = os.getenv("QueueAzureWebJobsStorage")
        if queue_connection_string is None:
            raise ValueError("QueueAzureWebJobsStorage no está configurada")

        # Enviar mensaje a la cola para activar la cuenta
        queue_service = QueueServiceClient.from_connection_string(
            queue_connection_string
        )

        # Configurar las políticas de codificación y decodificación Base64
        queue_client = queue_service.get_queue_client("queueactivation")
        message = user.correo
        queue_client.send_message(message)

        logger.info("Mensaje enviado a la cola")

        # Registrar usuario en la base de datos solo si el mensaje se envió con éxito
        cursor.execute(
            "INSERT INTO Usuarios (TipoUsuarioID, Primer_Nombre, Segundo_Nombre, Primer_Apellido, Segundo_Apellido, Correo) VALUES (?, ?, ?, ?, ?, ?)",
            (
                1,
                user.primer_nombre,
                user.segundo_nombre,
                user.primer_apellido,
                user.segundo_apellido,
                user.correo,
            ),
        )
        conn.commit()
        logger.info("Usuario insertado en la base de datos")

        return {
            "success": True,
            "message": "Usuario registrado exitosamente, se ha enviado un correo para activar la cuenta",
        }

    except Exception as e:
        if user_record:
            # Eliminar el usuario de Firebase si hay un error
            firebase_auth.delete_user(user_record.uid)
            logger.info(f"Usuario eliminado de Firebase: {user_record.uid}")

        if conn:
            conn.rollback()

        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al registrar usuario: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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


async def generate_activation_code(email: str):

    code = random.randint(100000, 999999)
    query = f" exec otd.generate_activation_code @email = '{email}', @code = {code}"
    result = {}
    try:
        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Código de activación generado exitosamente", "code": code}
