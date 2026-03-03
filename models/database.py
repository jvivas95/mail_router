import sqlite3
from datetime import datetime

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
            status TEXT DEFAULT 'pending'
        )
    ''')

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

    # Insertar fila de estado inicial si no existe
    c.execute(
            '''INSERT OR IGNORE INTO rotation_state VALUES (1, 0, ?)''',
            (datetime.now().isoformat(),)
        )

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

def get_active_recipients() -> list:
    """Función para obtener los destinatarios activos de la base de datos."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM recipients WHERE active = 1 ORDER BY order_index, id'
    ).fetchall() # fetchall() devuelve una lista de filas, cada una como un objeto Row que se puede convertir a dict
    conn.close()
    return [dict(r) for r in rows] # Convertir cada fila a dict para facilitar su uso en la aplicación