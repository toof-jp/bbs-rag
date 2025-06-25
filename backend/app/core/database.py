import asyncpg
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# postgres:// を postgresql:// に変換（SQLAlchemy 1.4+ 対応）
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# 同期用エンジン（インデックス作成など）
engine = create_engine(database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# 非同期データベース接続
async def get_async_db_connection():
    """非同期でデータベース接続を取得"""
    conn = await asyncpg.connect(database_url)
    try:
        yield conn
    finally:
        await conn.close()


def get_db():
    """同期的なデータベースセッションを取得"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
