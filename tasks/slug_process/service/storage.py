import json
import os
import tempfile
from pathlib import Path

from common.paths import LOCAL_DIR

from .models import SlugScript

SLUG_SCRIPT_FILE = LOCAL_DIR / "slug_script.json"


def save_slug_script(script: SlugScript, destination: Path = SLUG_SCRIPT_FILE) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(script.model_dump(), ensure_ascii=False, indent=2)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.stem}-",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    try:
        os.replace(temp_path, destination)
    except OSError:
        temp_path.unlink(missing_ok=True)
        raise

    return destination
