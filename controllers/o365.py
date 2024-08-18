import os
from fastapi import HTTPException, Request
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.responses import RedirectResponse, JSONResponse
from urllib.parse import urlencode
import requests

from utils.security import generate_pkce_verifier, generate_pkce_challenge

from dotenv import load_dotenv
load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
tenant_id = os.getenv("TENANT_ID")
redirect_uri = os.getenv("REDIRECT_URI")

# Imprimir valores del entorno para depuración
print(f"CLIENT_ID: {client_id}")
print(f"CLIENT_SECRET: {client_secret}")
print(f"TENANT_ID: {tenant_id}")
print(f"REDIRECT_URI: {redirect_uri}")

# OAuth2 configuration
authorization_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=authorization_url,
    tokenUrl=token_url,
)

async def login_o365(request: Request):
    pkce_verifier = generate_pkce_verifier()  # Generate the PKCE verifier
    pkce_challenge = generate_pkce_challenge(pkce_verifier)

    # Store the PKCE verifier in the session or a temporary storage
    request.session['pkce_verifier'] = pkce_verifier

    auth_url_params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": "User.Read",
        "code_challenge": pkce_challenge,
        "code_challenge_method": "S256"
    }
    auth_url = f"{authorization_url}?{urlencode(auth_url_params)}"
    return RedirectResponse(auth_url)

async def auth_callback_o365(request: Request):
    code = request.query_params.get("code")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    # Recupera el PKCE verifier de la sesión
    pkce_verifier = request.session.get('pkce_verifier')
    if not pkce_verifier:
        raise HTTPException(status_code=400, detail="PKCE verifier not found in session")

    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,  # Añadir el client_secret aquí
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": pkce_verifier  # Usa el PKCE verifier correcto
    }

    token_response = requests.post(token_url, data=token_data)
    token_response_data = token_response.json()

    if "access_token" in token_response_data:
        return JSONResponse(content={"access_token": token_response_data["access_token"]})
    else:
        return JSONResponse(content={
            "error": token_response_data.get("error"),
            "error_description": token_response_data.get("error_description")},
            status_code=400
        )
