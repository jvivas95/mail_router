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


# Endpoint para obtener emails con paginación
@api_bp.route('/emails')
def emails():
    """Endpoint para obtener emails con paginación."""
    page = int(request.args.get('page', 1)) # Obtener el número de página de los parámetros de la URL, por defecto es 1
    per_page = int(request.args.get('per_page', 20)) # Obtener la cantidad de emails por página de los parámetros de la URL, por defecto es 20
    offset = (page -1) * per_page # Calcular el offset para la consulta a la base de datos
    
    rows = get_emails(limit=per_page, offset=offset) # Obtener los emails de la base de datos con el límite y offset calculados
    total = get_stats()['total'] # Obtener el total de emails para calcular el número total de páginas
    
    return jsonify({
        'emails': rows, # Lista de emails obtenidos
        'total': total, # Total de emails en la base de datos
        'page': page, # Página actual
        'pages': -(-total // per_page) # Calcular el número total de páginas (ceil division)
    })