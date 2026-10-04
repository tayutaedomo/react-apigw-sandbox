"""リクエストログの概要・方針・ケース一覧。

方針: ASGI アプリへ HTTP リクエストを送り、出力された JSON とレスポンスを
照合する。Lambda コンテキストは Adapter のヘッダー形式を模擬し、AWS 実行の
検証とは区別する。ログは StringIO に隔離して、並行処理の混同と秘密の漏洩も確認する。

ケース:
- 正常終了: ステータス・処理時間・生成 UUID、クエリ・認証情報の非記録。
- 405: 実際のステータスの記録、リクエスト本文の非記録。
- 未処理例外: ERROR とスタックトレースの記録、500 の維持。
- 並行処理: リクエストごとの ID とステータスが一致。
- Lambda: 呼び出し ID の継承、コンテキスト欠落・破損時の UUID フォールバック。
- 環境への非依存: ローカルでも有効なコンテキストの ID を利用。
"""

import asyncio
from io import StringIO
import json
from uuid import UUID, uuid4

from aws_lambda_powertools import Logger
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import httpx2
import pytest

from app.main import app
from app import request_logging
from app.request_logging import RequestLoggingMiddleware


@pytest.fixture
def log_stream(monkeypatch):
    monkeypatch.delenv("AWS_LAMBDA_RUNTIME_API", raising=False)
    stream = StringIO()
    logger = Logger(service=f"test-{uuid4()}", stream=stream)
    monkeypatch.setattr(request_logging, "logger", logger)
    return stream


def read_logs(stream):
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def test_success_log_matches_response_and_does_not_leak_request_data(log_stream):
    with TestClient(app) as client:
        response = client.get(
            "/hello?token=secret-query",
            headers={"Authorization": "Bearer secret-header"},
        )

    [record] = read_logs(log_stream)
    assert record["message"] == "HTTP request completed"
    assert record["level"] == "INFO"
    assert record["method"] == "GET"
    assert record["path"] == "/hello"
    assert record["status_code"] == 200
    assert record["duration_ms"] >= 0
    assert record["correlation_id"] == response.headers["x-request-id"]
    UUID(record["correlation_id"])
    assert "secret-query" not in log_stream.getvalue()
    assert "secret-header" not in log_stream.getvalue()


def test_response_error_is_logged_with_its_actual_status(log_stream):
    with TestClient(app) as client:
        response = client.post("/hello", json={"secret-body": "do-not-log"})

    [record] = read_logs(log_stream)
    assert response.status_code == record["status_code"] == 405
    assert record["correlation_id"] == response.headers["x-request-id"]
    assert "secret-body" not in log_stream.getvalue()
    assert "do-not-log" not in log_stream.getvalue()


def test_unhandled_exception_is_logged_and_still_returns_500(log_stream):
    test_app = FastAPI()
    test_app.add_middleware(RequestLoggingMiddleware)

    @test_app.get("/failure")
    def fail():
        raise RuntimeError("test failure")

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/failure")

    [record] = read_logs(log_stream)
    assert response.status_code == record["status_code"] == 500
    assert record["level"] == "ERROR"
    assert record["message"] == "HTTP request failed"
    assert record["exception_name"] == "RuntimeError"
    assert "test failure" in record["exception"]
    assert record["path"] == "/failure"
    UUID(record["correlation_id"])


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_concurrent_requests_keep_separate_ids_and_statuses(log_stream):
    test_app = FastAPI()
    test_app.add_middleware(RequestLoggingMiddleware)
    both_started = asyncio.Event()
    started = 0

    @test_app.get("/work/{name}")
    async def work(name: str):
        nonlocal started
        started += 1
        if started == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=5)
        return JSONResponse({"name": name}, status_code=201 if name == "first" else 202)

    async with httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        responses = await asyncio.gather(client.get("/work/first"), client.get("/work/second"))

    records = {record["path"]: record for record in read_logs(log_stream)}
    assert len(records) == 2
    assert len({record["correlation_id"] for record in records.values()}) == 2
    for name, response in zip(["first", "second"], responses):
        record = records[f"/work/{name}"]
        assert record["correlation_id"] == response.headers["x-request-id"]
        assert record["status_code"] == response.status_code


def test_lambda_request_id_matches_log_and_response(log_stream, monkeypatch):
    monkeypatch.setenv("AWS_LAMBDA_RUNTIME_API", "localhost:9001")
    invocation_id = str(uuid4())
    with TestClient(app) as client:
        response = client.get("/hello", headers={
            "x-amzn-lambda-context": json.dumps({"request_id": invocation_id})
        })
    [record] = read_logs(log_stream)
    assert record["lambda_request_id"] == record["correlation_id"] == invocation_id
    assert record["request_id_source"] == "lambda"
    assert response.headers["x-request-id"] == invocation_id


@pytest.mark.parametrize("context", [None, "not-json", "[]", '{"request_id":"invalid"}'])
def test_invalid_context_falls_back_to_generated_id(log_stream, monkeypatch, context):
    monkeypatch.setenv("AWS_LAMBDA_RUNTIME_API", "localhost:9001")
    headers = {"x-amzn-lambda-context": context} if context is not None else {}
    with TestClient(app) as client:
        response = client.get("/hello", headers=headers)
    [record] = read_logs(log_stream)
    assert response.status_code == 200
    assert record["correlation_id"] == response.headers["x-request-id"]
    UUID(record["correlation_id"])
    assert "lambda_request_id" not in record
    assert record["request_id_source"] == "generated"


def test_valid_context_is_used_without_runtime_environment(log_stream):
    supplied_id = str(uuid4())
    with TestClient(app) as client:
        response = client.get("/hello", headers={
            "x-amzn-lambda-context": json.dumps({"request_id": supplied_id})
        })
    [record] = read_logs(log_stream)
    assert record["request_id_source"] == "lambda"
    assert record["correlation_id"] == supplied_id
    assert record["correlation_id"] == response.headers["x-request-id"]
    UUID(record["correlation_id"])
