from fastapi import FastAPI, Request, Depends, Query, Response
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from controllers.o365 import login_o365, auth_callback_o365
from controllers.google import login_google, auth_callback_google
from controllers.checkout import (
    fetch_all_payment_types,
    fetch_all_states,
    fetch_cities_by_states,
    insertar_factura,
)
from controllers.firebase import register_user_firebase, login_user_firebase
from controllers.products import (
    fetch_products_and_bundles,
    fetch_categories,
    fetch_sizes,
    fetch_brands,
    fetch_colors,
)
from utils.security import validate, validate_func
from models.UserRegister import UserRegister
from models.UserLogin import UserLogin
from models.factura import FacturaRequest
from typing import Optional
import os
from dotenv import load_dotenv
import random
import string
from fastapi.security import OAuth2PasswordBearer


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

# Add SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY_MIDDLEWARE"))


@app.get("/")
async def hello():
    return {"Hello": "World", "version": "0.1.15"}


@app.get("/login/outlook")
async def login(request: Request):
    return await login_o365(request)


@app.get("/auth/callback")
async def authcallback(request: Request):
    return await auth_callback_o365(request)


@app.get("/login/google")
async def logingoogle():
    return await login_google()


@app.get("/auth/google/callback")
async def authcallbackgoogle(request: Request):
    return await auth_callback_google(request)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.post("/user/{email}/code")
@validate_func
def request_code(email: str, token: str = Depends(oauth2_scheme)):
    # Lógica para manejar la solicitud
    return {"message": "Code requested"}


@app.post("/register")
async def register(user: UserRegister):
    return await register_user_firebase(user)


@app.post("/login")
async def login(user: UserLogin):
    return await login_user_firebase(user)


@app.get("/products")
async def get_products(
    category: Optional[str] = Query(None),
    size: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
):
    return fetch_products_and_bundles(category, size, brand, color)


@app.get("/categories")
async def get_categories():
    return fetch_categories()


@app.get("/sizes")
async def get_sizes():
    return fetch_sizes()


@app.get("/brands")
async def get_brands():
    return fetch_brands()


@app.get("/colors")
async def get_colors():
    return fetch_colors()


@app.get("/user")
@validate
async def user(request: Request):
    return {
        "email": request.state.email,
        "firstname": request.state.firstname,
        "secondname": request.state.secondname,
        "lastname": request.state.lastname,
        "secondlastname": request.state.secondlastname,
        "usuario_id": request.state.usuario_id,
        "tipo_usuario_id": request.state.tipo_usuario_id,
        "active": request.state.active,
    }


@app.get("/payment/types")
async def get_payment_types():
    return await fetch_all_payment_types()


@app.get("/states")
async def get_states():
    return await fetch_all_states()


@app.get("/states/{state_id}/cities")
async def get_cities(state_id: int):
    return await fetch_cities_by_states(state_id)


@app.post("/factura")
async def crear_factura(factura_request: FacturaRequest):
    return await insertar_factura(factura_request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
