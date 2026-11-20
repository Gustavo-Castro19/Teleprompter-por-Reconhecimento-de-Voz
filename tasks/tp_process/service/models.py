from typing import Any, Literal

from pydantic import BaseModel


class ScriptMeta(BaseModel):
    program_name: str
    create_at: str
    total_words: int
    total_lines: int
    total_laudas: int


class LineContent(BaseModel):
    type: Literal["text", "technical"]
    text: str


class VisualLine(BaseModel):
    id: str
    lauda_id: str
    content: LineContent


class MatchingWord(BaseModel):
    id: int
    word: str
    line_id: str
    word_index_in_line: int


class Lauda(BaseModel):
    id: str
    title: str
    presenter: str | None = None
    first_line_id: str | None = None
    order: int


class SlugScript(BaseModel):
    meta: ScriptMeta
    visual_lines: list[VisualLine]
    matching_words: list[MatchingWord]
    laudas: list[Lauda]


class DeviceConfig(BaseModel):
    device_id: int | None = None
    name: str = "default"
    sample_rate: int = 16000
    channels: int = 1


class DeviceInfo(BaseModel):
    id: int
    name: str
    channels: int
    default_samplerate: float
    is_default: bool = False


class DeviceSelectRequest(BaseModel):
    device_id: int | None = None


class PositionOut(BaseModel):
    type: Literal["position"] = "position"
    word_id: int
    word_line_id: int
    line_id: str


class StatusOut(BaseModel):
    type: Literal["status"] = "status"
    state: Literal["improvising", "tracking"]


class PositionJumpIn(BaseModel):
    type: Literal["position"]
    line_id: str
    page: str | None = None
    is_page_jump: bool = True


class OperationalIn(BaseModel):
    type: Literal["operational"]
    state: bool
    line_id: str | None = None


OutgoingMessage = PositionOut | StatusOut
IncomingMessage = PositionJumpIn | OperationalIn


def parse_incoming(raw: dict[str, Any]) -> IncomingMessage:
    msg_type = raw.get("type")
    if msg_type == "operational":
        return OperationalIn.model_validate(raw)
    if msg_type == "position":
        return PositionJumpIn.model_validate(raw)
    raise ValueError(f"Tipo de mensagem desconhecido: {msg_type!r}")
