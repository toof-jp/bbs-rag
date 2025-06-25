# BBS RAG Backend

## セットアップ

### 1. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集して、必要な情報を設定
```

### 2. 依存関係のインストール (uvを使用)

```bash
# uvのインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存関係のインストール
make install

# 開発用依存関係も含める場合
make install-dev
```

### 3. ベクトルインデックスの作成

```bash
# 初回のフルインデックス作成
make create-index

# 増分更新（新しい投稿のみ）
make update-index
```

### 4. 開発サーバーの起動

```bash
make dev
# または
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 開発コマンド

```bash
# コードのフォーマット
make format

# リント実行
make lint

# テスト実行
make test
```

## API仕様

開発サーバー起動後、以下のURLでAPIドキュメントを確認できます：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json