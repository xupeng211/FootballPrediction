"""数据库赔率模型
Database Odds Models.

定义赔率相关的数据库模型和操作
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from src.database.base import BaseModel


class MarketType(Enum):
    """市场类型枚举."""

    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"
    OVER_2_5 = "over_2_5"
    UNDER_2_5 = "under_2_5"
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"


class BetType(Enum):
    """投注类型枚举."""

    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"
    OVER_2_5 = "over_2_5"
    UNDER_2_5 = "under_2_5"
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"


class Odds(BaseModel):
    """赔率模型."""

    __tablename__ = "odds"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    bookmaker = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=True, index=True)  # 数据源标识

    # 基础赔率字段
    home_win = Column(Numeric(10, 4), nullable=True)
    draw = Column(Numeric(10, 4), nullable=True)
    away_win = Column(Numeric(10, 4), nullable=True)

    # 扩展赔率字段
    over_under = Column(Numeric(10, 4), nullable=True)
    asian_handicap = Column(Numeric(10, 4), nullable=True)

    # 实时性字段
    live_odds = Column(Boolean, default=False)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    confidence_score = Column(Numeric(5, 3), nullable=True)  # 赔率可信度 (0-1)

    # 市场深度
    total_volume = Column(Numeric(15, 2), nullable=True)  # 总交易量
    home_win_volume = Column(Numeric(15, 2), nullable=True)
    draw_volume = Column(Numeric(15, 2), nullable=True)
    away_win_volume = Column(Numeric(15, 2), nullable=True)

    # 价格变动追踪
    price_movement = Column(JSON, nullable=True)  # 价格历史变动
    volatility_index = Column(Numeric(5, 3), nullable=True)  # 波动指数

    # 数据质量指标
    data_quality_score = Column(Numeric(5, 3), nullable=True)
    source_reliability = Column(String(20), nullable=True)

    # 原始字段保留
    bet_type = Column(String(50), nullable=True)
    odds_value = Column(Numeric(10, 4), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # 关系
    odds_history = relationship("OddsHistory", back_populates="odds")

    def __repr__(self):
        """函数文档字符串."""
        # 添加pass语句
        return f"<Odds(match_id={self.match_id}, bookmaker={self.bookmaker}, type={self.bet_type}, odds={self.odds_value})>"

    @property
    def decimal_odds(self) -> Decimal:
        """获取十进制赔率."""
        return Decimal(str(self.odds_value))

    @property
    def implied_probability(self) -> float:
        """获取隐含概率."""
        return float(1 / self.odds_value)


class OddsHistory(BaseModel):
    """赔率历史记录模型."""

    __tablename__ = "odds_history"

    id = Column(Integer, primary_key=True, index=True)
    odds_id = Column(Integer, ForeignKey("odds.id"), nullable=False, index=True)

    # 基础赔率历史
    old_home_win = Column(Numeric(10, 4), nullable=True)
    new_home_win = Column(Numeric(10, 4), nullable=True)
    old_draw = Column(Numeric(10, 4), nullable=True)
    new_draw = Column(Numeric(10, 4), nullable=True)
    old_away_win = Column(Numeric(10, 4), nullable=True)
    new_away_win = Column(Numeric(10, 4), nullable=True)

    # 扩展赔率历史
    old_over_under = Column(Numeric(10, 4), nullable=True)
    new_over_under = Column(Numeric(10, 4), nullable=True)
    old_asian_handicap = Column(Numeric(10, 4), nullable=True)
    new_asian_handicap = Column(Numeric(10, 4), nullable=True)

    # 历史记录字段
    old_total_volume = Column(Numeric(15, 2), nullable=True)
    new_total_volume = Column(Numeric(15, 2), nullable=True)
    old_confidence_score = Column(Numeric(5, 3), nullable=True)
    new_confidence_score = Column(Numeric(5, 3), nullable=True)

    # 变动信息
    change_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    change_reason = Column(Text, nullable=True)
    price_impact = Column(String(50), nullable=True)  # "minor", "moderate", "major"

    # 关系
    odds = relationship("Odds", back_populates="odds_history")

    def __repr__(self):
        """函数文档字符串."""
        # 添加pass语句
        return f"<OddsHistory(odds_id={self.odds_id}, change={self.old_odds_value}->{self.new_odds_value})>"


class MarketAnalysis(BaseModel):
    """市场分析模型."""

    __tablename__ = "market_analysis"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    bet_type = Column(String(50), nullable=False)
    average_odds = Column(Numeric(10, 4), nullable=False)
    min_odds = Column(Numeric(10, 4), nullable=False)
    max_odds = Column(Numeric(10, 4), nullable=False)
    bookmaker_count = Column(Integer, default=0)
    analysis_time = Column(DateTime, default=datetime.utcnow)
    market_confidence = Column(Numeric(3, 2), default=0.5)  # 0-1之间的市场信心度

    # 新增市场分析字段
    market_efficiency = Column(Numeric(5, 3), nullable=True)  # 市场效率 (0-1)
    implied_probabilities = Column(JSON, nullable=True)  # 各结果隐含概率
    market_bias = Column(String(20), nullable=True)  # 市场偏差
    arbitrage_opportunity = Column(Boolean, default=False)  # 套利机会
    total_volume_analyzed = Column(Numeric(15, 2), nullable=True)  # 分析的总交易量
    volatility_analysis = Column(JSON, nullable=True)  # 波动性分析数据

    # MarketAnalysis模型不直接引用Match，避免关系冲突

    def __repr__(self):
        """函数文档字符串."""
        # 添加pass语句
        return f"<MarketAnalysis(match_id={self.match_id}, type={self.bet_type}, avg_odds={self.average_odds})>"

    @property
    def odds_range(self) -> Decimal:
        """获取赔率范围."""
        return self.max_odds - self.min_odds

    @property
    def market_volatility(self) -> float:
        """获取市场波动性."""
        if self.average_odds == 0:
            return 0.0
        return float((self.max_odds - self.min_odds) / self.average_odds)


# 导出的类列表
__all__ = [
    "MarketType",
    "BetType",
    "Odds",
    "OddsHistory",
    "MarketAnalysis"
]
