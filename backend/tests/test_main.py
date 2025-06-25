"""Basic tests for the FastAPI application."""
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to BBS RAG API", "docs": "/docs"}


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "chat"}