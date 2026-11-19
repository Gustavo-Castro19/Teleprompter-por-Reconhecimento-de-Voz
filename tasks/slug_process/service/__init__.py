from pathlib import Path

from .builder import build_slug_script
from .errors import (
    InvalidFileContentError,
    InvalidScriptStructureError,
    ScriptImportError,
    UnsupportedFileError,
)
from .file_reader import parse_uploaded_file
from .models import SlugScript
from .storage import save_slug_script


def import_script_file(filename: str, raw: bytes) -> tuple[SlugScript, Path]:
    script = build_slug_script(parse_uploaded_file(filename, raw))
    return script, save_slug_script(script)


__all__ = [
    "InvalidFileContentError",
    "InvalidScriptStructureError",
    "ScriptImportError",
    "UnsupportedFileError",
    "import_script_file",
]
