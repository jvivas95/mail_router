# routes/api.py - Endpoints REST para actualización en tiempo real
"""
    Blueprint -> agrupa rutas relacionadas.
    jsonify -> convierte datos a formato JSON para respuestas API.
    request -> maneja datos de solicitudes entrantes.
"""
from flask import Blueprint, jsonify, request
from models.database import get_emails, get_stats
from services.worker import is_running

# Creación del Blueprint para agrupar todas las rutas de la API con un prefijo '/api'.
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Endpoint para obtener estadísticas en tiempo real
@api_bp.route('/stats')
def stats():
    """Endpoint para obtener estadísticas en tiempo real."""
    data = get_stats() # Obtenemos las estadísticas de la base de datos
    data['worker_running'] = is_running() # Agregamos el estado del worker a las estadísticas
    # jsonify convierte el dict a formato JSON y lo envía al navegador.
    return jsonify(data)