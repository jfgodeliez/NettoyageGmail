"""Récupération des métadonnées et corps d'emails via l'API Gmail."""

import base64
import os
import time
from dataclasses import dataclass, field

from dotenv import load_dotenv
from googleapiclient.errors import HttpError

load_dotenv()

MAX_EMAILS = int(os.getenv("MAX_EMAILS", "10000"))
BATCH_SIZE = 500


@dataclass
class EmailMeta:
    msg_id: str
    thread_id: str
    sender: str
    sender_domain: str
    subject: str
    date: str
    labels: list[str] = field(default_factory=list)
    is_newsletter: bool = False
    unsubscribe_link: str = ""
    size_estimate: int = 0


def _parse_headers(headers: list[dict]) -> dict:
    return {h["name"].lower(): h["value"] for h in headers}


def _extract_domain(sender: str) -> str:
    if "<" in sender:
        email = sender.split("<")[1].rstrip(">").strip()
    else:
        email = sender.strip()
    return email.split("@")[-1].lower() if "@" in email else sender.lower()


def fetch_all_metadata(service, progress_callback=None) -> list[EmailMeta]:
    """Récupère les métadonnées de tous les emails. progress_callback(current, total)."""
    message_ids: list[dict] = []
    page_token = None

    while True:
        kwargs = {"userId": "me", "maxResults": BATCH_SIZE, "q": "-in:spam -in:trash"}
        if page_token:
            kwargs["pageToken"] = page_token
        try:
            result = service.users().messages().list(**kwargs).execute()
        except HttpError as e:
            raise RuntimeError(f"Erreur API Gmail : {e}") from e

        message_ids.extend(result.get("messages", []))
        if MAX_EMAILS and len(message_ids) >= MAX_EMAILS:
            message_ids = message_ids[:MAX_EMAILS]
            break
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    total = len(message_ids)
    emails: list[EmailMeta] = []

    for chunk_start in range(0, total, 100):
        chunk = message_ids[chunk_start: chunk_start + 100]
        chunk_results: list[EmailMeta] = []

        def callback(request_id, response, exception):  # noqa: ANN001
            if exception:
                return
            headers = _parse_headers(response.get("payload", {}).get("headers", []))
            sender = headers.get("from", "")
            unsubscribe = headers.get("list-unsubscribe", "")
            chunk_results.append(EmailMeta(
                msg_id=response["id"],
                thread_id=response.get("threadId", ""),
                sender=sender,
                sender_domain=_extract_domain(sender),
                subject=headers.get("subject", "(sans objet)"),
                date=headers.get("date", ""),
                labels=response.get("labelIds", []),
                is_newsletter=bool(unsubscribe),
                unsubscribe_link=unsubscribe,
                size_estimate=response.get("sizeEstimate", 0),
            ))

        batch = service.new_batch_http_request(callback=callback)
        for msg in chunk:
            batch.add(service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date", "List-Unsubscribe"],
            ))
        batch.execute()
        time.sleep(0.1)
        emails.extend(chunk_results)

        if progress_callback:
            progress_callback(min(chunk_start + 100, total), total)

    return emails


def fetch_email_body(service, msg_id: str) -> dict:
    """Retourne le corps d'un email : {'content': str, 'mime': 'html'|'text'}."""
    try:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    except HttpError as e:
        raise RuntimeError(f"Erreur récupération email {msg_id}: {e}") from e

    payload = msg.get("payload", {})
    html_body, text_body = _extract_parts(payload)

    if html_body:
        return {"content": html_body, "mime": "html"}
    if text_body:
        return {"content": text_body, "mime": "text"}
    return {"content": "(Aucun contenu disponible)", "mime": "text"}


def _extract_parts(payload: dict) -> tuple[str | None, str | None]:
    """Parcourt récursivement le payload MIME, retourne (html, text)."""
    html_body = None
    text_body = None
    mime = payload.get("mimeType", "")

    if mime == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            html_body = _b64decode(data)
    elif mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            text_body = _b64decode(data)
    elif mime.startswith("multipart/"):
        for part in payload.get("parts", []):
            h, t = _extract_parts(part)
            if h:
                html_body = h
            if t and not text_body:
                text_body = t

    return html_body, text_body


def _b64decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
