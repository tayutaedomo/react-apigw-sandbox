"""API の常時公開と、独立プロセスでのログ閾値・継続呼び出しを確認する。"""

import json
import os
import subprocess
import sys

import pytest

@pytest.mark.parametrize("alc_level, count", [(None, 10), ("DEBUG", 13), ("INFO", 10), ("WARN", 7)])
def test_probe_outputs_match_effective_levels_on_repeated_requests(alc_level, count):
    # プロセス起動時の Logger 初期化と Uvicorn 設定を含め、呼び出し間の混同も検出する。
    code = '''
import json
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
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True,
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
