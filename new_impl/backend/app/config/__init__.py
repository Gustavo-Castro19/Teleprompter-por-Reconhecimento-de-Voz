from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Flask
    secret_key: str = "squad29_dev_key"
    flask_env: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Vosk
    vosk_model_path: str = "/app/models/vosk-model-pt"
    vosk_sample_rate: int = 16000

    # Audio
    audio_device_index: int | None = None
    audio_chunk_size: int = 4096
    audio_format: int = 16  # pyaudio.paInt16
    audio_channels: int = 1
    audio_rate: int = 16000

    # Script
    script_path: str = "roteiros/roteiro_demo_bddf.json"

    # Speech recognition
    palavras_por_minuto_base: int = 150
    similaridade_minima: float = 0.6
    cobertura_minima: float = 0.4
    relevancia_minima: float = 0.3

    # Scroll
    velocidade_minima_rolagem: float = 0.05
    velocidade_maxima_rolagem: float = 3.0

    # TP Display
    tp_max_width_vw: int = 90
    tp_max_height_vh: int = 60
    tp_aspect_ratio: str = "4/3"

    # Redis (for multi-worker SocketIO)
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_allowed_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Backward compatibility dict
CONFIG = {
    "secret_key": get_settings().secret_key,
    "flask_env": get_settings().flask_env,
    "host": get_settings().host,
    "port": get_settings().port,
    "vosk_model_path": get_settings().vosk_model_path,
    "vosk_sample_rate": get_settings().vosk_sample_rate,
    "audio": {
        "device_index": get_settings().audio_device_index,
        "chunk_size": get_settings().audio_chunk_size,
        "format": get_settings().audio_format,
        "channels": get_settings().audio_channels,
        "rate": get_settings().audio_rate,
    },
    "caminho_roteiro": get_settings().script_path,
    "palavras_por_minuto_base": get_settings().palavras_por_minuto_base,
    "similaridade_minima": get_settings().similaridade_minima,
    "cobertura_minima": get_settings().cobertura_minima,
    "relevancia_minima": get_settings().relevancia_minima,
    "velocidade_minima_rolagem": get_settings().velocidade_minima_rolagem,
    "velocidade_maxima_rolagem": get_settings().velocidade_maxima_rolagem,
    "tp_display": {
        "max_width_vw": get_settings().tp_max_width_vw,
        "max_height_vh": get_settings().tp_max_height_vh,
        "aspect_ratio": get_settings().tp_aspect_ratio,
    },
    "redis_url": get_settings().redis_url,
    "cors_allowed_origins": get_settings().cors_allowed_origins,
}