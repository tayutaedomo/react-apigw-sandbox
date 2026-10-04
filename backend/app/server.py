"""Uvicorn とアプリのログレベルを統一し、サーバーログを JSON 化する。"""

import os
import uvicorn


def get_log_level() -> str:
    """共通の環境変数を検証し、未設定なら INFO を返す。"""
    level = os.environ.get("POWERTOOLS_LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("POWERTOOLS_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL")
    return level


def build_log_config() -> dict:
    """標準 logging の dictConfig 形式で Uvicorn の出力先と形式を定義する。"""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {
            "()": "aws_lambda_powertools.logging.formatter.LambdaPowertoolsFormatter",
            "service": "sandbox-api", "utc": True, "use_rfc3339": True,
        }},
        "handlers": {"stdout": {
            "class": "logging.StreamHandler", "stream": "ext://sys.stdout",
            "formatter": "json",
        }},
        "loggers": {
            # 起動・終了ログを標準出力へ JSON で送り、親への伝播での二重出力を防ぐ。
            "uvicorn": {"handlers": ["stdout"], "level": get_log_level(), "propagate": False},
            "uvicorn.error": {"level": get_log_level(), "propagate": True},
            # アクセスログはミドルウェアの処理時間・ID 付きログに集約する。
            "uvicorn.access": {"handlers": [], "propagate": False},
        },
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080,
                access_log=False, log_config=build_log_config())
