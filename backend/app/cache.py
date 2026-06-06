"""Persistance SQLite : emails, groupes, décisions, overrides."""

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
    group_id      INTEGER PRIMARY KEY,
    theme         TEXT UNIQUE,
    category      TEXT,
    sample_senders TEXT,
    email_ids     TEXT,
    is_custom     INTEGER DEFAULT 0,
    is_persistent INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS decisions (
    group_id    INTEGER PRIMARY KEY,
    action      TEXT
);
CREATE TABLE IF NOT EXISTS email_overrides (
    msg_id      TEXT PRIMARY KEY,
    group_id    INTEGER,
    FOREIGN KEY (group_id) REFERENCES groups(group_id)
);
CREATE TABLE IF NOT EXISTS email_decisions (
    msg_id  TEXT PRIMARY KEY,
    action  TEXT
);
"""

_MIGRATIONS = [
    "ALTER TABLE groups ADD COLUMN is_custom INTEGER DEFAULT 0",
    "ALTER TABLE groups ADD COLUMN is_persistent INTEGER DEFAULT 0",
]


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
        # Migrations pour les DB existantes
        for sql in _MIGRATIONS:
            try:
                con.execute(sql)
            except sqlite3.OperationalError:
                pass  # colonne déjà présente


# ── Emails ────────────────────────────────────────────────────────────────────

def save_emails(emails: list[EmailMeta]) -> None:
    rows = [(e.msg_id, e.thread_id, e.sender, e.sender_domain, e.subject,
             e.date, json.dumps(e.labels), int(e.is_newsletter),
             e.unsubscribe_link, e.size_estimate) for e in emails]
    with _conn() as con:
        con.executemany(
            "INSERT OR REPLACE INTO emails VALUES (?,?,?,?,?,?,?,?,?,?)", rows
        )


def load_emails() -> list[EmailMeta]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM emails").fetchall()
    return [_row_to_email(r) for r in rows]


# ── Groupes ───────────────────────────────────────────────────────────────────

def save_groups(groups: list[EmailGroup]) -> None:
    """Sauvegarde les groupes auto-générés en préservant les groupes custom."""
    with _conn() as con:
        con.execute("DELETE FROM groups WHERE is_custom = 0")
        con.executemany(
            "INSERT OR REPLACE INTO groups (group_id, theme, category, sample_senders, email_ids, is_custom, is_persistent) VALUES (?,?,?,?,?,0,0)",
            [(g.group_id, g.theme, g.category,
              json.dumps(g.sample_senders), json.dumps(g.ids)) for g in groups],
        )


def create_custom_group(theme: str, category: str = "autre") -> int:
    """Crée un groupe manuel persistant. Retourne le group_id."""
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO groups (theme, category, sample_senders, email_ids, is_custom, is_persistent) VALUES (?,?,?,?,1,1)",
            (theme, category, json.dumps([]), json.dumps([])),
        )
        return cur.lastrowid


def delete_custom_group(group_id: int) -> bool:
    """Supprime un groupe custom et remet ses emails dans leur groupe d'origine."""
    with _conn() as con:
        row = con.execute("SELECT is_custom FROM groups WHERE group_id=?", (group_id,)).fetchone()
        if not row or not row["is_custom"]:
            return False
        con.execute("DELETE FROM email_overrides WHERE group_id=?", (group_id,))
        con.execute("DELETE FROM groups WHERE group_id=?", (group_id,))
        con.execute("DELETE FROM decisions WHERE group_id=?", (group_id,))
    return True


def load_groups_with_emails() -> list[EmailGroup]:
    """Charge les groupes avec leurs emails, en appliquant les overrides individuels."""
    with _conn() as con:
        group_rows = con.execute("SELECT * FROM groups ORDER BY is_custom ASC, group_id ASC").fetchall()
        email_rows = con.execute("SELECT * FROM emails").fetchall()
        override_rows = con.execute("SELECT msg_id, group_id FROM email_overrides").fetchall()

    email_by_id: dict[str, EmailMeta] = {r["msg_id"]: _row_to_email(r) for r in email_rows}
    # msg_id → group_id cible (override)
    overrides: dict[str, int] = {r["msg_id"]: r["group_id"] for r in override_rows}

    # Construire les listes d'emails par groupe en appliquant les overrides
    group_emails: dict[int, list[EmailMeta]] = {r["group_id"]: [] for r in group_rows}

    for r in group_rows:
        base_ids = json.loads(r["email_ids"])
        for mid in base_ids:
            if mid not in email_by_id:
                continue
            target_gid = overrides.get(mid, r["group_id"])
            if target_gid in group_emails:
                group_emails[target_gid].append(email_by_id[mid])

    # Emails overridés vers des groupes custom (pas dans leur liste de base)
    for mid, gid in overrides.items():
        if mid in email_by_id and gid in group_emails:
            email = email_by_id[mid]
            if email not in group_emails[gid]:
                group_emails[gid].append(email)

    groups = []
    for r in group_rows:
        mails = group_emails.get(r["group_id"], [])
        groups.append(EmailGroup(
            group_id=r["group_id"],
            theme=r["theme"],
            category=r["category"],
            emails=mails,
            sample_senders=json.loads(r["sample_senders"]),
            is_custom=bool(r["is_custom"]),
        ))
    return groups


def get_group_list() -> list[dict]:
    """Retourne id + thème de tous les groupes (pour le sélecteur de déplacement)."""
    with _conn() as con:
        rows = con.execute("SELECT group_id, theme, category, is_custom FROM groups ORDER BY theme").fetchall()
    return [{"group_id": r["group_id"], "theme": r["theme"],
             "category": r["category"], "is_custom": bool(r["is_custom"])} for r in rows]


# ── Overrides individuels ─────────────────────────────────────────────────────

def move_email(msg_id: str, target_group_id: int) -> None:
    """Déplace un email vers un autre groupe (override persistant)."""
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO email_overrides (msg_id, group_id) VALUES (?,?)",
            (msg_id, target_group_id),
        )


def reset_email_override(msg_id: str) -> None:
    """Remet un email dans son groupe d'origine (supprime l'override)."""
    with _conn() as con:
        con.execute("DELETE FROM email_overrides WHERE msg_id=?", (msg_id,))


def get_email_override(msg_id: str) -> int | None:
    with _conn() as con:
        row = con.execute("SELECT group_id FROM email_overrides WHERE msg_id=?", (msg_id,)).fetchone()
    return row["group_id"] if row else None


# ── Décisions ─────────────────────────────────────────────────────────────────

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


# ── État du cache ─────────────────────────────────────────────────────────────

def count_cached_emails() -> int:
    if not os.path.exists(DB_PATH):
        return 0
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM emails").fetchone()[0]


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


def remove_emails(msg_ids: set[str]) -> None:
    """Retire les emails traités du cache et met à jour les groupes en conséquence.

    Les groupes auto qui deviennent vides sont supprimés.
    Les groupes custom vides sont conservés.
    """
    if not msg_ids:
        return
    from collections import Counter
    ids_list = list(msg_ids)
    placeholders = ",".join("?" * len(ids_list))

    with _conn() as con:
        con.execute(f"DELETE FROM emails WHERE msg_id IN ({placeholders})", ids_list)
        con.execute(f"DELETE FROM email_overrides WHERE msg_id IN ({placeholders})", ids_list)
        con.execute(f"DELETE FROM email_decisions WHERE msg_id IN ({placeholders})", ids_list)

        # Index domaine des emails restants pour recalculer sample_senders
        remaining = {
            r["msg_id"]: r["sender_domain"]
            for r in con.execute("SELECT msg_id, sender_domain FROM emails").fetchall()
        }

        for row in con.execute("SELECT group_id, email_ids, is_custom FROM groups").fetchall():
            old_ids: list[str] = json.loads(row["email_ids"])
            new_ids = [mid for mid in old_ids if mid not in msg_ids]

            if not new_ids and not row["is_custom"]:
                con.execute("DELETE FROM groups WHERE group_id=?", (row["group_id"],))
                con.execute("DELETE FROM decisions WHERE group_id=?", (row["group_id"],))
            else:
                top_senders = [
                    d for d, _ in Counter(
                        remaining[mid] for mid in new_ids if mid in remaining
                    ).most_common(3)
                ]
                con.execute(
                    "UPDATE groups SET email_ids=?, sample_senders=? WHERE group_id=?",
                    (json.dumps(new_ids), json.dumps(top_senders), row["group_id"]),
                )


# ── Décisions individuelles d'emails ─────────────────────────────────────────

def set_email_decision(msg_id: str, action: str) -> None:
    with _conn() as con:
        con.execute("INSERT OR REPLACE INTO email_decisions (msg_id, action) VALUES (?,?)", (msg_id, action))


def delete_email_decision(msg_id: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM email_decisions WHERE msg_id=?", (msg_id,))


def load_email_decisions() -> dict[str, str]:
    with _conn() as con:
        rows = con.execute("SELECT msg_id, action FROM email_decisions").fetchall()
    return {r["msg_id"]: r["action"] for r in rows}


def get_email_decision(msg_id: str) -> str | None:
    with _conn() as con:
        row = con.execute("SELECT action FROM email_decisions WHERE msg_id=?", (msg_id,)).fetchone()
    return row["action"] if row else None


def count_email_decisions() -> int:
    if not os.path.exists(DB_PATH):
        return 0
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM email_decisions").fetchone()[0]


def clear_email_decisions_for_ids(msg_ids: set[str]) -> None:
    if not msg_ids:
        return
    placeholders = ",".join("?" * len(msg_ids))
    with _conn() as con:
        con.execute(f"DELETE FROM email_decisions WHERE msg_id IN ({placeholders})", list(msg_ids))


def clear_decisions_for_groups(group_ids: set[int]) -> None:
    """Efface les décisions pour les groupes dont l'action a été exécutée."""
    if not group_ids:
        return
    placeholders = ",".join("?" * len(group_ids))
    with _conn() as con:
        con.execute(f"DELETE FROM decisions WHERE group_id IN ({placeholders})", list(group_ids))


def clear_cache() -> None:
    """Supprime emails et groupes auto mais préserve groupes custom et overrides."""
    with _conn() as con:
        con.execute("DELETE FROM emails")
        con.execute("DELETE FROM groups WHERE is_custom = 0")
        con.execute("DELETE FROM decisions")
        con.execute("DELETE FROM email_decisions")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_email(r) -> EmailMeta:
    return EmailMeta(
        msg_id=r["msg_id"], thread_id=r["thread_id"],
        sender=r["sender"], sender_domain=r["sender_domain"],
        subject=r["subject"], date=r["date"],
        labels=json.loads(r["labels"]),
        is_newsletter=bool(r["is_newsletter"]),
        unsubscribe_link=r["unsubscribe_link"],
        size_estimate=r["size_estimate"],
    )
