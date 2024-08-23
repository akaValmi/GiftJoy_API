from fastapi import HTTPException
from typing import List
import pyodbc
from utils.database import get_db_connection
from models.factura import FacturaRequest


async def fetch_all_payment_types() -> List[dict]:
    conn = None
    cursor = None
    try:
        conn = await get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT TipoPagoID, Nombre FROM TiposPago")
        rows = cursor.fetchall()
        return [{"TipoPagoID": row.TipoPagoID, "Nombre": row.Nombre} for row in rows]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener los tipos de pago: {e}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def fetch_all_states() -> List[dict]:
    conn = None
    cursor = None
    try:
        conn = await get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DepartamentoID, Nombre FROM Departamentos")
        rows = cursor.fetchall()
        return [
            {"DepartamentoID": row.DepartamentoID, "Nombre": row.Nombre} for row in rows
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener los departamentos: {e}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def fetch_cities_by_states(state_id: int) -> List[dict]:
    conn = None
    cursor = None
    try:
        conn = await get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT CiudadID, Nombre 
            FROM Ciudades
            WHERE DepartamentoID = ?
        """,
            (state_id,),
        )
        rows = cursor.fetchall()
        return [{"CiudadID": row.CiudadID, "Nombre": row.Nombre} for row in rows]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener las ciudades: {e}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def insertar_factura(factura_request: FacturaRequest):
    conn = None
    cursor = None
    try:
        conn = (
            await get_db_connection()
        )  # Suponiendo que esta función maneja la conexión
        cursor = conn.cursor()
        # Print the address information for debugging

        # Insert or update address
        cursor.execute(
            """
            IF NOT EXISTS (SELECT 1 FROM Direcciones
                            WHERE UsuarioID = ? AND CiudadID = ? AND Direccion = ? AND Telefono = ?)
            BEGIN
                INSERT INTO Direcciones (UsuarioID, CiudadID, Direccion, Telefono)
                VALUES (?, ?, ?, ?)
            END
            """,
            (
                factura_request.userId,
                factura_request.ciudad,
                factura_request.direccion,
                factura_request.telefono,
                factura_request.userId,
                factura_request.ciudad,
                factura_request.direccion,
                factura_request.telefono,
            ),
        )
        conn.commit()

        # Get the address ID
        cursor.execute(
            """
            SELECT DireccionID
            FROM Direcciones
            WHERE UsuarioID = ? AND CiudadID = ? AND Direccion = ? AND Telefono = ?
            """,
            (
                factura_request.userId,
                factura_request.ciudad,
                factura_request.direccion,
                factura_request.telefono,
            ),
        )
        direccion_id = cursor.fetchone()[0]
        print(f"DireccionID obtenido: {direccion_id}")

        # Insert invoice
        cursor.execute(
            """
    INSERT INTO Facturas (UsuarioID, EstadoID, TipoPagoID, DireccionID, Descuento, Total, Impuestos, RTN, Observaciones)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
            (
                factura_request.userId,
                1,
                factura_request.tipoPago,
                direccion_id,
                0,  # Valor para Descuento
                factura_request.total,
                factura_request.isv,
                "123456",
                factura_request.observations,
            ),
        )
        conn.commit()

        # Get the invoice ID
        cursor.execute("SELECT @@IDENTITY AS FacturaID")
        result = cursor.fetchone()
        if result:
            FacturaID = result[0]
            if FacturaID is None:
                raise Exception("Error retrieving FacturaID.")
            print(f"FacturaID obtenido: {FacturaID}")
        else:
            raise Exception("Error retrieving FacturaID.")

        # Insert invoice details
        for item in factura_request.cart:
            cursor.execute(
                """
                INSERT INTO DetallesFacturas (FacturaID, ItemID, ItemTypeID, ColorID, TallaID, Cantidad, Precio)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    FacturaID,
                    item.id,
                    item.ItemTypeID,
                    item.colorId.ColorID,
                    item.sizeId.TallaID if item.sizeId else None,
                    item.quantity,
                    item.price,
                ),
            )
            if item.productos:
                for producto in item.productos:
                    cursor.execute(
                        """
                        INSERT INTO DetallesFacturas (FacturaID, ItemID, ItemTypeID, ColorID, TallaID, Cantidad, Precio)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            FacturaID,
                            producto.id,
                            producto.ItemTypeID,
                            producto.colorId.ColorID,
                            producto.sizeId.TallaID if producto.sizeId else None,
                            producto.quantity,
                            0,  # Precio 0 para productos dentro de bundles
                        ),
                    )

        conn.commit()
        return {"message": "Factura creada exitosamente"}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear la factura: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
