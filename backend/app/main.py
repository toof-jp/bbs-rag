from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import chat
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # スタートアップ時の処理
    print("Starting up BBS RAG API...")
    yield
    # シャットダウン時の処理
    print("Shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ルートエンドポイント
@app.get("/")
def read_root():
    return {"message": "Welcome to BBS RAG API", "docs": "/docs"}


# APIルーターの登録
app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["chat"])
