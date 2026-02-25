"""
routes/config_routes.py — Guardar configuración del servidor de correo
"""

from flask import Blueprint, request, redirect, url_for, flash
from config import load_config, save_config

config_bp = Blueprint("config_routes", __name__)


@config_bp.route("/config", methods=["POST"])
def update():
    cfg = load_config()

    cfg["email_address"]  = request.form.get("email_address", "").strip()
    cfg["email_password"]  = request.form.get("email_password", "").strip()
    cfg["imap_host"]      = request.form.get("imap_host", "imap.gmail.com").strip()
    cfg["smtp_host"]      = request.form.get("smtp_host", "smtp.gmail.com").strip()
    cfg["check_interval"] = int(request.form.get("check_interval", 60))

    save_config(cfg)
    flash("Configuración guardada correctamente", "success")
    return redirect(url_for("dashboard.index"))