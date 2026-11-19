"""Valida o arquivo enviado (.txt/.json) e devolve o espelho como dict."""

import json
from pathlib import PurePath
from typing import Any

from .errors import InvalidFileContentError, InvalidScriptStructureError, UnsupportedFileError

_ALLOWED = {".txt", ".json"}


def parse_uploaded_file(filename: str, raw: bytes) -> dict[str, Any]:
    extension = PurePath(filename).suffix.lower()
    if extension not in _ALLOWED:
        raise UnsupportedFileError(
            f"Extensão '{extension or 'sem extensão'}' não suportada. Use: {', '.join(sorted(_ALLOWED))}"
        )

    if not raw.strip():
        raise InvalidFileContentError("O arquivo está vazio")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InvalidFileContentError("O arquivo precisa estar codificado em UTF-8") from error

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise InvalidFileContentError(
            f"Conteúdo não é um JSON válido (linha {error.lineno}, coluna {error.colno})"
        ) from error

    if not isinstance(payload, dict):
        raise InvalidScriptStructureError("O JSON deve ser um objeto com 'mirror' e 'slugs'")

    mirror = payload.get("mirror")
    if mirror is not None and not isinstance(mirror, dict):
        raise InvalidScriptStructureError("'mirror' deve ser um objeto")

    slugs = payload.get("slugs")
    if not isinstance(slugs, list):
        raise InvalidScriptStructureError("'slugs' deve ser uma lista")

    for index, slug in enumerate(slugs):
        if not isinstance(slug, dict):
            raise InvalidScriptStructureError(f"'slugs[{index}]' deve ser um objeto")

    return payload
