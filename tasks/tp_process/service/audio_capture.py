from __future__ import annotations

import logging
import queue
import threading
from typing import Callable

import sounddevice as sd

from .models import DeviceConfig

logger = logging.getLogger(__name__)

AudioChunkHandler = Callable[[bytes], None]


class AudioCapture:
    """Captura PCM int16 mono via sounddevice.

    O callback só enfileira; o processamento ASR roda em thread dedicada
    para não bloquear o PortAudio.
    """

    def __init__(self, on_chunk: AudioChunkHandler | None = None) -> None:
        self._on_chunk = on_chunk
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=64)
        self._stream: sd.RawInputStream | None = None
        self._lock = threading.Lock()
        self._running = False
        self._worker: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self, config: DeviceConfig) -> None:
        with self._lock:
            if self._running:
                self._stop_unlocked()

            self._drain_queue()
            sample_rate = int(config.sample_rate or 16000)
            channels = max(1, int(config.channels or 1))
            device = config.device_id

            def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
                if status:
                    logger.warning("sounddevice status: %s", status)
                chunk = bytes(indata)
                try:
                    self._queue.put_nowait(chunk)
                except queue.Full:
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        self._queue.put_nowait(chunk)
                    except queue.Full:
                        pass

            try:
                self._stream = sd.RawInputStream(
                    samplerate=sample_rate,
                    blocksize=4000,
                    device=device,
                    dtype="int16",
                    channels=channels,
                    callback=callback,
                )
                self._stream.start()
            except Exception as error:
                self._stream = None
                raise RuntimeError(
                    f"Falha ao abrir dispositivo de áudio "
                    f"(device_id={device}, rate={sample_rate}): {error}"
                ) from error

            self._running = True
            self._worker = threading.Thread(
                target=self._worker_loop,
                name="tp-audio-worker",
                daemon=True,
            )
            self._worker.start()
            logger.info(
                "Captura iniciada device_id=%s rate=%s channels=%s",
                device,
                sample_rate,
                channels,
            )

    def _worker_loop(self) -> None:
        while self._running:
            try:
                chunk = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            if chunk is None:
                break
            handler = self._on_chunk
            if handler is None:
                continue
            try:
                handler(chunk)
            except Exception as error:
                logger.exception("Erro no handler de áudio: %s", error)

    def read(self, timeout: float = 0.25) -> bytes | None:
        try:
            item = self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
        return item

    def stop(self) -> None:
        with self._lock:
            self._stop_unlocked()

    def _stop_unlocked(self) -> None:
        was_running = self._running
        self._running = False
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass

        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as error:
                logger.warning("Erro ao parar captura: %s", error)

        worker = self._worker
        self._worker = None
        if (
            worker is not None
            and worker.is_alive()
            and threading.current_thread() is not worker
        ):
            worker.join(timeout=1.5)

        self._drain_queue()
        if was_running:
            logger.info("Captura parada")

    def _drain_queue(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
