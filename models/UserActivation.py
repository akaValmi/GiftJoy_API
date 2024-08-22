from pydantic import BaseModel, EmailStr


class UserActivation(BaseModel):
    email: EmailStr
    code: int

    class Config:
        schema_extra = {"example": {"email": "user@example.com", "code": 123456}}
