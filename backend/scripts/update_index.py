#!/usr/bin/env python
"""
インデックス差分更新スクリプト

使用方法:
    cd backend
    uv run python scripts/update_index.py
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from collections.abc import Iterator
from typing import Any

from langchain_core.documents import Document
from sqlalchemy import func

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.res import Res
from app.rag.loader import PostgresResLoader, ThreadAwareLoader
from app.rag.retriever import get_parent_document_retriever, get_vector_store

# メタデータファイルのパス
METADATA_FILE = os.path.join(os.path.dirname(__file__), "../index_metadata.json")


def load_metadata() -> dict[str, Any]:
    """インデックスのメタデータを読み込む"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE) as f:
            data: dict[str, Any] = json.load(f)
            return data
    return {"last_processed_no": 0, "last_update": None}


def save_metadata(metadata: dict[str, Any]) -> None:
    """インデックスのメタデータを保存"""
    metadata["last_update"] = datetime.now().isoformat()
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)


class IncrementalPostgresResLoader(PostgresResLoader):
    """差分更新用のローダー"""

    def __init__(self, start_no: int, batch_size: int = 1000):
        super().__init__(batch_size)
        self.start_no = start_no

    def lazy_load(self) -> Iterator[Document]:
        """指定されたレス番号以降のデータを読み込む"""
        db = SessionLocal()
        try:
            last_no = self.start_no
            batch_count = 0
            total_processed = 0

            while True:
                # 新しいレスのみを取得
                res_list = (
                    db.query(Res)
                    .filter(Res.no > last_no)
                    .order_by(Res.no)
                    .limit(self.batch_size)
                    .all()
                )

                if not res_list:
                    break

                batch_count += 1
                total_processed += len(res_list)

                if batch_count % 10 == 0:
                    print(f"  [IncrementalLoader] Processed {total_processed} new records...")

                for res in res_list:
                    content = f"No.{res.no}: {res.main_text}"
                    metadata = {
                        "no": res.no,
                        "id": res.id,
                        "datetime": res.datetime.isoformat() if res.datetime else "",
                        "datetime_text": res.datetime_text,
                        "name_and_trip": res.name_and_trip,
                        "source": f"res_no_{res.no}",
                    }

                    yield Document(page_content=content, metadata=metadata)

                last_no = int(res_list[-1].no)
        finally:
            db.close()


class IncrementalThreadAwareLoader(ThreadAwareLoader):
    """差分更新用のスライディングウィンドウローダー"""

    def __init__(self, start_no: int, window_size: int = 50, overlap: int = 20):
        super().__init__(window_size, overlap)
        self.start_no = start_no
        # 境界付近の再構築のため、少し前から開始
        self.rebuild_start = max(0, start_no - window_size)

    def lazy_load(self) -> Iterator[Document]:
        """新しいレスを含むウィンドウを生成"""
        # ベースローダーを差分用に変更
        self.base_loader = IncrementalPostgresResLoader(self.rebuild_start)

        # 親クラスの処理を呼び出す
        yield from super().lazy_load()


async def update_index() -> None:
    """インデックスを差分更新"""
    print("Starting incremental index update...")

    # メタデータを読み込む
    metadata = load_metadata()
    last_processed_no = metadata.get("last_processed_no", 0)

    print(f"Last processed res no: {last_processed_no}")

    # データベースから最新のレス番号を取得
    db = SessionLocal()
    try:
        latest_no = db.query(func.max(Res.no)).scalar() or 0
        new_res_count = db.query(Res).filter(Res.no > last_processed_no).count()

        if new_res_count == 0:
            print("No new res found. Index is up to date.")
            return

        print(f"Found {new_res_count} new res (No.{last_processed_no + 1} to No.{latest_no})")
    finally:
        db.close()

    # ローダーの初期化
    print("Initializing incremental loaders...")
    # 境界付近のウィンドウを再構築するため、少し前から開始
    parent_loader = IncrementalThreadAwareLoader(
        start_no=last_processed_no, window_size=50, overlap=20
    )

    # ベクトルストアとretrieverの取得（既存のものを使用）
    print("Getting existing vector store and retriever...")
    vector_store = get_vector_store()
    retriever = get_parent_document_retriever(vector_store)

    # 新しい親ドキュメントを読み込み
    print("\nLoading new parent documents...")
    parent_docs = []
    doc_count = 0
    start_time = time.time()

    for doc in parent_loader.lazy_load():
        parent_docs.append(doc)
        doc_count += 1

        if doc_count % 10 == 0:
            elapsed = time.time() - start_time
            rate = doc_count / elapsed if elapsed > 0 else 0
            print(f"  Loaded {doc_count} documents... (rate: {rate:.1f} docs/s)", end="\r")

    print(f"\n✓ Created {len(parent_docs)} parent documents for update")

    # ドキュメントをretrieverに追加
    if parent_docs:
        print("\nAdding new documents to vector store...")
        batch_size = 10

        with tqdm(total=len(parent_docs), desc="Updating index", unit="docs") as pbar:
            for i in range(0, len(parent_docs), batch_size):
                batch = parent_docs[i : i + batch_size]

                try:
                    retriever.add_documents(batch)
                    pbar.update(len(batch))

                    progress = (i + batch_size) / len(parent_docs) * 100
                    pbar.set_postfix({"progress": f"{min(progress, 100):.1f}%"})

                except Exception as e:
                    print(f"\n⚠️  Error at batch {i//batch_size + 1}: {e}")
                    print(f"Error details: {type(e).__name__}: {e}")
                    print(f"Skipping batch {i//batch_size + 1}")
                    continue

    # メタデータを更新
    metadata["last_processed_no"] = latest_no
    save_metadata(metadata)

    print("\nIndex update completed successfully!")
    print(f"Updated last_processed_no to: {latest_no}")

    # 統計情報を表示
    print("\nUpdate Statistics:")
    print(f"- New parent documents added: {len(parent_docs)}")
    print(f"- New res processed: {new_res_count}")
    print(f"- Last update: {metadata['last_update']}")


def main() -> None:
    """メイン関数"""
    # 環境変数の確認
    if not settings.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY is not set in environment variables")
        sys.exit(1)

    if not settings.DATABASE_URL:
        print("Error: DATABASE_URL is not set in environment variables")
        sys.exit(1)

    print("=== BBS RAG Incremental Index Update ===")
    db_url = (
        settings.DATABASE_URL.split("@")[1]
        if "@" in settings.DATABASE_URL
        else settings.DATABASE_URL
    )
    print(f"Database: {db_url}")
    print(f"Collection: {settings.COLLECTION_NAME}")
    print("========================================\n")

    # 開始時間を記録
    start_time = time.time()

    # インデックス更新の実行
    asyncio.run(update_index())

    # 実行時間を表示
    elapsed_time = time.time() - start_time
    print(f"\n✓ Total execution time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")


if __name__ == "__main__":
    main()
