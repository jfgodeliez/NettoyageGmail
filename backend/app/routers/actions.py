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
    email_decisions = cache.load_email_decisions()

    if not decisions and not email_decisions:
        raise HTTPException(status_code=400, detail="Aucune décision à exécuter")

    groups = cache.load_groups_with_emails()
    groups_by_id = {g.group_id: g for g in groups}

    service = None if body.dry_run else build_gmail_service()

    # Décisions individuelles d'abord
    result = gmail_actions.execute_email_decisions(service, email_decisions, dry_run=body.dry_run)

    # Emails protégés individuellement — exclus des batchs de groupe
    kept_ids = {mid for mid, action in email_decisions.items() if action == "keep"}

    # Décisions de groupe (emails "keep" individuels exclus)
    group_result = gmail_actions.execute_decisions(service, decisions, groups_by_id, dry_run=body.dry_run, kept_ids=kept_ids)
    result.done += group_result.done
    result.errors += group_result.errors
    result.details.extend(group_result.details)
    result.processed_ids.extend(group_result.processed_ids)
    result.processed_group_ids.extend(group_result.processed_group_ids)

    if not body.dry_run:
        all_processed = set(result.processed_ids)
        if email_decisions:
            # Les emails individuels sont inclus dans processed_ids si traités
            cache.clear_email_decisions_for_ids(set(email_decisions.keys()))
        if all_processed:
            cache.remove_emails(all_processed)
        cache.clear_decisions_for_groups(set(result.processed_group_ids))

    return {
        "done": result.done,
        "errors": result.errors,
        "details": result.details,
        "dry_run": body.dry_run,
        "cache_remaining": cache.count_cached_emails(),
    }
