"""モジュール名を持つ Powertools 子 Logger を生成する。"""

from aws_lambda_powertools import Logger


def create(service: str, level: str) -> Logger:
    return Logger(service=service, child=True, level=level)
