from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "token_holdem.jsonl"


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "event", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)


def get_logger(name: str = "token_holdem") -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(isinstance(handler, RotatingFileHandler) and getattr(handler, "baseFilename", None) == str(LOG_FILE.resolve()) for handler in logger.handlers):
        handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
        handler.setFormatter(JsonLineFormatter())
        logger.addHandler(handler)
    return logger


def log_event(logger: logging.Logger, message: str, **event: Any) -> None:
    logger.info(message, extra={"event": event})
