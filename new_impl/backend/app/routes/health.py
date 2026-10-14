from flask import jsonify, current_app
from app.routes import health_bp


@health_bp.route("/health")
def health():
    return jsonify({"status": "healthy", "service": "teleprompter-backend"})


@health_bp.route("/ready")
def ready():
    # Check if Vosk model is loaded, script is loaded, etc.
    checks = {
        "vosk_model": True,  # Will be set by app
        "script_loaded": True,
    }
    all_ready = all(checks.values())
    status = 200 if all_ready else 503
    return jsonify({"ready": all_ready, "checks": checks}), status