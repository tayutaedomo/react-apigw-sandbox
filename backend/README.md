# バックエンド

## 概要

FastAPI で Hello World API を提供します。

- FastAPI: API と OpenAPI ドキュメント。
- Uvicorn: ローカルの HTTP サーバー。
- uv: 仮想環境と依存の管理。
- pytest / httpx2: API テスト。

以下のコマンドは、すべて `backend/` 内で実行します。

## 開発環境

### 必要なツール

- Python: `3.13` 以上。`pyproject.toml` の `requires-python` に定義。
- uv: `0.10.12` で検証済み。

### セットアップ

lockfile に記録した依存をインストールします。

```sh
uv sync --locked
```

- 仮想環境: `.venv/` に作成。
- 直接依存: `pyproject.toml` で完全なバージョンを指定。
- 間接依存: `uv.lock` で固定。
- テスト依存: `dev` グループも標準でインストール。
- 実行時: `uv run` を使うため、仮想環境の手動 activate は不要。

## 起動と API の確認

### 開発サーバー

```sh
uv run --locked uvicorn app.main:app --reload --host localhost --port 8000
```

- API: `http://localhost:8000`。
- OpenAPI ドキュメント: `http://localhost:8000/docs`。
- `--reload`: ソース変更時にサーバーを再起動。
- 終了: `Ctrl+C`。

### Hello World

別ターミナルからレスポンスを確認できます。

```sh
curl http://localhost:8000/hello
```

- メソッド・パス: `GET /hello`。
- HTTP ステータス: `200`。
- 本文: `{"message":"Hello World"}`。

### CORS

ブラウザーからのアクセスは `http://localhost:5173` を許可します。

- 設定場所: `app/main.py` の `CORSMiddleware`。
- 許可メソッド: `GET`。
- credentials: 許可しません。
- `http://127.0.0.1:5173`: 別 Origin のため対象外。

CORS はブラウザーがレスポンスを読み取れるかの制御です。`curl` の疎通だけではブラウザーの動作は確認できないため、[e2e テスト](../e2e/README.md)も使用します。

## テスト

### 実行コマンド

```sh
uv run --locked pytest
```

### 確認する内容

- `/hello` のステータスと JSON 本文。
- 許可 Origin に対する CORS ヘッダー。
- 未許可 Origin に許可ヘッダーを付けないこと。

## 操作のまとめ

- セットアップ: `uv sync --locked`。
- 開発: Uvicorn を `--reload` 付きで起動。
- 検証: `uv run --locked pytest`。
