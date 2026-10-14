from flask_socketio import emit

from app.services.speech_recognizer import HybridSpeechRecognizer
from app.utils.logger import get_logger

logger = get_logger(__name__)

speech_recognizer = HybridSpeechRecognizer()


def register_audio_handlers(sio):
    @sio.on("audio_stream")
    def handle_audio_stream(data):
        """
        Handle binary audio stream from frontend for Vosk processing.
        Expected format: {"audio": base64_string, "sampleRate": 16000}
        """
        if not data or "audio" not in data:
            return

        audio_b64 = data["audio"]
        result = speech_recognizer.process_vosk_audio(audio_b64)

        if result.type.value == "ERRO":
            emit("speech_error", {"error": "Vosk processing failed", "fallback": True})
            return

        # Forward result to main handler
        sio.emit("speech_result", {
            "text": result.text,
            "isFinal": result.type.value == "FINAL",
            "source": result.source.value,
            "confidence": result.confidence,
        })

    @sio.on("speech_start")
    def handle_speech_start(data):
        """Initialize speech recognition session"""
        mode = data.get("mode", "web") if data else "web"
        language = data.get("language", "pt-BR") if data else "pt-BR"
        logger.info(f"Speech recognition started: mode={mode}, lang={language}")

        if mode == "vosk":
            if not speech_recognizer.is_vosk_ready():
                speech_recognizer.initialize_vosk()
            emit("speech_ready", {"mode": "vosk", "ready": speech_recognizer.is_vosk_ready()})
        else:
            emit("speech_ready", {"mode": "web", "ready": True})

    @sio.on("speech_stop")
    def handle_speech_stop():
        """Stop speech recognition session"""
        speech_recognizer.reset_vosk()
        logger.info("Speech recognition stopped")