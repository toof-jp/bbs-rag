"""Graph traversal logic for GraphRAG."""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select, text
from sqlalchemy.orm import Session

from app.models.graph import Post, Relationship

logger = logging.getLogger(__name__)


class GraphTraverser:
    """Traverse the knowledge graph to collect context."""

    def __init__(self, max_depth: int = 3, max_nodes: int = 50):
        """Initialize the graph traverser.
        
        Args:
            max_depth: Maximum depth for graph traversal
            max_nodes: Maximum number of nodes to collect
        """
        self.max_depth = max_depth
        self.max_nodes = max_nodes

    def get_related_posts_recursive(
        self, 
        session: Session, 
        start_post_ids: list[UUID], 
        relationship_types: Optional[list[str]] = None
    ) -> list[Post]:
        """Get related posts using recursive SQL query.
        
        Args:
            session: Database session
            start_post_ids: Starting post IDs
            relationship_types: Types of relationships to follow (None = all)
            
        Returns:
            List of related posts
        """
        if not start_post_ids:
            return []

        # Build relationship type filter
        rel_filter = ""
        if relationship_types:
            types_str = ",".join(f"'{t}'" for t in relationship_types)
            rel_filter = f"AND r.relationship_type IN ({types_str})"

        # Recursive CTE query to traverse the graph
        query = text(f"""
        WITH RECURSIVE graph_traversal AS (
            -- Base case: starting posts
            SELECT 
                p.post_id,
                p.source_post_no,
                p.content,
                p.timestamp,
                0 as depth,
                ARRAY[p.post_id] as path
            FROM posts p
            WHERE p.post_id = ANY(:start_ids)
            
            UNION ALL
            
            -- Recursive case: follow relationships
            SELECT 
                p.post_id,
                p.source_post_no,
                p.content,
                p.timestamp,
                gt.depth + 1,
                gt.path || p.post_id
            FROM graph_traversal gt
            JOIN relationships r ON (
                (r.source_node_id = gt.post_id OR r.target_node_id = gt.post_id)
                {rel_filter}
            )
            JOIN posts p ON (
                p.post_id = CASE 
                    WHEN r.source_node_id = gt.post_id THEN r.target_node_id
                    ELSE r.source_node_id
                END
            )
            WHERE 
                gt.depth < :max_depth
                AND NOT p.post_id = ANY(gt.path)  -- Avoid cycles
        )
        SELECT DISTINCT 
            post_id,
            source_post_no,
            content,
            timestamp
        FROM graph_traversal
        ORDER BY source_post_no
        LIMIT :max_nodes
        """)

        result = session.execute(
            query,
            {
                "start_ids": start_post_ids,
                "max_depth": self.max_depth,
                "max_nodes": self.max_nodes,
            }
        )

        posts = []
        for row in result:
            post = Post(
                post_id=row.post_id,
                source_post_no=row.source_post_no,
                content=row.content,
                timestamp=row.timestamp,
            )
            posts.append(post)

        return posts

    def get_conversation_context(
        self, session: Session, start_post_ids: list[UUID]
    ) -> dict[str, Any]:
        """Get full conversation context starting from given posts.
        
        Args:
            session: Database session
            start_post_ids: Starting post IDs
            
        Returns:
            Dictionary containing posts and relationships
        """
        # Get reply-based context (semantic relationships)
        reply_posts = self.get_related_posts_recursive(
            session, start_post_ids, ["IS_REPLY_TO"]
        )
        
        # Get sequential context (structural relationships)
        sequential_posts = self.get_related_posts_recursive(
            session, start_post_ids, ["IS_SEQUENTIAL_TO"]
        )
        
        # Combine and deduplicate
        all_post_ids = set()
        all_posts = []
        
        for post in reply_posts + sequential_posts:
            if post.post_id not in all_post_ids:
                all_post_ids.add(post.post_id)
                all_posts.append(post)
        
        # Sort by post number
        all_posts.sort(key=lambda p: p.source_post_no)
        
        # Get relationships between these posts
        relationships = []
        if all_post_ids:
            rel_query = select(Relationship).where(
                and_(
                    Relationship.source_node_id.in_(all_post_ids),
                    Relationship.target_node_id.in_(all_post_ids)
                )
            )
            relationships = list(session.execute(rel_query).scalars().all())
        
        return {
            "posts": all_posts,
            "relationships": relationships,
            "stats": {
                "total_posts": len(all_posts),
                "reply_posts": len(reply_posts),
                "sequential_posts": len(sequential_posts),
                "total_relationships": len(relationships),
            }
        }

    def format_context_for_llm(self, context_data: dict[str, Any]) -> str:
        """Format the context data for LLM consumption.
        
        Args:
            context_data: Context data from get_conversation_context
            
        Returns:
            Formatted string for LLM
        """
        posts = context_data["posts"]
        relationships = context_data["relationships"]
        
        # Build post ID to number mapping
        id_to_no = {p.post_id: p.source_post_no for p in posts}
        
        # Format posts
        formatted_posts = []
        for post in posts:
            formatted_posts.append(
                f"No.{post.source_post_no} ({post.timestamp.strftime('%Y-%m-%d %H:%M:%S')}):\n"
                f"{post.content}\n"
            )
        
        # Format relationships
        formatted_rels = []
        for rel in relationships:
            source_no = id_to_no.get(rel.source_node_id, "?")
            target_no = id_to_no.get(rel.target_node_id, "?")
            formatted_rels.append(
                f"- No.{source_no} {rel.relationship_type} No.{target_no}"
            )
        
        # Combine into final context
        context = "=== CONVERSATION CONTEXT ===\n\n"
        context += "Posts:\n" + "\n---\n".join(formatted_posts)
        
        if formatted_rels:
            context += "\n\n=== RELATIONSHIPS ===\n"
            context += "\n".join(formatted_rels)
        
        context += "\n\n=== STATISTICS ===\n"
        for key, value in context_data["stats"].items():
            context += f"- {key}: {value}\n"
        
        return context