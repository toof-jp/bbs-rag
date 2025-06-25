from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    COLLECTION_NAME: str = "bbs_rag_collection"

    # OpenAI Model設定
    OPENAI_MODEL: str = "gpt-4o-mini"  # デフォルトはコスト効率の良いモデル
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # API設定
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BBS RAG API"

    # CORS設定
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
