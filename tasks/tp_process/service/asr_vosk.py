from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Callable

from common.paths import MODELS_DIR

from .script_loader import normalize_word

logger = logging.getLogger(__name__)

MODEL_DIR = MODELS_DIR / "model-pt"
SpokenHandler = Callable[[list[str], bool], None]


def _import_vosk() -> Any:
    """Importa Vosk sob demanda (exige DLLs no bundle PyInstaller)."""
    try:
        from vosk import KaldiRecognizer, Model, SetLogLevel
    except OSError as error:
        raise FileNotFoundError(
            "Falha ao carregar a biblioteca nativa do Vosk (libvosk). "
            "Isso NÃO é o modelo de idioma — regenere o exe com tp_process.spec "
            f"(DLLs do pacote vosk). Detalhe: {error}"
        ) from error
    except Exception as error:
        raise RuntimeError(f"Falha ao importar vosk: {error}") from error
    return KaldiRecognizer, Model, SetLogLevel


class VoskAsr:
    """ASR Vosk offline — processa chunks PCM e emite tokens normalizados."""

    def __init__(
        self,
        model_path: Path = MODEL_DIR,
        sample_rate: int = 16000,
        on_spoken: SpokenHandler | None = None,
    ) -> None:
        self._model_path = model_path
        self._sample_rate = sample_rate
        self._on_spoken = on_spoken
        self._model: Any = None
        self._recognizer: Any = None
        self._kaldi_cls: Any = None
        self._lock = threading.Lock()
        self._last_partial_tokens: list[str] = []

    @property
    def model_path(self) -> Path:
        return self._model_path

    def ensure_model(self) -> None:
        if self._model is not None:
            return
        if not self._model_path.exists():
            raise FileNotFoundError(
                f"Modelo Vosk não encontrado em {self._model_path}. "
                'Baixe o modelo pt-BR e renomeie a pasta para "model-pt".'
            )
        if not any(self._model_path.iterdir()):
            raise FileNotFoundError(
                f"Pasta do modelo Vosk está vazia: {self._model_path}"
            )

        KaldiRecognizer, Model, SetLogLevel = _import_vosk()
        self._kaldi_cls = KaldiRecognizer
        SetLogLevel(-1)
        logger.info("Carregando modelo Vosk: %s", self._model_path)
        self._model = Model(str(self._model_path))
        logger.info("Modelo Vosk carregado")

    def reset(self) -> None:
        with self._lock:
            self.ensure_model()
            assert self._model is not None and self._kaldi_cls is not None
            self._recognizer = self._kaldi_cls(self._model, self._sample_rate)
            self._recognizer.SetWords(True)
            self._last_partial_tokens = []

    def process_audio(self, chunk: bytes) -> None:
        if not chunk:
            return
        with self._lock:
            if self._recognizer is None:
                self.reset()
            assert self._recognizer is not None

            if self._recognizer.AcceptWaveform(chunk):
                payload = json.loads(self._recognizer.Result())
                tokens = tokenize_text(payload.get("text") or "")
                self._last_partial_tokens = []
                if tokens and self._on_spoken:
                    self._on_spoken(tokens, True)
                return

            payload = json.loads(self._recognizer.PartialResult())
            tokens = tokenize_text(payload.get("partial") or "")
            if tokens == self._last_partial_tokens:
                return
            self._last_partial_tokens = tokens
            if tokens and self._on_spoken:
                self._on_spoken(tokens, False)

    def close(self) -> None:
        with self._lock:
            self._recognizer = None
            self._last_partial_tokens = []


def tokenize_text(text: str) -> list[str]:
    parts = (text or "").split()
    return [normalize_word(part) for part in parts if normalize_word(part)]
