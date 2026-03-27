# routes/dashboard.py
"""
    Blueprint -> agrupa rutas relacionadas.
    render_template -> renderiza plantillas HTML.
    redirect -> redirige a otra ruta.
    url_for -> genera URLs para rutas.
    flash -> muestra mensajes temporales al usuario.
    request -> maneja datos de solicitudes entrantes.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request # Blueprint para organizar las rutas, render_template para renderizar las plantillas, redirect y url_for para redirigir a otras rutas, flash para mostrar mensajes
from models.database import (
    get_emails, get_stats, get_all_recipients,
    get_active_recipients, get_rotation_state,
    get_email_by_id
)
from services.worker import is_running, process_inbox, start_worker, stop_worker # Importamos las funciones necesarias del worker
from config import load_config, save_config # Importamos las funciones necesarias para manejar la configuración

# Creación del Blueprint para agrupar todas las rutas del dashboard.
dashboard_bp = Blueprint('dashboard', __name__)

# El decorador @route conecta la URL '/' con la función index().
@dashboard_bp.route('/')
def index():
    """Ruta principal del dashboard. Muestra mails recibidos y estado del worker."""
    emails = get_emails() # Obtenemos los emails de la base de datos
    recipients = get_all_recipients() # Obtenemos los destinatarios de la base de datos
    active = get_active_recipients() # Obtenemos los destinatarios activos de la base de datos
    state = get_rotation_state() # Obtenemos el estado de rotación de la base de datos
    stats = get_stats() # Obtenemos las estadísticas de la base de datos
    cfg = load_config() # Cargamos la configuración actual
    
    current_recipient = None # Inicializamos la variable para el destinatario actual
    if active and state: # Si hay destinatarios activos y la rotación está habilitada
        idx = state['current_index'] % len(active) # Calculamos el índice del destinatario actual usando el índice de rotación y el número de destinatarios activos
        current_recipient = active[idx] # Obtenemos el destinatario actual usando el índice calculado
    
    # Renderización de la plantilla 'dashboard.html' con los datos obtenidos. Busca el archivo en la carpeta templates/
    return render_template(
        'dashboard.html',
        emails = emails,
        recipients = recipients,
        active_recipients = active,
        current_recipient = current_recipient,
        stats = stats,
        cfg = cfg,
        worker_running = is_running()
    )


# Ruta para iniciar el worker. Solo acepta solicitudes POST.
@dashboard_bp.route('/worker/start', methods=['POST'])
def worker_start():
    """Inicia el worker para procesar la bandeja de entrada."""
    cfg = load_config() # Cargamos la configuración actual
    cfg['active'] = True # Marcamos el worker como activo
    save_config(cfg) # Guardamos la configuración actualizada
    start_worker() # Iniciamos el worker
    flash('Monitor activado', 'success') # Mostramos un mensaje de éxito al usuario
    return redirect(url_for('dashboard.index')) # Redirigimos al dashboard


# Ruta para detener el worker. Solo acepta solicitudes POST.
@dashboard_bp.route('/worker/stop', methods=['POST'])
def worker_stop():
    """Detener el worker para procesar la bandeja de entrada."""
    cfg = load_config() # Cargamos la configuración actual
    cfg['active'] = False # Marcamos el worker como inactivo
    save_config(cfg) # Guardamos la configuración actualizada
    stop_worker() # Detenemos el worker
    flash('Monitor de correos detenido', 'success') # Mostramos un mensaje de información al usuario
    return redirect(url_for('dashboard.index')) # Redirigimos al dashboard


# Ruta que muestra los detalles de un email específico. El <int:eid> indica que se espera un entero como parte de la URL, que se pasará a la función como argumento 'eid'.
@dashboard_bp.route('/email/<int:eid>')
def email_detail(eid):
    """Muestra los detalles de un email específico."""
    em = get_email_by_id(eid) # Obtenemos el email por su ID
    if not em: # Si no se encuentra el email, redirigimos al dashboard con un mensaje de error
        return 'No encontrado', 404
    return render_template('email_detail.html', email=em) # Renderizamos la plantilla 'email_detail.html' con el email obtenido


# Ruta para procesar la bandeja de entrada de inmediato. Solo acepta solicitudes POST.
@dashboard_bp.route('/worker/check-now', methods=['POST'])
def check_now():
    """Procesa la bandeja de entrada de inmediato."""
    cfg = load_config() # Cargamos la configuración actual
    if not cfg.get('email_address') or not cfg.get('email_password'): # Si no se han configurado el correo electrónico o la contraseña, mostramos un mensaje de error
        flash('Configura tu correo electrónico y contraseña para usar esta función', 'error')
        return redirect(url_for('dashboard.index')) # Redirigimos al dashboard
    
    n = process_inbox(cfg) # Procesamos la bandeja de entrada y obtenemos el número de emails procesados
    if n >= 0: # Si se procesaron 0 o más emails, mostramos un mensaje de éxito
        flash(f'Procesados {n} emails. ¡Buen trabajo!', 'success') # Si se procesaron 9 o más emails, mostramos un mensaje de éxito
    else: # Si hubo un error al procesar la bandeja de entrada, mostramos un mensaje de error
        flash('Error al procesar la bandeja de entrada. Revisa la configuración y el estado del monitor.', 'error')
    return redirect(url_for('dashboard.index')) # Redirigimos al dashboard