"""JSON ログ設定を適用して Uvicorn を起動する。"""

import uvicorn

from app.logging_config import configure_logging


if __name__ == "__main__":
    configure_logging()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080,
                access_log=False, log_config=None)
