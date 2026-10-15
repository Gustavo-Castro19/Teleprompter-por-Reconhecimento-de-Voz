from flask import request
from flask_socketio import emit, join_room, leave_room

from app.services import StateMachine, TeleprompterState, ScrollController, ScriptAligner, HybridSpeechRecognizer
from app.services.script_processor import ScriptProcessor
from app.utils.logger import EventLogger, get_logger

logger = get_logger(__name__)

# Global state (in production, use Redis for multi-worker)
state = StateMachine()
script_processor = ScriptProcessor()
speech_recognizer = HybridSpeechRecognizer()
scroll_controller: ScrollController | None = None
aligner: ScriptAligner | None = None
socketio = None


def init_websocket(sio):
    global socketio, scroll_controller, aligner
    socketio = sio

    # Load script
    logger.info("Loading script...")
    spoken, visual, mapping = script_processor.load_script()

    state.spoken_lines = spoken
    state.visual_lines = visual
    state.spoken_to_visual_map = mapping
    state.segments = script_processor.segments
    state.visual_metadata = script_processor.visual_metadata

    aligner = ScriptAligner(mapping, visual)
    scroll_controller = ScrollController(state, aligner, socketio)

    if not speech_recognizer.initialize_vosk():
        logger.warning("Vosk not initialized - Web Speech API only mode")

    logger.info("WebSocket handlers ready")


def emit_script_to_frontend():
    from flask import request
    first_visual = aligner.get_first_visual_index() if aligner else 0

    segments_frontend = [s.to_frontend() for s in state.segments]
    metadata_frontend = [m.to_frontend() for m in state.visual_metadata]
    scroll_config = calculate_scroll_config()

    emit(
        "roteiro",
        {
            "linhas": state.visual_lines,
            "indiceAtual": first_visual,
            "segmentos": segments_frontend,
            "metadadosLinhas": metadata_frontend,
            "configRolagem": scroll_config,
        },
    )

    emit("config_rolagem", scroll_config)

    emit(
        "cmd",
        {
            "index": first_visual,
            "type": "sync",
            "text": "",
            "segmento": None,
            "pausaAposSegundos": 0,
        },
    )

    emit_tp_display_config()
    emit_audio_devices()


def calculate_scroll_config():
    segments = state.segments
    visual_meta = state.visual_metadata

    speech_time = sum(s.estimated_time or 0.0 for s in segments)
    pause_time = sum(
        m.technical_pause_seconds or 0.0 for m in visual_meta
    ) + sum(s.pause_after_seconds or 0.0 for s in segments)

    total_words = sum(len(s.spoken_text.split()) for s in segments)

    return {
        "palavrasPorMinutoBase": 150,
        "totalPalavrasFalaveis": total_words,
        "totalSegmentosFalaveis": len(segments),
        "totalLinhasVisuais": len(state.visual_lines),
        "tempoTotalFalaSegundos": round(speech_time, 2),
        "tempoTotalPausasTecnicasSegundos": round(pause_time, 2),
        "tempoTotalEstimadoSegundos": round(speech_time + pause_time, 2),
        "origemDoTempo": "speakingTime_tapeTime_totalTime_json_com_fallback",
        "velocidadeMinima": 0.05,
        "velocidadeMaxima": 3.0,
    }


def emit_tp_display_config():
    config = {
        "maxWidthVw": 90,
        "maxHeightVh": 60,
        "aspectRatio": "4/3",
    }
    socketio.emit("config_tp_display", config)
    logger.info(f"[SOCKET] TP Display config sent: {config}")


def emit_audio_devices():
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

    socketio.emit("dispositivos_audio", {"dispositivos": devices})
    logger.info(f"[SOCKET] Audio devices sent: {len(devices)} found")


def emit_status():
    socketio.emit(
        "status_motor",
        {
            "estado": state.state.value,
            "correndo": state.running,
            "indiceAtual": state.current_spoken_index,
            "modoImproviso": state.is_improv(),
        }
    )


def emit_scroll_state(state_type: str, reason: str = "", pause_seconds: float = 0):
    socketio.emit(
        "estado_rolagem",
        {
            "tipo": state_type,
            "motivo": reason,
            "pausaSegundos": round(pause_seconds or 0.0, 2),
            "indiceFalado": state.current_spoken_index,
        }
    )


# SocketIO event handlers
def register_handlers(sio):
    init_websocket(sio)

    @sio.on("connect")
    def handle_connect(auth=None):
        EventLogger.client_connected()
        emit_script_to_frontend()
        emit_status()

    @sio.on("disconnect")
    def handle_disconnect():
        logger.info(f"Client disconnected: {request.sid}")

    @sio.on("iniciar_motor")
    def handle_start_engine():
        logger.info("[SOCKET] Engine start requested")
        state.running = True
        state.change_state(TeleprompterState.AUTOMATIC)
        emit_status()
        emit_scroll_state("AUTOMATICO", "Motor iniciado")

    @sio.on("solicitar_config_rolagem")
    def handle_request_scroll_config():
        socketio.emit("config_rolagem", calculate_scroll_config())

    @sio.on("manual_next")
    def handle_manual_next():
        target = state.current_spoken_index + 1
        if target < len(state.spoken_lines):
            scroll_controller.send_command(target, "next", "Avanço manual")
        emit_status()

    @sio.on("manual_prev")
    def handle_manual_prev():
        target = max(state.current_spoken_index - 1, 0)
        scroll_controller.send_command(target, "back", "Retorno manual")
        emit_status()

    @sio.on("pausar_motor")
    def handle_pause():
        if not state.is_finished():
            state.change_state(TeleprompterState.PAUSED)
            emit_scroll_state("PAUSADO", "Pausa manual")
        emit_status()

    @sio.on("retomar_motor")
    def handle_resume():
        if not state.is_finished():
            state.change_state(TeleprompterState.AUTOMATIC)
            emit_scroll_state("AUTOMATICO", "Retomada manual")
        emit_status()

    @sio.on("alternar_pausa")
    def handle_toggle_pause():
        if state.is_finished():
            emit_status()
            return

        if state.is_paused():
            state.change_state(TeleprompterState.AUTOMATIC)
            emit_scroll_state("AUTOMATICO", "Retomada manual")
        else:
            state.change_state(TeleprompterState.PAUSED)
            emit_scroll_state("PAUSADO", "Pausa manual")
        emit_status()

    @sio.on("solicitar_config_tp_display")
    def handle_request_tp_config():
        emit_tp_display_config()

    @sio.on("solicitar_dispositivos_audio")
    def handle_request_audio_devices():
        emit_audio_devices()

    # Speech recognition events from frontend
    @sio.on("speech_result")
    def handle_speech_result(data):
        """Handle Web Speech API results from frontend"""
        if not data:
            return

        text = data.get("text", "")
        is_final = data.get("isFinal", False)
        source = data.get("source", "web")
        confidence = data.get("confidence", 0.0)

        if source == "web":
            result = speech_recognizer.process_web_speech(text, is_final, confidence)
            _process_recognition_result(result)

    @sio.on("speech_audio")
    def handle_speech_audio(data):
        """Handle audio chunks for Vosk fallback"""
        if not data or "audio" not in data:
            return

        audio_b64 = data.get("audio")
        result = speech_recognizer.process_vosk_audio(audio_b64)
        _process_recognition_result(result)


def _process_recognition_result(result):
    if result.type == RecognitionType.ERROR:
        logger.error("Speech recognition error")
        return

    if result.type == RecognitionType.PARTIAL:
        scroll_controller.evaluate_partial(result.text, allow_advance=True)
    elif result.type == RecognitionType.FINAL:
        decision = scroll_controller.evaluate_final(result.text)
        if decision.should_advance and decision.target_index is not None:
            segment = decision.segment
            scroll_controller.send_command(
                decision.target_index,
                decision.event_type,
                segment.spoken_text if segment else ""
            )