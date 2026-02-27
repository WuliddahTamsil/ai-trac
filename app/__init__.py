from flask import Flask
from .blueprints.main import main_bp
from .blueprints.dashboard import dashboard_bp
from .blueprints.control import control_bp
from .blueprints.ml import ml_bp
from .blueprints.analytics import analytics_bp
from .blueprints.telemetry import telemetry_bp
from .blueprints.maintenance import maintenance_bp
from .blueprints.history import history_bp
from .blueprints.settings import settings_bp
from .blueprints.api import api_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = 'aitrac-secret-2025'

    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(control_bp, url_prefix='/control')
    app.register_blueprint(ml_bp, url_prefix='/ml')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(telemetry_bp, url_prefix='/telemetry')
    app.register_blueprint(maintenance_bp, url_prefix='/maintenance')
    app.register_blueprint(history_bp, url_prefix='/history')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
