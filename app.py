# app.py - Entry point: registra Blueprints y arranca la app

from flask import Flask
from flask_login import LoginManager

from models.database import init_db, get_user_by_id, create_default_admin
from models.user import User
from config import load_config
from services.worker import start_worker, stop_worker

from routes.dashboard import dashboard_bp
from routes.recipients import recipients_bp
from routes.config_routes import config_bp
from routes.api import api_bp
from routes.auth import auth_bp
from routes.users import users_bp

# Crear la aplicación Flask
app = Flask(__name__) # Se utiliza __name__ para que Flask sepa dónde buscar los archivos de templates y estáticos

# Configuración de la clave secreta para sesiones (importante para seguridad)
# Es una clave que Flask utiliza para firmar las cookies de sesión y los mensajes flash. Sin esta clave, los mensajes Flash no funcionan.
app.secret_key = 'supersecretkey'  # Cambiar esto en producción, si no se cambia, cualquiera podría falsificar sesiones.

# Flask-Login
login_manager = LoginManager() # Creamos una instancia de LoginManager, que es la extensión de Flask-Login que se encarga de manejar la autenticación de usuarios.
login_manager.init_app(app) # Inicializamos Flask-Login con nuestra aplicación Flask
login_manager.login_view = 'auth.login' # Especificamos la vista de inicio de sesión, es decir, a dónde se redirige a los usuarios no autenticados cuando intentan acceder a una ruta protegida.
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página." # Mensaje que se muestra cuando un usuario no autenticado intenta acceder a una ruta protegida.
login_manager.login_message_category = "error" # Categoría del mensaje de inicio de sesión, se puede usar para estilos en el frontend.

@login_manager.user_loader
def load_user(user_id):
    """Cargar el usuario desde la DB en cada request autenticado."""
    row = get_user_by_id(user_id) # Obtener el usuario de la base de datos usando su ID
    if not row:
        return None # Si no se encuentra el usuario, devolver None
    return User(id=row['id'], username=row['username'], role=row['role']) # Devolver una instancia de User con los datos obtenidos de la base de datos

# Registrar Blueprints
# Con register_blueprint, estamos diciendo a Flask que incluya las rutas definidas en cada Blueprint. Esto ayuda a organizar el código en módulos separados.
app.register_blueprint(auth_bp) # Blueprint para autenticación (login/logout)
app.register_blueprint(dashboard_bp)
app.register_blueprint(recipients_bp)
app.register_blueprint(config_bp)
app.register_blueprint(api_bp)
app.register_blueprint(users_bp) # Blueprint para gestión de usuarios (solo admin)

# Iniciar la aplicación
if __name__ == '__main__': # Este bloque se ejecuta solo si este archivo se ejecuta directamente, no si se importa como módulo
    init_db()  # Inicializar la base de datos
    create_default_admin()  # Crear un usuario admin por defecto si no existe
    cfg = load_config()  # Cargar configuración
    if cfg.get('active') and cfg.get('email_address'):
        start_worker()  # Iniciar el worker si la configuración es válida
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)  # Evitar reinicios múltiples con el worker