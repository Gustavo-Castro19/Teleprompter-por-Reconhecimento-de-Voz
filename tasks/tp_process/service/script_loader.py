from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path

from common.paths import LOCAL_DIR

from .models import MatchingWord, SlugScript, VisualLine

logger = logging.getLogger(__name__)

SLUG_SCRIPT_FILE = LOCAL_DIR / "slug_script.json"
_WORD_CLEAN = re.compile(r"[^\wÀ-ÿ]+", re.UNICODE)


def normalize_word(word: str) -> str:
    text = unicodedata.normalize("NFC", word or "").strip().lower()
    text = _WORD_CLEAN.sub("", text)
    return text


def load_slug_script(path: Path | None = None) -> SlugScript:
    target = path or SLUG_SCRIPT_FILE
    if not target.exists():
        raise FileNotFoundError(f"Roteiro não encontrado: {target}")

    raw = json.loads(target.read_text(encoding="utf-8"))
    script = SlugScript.model_validate(raw)
    logger.info(
        "Roteiro carregado: %s (%s palavras, %s linhas)",
        script.meta.program_name,
        script.meta.total_words,
        script.meta.total_lines,
    )
    return script


def script_words(matching: list[MatchingWord]) -> list[str]:
    return [normalize_word(item.word) for item in matching]


def find_word_index_by_line(
    matching: list[MatchingWord],
    line_id: str | None,
    visual_lines: list[VisualLine] | None = None,
) -> int:
    """Resolve line_id para índice em matching_words.

    Linhas técnicas (ex.: 0A-1) não têm palavras — avança para a próxima
    linha de texto na ordem de visual_lines.
    """
    if not line_id:
        return 0

    for index, item in enumerate(matching):
        if item.line_id == line_id:
            return index

    if not visual_lines:
        raise ValueError(f"line_id não encontrado no matching_words: {line_id!r}")

    line_order = {line.id: index for index, line in enumerate(visual_lines)}
    start_order = line_order.get(line_id)

    if start_order is None:
        # Aceita lauda_id (ex.: "0A") → primeira linha visual dessa lauda
        for index, line in enumerate(visual_lines):
            if line.lauda_id == line_id:
                start_order = index
                break

    if start_order is None:
        raise ValueError(f"line_id não encontrado no roteiro: {line_id!r}")

    for index, item in enumerate(matching):
        item_order = line_order.get(item.line_id)
        if item_order is not None and item_order >= start_order:
            logger.info(
                "line_id=%r sem matching — cursor na próxima linha falada %r (word index %s)",
                line_id,
                item.line_id,
                index,
            )
            return index

    raise ValueError(
        f"Nenhuma palavra falável após line_id={line_id!r} no matching_words"
    )
