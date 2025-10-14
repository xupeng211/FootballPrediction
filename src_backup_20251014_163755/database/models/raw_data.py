from typing import Dict, Optional
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.exc import SQLAlchemyError, DatabaseError
from sqlalchemy.orm import validates
from ..base import BaseModel
from ..types import JsonbType


"""
Bronze层原始数据模型

用于存储从外部API采集的原始JSON数据。
包含比赛数据、赔率数据、比分数据等的原始存储表。

基于 DATA_DESIGN.md 第2.1节Bronze层设计。
"""


class RawMatchData(BaseModel):
    """
    Bronze层原始比赛数据模型

    存储从外部API采集的原始比赛数据（JSONB/JSON格式），
    作为数据处理管道的输入源。
    """

    __tablename__ = "raw_match_data"

    # 基础字段
    id = Column(Integer, primary_key=True, comment="主键ID")
    data_source = Column(String(100), nullable=False, comment="数据源标识")
    raw_data: Any = Column(JsonbType, nullable=False, comment="原始JSON/JSONB数据")

    # 时间字段
    collected_at = Column(DateTime, nullable=False, comment="采集时间")
    processed = Column(Boolean, nullable=False, default=False, comment="是否已处理")

    # 快速检索字段（从JSON/JSONB中提取）
    external_match_id = Column(String(100), nullable=True, comment="外部比赛ID")
    external_league_id = Column(String(100), nullable=True, comment="外部联赛ID")
    match_time = Column(DateTime, nullable=True, comment="比赛时间")

    # 元数据字段
    created_at = Column(
        DateTime, nullable=False, default=func.now(), comment="创建时间"
    )

    @validates("data_source")
    def validate_data_source(self, key: str, data_source: str) -> str:
        """验证数据源"""
        if not data_source or len(data_source.strip()) == 0:
            raise ValueError("Data source cannot be empty")
        return data_source.strip()

    @property
    def is_processed(self) -> bool:
        """是否已处理"""
        return bool(self.processed)

    def mark_processed(self) -> None:
        """标记为已处理"""
        # 直接赋值布尔值，由SQLAlchemy处理类型转换
        object.__setattr__(self, "processed", True)

    def get_raw_data_field(self, field_path: str) -> Any:
        """
        从原始数据中获取指定字段

        Args:
            field_path: 字段路径，如 "homeTeam.name"

        Returns:
            字段值，不存在时返回None
        """
        if not self.raw_data:
            return None

        try:
            value = self.raw_data
            for field in field_path.split("."):
                if isinstance(value, Dict[str, Any]) and field in value:
                    value = value[field]
                else:
                    return None
            return value
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError):
            return None

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<RawMatchData("
            f"id={self.id}, "
            f"source={self.data_source}, "
            f"external_id={self.external_match_id}, "
            f"processed={self.processed}"
            f")>"
        )


class RawOddsData(BaseModel):
    """
    Bronze层原始赔率数据模型

    存储从博彩公司API采集的原始赔率数据，
    支持高频更新和历史变化追踪。
    """

    __tablename__ = "raw_odds_data"

    # 基础字段
    id = Column(Integer, primary_key=True, comment="主键ID")
    data_source = Column(String(100), nullable=False, comment="数据源标识")
    raw_data: Any = Column(JsonbType, nullable=False, comment="原始JSON/JSONB数据")

    # 时间字段
    collected_at = Column(DateTime, nullable=False, comment="采集时间")
    processed = Column(Boolean, nullable=False, default=False, comment="是否已处理")

    # 快速检索字段（从JSON/JSONB中提取）
    external_match_id = Column(String(100), nullable=True, comment="外部比赛ID")
    bookmaker = Column(String(100), nullable=True, comment="博彩公司")
    market_type = Column(String(50), nullable=True, comment="市场类型")

    # 元数据字段
    created_at = Column(
        DateTime, nullable=False, default=func.now(), comment="创建时间"
    )

    @validates("data_source")
    def validate_data_source(self, key: str, data_source: str) -> str:
        """验证数据源"""
        if not data_source or len(data_source.strip()) == 0:
            raise ValueError("Data source cannot be empty")
        return data_source.strip()

    @property
    def is_processed(self) -> bool:
        """是否已处理"""
        return self.processed  # type: ignore

    def mark_processed(self) -> None:
        """标记为已处理"""
        self.processed = True  # type: ignore

    def get_odds_values(self) -> Optional[Dict[str, float]:
        """
        提取赔率值

        Returns:
            赔率字典，格式如 {"home": 1.85, "draw": 3.2, "away": 4.5}
        """
        if not self.raw_data:
            return None

        try:
            outcomes = self.raw_data.get(str("outcomes"), [])
            odds_dict = {}

            for outcome in outcomes:
                name = outcome.get(str("name"), "").lower()
                price = outcome.get("price")
                if name and price:
                    odds_dict[name] = float(price)

            return odds_dict if odds_dict else None
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError):
            return None

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<RawOddsData("
            f"id={self.id}, "
            f"source={self.data_source}, "
            f"match_id={self.external_match_id}, "
            f"bookmaker={self.bookmaker}, "
            f"processed={self.processed}"
            f")>"
        )


class RawScoresData(BaseModel):
    """
    Bronze层原始比分数据模型

    存储从体育API采集的实时比分数据，
    包括比赛进程、半场比分、最终比分等信息。
    """

    __tablename__ = "raw_scores_data"

    # 基础字段
    id = Column(Integer, primary_key=True, comment="主键ID")
    data_source = Column(String(100), nullable=False, comment="数据源标识")
    raw_data: Any = Column(JsonbType, nullable=False, comment="原始JSON/JSONB数据")

    # 时间字段
    collected_at = Column(DateTime, nullable=False, comment="采集时间")
    processed = Column(Boolean, nullable=False, default=False, comment="是否已处理")

    # 快速检索字段（从JSON/JSONB中提取）
    external_match_id = Column(String(100), nullable=True, comment="外部比赛ID")
    match_status = Column(String(50), nullable=True, comment="比赛状态")
    home_score = Column(Integer, nullable=True, comment="主队比分")
    away_score = Column(Integer, nullable=True, comment="客队比分")
    match_minute = Column(Integer, nullable=True, comment="比赛分钟")

    # 元数据字段
    created_at = Column(
        DateTime, nullable=False, default=func.now(), comment="创建时间"
    )

    @validates("data_source")
    def validate_data_source(self, key: str, data_source: str) -> str:
        """验证数据源"""
        if not data_source or len(data_source.strip()) == 0:
            raise ValueError("Data source cannot be empty")
        return data_source.strip()

    @validates("home_score", "away_score")
    def validate_score(self, key: str, score: Optional[int]) -> Optional[int]:
        """验证比分数据"""
        if score is not None and (score < 0 or score > 99):
            raise ValueError(f"Score must be between 0 and 99, got {score}")
        return score

    @property
    def is_processed(self) -> bool:
        """是否已处理"""
        return self.processed  # type: ignore

    def mark_processed(self) -> None:
        """标记为已处理"""
        self.processed = True  # type: ignore

    @property
    def is_live(self) -> bool:
        """是否为进行中的比赛"""
        return self.match_status in ["live", "in_progress", "1H", "2H"]

    @property
    def is_finished(self) -> bool:
        """是否为已结束的比赛"""
        return self.match_status in ["finished", "full_time", "ft"]

    def get_score_info(self) -> Optional[Dict[str, Any]:
        """
        提取比分信息

        Returns:
            比分信息字典，包含主客队比分、状态等
        """
        if not self.raw_data:
            return None

        try:
            return {
                "home_score": self.home_score
                or self.raw_data.get(str("home_score"), 0),
                "away_score": self.away_score
                or self.raw_data.get(str("away_score"), 0),
                "status": self.match_status
                or self.raw_data.get(str("status"), "unknown"),
                "minute": self.match_minute or self.raw_data.get("minute"),
                "half_time_home": self.raw_data.get("half_time_home"),
                "half_time_away": self.raw_data.get("half_time_away"),
                "events": self.raw_data.get(str("events"), []),  # 进球、黄牌等事件
            }
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError):
            return None

    def get_latest_events(self, event_type: Optional[str] = None) -> list:
        """
        获取最新比赛事件

        Args:
            event_type: 事件类型过滤 (goal, card, substitution等)

        Returns:
            事件列表
        """
        if not self.raw_data or "events" not in self.raw_data:
            return []

        events = self.raw_data.get(str("events"), [])
        if event_type:
            events = [e for e in events if e.get("type") == event_type]

        # 按时间排序，最新的在前
        return sorted(events, key=lambda x: x.get(str("minute"), 0), reverse=True)

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<RawScoresData("
            f"id={self.id}, "
            f"source={self.data_source}, "
            f"match_id={self.external_match_id}, "
            f"score={self.home_score}-{self.away_score}, "
            f"status={self.match_status}, "
            f"processed={self.processed}"
            f")>"
        )
