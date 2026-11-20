from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

import sounddevice as sd

from common.paths import CONFIG_DIR

from .models import DeviceConfig, DeviceInfo

logger = logging.getLogger(__name__)

DEVICE_CONFIG_FILE = CONFIG_DIR / "config_device.json"
TARGET_SAMPLE_RATE = 16000


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.stem}-",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)
    try:
        os.replace(temp_path, path)
    except OSError:
        temp_path.unlink(missing_ok=True)
        raise


def list_input_devices() -> list[DeviceInfo]:
    devices: list[DeviceInfo] = []
    try:
        default_input = sd.default.device[0]
    except Exception:
        default_input = None

    for index, info in enumerate(sd.query_devices()):
        max_input = int(info.get("max_input_channels") or 0)
        if max_input <= 0:
            continue
        devices.append(
            DeviceInfo(
                id=index,
                name=str(info.get("name") or f"Device {index}"),
                channels=max_input,
                default_samplerate=float(info.get("default_samplerate") or 0),
                is_default=index == default_input,
            )
        )
    return devices


def resolve_default_config() -> DeviceConfig:
    devices = list_input_devices()
    default = next((d for d in devices if d.is_default), None)
    if default is None and devices:
        default = devices[0]
    if default is None:
        return DeviceConfig(
            device_id=None,
            name="default",
            sample_rate=TARGET_SAMPLE_RATE,
            channels=1,
        )
    return DeviceConfig(
        device_id=default.id,
        name=default.name,
        sample_rate=TARGET_SAMPLE_RATE,
        channels=1,
    )


def load_device_config() -> DeviceConfig:
    if not DEVICE_CONFIG_FILE.exists():
        config = resolve_default_config()
        save_device_config(config)
        logger.info(
            "Config de áudio criada em %s (device_id=%s)",
            DEVICE_CONFIG_FILE,
            config.device_id,
        )
        return config

    try:
        raw = json.loads(DEVICE_CONFIG_FILE.read_text(encoding="utf-8"))
        return DeviceConfig.model_validate(raw)
    except Exception as error:
        logger.warning("Falha ao ler %s: %s — regenerando", DEVICE_CONFIG_FILE, error)
        config = resolve_default_config()
        save_device_config(config)
        return config


def save_device_config(config: DeviceConfig) -> DeviceConfig:
    _atomic_write(
        DEVICE_CONFIG_FILE,
        json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
    )
    logger.info(
        "Config de áudio salva: device_id=%s name=%r",
        config.device_id,
        config.name,
    )
    return config


def select_device(device_id: int | None) -> DeviceConfig:
    if device_id is None:
        config = resolve_default_config()
        return save_device_config(config)

    devices = {d.id: d for d in list_input_devices()}
    info = devices.get(device_id)
    if info is None:
        raise ValueError(f"Dispositivo de entrada {device_id} não encontrado")

    config = DeviceConfig(
        device_id=info.id,
        name=info.name,
        sample_rate=TARGET_SAMPLE_RATE,
        channels=1,
    )
    return save_device_config(config)


def ensure_device_config() -> DeviceConfig:
    return load_device_config()
