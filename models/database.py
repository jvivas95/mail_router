"""
models/database.py — Inicialización y acceso a SQLite
"""

import sqlite3
from datetime import datetime

DB_FILE = "mailrouter.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            uid           TEXT UNIQUE,
            sender        TEXT,
            subject       TEXT,
            date_received TEXT,
            body          TEXT,
            forwarded_to  TEXT,
            forwarded_at  TEXT,
            status        TEXT DEFAULT 'pending'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS recipients (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT,
            email       TEXT UNIQUE,
            active      INTEGER DEFAULT 1,
            order_index INTEGER DEFAULT 0,
            created_at  TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS rotation_state (
            id            INTEGER PRIMARY KEY DEFAULT 1,
            current_index INTEGER DEFAULT 0,
            last_updated  TEXT
        )
    """)

    c.execute(
        "INSERT OR IGNORE INTO rotation_state (id, current_index, last_updated) VALUES (1, 0, ?)",
        (datetime.now().isoformat(),)
    )

    conn.commit()
    conn.close()


# ── Helpers de consulta ────────────────────────────────────────────────────────

def get_emails(limit: int = 50, offset: int = 0) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM emails ORDER BY date_received DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_email_by_id(eid: int) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM emails WHERE id=?", (eid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats() -> dict:
    conn = get_db()
    stats = {
        "total":     conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0],
        "forwarded": conn.execute("SELECT COUNT(*) FROM emails WHERE status='forwarded'").fetchone()[0],
        "pending":   conn.execute("SELECT COUNT(*) FROM emails WHERE status='pending'").fetchone()[0],
        "errors":    conn.execute("SELECT COUNT(*) FROM emails WHERE status='error'").fetchone()[0],
    }
    conn.close()
    return stats


def get_all_recipients() -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM recipients ORDER BY order_index ASC, id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_recipients() -> list:
    return [r for r in get_all_recipients() if r["active"]]


def add_recipient(name: str, email: str) -> None:
    conn = get_db()
    max_idx = conn.execute("SELECT MAX(order_index) FROM recipients").fetchone()[0] or 0
    conn.execute(
        "INSERT INTO recipients (name, email, active, order_index, created_at) VALUES (?,?,1,?,?)",
        (name, email, max_idx + 1, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def toggle_recipient(rid: int) -> None:
    conn = get_db()
    r = conn.execute("SELECT active FROM recipients WHERE id=?", (rid,)).fetchone()
    if r:
        conn.execute("UPDATE recipients SET active=? WHERE id=?", (0 if r["active"] else 1, rid))
        conn.commit()
    conn.close()


def delete_recipient(rid: int) -> None:
    conn = get_db()
    conn.execute("DELETE FROM recipients WHERE id=?", (rid,))
    conn.commit()
    conn.close()


def get_rotation_state() -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM rotation_state WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else None


def set_rotation_index(idx: int) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE rotation_state SET current_index=?, last_updated=? WHERE id=1",
        (idx, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()