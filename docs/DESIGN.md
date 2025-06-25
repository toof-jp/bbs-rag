# 掲示板RAGアプリケーション設計書

## 1\. はじめに

### 1.1. 目的

本ドキュメントは、LangChainを利用して掲示板の過去ログを対象としたRetrieval Augmented Generation (RAG) アプリケーションを開発するための実装設計を定義する。ユーザーは自然言語で質問を投げかけることで、掲示板の文脈を理解した回答をリアルタイムで得ることができる。

### 1.2. 背景

アンカー機能（特定のレスへの返信機能）があまり使用されていない掲示板では、単純なキーワード検索では会話の流れや文脈を把握することが困難である。本システムでは、RAG技術、特にレスの前後の関係性を考慮した検索手法を用いることで、この課題を解決する。

### 1.3. 設計方針

  - **コンポーネントベース:** フロントエンド、バックエンド、データベース、RAGパイプラインを疎結合なコンポーネントとして設計し、拡張性とメンテナンス性を確保する。
  - **リアルタイム応答:** サーバーサイドイベント (SSE) を利用したストリーミング通信により、LLMの生成する回答をリアルタイムでフロントエンドに表示し、高いUXを実現する。
  - **型安全な開発:** OpenAPIによるAPI仕様の定義と、それに基づくクライアントコードの自動生成により、フロントエンドとバックエンド間の連携を型安全に進める。
  - **段階的実装:** まずは中核となるRAGパイプラインを構築し、その後、より高度な検索手法（Graph RAGなど）への拡張も視野に入れた設計とする。

## 2\. システムアーキテクチャ

### 2.1. 全体構成図

```mermaid
graph TD
    subgraph Browser
        A[Frontend (React/Vite)]
    end

    subgraph Server
        B[Backend (FastAPI/Python)]
        C[RAG Pipeline (LangChain)]
        D[Vector Store (PGVector)]
        E[Database (PostgreSQL)]
    end

    subgraph External Services
        F[LLM API (e.g., OpenAI)]
    end

    A -- HTTP/REST (OpenAPI) --> B
    B -- Ask Query --> C
    C -- Retrieve --> D
    C -- Load Context --> E
    C -- Generate --> F
    F -- Stream Tokens --> C
    C -- Stream Response --> B
    B -- SSE (Streaming) --> A
```

### 2.2. 技術スタック

| 領域 | 技術 | 役割・選定理由 |
| :--- | :--- | :--- |
| **Frontend** | Vite, React, TypeScript | 高速な開発サイクルと型安全性を持つモダンなSPA開発環境。 |
| **Backend** | Python, FastAPI, Uvicorn | Pythonの豊富なAI/MLライブラリ資産を活用でき、高速な非同期APIサーバーを容易に構築可能。 |
| **AI/RAG** | LangChain | RAGパイプラインの構築を効率化するフレームワーク。 |
| **Database** | PostgreSQL | 堅牢なリレーショナルデータベース。掲示板データの保存用。 |
| **Vector Store** | Chroma | 高速なローカルベクトルデータベース。追加のインフラ不要で、開発・運用が簡単。 |
| **LLM** | OpenAI API (GPT-4oなど) | (選択可能) 高性能な言語モデル。ストリーミング応答に対応。 |
| **API仕様** | OpenAPI 3.0 | APIスキーマの標準的な定義方法。各種ツールとの連携が容易。 |

## 3\. データベース設計

### 3.1. 使用データベース

  - **プライマリDB:** PostgreSQL
  - **ベクトルストア:** Chroma (ローカルファイルベース)

### 3.2. スキーマ定義

提供されたスキーマをそのまま利用する。

**Table: `public.res`**

```sql
CREATE TABLE public.res (
    no integer NOT NULL DEFAULT nextval('res_no_seq'::regclass),
    name_and_trip text NOT NULL,
    datetime timestamp without time zone NOT NULL,
    datetime_text text NOT NULL,
    id text NOT NULL,
    main_text text NOT NULL,
    main_text_html text NOT NULL,
    oekaki_id integer,
    CONSTRAINT res_pkey PRIMARY KEY (no)
);
```

### 3.3. ベクトルストアのデータ構造

Chromaに格納するドキュメントの構造は以下の通り。

  - **`page_content`**: 埋め込み対象となるテキスト。主にレス本文 (`main_text`) を格納する。
  - **`metadata`**: 検索や文脈再構築に利用する付加情報。
    ```json
    {
      "no": 123,
      "id": "abcdefg",
      "datetime": "2024-01-01T12:00:00",
      "name_and_trip": "名無しさん◆trip",
      "source": "res_no_123"
    }
    ```
  - **保存場所**: `backend/chroma_db/` ディレクトリに永続化される。

## 4\. バックエンド設計 (FastAPI)

### 4.1. ディレクトリ構成

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       └── chat.py        # /ask エンドポイント
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # 環境変数読み込み
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── chain.py         # RAGチェーンの定義
│   │   ├── loader.py        # カスタムDocument Loader
│   │   ├── retriever.py     # Retrieverの定義
│   │   └── schemas.py       # データ構造定義 (Pydantic)
│   └── __init__.py
│   └── main.py            # FastAPIアプリケーションのエントリポイント
├── scripts/
│   └── create_index.py      # インデックス作成用バッチスクリプト
├── .env                     # 環境変数ファイル
├── Dockerfile
└── requirements.txt
```

### 4.2. APIエンドポイント定義 (OpenAPI)

FastAPIが自動生成するOpenAPI仕様。ここでは主要なエンドポイントの定義を示す。

**`POST /api/v1/ask`**

  - **Summary:** 掲示板の内容に関する質問を受け付け、ストリーミングで回答を返す。
  - **Request Body:**
    ```json
    {
      "question": "string",
      "conversation_id": "string (optional)"
    }
    ```
  - **Responses:**
      - **`200 OK`**:
          - **Content-Type:** `text/event-stream`
          - **Description:** サーバーサイドイベント (SSE) 形式で回答のトークンをストリーミングする。

### 4.3. RAGパイプライン設計 (LangChain)

#### 4.3.1. フェーズ1: インデックス作成 (バッチ処理)

`scripts/create_index.py` として実装。

1.  **データローダー (`rag/loader.py`)**:
      - `psycopg2` を用いてPostgreSQLに接続し、`res`テーブルからデータを取得する`PostgresResLoader`を`BaseLoader`を継承して実装する。
2.  **テキスト分割/チャンキング戦略**:
      - **スライディングウィンドウ方式** を採用する。
      - **親ドキュメント**: 50レスを1ウィンドウとし、20レスずつ重複させながらスライド。これによりどこで区切っても文脈が保持される。
      - **子ドキュメント**: `ParentDocumentRetriever`により親ドキュメントをさらに400文字ごとに分割。
      - **出典特定**: 検索後、GPT-3.5-turboを使用して関連する具体的なレス番号を抽出。
3.  **埋め込みモデル**:
      - OpenAIの`text-embedding-3-small`など、コストと性能のバランスが良いモデルを選定する。
4.  **ベクトルストアへの格納**:
      - `langchain_community.vectorstores.Chroma` を使用。
      - 親ドキュメントと子ドキュメントを適切に設定し、`ParentDocumentRetriever`の`add_documents`メソッドを使用してインデックスを構築する。
      - データは `backend/chroma_db/` ディレクトリに永続化される。

#### 4.3.2. フェーズ2: 質問応答 (リアルタイム処理)

`rag/chain.py` に実装。

1.  **リトリーバー (`rag/retriever.py`)**:
      - インデックス作成済みのベクトルストアと`docstore`から`ParentDocumentRetriever`を初期化して使用する。
      - （高度化）`SelfQueryRetriever`のロジックを組み合わせ、`id`や期間でのフィルタリングを可能にする。
2.  **プロンプトテンプレート**:
      - 取得した文脈（親ドキュメント）と質問を効果的にLLMに渡すためのプロンプトを設計する。
    <!-- end list -->
    ```python
    from langchain_core.prompts import ChatPromptTemplate

    template = """
    あなたは賢い掲示板のアシスタントです。
    提供された掲示板の過去ログの文脈を元に、ユーザーの質問に日本語で回答してください。
    文脈に答えがない場合は、無理に答えを生成せず「分かりません」と回答してください。

    【文脈】
    {context}

    【質問】
    {question}
    """
    prompt = ChatPromptTemplate.from_template(template)
    ```
3.  **LLM**:
      - `ChatOpenAI`など、ストリーミングに対応したモデルを利用する。
4.  **ストリーミング応答**:
      - FastAPIの`StreamingResponse`とLangChainの`AsyncIteratorCallbackHandler`を組み合わせる。LLMからの生成トークンを非同期イテレータ経由で受け取り、そのままSSEイベントとしてクライアントに送信する。

### 4.4. 環境変数管理 (`.env`)

```ini
# PostgreSQL
DATABASE_URL="postgresql://user:password@localhost:5432/bbs2"

# OpenAI
OPENAI_API_KEY="sk-..."

# PGVector
COLLECTION_NAME="bbs_rag_collection"
```

## 5\. フロントエンド設計 (React + Vite)

### 5.1. ディレクトリ構成

```
frontend/
├── public/
├── src/
│   ├── api/                 # OpenAPI Generatorで生成されたクライアント
│   ├── components/
│   │   ├── ChatInterface.tsx
│   │   ├── Message.tsx
│   │   └── InputForm.tsx
│   ├── App.tsx
│   ├── main.tsx
│   └── styles/
├── index.html
├── openapi-generator-config.json
├── package.json
└── tsconfig.json
```

### 5.2. APIクライアント

  - バックエンドのFastAPIサーバーを起動し、`/openapi.json`にアクセスする。
  - `openapi-generator-cli` を使用し、上記のJSONからTypeScriptのAPIクライアント (`src/api/`) を自動生成する。
    ```bash
    openapi-generator-cli generate -i http://localhost:8000/openapi.json -g typescript-fetch -o src/api
    ```

### 5.3. ストリーミングデータのハンドリング

  - `fetch` APIを使用してバックエンドに`POST /api/v1/ask`リクエストを送信する。
  - レスポンスの`body`は`ReadableStream`なので、`TextDecoder`を用いてチャンクをデコードし、リアルタイムでReactのstateに追記していくことで、タイプライターのような表示効果を実現する。

<!-- end list -->

```typescript
// ChatInterface.tsx の一部
const handleSend = async (question: string) => {
  setMessages(prev => [...prev, { role: 'user', content: question }]);
  const response = await fetch('/api/v1/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  if (response.body) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let aiResponse = '';
    
    // AIアシスタントのメッセージを初期化
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      // SSEのデータ部分をパース
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.substring(6);
          if (data) {
            aiResponse += JSON.parse(data).token;
            // 最後のメッセージを更新
            setMessages(prev => {
              const newMessages = [...prev];
              newMessages[newMessages.length - 1].content = aiResponse;
              return newMessages;
            });
          }
        }
      }
    }
  }
};
```

## 6\. 開発・運用

### 6.1. 開発環境構築

  - `docker-compose.yml` を作成し、フロントエンド、バックエンド、PostgreSQL(PGVector含む)のコンテナを一括で起動できるようにする。
  - これにより、開発者間の環境差異をなくし、セットアップを容易にする。

### 6.2. インデックス更新戦略

  - 新しいレスが投稿された際のインデックス更新は、以下のいずれかの戦略を取る。
    1.  **定時バッチ処理:** 夜間などに`scripts/create_index.py`をcronジョブとして実行し、差分または全データを再インデックスする。
    2.  **イベントドリブン:** (高度) データベースのトリガーなどを利用して、新規投稿をイベントとして検知し、インデックス更新用のマイクロサービスを呼び出す。
  - 初期実装では、運用負荷の低い**定時バッチ処理**を推奨する。
