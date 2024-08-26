from pydantic import BaseModel
from typing import List, Optional


class Size(BaseModel):
    TallaID: Optional[int] = None
    NombreTalla: Optional[str] = None


class Color(BaseModel):
    ColorID: int
    NombreColor: str
    ImgColor: str


class Producto(BaseModel):
    id: int
    name: str
    quantity: int
    ItemTypeID: int
    sizeId: Optional[Size] = None
    colorId: Color
    id_bundle: Optional[int] = None


class CartItem(BaseModel):
    id: int
    name: str
    price: float
    quantity: int
    ItemTypeID: int
    colorId: Color
    sizeId: Optional[Size] = None
    productos: List[Producto]


class FacturaRequest(BaseModel):
    departamento: int
    ciudad: int
    direccion: str
    telefono: str
    tipoPago: int
    cart: List[CartItem]
    observations: str
    userId: int
    subtotal: float
    isv: float
    total: float
