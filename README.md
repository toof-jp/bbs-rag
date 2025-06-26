# BBS RAG Application

掲示板の過去ログを対象としたGraphRAG（Graph-enhanced Retrieval Augmented Generation）アプリケーション。LangChainとFastAPIを使用して構築され、知識グラフとベクトル検索を組み合わせた高度な文脈理解とリアルタイムストリーミング応答を提供します。

## 概要

このアプリケーションは、アンカー機能が十分に活用されていない掲示板において、会話の文脈を理解した検索と回答生成を実現します。

## 技術スタック

- **Backend**: Python, FastAPI, LangChain
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Database**: 
  - PostgreSQL (ソースDB: 掲示板データ、読み取り専用)
  - PostgreSQL (RAG DB: 知識グラフとGraphRAG用)
- **Vector Store**: Chroma (ベクトル検索用)
- **Graph Processing**: LangGraph (ワークフローオーケストレーション)
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
# PostgreSQL Databases
DATABASE_URL=postgresql://user:password@localhost:5432/bbs2  # ソースDB (読み取り専用)
RAG_DATABASE_URL=postgresql://user:password@localhost:5432/bbs_rag  # RAG DB (GraphRAG用)

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

### GraphRAGシステムのセットアップ

GraphRAGシステムは3段階のセットアップが必要です：

#### 1. RAGデータベースの初期化

```bash
cd backend

# RAGデータベースのテーブルを作成
uv run python scripts/init_rag_db.py
```

#### 2. データの同期

ソースDBからRAG DBへデータを同期し、知識グラフを構築：

```bash
# 初回フル同期を実行（全ての投稿を同期）
uv run python scripts/sync_data.py --initial

# または、継続的な同期を開始（本番環境用）
uv run python scripts/sync_data.py --interval 60  # 60秒ごとに新規投稿をチェック
```

オプション：
- `--batch-size`: 一度に処理する投稿数（デフォルト: 100）
- `--initial`: 初回フル同期（全投稿を同期して終了）
- `--interval`: 継続的同期の間隔（秒）

#### 3. ベクトルインデックスの作成

RAG DB内の投稿からベクトルインデックスを作成：

```bash
uv run python scripts/create_graphrag_index.py
```

**注意**: 必ず上記の順番でセットアップを実行してください。データ同期により知識グラフ（IS_REPLY_TO、IS_SEQUENTIAL_TO関係）が構築され、GraphRAGシステムが高度な文脈理解を実現します。

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

### GraphRAGパイプライン

GraphRAG（Graph-enhanced RAG）は、従来のベクトル検索に知識グラフを組み合わせた高度なRAGシステムです：

#### 知識グラフ構造
- **ノード**: 投稿（posts）
- **エッジ**: 
  - `IS_REPLY_TO`: セマンティックな返信関係（LLMが推論）
  - `IS_SEQUENTIAL_TO`: 構造的な連続関係（次の20投稿）

#### 検索フロー（LangGraphワークフロー）
1. **Vector Retriever**: ベクトル類似度検索で初期投稿を取得
2. **Graph Traverser**: 知識グラフを再帰的に探索し関連投稿を収集
3. **Context Synthesizer**: 収集した投稿から重要な文脈を抽出
4. **Response Generator**: 文脈を基に回答を生成

### データ同期パイプライン

- ソースDB（読み取り専用）からRAG DBへの自動同期
- GPT-3.5-turboによる返信関係の推論
- インクリメンタルな更新対応

### ストリーミング応答

Server-Sent Events (SSE)を使用してリアルタイムでトークンをストリーミング

## プロジェクト構造

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # APIエンドポイント
│   │   ├── core/         # 設定、データベース接続
│   │   ├── models/       # SQLAlchemyモデル（ソースDBとGraphRAG）
│   │   ├── rag/          # GraphRAGパイプライン
│   │   │   ├── graphrag_chain.py  # LangGraphワークフロー
│   │   │   └── graph_traversal.py # 知識グラフ探索
│   │   └── sync/         # データ同期パイプライン
│   └── scripts/          
│       ├── init_rag_db.py          # RAG DB初期化
│       ├── sync_data.py            # データ同期実行
│       └── create_graphrag_index.py # ベクトルインデックス作成
├── frontend/
│   └── src/
│       ├── api/          # 自動生成されたAPIクライアント
│       └── components/   # Reactコンポーネント
└── docker-compose.yml
```

## 既存システムからの移行ガイド

旧バージョン（単純なRAG）からGraphRAGへ移行する場合：

1. 既存のChromaインデックスは保持されますが、RAG DBが新たに必要です
2. `scripts/create_index.py`の代わりに、上記の3段階セットアップを実行してください
3. 環境変数に`RAG_DATABASE_URL`を追加する必要があります

## トラブルシューティング

### RAG DBの初期化エラー
```
psql: FATAL: database "bbs_rag" does not exist
```
→ PostgreSQLに`bbs_rag`データベースを作成してください：
```bash
createdb bbs_rag
```

### データ同期が進まない
- ソースDBに接続できることを確認
- `DATABASE_URL`が正しく設定されていることを確認
- ログを確認: `docker-compose logs -f backend`

## ライセンス

[ライセンス情報を追加]