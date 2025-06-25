from sqlalchemy import Column, DateTime, Integer, Text

from app.core.database import Base


class Res(Base):
    """掲示板のレステーブルのSQLAlchemyモデル"""

    __tablename__ = "res"
    __table_args__ = {"schema": "public"}

    no = Column(Integer, primary_key=True, index=True)
    name_and_trip = Column(Text, nullable=False)
    datetime = Column(DateTime, nullable=False)
    datetime_text = Column(Text, nullable=False)
    id = Column(Text, nullable=False)
    main_text = Column(Text, nullable=False)
    main_text_html = Column(Text, nullable=False)
    oekaki_id = Column(Integer, nullable=True)
