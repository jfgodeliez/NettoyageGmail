"""Routes OAuth2 : /auth/login, /auth/callback, /auth/logout, /auth/status."""

import os

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from ..auth_web import exchange_code, get_authorization_url, is_authenticated, revoke

router = APIRouter(prefix="/auth", tags=["auth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@router.get("/status")
def auth_status():
    return {"authenticated": is_authenticated()}


@router.get("/login")
def login():
    url, _ = get_authorization_url()
    return RedirectResponse(url)


@router.get("/callback")
def callback(code: str, state: str = ""):
    try:
        exchange_code(code, state)
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/?error={str(e)}")
    return RedirectResponse(f"{FRONTEND_URL}/")


@router.post("/logout")
def logout():
    revoke()
    return {"ok": True}
