# services/mail_sender.py - Reenvío de mails vía SMTP y gestión de rotación

import smtplib # Libreria para enviar correos

from email.mime.multipart import MIMEMultipart # Libreria para crear correos con múltiples partes (texto, HTML, archivos adjuntos)
from email.mime.text import MIMEText # Libreria para crear el contenido del correo
from email.mime.base import MIMEBase # Libreria para manejar archivos adjuntos
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
    """
        Construye el mensaje de reenvío en formato HTML + texto plano.
    """
    
    fwd = MIMEMultipart('mixed') # Crear un mensaje multipart para texto y HTML. Uso de 'mixed' para indicar que el correo tiene varias partes (texto, HTML, adjuntos)
    fwd['Subject'] = f"Fwd: {original['subject']}" # Asunto del correo, prefijado con "Fwd:" para indicar que es un reenvío
    fwd['From'] = from_address # Dirección del remitente (nuestra dirección de correo)
    fwd['To'] = recipient['email'] # Dirección del destinatario (el agente al que se le asigna el correo)
    
    body_part = MIMEMultipart('alternative') # Crear una parte alternativa para texto y HTML (permite que el cliente de correo elija cuál mostrar)
    
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
        f"--- ASIGNADO A: {recipient['name']} ---\n"
        f"MailRouter Sistema Automático"
    )
    
    fwd.attach(MIMEText(text, "plain")) # Adjuntar la parte de texto plano al mensaje multipart
    fwd.attach(MIMEText(html, "html")) # Adjuntar la parte HTML al mensaje multipart
    
    fwd.attach(body_part) # Adjuntar la parte alternativa (texto + HTML) al mensaje principal
    
    # Adjuntar cada archivo adjunto del correo original
    for attachment in original.get('attachments', []):
        part = MIMEBase(attachment['maintype'], attachment['subtype']) # Crear una parte MIME para el archivo adjunto
        part.set_payload(attachment['data']) # Establecer el contenido del archivo adjunto
        
        # Codificar el archivo adjunto en base64 para que pueda ser enviado por correo electrónico
        encoders.encode_base64(part)
        
        # Agregar encabezados para indicar que es un archivo adjunto y su nombre
        part.add_header(
            'Content-Disposition',
            'attachment',
            filename=attachment['filename']
        )
        
        fwd.attach(part) # Adjuntar el archivo al mensaje multipart
    
    return fwd # Devolver el mensaje de reenvío construido

def send_email(fwd_msg: MIMEMultipart, recipient_email: str, cfg: dict) -> None:
    """
        Función para enviar el mail por SMTP con autenticación TLS.
    """
    with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port']) as server: # Conexión al servidor SMTP
        server.starttls() # Iniciar TLS para seguridad
        server.login(cfg['email_address'], cfg['email_password']) # Autenticación con el servidor SMTP
        server.sendmail(cfg['email_address'], recipient_email, fwd_msg.as_string()) # Enviar el correo electrónico