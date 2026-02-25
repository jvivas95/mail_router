"""
routes/recipients.py — CRUD de destinatarios del departamento comercial
"""

import sqlite3
from flask import Blueprint, request, redirect, url_for, flash
from models.database import add_recipient, toggle_recipient, delete_recipient

recipients_bp = Blueprint("recipients", __name__)


@recipients_bp.route("/recipients/add", methods=["POST"])
def add():
    name  = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not email:
        flash("Nombre y email son requeridos", "error")
        return redirect(url_for("dashboard.index"))

    try:
        add_recipient(name, email)
        flash(f"Destinatario {name} agregado", "success")
    except sqlite3.IntegrityError:
        flash("Ese email ya existe en la lista", "error")

    return redirect(url_for("dashboard.index"))


@recipients_bp.route("/recipients/<int:rid>/toggle", methods=["POST"])
def toggle(rid):
    toggle_recipient(rid)
    flash("Estado del destinatario actualizado", "success")
    return redirect(url_for("dashboard.index"))


@recipients_bp.route("/recipients/<int:rid>/delete", methods=["POST"])
def delete(rid):
    delete_recipient(rid)
    flash("Destinatario eliminado", "success")
    return redirect(url_for("dashboard.index"))