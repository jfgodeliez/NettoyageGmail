"""Exécution des actions Gmail (suppression, archivage)."""

import time
from dataclasses import dataclass, field

from googleapiclient.errors import HttpError

BATCH_CHUNK = 1000


@dataclass
class ActionResult:
    done: int = 0
    errors: int = 0
    details: list[str] = field(default_factory=list)
    processed_ids: list[str] = field(default_factory=list)
    processed_group_ids: list[int] = field(default_factory=list)


def execute_email_decisions(
    service,
    email_decisions: dict[str, str],
    dry_run: bool = False,
) -> ActionResult:
    """Exécute les décisions de suppression/archivage individuelles par email."""
    result = ActionResult()
    trash_ids = [mid for mid, action in email_decisions.items() if action == "trash"]
    archive_ids = [mid for mid, action in email_decisions.items() if action == "archive"]

    if trash_ids:
        if dry_run:
            result.done += len(trash_ids)
            result.details.append(f"[dry-run] trash → {len(trash_ids)} email(s) individuel(s)")
        else:
            r = _batch_modify(service, trash_ids, add_labels=["TRASH"], remove_labels=["INBOX"])
            result.done += r.done
            result.errors += r.errors
            result.processed_ids.extend(trash_ids)
            result.details.append(f"trash → {r.done} email(s) individuel(s) ({r.errors} erreur(s))")

    if archive_ids:
        if dry_run:
            result.done += len(archive_ids)
            result.details.append(f"[dry-run] archive → {len(archive_ids)} email(s) individuel(s)")
        else:
            r = _batch_modify(service, archive_ids, add_labels=[], remove_labels=["INBOX"])
            result.done += r.done
            result.errors += r.errors
            result.processed_ids.extend(archive_ids)
            result.details.append(f"archive → {r.done} email(s) individuel(s) ({r.errors} erreur(s))")

    return result


def execute_decisions(
    service,
    decisions: dict[int, str],
    groups_by_id: dict[int, "EmailGroup"],  # noqa: F821
    dry_run: bool = False,
) -> ActionResult:
    result = ActionResult()
    for group_id, action in decisions.items():
        if action == "keep":
            result.processed_group_ids.append(group_id)
            continue
        group = groups_by_id.get(group_id)
        if not group:
            continue
        if dry_run:
            result.done += group.count
            result.details.append(f"[dry-run] {action} → {group.theme} ({group.count} emails)")
            continue

        ids = group.ids
        if action == "trash":
            r = _batch_modify(service, ids, add_labels=["TRASH"], remove_labels=["INBOX"])
        elif action == "archive":
            r = _batch_modify(service, ids, add_labels=[], remove_labels=["INBOX"])
        else:
            continue

        result.done += r.done
        result.errors += r.errors
        result.details.append(f"{action} → {group.theme} ({r.done} ok, {r.errors} erreurs)")
        # Collecter les IDs traités pour la mise à jour du cache
        result.processed_ids.extend(ids)
        result.processed_group_ids.append(group_id)

    return result


def _batch_modify(service, ids: list[str], add_labels: list[str], remove_labels: list[str]) -> ActionResult:
    result = ActionResult()
    for start in range(0, len(ids), BATCH_CHUNK):
        chunk = ids[start: start + BATCH_CHUNK]
        try:
            body: dict = {"ids": chunk}
            if add_labels:
                body["addLabelIds"] = add_labels
            if remove_labels:
                body["removeLabelIds"] = remove_labels
            service.users().messages().batchModify(userId="me", body=body).execute()
            result.done += len(chunk)
        except HttpError as e:
            result.errors += len(chunk)
            result.details.append(f"Erreur batchModify : {e}")
        time.sleep(0.2)
    return result
