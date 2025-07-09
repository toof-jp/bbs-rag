"""Test API endpoints."""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ["OPENAI_API_KEY"] = "sk-test"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_bbs2"
os.environ["COLLECTION_NAME"] = "test_collection"


def test_root() -> None:
    """Test root endpoint."""
    # Mock the retriever initialization
    with patch("app.rag.retriever.create_retriever"):
        from app.main import app

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {
            "message": "BBS RAG API",
            "version": "0.1.0",
            "docs": "/docs",
        }


def test_health_check() -> None:
    """Test health check endpoint."""
    # Mock the retriever initialization
    with patch("app.rag.retriever.create_retriever"):
        from app.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
