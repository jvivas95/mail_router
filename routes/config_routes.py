# routes/config_routes.py - Guardar configuración del servidor de correo
"""
    Blueprint -> agrupa rutas relacionadas.
    request -> maneja datos de solicitudes entrantes.
    redirect -> redirige a otra ruta.
    url_for -> genera URLs para rutas.
    flash -> muestra mensajes temporales al usuario.
"""
from flask import Blueprint, request, redirect, url_for, flash
from config import load_config, save_config # Importamos las funciones necesarias para manejar la configuración

# Creación del Blueprint para agrupar todas las rutas relacionadas con la configuración.
config_bp = Blueprint('config_routes', __name__)

# El decorador @route conecta la URL '/config' con la función update(). Solo acepta solicitudes POST.
@config_bp.route('/config', methods=['POST'])
def update():
    cfg = load_config() # Cargamos la configuración actual
    
    cfg['email_address'] = request.form.get('email_address', "").strip() # Obtenemos el email del formulario y lo limpiamos de espacios
    cfg['email_password'] = request.form.get('email_password', "").strip() # Obtenemos la contraseña del formulario y la limpiamos de espacios
    cfg['imap_host'] = request.form.get('imap_host', "imap.gmail.com").strip() # Obtenemos el host IMAP del formulario y lo limpiamos de espacios
    cfg['smtp_host'] = request.form.get('smtp_host', "smtp.gmail.com").strip() # Obtenemos el host SMTP del formulario y lo limpiamos de espacios
    cfg['check_interval'] = int(request.form.get('check_interval', 60)) # Obtenemos el intervalo de chequeo del formulario y lo convertimos a entero
    
    save_config(cfg) # Guardamos la configuración actualizada
    flash('Configuración actualizada', 'success') # Mostramos un mensaje de éxito al usuario
    return redirect(url_for('dashboard.index')) # Redirigimos al dashboard para mostrar la configuración actualizada