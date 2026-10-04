import uvicorn


LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "aws_lambda_powertools.logging.formatter.LambdaPowertoolsFormatter",
            "service": "sandbox-api",
            "utc": True,
            "use_rfc3339": True,
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"level": "INFO", "propagate": True},
        "uvicorn.access": {"handlers": [], "propagate": False},
    },
}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        access_log=False,
        log_config=LOG_CONFIG,
    )
