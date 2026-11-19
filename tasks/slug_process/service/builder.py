"""Monta o SlugScript a partir do espelho (mirror + slugs) já validado."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .body import classify_segment, extract_words, parse_body
from .models import Lauda, MatchingWord, ScriptMeta, SlugScript, VisualLine

_WS = re.compile(r"\s+")
_ALNUM = re.compile(r"[^\W_]")


def build_slug_script(payload: dict[str, Any]) -> SlugScript:
    slugs = sorted(payload["slugs"], key=_slug_order)
    visual_lines: list[VisualLine] = []
    matching_words: list[MatchingWord] = []
    laudas: list[Lauda] = []
    used_ids: set[str] = set()

    for order, slug in enumerate(slugs):
        lauda_id = _unique_lauda_id(slug.get("page"), order, used_ids)
        lines = _lines_from_body(lauda_id, slug.get("body"))

        laudas.append(
            Lauda(
                id=lauda_id,
                title=_title(slug),
                presenter=_presenter(slug.get("presenter")),
                first_line_id=lines[0].id if lines else None,
                order=order,
            )
        )
        visual_lines.extend(lines)

        for line in lines:
            if line.content.type != "text":
                continue
            for word, token_index in extract_words(line.content.text):
                matching_words.append(
                    MatchingWord(
                        id=len(matching_words),
                        word=word,
                        line_id=line.id,
                        word_index_in_line=token_index,
                    )
                )

    return SlugScript(
        meta=ScriptMeta(
            program_name=_program_name(payload.get("mirror") or {}, slugs),
            create_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            total_words=len(matching_words),
            total_lines=len(visual_lines),
            total_laudas=len(laudas),
        ),
        visual_lines=visual_lines,
        matching_words=matching_words,
        laudas=laudas,
    )


def _slug_order(slug: dict[str, Any]) -> float:
    try:
        return float(slug.get("order"))
    except (TypeError, ValueError):
        return float("inf")


def _unique_lauda_id(page: Any, order: int, used_ids: set[str]) -> str:
    base = _WS.sub("", str(page or "")).upper() or f"SEM_PG_{order}"
    lauda_id = base
    suffix = 2
    while lauda_id in used_ids:
        lauda_id = f"{base}_{suffix}"
        suffix += 1
    used_ids.add(lauda_id)
    return lauda_id


def _presenter(value: Any) -> str | None:
    presenter = _WS.sub("", str(value or ""))
    return presenter if _ALNUM.search(presenter) else None


def _title(slug: dict[str, Any]) -> str:
    title = _collapse(str(slug.get("title") or ""))
    if title:
        return title

    for field in slug.get("extraFields") or []:
        if isinstance(field, dict) and field.get("label") == "RETRANCA":
            return _collapse(str(field.get("value") or ""))
    return ""


def _lines_from_body(lauda_id: str, body: Any) -> list[VisualLine]:
    if not isinstance(body, str):
        return []

    lines: list[VisualLine] = []
    for segment in parse_body(body):
        content = classify_segment(segment)
        if content is None:
            continue
        lines.append(
            VisualLine(
                id=f"{lauda_id}-{len(lines) + 1}",
                lauda_id=lauda_id,
                content=content,
            )
        )
    return lines


def _program_name(mirror: dict[str, Any], slugs: list[dict[str, Any]]) -> str:
    for candidate in (mirror.get("path"), slugs[0].get("path") if slugs else None):
        name = str(candidate or "").strip()
        if name:
            return name
    return ""


def _collapse(text: str) -> str:
    return _WS.sub(" ", text).strip()
