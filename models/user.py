# models/user.py - Define la clase User para autenticación con Flask-Login

from flask_login import UserMixin
# UserMixin proporciona implementaciones por defecto de los métodos
# que flask-login necesita: is_authenticated, is_active, is_anonymous y get_id.

class User(UserMixin):
    """Clase User para autenticación con Flask-Login."""
    
    def __init__(self, id: int, username: str, role: str):
        """Inicializa un nuevo usuario."""
        self.id = id
        self.username = username
        self.role = role
    
    def is_admin(self) -> bool:
        """Método para verificar si el usuario es admin."""
        return self.role == 'admin'
    
    def get_id(self) -> str:
        """Devuelve el ID del usuario como string (requerido por Flask-Login)."""
        return str(self.id)