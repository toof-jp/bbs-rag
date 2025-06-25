from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ResDocument(BaseModel):
    """掲示板のレスを表すデータモデル"""
    no: int
    name_and_trip: str
    datetime: datetime
    datetime_text: str
    id: str
    main_text: str
    main_text_html: str
    oekaki_id: Optional[int] = None


class AskRequest(BaseModel):
    """質問リクエストのスキーマ"""
    question: str
    conversation_id: Optional[str] = None


class StreamToken(BaseModel):
    """ストリーミング応答の単一トークン"""
    token: str
    
    
class RetrievedContext(BaseModel):
    """検索で取得したコンテキスト情報"""
    content: str
    metadata: dict
    score: Optional[float] = None