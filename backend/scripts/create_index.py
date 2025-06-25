#!/usr/bin/env python
"""
インデックス作成スクリプト

使用方法:
    cd backend
    uv run python scripts/create_index.py
"""
import asyncio
import sys
import time
from pathlib import Path

from tqdm import tqdm

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(str(Path(__file__).parent.parent))


from app.core.config import settings
from app.core.database import SessionLocal
from app.models.res import Res
from app.rag.loader import PostgresResLoader, ThreadAwareLoader
from app.rag.retriever import get_parent_document_retriever, get_vector_store


async def create_index():
    """ベクトルインデックスを作成"""
    print("Starting index creation process...")

    # データベースのレコード数を確認
    db = SessionLocal()
    try:
        res_count = db.query(Res).count()
        print(f"Found {res_count} records in res table")

        if res_count == 0:
            print("No records found in res table. Please ensure data is loaded.")
            return
    finally:
        db.close()

    # ローダーの初期化
    print("Initializing document loaders...")
    base_loader = PostgresResLoader(batch_size=100)
    # スライディングウィンドウ: 50レスごと、20レス重複
    parent_loader = ThreadAwareLoader(window_size=50, overlap=20)

    # デバッグ: まず基本ローダーで数件読み込んでみる
    print("Testing base loader...")
    test_docs = list(base_loader.lazy_load())[:5]
    if test_docs:
        print(f"✓ Base loader working. Sample document: {test_docs[0].page_content[:100]}...")
    else:
        print("✗ Base loader returned no documents")
        return

    # ベクトルストアとretrieverの取得
    print("Setting up vector store and retriever...")
    vector_store = get_vector_store()

    # 既存のインデックスをクリア（オプション）
    print("Clearing existing index...")
    try:
        # Chromaコレクションをリセット
        vector_store.delete_collection()
        print("Existing index cleared")
    except Exception as e:
        print(f"No existing index to clear or error: {e}")

    # ベクトルストアとretrieverを再作成
    print("Creating new vector store and retriever...")
    vector_store = get_vector_store()
    retriever = get_parent_document_retriever(vector_store)

    # 親ドキュメントと子ドキュメントの準備
    print("\nLoading parent documents...")
    parent_docs = []

    # まずドキュメントを読み込み（プログレスバーなしで確認）
    print("Loading documents (this may take a few minutes)...")
    doc_count = 0
    start_time = time.time()

    for doc in parent_loader.lazy_load():
        parent_docs.append(doc)
        doc_count += 1

        # 100件ごとに進捗を表示
        if doc_count % 100 == 0:
            elapsed = time.time() - start_time
            rate = doc_count / elapsed
            estimated_total = (res_count + 49) // 50
            estimated_remaining = (estimated_total - doc_count) / rate if rate > 0 else 0
            print(
                f"  Loaded {doc_count} documents... " f"(~{estimated_remaining:.0f}s remaining)",
                end="\r",
            )

    print(f"\n✓ Created {len(parent_docs)} parent documents")

    # ドキュメントをretrieverに追加
    print("\nAdding documents to vector store...")
    if parent_docs:
        # バッチ処理で追加
        batch_size = 10  # 元のバッチサイズに戻す
        # total_batches = (len(parent_docs) + batch_size - 1) // batch_size

        with tqdm(total=len(parent_docs), desc="Indexing documents", unit="docs") as pbar:
            for i in range(0, len(parent_docs), batch_size):
                batch = parent_docs[i : i + batch_size]

                try:
                    retriever.add_documents(batch)
                    pbar.update(len(batch))

                    # 進捗率を表示
                    progress = (i + batch_size) / len(parent_docs) * 100
                    pbar.set_postfix({"progress": f"{min(progress, 100):.1f}%"})

                except Exception as e:
                    print(f"\n⚠️  Error at batch {i//batch_size + 1}: {e}")
                    print(f"Error details: {type(e).__name__}: {e}")
                    print(f"Skipping batch {i//batch_size + 1}")
                    continue

    print("Index creation completed successfully!")

    # インデックスの統計情報を表示
    print("\nIndex Statistics:")
    print(f"- Total parent documents: {len(parent_docs)}")
    if parent_docs:
        total_res = sum(doc.metadata.get("res_count", 0) for doc in parent_docs)
        print(f"- Total res covered: {total_res}")
        print(f"- Average res per parent document: {total_res / len(parent_docs):.1f}")


def main():
    """メイン関数"""
    # 環境変数の確認
    if not settings.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY is not set in environment variables")
        sys.exit(1)

    if not settings.DATABASE_URL:
        print("Error: DATABASE_URL is not set in environment variables")
        sys.exit(1)

    print("=== BBS RAG Index Creation ===")
    db_url = (
        settings.DATABASE_URL.split("@")[1]
        if "@" in settings.DATABASE_URL
        else settings.DATABASE_URL
    )
    print(f"Database: {db_url}")
    print(f"Collection: {settings.COLLECTION_NAME}")
    print(f"LLM Model: {settings.OPENAI_MODEL}")
    print(f"Embedding Model: {settings.OPENAI_EMBEDDING_MODEL}")
    print("==============================\n")

    # 開始時間を記録
    start_time = time.time()

    # インデックス作成の実行
    asyncio.run(create_index())

    # 実行時間を表示
    elapsed_time = time.time() - start_time
    print(f"\n✓ Total execution time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")


if __name__ == "__main__":
    main()
