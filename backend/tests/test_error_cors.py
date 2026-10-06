"""エラーレスポンスの CORS・本文・相関 ID とログの検証。

方針: 実際のアプリ構成を TestClient で実行し、例外を500レスポンスとして観測する。
ブラウザーによる読み取り拒否とプリフライト後の送信有無は Playwright で検証する。

ケース:
- 404・405・入力422、明示的400/409/418/429/500/502/503/504、未処理例外・応答検証500。
- 全ケースで許可 Origin だけに CORS を付け、credentials は許可しない。
- 429の Retry-After、500の内部情報非公開、ステータス・ID・例外のログ整合。
- プリフライト: GET許可、Origin・メソッド・ヘッダーの拒否。
- 検証 API の既定無効と、許可メソッド外でもサーバーが応答すること。
"""

from io import StringIO
import json
from uuid import UUID, uuid4

from aws_lambda_powertools import Logger
from fastapi.testclient import TestClient
import pytest

from app import request_logging
from app.main import create_app

CASES = [
    ("GET", "/missing", 404),
    ("POST", "/hello", 405),
    ("GET", "/errors/validation", 422),
    ("GET", "/errors/validation?value=wrong", 422),
    ("GET", "/errors/validation?value=0", 422),
    *[("GET", f"/errors/http/{status}", status) for status in (400, 409, 418, 429, 500, 502, 503, 504)],
    ("GET", "/errors/unhandled", 500),
    ("GET", "/errors/response-validation", 500),
]


@pytest.fixture
def probe_client():
    with TestClient(create_app(enable_error_endpoints=True), raise_server_exceptions=False) as client:
        yield client


@pytest.mark.parametrize("origin,allowed", [("http://localhost:5173", True), ("http://localhost:9999", False), (None, False)])
@pytest.mark.parametrize("method,path,status", CASES)
def test_error_cors_and_body(probe_client, origin, allowed, method, path, status):
    response = probe_client.request(method, path, headers={"Origin": origin} if origin else {})
    assert response.status_code == status
    UUID(response.headers["x-request-id"])
    assert "access-control-allow-credentials" not in response.headers
    if allowed:
        assert response.headers["access-control-allow-origin"] == origin
        assert "Origin" in response.headers["vary"]
        assert "X-Request-Id" in response.headers["access-control-expose-headers"]
    else:
        assert "access-control-allow-origin" not in response.headers

    if path in {"/errors/unhandled", "/errors/response-validation"}:
        assert response.text == "Internal Server Error"
        assert "Traceback" not in response.text
    elif status == 422:
        assert isinstance(response.json()["detail"], list)
    else:
        assert isinstance(response.json()["detail"], str)
    if status == 429:
        assert response.headers["retry-after"] == "1"


@pytest.mark.parametrize("method,path,status", CASES)
def test_error_log_matches_response(monkeypatch, probe_client, method, path, status):
    stream = StringIO()
    monkeypatch.setattr(request_logging, "logger", Logger(service=f"test-{uuid4()}", stream=stream))
    response = probe_client.request(method, path, headers={"Origin": "http://localhost:5173"})
    [record] = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert record["status_code"] == response.status_code == status
    assert record["correlation_id"] == response.headers["x-request-id"]
    # HTTPException は処理済み応答、未処理例外のみ ERROR とスタックトレースになる。
    if path in {"/errors/unhandled", "/errors/response-validation"}:
        assert record["level"] == "ERROR"
        assert record["exception_name"] in {"RuntimeError", "ResponseValidationError"}
    else:
        assert record["level"] == "INFO"
        assert "exception" not in record


@pytest.mark.parametrize("origin,method,headers,status,reason", [
    ("http://localhost:5173", "GET", "", 200, None),
    ("http://localhost:9999", "GET", "", 400, "origin"),
    ("http://localhost:5173", "POST", "", 400, "method"),
    ("http://localhost:5173", "GET", "x-probe", 400, "headers"),
])
def test_preflight_policy(probe_client, origin, method, headers, status, reason):
    request_headers = {"Origin": origin, "Access-Control-Request-Method": method}
    if headers:
        request_headers["Access-Control-Request-Headers"] = headers
    response = probe_client.options("/errors/http/400", headers=request_headers)
    assert response.status_code == status
    assert "access-control-allow-credentials" not in response.headers
    assert response.headers.get("access-control-allow-origin") == (origin if origin.endswith(":5173") else None)
    assert response.headers["access-control-allow-methods"] == "GET"
    if reason:
        assert reason in response.text


def test_error_endpoints_are_disabled_by_default():
    with TestClient(create_app()) as client:
        assert client.get("/hello").status_code == 200
        assert client.get("/errors/http/400").status_code == 404
        assert client.get("/errors/unhandled").status_code == 404


def test_unsupported_status_is_not_returned(probe_client):
    assert probe_client.get("/errors/http/200").status_code == 404


def test_allowed_method_is_not_server_authorization(probe_client):
    # POST は CORS プリフライトでは拒否されるが、単純 POST はサーバーへ届く。
    response = probe_client.post("/hello", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 405
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
