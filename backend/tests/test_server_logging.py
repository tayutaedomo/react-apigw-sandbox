"""サーバーログの概要・方針・ケース一覧。

方針: 別プロセスで実際の logging 設定を適用し、標準出力を JSON として読む。
ケース: Uvicorn とアプリの JSON 出力、WARNING 設定で INFO を抑制、設定不正で起動失敗。
"""

import json
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("level, expected", [("INFO", ["INFO", "WARNING"]), ("WARNING", ["WARNING"])])
def test_uvicorn_and_app_respect_common_log_level(level, expected):
    code = '''
import logging
from logging.config import dictConfig
from app.server import build_log_config
from app.request_logging import logger
dictConfig(build_log_config())
server = logging.getLogger("uvicorn.error")
for target in (server, logger):
    target.info("info message")
    target.warning("warning message")
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            env={**os.environ, "POWERTOOLS_LOG_LEVEL": level}, check=True)
    records = [json.loads(line) for line in result.stdout.splitlines()]
    assert [record["level"] for record in records] == expected * 2
    assert all(record["service"] == "sandbox-api" for record in records)
    assert all("timestamp" in record for record in records)


def test_invalid_log_level_fails_startup():
    result = subprocess.run([sys.executable, "-m", "app.server"], capture_output=True, text=True,
                            env={**os.environ, "POWERTOOLS_LOG_LEVEL": "INVALID"})
    assert result.returncode != 0
    assert "POWERTOOLS_LOG_LEVEL must be" in result.stderr
