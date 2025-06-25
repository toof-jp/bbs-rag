#!/usr/bin/env python3
"""Create vector index from bulletin board posts."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.rag.loader import PostgresResLoader
from app.rag.retriever import SlidingWindowChunker, create_retriever


def load_index_metadata() -> dict[str, Any]:
    """Load index metadata from file."""
    metadata_path = Path("index_metadata.json")
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            data: dict[str, Any] = json.load(f)
            return data
    return {"last_processed_no": 0, "last_updated": None}


def save_index_metadata(metadata: dict[str, Any]) -> None:
    """Save index metadata to file."""
    with open("index_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)


async def create_index(incremental: bool = False) -> None:
    """Create or update the vector index.

    Args:
        incremental: If True, only process new posts since last update
    """
    print("🚀 Starting index creation...")

    # Load metadata
    metadata = load_index_metadata()
    start_no = None

    if incremental and metadata["last_processed_no"] > 0:
        start_no = metadata["last_processed_no"] + 1
        print(f"📊 Incremental update: Starting from post No.{start_no}")
    else:
        print("📊 Full index creation")

    # Initialize loader
    loader = PostgresResLoader(start_no=start_no)

    # Load documents
    print("📖 Loading posts from database...")
    documents = loader.load()

    if not documents:
        print("✅ No new posts to process")
        return

    print(f"📄 Loaded {len(documents)} posts")

    # Create sliding windows
    print("🪟 Creating sliding windows...")
    chunker = SlidingWindowChunker(
        window_size=settings.window_size,
        overlap=settings.window_overlap,
    )
    windows = chunker.create_windows(documents)
    print(f"📦 Created {len(windows)} windows")

    # Initialize retriever
    print("🔧 Initializing retriever...")
    retriever = create_retriever()

    # Add documents to index
    print("💾 Adding documents to vector store...")

    # Add documents in batches to show progress
    batch_size = 10
    for i in range(0, len(windows), batch_size):
        batch = windows[i : i + batch_size]
        retriever.add_documents(batch)
        progress = min(i + batch_size, len(windows))
        print(f"   Progress: {progress}/{len(windows)} windows indexed")

    # Update metadata
    if documents:
        last_no = max(doc.metadata["no"] for doc in documents)
        metadata["last_processed_no"] = last_no
        metadata["last_updated"] = datetime.now().isoformat()
        save_index_metadata(metadata)
        print(f"📝 Updated metadata: last processed No.{last_no}")

    print("✅ Index creation completed successfully!")


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Create vector index for BBS RAG")
    parser.add_argument(
        "--incremental",
        "-i",
        action="store_true",
        help="Perform incremental update instead of full rebuild",
    )

    args = parser.parse_args()

    try:
        await create_index(incremental=args.incremental)
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
