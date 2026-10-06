"""HTTP の処理結果を記録し、Lambda またはローカルの ID で追跡する。"""

import json
from time import perf_counter
from uuid import UUID, uuid4

from aws_lambda_powertools import Logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.server import get_log_level

logger = Logger(service="sandbox-api", utc=True, use_rfc3339=True, level=get_log_level())


def request_id(scope: Scope) -> tuple[str, str]:
    """Adapter の request_id を優先し、取得できなければ UUID を生成する。

    ローカル実行・readiness probe・コンテキスト不正を同じフォールバックで扱う。
    生成 ID は Lambda 呼び出し ID とは区別し、ログに出所を記録する。
    Lambda では Adapter が同名ヘッダーを上書きする。直接公開したローカル API
    のヘッダーは呼び出し元が指定できるため、ID を認証や信頼の判断には使わない。
    """
    # Web Adapter がクライアントの同名ヘッダーを上書きして渡す JSON を読む。
    raw = next((value for name, value in scope["headers"]
                if name.lower() == b"x-amzn-lambda-context"), None)
    try:
        context = json.loads(raw) if raw is not None else {}
        value = context.get("request_id")
        if isinstance(value, str):
            # UUID 検証により、レスポンスヘッダーに制御文字を持ち込ませない。
            parsed = UUID(value)
            if value == str(parsed):
                return value, "lambda"
    except (ValueError, TypeError, AttributeError, UnicodeDecodeError):
        pass
    return str(uuid4()), "generated"


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
        # レスポンス開始前の例外でも未設定の値にしない。通常は実際の500を取得する。
        status_code = 500
        completed_duration_ms: float | None = None

        async def send_with_request_id(message: Message) -> None:
            """レスポンス開始時にステータスを取得し、追跡 ID を付与する。"""
            nonlocal status_code, completed_duration_ms
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message = {
                    **message,
                    "headers": [
                        *message.get("headers", []),
                        (b"x-request-id", correlation_id.encode("ascii")),
                    ],
                }
            elif message["type"] == "http.response.body" and not message.get("more_body", False):
                # Adapter が本文を受け取ると Lambda が停止する場合がある。ログ出力が
                # 後続の呼び出しへ遅れても、停止中の時間を処理時間へ含めない。
                completed_duration_ms = round((perf_counter() - started) * 1000, 3)
            await send(message)

        def fields() -> dict:
            """完了時点の情報だけを返し、本文や秘密を含むヘッダーは記録しない。"""
            return {
                "method": scope["method"],
                "path": scope["path"],
                "status_code": status_code,
                "duration_ms": completed_duration_ms if completed_duration_ms is not None
                else round((perf_counter() - started) * 1000, 3),
                "correlation_id": correlation_id,
                "request_id_source": id_source,
                "lambda_request_id": correlation_id if id_source == "lambda" else None,
            }

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            logger.exception("HTTP request failed", extra=fields())
            # FastAPI は500送信後も例外を再送出する。ERROR に記録して再送出を維持する。
            raise
        else:
            # extra はログ1件に限定され、並行処理間で Logger の状態を共有しない。
            logger.info("HTTP request completed", extra=fields())
