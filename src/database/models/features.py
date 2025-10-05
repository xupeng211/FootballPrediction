"""
比赛特征数据模型

存储用于机器学习预测的特征数据，包括球队统计、历史表现等。
"""

from decimal import Decimal
from enum import Enum
from typing import Dict, Optional

from sqlalchemy import DECIMAL, Boolean
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import BaseModel


class TeamType(Enum):
    """球队类型枚举"""

    HOME = "home"  # 主队
    AWAY = "away"  # 客队


class Features(BaseModel):
    """
    特征数据表模型

    存储用于机器学习预测的各种特征
    """

    __tablename__ = "features"

    # 关联信息
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, comment="比赛ID"
    )

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="球队ID"
    )

    team_type: Mapped[TeamType] = mapped_column(
        SQLEnum(TeamType), nullable=False, comment="球队类型（主队/客队）"
    )

    # 近期表现（最近5场）
    recent_5_wins: Mapped[int] = mapped_column(
        Integer, default=0, comment="近5场胜利数"
    )

    recent_5_draws: Mapped[int] = mapped_column(
        Integer, default=0, comment="近5场平局数"
    )

    recent_5_losses: Mapped[int] = mapped_column(
        Integer, default=0, comment="近5场失败数"
    )

    recent_5_goals_for: Mapped[int] = mapped_column(
        Integer, default=0, comment="近5场进球数"
    )

    recent_5_goals_against: Mapped[int] = mapped_column(
        Integer, default=0, comment="近5场失球数"
    )

    # 主客场记录
    home_wins: Mapped[int] = mapped_column(Integer, default=0, comment="主场胜利数")

    home_draws: Mapped[int] = mapped_column(Integer, default=0, comment="主场平局数")

    home_losses: Mapped[int] = mapped_column(Integer, default=0, comment="主场失败数")

    away_wins: Mapped[int] = mapped_column(Integer, default=0, comment="客场胜利数")

    away_draws: Mapped[int] = mapped_column(Integer, default=0, comment="客场平局数")

    away_losses: Mapped[int] = mapped_column(Integer, default=0, comment="客场失败数")

    # 对战历史
    h2h_wins = mapped_column(Integer, default=0, comment="对战历史胜利数")

    h2h_draws = mapped_column(Integer, default=0, comment="对战历史平局数")

    h2h_losses = mapped_column(Integer, default=0, comment="对战历史失败数")

    h2h_goals_for = mapped_column(Integer, default=0, comment="对战历史进球数")

    h2h_goals_against = mapped_column(Integer, default=0, comment="对战历史失球数")

    # 联赛排名和积分
    league_position = mapped_column(Integer, nullable=True, comment="当前联赛排名")

    points = mapped_column(Integer, nullable=True, comment="当前积分")

    goal_difference = mapped_column(Integer, nullable=True, comment="净胜球")

    # 其他特征
    days_since_last_match = mapped_column(
        Integer, nullable=True, comment="距离上场比赛天数"
    )

    is_derby = mapped_column(Boolean, nullable=True, comment="是否为德比战")

    avg_possession: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="平均控球率"
    )

    avg_shots_per_game: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均射门次数"
    )

    # 扩展特征
    avg_goals_per_game: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均进球数"
    )

    avg_shots_on_target: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均射正次数"
    )

    avg_corners_per_game: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均角球数"
    )

    avg_goals_conceded: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均失球数"
    )

    clean_sheets: Mapped[int] = mapped_column(Integer, default=0, comment="零封场次")

    avg_cards_per_game: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均红黄牌数"
    )

    # 连胜/连败记录
    current_form: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="当前状态（如 WWDLW）"
    )

    win_streak = mapped_column(Integer, default=0, comment="连胜场次")

    unbeaten_streak = mapped_column(Integer, default=0, comment="不败场次")

    # 关系定义
    match = relationship("Match", back_populates="features")

    team = relationship("Team", back_populates="features")

    # 索引定义
    __table_args__ = (
        Index("idx_features_match", "match_id"),
        Index("idx_features_team", "team_id"),
        Index("idx_features_match_team", "match_id", "team_id"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return (
            f"<Features(id={self.id}, match_id={self.match_id}, "
            f"team_id={self.team_id}, type='{self.team_type.value}')>"
        )

    @property
    def is_home_team(self) -> bool:
        """判断是否为主队特征"""
        return self.team_type == TeamType.HOME

    @property
    def recent_5_points(self) -> int:
        """计算最近5场的积分"""
        return (self.recent_5_wins * 3) + self.recent_5_draws

    def recent_5_win_rate(self) -> float:
        """计算最近5场胜率"""
        total_games = self.recent_5_wins + self.recent_5_draws + self.recent_5_losses
        if total_games == 0:
            return 0.0
        return self.recent_5_wins / total_games

    @property
    def recent_5_goal_difference(self) -> int:
        """计算最近5场净胜球"""
        return self.recent_5_goals_for - self.recent_5_goals_against

    def home_win_rate(self) -> float:
        """计算主场胜率"""
        total_home = self.home_wins + self.home_draws + self.home_losses
        if total_home == 0:
            return 0.0
        return self.home_wins / total_home

    def away_win_rate(self) -> float:
        """计算客场胜率"""
        total_away = self.away_wins + self.away_draws + self.away_losses
        if total_away == 0:
            return 0.0
        return self.away_wins / total_away

    def h2h_win_rate(self) -> float:
        """计算对战胜率"""
        total_h2h = self.h2h_wins + self.h2h_draws + self.h2h_losses
        if total_h2h == 0:
            return 0.0
        return self.h2h_wins / total_h2h

    def _get_basic_stats_features(self) -> Dict[str, float]:
        """获取基础统计特征"""
        return {
            "recent_5_wins": float(self.recent_5_wins),
            "recent_5_draws": float(self.recent_5_draws),
            "recent_5_losses": float(self.recent_5_losses),
            "recent_5_goals_for": float(self.recent_5_goals_for),
            "recent_5_goals_against": float(self.recent_5_goals_against),
            "recent_5_points": float(self.recent_5_points),
            "recent_5_win_rate": float(self.recent_5_win_rate()),
            "recent_5_goal_difference": float(self.recent_5_goal_difference),
        }

    def _get_home_away_features(self) -> Dict[str, float]:
        """获取主客场统计特征"""
        return {
            "home_wins": float(self.home_wins),
            "home_draws": float(self.home_draws),
            "home_losses": float(self.home_losses),
            "away_wins": float(self.away_wins),
            "away_draws": float(self.away_draws),
            "away_losses": float(self.away_losses),
            "home_win_rate": float(self.home_win_rate()),
            "away_win_rate": float(self.away_win_rate()),
        }

    def _get_h2h_features(self) -> Dict[str, float]:
        """获取对战历史特征"""
        return {
            "h2h_wins": float(self.h2h_wins),
            "h2h_draws": float(self.h2h_draws),
            "h2h_losses": float(self.h2h_losses),
            "h2h_goals_for": float(self.h2h_goals_for),
            "h2h_goals_against": float(self.h2h_goals_against),
            "h2h_win_rate": float(self.h2h_win_rate()),
        }

    def _get_league_features(self) -> Dict[str, float]:
        """获取联赛状况特征"""
        return {
            "league_position": (
                float(self.league_position) if self.league_position else 0.0
            ),
            "points": float(self.points) if self.points else 0.0,
            "goal_difference": (
                float(self.goal_difference) if self.goal_difference else 0.0
            ),
        }

    def _get_extended_features(self) -> Dict[str, float]:
        """获取扩展特征"""
        return {
            "days_since_last_match": (
                float(self.days_since_last_match) if self.days_since_last_match else 0.0
            ),
            "is_derby": float(int(self.is_derby)) if self.is_derby is not None else 0.0,
            "avg_possession": (
                float(self.avg_possession) if self.avg_possession else 0.0
            ),
            "avg_shots_per_game": (
                float(self.avg_shots_per_game) if self.avg_shots_per_game else 0.0
            ),
            "avg_goals_per_game": (
                float(self.avg_goals_per_game) if self.avg_goals_per_game else 0.0
            ),
            "avg_shots_on_target": (
                float(self.avg_shots_on_target) if self.avg_shots_on_target else 0.0
            ),
            "avg_corners_per_game": (
                float(self.avg_corners_per_game) if self.avg_corners_per_game else 0.0
            ),
            "avg_goals_conceded": (
                float(self.avg_goals_conceded) if self.avg_goals_conceded else 0.0
            ),
            "clean_sheets": float(self.clean_sheets),
            "avg_cards_per_game": (
                float(self.avg_cards_per_game) if self.avg_cards_per_game else 0.0
            ),
            "win_streak": float(self.win_streak),
            "unbeaten_streak": float(self.unbeaten_streak),
        }

    def get_feature_vector(self) -> Dict[str, float]:
        """
        获取特征向量（用于机器学习）

        Returns:
            Dict[str, float]: 包含所有特征的字典
        """
        features = {}
        features.update(self._get_basic_stats_features())
        features.update(self._get_home_away_features())
        features.update(self._get_h2h_features())
        features.update(self._get_league_features())
        features.update(self._get_extended_features())
        return features

    def calculate_team_strength(self) -> float:
        """
        计算球队实力评分

        Returns:
            float: 球队实力评分 (0-100)
        """
        # 基于多个维度计算综合实力
        score = 0.0

        # 最近状态 (30%)
        recent_score = (
            self.recent_5_win_rate() * 0.6
            + (self.recent_5_goal_difference + 10) / 20 * 0.4
        )
        score += recent_score * 0.3

        # 主客场表现 (25%)
        if self.is_home_team:
            home_away_score = self.home_win_rate()
        else:
            home_away_score = self.away_win_rate()
        score += home_away_score * 0.25

        # 对战历史 (20%)
        h2h_score = self.h2h_win_rate()
        score += h2h_score * 0.2

        # 联赛排名 (15%)
        if self.league_position:
            # 假设联赛有20支球队，排名越靠前分数越高
            position_score = max(0, (21 - self.league_position) / 20)
            score += position_score * 0.15

        # 其他因素 (10%)
        other_score = 0.5  # 基础分
        if self.avg_goals_per_game and self.avg_goals_conceded:
            attack_defense_ratio = float(self.avg_goals_per_game) / (
                float(self.avg_goals_conceded) + 0.1
            )
            other_score = min(1.0, attack_defense_ratio / 3)

        score += other_score * 0.1

        return min(100.0, score * 100)

    @classmethod
    def get_match_features(cls, session, match_id: int):
        """获取比赛的特征数据"""
        return session.query(cls).filter(cls.match_id == match_id).all()

    @classmethod
    def get_team_features(cls, session, team_id: int, limit: int = 10):
        """获取球队的最近特征数据"""
        return (
            session.query(cls)
            .filter(cls.team_id == team_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
            .all()
        )
