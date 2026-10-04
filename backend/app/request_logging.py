"""HTTP の処理結果を記録し、Lambda またはローカルの ID で追跡する。"""

import json
import os
from time import perf_counter
from uuid import UUID, uuid4

from aws_lambda_powertools import Logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.server import get_log_level

logger = Logger(service="sandbox-api", utc=True, use_rfc3339=True, level=get_log_level())


def request_id(scope: Scope) -> tuple[str | None, str]:
    """Lambda では Adapter の request_id、ローカルでは UUID を返す。

    Lambda の readiness probe には呼び出しコンテキストがないため、ID は
    None とする。壊れたコンテキストでも API を失敗させず、生成 ID で
    Lambda の ID を代用しない。ローカルでは外部からのコンテキストを信用しない。
    """
    if not os.environ.get("AWS_LAMBDA_RUNTIME_API"):
        return str(uuid4()), "local"

    # Web Adapter がクライアントの同名ヘッダーを上書きして渡す JSON を読む。
    raw = next((value for name, value in scope["headers"]
                if name.lower() == b"x-amzn-lambda-context"), None)
    try:
        context = json.loads(raw) if raw is not None else {}
        value = context.get("request_id")
        if isinstance(value, str):
            # UUID 検証により、レスポンスヘッダーに制御文字を持ち込ませない。
            UUID(value)
            return value, "lambda"
    except (ValueError, TypeError, AttributeError, UnicodeDecodeError):
        pass
    return None, "unavailable"


class RequestLoggingMiddleware:
    """ASGI のレスポンス開始を監視し、実際のステータスと処理時間を記録する。"""

    def __init__(self, app: ASGIApp) -> None:
        """後続の ASGI アプリを保持する。リクエスト固有の状態は保持しない。"""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """HTTP のみを計測し、正常終了または例外のログを1件出力する。"""
        if scope["type"] != "http":
            # lifespan や WebSocket は HTTP のステータス計測の対象外。
            await self.app(scope, receive, send)
            return

        started = perf_counter()
        correlation_id, id_source = request_id(scope)
        # レスポンス開始前の例外は、外側のエラーハンドラーが 500 に変換する。
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            """レスポンス開始時にステータスを取得し、追跡 ID を付与する。"""
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                if correlation_id is not None:
                    message = {
                        **message,
                        "headers": [
                            *message.get("headers", []),
                            (b"x-request-id", correlation_id.encode("ascii")),
                        ],
                    }
            await send(message)

        def fields() -> dict:
            """完了時点の情報だけを返し、本文や秘密を含むヘッダーは記録しない。"""
            return {
                "method": scope["method"],
                "path": scope["path"],
                "status_code": status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 3),
                "correlation_id": correlation_id,
                "request_id_source": id_source,
                "lambda_request_id": correlation_id if id_source == "lambda" else None,
            }

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            logger.exception("HTTP request failed", extra=fields())
            # エラー処理は FastAPI に任せ、例外を成功レスポンスへ変換しない。
            raise
        else:
            # extra はログ1件に限定され、並行処理間で Logger の状態を共有しない。
            logger.info("HTTP request completed", extra=fields())
