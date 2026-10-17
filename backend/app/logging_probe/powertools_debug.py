"""DEBUG レベルの Powertools 子 Logger。"""

from aws_lambda_powertools import Logger


def create(service: str) -> Logger:
    return Logger(service=service, child=True, level="DEBUG")
