"""比較する Logger の指定値を同梱ファイルから起動時に読み込む。"""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("levels.json")
LOGGER_NAMES = {"powertools_parent", "powertools_debug", "powertools_warning", "stdlib_debug", "stdlib_warning"}
VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def get_probe_levels() -> dict[str, str]:
    try:
        levels = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError("ログ設定ファイルは Logger 名とレベルの JSON オブジェクトで指定してください") from exc
    if (not isinstance(levels, dict) or levels.keys() != LOGGER_NAMES
            or any(not isinstance(value, str) or value not in VALID_LEVELS for value in levels.values())):
        raise ValueError("ログ設定ファイルには比較対象の全 Logger 名と有効なログレベルを指定してください")
    return levels
