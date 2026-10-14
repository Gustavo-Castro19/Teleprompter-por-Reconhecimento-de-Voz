from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


@dataclass
class ComparisonResult:
    found: bool
    score: float = 0.0
    target_index: Optional[int] = None
    reason: str = ""


@dataclass
class SystemEvent:
    event_type: str
    text: str = ""
    current_index: int = 0
    note: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScriptSegment:
    spoken_text: str
    visual_text: str
    line_type: str = "fala"
    spoken_index: int = 0
    visual_index: int = 0

    estimated_time: Optional[float] = None
    time_source: str = "estimativa_por_palavras"

    presenter: Optional[str] = None
    title: Optional[str] = None
    page: Optional[str] = None
    item_type: Optional[str] = None
    slug_order: Optional[int] = None
    slug_id: Optional[str] = None

    speaking_time: float = 0.0
    tape_time: float = 0.0
    total_time: float = 0.0
    start_time: Optional[float] = None

    pause_after_seconds: float = 0.0
    pause_reason: str = ""

    def to_frontend(self) -> dict:
        return {
            "textoFalado": self.spoken_text,
            "textoVisual": self.visual_text,
            "tipoLinha": self.line_type,
            "indiceFalado": self.spoken_index,
            "indiceVisual": self.visual_index,
            "quantidadePalavras": len(self.spoken_text.split()),
            "tempoEstimadoSegundos": round(self.estimated_time or 0.0, 2),
            "origemTempo": self.time_source,
            "apresentador": self.presenter,
            "titulo": self.title,
            "pagina": self.page,
            "itemType": self.item_type,
            "ordemSlug": self.slug_order,
            "slugId": self.slug_id,
            "speakingTime": self.speaking_time,
            "tapeTime": self.tape_time,
            "totalTime": self.total_time,
            "startTime": self.start_time,
            "pausaAposSegundos": round(self.pause_after_seconds or 0.0, 2),
            "motivoPausa": self.pause_reason,
        }


@dataclass
class VisualLineMeta:
    visual_index: int
    visual_text: str
    line_type: str = "fala"

    title: Optional[str] = None
    page: Optional[str] = None
    item_type: Optional[str] = None
    slug_order: Optional[int] = None
    slug_id: Optional[str] = None

    speaking_time: float = 0.0
    tape_time: float = 0.0
    total_time: float = 0.0

    duration_seconds: float = 0.0
    time_source: str = "sem_tempo"
    technical_pause_seconds: float = 0.0
    pause_reason: str = ""

    def to_frontend(self) -> dict:
        return {
            "indiceVisual": self.visual_index,
            "textoVisual": self.visual_text,
            "tipoLinha": self.line_type,
            "titulo": self.title,
            "pagina": self.page,
            "itemType": self.item_type,
            "ordemSlug": self.slug_order,
            "slugId": self.slug_id,
            "speakingTime": self.speaking_time,
            "tapeTime": self.tape_time,
            "totalTime": self.total_time,
            "duracaoSegundos": round(self.duration_seconds or 0.0, 2),
            "origemTempo": self.time_source,
            "pausaTecnicaSegundos": round(self.technical_pause_seconds or 0.0, 2),
            "motivoPausa": self.pause_reason,
        }


@dataclass
class TeleprompterState:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_state: str = "AGUARDANDO"
    running: bool = False
    current_spoken_index: int = 0
    current_visual_index: int = 0
    improv_mode: bool = False
    discard_buffer: bool = False

    spoken_lines: list[str] = field(default_factory=list)
    visual_lines: list[str] = field(default_factory=list)
    visual_line_types: list[str] = field(default_factory=list)
    spoken_to_visual_map: list[int] = field(default_factory=list)

    segments: list[ScriptSegment] = field(default_factory=list)
    visual_metadata: list[VisualLineMeta] = field(default_factory=list)

    audio_process = None

    def is_automatic(self) -> bool:
        return self.current_state == "AUTOMATICO"

    def is_paused(self) -> bool:
        return self.current_state == "PAUSADO"

    def is_finished(self) -> bool:
        return self.current_state == "FINALIZADO"

    def is_failed(self) -> bool:
        return self.current_state == "FALHA"

    def is_improv(self) -> bool:
        return self.improv_mode

    def change_state(self, new_state: str) -> None:
        self.current_state = new_state
        if new_state == "IMPROVISO":
            self.improv_mode = True
        elif new_state == "AUTOMATICO":
            self.improv_mode = False