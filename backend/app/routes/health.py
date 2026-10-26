from flask import jsonify

from app.routes import health_bp
from app.websocket.session_manager import session_manager


@health_bp.route("/health")
def health():
    return jsonify({"status": "healthy", "service": "teleprompter-backend"})


@health_bp.route("/ready")
def ready():
    checks = {
        "vosk_model": session_manager._shared_speech_recognizer.is_vosk_ready(),
        "script_loaded": session_manager.script_loaded,
    }
    all_ready = all(checks.values())
    status = 200 if all_ready else 503
    return jsonify({"ready": all_ready, "checks": checks}), status
