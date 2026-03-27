# routes/auth.py - Rutas de autenticación: login y logout

from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash

from models.database import get_user_by_username
from models.user import User

auth_bp = Blueprint('auth', __name__)


# El decorador @route conecta la URL '/login' con la función login(). Acepta solicitudes GET y POST.
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Muestra el formulario de login y procesa las credenciales."""
    
    if request.method == 'POST': # Si el método es POST, significa que el usuario ha enviado el formulario de login.
        username = request.form.get('username').strip() # Obtiene el nombre de usuario del formulario.
        password = request.form.get('password').strip() # Obtiene la contraseña del formulario.
        
        # Busca el usuario en la base de datos por su nombre de usuario.
        row = get_user_by_username(username)
        
        if not row: # Si no se encuentra el usuario, muestra un mensaje de error.
            flash('Usuario no encontrado.', 'error')
            return redirect(url_for('auth.login'))
        
        # Comprueba si la contraseña proporcionada coincide con la contraseña almacenada (hash).
        if not check_password_hash(row['password'], password):
            flash('Contraseña incorrecta.', 'error')
            return redirect(url_for('auth.login'))
        
        # Crear objeto user e iniciar sesión
        user = User(id=row['id'], username=row['username'], password=row['password'])
        
        login_user(user)
        
        flash(f'Bienvenido, {user.username}!', 'success')
        return redirect(url_for('dashboard.index')) # Redirige al dashboard después de iniciar sesión.
    
    return render_template('login.html') # Si el método es GET, muestra el formulario de login.


@auth_bp.route('/logout')
@login_required
def logout():
    """Cerrar sesión del usuario."""
    logout_user() # Cierra la sesión del usuario.
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('auth.login')) # Redirige a la página de login después de cerrar sesión.