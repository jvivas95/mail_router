"""
services/worker.py — Thread de monitoreo en segundo plano
"""

import threading
import time
from datetime import datetime

from config import load_config
from models.database import get_db
from services.mail_reader import fetch_unseen_emails
from services.mail_sender import get_next_recipient, build_forward_email, send_email

_worker_running = False
_worker_thread: threading.Thread | None = None


def is_running() -> bool:
    return _worker_running


def _forward_pending_emails(conn, cfg: dict) -> int:
    rows = conn.execute(
        """
        SELECT uid, sender, subject, date_received, body, status
        FROM emails
        WHERE status IN ('pending', 'no_recipients', 'error')
        ORDER BY id ASC
        """
    ).fetchall()

    if not rows:
        return 0

    processed = 0

    for row in rows:
        recipient, _ = get_next_recipient()

        if not recipient:
            if row["status"] != "no_recipients":
                conn.execute("UPDATE emails SET status='no_recipients' WHERE uid=?", (row["uid"],))
                conn.commit()
            continue

        original = {
            "sender": row["sender"] or "",
            "subject": row["subject"] or "(sin asunto)",
            "date": row["date_received"] or "",
            "body": row["body"] or "",
        }

        try:
            fwd = build_forward_email(original, recipient, cfg["email_address"])
            send_email(fwd, recipient["email"], cfg)

            conn.execute(
                """
                UPDATE emails
                SET forwarded_to=?, forwarded_at=?, status='forwarded'
                WHERE uid=?
                """,
                (
                    f"{recipient['name']} <{recipient['email']}>",
                    datetime.now().isoformat(),
                    row["uid"],
                ),
            )
            conn.commit()
            processed += 1
            print(f"[Worker] Reenviado '{original['subject']}' → {recipient['name']}")

        except Exception as e:
            print(f"[Worker] Error al reenviar: {e}")
            conn.execute("UPDATE emails SET status='error' WHERE uid=?", (row["uid"],))
            conn.commit()

    return processed


def process_inbox(cfg: dict) -> int:
    """
    Lee correos no vistos, los registra y los reenvía.
    Devuelve el número de correos procesados, o -1 si hay error.
    """
    try:
        emails = fetch_unseen_emails(cfg)
        print(f"[Worker] Correos no leídos encontrados: {len(emails)}")
    except Exception as e:
        print(f"[Worker] Error IMAP: {e}")
        import traceback
        traceback.print_exc()
        return -1

    conn = get_db()

    for em in emails:
        # Evitar duplicados
        existing = conn.execute("SELECT id FROM emails WHERE uid=?", (em["uid"],)).fetchone()
        if existing:
            continue

        # Registrar en DB
        conn.execute("""
            INSERT INTO emails (uid, sender, subject, date_received, body, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (em["uid"], em["sender"], em["subject"], datetime.now().isoformat(), em["body"]))
        conn.commit()

    processed = _forward_pending_emails(conn, cfg)

    conn.close()
    return processed


def _worker_loop():
    global _worker_running
    print("[Worker] Iniciado")
    while _worker_running:
        cfg = load_config()
        if cfg.get("active") and cfg.get("email_address") and cfg.get("email_password"):
            n = process_inbox(cfg)
            if n > 0:
                print(f"[Worker] {n} correo(s) procesado(s)")
            elif n < 0:
                print("[Worker] Fallo de conexión, reintentando en el siguiente ciclo...")

        interval = cfg.get("check_interval", 60)
        for _ in range(interval):
            if not _worker_running:
                break
            time.sleep(1)

    print("[Worker] Detenido")


def start_worker() -> None:
    global _worker_running, _worker_thread
    if not _worker_running:
        _worker_running = True
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
        _worker_thread.start()


def stop_worker() -> None:
    global _worker_running
    _worker_running = False