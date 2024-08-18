from fastapi import FastAPI, Request, Depends, Query
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from controllers.o365 import login_o365, auth_callback_o365
from controllers.google import login_google, auth_callback_google
from controllers.firebase import register_user_firebase, login_user_firebase
from controllers.products import fetch_products_and_bundles, fetch_categories, fetch_sizes, fetch_brands, fetch_colors
from utils.security import validate
from models.Userlogin import UserRegister
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Cambia esto según la URL de tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key="valmivalmi120WS")

@app.get("/")
async def hello():
    return {
        "Hello": "World"
        , "version": "0.1.15"
    }

@app.get("/login")
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

@app.post("/register")
async def register(user: UserRegister):
    return await register_user_firebase(user)

@app.post("/login/custom")
async def login_custom(user: UserRegister):
    return await login_user_firebase(user)






@app.get("/user")
@validate
async def user(request: Request):
    return {
        "email": request.state.email
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)





@app.get("/products")
async def get_products(
    category: Optional[str] = Query(None),
    size: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    color: Optional[str] = Query(None)
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

