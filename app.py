# app.py - Entry point: registra Blueprints y arranca la app

from flask import Flask
from models.database import init_db
from config import load_config
from services.worker import start_worker, stop_worker

from routes.dashboard import dashboard_bp
from routes.recipients import recipients_bp
from routes.config_routes import config_bp
from routes.api import api_bp

# Crear la aplicación Flask
app = Flask(__name__) # Se utiliza __name__ para que Flask sepa dónde buscar los archivos de templates y estáticos

# Configuración de la clave secreta para sesiones (importante para seguridad)
# Es una clave que Flask utiliza para firmar las cookies de sesión y los mensajes flash. Sin esta clave, los mensajes Flash no funcionan.
app.secret_key = 'supersecretkey'  # Cambiar esto en producción, si no se cambia, cualquiera podría falsificar sesiones.

# Registrar Blueprints
# Con register_blueprint, estamos diciendo a Flask que incluya las rutas definidas en cada Blueprint. Esto ayuda a organizar el código en módulos separados.
app.register_blueprint(dashboard_bp)
app.register_blueprint(recipients_bp)
app.register_blueprint(config_bp)
app.register_blueprint(api_bp)

# Iniciar la aplicación
if __name__ == '__main__': # Este bloque se ejecuta solo si este archivo se ejecuta directamente, no si se importa como módulo
    init_db()  # Inicializar la base de datos
    cfg = load_config()  # Cargar configuración
    if cfg.get('active') and cfg.get('email_address'):
        start_worker()  # Iniciar el worker si la configuración es válida
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)  # Evitar reinicios múltiples con el worker