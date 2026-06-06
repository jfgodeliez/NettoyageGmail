"""Routes emails : aperçu et déplacement entre groupes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth_web import build_gmail_service
from ..session import require_session
from ..gmail_client import fetch_email_body
from .. import cache

router = APIRouter(prefix="/api/emails", tags=["emails"])


class MoveRequest(BaseModel):
    target_group_id: int


@router.get("/{msg_id}/preview")
def email_preview(msg_id: str, _=Depends(require_session)):
    try:
        service = build_gmail_service()
        return fetch_email_body(service, msg_id)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/{msg_id}/move")
def move_email(msg_id: str, body: MoveRequest, _=Depends(require_session)):
    groups = cache.get_group_list()
    if not any(g["group_id"] == body.target_group_id for g in groups):
        raise HTTPException(status_code=404, detail="Groupe cible introuvable")
    cache.move_email(msg_id, body.target_group_id)
    return {"ok": True}


@router.delete("/{msg_id}/move")
def reset_move(msg_id: str, _=Depends(require_session)):
    cache.reset_email_override(msg_id)
    return {"ok": True}
