"""
SoccerOctopus Flask application factory.
"""

import os

from flask import Flask
from flask_cors import CORS
from sqlalchemy import inspect

from .config import Config
from .db.base import db
from .runtime_settings import RuntimeSettingsService


def _sqlalchemy_engine_options(database_url: str) -> dict:
    if not database_url.startswith("postgresql"):
        return {}
    return {
        "pool_pre_ping": True,
        "connect_args": {"prepare_threshold": None},
    }


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if config_overrides:
        app.config.update(config_overrides)
    engine_options = _sqlalchemy_engine_options(app.config["SQLALCHEMY_DATABASE_URI"])
    if engine_options:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options
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
    from .api.billing import bp as billing_bp
    from .api.competitions import bp as competitions_bp
    from .api.markets import bp as markets_bp
    from .api.predictions import bp as predictions_bp
    from .api.webhooks import bp as webhooks_bp

    app.register_blueprint(predictions_bp)
    app.register_blueprint(markets_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(competitions_bp)
    app.register_blueprint(webhooks_bp)

    from .competitions.cli import sync_season_command

    app.cli.add_command(sync_season_command)

    @app.route("/health")
    def health():
        return {"status": "ok", "service": "FifaOctopus"}

    return app
