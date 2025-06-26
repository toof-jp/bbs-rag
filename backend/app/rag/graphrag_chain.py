"""GraphRAG chain implementation using LangGraph."""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional, TypedDict
from uuid import UUID

from langchain.callbacks.base import AsyncCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, StateGraph
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_rag_db
from app.models.graph import Post
from app.rag.graph_traversal import GraphTraverser

logger = logging.getLogger(__name__)


class GraphRAGState(TypedDict):
    """State for GraphRAG workflow."""
    question: str
    vector_results: list[UUID]
    graph_context: dict[str, Any]
    formatted_context: str
    answer: str
    streaming_handler: Optional[AsyncCallbackHandler]


class GraphRAGChain:
    """GraphRAG chain using LangGraph."""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )
        self.graph_traverser = GraphTraverser(max_depth=3, max_nodes=50)
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(GraphRAGState)

        # Add nodes
        workflow.add_node("vector_retriever", self._vector_retriever)
        workflow.add_node("graph_traverser", self._graph_traverser)
        workflow.add_node("context_synthesizer", self._context_synthesizer)
        workflow.add_node("response_generator", self._response_generator)

        # Add edges
        workflow.set_entry_point("vector_retriever")
        workflow.add_edge("vector_retriever", "graph_traverser")
        workflow.add_edge("graph_traverser", "context_synthesizer")
        workflow.add_edge("context_synthesizer", "response_generator")
        workflow.add_edge("response_generator", END)

        return workflow.compile()

    async def _vector_retriever(self, state: GraphRAGState) -> GraphRAGState:
        """Retrieve relevant posts using vector similarity."""
        logger.info(f"Vector retrieval for question: {state['question']}")
        
        # Import Chroma here to avoid circular imports
        from langchain_community.vectorstores import Chroma
        
        # Initialize Chroma vector store
        vectorstore = Chroma(
            collection_name=settings.collection_name,
            embedding_function=self.embeddings,
            persist_directory=settings.chroma_persist_directory,
        )
        
        # Search for similar documents
        docs = await asyncio.to_thread(
            vectorstore.similarity_search,
            state["question"],
            k=5
        )
        
        # Extract post IDs from metadata
        post_ids = []
        with get_rag_db() as session:
            for doc in docs:
                if "source_post_no" in doc.metadata:
                    # Find post by source_post_no
                    post = session.execute(
                        select(Post).where(Post.source_post_no == int(doc.metadata["source_post_no"]))
                    ).scalar_one_or_none()
                    if post:
                        post_ids.append(post.post_id)
        
        state["vector_results"] = post_ids
        logger.info(f"Found {len(post_ids)} relevant posts")
        return state

    async def _graph_traverser(self, state: GraphRAGState) -> GraphRAGState:
        """Traverse the graph to collect context."""
        logger.info("Starting graph traversal")
        
        with get_rag_db() as session:
            context = self.graph_traverser.get_conversation_context(
                session, state["vector_results"]
            )
        
        state["graph_context"] = context
        logger.info(f"Collected {context['stats']['total_posts']} posts from graph")
        return state

    async def _context_synthesizer(self, state: GraphRAGState) -> GraphRAGState:
        """Synthesize context for LLM."""
        logger.info("Synthesizing context")
        
        formatted_context = self.graph_traverser.format_context_for_llm(
            state["graph_context"]
        )
        
        state["formatted_context"] = formatted_context
        return state

    async def _response_generator(self, state: GraphRAGState) -> GraphRAGState:
        """Generate response using LLM."""
        logger.info("Generating response")
        
        # Build prompt
        system_prompt = """あなたは賢い掲示板のアシスタントです。
提供された掲示板の会話コンテキストとグラフ関係性を元に、ユーザーの質問に日本語で回答してください。
文脈に答えがない場合は、無理に答えを生成せず「分かりません」と回答してください。

回答する際は、参考にしたレス番号（No.XXX）を明示してください。
グラフの関係性（返信関係など）も考慮して、会話の流れを理解した上で回答してください。"""

        user_prompt = f"""【コンテキスト】
{state['formatted_context']}

【質問】
{state['question']}

【回答】"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Use streaming handler if provided
        if state.get("streaming_handler"):
            response = await self.llm.ainvoke(
                messages,
                config={"callbacks": [state["streaming_handler"]]}
            )
        else:
            response = await self.llm.ainvoke(messages)

        state["answer"] = response.content
        return state

    async def ainvoke(self, question: str, streaming_handler: Optional[AsyncCallbackHandler] = None) -> dict[str, Any]:
        """Invoke the GraphRAG chain.
        
        Args:
            question: User's question
            streaming_handler: Optional callback handler for streaming
            
        Returns:
            Dictionary with answer and context
        """
        initial_state = GraphRAGState(
            question=question,
            vector_results=[],
            graph_context={},
            formatted_context="",
            answer="",
            streaming_handler=streaming_handler
        )
        
        result = await self.workflow.ainvoke(initial_state)
        
        return {
            "answer": result["answer"],
            "context": result["graph_context"],
            "stats": result["graph_context"].get("stats", {})
        }

    async def astream(self, question: str) -> AsyncIterator[str]:
        """Stream the answer for a question.
        
        Args:
            question: User's question
            
        Yields:
            Tokens of the generated answer
        """
        # Import here to avoid circular imports
        from app.rag.chain import StreamingCallbackHandler
        
        stream_handler = StreamingCallbackHandler()
        
        # Run the chain asynchronously
        task = asyncio.create_task(self.ainvoke(question, stream_handler))
        
        # Stream tokens
        async for token in stream_handler.aiter():
            yield token
        
        # Wait for completion
        await task


# Global GraphRAG chain instance
graphrag_chain = GraphRAGChain()