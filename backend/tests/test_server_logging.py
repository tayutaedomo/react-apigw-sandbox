"""起動時の共通設定・モジュール別指定・設定不正時の動作を確認する。"""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("level, module_debug", [("INFO", False), ("WARNING", False), ("INFO", True)])
def test_uvicorn_and_app_respect_configured_levels(level, module_debug, tmp_path):
    backend_dir = Path(__file__).resolve().parents[1]
    config = json.loads((backend_dir / "app/logging.json").read_text())
    if module_debug:
        config["loggers"]["app.request_logging"] = {"level": "DEBUG"}
    config_path = tmp_path / "logging.json"
    config_path.write_text(json.dumps(config))
    env = {**os.environ, "PYTHONPATH": str(backend_dir),
           "POWERTOOLS_LOG_LEVEL": level, "AWS_LAMBDA_LOG_LEVEL": "DEBUG"}
    result = subprocess.run([sys.executable, str(Path(__file__).with_name("logging_scenario.py")),
                             str(config_path)], env=env, capture_output=True, text=True, check=True)
    records = [json.loads(line) for line in result.stdout.splitlines()]
    common_levels = ["INFO", "WARNING"] if level == "INFO" else ["WARNING"]
    assert [r["level"] for r in records if r["logger_name"] == "uvicorn.error"] == common_levels
    assert [r["level"] for r in records if r["logger_name"] == "app.request_logging"] == (
        ["DEBUG", "INFO", "WARNING"] if module_debug else common_levels
    )
    assert "sibling debug" not in result.stdout
    assert all(record["service"] == "sandbox-api" for record in records)
    assert all(record["timestamp"].endswith("+00:00") for record in records)


def test_invalid_log_level_fails_startup():
    result = subprocess.run([sys.executable, "-m", "app.server"], capture_output=True, text=True,
                            env={**os.environ, "POWERTOOLS_LOG_LEVEL": "INVALID"})
    assert result.returncode != 0
    assert "POWERTOOLS_LOG_LEVEL must be" in result.stderr
