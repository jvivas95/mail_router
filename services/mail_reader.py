"""
services/mail_reader.py — Lectura de correos vía IMAP
"""

import imaplib
import email
import email.message
from email.header import decode_header


def decode_str(s: str | None) -> str:
    if s is None:
        return ""
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def safe_decode(payload: bytes, charset: str) -> str:
    """Decodifica bytes con fallback progresivo ante encodings desconocidos."""
    charset = (charset or "utf-8").lower().strip()
    for enc in [charset, "utf-8", "latin-1", "cp1252"]:
        try:
            return payload.decode(enc, errors="replace")
        except (LookupError, UnicodeDecodeError):
            continue
    return payload.decode("latin-1", errors="replace")


def get_body(msg: email.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = safe_decode(payload, part.get_content_charset() or "utf-8")
                        break
                except Exception:
                    pass
        # fallback a HTML si no hay texto plano
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = safe_decode(payload, part.get_content_charset() or "utf-8")
                            break
                    except Exception:
                        pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = safe_decode(payload, msg.get_content_charset() or "utf-8")
        except Exception:
            body = ""

    return body[:5000]


def fetch_unseen_emails(cfg: dict) -> list[dict]:
    """
    Conecta via IMAP y devuelve lista de correos no leídos.
    Cada correo es un dict con: uid, sender, subject, date, body, raw_msg
    """
    mail = imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"])
    mail.login(cfg["email_address"], cfg["email_password"])
    mail.select("INBOX")

    _, search_data = mail.search(None, "UNSEEN")
    uids = search_data[0].split()

    results = []
    for uid_bytes in uids:
        uid = uid_bytes.decode()
        try:
            _, msg_data = mail.fetch(uid_bytes, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            results.append({
                "uid":     uid,
                "sender":  decode_str(msg.get("From", "")),
                "subject": decode_str(msg.get("Subject", "(sin asunto)")),
                "date":    decode_str(msg.get("Date", "")),
                "body":    get_body(msg),
                "raw_msg": msg,
            })
        except Exception as e:
            print(f"[Reader] Error procesando UID {uid}: {e}")
            continue

    mail.logout()
    return results