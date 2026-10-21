from flask import request
from flask_socketio import emit, disconnect, join_room

from app.services import (
    TeleprompterState,
    ScrollController,
    HybridSpeechRecognizer,
    RecognitionType,
)
from app.models import ScriptSegment, VisualLineMeta
from app.services.bddf_processor import BddfPayloadError, process_bddf_request
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


def emit_script_to_frontend(session, target=None):
    first_visual = session.aligner.get_visual_index(session.state.current_spoken_index)

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
        to=target or request.sid,
    )

    emit("config_rolagem", scroll_config, to=target or request.sid)

    emit(
        "cmd",
        {
            "index": first_visual,
            "type": "sync",
            "text": "",
            "segmento": None,
            "pausaAposSegundos": 0,
        },
        to=target or request.sid,
    )

    emit_tp_display_config(session, target=target)


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


def emit_tp_display_config(session, target=None):
    config = {
        "maxWidthVw": 90,
        "maxHeightVh": 60,
        "aspectRatio": "4/3",
    }
    destination = target or request.sid
    socketio.emit("config_tp_display", config, to=destination)
    logger.info(f"[SOCKET] TP Display config sent to {destination}")


def emit_status(session):
    socketio.emit(
        "status_motor",
        {
            "estado": session.state.state.value,
            "correndo": session.state.running,
            "indiceAtual": session.state.current_spoken_index,
            "modoImproviso": session.state.is_improv(),
        },
        to=session.room_id,
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
        to=session.room_id,
    )


# Pydantic models for input validation
from pydantic import BaseModel


class SpeechResultData(BaseModel):
    text: str = ""
    isFinal: bool = False
    source: str = "web"
    confidence: float = 0.0


class SpeechAudioData(BaseModel):
    audio: str  # base64 encoded


def _load_processed_script(session, payload):
    parsed = process_bddf_request(payload)
    visual_lines = []
    visual_line_types = []
    spoken_lines = []
    spoken_to_visual = []
    segments = []
    visual_metadata = []
    processor = session.script_processor

    for program in parsed["programs"]:
        for block in program["blocks"]:
            for subblock in block["subblocks"]:
                is_technical = subblock["type"] == "technical"
                for line in subblock["lines"]:
                    visual_index = len(visual_lines)
                    line_type = processor.classify_visual_line(line) if is_technical else "fala"
                    visual_lines.append(line)
                    visual_line_types.append(line_type)

                    duration = 0.0
                    if not is_technical and processor.is_spoken_line(line):
                        spoken_index = len(spoken_lines)
                        duration = round(processor.estimate_reading_time(line), 2)
                        spoken_lines.append(line)
                        spoken_to_visual.append(visual_index)
                        segments.append(
                            ScriptSegment(
                                spoken_text=line,
                                visual_text=line,
                                spoken_index=spoken_index,
                                visual_index=visual_index,
                                estimated_time=duration,
                            )
                        )

                    visual_metadata.append(
                        VisualLineMeta(
                            visual_index=visual_index,
                            visual_text=line,
                            line_type=line_type,
                            duration_seconds=duration,
                            time_source="estimativa_por_palavras" if duration else "sem_tempo",
                        )
                    )

    if not visual_lines:
        raise BddfPayloadError("O arquivo não contém linhas de roteiro reconhecíveis.")
    if not spoken_lines:
        raise BddfPayloadError("O arquivo não contém falas reconhecíveis para acompanhar por voz.")

    state = session.state
    state.visual_lines = visual_lines
    state.visual_line_types = visual_line_types
    state.spoken_lines = spoken_lines
    state.spoken_to_visual_map = spoken_to_visual
    state.segments = segments
    state.visual_metadata = visual_metadata
    state.current_spoken_index = 0
    state.current_visual_index = spoken_to_visual[0] if spoken_to_visual else 0
    state.last_partial_text = ""
    state.partial_read_count = 0
    state.restart_partial_block = False
    state.discard_buffer = True
    state.last_advance_time = 0.0

    session.aligner.spoken_to_visual = spoken_to_visual
    session.aligner.visual_lines = visual_lines
    controller = session.scroll_controller
    controller.last_final_text = ""
    controller.last_partial_processed = ""
    session.speech_recognizer.reset_vosk()

    return len(visual_lines)


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
        if not token:
            logger.warning(f"Connection rejected: no auth token from {sid}")
            return False  # Reject connection

        room_id = (auth or {}).get("teleprompter_id") if isinstance(auth, dict) else None
        if not room_id or len(room_id) > 128:
            logger.warning(f"Connection rejected: no valid room id from {sid}")
            return False

        # Create or join this browser's shared teleprompter session.
        session = session_manager.create_session(sid, token, room_id)
        join_room(room_id)
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

    @sio.on("load_script")
    def handle_load_script(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return {"ok": False, "error": "Sessão indisponível."}
        if not isinstance(data, dict):
            return {"ok": False, "error": "Dados de arquivo inválidos."}
        if not _require_auth(data.get("token")):
            return {"ok": False, "error": "Autenticação inválida."}

        try:
            payload = data.get("payload")
            line_count = _load_processed_script(session, payload)
        except (BddfPayloadError, TypeError, ValueError) as error:
            logger.warning(f"Script upload rejected: {error}")
            return {"ok": False, "error": str(error)}

        if not session.state.is_paused():
            next_state = TeleprompterState.AUTOMATIC if session.state.running else TeleprompterState.WAITING
            session.state.change_state(next_state)
        emit_script_to_frontend(session, target=session.room_id)
        emit_status(session)
        return {"ok": True, "lineCount": line_count}

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

        if session.state.is_paused() or session.state.state == TeleprompterState.WAITING:
            was_waiting = session.state.state == TeleprompterState.WAITING
            session.state.running = True
            session.state.change_state(TeleprompterState.AUTOMATIC)
            reason = "Motor iniciado" if was_waiting else "Retomada manual"
            emit_scroll_state(session, "AUTOMATICO", reason)
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

    @sio.on("speech_start")
    def handle_speech_start(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return
        mode = (data or {}).get("mode", "web")
        ready = mode != "vosk" or session.speech_recognizer.is_vosk_ready()

        # Audio results are ignored while the state machine is WAITING. Starting
        # the microphone is the user's explicit request to begin voice tracking.
        if ready and session.state.state == TeleprompterState.WAITING:
            session.state.running = True
            session.state.change_state(TeleprompterState.AUTOMATIC)
            emit_status(session)
            emit_scroll_state(session, "AUTOMATICO", "Acompanhamento por voz iniciado")

        emit("speech_ready", {"mode": mode, "ready": ready}, to=request.sid)

    @sio.on("speech_stop")
    def handle_speech_stop(data=None):
        session = _get_session_or_disconnect()
        if not session:
            return
        if not _require_auth((data or {}).get("token") if data else None):
            return

        session.speech_recognizer.reset_vosk()

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
