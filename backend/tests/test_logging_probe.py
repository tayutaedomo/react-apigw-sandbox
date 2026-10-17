"""API の常時公開と、独立プロセスでのログ閾値・継続呼び出しを確認する。"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("alc_level, count, overrides", [
    (None, 10, {}), ("DEBUG", 13, {}), ("INFO", 10, {}), ("WARN", 7, {}),
    (None, 8, {"powertools_warning": "ERROR", "stdlib_debug": "ERROR", "stdlib_warning": "DEBUG"}),
    ("DEBUG", 12, {"powertools_warning": "ERROR", "stdlib_debug": "ERROR", "stdlib_warning": "DEBUG"}),
])
def test_probe_outputs_match_effective_levels_on_repeated_requests(alc_level, count, overrides, tmp_path):
    # プロセス起動時の Logger 初期化と Uvicorn 設定を含め、呼び出し間の混同も検出する。
    code = '''
import json
import sys
from pathlib import Path
from app.logging_probe import settings
if len(sys.argv) > 1:
    settings.CONFIG_PATH = Path(sys.argv[1])
from logging.config import dictConfig
from fastapi.testclient import TestClient
from app.server import build_log_config
dictConfig(build_log_config())
from app.main import app
with TestClient(app) as client:
    for _ in range(2):
        response = client.get("/logging/probe?token=secret-query", headers={"Authorization": "secret-header"})
        assert response.status_code == 200
        print(json.dumps({"response": response.json()}))
'''
    env = {key: value for key, value in os.environ.items()
           if key not in {"AWS_LAMBDA_LOG_LEVEL", "POWERTOOLS_LOG_LEVEL", "POWERTOOLS_LOGGER_SAMPLE_RATE"}}
    if alc_level:
        env["AWS_LAMBDA_LOG_LEVEL"] = alc_level
    command = [sys.executable, "-c", code]
    if overrides:
        levels = json.loads(Path("app/logging_probe/levels.json").read_text())
        levels.update(overrides)
        config_path = tmp_path / "levels.json"
        config_path.write_text(json.dumps(levels))
        command.append(str(config_path))
    result = subprocess.run(command, env=env, capture_output=True,
                            text=True, check=True)
    records = [json.loads(line) for line in result.stdout.splitlines()]
    responses = [record["response"] for record in records if "response" in record]
    assert len(responses) == 2
    assert responses[0]["probe_id"] != responses[1]["probe_id"]
    for response in responses:
        logs = [record for record in records if record.get("probe_id") == response["probe_id"]]
        assert len(logs) == count
        assert len(response["cases"]) == 5
        for case in response["cases"]:
            if case["case"] in overrides:
                assert case["configured_level"] == overrides[case["case"]]
            selected = [record for record in logs if record["logger_case"] == case["case"]]
            assert [record["level"] for record in selected] == case["expected_application_levels"]
            assert all(record["logger_name"] == case["logger_name"] for record in selected)
            if case["case"].startswith("powertools"):
                assert case["effective_level"] == (
                    "WARNING" if alc_level == "WARN" else alc_level or case["configured_level"]
                )
            else:
                assert case["effective_level"] == case["configured_level"]
        assert all(record["service"] == "sandbox-api-logger-probe" for record in logs)
        assert all(record["timestamp"].endswith("+00:00") for record in logs)
    assert "secret-query" not in result.stdout
    assert "secret-header" not in result.stdout


@pytest.mark.parametrize("value", ["not-json", "[]", "null", '{"unknown":"INFO"}',
                                    '{"stdlib_debug":"INVALID"}', '{"stdlib_debug":10}', '{}'])
def test_invalid_probe_configuration_fails_startup(value, tmp_path):
    config_path = tmp_path / "levels.json"
    if value.startswith('{"stdlib_debug":'):
        levels = json.loads(Path("app/logging_probe/levels.json").read_text())
        levels.update(json.loads(value))
        value = json.dumps(levels)
    config_path.write_text(value)
    code = "from pathlib import Path; import sys; from app.logging_probe import settings; settings.CONFIG_PATH = Path(sys.argv[1]); import app.main"
    result = subprocess.run([sys.executable, "-c", code, str(config_path)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "ログ設定ファイル" in result.stderr
