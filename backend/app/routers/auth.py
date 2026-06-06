"""Routes auth : login app (password) + OAuth2 Gmail."""

import os

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired
from pydantic import BaseModel

from ..auth_web import exchange_code, get_authorization_url, is_authenticated, revoke
from ..session import SESSION_MAX_AGE, create_session, delete_session, require_session, verify_password, _signer

router = APIRouter(prefix="/auth", tags=["auth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


# ── Auth application (mot de passe) ──────────────────────────────────────────

class LoginRequest(BaseModel):
    password: str


@router.get("/app-status")
def app_status(ng_session: str = Cookie(None)):
    if not ng_session:
        return {"authenticated": False}
    try:
        _signer().loads(ng_session, max_age=SESSION_MAX_AGE)
        return {"authenticated": True}
    except (BadSignature, SignatureExpired):
        return {"authenticated": False}


@router.post("/app-login")
def app_login(body: LoginRequest, response: Response):
    if not verify_password(body.password):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    create_session(response)
    return {"ok": True}


@router.post("/app-logout")
def app_logout(response: Response):
    delete_session(response)
    revoke()
    return {"ok": True}


# ── Auth Gmail (OAuth2) ───────────────────────────────────────────────────────

@router.get("/status")
def gmail_status(_=Depends(require_session)):
    return {"authenticated": is_authenticated()}


@router.get("/login")
def gmail_login(_=Depends(require_session)):
    url, _ = get_authorization_url()
    return RedirectResponse(url)


@router.get("/callback")
def callback(code: str, state: str = "", _=Depends(require_session)):
    try:
        exchange_code(code, state)
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/?error={str(e)}")
    return RedirectResponse(f"{FRONTEND_URL}/")


@router.post("/logout")
def gmail_logout(_=Depends(require_session)):
    revoke()
    return {"ok": True}
