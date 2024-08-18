# controllers/products_and_bundles.py
from typing import List, Dict
import pyodbc
from fastapi import HTTPException
from dotenv import load_dotenv
from typing import Optional
import os

load_dotenv()

driver = os.getenv('SQL_DRIVER')
server = os.getenv('SQL_SERVER')
database = os.getenv('SQL_DATABASE')
username = os.getenv('SQL_USERNAME')
password = os.getenv('SQL_PASSWORD')

connection_string = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}"

def get_db_connection():
    try:
        conn = pyodbc.connect(connection_string, timeout=10)
        return conn
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")


def fetch_products_and_bundles(
    category: Optional[str] = None,
    size: Optional[str] = None,
    brand: Optional[str] = None,
    color: Optional[str] = None
) -> Dict[str, List[Dict]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Construir la cláusula WHERE con los filtros proporcionados
        filter_clauses = []
        params = []

        if category:
            filter_clauses.append("cat.CategoriaID = ?")
            params.append(category)
        if size:
            filter_clauses.append("t.Nombre = ?")
            params.append(size)
        if brand:
            filter_clauses.append("m.Nombre = ?")
            params.append(brand)
        if color:
            filter_clauses.append("c.Nombre = ?")
            params.append(color)

        filter_sql = " AND ".join(filter_clauses)
        if filter_sql:
            filter_sql = "WHERE " + filter_sql

        # Obtener productos con todos los datos
        cursor.execute(f"""
            SELECT
                p.ProductoID,
                p.Nombre AS NombreProducto,
                p.Stock,
                p.Img,
                c.Nombre AS NombreColor,
                m.Nombre AS NombreMarca,
                i.Precio
            FROM Productos p
            INNER JOIN Inventarios i ON p.ProductoID = i.ProductoID
            LEFT JOIN Marcas m ON p.MarcaID = m.MarcaID
            LEFT JOIN Colores c ON p.ColorID = c.ColorID
            LEFT JOIN ProductosCategorias pc ON p.ProductoID = pc.ProductoID
            LEFT JOIN Categorias cat ON pc.CategoriaID = cat.CategoriaID
            {filter_sql}
        """, params)

        productos = cursor.fetchall()

        # Crear un diccionario para agrupar las tallas por producto
        productos_dict = {}
        for row in productos:
            producto_id = row[0]
            if producto_id not in productos_dict:
                productos_dict[producto_id] = {
                    'ProductoID': row[0],
                    'NombreProducto': row[1],
                    'Stock': row[2],
                    'Img': row[3],
                    'Tallas': [],  # Inicializamos una lista vacía para las tallas
                    'NombreColor': row[4],
                    'NombreMarca': row[5],
                    'Precio': row[6]
                }

        # Obtener todas las tallas asociadas a cada producto
        cursor.execute("""
            SELECT
                p.ProductoID,
                t.Nombre AS NombreTalla
            FROM ProductoTallas pt
            INNER JOIN Productos p ON pt.ProductoID = p.ProductoID
            INNER JOIN Tallas t ON pt.TallaID = t.TallaID
        """)
        tallas = cursor.fetchall()
        for row in tallas:
            producto_id = row[0]
            talla_nombre = row[1]
            if producto_id in productos_dict:
                productos_dict[producto_id]['Tallas'].append(talla_nombre)

        # Convertir el diccionario a una lista
        productos_list = list(productos_dict.values())

        # Obtener bundles
        cursor.execute("""
            SELECT
                b.BundleID,
                b.Nombre AS NombreBundle,
                b.Descripcion AS DescripcionBundle,
                SUM(i.Precio * bd.Cantidad) AS PrecioTotalBundle
            FROM Bundles b
            INNER JOIN BundleDetalles bd ON b.BundleID = bd.BundleID
            INNER JOIN Inventarios i ON bd.ProductoID = i.ProductoID
            GROUP BY b.BundleID, b.Nombre, b.Descripcion
        """)
        bundles = cursor.fetchall()
        bundles_list = [dict(zip([column[0] for column in cursor.description], row)) for row in bundles]

        return {
            "productos": productos_list,
            "bundles": bundles_list
        }

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error executing query: {str(e)}")
    finally:
        cursor.close()
        conn.close()




def fetch_categories() -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                CategoriaID,
                Nombre AS NombreCategoria,
                Descripcion AS DescripcionCategoria
            FROM Categorias
        """)
        categories = cursor.fetchall()
        categories_list = [dict(zip([column[0] for column in cursor.description], row)) for row in categories]
        return categories_list

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error executing query: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def fetch_sizes() -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                TallaID,
                Nombre AS NombreTalla
            FROM Tallas
        """)
        sizes = cursor.fetchall()
        sizes_list = [dict(zip([column[0] for column in cursor.description], row)) for row in sizes]
        return sizes_list

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error executing query: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def fetch_brands() -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                MarcaID,
                Nombre AS NombreMarca,
                Hexadecimal AS HexadecimalMarca
            FROM Marcas
        """)
        brands = cursor.fetchall()
        brands_list = [dict(zip([column[0] for column in cursor.description], row)) for row in brands]
        return brands_list

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error executing query: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def fetch_colors() -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                ColorID,
                Nombre AS NombreColor
            FROM Colores
        """)
        colors = cursor.fetchall()
        colors_list = [dict(zip([column[0] for column in cursor.description], row)) for row in colors]
        return colors_list

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error executing query: {str(e)}")
    finally:
        cursor.close()
        conn.close()