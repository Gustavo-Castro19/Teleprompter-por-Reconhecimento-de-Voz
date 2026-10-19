from dataclasses import dataclass
from typing import Optional


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
    start_time: Optional[str] = None
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
