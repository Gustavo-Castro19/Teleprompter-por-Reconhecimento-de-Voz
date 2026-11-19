from typing import Literal

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
    presenter: str | None
    first_line_id: str | None
    order: int


class SlugScript(BaseModel):
    meta: ScriptMeta
    visual_lines: list[VisualLine]
    matching_words: list[MatchingWord]
    laudas: list[Lauda]
