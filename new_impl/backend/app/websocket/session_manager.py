"""Per-session state management for multi-user support."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from app.services import StateMachine, TeleprompterState, ScrollController, ScriptAligner, HybridSpeechRecognizer
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
    created_at: float = field(default_factory=lambda: __import__('time').time())


class SessionManager:
    """Manages per-session state. In production with multiple workers, use Redis."""

    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._script_processor = ScriptProcessor()
        self._shared_speech_recognizer = HybridSpeechRecognizer()
        self._script_loaded = False

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

    def create_session(self, sid: str, auth_token: str) -> SessionData:
        """Create a new session with its own mutable state."""
        if not self._script_loaded:
            self.load_script_once()

        # Each session gets its own StateMachine (mutable)
        state = StateMachine()
        state.spoken_lines = self._default_spoken
        state.visual_lines = self._default_visual
        state.spoken_to_visual_map = self._default_mapping
        state.segments = self._default_segments
        state.visual_metadata = self._default_visual_metadata

        aligner = ScriptAligner(self._default_mapping, self._default_visual)
        scroll_controller = ScrollController(state, aligner, None)  # socketio set later

        # Share the Vosk recognizer (single model in memory)
        speech_recognizer = self._shared_speech_recognizer

        session = SessionData(
            sid=sid,
            state=state,
            script_processor=self._script_processor,
            speech_recognizer=speech_recognizer,
            scroll_controller=scroll_controller,
            aligner=aligner,
            auth_token=auth_token,
        )
        self._sessions[sid] = session
        logger.info(f"Created session {sid}")
        return session

    def get_session(self, sid: str) -> Optional[SessionData]:
        return self._sessions.get(sid)

    def remove_session(self, sid: str) -> None:
        if sid in self._sessions:
            del self._sessions[sid]
            logger.info(f"Removed session {sid}")

    def validate_token(self, sid: str, token: str) -> bool:
        session = self._sessions.get(sid)
        return session is not None and session.auth_token == token

    def set_socketio(self, socketio) -> None:
        """Inject socketio instance into all session controllers."""
        for session in self._sessions.values():
            session.scroll_controller.socketio = socketio


# Global session manager (single worker)
session_manager = SessionManager()