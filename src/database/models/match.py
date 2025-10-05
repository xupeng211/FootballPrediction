"""
比赛模型

存储足球比赛的详细信息，包括比赛时间、比分、状态等。
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import CheckConstraint, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import BaseModel


class MatchStatus(Enum):
    """比赛状态枚举"""

    SCHEDULED = "scheduled"  # 已安排
    LIVE = "live"  # 进行中
    FINISHED = "finished"  # 已结束
    CANCELLED = "cancelled"  # 已取消


class Match(BaseModel):
    """
    比赛表模型

    对应 architecture.md 中的 matches 表设计
    """

    __tablename__ = "matches"

    # 外键关联
    home_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="主队ID"
    )

    away_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="客队ID"
    )

    league_id: Mapped[int] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, comment="联赛ID"
    )

    season: Mapped[str] = mapped_column(String(20), nullable=False, comment="赛季")

    # 比赛时间
    match_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="比赛时间")

    match_status: Mapped[MatchStatus] = mapped_column(
        SQLEnum(MatchStatus),
        nullable=False,
        default=MatchStatus.SCHEDULED,
        comment="比赛状态",
    )

    # 比分信息
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="主队比分")

    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="客队比分")

    home_ht_score: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="主队半场比分"
    )

    away_ht_score: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="客队半场比分"
    )

    minute: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="比赛进行时间（分钟）"
    )

    # 比赛详情
    venue: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="比赛场地")

    referee: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="主裁判")

    weather: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="天气情况")

    # 关系定义
    home_team = relationship(
        "Team", foreign_keys="Match.home_team_id", back_populates="home_matches"
    )

    away_team = relationship(
        "Team", foreign_keys="Match.away_team_id", back_populates="away_matches"
    )

    league = relationship("League", back_populates="matches")

    # 赔率信息
    odds = relationship(
        "Odds", back_populates="match", lazy="dynamic", cascade="all, delete-orphan"
    )

    # 特征数据
    features = relationship(
        "Features", back_populates="match", lazy="dynamic", cascade="all, delete-orphan"
    )

    # 预测结果
    predictions = relationship(
        "Predictions",
        back_populates="match",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # 索引和约束定义
    __table_args__ = (
        # 索引定义
        Index("idx_matches_date", "match_time"),
        Index("idx_matches_teams", "home_team_id", "away_team_id"),
        Index("idx_matches_league_season", "league_id", "season"),
        Index("idx_matches_status", "match_status"),
        Index("idx_matches_home_team_date", "home_team_id", "match_time"),
        Index("idx_matches_away_team_date", "away_team_id", "match_time"),
        # CHECK约束定义 - 确保数据完整性
        CheckConstraint("home_score >= 0 AND home_score <= 99", name="ck_matches_home_score_range"),
        CheckConstraint("away_score >= 0 AND away_score <= 99", name="ck_matches_away_score_range"),
        CheckConstraint(
            "home_ht_score >= 0 AND home_ht_score <= 99",
            name="ck_matches_home_ht_score_range",
        ),
        CheckConstraint(
            "away_ht_score >= 0 AND away_ht_score <= 99",
            name="ck_matches_away_ht_score_range",
        ),
        CheckConstraint("match_time > '2000-01-01'", name="ck_matches_match_time_range"),
        CheckConstraint("home_team_id != away_team_id", name="ck_matches_different_teams"),
        CheckConstraint("minute >= 0 AND minute <= 120", name="ck_matches_minute_range"),
    )

    def __repr__(self) -> str:
        return (
            f"<Match(id={self.id}, "
            f"home='{self.home_team.team_name if self.home_team else 'Unknown'}', "
            f"away='{self.away_team.team_name if self.away_team else 'Unknown'}', "
            f"date='{self.match_time}')>"
        )

    @property
    def match_name(self) -> str:
        """返回比赛名称"""
        if self.home_team and self.away_team:
            return f"{self.home_team.team_name} vs {self.away_team.team_name}"
        return f"Match {self.id}"

    @property
    def is_finished(self) -> bool:
        """判断比赛是否已结束"""
        return self.match_status == MatchStatus.FINISHED

    @property
    def is_upcoming(self) -> bool:
        """判断比赛是否未来进行"""
        return self.match_status == MatchStatus.SCHEDULED and self.match_time > datetime.utcnow()

    @property
    def final_score(self) -> Optional[str]:
        """返回最终比分"""
        if self.home_score is not None and self.away_score is not None:
            return f"{self.home_score}-{self.away_score}"
        return None

    @property
    def ht_score(self) -> Optional[str]:
        """返回半场比分"""
        if self.home_ht_score is not None and self.away_ht_score is not None:
            return f"{self.home_ht_score}-{self.away_ht_score}"
        return None

    def get_result(self) -> Optional[str]:
        """
        获取比赛结果

        Returns:
            Optional[str]: 'home_win', 'draw', 'away_win' 或 None（未结束）
        """
        if not self.is_finished or self.home_score is None or self.away_score is None:
            return None

        if self.home_score > self.away_score:
            return "home_win"
        elif self.home_score == self.away_score:
            return "draw"
        else:
            return "away_win"

    def get_total_goals(self) -> Optional[int]:
        """获取总进球数"""
        if self.home_score is not None and self.away_score is not None:
            return self.home_score + self.away_score
        return None

    def is_over_2_5_goals(self) -> Optional[bool]:
        """判断是否大于2.5球"""
        total_goals = self.get_total_goals()
        if total_goals is not None:
            return total_goals > 2.5
        return None

    def both_teams_scored(self) -> Optional[bool]:
        """判断双方是否都有进球"""
        if self.home_score is not None and self.away_score is not None:
            return self.home_score > 0 and self.away_score > 0
        return None

    def get_match_stats(self) -> Dict[str, Any]:
        """获取比赛统计信息"""
        stats = {
            "match_id": self.id,
            "home_team": self.home_team.team_name if self.home_team else None,
            "away_team": self.away_team.team_name if self.away_team else None,
            "league": self.league.league_name if self.league else None,
            "match_date": self.match_time,
            "status": self.match_status.value,
            "final_score": self.final_score,
            "ht_score": self.ht_score,
            "result": self.get_result(),
            "total_goals": self.get_total_goals(),
            "over_2_5": self.is_over_2_5_goals(),
            "both_teams_scored": self.both_teams_scored(),
            "referee": self.referee,
            "venue": self.venue,
            "weather": self.weather,
        }
        return stats

    def update_score(
        self,
        home_score: int,
        away_score: int,
        home_ht: Optional[int] = None,
        away_ht: Optional[int] = None,
    ):
        """更新比赛比分"""
        self.home_score = home_score
        self.away_score = away_score

        if home_ht is not None:
            self.home_ht_score = home_ht

        if away_ht is not None:
            self.away_ht_score = away_ht

        # 如果比赛结束，更新状态
        if self.match_status == MatchStatus.LIVE:
            self.match_status = MatchStatus.FINISHED

    @classmethod
    def get_by_teams_and_date(
        cls, session, home_team_id: int, away_team_id: int, match_date: datetime
    ):
        """根据球队和日期获取比赛"""
        return (
            session.query(cls)
            .filter(
                cls.home_team_id == home_team_id,
                cls.away_team_id == away_team_id,
                cls.match_time == match_date,
            )
            .first()
        )

    @classmethod
    def get_upcoming_matches(cls, session, days: int = 7):
        """获取未来几天的比赛"""

        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days)

        return (
            session.query(cls)
            .filter(
                cls.match_status == MatchStatus.SCHEDULED,
                cls.match_time.between(start_date, end_date),  # type: ignore
            )
            .order_by(cls.match_time)
            .all()
        )  # type: ignore

    @classmethod
    def get_finished_matches(
        cls, session, league_id: Optional[int] = None, season: Optional[str] = None
    ):
        """获取已结束的比赛"""
        query = session.query(cls).filter(cls.match_status == MatchStatus.FINISHED)

        if league_id:
            query = query.filter(cls.league_id == league_id)
        if season:
            query = query.filter(cls.season == season)

        return query.order_by(cls.match_time.desc()).all()  # type: ignore

    @classmethod
    def get_team_matches(cls, session, team_id: int, season: Optional[str] = None):
        """获取某个球队的所有比赛"""
        from sqlalchemy import or_

        query = session.query(cls).filter(
            or_(cls.home_team_id == team_id, cls.away_team_id == team_id)  # type: ignore
        )

        if season:
            query = query.filter(cls.season == season)

        return query.order_by(cls.match_time.desc()).all()  # type: ignore
