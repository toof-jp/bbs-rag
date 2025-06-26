#!/usr/bin/env python3
"""Create vector index for GraphRAG system from RAG database posts."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import get_rag_db
from app.models.graph import Post


async def create_index(batch_size: int = 100) -> None:
    """Create vector index from posts in RAG database.

    Args:
        batch_size: Number of posts to process in each batch
    """
    print("🚀 Starting GraphRAG vector index creation...")

    # Initialize embeddings
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )

    # Initialize vector store
    vectorstore = Chroma(
        collection_name=settings.collection_name,
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_directory,
    )

    with get_rag_db() as session:
        # Get total count
        total_count = session.execute(select(func.count()).select_from(Post)).scalar() or 0

        if total_count == 0:
            print("❌ No posts found in RAG database. Run sync pipeline first.")
            return

        print(f"📄 Found {total_count} posts in RAG database")

        # Process in batches
        offset = 0
        processed = 0

        while offset < total_count:
            # Get batch of posts
            posts = (
                session.execute(
                    select(Post).order_by(Post.source_post_no).limit(batch_size).offset(offset)
                )
                .scalars()
                .all()
            )

            if not posts:
                break

            # Convert to documents
            documents = []
            for post in posts:
                doc = Document(
                    page_content=post.content,
                    metadata={
                        "post_id": str(post.post_id),
                        "source_post_no": post.source_post_no,
                        "timestamp": post.timestamp.isoformat(),
                        "source": f"graphrag_post_{post.source_post_no}",
                    },
                )
                documents.append(doc)

            # Add to vector store
            try:
                vectorstore.add_documents(documents)
                processed += len(documents)
                print(f"   Progress: {processed}/{total_count} posts indexed")
            except Exception as e:
                print(f"❌ Error indexing batch: {e}")
                raise

            offset += batch_size

    print("✅ GraphRAG vector index creation completed successfully!")
    print(f"📊 Total posts indexed: {processed}")


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Create vector index for GraphRAG")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for processing (default: 100)",
    )

    args = parser.parse_args()

    try:
        await create_index(batch_size=args.batch_size)
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
