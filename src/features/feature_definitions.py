# mypy: ignore-errors
"""特征定义.

定义足球预测系统中的核心特征：
- 近期战绩特征：recent_5_wins, goals_for/against
- 历史对战特征:h2h_wins, h2h_goals_avg
- 赔率特征:implied_probability, bookmaker_consensus
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from .entities import MatchEntity, TeamEntity


@dataclass
class RecentPerformanceFeatures:
    """类文档字符串."""

    pass  # 添加pass语句
    """
    近期战绩特征

    计算球队近期（最近5场比赛）的表现指标
    """

    # 基础信息
    team_id: int
    calculation_date: datetime

    # 近期战绩特征 (最近5场)
    recent_5_wins: int = 0  # 近5场胜利数
    recent_5_draws: int = 0  # 近5场平局数
    recent_5_losses: int = 0  # 近5场失败数
    recent_5_goals_for: int = 0  # 近5场进球数
    recent_5_goals_against: int = 0  # 近5场失球数
    recent_5_points: int = 0  # 近5场积分

    # 主客场分别统计
    recent_5_home_wins: int = 0  # 近5场主场胜利
    recent_5_away_wins: int = 0  # 近5场客场胜利
    recent_5_home_goals_for: int = 0  # 近5场主场进球
    recent_5_away_goals_for: int = 0  # 近5场客场进球

    # 计算属性
    @property
    def recent_5_win_rate(self) -> float:
        """近5场胜率."""
        total_games = self.recent_5_wins + self.recent_5_draws + self.recent_5_losses
        return self.recent_5_wins / total_games if total_games > 0 else 0.0

    @property
    def recent_5_goals_per_game(self) -> float:
        """近5场场均进球."""
        total_games = self.recent_5_wins + self.recent_5_draws + self.recent_5_losses
        return self.recent_5_goals_for / total_games if total_games > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "team_id": self.team_id,
            "calculation_date": self.calculation_date.isoformat(),
            "recent_5_wins": self.recent_5_wins,
            "recent_5_draws": self.recent_5_draws,
            "recent_5_losses": self.recent_5_losses,
            "recent_5_goals_for": self.recent_5_goals_for,
            "recent_5_goals_against": self.recent_5_goals_against,
            "recent_5_points": self.recent_5_points,
            "recent_5_home_wins": self.recent_5_home_wins,
            "recent_5_away_wins": self.recent_5_away_wins,
            "recent_5_home_goals_for": self.recent_5_home_goals_for,
            "recent_5_away_goals_for": self.recent_5_away_goals_for,
            "recent_5_win_rate": self.recent_5_win_rate,
            "recent_5_goals_per_game": self.recent_5_goals_per_game,
        }


@dataclass
class HistoricalMatchupFeatures:
    """类文档字符串."""

    pass  # 添加pass语句
    """
    历史对战特征

    计算两支球队的历史对战记录
    """

    # 基础信息
    home_team_id: int
    away_team_id: int
    calculation_date: datetime

    # 历史对战特征 (所有历史比赛)
    h2h_total_matches: int = 0  # 历史对战总场次
    h2h_home_wins: int = 0  # 主队历史胜利数
    h2h_away_wins: int = 0  # 客队历史胜利数
    h2h_draws: int = 0  # 历史平局数
    h2h_home_goals_total: int = 0  # 主队历史进球总数
    h2h_away_goals_total: int = 0  # 客队历史进球总数

    # 近期对战 (最近5次交手)
    h2h_recent_5_home_wins: int = 0  # 近5次主队胜利
    h2h_recent_5_away_wins: int = 0  # 近5次客队胜利
    h2h_recent_5_draws: int = 0  # 近5次平局

    # 计算属性
    @property
    def h2h_home_win_rate(self) -> float:
        """主队历史胜率."""
        return (
            self.h2h_home_wins / self.h2h_total_matches
            if self.h2h_total_matches > 0
            else 0.0
        )

    @property
    def h2h_goals_avg(self) -> float:
        """历史对战场均总进球数."""
        total_goals = self.h2h_home_goals_total + self.h2h_away_goals_total
        return (
            total_goals / self.h2h_total_matches if self.h2h_total_matches > 0 else 0.0
        )

    @property
    def h2h_home_goals_avg(self) -> float:
        """主队历史场均进球."""
        return (
            self.h2h_home_goals_total / self.h2h_total_matches
            if self.h2h_total_matches > 0
            else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "calculation_date": self.calculation_date.isoformat(),
            "h2h_total_matches": self.h2h_total_matches,
            "h2h_home_wins": self.h2h_home_wins,
            "h2h_away_wins": self.h2h_away_wins,
            "h2h_draws": self.h2h_draws,
            "h2h_home_goals_total": self.h2h_home_goals_total,
            "h2h_away_goals_total": self.h2h_away_goals_total,
            "h2h_recent_5_home_wins": self.h2h_recent_5_home_wins,
            "h2h_recent_5_away_wins": self.h2h_recent_5_away_wins,
            "h2h_recent_5_draws": self.h2h_recent_5_draws,
            "h2h_home_win_rate": self.h2h_home_win_rate,
            "h2h_goals_avg": self.h2h_goals_avg,
            "h2h_home_goals_avg": self.h2h_home_goals_avg,
        }


@dataclass
class OddsFeatures:
    """类文档字符串."""

    pass  # 添加pass语句
    """
    赔率特征

    从博彩赔率中计算隐含概率和市场共识
    """

    # 基础信息
    match_id: int
    calculation_date: datetime

    # 赔率数据
    home_odds_avg: Decimal | None = None  # 主胜平均赔率
    draw_odds_avg: Decimal | None = None  # 平局平均赔率
    away_odds_avg: Decimal | None = None  # 客胜平均赔率

    # 赔率特征
    home_implied_probability: float | None = None  # 主胜隐含概率
    draw_implied_probability: float | None = None  # 平局隐含概率
    away_implied_probability: float | None = None  # 客胜隐含概率

    # 市场共识特征
    bookmaker_count: int = 0  # 参与博彩公司数量
    odds_variance_home: float | None = None  # 主胜赔率方差
    odds_variance_draw: float | None = None  # 平局赔率方差
    odds_variance_away: float | None = None  # 客胜赔率方差

    # 价值特征
    max_home_odds: Decimal | None = None  # 最高主胜赔率
    min_home_odds: Decimal | None = None  # 最低主胜赔率
    odds_range_home: float | None = None  # 主胜赔率范围

    # 计算属性
    @property
    def bookmaker_consensus(self) -> float | None:
        """博彩公司共识度 (1 - 平均方差)."""
        if all(
            v is not None
            for v in [
                self.odds_variance_home,
                self.odds_variance_draw,
                self.odds_variance_away,
            ]
        ):
            # 验证方差值是否存在
            home_var = self.odds_variance_home
            draw_var = self.odds_variance_draw
            away_var = self.odds_variance_away
            if not (
                home_var is not None and draw_var is not None and away_var is not None
            ):
                raise ValueError("计算赔率稳定性需要所有方差值都不能为None")

            avg_variance = (home_var + draw_var + away_var) / 3
            return 1.0 - min(avg_variance, 1.0)  # 限制在0-1之间
        return None

    @property
    def market_efficiency(self) -> float | None:
        """市场效率 (总隐含概率)."""
        if all(
            p is not None
            for p in [
                self.home_implied_probability,
                self.draw_implied_probability,
                self.away_implied_probability,
            ]
        ):
            # Type assertions since we've checked for None above'
            home_prob = self.home_implied_probability
            draw_prob = self.draw_implied_probability
            away_prob = self.away_implied_probability
            if not (
                home_prob is not None
                and draw_prob is not None
                and away_prob is not None
            ):
                raise ValueError("计算总隐含概率需要所有概率值都不能为None")

            return home_prob + draw_prob + away_prob
        return None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "match_id": self.match_id,
            "calculation_date": self.calculation_date.isoformat(),
            "home_odds_avg": float(self.home_odds_avg) if self.home_odds_avg else None,
            "draw_odds_avg": float(self.draw_odds_avg) if self.draw_odds_avg else None,
            "away_odds_avg": float(self.away_odds_avg) if self.away_odds_avg else None,
            "home_implied_probability": self.home_implied_probability,
            "draw_implied_probability": self.draw_implied_probability,
            "away_implied_probability": self.away_implied_probability,
            "bookmaker_count": self.bookmaker_count,
            "odds_variance_home": self.odds_variance_home,
            "odds_variance_draw": self.odds_variance_draw,
            "odds_variance_away": self.odds_variance_away,
            "max_home_odds": float(self.max_home_odds) if self.max_home_odds else None,
            "min_home_odds": float(self.min_home_odds) if self.min_home_odds else None,
            "odds_range_home": self.odds_range_home,
            "bookmaker_consensus": self.bookmaker_consensus,
            "market_efficiency": self.market_efficiency,
        }


@dataclass
class AllMatchFeatures:
    """类文档字符串."""

    pass  # 添加pass语句
    """
    比赛完整特征集合

    包含一场比赛的所有特征
    """

    match_entity: MatchEntity
    home_team_recent: RecentPerformanceFeatures
    away_team_recent: RecentPerformanceFeatures
    historical_matchup: HistoricalMatchupFeatures
    odds_features: OddsFeatures

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "match_entity": self.match_entity.to_dict(),
            "home_team_recent": self.home_team_recent.to_dict(),
            "away_team_recent": self.away_team_recent.to_dict(),
            "historical_matchup": self.historical_matchup.to_dict(),
            "odds_features": self.odds_features.to_dict(),
        }


@dataclass
class AllTeamFeatures:
    """类文档字符串."""

    pass  # 添加pass语句
    """
    球队完整特征集合

    包含一支球队的所有特征
    """

    team_entity: TeamEntity
    recent_performance: RecentPerformanceFeatures

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "team_entity": self.team_entity.to_dict(),
            "recent_performance": self.recent_performance.to_dict(),
        }
