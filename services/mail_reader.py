# services/mail_reader.py
import imaplib # Para conectarse al servidor IMAP y leer correos electrónicos
import email, email.message # Transforma el correo electrónico en un objeto de Python para facilitar su manipulación
from email.header import decode_header # Para decodificar los encabezados de los correos electrónicos, como el asunto y el remitente

def decode_str(s) -> str:
    """Decodifica cabeceras del mail (asunto, remitente, etc...)
    que pueden venir codificadas en Base64 o Quoted-Printable."""
    if s is None: # Si el valor es None, devolvemos una cadena vacía para evitar errores posteriores
        return ""
    
    parts = decode_header(s) # Devuelve una lista de tuplas (parte_decodificada, charset) para cada fragmento del encabezado
    result = [] # lista vacía para almacenar las partes decodificadas del encabezado
    
    for part, enc in parts: # Iteramos sobre cada parte decodificada del encabezado
        if isinstance(part, bytes): # Si la parte es un objeto bytes, intentamos decodificarlo usando el charset especificado
            result.append(part.decode(enc or 'utf-8', errors='replace')) # Si el charset no está especificado, se asume 'utf-8'. Si la decodificación falla, se reemplazan los caracteres no decodificables.
        else:
            result.append(part) # Si la parte ya es una cadena (str), se agrega directamente a la lista de resultados sin necesidad de decodificación
    return ''.join(result) # Unimos todas las partes decodificadas en una sola cadena y la devolvemos


def safe_decode(payload: bytes, charset: str) -> str: # Payload es el contenido del correo electrónico en bytes | charset es el conjunto de caracteres que se supone que se debe usar para decodificar el payload
    """Intenta decodificar bytes probando varios encodings.
    Así se evita que un correo con un charset mal especificado cause errores."""
    charset = (charset or 'utf-8').lower().strip() # Si el charset es None, se asume 'utf-8'. Se convierte a minúsculas y se eliminan espacios en blanco para normalizar el valor del charset.
    
    for enc in [charset, 'utf-8', 'latin-1', 'cp1252']: # Intentamos decodificar usando varios encodings para evitar errores. Primero se intenta con el charset especificado, luego con 'utf-8', 'latin-1' y finalmente 'cp1252' (windows).
        try: # Intentamos decodificar el payload usando el encoding actual. Si la decodificación es exitosa, se devuelve el resultado. Si falla, se captura la excepción y se continúa con el siguiente encoding en la lista.
            return payload.decode(enc, errors='replace') # Intenta convertir los bytes del payload a una cadena usando el encoding actual. Si hay caracteres que no se pueden decodificar, se reemplazan con un carácter de reemplazo (generalmente '?').
        except (LookupError, UnicodeDecodeError): # Captura de errores relacionados con el encoding (LookupError si el encoding no es reconocido, UnicodeDecodeError si hay un error al decodificar). Si ocurre alguno de estos errores, se continúa con el siguiente encoding en la lista.
            continue
    return payload.decode('latin-1', errors='replace') # Si todos los intentos anteriores fallan, se intenta decodificar usando 'latin-1' como último recurso, ya que este encoding puede decodificar cualquier byte sin generar errores (aunque el resultado puede no ser correcto si el charset real es diferente).


def fetch_unseen_emails(cfg: dict) -> list:
    """Conecta al servidor IMAP y devuelve los correos no leídos."""
    
    # 1. Conectar al servidor seguro (SSL en el puerto 993)
    try:
        mail = imaplib.IMAP4_SSL(cfg['imap_host'], cfg['imap_port']) # Crea una conexión segura al servidor IMAP utilizando SSL. El host y el puerto se obtienen del diccionario de configuración (cfg).
        mail.login(cfg['email_address'], cfg['email_password']) # Inicia sesión en el servidor IMAP utilizando la dirección de correo electrónico y la contraseña proporcionadas en el diccionario de configuración (cfg).
        mail.select('INBOX') # Selecciona la bandeja de entrada
    except Exception as e:
        print(f"Error al conectar al servidor IMAP: {e}")
        return [] # Si hay un error al conectar o iniciar sesión, se imprime el error y se devuelve una lista vacía para indicar que no se pudieron obtener correos electrónicos.
    
    # 2. Buscar correos no leídos
    try:
        _, search_data = mail.search(None, 'UNSEEN') # Busca los correos electrónicos que no han sido leídos (UNSEEN) en la bandeja de entrada. El resultado es una lista de UIDs (identificadores únicos) de los correos no leídos.
        uids = search_data[0].split() # Lista de UIDs de correos no leídos. Se obtiene el primer elemento de search_data (que es una cadena de bytes con los UIDs separados por espacios) y se divide en una lista de UIDs individuales.
    except Exception as e:
        print(f"Error al buscar correos no leídos: {e}")
        mail.logout()
        return [] # Si hay un error al buscar los correos no leídos, se imprime el error, se cierra la conexión al servidor IMAP y se devuelve una lista vacía para indicar que no se pudieron obtener correos electrónicos.
    for uid_bytes in uids: # Bucle para procesar cada correo no leído utilizando su UID.
        uid = uid_bytes.decode() # Decodifica el UID de bytes a cadena para facilitar su uso en el diccionario de resultados y en la impresión de errores. El UID es un identificador único que se utiliza para referirse a cada correo electrónico en el servidor IMAP.
        try:
            # 3. Descargar el correo completo en formato RFC822
            _, msg_data = mail.fetch(uid_bytes, '(RFC822)') # Descarga el correo completo en formato RFC822 utilizando el UID. El resultado es una lista de tuplas, donde cada tupla contiene el UID y el contenido del correo en bytes.
            raw = msg_data[0][1] # El correo completo en bytes se encuentra en el segundo elemento de la primera tupla de msg_data. Este es el contenido del correo electrónico que se va a procesar.
            msg = email.message_from_bytes(raw) # Convertir a objeto email.message para facilitar la manipulación. Esto transforma el correo electrónico en un objeto de Python que permite acceder fácilmente a sus partes, como los encabezados y el cuerpo.
            
            # Creación de un diccionario con la información relevante del correo electrónico para su posterior procesamiento. Se decodifican los encabezados utilizando la función decode_str para manejar posibles codificaciones en Base64 o Quoted-Printable.
            # El cuerpo del correo se obtiene utilizando la función get_body, que maneja correos con múltiples partes (multipart) y decodifica el contenido de texto.
            results.append({
                'uid': uid,
                'sender': decode_str(msg.get('From', '')), # Decodifica el encabezado 'From' para obtener el remitente del correo electrónico. Si el encabezado no está presente, se devuelve una cadena vacía.
                'subject': decode_str(msg.get('Subject', '(sin asunto)')), # Decodifica el encabezado 'Subject' para obtener el asunto del correo electrónico. Si el encabezado no está presente, se devuelve '(sin asunto)'.
                'date': decode_str(msg.get('Date', '')), # Decodifica el encabezado 'Date' para obtener la fecha del correo electrónico. Si el encabezado no está presente, se devuelve una cadena vacía.
                'body': get_body(msg), # Obtiene el cuerpo del correo electrónico utilizando la función get_body, que maneja correos con múltiples partes (multipart) y decodifica el contenido de texto.
                'raw_msg': msg # Objeto original para reenviar o procesar posteriormente sin perder información. Esto permite acceder a cualquier parte del correo electrónico que pueda ser necesaria en el futuro, como los archivos adjuntos o los encabezados adicionales.
            })
        except Exception as e:
            print(f"Error al procesar correo UID {uid}: {e}")
            continue # Si hay un error con un correo, se salta al siguiente
    
    mail.logout() # Cerrar la conexión al servidor
    return results # Devuelve la lista de correos no leídos procesados, cada uno representado como un diccionario con su información relevante (UID, remitente, asunto, fecha, cuerpo y el objeto original del correo).