"""RAG chain implementation with streaming support."""

import asyncio
import json
from typing import Any, AsyncIterator, Optional
from uuid import UUID

from langchain.callbacks.base import AsyncCallbackHandler
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.rag.retriever import get_retriever
from app.rag.schemas import CitationPost


class StreamingCallbackHandler(AsyncCallbackHandler):
    """Callback handler for streaming tokens."""

    def __init__(self) -> None:
        self.tokens: asyncio.Queue[Optional[str]] = asyncio.Queue()
        self.done = False

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Called when a new token is generated."""
        await self.tokens.put(token)

    async def on_llm_end(self, *args: Any, **kwargs: Any) -> None:
        """Called when LLM generation ends."""
        self.done = True
        await self.tokens.put(None)  # Signal end of stream

    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM encounters an error."""
        self.done = True
        await self.tokens.put(None)

    async def aiter(self) -> AsyncIterator[str]:
        """Async iterator for tokens."""
        while not self.done:
            token = await self.tokens.get()
            if token is None:
                break
            yield token


def create_prompt_template() -> ChatPromptTemplate:
    """Create the prompt template for the RAG chain."""
    template = """あなたは賢い掲示板のアシスタントです。
提供された掲示板の過去ログの文脈を元に、ユーザーの質問に日本語で回答してください。
文脈に答えがない場合は、無理に答えを生成せず「分かりません」と回答してください。

回答する際は、参考にしたレス番号（No.XXX）を明示してください。

【文脈】
{context}

【質問】
{question}

【回答】"""

    return ChatPromptTemplate.from_template(template)


async def extract_citations(context: str, answer: str) -> list[CitationPost]:
    """Extract citation post numbers from the answer using GPT-3.5-turbo.

    Args:
        context: The context containing posts
        answer: The generated answer

    Returns:
        List of cited posts
    """
    llm = ChatOpenAI(
        model=settings.citation_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )

    prompt = ChatPromptTemplate.from_template(
        """以下の回答文から、参照されているレス番号（No.XXX形式）を全て抽出してください。
文脈から該当するレスの情報を取得して、JSON配列で返してください。

【文脈】
{context}

【回答】
{answer}

【出力形式】
[
  {{
    "no": レス番号,
    "name_and_trip": "投稿者名",
    "datetime": "投稿日時",
    "content": "レス内容の最初の100文字"
  }}
]

レス番号が見つからない場合は空の配列[]を返してください。"""
    )

    chain = prompt | llm

    try:
        result = await chain.ainvoke({"context": context, "answer": answer})
        citations_data = json.loads(str(result.content))

        citations = []
        for item in citations_data:
            citation = CitationPost(
                no=item["no"],
                name_and_trip=item["name_and_trip"],
                datetime=item["datetime"],
                content=item["content"],
            )
            citations.append(citation)

        return citations
    except Exception as e:
        print(f"Error extracting citations: {e}")
        return []


class RAGChain:
    """RAG chain with streaming support."""

    def __init__(self) -> None:
        self.retriever = get_retriever()
        self.prompt = create_prompt_template()

    async def astream(
        self, question: str, conversation_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream the answer for a question.

        Args:
            question: The question to answer
            conversation_id: Optional conversation ID

        Yields:
            Tokens of the generated answer
        """
        # Create streaming callback
        stream_handler = StreamingCallbackHandler()

        # Initialize LLM with streaming
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
            streaming=True,
            callbacks=[stream_handler],
        )

        # Create document chain
        document_chain = create_stuff_documents_chain(llm, self.prompt)

        # Create retrieval chain
        retrieval_chain = create_retrieval_chain(self.retriever, document_chain)

        # Run chain asynchronously
        task = asyncio.create_task(retrieval_chain.ainvoke({"input": question}))

        # Stream tokens
        async for token in stream_handler.aiter():
            yield token

        # Wait for completion
        await task

    async def ainvoke(self, question: str, conversation_id: Optional[str] = None) -> dict[str, Any]:
        """Get the complete answer with citations.

        Args:
            question: The question to answer
            conversation_id: Optional conversation ID

        Returns:
            Dictionary with answer and citations
        """
        # Initialize LLM without streaming
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )

        # Create document chain
        document_chain = create_stuff_documents_chain(llm, self.prompt)

        # Create retrieval chain
        retrieval_chain = create_retrieval_chain(self.retriever, document_chain)

        # Get result
        result = await retrieval_chain.ainvoke({"input": question})

        # Extract context and answer
        context = "\n\n".join([doc.page_content for doc in result.get("context", [])])
        answer = result.get("answer", "")

        # Extract citations
        citations = await extract_citations(context, answer)

        return {
            "answer": answer,
            "citations": citations,
        }


# Global chain instance
rag_chain = RAGChain()
