"""Retriever implementation with sliding window strategy."""

import os
from typing import Optional

from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import LocalFileStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


class SlidingWindowChunker:
    """Create sliding window chunks from documents."""

    def __init__(self, window_size: int = 50, overlap: int = 20):
        """Initialize the chunker.

        Args:
            window_size: Number of posts per window
            overlap: Number of overlapping posts between windows
        """
        self.window_size = window_size
        self.overlap = overlap

    def create_windows(self, documents: list[Document]) -> list[Document]:
        """Create sliding window documents from individual post documents.

        Args:
            documents: List of individual post documents

        Returns:
            List of window documents
        """
        if not documents:
            return []

        windows = []
        step = self.window_size - self.overlap

        for i in range(0, len(documents), step):
            # Get posts for this window
            window_docs = documents[i : i + self.window_size]

            if not window_docs:
                break

            # Combine posts into a single window document
            combined_content = "\n\n---\n\n".join(
                [
                    f"No.{doc.metadata['no']} 名前：{doc.metadata['name_and_trip']} "
                    f"投稿日：{doc.metadata['datetime']}\n{doc.page_content}"
                    for doc in window_docs
                ]
            )

            # Create metadata for the window
            start_no = window_docs[0].metadata["no"]
            end_no = window_docs[-1].metadata["no"]

            window_metadata = {
                "start_no": start_no,
                "end_no": end_no,
                "post_count": len(window_docs),
                "source": f"window_{start_no}_{end_no}",
            }

            window_doc = Document(
                page_content=combined_content,
                metadata=window_metadata,
            )

            windows.append(window_doc)

        return windows


def create_retriever(
    persist_directory: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> ParentDocumentRetriever:
    """Create a ParentDocumentRetriever with sliding window strategy.

    Args:
        persist_directory: Directory to persist vector store
        collection_name: Name of the collection in vector store

    Returns:
        Configured ParentDocumentRetriever
    """
    persist_dir = persist_directory or settings.chroma_persist_directory
    collection = collection_name or settings.collection_name

    # Initialize embeddings
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )

    # Initialize vector store
    vectorstore = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )

    # Initialize docstore for parent documents
    docstore_path = os.path.join(os.path.dirname(persist_dir), "docstore")
    os.makedirs(docstore_path, exist_ok=True)
    docstore = LocalFileStore(docstore_path)

    # Create child text splitter (for splitting parent documents)
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.child_chunk_size,
        chunk_overlap=50,
        separators=["\n\n---\n\n", "\n\n", "\n", " ", ""],
    )

    # Create retriever
    retriever = ParentDocumentRetriever(
        vectorstore=vectorstore,
        docstore=docstore,  # type: ignore[arg-type]
        child_splitter=child_splitter,
        search_kwargs={"k": settings.search_k},
    )

    return retriever


def get_retriever() -> ParentDocumentRetriever:
    """Get the default retriever instance."""
    return create_retriever()
