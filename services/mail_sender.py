"""
services/mail_sender.py — Reenvío de correos vía SMTP y gestión de rotación
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from models.database import (
    get_db, get_active_recipients, get_rotation_state,
    set_rotation_index
)


def get_next_recipient() -> tuple[dict | None, int]:
    """
    Devuelve el siguiente destinatario en la rotación y su índice.
    Avanza el puntero de rotación en la base de datos.
    """
    recipients = get_active_recipients()
    if not recipients:
        return None, -1

    state = get_rotation_state()
    idx = state["current_index"] if state else 0

    if idx >= len(recipients):
        idx = 0

    recipient = recipients[idx]
    next_idx = (idx + 1) % len(recipients)
    set_rotation_index(next_idx)

    return recipient, idx


def build_forward_email(original: dict, recipient: dict, from_address: str) -> MIMEMultipart:
    """
    Construye el mensaje de reenvío en formato HTML + texto plano.
    """
    fwd = MIMEMultipart("alternative")
    fwd["Subject"] = f"Fwd: {original['subject']}"
    fwd["From"]    = from_address
    fwd["To"]      = recipient["email"]

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 680px; margin: 0 auto;">
      <div style="background: #1a1a2e; color: #e0e0e0; padding: 16px 24px; border-radius: 8px 8px 0 0;">
        <p style="margin:0; font-size:13px; color:#7c83fd;">
          📨 Mensaje reenviado desde <strong>{from_address}</strong>
        </p>
      </div>
      <div style="border:1px solid #e0e0e0; border-top:none; padding:24px; border-radius:0 0 8px 8px;">
        <table style="width:100%; font-size:13px; color:#555; margin-bottom:16px;">
          <tr><td style="font-weight:600; width:80px; padding:4px 0;">De:</td><td>{original['sender']}</td></tr>
          <tr><td style="font-weight:600; padding:4px 0;">Asunto:</td><td>{original['subject']}</td></tr>
          <tr><td style="font-weight:600; padding:4px 0;">Fecha:</td><td>{original['date']}</td></tr>
        </table>
        <hr style="border:none; border-top:1px solid #eee; margin:16px 0;">
        <div style="white-space:pre-wrap; color:#222; line-height:1.6;">{original['body']}</div>
      </div>
      <p style="text-align:center; font-size:11px; color:#aaa; margin-top:12px;">
        Asignado a: <strong>{recipient['name']}</strong> — MailRouter Sistema Automático
      </p>
    </div>
    """

    text = (
        f"--- MENSAJE REENVIADO ---\n"
        f"De: {original['sender']}\n"
        f"Asunto: {original['subject']}\n"
        f"Fecha: {original['date']}\n\n"
        f"{original['body']}\n\n"
        f"---\nAsignado a: {recipient['name']}"
    )

    fwd.attach(MIMEText(text, "plain"))
    fwd.attach(MIMEText(html, "html"))
    return fwd


def send_email(fwd_msg: MIMEMultipart, recipient_email: str, cfg: dict) -> None:
    """
    Envía el mensaje construido vía SMTP con TLS.
    """
    with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
        server.starttls()
        server.login(cfg["email_address"], cfg["email_password"])
        server.sendmail(cfg["email_address"], recipient_email, fwd_msg.as_string())