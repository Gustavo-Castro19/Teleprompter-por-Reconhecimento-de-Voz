from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import time

from app.utils.logger import get_logger

logger = get_logger(__name__)


class TeleprompterState(str, Enum):
    AUTOMATIC = "AUTOMATICO"
    PAUSED = "PAUSADO"
    FINISHED = "FINALIZADO"
    FAILED = "FALHA"
    IMPROV = "IMPROVISO"
    VT_OR_LINK = "VT_OU_LINK"
    RECONNECTING_AUDIO = "RECONECTANDO_AUDIO"
    WAITING = "AGUARDANDO"


@dataclass
class StateMachine:
    spoken_lines: list[str] = field(default_factory=list)
    visual_lines: list[str] = field(default_factory=list)
    visual_line_types: list[str] = field(default_factory=list)
    spoken_to_visual_map: list[int] = field(default_factory=list)

    segments: list = field(default_factory=list)
    visual_metadata: list = field(default_factory=list)

    current_spoken_index: int = 0
    current_visual_index: int = 0

    state: TeleprompterState = TeleprompterState.WAITING
    running: bool = False

    audio_task = None

    last_advance_time: float = 0.0
    discard_buffer: bool = False

    last_partial_text: str = ""
    partial_read_count: int = 0
    restart_partial_block: bool = False

    last_improv_text: str = ""
    improv_start_time: Optional[float] = None

    def change_state(self, new_state: TeleprompterState) -> None:
        if new_state == self.state:
            return

        old_state = self.state
        self.state = new_state
        logger.info(f"State changed: {old_state.value} -> {new_state.value}")

    def is_automatic(self) -> bool:
        return self.state == TeleprompterState.AUTOMATIC

    def is_paused(self) -> bool:
        return self.state == TeleprompterState.PAUSED

    def is_finished(self) -> bool:
        return self.state == TeleprompterState.FINISHED

    def is_failed(self) -> bool:
        return self.state == TeleprompterState.FAILED

    def is_improv(self) -> bool:
        return self.state == TeleprompterState.IMPROV

    def is_vt_or_link(self) -> bool:
        return self.state == TeleprompterState.VT_OR_LINK

    def is_reconnecting_audio(self) -> bool:
        return self.state == TeleprompterState.RECONNECTING_AUDIO

    def can_evaluate_audio(self) -> bool:
        return self.state in (
            TeleprompterState.AUTOMATIC,
            TeleprompterState.IMPROV,
            TeleprompterState.VT_OR_LINK,
        )

    def advance_to(self, spoken_index: int) -> bool:
        if 0 <= spoken_index < len(self.spoken_lines):
            self.current_spoken_index = spoken_index
            if self.spoken_to_visual_map:
                self.current_visual_index = self.spoken_to_visual_map[spoken_index]
            self.last_advance_time = time.time()
            self.discard_buffer = True
            return True
        return False

    def go_back(self) -> bool:
        if self.current_spoken_index > 0:
            self.current_spoken_index -= 1
            if self.spoken_to_visual_map:
                self.current_visual_index = self.spoken_to_visual_map[self.current_spoken_index]
            self.last_advance_time = time.time()
            self.discard_buffer = True
            return True
        return False

    def reset_improv_tracking(self) -> None:
        self.last_improv_text = ""
        self.improv_start_time = None

    def update_improv_tracking(self, text: str) -> None:
        if not self.improv_start_time:
            self.improv_start_time = time.time()
        self.last_improv_text = text