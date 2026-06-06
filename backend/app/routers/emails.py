"""Routes emails : aperçu et déplacement entre groupes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth_web import build_gmail_service, is_authenticated
from ..gmail_client import fetch_email_body
from .. import cache

router = APIRouter(prefix="/api/emails", tags=["emails"])


def _require_auth():
    if not is_authenticated():
        raise HTTPException(status_code=401, detail="Non authentifié")


class MoveRequest(BaseModel):
    target_group_id: int


@router.get("/{msg_id}/preview")
def email_preview(msg_id: str, _=Depends(_require_auth)):
    try:
        service = build_gmail_service()
        return fetch_email_body(service, msg_id)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/{msg_id}/move")
def move_email(msg_id: str, body: MoveRequest, _=Depends(_require_auth)):
    """Déplace un email vers un autre groupe (override persistant)."""
    groups = cache.get_group_list()
    if not any(g["group_id"] == body.target_group_id for g in groups):
        raise HTTPException(status_code=404, detail="Groupe cible introuvable")
    cache.move_email(msg_id, body.target_group_id)
    return {"ok": True}


@router.delete("/{msg_id}/move")
def reset_move(msg_id: str, _=Depends(_require_auth)):
    """Remet un email dans son groupe d'origine."""
    cache.reset_email_override(msg_id)
    return {"ok": True}
