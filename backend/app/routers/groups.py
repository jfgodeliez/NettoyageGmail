"""Routes groupes : /api/groups."""

import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..auth_web import build_gmail_service, is_authenticated
from .. import cache, analyzer, gmail_client

router = APIRouter(prefix="/api/groups", tags=["groups"])

# État du chargement en cours (simple, mono-utilisateur)
_fetch_state: dict[str, Any] = {"running": False, "progress": 0, "total": 0, "error": None}


def _require_auth():
    if not is_authenticated():
        raise HTTPException(status_code=401, detail="Non authentifié")


@router.get("")
def get_groups(refresh: bool = False, _=Depends(_require_auth)):
    """Retourne la liste des groupes (depuis cache ou en déclenchant un fetch)."""
    if refresh:
        cache.clear_cache()

    if cache.cache_has_groups():
        groups = cache.load_groups_with_emails()
        decisions = cache.load_decisions()
        return _serialize_groups(groups, decisions)

    # Pas de cache : retourner l'état du fetch en cours
    if _fetch_state["running"]:
        return {"fetching": True, "progress": _fetch_state["progress"], "total": _fetch_state["total"]}

    return {"fetching": False, "ready": False}


@router.post("/fetch")
def trigger_fetch(background_tasks: BackgroundTasks, _=Depends(_require_auth)):
    """Lance le chargement des emails en tâche de fond."""
    if _fetch_state["running"]:
        return {"ok": True, "message": "Déjà en cours"}
    background_tasks.add_task(_do_fetch)
    return {"ok": True}


@router.get("/fetch-status")
def fetch_status(_=Depends(_require_auth)):
    return {
        "running": _fetch_state["running"],
        "progress": _fetch_state["progress"],
        "total": _fetch_state["total"],
        "error": _fetch_state["error"],
        "ready": cache.cache_has_groups(),
    }


@router.get("/{group_id}/emails")
def get_group_emails(group_id: int, page: int = 1, per_page: int = 50, _=Depends(_require_auth)):
    groups = cache.load_groups_with_emails()
    group = next((g for g in groups if g.group_id == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail="Groupe introuvable")

    start = (page - 1) * per_page
    end = start + per_page
    emails_page = group.emails[start:end]
    decisions = cache.load_decisions()

    return {
        "group_id": group.group_id,
        "theme": group.theme,
        "category": group.category,
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
                "count": g.count,
                "size_mb": round(g.size_mb, 1),
                "sample_senders": g.sample_senders,
                "decision": decisions.get(g.group_id),
            }
            for g in groups
        ],
    }
