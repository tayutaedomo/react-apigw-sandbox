"""FastAPI 全体をログと CORS で包み、未処理例外の応答にも適用する。"""

import json
import os
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.request_logging import RequestLoggingMiddleware
from app.errors import router as errors_router


class HelloResponse(BaseModel):
    message: str


def hello() -> HelloResponse:
    """正常系の疎通と readiness のために固定のメッセージを返す。"""
    return HelloResponse(message="Hello World")


def allowed_origins() -> list[str]:
    """環境変数の JSON 配列から、完全一致で許可する Origin を読み取る。

    未指定ならローカル開発だけを許可する。誤設定は起動時に検出し、
    wildcard やパス付き URL を黙って許可設定に使わない。
    """
    values = json.loads(os.environ.get("CORS_ALLOW_ORIGINS", '["http://localhost:5173"]'))
    if not isinstance(values, list) or not values:
        raise ValueError("CORS_ALLOW_ORIGINS は空でない Origin の JSON 配列にしてください")
    for value in values:
        if not isinstance(value, str):
            raise ValueError("Origin は文字列にしてください")
        url = urlsplit(value)
        if (
            url.scheme not in ("http", "https") or not url.hostname or url.username
            or url.password or url.path or url.query or url.fragment
            or "*" in value or any(char.isspace() for char in value)
        ):
            raise ValueError("Origin は http(s)://host[:port] 形式にしてください")
        # 不正なポートも起動時に検出する。
        _ = url.port
    return values


def create_app(*, enable_error_endpoints: bool = False) -> CORSMiddleware:
    """検証 API の有効化を選び、500 を含むすべての HTTP 応答に CORS を適用する。"""
    api = FastAPI(title="Sandbox API")
    api.get("/hello", response_model=HelloResponse)(hello)
    if enable_error_endpoints:
        api.include_router(errors_router)

    # FastAPI 内部の ServerErrorMiddleware が生成する500も観測するため、
    # add_middleware ではなく FastAPI 全体を包む。詳細: docs/cors.md。
    logged_app = RequestLoggingMiddleware(api)

    # 最も外側で、正常応答と500の両方へ CORS ヘッダーを付ける。
    # プリフライトはここで直接応答し、logged_app と api には届かない。
    cors_app = CORSMiddleware(
        logged_app,
        allow_origins=allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=[],
        # ブラウザーから相関 ID と429の再試行情報を読めるようにする。
        expose_headers=["X-Request-Id", "Retry-After"],
    )
    return cors_app


app = create_app(enable_error_endpoints=os.environ.get("ENABLE_ERROR_ENDPOINTS") == "true")
