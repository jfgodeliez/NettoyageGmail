"""Authentification OAuth2 Gmail — flux web (redirect + callback)."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "/data/token.json")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")


def get_authorization_url() -> tuple[str, str]:
    """Retourne (url_google, state) pour démarrer le flux OAuth2."""
    flow = Flow.from_client_secrets_file(CREDENTIALS_FILE, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url, state


def exchange_code(code: str, state: str) -> Credentials:
    """Échange le code d'autorisation contre des credentials et les stocke."""
    flow = Flow.from_client_secrets_file(CREDENTIALS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = REDIRECT_URI
    flow.fetch_token(code=code)
    creds = flow.credentials
    Path(TOKEN_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    return creds


def get_credentials() -> Credentials | None:
    """Retourne les credentials stockés, rafraîchis si nécessaire."""
    if not Path(TOKEN_FILE).exists():
        return None
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        else:
            return None
    return creds


def is_authenticated() -> bool:
    return get_credentials() is not None


def build_gmail_service():
    creds = get_credentials()
    if not creds:
        raise RuntimeError("Non authentifié")
    return build("gmail", "v1", credentials=creds)


def revoke() -> None:
    """Supprime le token local."""
    if Path(TOKEN_FILE).exists():
        Path(TOKEN_FILE).unlink()
