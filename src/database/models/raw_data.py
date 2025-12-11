from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from src.database.base import BaseModel
from src.database.types import JsonbType


class RawData(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "raw_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False)
    data_type = Column(String(50), nullable=False)
    external_id = Column(String(100), nullable=True)
    raw_content = Column(JsonbType, nullable=True)
    raw_data = Column(JsonbType, nullable=True)  # 保留原有字段
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    def __repr__(self) -> str:
        """安全的__repr__方法，只访问自己的列字段."""
        processed_val = self.processed if self.processed is not None else False
        return (
            f"RawData(id={self.id}, "
            f"source={self.source!r}, "
            f"data_type={self.data_type!r}, "
            f"processed={processed_val})"
        )


class RawMatchData(BaseModel):
    """原始比赛数据模型."""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "raw_match_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), nullable=False, unique=True)
    source = Column(String(100), nullable=False)
    match_data = Column(JsonbType, nullable=False)
    collected_at = Column(DateTime, nullable=False, default=func.now())
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now())

    def __repr__(self) -> str:
        """安全的__repr__方法，只访问自己的列字段."""
        return (
            f"RawMatchData(id={self.id}, "
            f"external_id={self.external_id!r}, "
            f"source={self.source!r}, "
            f"processed={self.processed})"
        )


class RawOddsData(BaseModel):
    """原始赔率数据模型."""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "raw_odds_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_match_id = Column(String(100), nullable=False)
    bookmaker = Column(String(100), nullable=False)
    odds_data = Column(JsonbType, nullable=False)
    collected_at = Column(DateTime, nullable=False, default=func.now())
    processed = Column(Boolean, default=False)

    def __repr__(self) -> str:
        """安全的__repr__方法，只访问自己的列字段."""
        return (
            f"RawOddsData(id={self.id}, "
            f"bookmaker={self.bookmaker!r}, "
            f"external_match_id={self.external_match_id!r}, "
            f"processed={self.processed})"
        )


class RawScoresData(BaseModel):
    """原始比分数据模型."""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "raw_scores_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_match_id = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False)
    scores_data = Column(JsonbType, nullable=False)
    collected_at = Column(DateTime, nullable=False, default=func.now())
    processed = Column(Boolean, default=False)

    def __repr__(self) -> str:
        """安全的__repr__方法，只访问自己的列字段."""
        return (
            f"RawScoresData(id={self.id}, "
            f"source={self.source!r}, "
            f"external_match_id={self.external_match_id!r}, "
            f"processed={self.processed})"
        )
