from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Awaitable, Callable

from .asr_vosk import VoskAsr
from .audio_capture import AudioCapture
from .device_config import load_device_config
from .matcher import FollowState, ScriptMatcher
from .models import (
    MatchingWord,
    OperationalIn,
    OutgoingMessage,
    PositionJumpIn,
    PositionOut,
    StatusOut,
    VisualLine,
)
from .script_loader import (
    find_word_index_by_line,
    load_slug_script,
    script_words,
)

logger = logging.getLogger(__name__)

EmitHandler = Callable[[OutgoingMessage], Awaitable[None] | None]
SPOKEN_TAIL = 32


class TeleprompterEngine:
    """Orquestra captura → Vosk → matcher → eventos WebSocket."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._emit: EmitHandler | None = None
        self._matcher = ScriptMatcher()
        self._follow = FollowState()
        self._matching: list[MatchingWord] = []
        self._visual_lines: list[VisualLine] = []
        self._script_tokens: list[str] = []
        self._spoken_committed: list[str] = []
        self._active = False
        self._lock = threading.RLock()

        self._asr = VoskAsr(on_spoken=self._on_spoken)
        self._capture = AudioCapture(on_chunk=self._on_audio_chunk)

    @property
    def active(self) -> bool:
        return self._active

    def bind(self, loop: asyncio.AbstractEventLoop, emit: EmitHandler) -> None:
        self._loop = loop
        self._emit = emit

    def unbind(self) -> None:
        self.stop()
        self._emit = None
        self._loop = None

    def handle_message(self, message: OperationalIn | PositionJumpIn) -> list[OutgoingMessage]:
        if isinstance(message, OperationalIn):
            if message.state:
                return self.start(line_id=message.line_id)
            self.stop()
            return []
        return self.jump_to_line(message.line_id)

    def start(self, line_id: str | None = None) -> list[OutgoingMessage]:
        with self._lock:
            self._stop_unlocked()
            try:
                script = load_slug_script()
                self._matching = list(script.matching_words)
                self._visual_lines = list(script.visual_lines)
                self._script_tokens = script_words(self._matching)
                if not self._matching:
                    raise ValueError("matching_words vazio no roteiro")

                cursor = find_word_index_by_line(
                    self._matching,
                    line_id,
                    self._visual_lines,
                )
                self._follow = FollowState(cursor=cursor, improvising=False)
                self._matcher.reset()
                self._spoken_committed = []

                config = load_device_config()
                self._asr.reset()
                self._capture.start(config)

                self._active = True
                logger.info(
                    "Teleprompter ativo line_id=%s cursor=%s device_id=%s",
                    line_id,
                    cursor,
                    config.device_id,
                )

                outgoing: list[OutgoingMessage] = [
                    StatusOut(state="tracking"),
                ]
                if cursor > 0:
                    outgoing.append(self._position_for_index(cursor - 1))
                elif self._matching:
                    outgoing.append(self._position_for_index(0))
                return outgoing
            except Exception:
                self._stop_unlocked()
                raise

    def stop(self) -> None:
        with self._lock:
            self._stop_unlocked()

    def _stop_unlocked(self) -> None:
        was_active = self._active
        self._active = False
        self._capture.stop()
        self._asr.close()
        if was_active:
            logger.info("Teleprompter desativado")

    def jump_to_line(self, line_id: str) -> list[OutgoingMessage]:
        with self._lock:
            if not self._matching or not self._visual_lines:
                script = load_slug_script()
                self._matching = list(script.matching_words)
                self._visual_lines = list(script.visual_lines)
                self._script_tokens = script_words(self._matching)

            cursor = find_word_index_by_line(
                self._matching,
                line_id,
                self._visual_lines,
            )
            self._follow = FollowState(cursor=cursor, improvising=False)
            self._matcher.reset()
            self._spoken_committed = []
            logger.info("Salto de lauda para line_id=%s cursor=%s", line_id, cursor)

            outgoing: list[OutgoingMessage] = [StatusOut(state="tracking")]
            if self._matching:
                index = max(0, min(cursor, len(self._matching) - 1))
                if cursor > 0:
                    index = cursor - 1
                outgoing.append(self._position_for_index(index))
            return outgoing

    def _on_audio_chunk(self, chunk: bytes) -> None:
        if not self._active:
            return
        try:
            self._asr.process_audio(chunk)
        except Exception as error:
            logger.exception("Erro no ASR: %s", error)

    def _on_spoken(self, tokens: list[str], is_final: bool) -> None:
        if not self._active or not tokens:
            return

        with self._lock:
            if is_final:
                self._spoken_committed.extend(tokens)
                if len(self._spoken_committed) > SPOKEN_TAIL * 4:
                    self._spoken_committed = self._spoken_committed[-SPOKEN_TAIL * 2 :]
                spoken = self._spoken_committed[-SPOKEN_TAIL:]
            else:
                spoken = (self._spoken_committed + tokens)[-SPOKEN_TAIL:]

            previous_cursor = self._follow.cursor
            result = self._matcher.follow(
                self._script_tokens,
                spoken,
                self._follow,
            )
            self._follow = result.state

            messages: list[OutgoingMessage] = []
            if result.status_changed:
                state = "improvising" if result.state.improvising else "tracking"
                messages.append(StatusOut(state=state))
                logger.info("Status → %s", state)

            if (
                not result.state.improvising
                and result.state.cursor > previous_cursor
                and result.state.cursor > 0
            ):
                messages.append(self._position_for_index(result.state.cursor - 1))
                logger.info(
                    "Posição word_id=%s line_id=%s cursor=%s",
                    messages[-1].word_id if isinstance(messages[-1], PositionOut) else "?",
                    getattr(messages[-1], "line_id", "?"),
                    result.state.cursor,
                )

        for message in messages:
            self._emit_async(message)

    def _position_for_index(self, index: int) -> PositionOut:
        word = self._matching[max(0, min(index, len(self._matching) - 1))]
        return PositionOut(
            word_id=word.id,
            word_line_id=word.word_index_in_line,
            line_id=word.line_id,
        )

    def _emit_async(self, message: OutgoingMessage) -> None:
        loop = self._loop
        emit = self._emit
        if loop is None or emit is None:
            return

        def runner() -> None:
            try:
                result = emit(message)
                if asyncio.iscoroutine(result):
                    loop.create_task(result)
            except Exception as error:
                logger.warning("Falha ao emitir mensagem WS: %s", error)

        try:
            loop.call_soon_threadsafe(runner)
        except RuntimeError:
            logger.debug("Loop asyncio indisponível para emitir WS")


# Instância única do processo
engine = TeleprompterEngine()
