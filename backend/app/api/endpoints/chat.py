"""Chat endpoint for RAG queries."""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.rag.graphrag_chain import graphrag_chain
from app.rag.schemas import QuestionRequest, StreamToken

router = APIRouter()


async def generate_stream(question: str, conversation_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE stream for the answer.

    Args:
        question: The question to answer
        conversation_id: Conversation ID for tracking (not used in GraphRAG)

    Yields:
        SSE formatted events
    """
    try:
        # Stream tokens using GraphRAG chain
        async for token in graphrag_chain.astream(question):
            # Format as SSE event
            event_data = StreamToken(token=token).model_dump_json()
            yield f"data: {event_data}\n\n"

        # Send completion event
        completion_data = json.dumps({"type": "complete"})
        yield f"data: {completion_data}\n\n"

    except Exception as e:
        # Send error event
        error_data = json.dumps({"type": "error", "message": str(e)})
        yield f"data: {error_data}\n\n"


@router.post("/ask")
async def ask_question(request: QuestionRequest) -> EventSourceResponse:
    """Ask a question about the bulletin board content.

    This endpoint streams the answer using Server-Sent Events (SSE).

    Args:
        request: Question request with question text and optional conversation ID

    Returns:
        EventSourceResponse streaming the answer tokens
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Use provided conversation_id or generate a default one
    conversation_id = request.conversation_id or "default"

    return EventSourceResponse(
        generate_stream(request.question, conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )
