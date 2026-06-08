"""
FifaOctopus Flask application factory.
"""

import os

from flask import Flask
from flask_cors import CORS

from .config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Ensure directories
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.PREDICTIONS_DIR, exist_ok=True)

    # Register blueprints
    from .api.predictions import bp as predictions_bp
    from .api.markets import bp as markets_bp
    app.register_blueprint(predictions_bp)
    app.register_blueprint(markets_bp)

    @app.route("/health")
    def health():
        return {"status": "ok", "service": "FifaOctopus"}

    return app
