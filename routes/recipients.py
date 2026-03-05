# routes/recipients.py - CRUD de destinatarios
"""
    Blueprint -> agrupa rutas relacionadas.
    request -> maneja datos de solicitudes entrantes.
    redirect -> redirige a otra ruta.
    url_for -> genera URLs para rutas.
    flash -> muestra mensajes temporales al usuario.
"""
import sqlite3
from flask import Blueprint, request, redirect, url_for, flash
from models.database import add_recipient, toggle_recipient, delete_recipient, update_recipient

# Creación del Blueprint para agrupar todas las rutas relacionadas con los destinatarios.
recipients_bp = Blueprint('recipients', __name__)

# El decorador @route conecta la URL '/recipients/add' con la función add(). Solo acepta solicitudes POST.
@recipients_bp.route('/recipients/add', methods=['POST']) # Ruta para agregar un nuevo destinatario. Solo acepta solicitudes POST.
def add():
    name = request.form.get('name', "").strip() # Obtenemos el nombre del formulario y lo limpiamos de espacios
    email = request.form.get('email', "").strip() # Obtenemos el email del formulario y lo limpiamos de espacios
    
    if not name or not email: # Validamos que se hayan ingresado ambos campos
        flash('Nombre y email son requeridos', 'error') # Mostramos un mensaje de error al usuario
        return redirect(url_for('dashboard.index')) # Redirigimos al dashboard
    
    try:
        add_recipient(name, email) # Intentamos agregar el destinatario a la base de datos
        flash(f'Destinatario {name} agregado', 'success') # Mostramos un mensaje de éxito al usuario
    except sqlite3.IntegrityError: # Si el email ya existe en la base de datos, se lanza una excepción de integridad
        flash('Email ya existe', 'error') # Mostramos un mensaje de error al usuario
    
    return redirect(url_for('dashboard.index')) # Redirigimos al dashboard


# El decorador @route conecta la URL '/recipients/<int:rid>/toggle' con la función toggle(). Solo acepta solicitudes POST.
@recipients_bp.route('/recipients/<int:rid>/toggle', methods=['POST']) # Ruta para activar/desactivar un destinatario. Solo acepta solicitudes POST.
def toggle(rid):
    toggle_recipient(rid) # Alternamos el estado del destinatario en la base de datos
    flash('Destinatario actualizado', 'success') # Mostramos un mensaje de éxito al usuario
    return redirect(url_for('dashboard.index')) # Redirigimos al dashboard


@recipients_bp.route('/recipients/<int:rid>/delete', methods=['POST']) # Ruta para eliminar un destinatario. Solo acepta solicitudes POST.
def delete(rid):
    delete_recipient(rid) # Eliminamos el destinatario de la base de datos
    flash('Destinatario eliminado', 'success') # Mostramos un mensaje de éxito al usuario
    return redirect(url_for('dashboard.index')) # Redirigimos al dashboard


# El decorador @route conecta la URL '/recipients/<int:rid>/update' con la función update(). Solo acepta solicitudes POST.
@recipients_bp.route('/recipients/<int:rid>/update', methods=['POST']) # Ruta para actualizar un destinatario. Solo acepta solicitudes POST.
def update(rid):
    name = request.form.get('name', "").strip() # Obtenemos el nuevo nombre del formulario y lo limpiamos de espacios
    email = request.form.get('email', "").strip() # Obtenemos el nuevo email del formulario y lo limpiamos de espacios
    
    if not name or not email: # Validamos que se hayan ingresado ambos campos
        flash('Nombre y email son requeridos', 'error') # Mostramos un mensaje de error al usuario
        return redirect(url_for('dashboard.index')) # Redirigimos al dashboard
    
    try:
        update_recipient(rid, name, email) # Intentamos actualizar el destinatario en la base de datos
        flash(f'Destinatario {name} actualizado', 'success') # Mostramos un mensaje de éxito al usuario
    except sqlite3.IntegrityError: # Si el nuevo email ya existe en la base de datos, se lanza una excepción de integridad
        flash('Email ya existe', 'error') # Mostramos un mensaje de error al usuario
    
    return redirect(url_for('dashboard.index')) # Redirigimos al dashboard