"""Per-session state management for multi-user support."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from app.services import StateMachine, ScrollController, ScriptAligner, HybridSpeechRecognizer
from app.services.script_processor import ScriptProcessor
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SessionData:
    """All state for a single teleprompter session."""
    sid: str
    state: StateMachine
    script_processor: ScriptProcessor
    speech_recognizer: HybridSpeechRecognizer
    scroll_controller: ScrollController
    aligner: ScriptAligner
    auth_token: str
    room_id: str
    sockets: set[str] = field(default_factory=set)
    created_at: float = field(default_factory=lambda: __import__('time').time())


class SessionManager:
    """Manages in-memory teleprompter rooms for this single worker."""

    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._rooms: Dict[str, SessionData] = {}
        self._script_processor = ScriptProcessor()
        self._shared_speech_recognizer = HybridSpeechRecognizer()
        self._script_loaded = False
        self._socketio = None

    @property
    def script_loaded(self) -> bool:
        return self._script_loaded

    def load_script_once(self) -> None:
        """Load script once and share across sessions (read-only data)."""
        if self._script_loaded:
            return
        logger.info("Loading script (shared across sessions)...")
        spoken, visual, mapping = self._script_processor.load_script()
        # Store as class-level defaults for new sessions
        self._default_spoken = spoken
        self._default_visual = visual
        self._default_mapping = mapping
        self._default_segments = self._script_processor.segments
        self._default_visual_metadata = self._script_processor.visual_metadata
        self._script_loaded = True
        logger.info("Script loaded and shared.")

    def create_session(self, sid: str, auth_token: str, room_id: str) -> SessionData:
        """Create a new session with its own mutable state."""
        if not self._script_loaded:
            self.load_script_once()

        existing = self._rooms.get(room_id)
        if existing and existing.auth_token == auth_token:
            existing.sockets.add(sid)
            self._sessions[sid] = existing
            return existing

        # Each browser teleprompter room has independent mutable state.
        state = StateMachine()
        state.spoken_lines = self._default_spoken
        state.visual_lines = self._default_visual
        state.spoken_to_visual_map = self._default_mapping
        state.segments = self._default_segments
        state.visual_metadata = self._default_visual_metadata

        aligner = ScriptAligner(self._default_mapping, self._default_visual)
        scroll_controller = ScrollController(state, aligner, self._socketio, room_id)

        # Decoder state is per room while the large immutable model is shared.
        speech_recognizer = HybridSpeechRecognizer(
            shared_model=self._shared_speech_recognizer.vosk.model
        )
        if self._shared_speech_recognizer.is_vosk_ready():
            speech_recognizer.initialize_vosk()

        session = SessionData(
            sid=sid,
            state=state,
            script_processor=self._script_processor,
            speech_recognizer=speech_recognizer,
            scroll_controller=scroll_controller,
            aligner=aligner,
            auth_token=auth_token,
            room_id=room_id,
            sockets={sid},
        )
        self._sessions[sid] = session
        self._rooms[room_id] = session
        logger.info(f"Created session {sid}")
        return session

    def get_session(self, sid: str) -> Optional[SessionData]:
        return self._sessions.get(sid)

    def remove_session(self, sid: str) -> None:
        if sid in self._sessions:
            session = self._sessions.pop(sid)
            session.sockets.discard(sid)
            if not session.sockets:
                self._rooms.pop(session.room_id, None)
            logger.info(f"Removed session {sid}")

    def validate_token(self, sid: str, token: str) -> bool:
        session = self._sessions.get(sid)
        return session is not None and session.auth_token == token

    def set_socketio(self, socketio) -> None:
        """Inject socketio instance into all session controllers."""
        self._socketio = socketio
        for session in self._sessions.values():
            session.scroll_controller.socketio = socketio


# Global session manager (single worker)
session_manager = SessionManager()
