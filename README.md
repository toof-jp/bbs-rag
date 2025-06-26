# BBS RAG Application

掲示板の過去ログを対象としたRAG（Retrieval Augmented Generation）アプリケーション。LangChainとFastAPIを使用して構築され、リアルタイムストリーミング応答を提供します。

## 概要

このアプリケーションは、アンカー機能が十分に活用されていない掲示板において、会話の文脈を理解した検索と回答生成を実現します。

## 技術スタック

- **Backend**: Python, FastAPI, LangChain
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Database**: PostgreSQL (掲示板データ用)
- **Vector Store**: Chroma (ベクトル検索用)
- **AI/LLM**: OpenAI API (GPT-4o)

## セットアップ

### 前提条件

- Docker & Docker Compose
- OpenAI APIキー

### 環境変数の設定

1. プロジェクトルートに`.env`ファイルを作成:
```bash
cp .env.example .env
```

2. 必要な環境変数を設定:
```env
# PostgreSQL接続情報
DATABASE_URL=postgresql://user:password@localhost:5432/bbs2

# OpenAI APIキー
OPENAI_API_KEY=sk-your-api-key

# ベクトルストア設定
COLLECTION_NAME=bbs_rag_collection

# Backend設定
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Frontend設定（開発用）
VITE_API_URL=http://localhost:8000

# API CORS設定
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

**注意**: `.env`ファイルはプロジェクトルートに配置してください。backendとfrontendの両方がこのファイルを参照します。

### Dockerでの起動

```bash
# .envファイルが作成済みであることを確認
# （環境変数の設定セクションで作成済み）

# コンテナの起動
docker-compose up -d

# ログの確認
docker-compose logs -f
```

### インデックスの作成

初回起動時、または新しいデータを追加した後：

```bash
cd backend

# 仮想環境を有効化している場合
python scripts/create_index.py

# または、uvを使って直接実行
uv run python scripts/create_index.py
```

## 開発

### バックエンド開発

```bash
# uvのインストール（初回のみ）
curl -LsSf https://astral.sh/uv/install.sh | sh

cd backend
# 仮想環境の作成と有効化
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係のインストール
uv pip install -e .
uv pip install -e ".[dev]"  # 開発用依存関係も含める場合

# 開発サーバーの起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

APIドキュメント: http://localhost:8000/docs

### フロントエンド開発

```bash
cd frontend
npm install
npm run dev
```

アプリケーション: http://localhost:5173

### APIクライアントの生成

```bash
cd frontend
npm run generate-api
```

## アーキテクチャ

### RAGパイプライン

- **ParentDocumentRetriever**: 文脈を保持しながら効率的な検索を実現
  - 親ドキュメント: 50レス程度のスレッド単位
  - 子ドキュメント: 個別のレス

### ストリーミング応答

Server-Sent Events (SSE)を使用してリアルタイムでトークンをストリーミング

## プロジェクト構造

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # APIエンドポイント
│   │   ├── core/         # 設定、データベース接続
│   │   ├── models/       # SQLAlchemyモデル
│   │   └── rag/          # RAGパイプライン
│   └── scripts/          # インデックス作成スクリプト
├── frontend/
│   └── src/
│       ├── api/          # 自動生成されたAPIクライアント
│       └── components/   # Reactコンポーネント
└── docker-compose.yml
```

## ライセンス

[ライセンス情報を追加]