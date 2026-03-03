import smtplib # Libreria para enviar correos
from email.mime.multipart import MIMEMultipart # Libreria para crear correos con múltiples partes (texto, HTML, archivos adjuntos)
from email.mime.text import MIMEText # Libreria para crear el contenido del correo
from datetime import datetime # Libreria para manejar fechas y horas
from models.database import get_db, get_active_recipients # Funciones para interactuar con la base de datos

def get_next_recipients():
    """Devuelve el siguiente destinatario en la rotación y avanza el índice para la próxima vez."""
    recipients = get_active_recipients() # Obtener la lista de destinatarios activos desde la base de datos
    if not recipients:
        return None, -1 # Si no hay destinatarios, devolver None y un índice inválido
    
    conn = get_db() # Obtener la conexión a la base de datos
    state = conn.execute(
        'SELECT current_index FROM rotation_state WHERE id = 1'
    ).fetchone() # Obtener el índice actual de rotación
    
    # Si el índice supera el número de agentes, reiniciar a 0
    idx = state['current_index'] if state else 0 # Si no hay estado, iniciar en 0
    if idx >= len(recipients): # Si el índice es mayor o igual al número de destinatarios, reiniciar a 0
        idx = 0
    
    recipient = recipients[idx] # Obtener el destinatario actual según el índice
    next_idx = (idx + 1) % len(recipients) # Calcular el siguiente índice de rotación
    
    # Guardar el nuevo índice en la base de datos
    conn.execute(
        'UPDATE rotation_state SET current_index = ?, last_updated = ? WHERE id=1',
        (next_idx, datetime.now().isoformat())
    )
    conn.commit() # Guardar los cambios en la base de datos
    conn.close() # Cerrar la conexión a la base de datos
    
    return recipient, idx # Devolver el destinatario actual y el índice utilizado para esta rotación

def send_email(fwd_msg, recipient_email: str, cfg: dict) -> None:
    """Función para enviar el mail por SMTP con autenticación TLS."""
    with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port']) as server: # Conexión al servidor SMTP
        server.starttls() # Iniciar TLS para seguridad
        server.login(cfg['email_address'], cfg['email_password']) # Autenticación con el servidor SMTP
        server.sendmail(cfg['email_address'], recipient_email, fwd_msg.as_string()) # Enviar el correo electrónico