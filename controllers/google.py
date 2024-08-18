import os
from fastapi import HTTPException, Request
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.responses import RedirectResponse, JSONResponse
from urllib.parse import urlencode
import requests

from dotenv import load_dotenv
load_dotenv()

google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

google_authorization_url = "https://accounts.google.com/o/oauth2/auth"
google_token_url = "https://oauth2.googleapis.com/token"
userinfo_url = "https://openidconnect.googleapis.com/v1/userinfo"

google_oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=google_authorization_url,
    tokenUrl=google_token_url,
)

async def login_google():
    auth_url_params = {
        "client_id": google_client_id,
        "response_type": "code",
        "redirect_uri": google_redirect_uri,
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{google_authorization_url}?{urlencode(auth_url_params)}"
    return RedirectResponse(auth_url)

async def auth_callback_google(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    token_data = {
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": google_redirect_uri,
    }

    token_response = requests.post(google_token_url, data=token_data)
    token_response_data = token_response.json()

    if "access_token" not in token_response_data:
        return JSONResponse(content={
                "error": token_response_data.get("error")
                , "error_description": token_response_data.get("error_description")
            }
            , status_code=400
        )

    access_token = token_response_data["access_token"]
    userinfo_response = requests.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
    userinfo_data = userinfo_response.json()

    return JSONResponse(content={"userinfo": userinfo_data})