from time import perf_counter
from uuid import uuid4

from aws_lambda_powertools import Logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send


logger = Logger(service="sandbox-api", utc=True, use_rfc3339=True)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = perf_counter()
        correlation_id = str(uuid4())
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message = {
                    **message,
                    "headers": [
                        *message.get("headers", []),
                        (b"x-request-id", correlation_id.encode("ascii")),
                    ],
                }
            await send(message)

        def fields() -> dict:
            return {
                "method": scope["method"],
                "path": scope["path"],
                "status_code": status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 3),
                "correlation_id": correlation_id,
            }

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            logger.exception("HTTP request failed", extra=fields())
            raise
        else:
            # Per-record metadata avoids sharing request state across concurrent requests.
            logger.info("HTTP request completed", extra=fields())
