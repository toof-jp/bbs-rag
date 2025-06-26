"""GraphRAG database models."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.models.base import Base


class Post(Base):
    """Post node in the knowledge graph."""

    __tablename__ = "posts"

    post_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_post_no = Column(Integer, nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Relationship(Base):
    """Relationship edge between posts."""

    __tablename__ = "relationships"

    relationship_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_node_id = Column(
        UUID(as_uuid=True), ForeignKey("posts.post_id"), nullable=False, index=True
    )
    target_node_id = Column(
        UUID(as_uuid=True), ForeignKey("posts.post_id"), nullable=False, index=True
    )
    relationship_type = Column(
        String(50), nullable=False, index=True
    )  # IS_REPLY_TO, IS_SEQUENTIAL_TO
    properties = Column(
        JSONB, default={}
    )  # Additional properties like confidence score
    created_at = Column(DateTime(timezone=True), server_default=func.now())
