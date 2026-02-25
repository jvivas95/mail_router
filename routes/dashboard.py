"""
routes/dashboard.py — Rutas principales del dashboard
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from models.database import (
    get_emails, get_stats, get_all_recipients,
    get_active_recipients, get_rotation_state
)
from services.worker import is_running, process_inbox, start_worker
from config import load_config

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    emails    = get_emails(limit=50)
    recipients = get_all_recipients()
    active     = get_active_recipients()
    state      = get_rotation_state()
    stats      = get_stats()
    cfg        = load_config()

    current_recipient = None
    if active and state:
        idx = state["current_index"] % len(active)
        current_recipient = active[idx]

    return render_template(
        "dashboard.html",
        emails=emails,
        recipients=recipients,
        active_recipients=active,
        current_recipient=current_recipient,
        stats=stats,
        cfg=cfg,
        worker_running=is_running()
    )


@dashboard_bp.route("/email/<int:eid>")
def email_detail(eid):
    from models.database import get_email_by_id
    em = get_email_by_id(eid)
    if not em:
        return "No encontrado", 404
    return render_template("email_detail.html", email=em)


@dashboard_bp.route("/worker/start", methods=["POST"])
def worker_start():
    from config import save_config
    cfg = load_config()
    cfg["active"] = True
    save_config(cfg)
    start_worker()
    flash("Monitor de correos activado", "success")
    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/worker/stop", methods=["POST"])
def worker_stop():
    from config import save_config
    from services.worker import stop_worker
    cfg = load_config()
    cfg["active"] = False
    save_config(cfg)
    stop_worker()
    flash("Monitor de correos detenido", "success")
    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/worker/check-now", methods=["POST"])
def check_now():
    cfg = load_config()
    if not cfg.get("email_address") or not cfg.get("email_password"):
        flash("Configura el email primero", "error")
        return redirect(url_for("dashboard.index"))
    n = process_inbox(cfg)
    if n >= 0:
        flash(f"Revisión completada: {n} correos nuevos procesados", "success")
    else:
        flash("Error al conectar con el servidor de correo", "error")
    return redirect(url_for("dashboard.index"))