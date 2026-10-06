"""CORS 検証用のエラーを再現する。ENABLE_ERROR_ENDPOINTS=true の場合だけ登録する。"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/errors", tags=["error-probes"])


@router.get("/http/{status_code}")
def http_error(status_code: int):
    """認証以外の代表的な4xx・5xxを返す。429には再試行までの秒数を付ける。"""
    # 任意のステータスは受け付けず、検証対象のエラーだけに限定する。
    if status_code not in {400, 409, 418, 429, 500, 502, 503, 504}:
        raise HTTPException(status_code=404, detail="Unknown error probe")
    headers = {"Retry-After": "1"} if status_code == 429 else None
    raise HTTPException(status_code=status_code, detail=f"Error probe: {status_code}", headers=headers)


@router.get("/validation")
def validation(value: Annotated[int, Query(ge=1)]):
    """欠落・型不正・範囲外を FastAPI 標準の422で返すための入力を定義する。"""
    return {"value": value}


@router.get("/unhandled")
def unhandled():
    """HTTPException と異なり、未処理例外を ServerErrorMiddleware で500に変換させる。"""
    raise RuntimeError("Intentional unhandled error probe")


class RequiredMessage(BaseModel):
    message: str


@router.get("/response-validation", response_model=RequiredMessage)
def response_validation():
    """必須フィールドを欠く戻り値で、サーバー側のレスポンス検証エラーを再現する。"""
    return {}
