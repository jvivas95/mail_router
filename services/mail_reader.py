# services/mail_reader.py
import imaplib # Para conectarse al servidor IMAP y leer correos electrónicos
import email, email.message # Transforma el correo electrónico en un objeto de Python para facilitar su manipulación
from email.header import decode_header # Para decodificar los encabezados de los correos electrónicos, como el asunto y el remitente

def decode_str(s) -> str:
    """Decodifica cabeceras del mail (asunto, remitente, etc...)
    que pueden venir codificadas en Base64 o Quoted-Printable."""
    if s is None:
        return ""
    
    parts = decode_header(s)
    result = []
    
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or 'utf-8', errors='replace'))
        else:
            result.append(part)
    return ''.join(result)


def safe_decode(payload: bytes, charset: str) -> str:
    """Intenta decodificar bytes probando varios encodings.
    Así se evita que un correo con un charset mal especificado cause errores."""
    charset = (charset or 'utf-8').lower().strip()
    for enc in [charset, 'utf-8', 'latin-1', 'cp1252']:
        try:
            return payload.decode(enc, errors='replace')
        except (LookupError, UnicodeDecodeError):
            continue
    return payload.decode('latin-1', errors='replace') # Fallback final


def fetch_unseen_emails(cfg: dict) -> list:
    """Conecta al servidor IMAP y devuelve los correos no leídos."""
    
    # 1. Conectar al servidor seguro (SSL en el puerto 993)
    try:
        mail = imaplib.IMAP4_SSL(cfg['imap_host'], cfg['imap_port'])
        mail.login(cfg['email_address'], cfg['email_password'])
        mail.select('INBOX') # Selecciona la bandeja de entrada
    except Exception as e:
        print(f"Error al conectar al servidor IMAP: {e}")
        return []
    
    # 2. Buscar correos no leídos
    try:
        _, search_data = mail.search(None, 'UNSEEN')
        uids = search_data[0].split() # Lista de UIDs de correos no leídos
    except Exception as e:
        print(f"Error al buscar correos no leídos: {e}")
        mail.logout()
        return []
    for uid_bytes in uids:
        uid = uid_bytes.decode()
        try:
            # 3. Descargar el correo completo en formato RFC822
            _, msg_data = mail.fetch(uid_bytes, '(RFC822)')
            raw = msg_data[0][1] # El correo completo en bytes
            msg = email.message_from_bytes(raw) # Convertir a objeto email.message
            
            results.append({
                'uid': uid,
                'sender': decode_str(msg.get('From', '')),
                'subject': decode_str(msg.get('Subject', '(sin asunto)')),
                'date': decode_str(msg.get('Date', '')),
                'body': get_body(msg),
                'raw_msg': msg # Objeto original para reenviar
            })
        except Exception as e:
            print(f"Error al procesar correo UID {uid}: {e}")
            continue # Si hay un error con un correo, se salta al siguiente
    
    mail.logout() # Cerrar la conexión al servidor
    return results