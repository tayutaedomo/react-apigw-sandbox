"""FastAPI 全体をログと CORS で包み、未処理例外の応答にも適用する。"""

import os

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


def create_app(*, enable_error_endpoints: bool = False) -> CORSMiddleware:
    """検証 API の有効化を選び、500 を含むすべての HTTP 応答に CORS を適用する。"""
    api = FastAPI(title="Sandbox API")
    api.get("/hello", response_model=HelloResponse)(hello)
    if enable_error_endpoints:
        api.include_router(errors_router)

    # add_middleware では FastAPI の ServerErrorMiddleware がさらに外側に置かれる。
    # その500も観測するため、ログを FastAPI の外側、CORS をさらに外側に配置する。
    # CORS のプリフライトはアプリへ届かないため、HTTP ログの対象外になる。
    return CORSMiddleware(
        RequestLoggingMiddleware(api),
        allow_origins=["http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=[],
        # ブラウザーから相関 ID と429の再試行情報を読めるようにする。
        expose_headers=["X-Request-Id", "Retry-After"],
    )


app = create_app(enable_error_endpoints=os.environ.get("ENABLE_ERROR_ENDPOINTS") == "true")
