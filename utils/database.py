from dotenv import load_dotenv
import os
import pyodbc
import logging
import json
from datetime import datetime

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

driver = os.getenv("SQL_DRIVER")
server = os.getenv("SQL_SERVER")
database = os.getenv("SQL_DATABASE")
username = os.getenv("SQL_USERNAME")
password = os.getenv("SQL_PASSWORD")


connection_string = (
    f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}"
)


def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()  # Convert datetime to ISO format string
    raise TypeError("Type not serializable")


async def get_db_connection():
    try:
        logger.info(
            f"Intentando conectar a la base de datos con la cadena de conexión: {connection_string}"
        )
        conn = pyodbc.connect(connection_string, timeout=10)
        logger.info("Conexión exitosa a la base de datos.")
        return conn
    except pyodbc.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise Exception(f"Database connection error: {str(e)}")


async def fetch_query_as_json(query):
    conn = await get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    result = []

    for row in rows:
        row_dict = dict(zip(columns, row))
        result.append(row_dict)

    cursor.close()
    conn.close()

    return json.dumps(result, default=json_serial)
