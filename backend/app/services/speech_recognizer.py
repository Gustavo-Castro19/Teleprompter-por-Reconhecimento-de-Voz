import os
import json
import base64
import logging
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from vosk import Model, KaldiRecognizer

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RecognitionSource(str, Enum):
    WEB_SPEECH = "web"
    VOSK = "vosk"


class RecognitionType(str, Enum):
    PARTIAL = "PARCIAL"
    FINAL = "FINAL"
    ERROR = "ERRO"


@dataclass
class RecognitionResult:
    type: RecognitionType
    text: str
    source: RecognitionSource
    confidence: float = 0.0


class VoskRecognizer:
    def __init__(self, model: Optional[Model] = None):
        self.model: Optional[Model] = model
        self.recognizer: Optional[KaldiRecognizer] = None
        self.sample_rate = settings.vosk_sample_rate

    def initialize(self) -> bool:
        model_path = settings.vosk_model_path
        if not os.path.exists(model_path):
            logger.error(f"Vosk model not found at: {model_path}")
            return False

        try:
            logger.info(f"Loading Vosk model from: {model_path}")
            if self.model is None:
                self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.Reset()
            logger.info("Vosk recognizer initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Vosk: {e}", exc_info=True)
            return False

    def process_audio(self, audio_data: bytes) -> RecognitionResult:
        if not self.recognizer:
            return RecognitionResult(RecognitionType.ERROR, "", RecognitionSource.VOSK)

        try:
            if self.recognizer.AcceptWaveform(audio_data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "")
                return RecognitionResult(RecognitionType.FINAL, text, RecognitionSource.VOSK)
            else:
                result = json.loads(self.recognizer.PartialResult())
                text = result.get("partial", "")
                return RecognitionResult(RecognitionType.PARTIAL, text, RecognitionSource.VOSK)
        except Exception as e:
            logger.error(f"Vosk processing error: {e}")
            return RecognitionResult(RecognitionType.ERROR, "", RecognitionSource.VOSK)

    def reset(self):
        if self.recognizer:
            self.recognizer.Reset()


class HybridSpeechRecognizer:
    """
    Hybrid speech recognition supporting:
    1. Web Speech API (browser-native, online) - primary
    2. Vosk (server-side, offline) - fallback
    
    The frontend decides which to use and sends results via SocketIO.
    This service handles Vosk processing for the fallback path.
    """

    def __init__(self, shared_model: Optional[Model] = None):
        self.vosk = VoskRecognizer(shared_model)
        self.vosk_ready = False

    def initialize_vosk(self) -> bool:
        self.vosk_ready = self.vosk.initialize()
        return self.vosk_ready

    def process_web_speech(self, text: str, is_final: bool, confidence: float = 0.0) -> RecognitionResult:
        """Process result from browser's Web Speech API"""
        return RecognitionResult(
            type=RecognitionType.FINAL if is_final else RecognitionType.PARTIAL,
            text=text,
            source=RecognitionSource.WEB_SPEECH,
            confidence=confidence
        )

    def process_vosk_audio(self, audio_base64: str) -> RecognitionResult:
        """Process audio chunk sent from frontend (base64 encoded)"""
        if not self.vosk_ready:
            return RecognitionResult(RecognitionType.ERROR, "", RecognitionSource.VOSK)

        try:
            audio_bytes = base64.b64decode(audio_base64)
            return self.vosk.process_audio(audio_bytes)
        except Exception as e:
            logger.error(f"Failed to decode/process audio: {e}")
            return RecognitionResult(RecognitionType.ERROR, "", RecognitionSource.VOSK)

    def reset_vosk(self):
        self.vosk.reset()

    def is_vosk_ready(self) -> bool:
        return self.vosk_ready
