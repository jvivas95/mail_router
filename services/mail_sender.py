# services/mail_sender.py - Reenvío de mails vía SMTP y gestión de rotación

import smtplib # Libreria para enviar correos
import mimetypes # Libreria para detectar el tipo MIME de los archivos adjuntos

from email.mime.multipart import MIMEMultipart # Libreria para crear correos con múltiples partes (texto, HTML, archivos adjuntos)
from email.mime.text import MIMEText # Libreria para crear el contenido del correo
from email.mime.base import MIMEBase # Libreria para manejar archivos adjuntos
from email.mime.application import MIMEApplication # Libreria para manejar archivos adjuntos de tipo aplicación (como PDFs, Word, etc.)
from email.mime.image import MIMEImage # Libreria para manejar archivos adjuntos de tipo imagen
from email.mime.audio import MIMEAudio # Libreria para manejar archivos adjuntos de tipo audio
from email.utils import encode_rfc2231 # Libreria para codificar nombres de archivos adjuntos con caracteres especiales
from email import encoders # Libreria para codificar archivos adjuntos
from datetime import datetime # Libreria para manejar fechas y horas
from models.database import (
    get_db,
    get_active_recipients,
    get_rotation_state,
    set_rotation_state
    )

def get_next_recipient():
    """Devuelve el siguiente destinatario en la rotación y avanza el índice para la próxima vez."""
    
    recipients = get_active_recipients() # Obtener la lista de destinatarios activos desde la base de datos
    
    # Si no hay destinatarios activos, devolver None y un índice inválido
    if not recipients:
        return None, -1
    
    # conn = get_db() # Obtener la conexión a la base de datos
    # state = conn.execute(
    #     'SELECT current_index FROM rotation_state WHERE id = 1'
    # ).fetchone() # Obtener el índice actual de rotación
    
    state = get_rotation_state() # Obtener el estado de rotación actual desde la base de datos
    
    # Si el índice supera el número de agentes, reiniciar a 0
    idx = state['current_index'] if state else 0 # Si no hay estado, iniciar en 0
    
    if idx >= len(recipients): # Si el índice es mayor o igual al número de destinatarios, reiniciar a 0
        idx = 0
    
    recipient = recipients[idx] # Obtener el destinatario actual según el índice
    next_idx = (idx + 1) % len(recipients) # Calcular el siguiente índice de rotación
    
    set_rotation_state(next_idx) # Persistir el índice para que la rotación avance en próximos envíos

    return recipient, idx # Devolver el destinatario actual y el índice utilizado para esta rotación
    
    # # Guardar el nuevo índice en la base de datos
    # conn.execute(
    #     'UPDATE rotation_state SET current_index = ?, last_updated = ? WHERE id=1',
    #     (next_idx, datetime.now().isoformat())
    # )
    # conn.commit() # Guardar los cambios en la base de datos
    # conn.close() # Cerrar la conexión a la base de datos
    
    # return recipient, idx # Devolver el destinatario actual y el índice utilizado para esta rotación


def build_forward_email(original: dict, recipient: dict, from_address: str) -> MIMEMultipart:
    import copy

    # print (f"[DEBUG] Claves en original: {list(original.keys())}")

    # Clonar el mensaje original completo — adjuntos incluidos
    raw = original["raw_msg"]
    # fwd = copy.deepcopy(raw)
    
    # Si tenemos el mensaje original, lo clonamos directamente (preservar adjuntos)
    if raw is not None:
        fwd = copy.deepcopy(raw)
        del fwd["From"]
        del fwd["To"]
        del fwd["Cc"]
        del fwd["Bcc"]
        del fwd["Subject"]
        del fwd["Message-ID"]
        del fwd["Reply-To"]
        fwd["From"]    = from_address
        fwd["To"]      = recipient["email"]
        fwd["Subject"] = f"Fwd: {original['subject']}"
        
        return fwd

    # Fallback: construir desde texto (correos sin raw_msg — desde DB)
    fwd = MIMEMultipart("alternative")
    fwd["Subject"] = f"Fwd: {original['subject']}"
    fwd["From"]    = from_address
    fwd["To"]      = recipient["email"]

    text = (
        f"--- MENSAJE REENVIADO ---\n"
        f"De: {original['sender']}\n"
        f"Asunto: {original['subject']}\n\n"
        f"{original['body']}\n\n"
        f"---\nAsignado a: {recipient['name']}"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif; max-width:680px;">
        <p style="color:#888; font-size:12px;">📨 Reenviado desde <strong>{from_address}</strong></p>
        <hr>
        <p><strong>De:</strong> {original['sender']}</p>
        <p><strong>Asunto:</strong> {original['subject']}</p>
        <hr>
        <div style="white-space:pre-wrap;">{original['body']}</div>
        <p style="color:#888; font-size:11px;">Asignado a: {recipient['name']}</p>
    </div>
    """
    fwd.attach(MIMEText(text, "plain", "utf-8"))
    fwd.attach(MIMEText(html, "html", "utf-8"))
    return fwd


def send_email(fwd_msg: MIMEMultipart, recipient_email: str, cfg: dict) -> None:
    """
        Función para enviar el mail por SMTP con autenticación TLS.
    """
    with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port']) as server: # Conexión al servidor SMTP
        server.starttls() # Iniciar TLS para seguridad
        server.login(cfg['email_address'], cfg['email_password']) # Autenticación con el servidor SMTP
        server.sendmail(cfg['email_address'], recipient_email, fwd_msg.as_bytes())