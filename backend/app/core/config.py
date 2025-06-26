"""Configuration settings for the BBS RAG application."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file="../.env",  # Read from project root
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env
    )

    # Database connections
    database_url: str = "postgresql://user:password@localhost:5432/bbs2"  # Source DB (read-only)
    rag_database_url: str = "postgresql://user:password@localhost:5432/bbs_rag"  # RAG DB

    # OpenAI
    openai_api_key: SecretStr = SecretStr("")

    # Vector Store
    collection_name: str = "bbs_rag_collection"
    chroma_persist_directory: str = "chroma_db"

    # API Settings
    api_v1_str: str = "/api/v1"
    project_name: str = "BBS RAG API"
    project_version: str = "0.1.0"

    # CORS
    backend_cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]

    # Backend server settings
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Model settings
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.7
    max_tokens: int = 2000

    # RAG settings
    window_size: int = 50
    window_overlap: int = 20
    child_chunk_size: int = 400
    search_k: int = 5

    # Citation extraction model
    citation_model: str = "gpt-3.5-turbo"


settings = Settings()
