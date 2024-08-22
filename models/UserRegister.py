from pydantic import BaseModel, EmailStr
from typing import Optional


class UserRegister(BaseModel):
    primer_nombre: str
    segundo_nombre: Optional[str] = None
    primer_apellido: str
    segundo_apellido: Optional[str] = None
    correo: EmailStr
    password: str
