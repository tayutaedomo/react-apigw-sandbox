"""概要: 配信先の Origin を環境変数で設定し、許可範囲が広がらないことを確認する。

方針: 実際の CORS 応答と起動時の入力検証を確認する。
ケース: 既定の localhost、追加 Origin の正常・500応答、未許可 Origin、
        空・型不正・wildcard・パス・認証情報・不正ポートの拒否。
"""
import json

from fastapi.testclient import TestClient
import pytest

from app.main import allowed_origins, create_app


def test_default_origin(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    assert allowed_origins() == ["http://localhost:5173"]


@pytest.mark.parametrize("path,status", [("/hello", 200), ("/errors/unhandled", 500)])
def test_additional_origin_receives_cors(monkeypatch, path, status):
    origin = "https://sandbox.example.com"
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", json.dumps(["http://localhost:5173", origin]))
    with TestClient(create_app(enable_error_endpoints=True), raise_server_exceptions=False) as client:
        response = client.get(path, headers={"Origin": origin})
        denied = client.get(path, headers={"Origin": "https://other.example.com"})
    assert response.status_code == status
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-origin" not in denied.headers


@pytest.mark.parametrize("value", [
    [], "https://example.com", [None], ["*"], ["https://*.example.com"],
    ["https://example.com/"], ["https://example.com/path"], ["https://example.com?x=1"],
    ["https://example.com#fragment"], ["https://user:pass@example.com"],
    ["ftp://example.com"], ["https://example.com:99999"], ["https://example.com:abc"],
    ["https://exa mple.com"],
])
def test_invalid_origin_is_rejected(monkeypatch, value):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", json.dumps(value))
    with pytest.raises(ValueError):
        allowed_origins()
