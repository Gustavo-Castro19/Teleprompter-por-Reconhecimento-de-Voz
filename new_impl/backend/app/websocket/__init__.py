from flask import Blueprint

ws_bp = Blueprint("websocket", __name__)

from app.websocket import handlers, audio_stream  # noqa