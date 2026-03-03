# services/worker.py
import datetime
import threading # Para manejar el worker en un hilo separado
import time # Para simular el procesamiento de correos
from config import load_config # Para cargar la configuración del worker
from models.database import get_db # Para registrar los correos procesados en la base de datos
from services.mail_reader import fetch_unseen_emails # Para obtener los correos no leídos del servidor IMAP
from services.mail_sender import send_email, get_next_recipient # Para enviar correos electrónicos a los destinatarios correspondientes

# Variables globales del módulo (estado del worker)
_worker_running = False
_worker_thread = None

def is_running():
    """Devuelve True si el worker está en ejecución, False en caso contrario."""
    return _worker_running

def process_inbox(cfg: dict) -> int:
    """Lectura de correos nuevos, los registra y los reenvía.
    Retornoa: nº de correos procesados, o -1 si hay errores."""
    try:
        emails = fetch_unseen_emails(cfg) # Obtener los correos no leídos del servidor IMAP utilizando la configuración proporcionada (cfg).
        print(f"[worker] {len(emails)} correos no leídos encontrados.") # Imprimir el número de correos no leídos encontrados para fines de depuración.
    except Exception as e:
        print(f"[Worker] Error IMAP: {e}") # Si hay un error al obtener los correos no leídos, se imprime el error para fines de depuración.
        return -1 # Devolver -1 para indicar que hubo un error al procesar los correos electrónicos.
    
    if not emails: # Si no hay correos no leídos, se devuelve 0 para indicar que no se procesaron correos electrónicos.
        return 0
    
    conn = get_db() # Obtener la conexión a la base de datos para registrar los correos procesados.
    
    processed = 0 # Contador para el número de correos procesados exitosamente.
    
    for em in emails:
        # Evitar duplicados: comprobación si ya se ha procesado este UID
        existing = conn.execute(
            'SELECT id FROM emails WHERE uid=?',
            (em['uid'],)
        ).fetchone() # Verificar si el correo electrónico con el UID actual ya ha sido registrado en la base de datos para evitar procesar correos duplicados.
        if existing:
            continue # Si el correo electrónico ya ha sido registrado, se omite y se continúa con el siguiente correo en la lista.
        
        # Guardar en la base de datos
        conn.execute("""
            INSERT INTO emails (uid, sender, subject, date_received, body, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (em['uid'], em['sender'], em['subject'], datetime.now().isoformat(), em['body'])
        )
        conn.commit() # Guardar los cambios en la base de datos después de insertar el nuevo correo electrónico.
        
        # Obtención del próximo destinatario en la rotación para reenviar el correo electrónico. Se utiliza la función get_next_recipient para obtener el destinatario actual y avanzar el índice de rotación.
        recipient, _= get_next_recipient()
        
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
    
    conn.close() # Cerrar la conexión a la base de datos después de procesar todos los correos electrónicos.
    return processed # Devolver el número de correos electrónicos que se procesaron exitosamente.

def _worker_loop():
    """Bucle infinito que se ejecuta en un thread separado para procesar la bandeja de entrada a intervalos regulares definidos en la configuración."""
    global _worker_running # Indica que el worker está en ejecución, se utiliza para controlar el bucle infinito del worker.
    while _worker_running:
        cfg = load_config() # Cargar la configuración del worker para obtener los parámetros necesarios para procesar la bandeja de entrada, como los intervalos de tiempo entre cada ejecución.
        if cfg.get('active', False): # Verificar si el worker está activo según la configuración. Si el valor de 'active' es True, se procede a procesar la bandeja de entrada; de lo contrario, se omite el procesamiento.
            process_inbox(cfg) # Llamar a la función process_inbox para procesar los correos electrónicos en la bandeja de entrada utilizando la configuración cargada.
        
        # Esperar el intervalo configurado (comprobando cada segundo si hay que parar)
        interval = cfg.get('check_interval', 60) # Obtener el intervalo de tiempo entre cada ejecución del worker desde la configuración, con un valor predeterminado de 60 segundos si no se especifica en la configuración.
        for _ in range(interval): # Bucle para esperar el intervalo configurado, comprobando cada segundo si el worker debe detenerse.
            if not _worker_running: # Si el worker ha sido detenido durante el período de espera, se sale del bucle para finalizar la ejecución del worker.
                break
            time.sleep(1) # Esperar 1 segundo antes de volver a comprobar si el worker debe detenerse.

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