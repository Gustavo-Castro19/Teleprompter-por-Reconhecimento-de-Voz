"""Prepara espelhos BDDF para exibição no teleprompter."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


class BddfPayloadError(ValueError):
    """Indica que a requisição não possui a estrutura mínima esperada."""


_TECHNICAL_WORDS = (
    "ABRE SOM",
    "ABRE IMAG",
    "RODA VT",
    "RODA IMAGEM",
    "RODA IMAGENS",
    "VINHETA",
    "INTERVALO",
    "LINK NO AR",
    "IMAGENS//OFF",
    "GLOBODRONE",
    "LOCUTOR",
    "MOSAIC",
)


def process_bddf_request(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Retorna programas, blocos editoriais e subblocos do teleprompter."""

    return {
        "programs": [
            _build_program(program_payload)
            for program_payload in _get_program_payloads(payload)
        ]
    }


def _get_program_payloads(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        for key in ("programs", "programas"):
            if key in payload:
                programs = payload[key]
                if not isinstance(programs, Sequence) or isinstance(programs, (str, bytes)):
                    raise BddfPayloadError(f"'{key}' deve ser uma lista de programas.")
                return [
                    _ensure_mapping(program, f"{key}[{index}]")
                    for index, program in enumerate(programs)
                ]
        return [payload]

    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        return [
            _ensure_mapping(program, f"payload[{index}]")
            for index, program in enumerate(payload)
        ]

    raise BddfPayloadError("A requisição deve ser um objeto ou uma lista de objetos.")


def _build_program(program_payload: Mapping[str, Any]) -> dict[str, Any]:
    mirror = program_payload.get("mirror", {})
    mirror = _ensure_mapping(mirror, "mirror")

    raw_items = program_payload.get("slugs", program_payload.get("items"))
    if raw_items is None:
        raise BddfPayloadError("Cada programa deve possuir 'slugs' ou 'items'.")
    if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
        raise BddfPayloadError("'slugs'/'items' deve ser uma lista.")

    blocks: list[dict[str, Any]] = []
    program_name = _program_name(mirror, program_payload)
    for index, item in enumerate(raw_items):
        item_mapping = _ensure_mapping(item, f"slugs[{index}]")
        subblocks = _extract_subblocks(item_mapping.get("body", ""))
        if subblocks:
            blocks.append(
                {
                    "program_name": program_name,
                    "subblocks": subblocks,
                }
            )

    return {
        "name": program_name,
        "blocks": blocks,
    }


def _program_name(mirror: Mapping[str, Any], program: Mapping[str, Any]) -> str:
    for source in (mirror, program):
        for key in ("name", "shortName", "short_name", "title"):
            value = source.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
    return "Programa sem nome"


def _extract_subblocks(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    subblocks: list[dict[str, Any]] = []
    current_lines: list[str] = []
    current_type: str | None = None

    for raw_value in values:
        if not isinstance(raw_value, str):
            raw_value = str(raw_value)

        raw_parts = re.split(r"<pi\b[^>]*>\s*=+\s*</pi>", raw_value, flags=re.I)
        if len(raw_parts) == 1:
            raw_parts = re.split(r"(?m)^\s*=+\s*$", raw_value)

        for part_index, raw_part in enumerate(raw_parts):
            if part_index:
                _append_subblock(subblocks, current_type, current_lines)
                current_lines = []
                current_type = None

            lines = _extract_lines(raw_part)
            for line in lines:
                line_type = "technical" if _is_command(line) else "text"
                if current_type != line_type and current_lines:
                    _append_subblock(subblocks, current_type, current_lines)
                    current_lines = []
                current_type = line_type
                current_lines.append(line)

    _append_subblock(subblocks, current_type, current_lines)
    return subblocks


def _extract_lines(value: str) -> list[str]:
    lines: list[str] = []

    # pi pode conter instruções úteis para o operador, mas cc é áudio de
    # entrevista e não deve aparecer no texto do teleprompter.
    clean = re.sub(
        r"<cc\b[^>]*>.*?</cc>",
        "\n",
        value,
        flags=re.I | re.S,
    )
    clean = re.sub(
        r"<pi\b[^>]*>(.*?)</pi>",
        lambda match: _keep_command_or_remove(match.group(1)),
        clean,
        flags=re.I | re.S,
    )
    clean = re.sub(r"<[^>]+>", "\n", clean)
    clean = clean.replace("\r", "\n").replace("/", " ")
    clean = re.sub(r"\{\{.*?\}\}|\{.*?\}", lambda match: match.group(0), clean, flags=re.S)

    for line in clean.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line and not _is_technical_line(line):
            lines.append(line)
    return lines


def _append_subblock(
    subblocks: list[dict[str, Any]],
    subblock_type: str | None,
    lines: list[str],
) -> None:
    if subblock_type and lines:
        subblocks.append({"type": subblock_type, "lines": list(lines)})


def _is_technical_line(line: str) -> bool:
    if _is_command(line):
        return False
    if re.fullmatch(r"[=\-_/\\ ]+", line):
        return True
    if line.startswith(("[", "(")) and line.endswith(("]", ")")):
        return True
    upper_line = line.upper()
    return any(word in upper_line for word in _TECHNICAL_WORDS)


def _keep_command_or_remove(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = value.strip()
    return value if _is_command(value) else "\n"


def _is_command(value: str) -> bool:
    return bool(re.fullmatch(r"\{\{.*?\}\}", value.strip(), flags=re.S))


def _ensure_mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BddfPayloadError(f"'{location}' deve ser um objeto.")
    return value
