"""
routes/api.py — Endpoints REST para consultas en tiempo real
"""

from flask import Blueprint, jsonify, request
from models.database import get_emails, get_stats
from services.worker import is_running

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/emails")
def emails():
    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    offset   = (page - 1) * per_page

    rows  = get_emails(limit=per_page, offset=offset)
    total = get_stats()["total"]

    return jsonify({
        "emails": rows,
        "total":  total,
        "page":   page,
        "pages":  -(-total // per_page)  # ceil division
    })


@api_bp.route("/stats")
def stats():
    data = get_stats()
    data["worker_running"] = is_running()
    return jsonify(data)