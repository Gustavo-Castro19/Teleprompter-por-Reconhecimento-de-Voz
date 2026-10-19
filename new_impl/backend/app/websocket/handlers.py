from flask import request
from flask_socketio import emit, disconnect

from app.services import (
    TeleprompterState,
    ScrollController,
    HybridSpeechRecognizer,
    RecognitionType,
)
from app.utils.logger import EventLogger, get_logger
from app.websocket.session_manager import session_manager

logger = get_logger(__name__)

socketio = None


def init_websocket(sio):
    global socketio
    socketio = sio

    # Load script once (shared read-only data)
    session_manager.load_script_once()

    # Initialize shared Vosk recognizer
    if not session_manager._shared_speech_recognizer.initialize_vosk():
        logger.warning("Vosk not initialized - Web Speech API only mode")

    # Inject socketio into session manager for later session creation
    session_manager.set_socketio(socketio)

    logger.info("WebSocket handlers ready")


def is_vosk_ready() -> bool:
    """Check if Vosk model is loaded and ready."""
    return session_manager._shared_speech_recognizer.is_vosk_ready()


def _get_session_or_disconnect() -> "SessionData | None":
    """Get session for current request.sid, disconnect if invalid."""
    sid = request.sid
    session = session_manager.get_session(sid)
    if not session:
        logger.warning(f"No session found for {sid}, disconnecting")
        disconnect()
        return None
    return session


def _require_auth(token: str | None) -> bool:
    """Validate auth token for current session."""
    sid = request.sid
    if not session_manager.validate_token(sid, token or ""):
        logger.warning(f"Invalid auth token for {sid}")
        disconnect()
        return False
    return True


def emit_script_to_frontend(session):
    first_visual = session.aligner.get_first_visual_index()

    segments_frontend = [s.to_frontend() for s in session.state.segments]
    metadata_frontend = [m.to_frontend() for m in session.state.visual_metadata]
    scroll_config = calculate_scroll_config(session)

    emit(
        "roteiro",
        {
            "linhas": session.state.visual_lines,
            "indiceAtual": first_visual,
            "segmentos": segments_frontend,
            "metadadosLinhas": metadata_frontend,
            "configRolagem": scroll_config,
        },
        to=request.sid,
    )

    emit("config_rolagem", scroll_config, to=request.sid)

    emit(
        "cmd",
        {
            "index": first_visual,
            "type": "sync",
            "text": "",
            "segmento": None,
            "pausaAposSegundos": 0,
        },
        to=request.sid,
    )

    emit_tp_display_config(session)
    emit_audio_devices(session)


def calculate_scroll_config(session):
    segments = session.state.segments
    visual_meta = session.state.visual_metadata

    speech_time = sum(s.estimated_time or 0.0 for s in segments)
    pause_time = sum(
        m.technical_pause_seconds or 0.0 for m in visual_meta
    ) + sum(s.pause_after_seconds or 0.0 for s in segments)

    total_words = sum(len(s.spoken_text.split()) for s in segments)

    return {
        "palavrasPorMinutoBase": 150,
        "totalPalavrasFalaveis": total_words,
        "totalSegmentosFalaveis": len(segments),
        "totalLinhasVisuais": len(session.state.visual_lines),
        "tempoTotalFalaSegundos": round(speech_time, 2),
        "tempoTotalPausasTecnicasSegundos": round(pause_time, 2),
        "tempoTotalEstimadoSegundos": round(speech_time + pause_time, 2),
        "origemDoTempo": "speakingTime_tapeTime_totalTime_json_com_fallback",
        "velocidadeMinima": 0.05,
        "velocidadeMaxima": 3.0,
    }


def emit_tp_display_config(session):
    config = {
        "maxWidthVw": 90,
        "maxHeightVh": 60,
        "aspectRatio": "4/3",
    }
    socketio.emit("config_tp_display", config, to=request.sid)
    logger.info(f"[SOCKET] TP Display config sent to {request.sid}")


def emit_audio_devices(session):
    # In web version, audio comes from browser, not server
    # But we can still list server devices for fallback
    from app.services import AudioManager
    audio_mgr = AudioManager()
    try:
        devices = [d.to_dict() for d in audio_mgr.list_devices()]
    except Exception as e:
        logger.error(f"Failed to list audio devices: {e}")
        devices = []
    finally:
        audio_mgr.close_microphone()

    socketio.emit("dispositivos_audio", {"dispositivos": devices}, to=request.sid)
    logger.info(f"[SOCKET] Audio devices sent to {request.sid}: {len(devices)} found")


def emit_status(session):
    socketio.emit(
        "status_motor",
        {
            "estado": session.state.state.value,
            "correndo": session.state.running,
            "indiceAtual": session.state.current_spoken_index,
            "modoImproviso": session.state.is_improv(),
        },
        to=request.sid,
    )


def emit_scroll_state(session, state_type: str, reason: str = "", pause_seconds: float = 0):
    socketio.emit(
        "estado_rolagem",
        {
            "tipo": state_type,
            "motivo": reason,
            "pausaSegundos": round(pause_seconds or 0.0, 2),
            "indiceFalado": session.state.current_spoken_index,
        },
        to=request.sid,
    )


# Pydantic models for input validation
from pydantic import BaseModel, Field
from typing import Optional


class SpeechResultData(BaseModel):
    text: str = ""
    isFinal: bool = False
    source: str = "web"
    confidence: float = 0.0


class SpeechAudioData(BaseModel):
    audio: str  # base64 encoded


class SelectAudioDeviceData(BaseModel):
    device_index: str | int  # "auto" or int


# SocketIO event handlers
def register_handlers(sio):
    init_websocket(sio)

    @sio.on("connect")
    def handle_connect(auth=None):
        sid = request.sid
        # Auth token must be provided in auth dict or query string
        token = None
        if auth and isinstance(auth, dict):
            token = auth.get("token")
        # Fallback: read from query string (Socket.IO puts query params in request.args)
        if not token:
            token = request.args.get("token")

        if not token:
            logger.warning(f"Connection rejected: no auth token from {sid}")
            return False  # Reject connection

        # Create session with validated token
        session = session_manager.create_session(sid, token)
        EventLogger.client_connected()
        emit_script_to_frontend(session)
        emit_status(session)

    @sio.on("disconnect")
    def handle_disconnect():
        sid = request.sid
        logger.info(f"Client disconnected: {sid}")
        session_manager.remove_session(sid)

    @sio.on("iniciar_motor")
    def handle_start_engine(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return

        logger.info(f"[SOCKET] Engine start requested by {request.sid}")
        session.state.running = True
        session.state.change_state(TeleprompterState.AUTOMATIC)
        emit_status(session)
        emit_scroll_state(session, "AUTOMATICO", "Motor iniciado")

    @sio.on("solicitar_config_rolagem")
    def handle_request_scroll_config(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return
        emit("config_rolagem", calculate_scroll_config(session), to=request.sid)

    @sio.on("manual_next")
    def handle_manual_next(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return

        target = session.state.current_spoken_index + 1
        if target < len(session.state.spoken_lines):
            session.scroll_controller.send_command(target, "next", "Avanço manual")
        emit_status(session)

    @sio.on("manual_prev")
    def handle_manual_prev(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return

        target = max(session.state.current_spoken_index - 1, 0)
        session.scroll_controller.send_command(target, "back", "Retorno manual")
        emit_status(session)

    @sio.on("pausar_motor")
    def handle_pause(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return

        if not session.state.is_finished():
            session.state.change_state(TeleprompterState.PAUSED)
            emit_scroll_state(session, "PAUSADO", "Pausa manual")
        emit_status(session)

    @sio.on("retomar_motor")
    def handle_resume(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return

        if not session.state.is_finished():
            session.state.change_state(TeleprompterState.AUTOMATIC)
            emit_scroll_state(session, "AUTOMATICO", "Retomada manual")
        emit_status(session)

    @sio.on("alternar_pausa")
    def handle_toggle_pause(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return

        if session.state.is_finished():
            emit_status(session)
            return

        if session.state.is_paused():
            session.state.change_state(TeleprompterState.AUTOMATIC)
            emit_scroll_state(session, "AUTOMATICO", "Retomada manual")
        else:
            session.state.change_state(TeleprompterState.PAUSED)
            emit_scroll_state(session, "PAUSADO", "Pausa manual")
        emit_status(session)

    @sio.on("solicitar_config_tp_display")
    def handle_request_tp_config(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return
        emit_tp_display_config(session)

    @sio.on("solicitar_dispositivos_audio")
    def handle_request_audio_devices(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return
        emit_audio_devices(session)

    @sio.on("selecionar_dispositivo_audio")
    def handle_select_audio_device(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return

        # Validate input
        try:
            payload = SelectAudioDeviceData.model_validate(data or {})
        except Exception as e:
            logger.warning(f"Invalid audio device payload: {e}")
            return

        # For web version, audio is captured in browser; this is a no-op
        # but we acknowledge the request
        logger.info(f"Audio device selection requested: {payload.device_index} (web mode - ignored)")
        emit_audio_devices(session)

    # Speech recognition events from frontend
    @sio.on("speech_result")
    def handle_speech_result(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return

        try:
            payload = SpeechResultData.model_validate(data or {})
        except Exception as e:
            logger.warning(f"Invalid speech_result payload: {e}")
            return

        if payload.source == "web":
            result = session.speech_recognizer.process_web_speech(
                payload.text, payload.isFinal, payload.confidence
            )
            _process_recognition_result(session, result)

    @sio.on("speech_audio")
    def handle_speech_audio(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return

        try:
            payload = SpeechAudioData.model_validate(data or {})
        except Exception as e:
            logger.warning(f"Invalid speech_audio payload: {e}")
            return

        result = session.speech_recognizer.process_vosk_audio(payload.audio)
        _process_recognition_result(session, result)


def _process_recognition_result(session, result):
    if result.type == RecognitionType.ERROR:
        logger.error("Speech recognition error")
        return

    if result.type == RecognitionType.PARTIAL:
        session.scroll_controller.evaluate_partial(result.text, allow_advance=True)
    elif result.type == RecognitionType.FINAL:
        decision = session.scroll_controller.evaluate_final(result.text)
        if decision.should_advance and decision.target_index is not None:
            segment = decision.segment
            session.scroll_controller.send_command(
                decision.target_index,
                decision.event_type,
                segment.spoken_text if segment else ""
            )