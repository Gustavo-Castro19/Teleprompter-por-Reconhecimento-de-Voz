import os
from flask import Flask, send_from_directory
from flask_socketio import SocketIO

from app.config import get_settings
from app.routes import health_bp, scripts_bp, teleprompter_bp
from app.websocket.handlers import register_handlers
from app.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)
settings = get_settings()

socketio = SocketIO(
    cors_allowed_origins=settings.cors_allowed_origins,
    async_mode="eventlet",
    ping_timeout=60,
    ping_interval=25,
    logger=False,
    engineio_logger=False,
)


def create_app() -> Flask:
    setup_logging(
        level=settings.flask_env.upper() if settings.flask_env != "development" else "DEBUG",
        json_format=settings.flask_env == "production"
    )

    # Determine template and static folders
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
    )

    app.config["SECRET_KEY"] = settings.secret_key
    app.config["ENV"] = settings.flask_env

    app.register_blueprint(health_bp)
    app.register_blueprint(scripts_bp, url_prefix="/api")
    app.register_blueprint(teleprompter_bp)

    # Initialize SocketIO
    socketio.init_app(app)

    # Register WebSocket handlers
    register_handlers(socketio)

    # Health check endpoint for load balancers
    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    logger.info(f"App created in {settings.flask_env} mode")
    return app


def run_app():
    app = create_app()
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    socketio.run(
        app,
        host=settings.host,
        port=settings.port,
        debug=settings.flask_env == "development",
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )


if __name__ == "__main__":
    run_app()
