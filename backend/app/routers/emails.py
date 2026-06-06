"""Routes emails : aperçu corps /api/emails/{id}/preview."""

from fastapi import APIRouter, Depends, HTTPException

from ..auth_web import build_gmail_service, is_authenticated
from ..gmail_client import fetch_email_body

router = APIRouter(prefix="/api/emails", tags=["emails"])


def _require_auth():
    if not is_authenticated():
        raise HTTPException(status_code=401, detail="Non authentifié")


@router.get("/{msg_id}/preview")
def email_preview(msg_id: str, _=Depends(_require_auth)):
    """Retourne le corps HTML ou texte d'un email pour l'aperçu."""
    try:
        service = build_gmail_service()
        result = fetch_email_body(service, msg_id)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
