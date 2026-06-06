"""Persistance SQLite : emails, groupes, décisions."""

import json
import os
import sqlite3
from contextlib import contextmanager

from dotenv import load_dotenv

from .gmail_client import EmailMeta
from .analyzer import EmailGroup

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "/data/gmail_cache.db")

DDL = """
CREATE TABLE IF NOT EXISTS emails (
    msg_id          TEXT PRIMARY KEY,
    thread_id       TEXT,
    sender          TEXT,
    sender_domain   TEXT,
    subject         TEXT,
    date            TEXT,
    labels          TEXT,
    is_newsletter   INTEGER,
    unsubscribe_link TEXT,
    size_estimate   INTEGER
);
CREATE TABLE IF NOT EXISTS groups (
    group_id    INTEGER PRIMARY KEY,
    theme       TEXT UNIQUE,
    category    TEXT,
    sample_senders TEXT,
    email_ids   TEXT
);
CREATE TABLE IF NOT EXISTS decisions (
    group_id    INTEGER PRIMARY KEY,
    action      TEXT   -- 'keep' | 'trash' | 'archive'
);
"""


@contextmanager
def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript(DDL)


def save_emails(emails: list[EmailMeta]) -> None:
    rows = [(e.msg_id, e.thread_id, e.sender, e.sender_domain, e.subject,
             e.date, json.dumps(e.labels), int(e.is_newsletter),
             e.unsubscribe_link, e.size_estimate) for e in emails]
    with _conn() as con:
        con.executemany(
            "INSERT OR REPLACE INTO emails VALUES (?,?,?,?,?,?,?,?,?,?)", rows
        )


def save_groups(groups: list[EmailGroup]) -> None:
    with _conn() as con:
        con.execute("DELETE FROM groups")
        con.executemany(
            "INSERT INTO groups VALUES (?,?,?,?,?)",
            [(g.group_id, g.theme, g.category,
              json.dumps(g.sample_senders), json.dumps(g.ids)) for g in groups],
        )


def load_emails() -> list[EmailMeta]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM emails").fetchall()
    return [EmailMeta(
        msg_id=r["msg_id"], thread_id=r["thread_id"],
        sender=r["sender"], sender_domain=r["sender_domain"],
        subject=r["subject"], date=r["date"],
        labels=json.loads(r["labels"]),
        is_newsletter=bool(r["is_newsletter"]),
        unsubscribe_link=r["unsubscribe_link"],
        size_estimate=r["size_estimate"],
    ) for r in rows]


def load_groups_with_emails() -> list[EmailGroup]:
    """Charge les groupes avec leurs emails depuis la DB."""
    with _conn() as con:
        group_rows = con.execute("SELECT * FROM groups ORDER BY group_id").fetchall()
        email_rows = con.execute("SELECT * FROM emails").fetchall()

    email_by_id: dict[str, EmailMeta] = {}
    for r in email_rows:
        email_by_id[r["msg_id"]] = EmailMeta(
            msg_id=r["msg_id"], thread_id=r["thread_id"],
            sender=r["sender"], sender_domain=r["sender_domain"],
            subject=r["subject"], date=r["date"],
            labels=json.loads(r["labels"]),
            is_newsletter=bool(r["is_newsletter"]),
            unsubscribe_link=r["unsubscribe_link"],
            size_estimate=r["size_estimate"],
        )

    groups = []
    for r in group_rows:
        ids = json.loads(r["email_ids"])
        mails = [email_by_id[i] for i in ids if i in email_by_id]
        groups.append(EmailGroup(
            group_id=r["group_id"],
            theme=r["theme"],
            category=r["category"],
            emails=mails,
            sample_senders=json.loads(r["sample_senders"]),
        ))
    return groups


def cache_has_emails() -> bool:
    if not os.path.exists(DB_PATH):
        return False
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM emails").fetchone()[0] > 0


def cache_has_groups() -> bool:
    if not os.path.exists(DB_PATH):
        return False
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM groups").fetchone()[0] > 0


def save_decision(group_id: int, action: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO decisions (group_id, action) VALUES (?,?)",
            (group_id, action),
        )


def load_decisions() -> dict[int, str]:
    with _conn() as con:
        rows = con.execute("SELECT group_id, action FROM decisions").fetchall()
    return {r["group_id"]: r["action"] for r in rows}


def clear_decisions() -> None:
    with _conn() as con:
        con.execute("DELETE FROM decisions")


def clear_cache() -> None:
    with _conn() as con:
        con.execute("DELETE FROM emails")
        con.execute("DELETE FROM groups")
        con.execute("DELETE FROM decisions")
