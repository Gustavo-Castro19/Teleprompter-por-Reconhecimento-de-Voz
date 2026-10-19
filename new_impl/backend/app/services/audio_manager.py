import pyaudio
from typing import Optional

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AudioDevice:
    def __init__(self, index: int, name: str, max_input_channels: int, default_sample_rate: float):
        self.index = index
        self.name = name
        self.max_input_channels = max_input_channels
        self.default_sample_rate = default_sample_rate

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "name": self.name,
            "maxInputChannels": self.max_input_channels,
            "defaultSampleRate": self.default_sample_rate,
        }


class AudioManager:
    def __init__(self):
        self.p: Optional[pyaudio.PyAudio] = pyaudio.PyAudio()
        self.stream = None
        self.device_index: Optional[int] = None
        self._closed = False

    def _ensure_pyaudio(self):
        if self.p is None and not self._closed:
            self.p = pyaudio.PyAudio()

    def list_devices(self) -> list[AudioDevice]:
        self._ensure_pyaudio()
        devices = []
        count = self.p.get_device_count()
        for i in range(count):
            try:
                info = self.p.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    devices.append(AudioDevice(
                        index=i,
                        name=info.get("name", f"Device {i}"),
                        max_input_channels=info.get("maxInputChannels", 0),
                        default_sample_rate=info.get("defaultSampleRate", 16000),
                    ))
            except Exception:
                continue
        return devices

    def open_microphone(self, device_index: Optional[int] = None) -> bytes:
        self._ensure_pyaudio()

        audio_cfg = {
            "device_index": settings.audio_device_index,
            "chunk_size": settings.audio_chunk_size,
            "channels": settings.audio_channels,
            "rate": settings.audio_rate,
        }
        target_idx = device_index if device_index is not None else audio_cfg.get("device_index")
        sample_rate = audio_cfg.get("rate", 16000)
        channels = audio_cfg.get("channels", 1)
        chunk_size = audio_cfg.get("chunk_size", 4096)

        if target_idx is None:
            devices = self.list_devices()
            if not devices:
                raise RuntimeError("No input devices found")

            preferred = ["pipewire", "pulse", "default", "sysdefault"]
            for pref in preferred:
                for d in devices:
                    if pref.lower() in d.name.lower():
                        target_idx = d.index
                        logger.info(f"Auto-selected preferred device: {d.name} (index {target_idx})")
                        break
                if target_idx is not None:
                    break

            if target_idx is None:
                target_idx = devices[0].index
                logger.info(f"Auto-selected first device: {devices[0].name} (index {target_idx})")
        else:
            try:
                info = self.p.get_device_info_by_index(target_idx)
                if info.get("maxInputChannels", 0) <= 0:
                    raise RuntimeError(f"Device {target_idx} has no input channels")
                logger.info(f"Using configured device: {info.get('name')} (index {target_idx})")
            except Exception as e:
                logger.warning(f"Configured device {target_idx} invalid: {e}, auto-selecting")
                devices = self.list_devices()
                if not devices:
                    raise RuntimeError("No input devices found")
                target_idx = devices[0].index
                logger.info(f"Auto-selected device: {devices[0].name} (index {target_idx})")

        self.device_index = target_idx

        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=target_idx,
            frames_per_buffer=chunk_size,
        )
        self.stream.start_stream()

        # Discard first buffer
        return self.stream.read(chunk_size, exception_on_overflow=False)

    def read_audio(self, chunk_size: int = 4096) -> bytes:
        if not self.stream:
            raise RuntimeError("Microphone not opened")
        try:
            return self.stream.read(chunk_size, exception_on_overflow=False)
        except Exception as e:
            logger.error(f"Audio read error: {e}")
            raise

    def close_microphone(self):
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        except Exception as e:
            logger.warning(f"Error closing stream: {e}")

        try:
            if self.p:
                self.p.terminate()
                self.p = None
        except Exception as e:
            logger.warning(f"Error terminating PyAudio: {e}")
        self._closed = True

    def __del__(self):
        """Ensure PyAudio is terminated on garbage collection."""
        self.close_microphone()

    def get_current_device(self) -> Optional[AudioDevice]:
        if self.device_index is not None and self.p:
            try:
                info = self.p.get_device_info_by_index(self.device_index)
                return AudioDevice(
                    index=self.device_index,
                    name=info.get("name", f"Device {self.device_index}"),
                    max_input_channels=info.get("maxInputChannels", 0),
                    default_sample_rate=info.get("defaultSampleRate", 16000),
                )
            except Exception:
                pass
        return None