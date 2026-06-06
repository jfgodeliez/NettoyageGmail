"""Routes groupes : /api/groups."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from ..auth_web import build_gmail_service
from ..session import require_session
from .. import cache, analyzer, gmail_client

router = APIRouter(prefix="/api/groups", tags=["groups"])

_fetch_state: dict[str, Any] = {"running": False, "progress": 0, "total": 0, "error": None}


class CreateGroupRequest(BaseModel):
    theme: str
    category: str = "autre"


@router.get("")
def get_groups(refresh: bool = False, _=Depends(require_session)):
    if refresh:
        cache.clear_cache()

    if cache.cache_has_groups():
        groups = cache.load_groups_with_emails()
        decisions = cache.load_decisions()
        return _serialize_groups(groups, decisions)

    if _fetch_state["running"]:
        return {"fetching": True, "progress": _fetch_state["progress"], "total": _fetch_state["total"]}

    return {"fetching": False, "ready": False}


@router.post("")
def create_group(body: CreateGroupRequest, _=Depends(require_session)):
    """Crée un groupe custom persistant."""
    if not body.theme.strip():
        raise HTTPException(status_code=400, detail="Le nom du groupe est requis")
    group_id = cache.create_custom_group(body.theme.strip(), body.category)
    return {"group_id": group_id, "theme": body.theme.strip(), "category": body.category}


@router.delete("/{group_id}")
def delete_group(group_id: int, _=Depends(require_session)):
    """Supprime un groupe custom (les emails retournent à leur classification d'origine)."""
    ok = cache.delete_custom_group(group_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Seuls les groupes custom peuvent être supprimés")
    return {"ok": True}


@router.get("/list")
def list_groups_simple(_=Depends(require_session)):
    """Liste id + thème de tous les groupes (pour le sélecteur de déplacement)."""
    return cache.get_group_list()


@router.post("/fetch")
def trigger_fetch(background_tasks: BackgroundTasks, _=Depends(require_session)):
    if _fetch_state["running"]:
        return {"ok": True, "message": "Déjà en cours"}
    background_tasks.add_task(_do_fetch)
    return {"ok": True}


@router.get("/fetch-status")
def fetch_status(_=Depends(require_session)):
    return {
        "running": _fetch_state["running"],
        "progress": _fetch_state["progress"],
        "total": _fetch_state["total"],
        "error": _fetch_state["error"],
        "ready": cache.cache_has_groups(),
    }


@router.get("/{group_id}/emails")
def get_group_emails(group_id: int, page: int = 1, per_page: int = 50, _=Depends(require_session)):
    groups = cache.load_groups_with_emails()
    group = next((g for g in groups if g.group_id == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail="Groupe introuvable")

    start = (page - 1) * per_page
    emails_page = group.emails[start: start + per_page]
    decisions = cache.load_decisions()

    return {
        "group_id": group.group_id,
        "theme": group.theme,
        "category": group.category,
        "is_custom": group.is_custom,
        "total": group.count,
        "page": page,
        "per_page": per_page,
        "decision": decisions.get(group_id),
        "emails": [
            {
                "msg_id": e.msg_id,
                "sender": e.sender,
                "sender_domain": e.sender_domain,
                "subject": e.subject,
                "date": e.date,
                "is_newsletter": e.is_newsletter,
                "size_kb": e.size_estimate // 1024,
                "overridden": cache.get_email_override(e.msg_id) is not None,
            }
            for e in emails_page
        ],
    }


def _do_fetch():
    _fetch_state["running"] = True
    _fetch_state["error"] = None
    _fetch_state["progress"] = 0
    _fetch_state["total"] = 0
    try:
        cache.init_db()
        service = build_gmail_service()

        def on_progress(current, total):
            _fetch_state["progress"] = current
            _fetch_state["total"] = total

        emails = gmail_client.fetch_all_metadata(service, progress_callback=on_progress)
        cache.save_emails(emails)
        groups = analyzer.analyze(emails)
        groups = analyzer.merge_small_groups(groups)
        cache.save_groups(groups)
    except Exception as e:
        _fetch_state["error"] = str(e)
    finally:
        _fetch_state["running"] = False


def _serialize_groups(groups, decisions: dict[int, str]) -> dict:
    return {
        "ready": True,
        "groups": [
            {
                "group_id": g.group_id,
                "theme": g.theme,
                "category": g.category,
                "is_custom": g.is_custom,
                "count": g.count,
                "size_mb": round(g.size_mb, 1),
                "sample_senders": g.sample_senders,
                "decision": decisions.get(g.group_id),
            }
            for g in groups
        ],
    }
