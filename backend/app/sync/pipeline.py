"""Data synchronization pipeline for GraphRAG system."""

import logging
from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_rag_db, get_source_db
from app.models.graph import Post, Relationship

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataSyncPipeline:
    """Pipeline for syncing data from source DB to GraphRAG DB."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            api_key=settings.openai_api_key,
        )
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

    def get_last_processed_no(self, rag_session: Session) -> int:
        """Get the last processed post number from RAG DB."""
        result = rag_session.execute(select(func.max(Post.source_post_no))).scalar()
        return result or 0

    def extract_new_posts(
        self, source_session: Session, last_no: int, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """Extract new posts from source DB."""
        query = text(
            """
            SELECT no, name_and_trip, datetime, id, main_text
            FROM public.res
            WHERE no > :last_no
            ORDER BY no ASC
            LIMIT :limit
        """
        )

        result = source_session.execute(query, {"last_no": last_no, "limit": limit})
        posts = []
        for row in result:
            posts.append(
                {
                    "no": row.no,
                    "name_and_trip": row.name_and_trip,
                    "datetime": row.datetime,
                    "id": row.id,
                    "main_text": row.main_text,
                }
            )
        return posts

    def create_post_node(self, post_data: dict[str, Any]) -> Post:
        """Create a Post node from raw post data."""
        return Post(
            source_post_no=post_data["no"],
            content=post_data["main_text"],
            timestamp=post_data["datetime"],
        )

    def infer_reply_relationships(
        self, post: Post, rag_session: Session, context_window: int = 50
    ) -> list[Relationship]:
        """Infer IS_REPLY_TO relationships using LLM."""
        # Get recent posts for context
        recent_posts = (
            rag_session.execute(
                select(Post)
                .where(Post.source_post_no < post.source_post_no)
                .order_by(Post.source_post_no.desc())
                .limit(context_window)
            )
            .scalars()
            .all()
        )

        if not recent_posts:
            return []

        # Build context for LLM
        context = "\n".join(
            [f"No.{p.source_post_no}: {p.content[:200]}..." for p in reversed(recent_posts)]
        )

        # Ask LLM to identify reply relationships
        prompt = f"""Given the following conversation context, identify which \
post numbers (if any) the new post No.{post.source_post_no} is replying to.

Context:
{context}

New post No.{post.source_post_no}:
{post.content}

Return only the post numbers that this post is directly replying to, separated by commas. \
If it's not replying to any specific post, return "NONE".
Example valid responses: "123,145" or "NONE"
"""

        response = self.llm.invoke(prompt)
        reply_text = response.content.strip()

        relationships = []
        if reply_text != "NONE" and reply_text:
            try:
                reply_nos = [int(no.strip()) for no in reply_text.split(",")]
                for reply_no in reply_nos:
                    # Find the target post
                    target_post = rag_session.execute(
                        select(Post).where(Post.source_post_no == reply_no)
                    ).scalar_one_or_none()

                    if target_post:
                        relationships.append(
                            Relationship(
                                source_node_id=post.post_id,
                                target_node_id=target_post.post_id,
                                relationship_type="IS_REPLY_TO",
                                properties={"confidence": 0.8},
                            )
                        )
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse reply relationships: {e}")

        return relationships

    def create_sequential_relationships(
        self,
        post: Post,
        source_session: Session,
        rag_session: Session,
        window_size: int = 20,
    ) -> list[Relationship]:
        """Create IS_SEQUENTIAL_TO relationships for subsequent posts."""
        # Get subsequent posts from source DB
        query = text(
            """
            SELECT no FROM public.res
            WHERE no > :current_no
            ORDER BY no ASC
            LIMIT :limit
        """
        )

        result = source_session.execute(
            query, {"current_no": post.source_post_no, "limit": window_size}
        )

        relationships = []
        for row in result:
            # Check if the subsequent post exists in RAG DB
            target_post = rag_session.execute(
                select(Post).where(Post.source_post_no == row.no)
            ).scalar_one_or_none()

            if target_post:
                relationships.append(
                    Relationship(
                        source_node_id=post.post_id,
                        target_node_id=target_post.post_id,
                        relationship_type="IS_SEQUENTIAL_TO",
                        properties={"distance": row.no - post.source_post_no},
                    )
                )

        return relationships

    def sync_batch(self, batch_size: int = 100) -> int:
        """Sync a batch of posts from source to RAG DB."""
        processed_count = 0

        with get_source_db() as source_db, get_rag_db() as rag_db:
            # Get last processed post number
            last_no = self.get_last_processed_no(rag_db)
            logger.info(f"Starting sync from post No.{last_no + 1}")

            # Extract new posts
            new_posts = self.extract_new_posts(source_db, last_no, batch_size)
            if not new_posts:
                logger.info("No new posts to sync")
                return 0

            logger.info(f"Found {len(new_posts)} new posts to sync")

            # Process each post
            for post_data in new_posts:
                try:
                    # Create post node
                    post = self.create_post_node(post_data)
                    rag_db.add(post)
                    rag_db.flush()  # Get the post_id

                    # Infer reply relationships
                    reply_rels = self.infer_reply_relationships(post, rag_db)
                    for rel in reply_rels:
                        rag_db.add(rel)

                    # Create sequential relationships
                    seq_rels = self.create_sequential_relationships(post, source_db, rag_db)
                    for rel in seq_rels:
                        rag_db.add(rel)

                    processed_count += 1

                    if processed_count % 10 == 0:
                        logger.info(f"Processed {processed_count}/{len(new_posts)} posts")

                except Exception as e:
                    logger.error(f"Error processing post No.{post_data['no']}: {e}")
                    rag_db.rollback()
                    raise

            # Commit all changes
            rag_db.commit()
            logger.info(f"Successfully synced {processed_count} posts")

        return processed_count

    def sync_all(self, batch_size: int = 100) -> int:
        """Sync all posts from source to RAG DB."""
        total_processed = 0
        
        logger.info(f"Starting full sync with batch_size={batch_size}")
        
        while True:
            count = self.sync_batch(batch_size)
            total_processed += count
            
            if count == 0:
                # No more posts to sync
                break
                
            logger.info(f"Total processed so far: {total_processed}")
            
        logger.info(f"Full sync completed. Total posts synced: {total_processed}")
        return total_processed

    def run_continuous_sync(self, batch_size: int = 100, interval_seconds: int = 60) -> None:
        """Run continuous synchronization."""
        import time

        logger.info(
            f"Starting continuous sync with batch_size={batch_size}, "
            f"interval={interval_seconds}s"
        )

        while True:
            try:
                count = self.sync_batch(batch_size)
                if count == 0:
                    logger.info(f"No new data. Sleeping for {interval_seconds} seconds...")
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                logger.info("Sync interrupted by user")
                break
            except Exception as e:
                logger.error(f"Sync error: {e}")
                logger.info(f"Retrying in {interval_seconds} seconds...")
                time.sleep(interval_seconds)
