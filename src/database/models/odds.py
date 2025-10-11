"""
Odds - 数据库模块

提供 odds 相关的数据库功能。

主要功能：
- [待补充 - Odds的主要功能]

使用示例：
    from database.models import Odds
    # 使用示例代码

注意事项：
- [待补充 - 使用注意事项]
"""

from ..base import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    CheckConstraint,
    DECIMAL,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

"""
足球比赛赔率数据模型

存储不同博彩公司的赔率信息，包括胜平负、大小球、让球等市场。
"""

from typing import Any, Dict, Optional
from sqlalchemy import DECIMAL, CheckConstraint, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, String, func
from src.database.base import BaseModel
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class MarketType(Enum):
    """赔率市场类型"""

    ONE_X_TWO = "1x2"  # 胜平负
    OVER_UNDER = "over_under"  # 大小球
    ASIAN_HANDICAP = "asian_handicap"  # 亚洲让球
    BOTH_TEAMS_SCORE = "both_teams_score"  # 双方进球


class Odds(BaseModel):
    """
    赔率表模型

    对应 architecture.md 中的 odds 表设计
    """

    __tablename__ = "odds"

    # 主键和外键
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, comment="比赛ID"
    )

    bookmaker: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="博彩公司名称"
    )

    # 市场类型
    market_type: Mapped[MarketType] = mapped_column(
        SQLEnum(MarketType), nullable=False, comment="市场类型"
    )

    # 1x2市场赔率
    home_odds: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 3), nullable=True, comment="主队胜赔率"
    )

    draw_odds: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 3), nullable=True, comment="平局赔率"
    )

    away_odds: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 3), nullable=True, comment="客队胜赔率"
    )

    # 大小球市场赔率
    over_odds: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 3), nullable=True, comment="大球赔率"
    )

    under_odds: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 3), nullable=True, comment="小球赔率"
    )

    line_value: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="盘口数值"
    )

    # 收集时间
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="赔率收集时间"
    )

    # 关系定义
    match = relationship("Match", back_populates="odds")

    # 索引和约束定义
    __table_args__ = (
        # 索引定义
        Index("idx_odds_match_bookmaker", "match_id", "bookmaker"),
        Index("idx_odds_collected_at", "collected_at"),
        Index("idx_odds_market_type", "market_type"),
        Index("idx_odds_match_market", "match_id", "market_type"),
        # CHECK约束定义 - 确保赔率数据的合理性
        CheckConstraint(
            "home_odds IS NULL OR home_odds > 1.01", name="ck_odds_home_odds_range"
        ),
        CheckConstraint(
            "draw_odds IS NULL OR draw_odds > 1.01", name="ck_odds_draw_odds_range"
        ),
        CheckConstraint(
            "away_odds IS NULL OR away_odds > 1.01", name="ck_odds_away_odds_range"
        ),
        CheckConstraint(
            "over_odds IS NULL OR over_odds > 1.01", name="ck_odds_over_odds_range"
        ),
        CheckConstraint(
            "under_odds IS NULL OR under_odds > 1.01", name="ck_odds_under_odds_range"
        ),
        CheckConstraint(
            "line_value IS NULL OR (line_value >= 0 AND line_value <= 10)",
            name="ck_odds_line_value_range",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Odds(id={self.id}, match_id={self.match_id}, "
            f"bookmaker='{self.bookmaker}', market='{self.market_type.value}')>"
        )

    @property
    def is_1x2_market(self) -> bool:
        """检查是否为胜平负市场"""
        return self.market_type == MarketType.ONE_X_TWO

    @property
    def is_over_under_market(self) -> bool:
        """检查是否为大小球市场"""
        return self.market_type == MarketType.OVER_UNDER

    @property
    def is_asian_handicap_market(self) -> bool:
        """检查是否为亚洲让球市场"""
        return self.market_type == MarketType.ASIAN_HANDICAP

    def get_implied_probabilities(self) -> Optional[Dict[str, float]]:
        """
        计算隐含概率

        Returns:
            Optional[Dict[str, float]]: 各结果的隐含概率
        """
        if self.is_1x2_market and all([self.home_odds, self.draw_odds, self.away_odds]):
            # 安全的类型转换，这里我们已经检查了all()，所以值不为None
            home_prob = 1.0 / float(self.home_odds)  # type: ignore
            draw_prob = 1.0 / float(self.draw_odds)  # type: ignore
            away_prob = 1.0 / float(self.away_odds)  # type: ignore

            # 标准化概率（去除博彩公司的利润边际）
            total_prob = home_prob + draw_prob + away_prob

            return {
                "home_win": home_prob / total_prob,
                "draw": draw_prob / total_prob,
                "away_win": away_prob / total_prob,
                "bookmaker_margin": (total_prob - 1.0) / total_prob,
            }

        elif self.is_over_under_market and all([self.over_odds, self.under_odds]):
            # 安全的类型转换，这里我们已经检查了all()，所以值不为None
            over_prob = 1.0 / float(self.over_odds)  # type: ignore
            under_prob = 1.0 / float(self.under_odds)  # type: ignore
            total_prob = over_prob + under_prob

            return {
                "over": over_prob / total_prob,
                "under": under_prob / total_prob,
                "bookmaker_margin": (total_prob - 1.0) / total_prob,
            }

        return None

    def get_best_value_bet(self) -> Optional[Dict[str, Any]]:
        """
        获取最佳价值投注建议

        Returns:
            Optional[Dict[str, Any]]: 包含投注建议的字典
        """
        probabilities = self.get_implied_probabilities()
        if not probabilities:
            return None

        if self.is_1x2_market:
            outcomes = ["home_win", "draw", "away_win"]
            odds_values = [self.home_odds, self.draw_odds, self.away_odds]

            best_value = 0.0
            best_outcome = None
            best_odds = None

            for outcome, odds in zip(outcomes, odds_values):
                if outcome in probabilities and odds:
                    # 计算期望价值 (Expected Value)
                    implied_prob = probabilities[outcome]
                    expected_value = (float(odds) * implied_prob) - 1.0

                    if expected_value > best_value:
                        best_value = expected_value
                        best_outcome = outcome
                        best_odds = float(odds)

            if best_outcome and best_value > 0:
                return {
                    "outcome": best_outcome,
                    "odds": best_odds,
                    "expected_value": best_value,
                    "implied_probability": probabilities[best_outcome],
                    "recommendation": "BET" if best_value > 0.05 else "CONSIDER",
                }

        return None

    def _calculate_percentage_change(
        self, current: Decimal, previous: Decimal
    ) -> float:
        """计算百分比变化"""
        if not current or not previous:
            return 0.0
        return abs(float(current) - float(previous)) / float(previous)

    def _check_1x2_movement(self, previous_odds: "Odds", threshold: float) -> bool:
        """检查1X2市场赔率变化"""
        current_odds = [self.home_odds, self.draw_odds, self.away_odds]
        prev_odds = [
            previous_odds.home_odds,
            previous_odds.draw_odds,
            previous_odds.away_odds,
        ]

        for curr, prev in zip(current_odds, prev_odds):
            if curr and prev:
                # 确保传递Decimal类型而不是Column对象
                change_pct = self._calculate_percentage_change(
                    Decimal(str(curr)), Decimal(str(prev))
                )
                if change_pct > threshold:
                    return True
        return False

    def _check_over_under_movement(
        self, previous_odds: "Odds", threshold: float
    ) -> bool:
        """检查大小球市场赔率变化"""
        if self.over_odds and previous_odds.over_odds:
            over_change = self._calculate_percentage_change(
                Decimal(str(self.over_odds)), Decimal(str(previous_odds.over_odds))
            )
            if over_change > threshold:
                return True

        if self.under_odds and previous_odds.under_odds:
            under_change = self._calculate_percentage_change(
                Decimal(str(self.under_odds)), Decimal(str(previous_odds.under_odds))
            )
            if under_change > threshold:
                return True

        return False

    def is_odds_movement_significant(
        self, previous_odds: "Odds", threshold: float = 0.1
    ) -> bool:
        """
        检查赔率变化是否显著

        Args:
            previous_odds: 之前的赔率数据
            threshold: 显著变化的阈值

        Returns:
            bool: 赔率变化是否显著
        """
        if not previous_odds or self.market_type != previous_odds.market_type:
            return False

        if self.is_1x2_market:
            return self._check_1x2_movement(previous_odds, threshold)
        elif self.is_over_under_market:
            return self._check_over_under_movement(previous_odds, threshold)

        return False

    @classmethod
    def get_latest_odds(cls, session, match_id: int, bookmaker: Optional[str] = None):
        """获取比赛最新赔率"""
        query = session.query(cls).filter(cls.match_id == match_id)
        if bookmaker:
            query = query.filter(cls.bookmaker == bookmaker)
        return query.order_by(cls.updated_at.desc()).all()

    @classmethod
    def get_odds_history(cls, session, match_id: int, market_type: MarketType):
        """获取特定比赛和市场的赔率历史"""
        return (
            session.query(cls)
            .filter(cls.match_id == match_id, cls.market_type == market_type)
            .order_by(cls.collected_at.asc())
            .all()
        )

    @classmethod
    def get_bookmaker_odds(cls, session, match_id: int, bookmaker: str):
        """获取特定博彩公司的赔率"""
        return (
            session.query(cls)
            .filter(cls.match_id == match_id, cls.bookmaker == bookmaker)
            .order_by(cls.collected_at.desc())
            .first()
        )

    @classmethod
    def get_market_average_odds(cls, session, match_id: int, market_type: MarketType):
        """获取市场平均赔率"""

        if market_type == MarketType.ONE_X_TWO:
            result = (
                session.query(
                    func.avg(cls.home_odds).label("avg_home"),
                    func.avg(cls.draw_odds).label("avg_draw"),
                    func.avg(cls.away_odds).label("avg_away"),
                )
                .filter(cls.match_id == match_id, cls.market_type == market_type)
                .first()
            )

            return {
                "home_odds": float(result.avg_home) if result.avg_home else None,
                "draw_odds": float(result.avg_draw) if result.avg_draw else None,
                "away_odds": float(result.avg_away) if result.avg_away else None,
            }

        elif market_type == MarketType.OVER_UNDER:
            result = (
                session.query(
                    func.avg(cls.over_odds).label("avg_over"),
                    func.avg(cls.under_odds).label("avg_under"),
                )
                .filter(cls.match_id == match_id, cls.market_type == market_type)
                .first()
            )

            return {
                "over_odds": float(result.avg_over) if result.avg_over else None,
                "under_odds": float(result.avg_under) if result.avg_under else None,
            }

        return None
