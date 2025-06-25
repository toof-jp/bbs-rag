from datetime import datetime

from pydantic import BaseModel


class ResDocument(BaseModel):
    """掲示板のレスを表すデータモデル"""

    no: int
    name_and_trip: str
    datetime: datetime
    datetime_text: str
    id: str
    main_text: str
    main_text_html: str
    oekaki_id: int | None = None


class AskRequest(BaseModel):
    """質問リクエストのスキーマ"""

    question: str
    conversation_id: str | None = None


class StreamToken(BaseModel):
    """ストリーミング応答の単一トークン"""

    token: str


class RetrievedContext(BaseModel):
    """検索で取得したコンテキスト情報"""

    content: str
    metadata: dict
    score: float | None = None
