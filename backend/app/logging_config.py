"""アプリと Uvicorn のログ設定を起動時に適用する。"""

import json
import logging.config
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("logging.json")
_configured = False


class LoggerNameFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.logger_name = record.name
        return True


def get_log_level() -> str:
    level = os.environ.get("POWERTOOLS_LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("POWERTOOLS_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL")
    return level


def build_log_config() -> dict:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if "POWERTOOLS_LOG_LEVEL" in os.environ:
        level = get_log_level()
        for name in ("app", "uvicorn"):
            config["loggers"][name]["level"] = level
    return config


def configure_logging() -> None:
    global _configured
    if not _configured:
        logging.config.dictConfig(build_log_config())
        _configured = True
