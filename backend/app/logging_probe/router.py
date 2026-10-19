"""HTTP 呼び出しでモジュール別のログ閾値と JSON 出力を比較する。"""

import logging
from uuid import uuid4

from aws_lambda_powertools import Logger
from fastapi import APIRouter
from pydantic import BaseModel

from app.logging_probe import powertools_debug, powertools_warning, stdlib_debug, stdlib_warning
from app.logging_probe.settings import get_probe_levels

SERVICE = "sandbox-api-logger-probe"
LEVELS = get_probe_levels()

# 初期化はプロセスにつき一度。HTTP 呼び出しごとに handler や Logger 状態を変更しない。
parent = Logger(service=SERVICE, level=LEVELS["powertools_parent"], utc=True, use_rfc3339=True)

TARGETS = (
    ("powertools_parent", parent, LEVELS["powertools_parent"]),
    ("powertools_debug", powertools_debug.create(SERVICE, LEVELS["powertools_debug"]), LEVELS["powertools_debug"]),
    ("powertools_warning", powertools_warning.create(SERVICE, LEVELS["powertools_warning"]), LEVELS["powertools_warning"]),
    ("stdlib_debug", stdlib_debug.create(LEVELS["stdlib_debug"]), LEVELS["stdlib_debug"]),
    ("stdlib_warning", stdlib_warning.create(LEVELS["stdlib_warning"]), LEVELS["stdlib_warning"]),
)

router = APIRouter(prefix="/logging", tags=["logging"])


class LoggerCase(BaseModel):
    case: str
    logger_name: str
    configured_level: str
    effective_level: str
    expected_application_levels: list[str]


class ProbeResponse(BaseModel):
    probe_id: str
    cases: list[LoggerCase]


@router.get("/probe", response_model=ProbeResponse)
def probe() -> ProbeResponse:
    """固定メッセージを出し、Lambda 側フィルター適用前の期待値を返す。"""
    probe_id = str(uuid4())
    cases = []
    for case, logger, configured_level in TARGETS:
        effective_level = logger.getEffectiveLevel()
        expected_levels = [level for level in ("DEBUG", "INFO", "WARNING")
                           if logging.getLevelNamesMapping()[level] >= effective_level]
        fields = {"probe_id": probe_id, "logger_case": case, "logger_name": logger.name}
        for level in ("DEBUG", "INFO", "WARNING"):
            getattr(logger, level.lower())("Logger level probe", extra=fields)
        cases.append(LoggerCase(case=case, logger_name=logger.name,
                                configured_level=configured_level,
                                effective_level=logging.getLevelName(effective_level),
                                expected_application_levels=expected_levels))
    return ProbeResponse(probe_id=probe_id, cases=cases)
