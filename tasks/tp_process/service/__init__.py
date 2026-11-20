"""Serviços do tp_process.

Importações pesadas (engine/Vosk) ficam sob demanda para o executável
conseguir subir e reportar erros com clareza.
"""

from .models import parse_incoming

__all__ = ["parse_incoming", "TeleprompterEngine", "engine"]


def __getattr__(name: str):
    if name in {"TeleprompterEngine", "engine"}:
        from .engine import TeleprompterEngine, engine

        return TeleprompterEngine if name == "TeleprompterEngine" else engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
