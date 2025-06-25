"""Data structures for the RAG pipeline."""

from typing import Optional

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Request model for asking questions."""

    question: str = Field(..., description="The question to ask about the bulletin board")
    conversation_id: Optional[str] = Field(
        None, description="Optional conversation ID for tracking"
    )


class StreamToken(BaseModel):
    """Model for streaming tokens."""

    token: str = Field(..., description="The token to stream")
    type: str = Field(default="token", description="Type of the stream message")


class CitationPost(BaseModel):
    """Model for cited post information."""

    no: int = Field(..., description="Post number")
    name_and_trip: str = Field(..., description="Author name and trip")
    datetime: str = Field(..., description="Post datetime")
    content: str = Field(..., description="Post content excerpt")


class AnswerResponse(BaseModel):
    """Response model for answers with citations."""

    answer: str = Field(..., description="The generated answer")
    citations: list[CitationPost] = Field(default_factory=list, description="List of cited posts")
