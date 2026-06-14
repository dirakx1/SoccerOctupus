"""
FifaOctopus Flask application factory.
"""

import os

from flask import Flask
from flask_cors import CORS
from sqlalchemy import inspect

from .db.base import db
from .runtime_settings import RuntimeSettingsService
from .config import Config


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if config_overrides:
        app.config.update(config_overrides)
    CORS(app, resources={r"/api/*": {"origins": [Config.FRONTEND_ORIGIN]}})
    db.init_app(app)

    # Ensure directories
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.PREDICTIONS_DIR, exist_ok=True)

    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table("app_settings"):
            RuntimeSettingsService.ensure_defaults(db)

    # Register blueprints
    from .api.admin import bp as admin_bp
    from .api.predictions import bp as predictions_bp
    from .api.webhooks import bp as webhooks_bp
    app.register_blueprint(predictions_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(webhooks_bp)

    @app.route("/health")
    def health():
        return {"status": "ok", "service": "FifaOctopus"}

    return app
