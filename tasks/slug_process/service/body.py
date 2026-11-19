"""Extrai linhas e palavras do HTML do campo body (iNews).

- <p> / quebra de linha: fecha o segmento atual
- <pi> vizinhos no mesmo parágrafo: fundidos (comando partido pelo iNews)
- texto falado vs <pi>: segmentos separados
- <cc>: ignorado
- chaves { }: linha technical normalizada para {{comando}}
- <pi> sem chaves e separadores =====: descartados
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

from .models import LineContent

_WS = re.compile(r"\s+")
_SEPARATOR = re.compile(r"[=\s]+")
_BRACES = re.compile(r"[{}]")
_LINE_BREAKS = re.compile(r"[\r\n]+")
_WORD_SPLITS = re.compile(r"[-–—/]+")
_NON_WORD = re.compile(r"[\W_]+")


@dataclass(frozen=True)
class Segment:
    text: str
    is_instruction: bool


def parse_body(body: str) -> list[Segment]:
    parser = _BodyParser()
    parser.feed(body)
    parser.close()
    return parser.segments


def classify_segment(segment: Segment) -> LineContent | None:
    text = _collapse(segment.text)
    if not text or _SEPARATOR.fullmatch(text):
        return None

    if _BRACES.search(text):
        command = _collapse(_BRACES.sub("", text))
        return LineContent(type="technical", text=f"{{{{{command}}}}}") if command else None

    if segment.is_instruction:
        return None

    return LineContent(type="text", text=text)


def extract_words(text: str) -> list[tuple[str, int]]:
    """Retorna (palavra, índice_do_token_visível) para matching de voz."""
    words: list[tuple[str, int]] = []
    for index, token in enumerate(text.split()):
        for part in _WORD_SPLITS.split(token):
            word = _NON_WORD.sub("", part)
            if word:
                words.append((word, index))
    return words


def _collapse(text: str) -> str:
    return _WS.sub(" ", text).strip()


class _BodyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.segments: list[Segment] = []
        self._parts: list[str] = []
        self._parts_are_instruction = False
        self._in_instruction = 0
        self._in_ignored = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "p":
            self._flush()
        elif tag == "pi":
            self._in_instruction += 1
        elif tag == "cc":
            self._in_ignored += 1
        elif tag == "tab":
            self._append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "p":
            self._flush()
        elif tag == "pi":
            self._in_instruction = max(0, self._in_instruction - 1)
        elif tag == "cc":
            self._in_ignored = max(0, self._in_ignored - 1)

    def handle_startendtag(self, tag: str, attrs) -> None:
        if tag == "tab":
            self._append(" ")

    def handle_data(self, data: str) -> None:
        if self._in_ignored:
            return
        first, *rest = _LINE_BREAKS.split(data)
        self._append(first)
        for chunk in rest:
            self._flush()
            self._append(chunk)

    def close(self) -> None:
        super().close()
        self._flush()

    def _append(self, text: str) -> None:
        if not text:
            return

        is_instruction = self._in_instruction > 0
        if self._parts and is_instruction != self._parts_are_instruction and text.strip():
            self._flush()

        if not self._parts:
            self._parts_are_instruction = is_instruction
        self._parts.append(text)

    def _flush(self) -> None:
        text = "".join(self._parts)
        self._parts.clear()
        if text.strip():
            self.segments.append(Segment(text, self._parts_are_instruction))
