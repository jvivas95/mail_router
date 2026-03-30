# models/database.py - Funciones para interactuar con la base de datos SQLite
import sqlite3 # Módulo para manejar bases de datos SQLite
from datetime import datetime # Módulo para manejar fechas y horas

from werkzeug.security import generate_password_hash # Función para generar hashes de contraseñas, utilizada para crear usuarios de forma segura

DB_FILE = 'mailrouter.db'

def get_db() -> sqlite3.Connection:
    """Abre y devuelve la conexión a la base de datos."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
    return conn

def init_db() -> None:
    """Crea las tablas si no existen. Se llama al iniciar la aplicación."""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT UNIQUE,
            sender TEXT,
            subject TEXT,
            date_received TEXT,
            body TEXT,
            forwarded_to TEXT,
            forwarded_at TEXT,
            status TEXT DEFAULT 'pending',
            attachments_count INTEGER DEFAULT 0
        )
    ''')
    
    # Agregar la columna attachments_count si no existe (para BDs existentes)
    try:
        c.execute('ALTER TABLE emails ADD COLUMN attachments_count INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # La columna ya existe, se ignora

    c.execute('''
        CREATE TABLE IF NOT EXISTS recipients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            active INTEGER DEFAULT 1,
            order_index INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS rotation_state (
            id INTEGER PRIMARY KEY DEFAULT 1,
            current_index INTEGER DEFAULT 0,
            last_updated TEXT
        )
    ''')

    # Insertar fila de estado inicial si no existe. Esto asegura que siempre haya una fila para manejar el estado de rotación.
    c.execute(
            '''INSERT OR IGNORE INTO rotation_state VALUES (1, 0, ?)''',
            (datetime.now().isoformat(),)
        )

    c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTERGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT
            )
    ''')

    conn.commit()
    conn.close()


# FUNCIONES DE CONSULTA

def get_emails(limit=50, offset=0) -> list:
    """Función para obtener los emails de la base de datos con paginación."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM emails ORDER BY date_received DESC LIMIT ? OFFSET ?',
        (limit, offset)
    ).fetchall() # fetchall() devuelve una lista de filas, cada una como un objeto Row que se puede convertir a dict
    conn.close()
    return [dict(r) for r in rows] # Convertir cada fila a dict para facilitar su uso en la aplicación


def get_email_by_id(eid: int) -> dict | None:
    """Función para obtener un email por su ID."""
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM emails WHERE id = ?',
        (eid,)
    ).fetchone() # fetchone() devuelve una sola fila o None si no hay resultados
    conn.close()
    return dict(row) if row else None # Convertir la fila a dict si existe, o devolver None


def get_stats() -> dict:
    """Función para obtener los estados de los mails."""
    conn = get_db()
    # Diccionario para almacenar los datos que se mostrarán en el dashboard. Se pueden agregar más estadísticas según sea necesario.
    stats = {
        'total': conn.execute('SELECT COUNT(*) FROM emails').fetchone()[0], # .fetchone()[0] devuelve el primer valor de la fila, que es el conteo total de emails
        'forwarded': conn.execute("SELECT COUNT(*) FROM emails WHERE status = 'forwarded'").fetchone()[0], # Conteo de emails con estado 'forwarded'
        'pending': conn.execute("SELECT COUNT(*) FROM emails WHERE status = 'pending'").fetchone()[0], # Conteo de emails con estado 'pending'
        'errors' : conn.execute("SELECT COUNT(*) FROM emails WHERE status = 'error'").fetchone()[0] # Conteo de emails con estado 'error'
    }
    conn.close()
    return stats # Devolvemos el diccionario con las estadísticas para que pueda ser utilizado en el dashboard o en la API


def get_all_recipients() -> list:
    """Función para obtener todos los destinatarios de la base de datos."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM recipients ORDER BY order_index ASC, id ASC'
    ).fetchall() # fetchall() devuelve una lista de filas, cada una como un objeto Row que se puede convertir a dict
    conn.close()
    return [dict(r) for r in rows] # Convertir cada fila a dict para facilitar su uso en la aplicación


def get_active_recipients() -> list:
    """Función para obtener solo los destinatarios activos de la base de datos."""
    return [r for r in get_all_recipients() if r['active']] # Filtrar solo los destinatarios activos para la rotación. Esto asegura que solo se consideren los destinatarios marcados como activos al seleccionar a quién reenviar los emails.


def add_recipient(name: str, email: str) -> bool:
    """Función para agregar un nuevo destinatario a la base de datos."""
    conn = get_db()
    max_idx = conn.execute('SELECT MAX(order_index) FROM recipients').fetchone()[0] or 0 # Obtener el índice máximo actual para asignar el siguiente índice de orden
    try:
        conn.execute(
            'INSERT INTO recipients (name, email, active, order_index, created_at) VALUES (?, ?, 1, ?, ?)',
            (name, email, max_idx +1, datetime.now().isoformat())
        )
        conn.commit()
        return True # Devolvemos True si la inserción fue exitosa
    except sqlite3.IntegrityError:
        return False # Devolvemos False si hubo un error de integridad (por ejemplo, email duplicado)
    finally:
        conn.close() # Aseguramos que la conexión se cierre en cualquier caso


def toggle_recipient(rid: int) -> None:
    """Función para activar o desactivar un destinatario."""
    conn = get_db()
    r = conn.execute('SELECT active FROM recipients WHERE id = ?', (rid,)).fetchone() # Obtener el estado actual del destinatario
    if r:
        conn.execute(
            'UPDATE recipients SET active = ? WHERE id = ?', # Cambiar el estado a 1 (activo) o 0 (inactivo) dependiendo del estado actual. Si está activo, se desactiva, y viceversa.
            (0 if r['active'] else 1, rid) # El operador ternario aquí evalúa r['active']. Si es 1 (activo), se convierte a 0 (inactivo). Si es 0 (inactivo), se convierte a 1 (activo).
        )
        conn.commit() # Guardar los cambios en la base de datos
    conn.close() # Cerrar la conexión a la base de datos


def delete_recipient(rid: int) -> None:
    """Función para eliminar un destinatario de la base de datos."""
    conn = get_db()
    conn.execute('DELETE FROM recipients WHERE id = ?',(rid,)) # Eliminar el destinatario con el ID especificado
    conn.commit() # Guardar los cambios en la base de datos
    conn.close() # Cerrar la conexión a la base de datos


def update_recipient(rid: int, name: str, email: str) -> bool:
    """Función para actualizar el nombre y correo de un destinatario."""
    conn = get_db()
    try:
        conn.execute(
            'UPDATE recipients SET name = ?, email = ? WHERE id = ?',
            (name, email, rid)
        )
        conn.commit()
        return True # Devolvemos True si la actualización fue exitosa
    except sqlite3.IntegrityError:
        return False # Devolvemos False si hubo un error de integridad (por ejemplo, email duplicado)
    finally:
        conn.close() # Aseguramos que la conexión se cierre en cualquier caso


def get_rotation_state() -> dict:
    """Función para obtener el estado actual de la rotación de destinatarios."""
    conn = get_db()
    row = conn.execute('SELECT * FROM rotation_state WHERE id = 1').fetchone() # Obtener la fila de estado de rotación (siempre con id=1)
    conn.close()
    return dict(row) if row else None # Convertir la fila a dict si existe, o devolver None


def set_rotation_state(idx: int) -> None:
    """Función para actualizar el índice actual de la rotación de destinatarios."""
    conn = get_db()
    conn.execute(
        'UPDATE rotation_state SET current_index = ?, last_updated = ? WHERE id = 1',
        (idx, datetime.now().isoformat())
    )
    conn.commit() # Guardar los cambios en la base de datos
    conn.close() # Cerrar la conexión a la base de datos


# FUNCIONES DE USUARIOS
def get_user_by_id(uid: int) -> dict | None:
    """Función para obtener un usuario por su ID."""
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM users WHERE id = ?',
        (uid,)).fetchone() # fetchone() devuelve una sola fila o None si no hay resultados
    conn.close()
    return dict(row) if row else None # Convertir la fila a dict si existe, o devolver None


def get_user_by_username(username: str) -> dict | None:
    """Función para obtener un usuario por su nombre de usuario."""
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM users WHERE username = ?',
        (username,)).fetchone() # fetchone() devuelve una sola fila o None si no hay resultados
    conn.close()
    return dict(row) if row else None # Convertir la fila a dict si existe, o devolver None


def get_all_users() -> list:
    """Función para obtener todos los usuarios de la base de datos."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM users ORDER BY id ASC'
    ).fetchall() # fetchall() devuelve una lista de filas, cada una como un objeto Row que se puede convertir a dict
    conn.close()
    return [dict(r) for r in rows] # Convertir cada fila a dict para facilitar su uso en la aplicación


def create_user(username: str, password_hash: str, role: str = 'user') -> None:
    """Función para crear un nuevo usuario en la base de datos."""
    conn = get_db()
    conn.execute(
        'INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)',
        (username, password_hash, role, datetime.now().isoformat())
    )
    conn.commit() # Guardar los cambios en la base de datos
    conn.close() # Cerrar la conexión a la base de datos


def delete_user(uid: int) -> None:
    """Función para eliminar un usuario de la base de datos."""
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id = ?',(uid,)) # Eliminar el usuario con el ID especificado
    conn.commit() # Guardar los cambios en la base de datos
    conn.close() # Cerrar la conexión a la base de datos


def create_default_admin():
    """Función para crear un usuario admin por defecto si no existe. Se llama al iniciar la aplicación."""
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] # Contar el número de usuarios existentes en la base de datos
    conn.close()
    if count == 0: # Si no hay usuarios, se crea un usuario admin por defecto
        create_user('admin', generate_password_hash('admin123'), 'admin') # Crear un usuario admin con nombre 'admin' y contraseña 'admin123'. Se recomienda cambiar esta contraseña después del primer inicio de sesión por razones de seguridad.