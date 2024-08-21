# controllers/products
from typing import List, Dict
import pyodbc
from fastapi import HTTPException
from dotenv import load_dotenv
from typing import Optional
from azure.storage.blob import BlobServiceClient
import os

load_dotenv()

driver = os.getenv("SQL_DRIVER")
server = os.getenv("SQL_SERVER")
database = os.getenv("SQL_DATABASE")
username = os.getenv("SQL_USERNAME")
password = os.getenv("SQL_PASSWORD")

connection_string = (
    f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}"
)

azure_connection_string = os.getenv("AZURE_SAK")
container_name = os.getenv("AZURE_STORAGE_CONTAINER")

if not azure_connection_string or not container_name:
    raise ValueError(
        "AZURE_SAK and AZURE_STORAGE_CONTAINER must be set in environment variables"
    )

blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)
container_client = blob_service_client.get_container_client(container_name)


def get_db_connection():
    try:
        conn = pyodbc.connect(connection_string, timeout=10)
        return conn
    except pyodbc.Error as e:
        raise HTTPException(
            status_code=500, detail=f"Database connection error: {str(e)}"
        )


def fetch_products_and_bundles(
    category: Optional[str] = None,
    size: Optional[str] = None,
    brand: Optional[str] = None,
    color: Optional[str] = None,
) -> Dict[str, List[Dict]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Construir la cláusula WHERE con los filtros proporcionados
        filter_clauses = []
        params = []

        if category:
            filter_clauses.append("cat.Nombre = ?")
            params.append(category)
        if brand:
            filter_clauses.append("m.Nombre = ?")
            params.append(brand)
        if color:
            filter_clauses.append("c.Nombre = ?")
            params.append(color)
        if size:
            filter_clauses.append("t.Nombre = ?")
            params.append(size)

        # Solo aplicar la cláusula WHERE si hay filtros
        filter_sql = " AND ".join(filter_clauses)
        if filter_clauses:
            filter_sql = "WHERE " + filter_sql

        # Obtener productos con todos los datos
        cursor.execute(
            f"""
    SELECT
        p.ProductoID,
        p.Nombre AS NombreProducto,
        p.Stock,
        c.ColorID,
        c.Nombre AS NombreColor,
        pc.Img AS ImgColor,
        m.Nombre AS NombreMarca,
        i.Precio,
        t.TallaID,
        t.Nombre AS NombreTalla
    FROM Productos p
    INNER JOIN Inventarios i ON p.ProductoID = i.ProductoID
    LEFT JOIN Marcas m ON p.MarcaID = m.MarcaID
    LEFT JOIN ProductoColores pc ON p.ProductoID = pc.ProductoID
    LEFT JOIN Colores c ON pc.ColorID = c.ColorID
    LEFT JOIN ProductoTallas pt ON p.ProductoID = pt.ProductoID
    LEFT JOIN Tallas t ON pt.TallaID = t.TallaID
    LEFT JOIN ProductosCategorias pcg ON p.ProductoID = pcg.ProductoID
    LEFT JOIN Categorias cat ON pcg.CategoriaID = cat.CategoriaID
    {filter_sql}
""",
            params,
        )

        productos = cursor.fetchall()

        # Crear un diccionario para agrupar las tallas y colores por producto
        productos_dict = {}
        for row in productos:
            producto_id = row[0]

            color = {
                "ColorID": row[3],
                "NombreColor": row[4],
                "ImgColor": (
                    container_client.get_blob_client(row[5]).url if row[5] else None
                ),
            }
            talla = {"TallaID": row[8], "NombreTalla": row[9]}

            if producto_id not in productos_dict:
                productos_dict[producto_id] = {
                    "ProductoID": row[0],
                    "NombreProducto": row[1],
                    "Stock": row[2],
                    "Tallas": [talla] if talla["NombreTalla"] else [],
                    "Colores": [color] if color["NombreColor"] else [],
                    "NombreMarca": row[6],
                    "Precio": row[7],
                }
            else:
                if talla and talla not in productos_dict[producto_id]["Tallas"]:
                    productos_dict[producto_id]["Tallas"].append(talla)
                if color and color not in productos_dict[producto_id]["Colores"]:
                    productos_dict[producto_id]["Colores"].append(color)

        productos_list = list(productos_dict.values())

        # Obtener bundles que contienen productos que cumplen con los filtros
        cursor.execute(
            f"""
     SELECT
        b.BundleID,
        b.Nombre AS NombreBundle,
        b.Descripcion AS DescripcionBundle,
        b.CostoPreparacion AS CostoPreparacionBundle,
        SUM(i.Precio * bd.Cantidad) AS PrecioProductosBundle
    FROM Bundles b
    INNER JOIN BundleDetalles bd ON b.BundleID = bd.BundleID
    INNER JOIN Inventarios i ON bd.ProductoID = i.ProductoID
    INNER JOIN Productos p ON bd.ProductoID = p.ProductoID
    LEFT JOIN Marcas m ON p.MarcaID = m.MarcaID
    LEFT JOIN ProductoColores pc ON p.ProductoID = pc.ProductoID
    LEFT JOIN Colores c ON pc.ColorID = c.ColorID
    LEFT JOIN ProductosCategorias pcg ON p.ProductoID = pcg.ProductoID
    LEFT JOIN Categorias cat ON pcg.CategoriaID = cat.CategoriaID
    LEFT JOIN ProductoTallas pt ON p.ProductoID = pt.ProductoID
    LEFT JOIN Tallas t ON pt.TallaID = t.TallaID
    {filter_sql}
    GROUP BY b.BundleID, b.Nombre, b.Descripcion, b.CostoPreparacion
""",
            params,
        )
        bundles = cursor.fetchall()
        bundles_dict = {}
        for row in bundles:
            BundleID = row[0]
            bundles_dict[BundleID] = {
                "BundleID": row[0],
                "NombreBundle": row[1],
                "DescripcionBundle": row[2],
                "CostoPreparacionBundle": float(row[3]),
                "PrecioTotalBundle": float(row[4]),  # Inicializar el precio total
                "Productos": [],
                "Colores": [],
            }

        # Obtener los detalles de los productos en los bundles y calcular el precio total
        cursor.execute(
            """
SELECT
    bd.BundleID,
    p.ProductoID,
    p.Nombre AS NombreProducto,
    bd.Cantidad,
    i.Precio,
    pc.ColorID,
    c.Nombre AS NombreColor,
    pc.Img AS ImgColor,
    pt.TallaID,
    t.Nombre AS NombreTalla
FROM BundleDetalles bd
INNER JOIN Productos p ON bd.ProductoID = p.ProductoID
INNER JOIN Inventarios i ON p.ProductoID = i.ProductoID
LEFT JOIN ProductoColores pc ON p.ProductoID = pc.ProductoID
LEFT JOIN Colores c ON pc.ColorID = c.ColorID
LEFT JOIN ProductoTallas pt ON p.ProductoID = pt.ProductoID
LEFT JOIN Tallas t ON pt.TallaID = t.TallaID;
"""
        )
        bundle_productos = cursor.fetchall()

        for row in bundle_productos:
            BundleID = row[0]
            if BundleID in bundles_dict:
                producto_id = row[1]
                color = {
                    "ColorID": row[5],
                    "NombreColor": row[6],
                    "ImgColor": (
                        container_client.get_blob_client(row[7]).url if row[7] else None
                    ),
                }
                talla = {"TallaID": row[8], "NombreTalla": row[9]}

                if not any(
                    p["ProductoID"] == producto_id
                    for p in bundles_dict[BundleID]["Productos"]
                ):
                    bundles_dict[BundleID]["Productos"].append(
                        {
                            "ProductoID": producto_id,
                            "NombreProducto": row[2],
                            "Cantidad": row[3],
                            "PrecioUnitario": float(row[4]),
                            "Colores": [color],
                            "Tallas": [talla] if talla["NombreTalla"] else [],
                        }
                    )
                else:
                    # Agregar el color al producto existente
                    for producto in bundles_dict[BundleID]["Productos"]:
                        if producto["ProductoID"] == producto_id:
                            if color not in producto["Colores"]:
                                producto["Colores"].append(color)
                            if talla not in producto["Tallas"]:
                                producto["Tallas"].append(talla)

                            # Elimina productos que no tienen colores ni tallas
        for bundle in bundles_dict.values():
            for producto in bundle["Productos"]:
                if not producto["Colores"]:
                    del producto["Colores"]
                if not producto["Tallas"]:
                    del producto["Tallas"]

        # Obtener los colores asociados a cada bundle
        cursor.execute(
            """
    SELECT
        b.BundleID,
        c.ColorID,
        c.Nombre AS NombreColor,
        bc.Img AS ImgColor
    FROM BundleColores bc
    INNER JOIN Bundles b ON bc.BundleID = b.BundleID
    INNER JOIN Colores c ON bc.ColorID = c.ColorID
"""
        )
        bundle_colores = cursor.fetchall()

        for row in bundle_colores:
            BundleID = row[0]
            color = {
                "ColorID": row[1],
                "NombreColor": row[2],
                "ImgColor": (
                    container_client.get_blob_client(row[3]).url if row[3] else None
                ),
            }
            if BundleID in bundles_dict:
                bundles_dict[BundleID]["Colores"].append(color)

        # Sumar el costo de preparación al precio total del bundle
        for bundle in bundles_dict.values():
            # Precio total de productos
            precio_total_productos = sum(
                p["Cantidad"] * p["PrecioUnitario"] for p in bundle["Productos"]
            )
            # Sumar el costo de preparación
            bundle["PrecioTotalBundle"] = precio_total_productos + bundle.get(
                "CostoPreparacionBundle", 0
            )

        return {"productos": productos_list, "bundles": list(bundles_dict.values())}

    finally:
        cursor.close()
        conn.close()


def fetch_categories() -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                CategoriaID,
                Nombre AS NombreCategoria,
                Descripcion AS DescripcionCategoria
            FROM Categorias
        """
        )
        categories = cursor.fetchall()
        categories_list = [
            dict(zip([column[0] for column in cursor.description], row))
            for row in categories
        ]
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
        cursor.execute(
            """
            SELECT
                TallaID,
                Nombre AS NombreTalla
            FROM Tallas
        """
        )
        sizes = cursor.fetchall()
        sizes_list = [
            dict(zip([column[0] for column in cursor.description], row))
            for row in sizes
        ]
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
        cursor.execute(
            """
            SELECT
                MarcaID,
                Nombre AS NombreMarca,
                Hexadecimal AS HexadecimalMarca
            FROM Marcas
        """
        )
        brands = cursor.fetchall()
        brands_list = [
            dict(zip([column[0] for column in cursor.description], row))
            for row in brands
        ]
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
        cursor.execute(
            """
            SELECT
                ColorID,
                Nombre AS NombreColor
            FROM Colores
        """
        )
        colors = cursor.fetchall()
        colors_list = [
            dict(zip([column[0] for column in cursor.description], row))
            for row in colors
        ]
        return colors_list

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error executing query: {str(e)}")
    finally:
        cursor.close()
        conn.close()
