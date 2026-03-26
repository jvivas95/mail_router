# services/worker.py - Thread de monitoreo en segundo plano

import threading  # librería estándar de Python para ejecutar código en paralelo (threads)
import time # librería estándar de Python para manejar el tiempo, utilizada para implementar retrasos entre las ejecuciones del worker
import traceback # librería estándar de Python para manejar y mostrar trazas de errores, utilizada para depurar errores que puedan ocurrir durante la ejecución del worker
from datetime import datetime # librería estándar de Python para manejar fechas y horas, utilizada para registrar la fecha y hora de los correos procesados

from config import load_config # Para cargar la configuración del worker
from models.database import get_db # Para registrar los correos procesados en la base de datos
from services.mail_reader import fetch_unseen_emails # Para obtener los correos no leídos del servidor IMAP
from services.mail_sender import build_forward_email, send_email, get_next_recipient # Para enviar correos electrónicos a los destinatarios correspondientes

# Variables globales del módulo (estado del worker)
# El guion bajo _ indica que es una variable privada del módulo, no debe ser accedida directamente desde fuera del módulo.
_worker_running = False # Interruptor del worker, indica si el worker está en ejecución o no.
_worker_thread: threading.Thread | None = None # Variable para almacenar la referencia al hilo del worker, se utiliza para controlar la ejecución del worker en segundo plano y permitir su detención cuando sea necesario.

def is_running():
    """Devuelve True si el worker está en ejecución, False en caso contrario."""
    return _worker_running

def _forward_pending_emails(conn, cfg:dict) -> int:
    """Función para reenviar correos electrónicos que están en estado 'pending', 'no_recipients' o 'error'. Retorna el número de correos procesados exitosamente."""
    rows = conn.execute(
        """
        SELECT uid, sender, subject, date_received, body, status
        FROM emails
        WHERE status IN ('pending', 'no_recipients', 'error')
        ORDER BY id ASC
        """
    ).fetchall() # Obtener los correos electrónicos que están en estado 'pending', 'no_recipients' o 'error' para intentar reenviarlos nuevamente. Se ordenan por ID ascendente para procesar primero los correos más antiguos.
    
    if not rows:
        return 0 # Si no hay correos electrónicos pendientes para reenviar, se devuelve 0 para indicar que no se procesaron correos electrónicos.
    
    processed = 0 # Contador para el número de correos electrónicos procesados exitosamente.
    
    for row in rows: # Bucle para procesar cada correo electrónico pendiente individualmente.
        recipient, _ = get_next_recipient() # Obtener el siguiente destinatario en la rotación para reenviar el correo electrónico. Se utiliza la función get_next_recipient para obtener el destinatario actual y avanzar el índice de rotación.
        if not recipient:
            if row['status'] != 'no_recipients': # Si no hay destinatarios disponibles y el estado actual del correo electrónico no es 'no_recipients', se actualiza el estado a 'no_recipients' en la base de datos para indicar que no se pudo reenviar debido a la falta de destinatarios.
                conn.execute(
                    "UPDATE emails SET status = 'no_recipients' WHERE uid=?",
                    (row['uid'],)
                )
                conn.commit() # Guardar los cambios en la base de datos después de actualizar el estado del correo electrónico a 'no_recipients'.
            continue
        
        original = {
            'sender': row['sender'] or '', # Si el valor del remitente es None, se asigna una cadena vacía para evitar errores al construir el correo electrónico a reenviar.
            'subject': row['subject'] or '(sin asunto)', # Si el valor del asunto es None, se asigna '(sin asunto)' para evitar errores al construir el correo electrónico a reenviar.
            'date': row['date_received'] or '', # Si el valor de la fecha de recepción es None, se asigna una cadena vacía para evitar errores al construir el correo electrónico a reenviar.
            'body': row['body'] or '', # Si el valor del cuerpo es None, se asigna una cadena vacía para evitar errores al construir el correo electrónico a reenviar.
            'attachments': [],
            'raw_msg': None
        }
        
        try:
            fwd = build_forward_email(original, recipient, cfg['email_address']) # Construir el correo electrónico a reenviar utilizando la función build_forward_email, que crea un nuevo mensaje de correo electrónico con el contenido del correo original y lo dirige al destinatario actual.
            send_email(fwd, recipient['email'], cfg) # Enviar el correo electrónico utilizando la función send_email, que maneja la conexión al servidor SMTP y el envío del correo electrónico al destinatario obtenido en la rotación.
            conn.execute("""
                        UPDATE emails
                        SET forwarded_to = ?, forwarded_at = ?, status = 'forwarded'
                        WHERE uid = ?
                        """,
                        (f"{recipient['name']} <{recipient['email']}>", datetime.now().isoformat(), row['uid'],) # Actualización del estado a 'forwarded' en la base de datos después de enviar el correo electrónico exitosamente, junto con la información del destinatario al que se reenviará y la fecha y hora del reenvío.
            )
            conn.commit() # Guardar los cambios en la base de datos después de actualizar el estado del correo electrónico a 'forwarded' y registrar la información del destinatario al que se reenviará y la fecha y hora del reenvío.
            processed += 1 # Incrementar el contador de correos electrónicos procesados exitosamente.
            print(f"[Worker] Reenviado correo UID {row['uid']} a {recipient['email']}") # Imprimir un mensaje de depuración indicando que el correo electrónico con el UID actual ha sido reenviado al destinatario correspondiente.
        
        except Exception as e:
            print(f"[Worker] Error al reenviar correo UID {row['uid']}: {e}") # Si hay un error al reenviar el correo electrónico, se imprime el error para fines de depuración, incluyendo el UID del correo electrónico que causó el error.
            conn.execute(
                "UPDATE emails SET status = 'error' WHERE uid = ?", # Si ocurre un error al reenviar el correo electrónico, se actualiza el estado del correo electrónico en la base de datos a 'error' para indicar que hubo un problema durante el proceso de reenvío.
                (row['uid'],)
            )
            conn.commit() # Guardar los cambios en la base de datos después de actualizar el estado del correo electrónico a 'error'.
    
    return processed # Devolver el número de correos electrónicos que se procesaron exitosamente durante este intento de reenvío de correos pendientes.

def process_inbox(cfg: dict) -> int:
    """Lectura de correos nuevos, los registra y los reenvía.
    Retorna: nº de correos procesados, o -1 si hay errores."""
    try:
        emails = fetch_unseen_emails(cfg) # Obtener los correos no leídos del servidor IMAP utilizando la configuración proporcionada (cfg).
        print(f"[worker] {len(emails)} correos no leídos encontrados.") # Imprimir el número de correos no leídos encontrados para fines de depuración.
    except Exception as e:
        print(f"[Worker] Error IMAP: {e}") # Si hay un error al obtener los correos no leídos, se imprime el error para fines de depuración.
        traceback.print_exc() # Imprimir la traza completa del error para obtener más detalles sobre el error que ocurrió durante la obtención de los correos no leídos.
        return -1 # Devolver -1 para indicar que hubo un error al procesar los correos electrónicos.
    
    if not emails: # Si no hay correos no leídos, se devuelve 0 para indicar que no se procesaron correos electrónicos.
        return 0
    
    conn = get_db() # Obtener la conexión a la base de datos para registrar los correos procesados.
    processed = 0 # Contador para el número de correos procesados exitosamente.
    
    for em in emails: # Bucle que itera sobre cada correo no leído obtenido del servidor IMAP para procesarlo individualmente.
        
        # DEBUG — Imprimir información detallada del correo electrónico para depuración, incluyendo el asunto, el número de adjuntos detectados, los detalles de cada adjunto y la estructura MIME completa del correo electrónico.
        # Esto es útil para verificar que se están obteniendo correctamente los correos electrónicos y sus adjuntos, y para identificar posibles problemas con la estructura de los correos electrónicos que puedan afectar el proceso de reenvío.
        print(f"\n{'='*50}")
        print(f"SUBJECT: {em['subject']}")
        print(f"ADJUNTOS DETECTADOS: {len(em['attachments'])}")
        for i, att in enumerate(em['attachments']):
            print(f"  [{i}] filename='{att['filename']}' maintype='{att['maintype']}' subtype='{att['subtype']}'")
        
        # Imprimir la estructura MIME completa del correo
        print("\nESTRUCTURA MIME:")
        for part in em['raw_msg'].walk():
            print(f"  content_type={part.get_content_type()} | disposition={part.get('Content-Disposition','ninguna')} | filename={part.get_filename()}")
        print('='*50)
        
        # Evitar duplicados: comprobación si ya se ha procesado este UID
        # Verificar si el correo electrónico con el UID actual ya ha sido registrado en la base de datos para evitar procesar correos duplicados.
        existing = conn.execute('SELECT id FROM emails WHERE uid=?',(em['uid'],)).fetchone()
        if existing:
            continue # Si el correo electrónico ya ha sido registrado, se omite y se continúa con el siguiente correo en la lista.
        
        # El correo se guarda en la base de datos con el estado 'pending'. Se realiza antes del reenvío para asegurar que quede registrado incluso si el proceso de reenvío falla posteriormente.
        conn.execute("""
            INSERT INTO emails (uid, sender, subject, date_received, body, status, attachments_count)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (em['uid'], em['sender'], em['subject'], datetime.now().isoformat(), em['body'], len(em['attachments']))
        )
        conn.commit() # Guardar los cambios en la base de datos después de insertar el nuevo correo electrónico.
        
        # Obtención del próximo destinatario en la rotación para reenviar el correo electrónico. Se utiliza la función get_next_recipient para obtener el destinatario actual y avanzar el índice de rotación.
        recipient, _= get_next_recipient() # Utilización de _ para ignorar el segundo valor devuelto por get_next_recipient, que es el índice de rotación actualizado, ya que no se necesita en este contexto.
        # Si no hay destinatarios disponibles, se actualiza el estado del correo electrónico a 'no_recipients' en la base de datos y se omite el proceso de reenvío para este correo electrónico.
        if not recipient:
            conn.execute(
                "UPDATE emails SET status = 'no_recipients' WHERE uid=?",
                (em['uid'],)
            )
            conn.commit() # Si no hay destinatarios disponibles, se actualiza el estado del correo electrónico en la base de datos a 'no_recipients' para indicar que no se pudo reenviar debido a la falta de destinatarios.
            continue
        
        try:
            # Construcción y envío del email utilizando la función send_email, que maneja la conexión al servidor SMTP y el envío del correo electrónico al destinatario obtenido en la rotación.
            fwd = build_forward_email(em, recipient, cfg['email_address']) # Construir el correo electrónico a reenviar utilizando la función build_forward_email, que crea un nuevo mensaje de correo electrónico con el contenido del correo original y lo dirige al destinatario actual.
            send_email(fwd, recipient['email'], cfg) # Enviar el correo electrónico utilizando la función send_email, que maneja la conexión al servidor SMTP y el envío del correo electrónico al destinatario obtenido en la rotación.
            
            # Actualización del estado a 'forwarded' en la base de datos después de enviar el correo electrónico exitosamente, junto con la información del destinatario al que se reenviará y la fecha y hora del reenvío.
            conn.execute("""
                        UPDATE emails SET forwarded_to = ?, forwarded_at = ?, status = 'forwarded'
                        WHERE uid = ?
                        """,
                        (f"{recipient['name']} <{recipient['email']}>", datetime.now().isoformat(), em['uid'])
                        )
            conn.commit() # Guardar los cambios en la base de datos después de actualizar el estado del correo electrónico.
            
            processed += 1 # Incrementar el contador de correos procesados exitosamente.
        
        except Exception as e:
            print(f"[Worker] Error al reenviar: {e}") # Si hay un error al reenviar el correo electrónico, se imprime el error para fines de depuración.
            conn.execute(
                "UPDATE emails SET status = 'error' WHERE uid = ?",
                (em['uid'],)
            )
            conn.commit() # Si ocurre un error al reenviar el correo electrónico, se actualiza el estado del correo electrónico en la base de datos a 'error' para indicar que hubo un problema durante el proceso de reenvío.
    
    # Llamar a la función _forward_pending_emails para intentar reenviar los correos electrónicos que están en estado 'pending', 'no_recipients' o 'error',
    # y obtener el número de correos electrónicos que se procesaron exitosamente durante este intento de reenvío de correos pendientes.
    processed += _forward_pending_emails(conn, cfg) 
    
    conn.close() # Cerrar la conexión a la base de datos después de procesar los correos electrónicos pendientes para liberar recursos y evitar posibles bloqueos en la base de datos.
    return processed # Devolver el número de correos electrónicos que se procesaron exitosamente.

def _worker_loop(): # Se utiliza un guion bajo al inicio del nombre de la función para indicar que es privada del módulo, no se debe llamar directamente desde fuera.
    """Bucle infinito que se ejecuta en un thread separado para procesar la bandeja de entrada a intervalos regulares definidos en la configuración."""
    global _worker_running # Indica que el worker está en ejecución, se utiliza para controlar el bucle infinito del worker.
    
    print("[Worker] Iniciando worker...") # Imprimir un mensaje de depuración indicando que el worker está iniciando.
    
    while _worker_running: # Bucle infinito que se ejecuta mientras el worker esté activo. El worker se detendrá cuando _worker_running se establezca en False.
        cfg = load_config() # Cargar la configuración del worker para obtener los parámetros necesarios para procesar la bandeja de entrada, como los intervalos de tiempo entre cada ejecución.
        if cfg.get('active') and cfg.get('email_address') and cfg.get('email_password'): # Verificar que la configuración esté activa y que se hayan proporcionado las credenciales de correo electrónico necesarias para procesar la bandeja de entrada. Si alguna de estas condiciones no se cumple, se omite el procesamiento de la bandeja de entrada en esta iteración del bucle.
            n = process_inbox(cfg) # Llamar a la función process_inbox para procesar la bandeja de entrada utilizando la configuración cargada, y obtener el número de correos electrónicos que se procesaron exitosamente.
            if n > 0:
                print (f"[Worker] Procesados {n} correos.") # Si se procesaron correos electrónicos exitosamente, se imprime el número de correos procesados para fines de depuración.
            elif n < 0:
                print("[Worker] Error al procesar la bandeja de entrada.") # Si hubo un error al procesar la bandeja de entrada (indicado por un valor negativo), se imprime un mensaje de error para fines de depuración.
        
        interval = cfg.get('check_interval', 60) # Obtener el intervalo de tiempo entre cada ejecución del worker desde la configuración, con un valor predeterminado de 60 segundos si no se especifica en la configuración.
        for _ in range(interval): # Bucle para esperar el intervalo configurado, comprobando cada segundo si el worker debe detenerse.
            if not _worker_running: # Si el worker ha sido detenido durante el período de espera, se sale del bucle para finalizar la ejecución del worker.
                break
            time.sleep(1) # Esperar 1 segundo antes de volver a comprobar si el worker debe detenerse. Esto permite que el worker responda rápidamente a una solicitud de detención sin tener que esperar todo el intervalo configurado.
    
    print("[Worker] Worker detenido.") # Imprimir un mensaje de depuración indicando que el worker se ha detenido después de salir del bucle infinito.

def start_worker() -> None:
    """Inicia el worker en un thread separado si no está ya en ejecución."""
    global _worker_running, _worker_thread
    if not _worker_running:
        _worker_running = True # Establecer la variable global _worker_running a True para indicar que el worker está en ejecución.
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True) # Crear un nuevo hilo para ejecutar la función _worker_loop, que contiene el bucle infinito del worker. El hilo se establece como daemon para que se cierre automáticamente cuando la aplicación principal termine.
        _worker_thread.start() # Iniciar el hilo del worker para que comience a ejecutar la función _worker_loop en segundo plano.

def stop_worker() -> None:
    """Detiene el worker y espera a que termine su ejecución."""
    global _worker_running
    _worker_running = False # Establecer la variable global _worker_running a False para indicar que el worker debe detenerse. Esto hará que el bucle infinito en la función _worker_loop termine en la próxima iteración.