from flask import Blueprint

health_bp = Blueprint("health", __name__)
scripts_bp = Blueprint("scripts", __name__)
teleprompter_bp = Blueprint("teleprompter", __name__)

from app.routes import health, scripts, teleprompter  # noqa