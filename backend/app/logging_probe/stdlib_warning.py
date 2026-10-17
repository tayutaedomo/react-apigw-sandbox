"""モジュール名を持つ標準 Logger のレベルを設定する。"""

import logging


def create(level: str) -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    return logger
