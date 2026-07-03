from flask import Blueprint, jsonify, request

from app.db.yl import check_yl_db

bp = Blueprint("health", __name__, url_prefix="/api/v1")


@bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "yl_db": check_yl_db(),
            "mockup_db": "skip",
        }
    )
