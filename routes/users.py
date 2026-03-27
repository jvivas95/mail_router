# routes/users.py - Gestión de usuarios del siistema (solo admin)

import sqlite3
from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from functools import wraps

from models import create_user, delete_user, get_user_by_id

users_bp = Blueprint('users', __name__)


def admin_required(f):
    """Decorador que restringe el acceso a usuarios con rol admin.
    Si un 'user' intenta acceder, se le redirige al dashboard con un error
    """
    @wraps(f) # Mantiene la información de la función original
    def decorated(*args, **kwargs): # Verifica si el usuario actual está autenticado y tiene rol de admin
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Acceso denegado: Solo administradores pueden acceder a esta sección.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@users_bp.route('/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    """Ruta para agregar un nuevo usuario al sistema. Solo accesible por el admin.
    Recibe los datos del formulario, valida y crea el usuario en la base de datos.
    """
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()
    role = request.form.get('role', 'user').strip()  # Por defecto, el rol es 'user'
    
    if not username or not password:
        flash('Error: El nombre de usuario y la contraseña son obligatorios.', 'error')
        return redirect(url_for('dashboard.index'))
    
    if role not in ['admin', 'user']:
        flash('Error: Rol inválido. Debe ser "admin" o "user".', 'error')
        return redirect(url_for('dashboard.index'))
    
    try:
        create_user(username, generate_password_hash(password), role)
        flash(f'Usuario "{username}" creado exitosamente.', 'success')
    except sqlite3.IntegrityError:
        flash(f'Error: El nombre de usuario "{username}" ya existe.', 'error')
    
    return redirect(url_for('dashboard.index'))


@users_bp.route('/users/<int:uid>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(uid):
    """Ruta para eliminar un usuario del sistema. Solo accesible por el admin."""
    
    # Evita que el admin se elimine a sí mismo
    if uid == current_user.id:
        flash('Error: No puedes eliminar tu propia cuenta.', 'error')
        return redirect(url_for('dashboard.index'))
    
    user = get_user_by_id(uid)
    if not user:
        flash('Error: Usuario no encontrado.', 'error')
        return redirect(url_for('dashboard.index'))
    
    delete_user(uid)
    flash(f'Usuario "{user.username}" eliminado exitosamente.', 'success')
    return redirect(url_for('dashboard.index'))