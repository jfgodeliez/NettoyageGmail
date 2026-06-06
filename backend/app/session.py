"""Gestion de session : cookie signé + vérification mot de passe."""

import hashlib
import os
import secrets

from fastapi import Cookie, HTTPException, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE = "ng_session"
SESSION_MAX_AGE = 86400 * 7  # 7 jours
_SECRET = os.getenv("SESSION_SECRET", "")
_PASSWORD_HASH = os.getenv("APP_PASSWORD_HASH", "")


def _signer() -> URLSafeTimedSerializer:
    if not _SECRET:
        raise RuntimeError("SESSION_SECRET non défini dans .env")
    return URLSafeTimedSerializer(_SECRET)


# ── Mot de passe ──────────────────────────────────────────────────────────────

def verify_password(plain: str) -> bool:
    if not _PASSWORD_HASH or ":" not in _PASSWORD_HASH:
        return False
    salt, stored = _PASSWORD_HASH.split(":", 1)
    computed = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100_000)
    return secrets.compare_digest(stored, computed.hex())


def hash_password(plain: str) -> str:
    """Utilitaire CLI : génère APP_PASSWORD_HASH pour le .env."""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100_000)
    return f"{salt}:{h.hex()}"


# ── Cookie de session ─────────────────────────────────────────────────────────

def create_session(response: Response) -> None:
    token = _signer().dumps("ok")
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
    )


def delete_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)


def require_session(ng_session: str = Cookie(None)) -> None:
    """Dépendance FastAPI : lève 401 si le cookie de session est absent ou invalide."""
    if not ng_session:
        raise HTTPException(status_code=401, detail="Connexion requise")
    try:
        _signer().loads(ng_session, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Session expirée")
