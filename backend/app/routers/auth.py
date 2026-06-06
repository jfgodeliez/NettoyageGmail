"""Routes OAuth2 : /auth/login, /auth/callback, /auth/logout, /auth/status."""

import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ..auth_web import exchange_code, get_authorization_url, is_authenticated, revoke

router = APIRouter(prefix="/auth", tags=["auth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Stockage temporaire du state OAuth2 (mémoire, suffisant pour usage mono-utilisateur)
_oauth_state: dict[str, str] = {}


@router.get("/status")
def auth_status():
    return {"authenticated": is_authenticated()}


@router.get("/login")
def login():
    url, state = get_authorization_url()
    _oauth_state["current"] = state
    return RedirectResponse(url)


@router.get("/callback")
def callback(code: str, state: str):
    stored_state = _oauth_state.pop("current", None)
    if stored_state and state != stored_state:
        return JSONResponse({"error": "State invalide"}, status_code=400)
    try:
        exchange_code(code, state)
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/?error={str(e)}")
    return RedirectResponse(f"{FRONTEND_URL}/")


@router.post("/logout")
def logout():
    revoke()
    return {"ok": True}
