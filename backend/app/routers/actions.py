"""Routes décisions et exécution : /api/decisions, /api/execute."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth_web import build_gmail_service
from ..session import require_session
from .. import cache, actions as gmail_actions

router = APIRouter(prefix="/api", tags=["actions"])

VALID_ACTIONS = {"keep", "trash", "archive"}


class DecisionRequest(BaseModel):
    group_id: int
    action: str


class ExecuteRequest(BaseModel):
    dry_run: bool = False


@router.post("/decisions")
def save_decision(body: DecisionRequest, _=Depends(require_session)):
    if body.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Action invalide : {body.action}")
    cache.save_decision(body.group_id, body.action)
    return {"ok": True}


@router.get("/decisions")
def get_decisions(_=Depends(require_session)):
    return cache.load_decisions()


@router.delete("/decisions")
def clear_decisions(_=Depends(require_session)):
    cache.clear_decisions()
    return {"ok": True}


@router.post("/execute")
def execute(body: ExecuteRequest, _=Depends(require_session)):
    decisions = cache.load_decisions()
    if not decisions:
        raise HTTPException(status_code=400, detail="Aucune décision à exécuter")

    groups = cache.load_groups_with_emails()
    groups_by_id = {g.group_id: g for g in groups}

    service = None if body.dry_run else build_gmail_service()
    result = gmail_actions.execute_decisions(service, decisions, groups_by_id, dry_run=body.dry_run)

    if not body.dry_run and result.done > 0:
        cache.clear_cache()

    return {
        "done": result.done,
        "errors": result.errors,
        "details": result.details,
        "dry_run": body.dry_run,
    }
