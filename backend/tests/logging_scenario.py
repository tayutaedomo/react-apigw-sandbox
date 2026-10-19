"""独立したプロセスでログ設定を適用し、各 Logger の出力を観測する。"""

import logging
import sys
from pathlib import Path

from app import logging_config

logging_config.CONFIG_PATH = Path(sys.argv[1])

from app.request_logging import logger

for target in (logging.getLogger("uvicorn.error"), logger):
    target.debug("debug message")
    target.info("info message")
    target.warning("warning message")

logging.getLogger("app.other").debug("sibling debug")
