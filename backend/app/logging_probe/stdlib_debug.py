"""DEBUG レベルの標準 Logger を Powertools formatter で出力する。"""

import logging


def create() -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    return logger
