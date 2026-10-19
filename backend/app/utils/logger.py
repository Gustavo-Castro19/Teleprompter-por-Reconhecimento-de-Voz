import logging
import sys
import json
from datetime import datetime
from typing import Any
from functools import lru_cache


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "lineno", "funcName", "created",
                "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "exc_info", "exc_text", "stack_info",
                "getMessage"
            ):
                log_data[key] = value
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S"
            )
        )
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers = [handler]


@lru_cache
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


from app.utils.logger import get_logger

logger = get_logger(__name__)


# Backward compatibility class
class Colors:
    VERDE = "\033[92m"
    AMARELO = "\033[93m"
    VERMELHO = "\033[91m"
    AZUL = "\033[94m"
    BASE = "\033[0m"


class EventLogger:
    @staticmethod
    def machine_active():
        logger.info("--- MACHINE ACTIVE ---")

    @staticmethod
    def state_change(old_state: str, new_state: str):
        logger.info(f"[STATE] {old_state} -> {new_state}")

    @staticmethod
    def script_finished():
        logger.info("[SYSTEM] Script finished. Stopping engine.")

    @staticmethod
    def system_failure(error: Exception):
        logger.error(f"[FAILURE] Critical system error: {error}", exc_info=True)

    @staticmethod
    def microphone_opened():
        logger.info("--- MICROPHONE OPENED ---")

    @staticmethod
    def scroll_event(event_type: str, spoken_idx: int, visual_idx: int):
        logger.info(f"--> [{event_type.upper()}] Going to spoken line {spoken_idx + 1}, visual {visual_idx + 1}")

    @staticmethod
    def recognition(recog_type: str, text: str, current_idx: int, current_line: str):
        logger.info(f"[{recog_type}] '{text}' | line {current_idx + 1}: '{current_line[:40]}'")

    @staticmethod
    def client_connected():
        logger.info("CLIENT CONNECTED")

    @staticmethod
    def server_started(url: str):
        logger.info(f"Server: {url}")