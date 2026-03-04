# routes/dashboard.py
"""
    Blueprint -> agrupa rutas relacionadas.
    render_template -> renderiza plantillas HTML.
    redirect -> redirige a otra ruta.
    url_for -> genera URLs para rutas.
    flash -> muestra mensajes temporales al usuario.
"""
from flask import Blueprint, render_template, redirect, url_for, flash # Blueprint para organizar las rutas, render_template para renderizar las plantillas, redirect y url_for para redirigir a otras rutas, flash para mostrar mensajes
from models.database import get_emails, get_stats, get_all_recipients # Importamos las funciones necesarias de la base de datos
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
    stats = get_stats() # Obtenemos las estadísticas de la base de datos
    cfg = load_config() # Cargamos la configuración actual
    
    # Renderización de la plantilla 'dashboard.html' con los datos obtenidos. Busca el archivo en la carpeta templates/
    return render_template(
        'dashboard.html',
        emails = emails,
        recipients = recipients,
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