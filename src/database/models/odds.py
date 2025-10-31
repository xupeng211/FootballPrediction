"""
数据库赔率模型
Database Odds Models

定义赔率相关的数据库模型和操作
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class MarketType(Enum):
    """市场类型枚举"""

    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"
    OVER_2_5 = "over_2_5"
    UNDER_2_5 = "under_2_5"
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"


class BetType(Enum):
    """投注类型枚举"""

    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"
    OVER_2_5 = "over_2_5"
    UNDER_2_5 = "under_2_5"
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"


class Odds(Base):
    """赔率模型"""

    __tablename__ = "odds"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, nullable=False, index=True)
    bookmaker = Column(String(100), nullable=False, index=True)
    bet_type = Column(String(50), nullable=False)
    odds_value = Column(Numeric(10, 4), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        return f"<Odds(match_id={self.match_id}, bookmaker={self.bookmaker}, type={self.bet_type}, odds={self.odds_value})>"

    @property
    def decimal_odds(self) -> Decimal:
        """获取十进制赔率"""
        return Decimal(str(self.odds_value))

    @property
    def implied_probability(self) -> float:
        """获取隐含概率"""
        return float(1 / self.odds_value)


class OddsHistory(Base):
    """赔率历史记录模型"""

    __tablename__ = "odds_history"

    id = Column(Integer, primary_key=True, index=True)
    odds_id = Column(Integer, nullable=False, index=True)
    old_odds_value = Column(Numeric(10, 4), nullable=False)
    new_odds_value = Column(Numeric(10, 4), nullable=False)
    change_time = Column(DateTime, default=datetime.utcnow)
    change_reason = Column(Text, nullable=True)

    def __repr__(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        return f"<OddsHistory(odds_id={self.odds_id}, change={self.old_odds_value}->{self.new_odds_value})>"


class MarketAnalysis(Base):
    """市场分析模型"""

    __tablename__ = "market_analysis"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, nullable=False, index=True)
    bet_type = Column(String(50), nullable=False)
    average_odds = Column(Numeric(10, 4), nullable=False)
    min_odds = Column(Numeric(10, 4), nullable=False)
    max_odds = Column(Numeric(10, 4), nullable=False)
    bookmaker_count = Column(Integer, default=0)
    analysis_time = Column(DateTime, default=datetime.utcnow)
    market_confidence = Column(Numeric(3, 2), default=0.5)  # 0-1之间的市场信心度

    def __repr__(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        return f"<MarketAnalysis(match_id={self.match_id}, type={self.bet_type}, avg_odds={self.average_odds})>"

    @property
    def odds_range(self) -> Decimal:
        """获取赔率范围"""
        return self.max_odds - self.min_odds

    @property
    def market_volatility(self) -> float:
        """获取市场波动性"""
        if self.average_odds == 0:
            return 0.0
        return float((self.max_odds - self.min_odds) / self.average_odds)


# 导出的类列表
__all__ = ["BetType", "Odds", "OddsHistory", "MarketAnalysis"]
