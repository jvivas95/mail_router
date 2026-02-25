"""
MailRouter — Entry point
"""

from flask import Flask
from models.database import init_db
from services.worker import start_worker
from config import load_config

from routes.dashboard import dashboard_bp
from routes.recipients import recipients_bp
from routes.config_routes import config_bp
from routes.api import api_bp

app = Flask(__name__)
app.secret_key = "mailrouter-secret-2024"

# Registrar blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(recipients_bp)
app.register_blueprint(config_bp)
app.register_blueprint(api_bp)

if __name__ == "__main__":
    init_db()
    cfg = load_config()
    if cfg.get("active") and cfg.get("email_address"):
        start_worker()
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)