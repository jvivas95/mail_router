# config.py - Gestión de configuración
import json
import os

CONFIG_FILE = 'config.json'

# Valores predeterminados de configuración
DEFAULT_CONFIG = {
    "imap_host": "imap.gmail.com",
    "imap_port": 993,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "email_address": "zz5hunter5zz@gmail.com",
    "email_password": "sjlo cwby brjw fzgg",
    "check_interval": 60,
    "active": False
}

def load_config() -> dict:
    """ Leer el config.json. Si no existe, devuelve los valores por defecto."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            cfg = json.load(f)
            # Añadir claves nuevas que puedan faltar en versiones anteriores
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k,v)
            return cfg
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict) -> None:
    """ Guarda el diccionario de configuración en config.json. """
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2) # dump se encarga de convertir el diccionario a JSON y escribirlo en el archivo