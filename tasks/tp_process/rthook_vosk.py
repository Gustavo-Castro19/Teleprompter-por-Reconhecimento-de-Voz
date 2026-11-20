"""Prepara pasta vosk/ + PATH para libvosk.dll no bundle PyInstaller."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_VOSK_DLLS = (
    "libvosk.dll",
    "libgcc_s_seh-1.dll",
    "libstdc++-6.dll",
    "libwinpthread-1.dll",
)


def _prepare_vosk_dlls() -> None:
    if not getattr(sys, "frozen", False):
        return
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return

    meipass = Path(base)
    vosk_dir = meipass / "vosk"
    vosk_dir.mkdir(parents=True, exist_ok=True)

    # Copia DLLs que tenham caído na raiz ou em subpastas para vosk/
    for dll_name in _VOSK_DLLS:
        dest = vosk_dir / dll_name
        if dest.exists():
            continue
        candidates = [meipass / dll_name, *meipass.rglob(dll_name)]
        for src in candidates:
            if src.is_file() and src.resolve() != dest.resolve():
                try:
                    shutil.copy2(src, dest)
                    break
                except OSError:
                    continue

    os.environ["PATH"] = str(vosk_dir) + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(vosk_dir))
        except OSError:
            pass
        try:
            os.add_dll_directory(str(meipass))
        except OSError:
            pass


_prepare_vosk_dlls()
