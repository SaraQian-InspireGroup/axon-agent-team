from flask import Flask
from flask_cors import CORS

from app.config import settings
from app.routes.health import bp as health_bp
from app.routes.meta import bp as meta_bp
from app.routes.plan_transfer import bp as plan_transfer_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    origins = [o.strip() for o in settings.mockup_cors_origins.split(",") if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins or "*"}})

    app.register_blueprint(health_bp)
    app.register_blueprint(meta_bp)
    app.register_blueprint(plan_transfer_bp)

    return app
