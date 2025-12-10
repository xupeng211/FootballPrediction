"""
特征定义模块.

定义足球预测系统中的核心特征数据结构和验证规则。
包含完整的类型定义、数据质量检查和特征键常量。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Union


# 特征键常量定义
class FeatureKeys:
    """特征键常量定义，避免字符串硬编码。"""

    # 基础比赛信息
    MATCH_ID = "match_id"
    HOME_TEAM_ID = "home_team_id"
    AWAY_TEAM_ID = "away_team_id"
    LEAGUE_ID = "league_id"
    MATCH_DATE = "match_date"
    SEASON = "season"

    # 近期战绩特征
    HOME_RECENT_5_WINS = "home_recent_5_wins"
    HOME_RECENT_5_DRAWS = "home_recent_5_draws"
    HOME_RECENT_5_LOSSES = "home_recent_5_losses"
    HOME_RECENT_5_GOALS_FOR = "home_recent_5_goals_for"
    HOME_RECENT_5_GOALS_AGAINST = "home_recent_5_goals_against"
    HOME_RECENT_5_POINTS = "home_recent_5_points"
    HOME_RECENT_5_WIN_RATE = "home_recent_5_win_rate"

    AWAY_RECENT_5_WINS = "away_recent_5_wins"
    AWAY_RECENT_5_DRAWS = "away_recent_5_draws"
    AWAY_RECENT_5_LOSSES = "away_recent_5_losses"
    AWAY_RECENT_5_GOALS_FOR = "away_recent_5_goals_for"
    AWAY_RECENT_5_GOALS_AGAINST = "away_recent_5_goals_against"
    AWAY_RECENT_5_POINTS = "away_recent_5_points"
    AWAY_RECENT_5_WIN_RATE = "away_recent_5_win_rate"

    # 历史对战特征
    H2H_TOTAL_MATCHES = "h2h_total_matches"
    H2H_HOME_WINS = "h2h_home_wins"
    H2H_AWAY_WINS = "h2h_away_wins"
    H2H_DRAWS = "h2h_draws"
    H2H_HOME_GOALS = "h2h_home_goals"
    H2H_AWAY_GOALS = "h2h_away_goals"
    H2H_AVG_TOTAL_GOALS = "h2h_avg_total_goals"
    H2H_HOME_WIN_RATE = "h2h_home_win_rate"

    # 赔率特征
    HOME_WIN_ODDS = "home_win_odds"
    DRAW_ODDS = "draw_odds"
    AWAY_WIN_ODDS = "away_win_odds"
    HOME_IMPLIED_PROBABILITY = "home_implied_probability"
    DRAW_IMPLIED_PROBABILITY = "draw_implied_probability"
    AWAY_IMPLIED_PROBABILITY = "away_implied_probability"
    BOOKMAKER_CONSENSUS = "bookmaker_consensus"

    # 高级分析特征
    HOME_XG = "home_xg"
    AWAY_XG = "away_xg"
    HOME_XGA = "home_xga"
    AWAY_XGA = "away_xga"
    HOME_PPDA = "home_ppda"
    AWAY_PPDA = "away_ppda"
    HOME_POSSESSION = "home_possession"
    AWAY_POSSESSION = "away_possession"

    # 统计特征
    HOME_AVG_GOALS_SCORED = "home_avg_goals_scored"
    HOME_AVG_GOALS_CONCEDED = "home_avg_goals_conceded"
    AWAY_AVG_GOALS_SCORED = "away_avg_goals_scored"
    AWAY_AVG_GOALS_CONCEDED = "away_avg_goals_conceded"

    # 时间特征
    DAYS_SINCE_LAST_HOME = "days_since_last_home"
    DAYS_SINCE_LAST_AWAY = "days_since_last_away"
    DAYS_SINCE_LAST_H2H = "days_since_last_h2h"


class FeatureType(Enum):
    """特征类型枚举。"""

    CATEGORICAL = "categorical"  # 分类特征
    NUMERICAL = "numerical"  # 数值特征
    BOOLEAN = "boolean"  # 布尔特征
    TEMPORAL = "temporal"  # 时间特征


@dataclass
class FeatureDefinition:
    """特征定义数据类。"""

    key: str
    name: str
    feature_type: FeatureType
    description: str
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    required: bool = True
    default_value: Optional[Any] = None


# 所有特征定义的注册表
FEATURE_DEFINITIONS: dict[str, FeatureDefinition] = {
    # 基础比赛信息
    FeatureKeys.MATCH_ID: FeatureDefinition(
        key=FeatureKeys.MATCH_ID,
        name="Match ID",
        feature_type=FeatureType.NUMERICAL,
        description="比赛唯一标识符",
        min_value=1,
        required=True,
    ),
    FeatureKeys.HOME_TEAM_ID: FeatureDefinition(
        key=FeatureKeys.HOME_TEAM_ID,
        name="Home Team ID",
        feature_type=FeatureType.NUMERICAL,
        description="主队ID",
        min_value=1,
        required=True,
    ),
    FeatureKeys.AWAY_TEAM_ID: FeatureDefinition(
        key=FeatureKeys.AWAY_TEAM_ID,
        name="Away Team ID",
        feature_type=FeatureType.NUMERICAL,
        description="客队ID",
        min_value=1,
        required=True,
    ),
    # 近期战绩特征
    FeatureKeys.HOME_RECENT_5_WINS: FeatureDefinition(
        key=FeatureKeys.HOME_RECENT_5_WINS,
        name="Home Recent 5 Wins",
        feature_type=FeatureType.NUMERICAL,
        description="主队近5场比赛胜利数",
        min_value=0,
        max_value=5,
        default_value=0,
    ),
    FeatureKeys.HOME_RECENT_5_WIN_RATE: FeatureDefinition(
        key=FeatureKeys.HOME_RECENT_5_WIN_RATE,
        name="Home Recent 5 Win Rate",
        feature_type=FeatureType.NUMERICAL,
        description="主队近5场比赛胜率",
        min_value=0.0,
        max_value=1.0,
        default_value=0.0,
    ),
    FeatureKeys.AWAY_RECENT_5_WINS: FeatureDefinition(
        key=FeatureKeys.AWAY_RECENT_5_WINS,
        name="Away Recent 5 Wins",
        feature_type=FeatureType.NUMERICAL,
        description="客队近5场比赛胜利数",
        min_value=0,
        max_value=5,
        default_value=0,
    ),
    FeatureKeys.AWAY_RECENT_5_WIN_RATE: FeatureDefinition(
        key=FeatureKeys.AWAY_RECENT_5_WIN_RATE,
        name="Away Recent 5 Win Rate",
        feature_type=FeatureType.NUMERICAL,
        description="客队近5场比赛胜率",
        min_value=0.0,
        max_value=1.0,
        default_value=0.0,
    ),
    # 历史对战特征
    FeatureKeys.H2H_TOTAL_MATCHES: FeatureDefinition(
        key=FeatureKeys.H2H_TOTAL_MATCHES,
        name="H2H Total Matches",
        feature_type=FeatureType.NUMERICAL,
        description="两队历史交锋总场次",
        min_value=0,
        default_value=0,
    ),
    FeatureKeys.H2H_HOME_WIN_RATE: FeatureDefinition(
        key=FeatureKeys.H2H_HOME_WIN_RATE,
        name="H2H Home Win Rate",
        feature_type=FeatureType.NUMERICAL,
        description="历史交锋中主队胜率",
        min_value=0.0,
        max_value=1.0,
        default_value=0.0,
    ),
    # 赔率特征
    FeatureKeys.HOME_WIN_ODDS: FeatureDefinition(
        key=FeatureKeys.HOME_WIN_ODDS,
        name="Home Win Odds",
        feature_type=FeatureType.NUMERICAL,
        description="主胜赔率",
        min_value=1.01,
        default_value=0.0,
    ),
    FeatureKeys.HOME_IMPLIED_PROBABILITY: FeatureDefinition(
        key=FeatureKeys.HOME_IMPLIED_PROBABILITY,
        name="Home Implied Probability",
        feature_type=FeatureType.NUMERICAL,
        description="主胜隐含概率",
        min_value=0.0,
        max_value=1.0,
        default_value=0.0,
    ),
    # 高级分析特征
    FeatureKeys.HOME_XG: FeatureDefinition(
        key=FeatureKeys.HOME_XG,
        name="Home Expected Goals",
        feature_type=FeatureType.NUMERICAL,
        description="主队预期进球数",
        min_value=0.0,
        max_value=10.0,
        default_value=0.0,
    ),
    FeatureKeys.AWAY_XG: FeatureDefinition(
        key=FeatureKeys.AWAY_XG,
        name="Away Expected Goals",
        feature_type=FeatureType.NUMERICAL,
        description="客队预期进球数",
        min_value=0.0,
        max_value=10.0,
        default_value=0.0,
    ),
    FeatureKeys.HOME_POSSESSION: FeatureDefinition(
        key=FeatureKeys.HOME_POSSESSION,
        name="Home Possession",
        feature_type=FeatureType.NUMERICAL,
        description="主队控球率",
        min_value=0.0,
        max_value=100.0,
        default_value=50.0,
    ),
    # 统计特征
    FeatureKeys.HOME_AVG_GOALS_SCORED: FeatureDefinition(
        key=FeatureKeys.HOME_AVG_GOALS_SCORED,
        name="Home Avg Goals Scored",
        feature_type=FeatureType.NUMERICAL,
        description="主队场均进球数",
        min_value=0.0,
        max_value=10.0,
        default_value=0.0,
    ),
}


@dataclass
class RecentPerformanceFeatures:
    """近期战绩特征数据结构。"""

    team_id: int
    calculation_date: datetime

    # 近期战绩特征 (最近5场)
    recent_5_wins: int = field(default=0)
    recent_5_draws: int = field(default=0)
    recent_5_losses: int = field(default=0)
    recent_5_goals_for: int = field(default=0)
    recent_5_goals_against: int = field(default=0)
    recent_5_points: int = field(default=0)

    # 主客场分别统计
    recent_5_home_wins: int = field(default=0)
    recent_5_away_wins: int = field(default=0)
    recent_5_home_goals_for: int = field(default=0)
    recent_5_away_goals_for: int = field(default=0)

    @property
    def recent_5_win_rate(self) -> float:
        """近5场胜率。"""
        return self.recent_5_wins / 5.0 if self.recent_5_wins > 0 else 0.0

    @property
    def recent_5_goals_diff(self) -> int:
        """近5场净胜球。"""
        return self.recent_5_goals_for - self.recent_5_goals_against

    def validate(self) -> list[str]:
        """验证数据完整性。"""
        errors = []

        if self.recent_5_wins < 0 or self.recent_5_wins > 5:
            errors.append(f"Invalid recent_5_wins: {self.recent_5_wins}")

        if self.recent_5_draws < 0 or self.recent_5_draws > 5:
            errors.append(f"Invalid recent_5_draws: {self.recent_5_draws}")

        if self.recent_5_losses < 0 or self.recent_5_losses > 5:
            errors.append(f"Invalid recent_5_losses: {self.recent_5_losses}")

        total_matches = self.recent_5_wins + self.recent_5_draws + self.recent_5_losses
        if total_matches > 5:
            errors.append(f"Total matches exceed 5: {total_matches}")

        return errors


@dataclass
class HeadToHeadFeatures:
    """历史对战特征数据结构。"""

    home_team_id: int
    away_team_id: int
    calculation_date: datetime

    # 历史对战统计
    total_matches: int = field(default=0)
    home_wins: int = field(default=0)
    away_wins: int = field(default=0)
    draws: int = field(default=0)
    home_goals: int = field(default=0)
    away_goals: int = field(default=0)

    @property
    def home_win_rate(self) -> float:
        """主队历史胜率。"""
        return self.home_wins / self.total_matches if self.total_matches > 0 else 0.0

    @property
    def avg_total_goals(self) -> float:
        """历史场均总进球数。"""
        return (
            (self.home_goals + self.away_goals) / self.total_matches
            if self.total_matches > 0
            else 0.0
        )

    def validate(self) -> list[str]:
        """验证数据完整性。"""
        errors = []

        if self.total_matches < 0:
            errors.append(f"Invalid total_matches: {self.total_matches}")

        calculated_total = self.home_wins + self.away_wins + self.draws
        if calculated_total != self.total_matches:
            errors.append(f"Total mismatch: {calculated_total} != {self.total_matches}")

        if self.home_wins < 0 or self.away_wins < 0 or self.draws < 0:
            errors.append("Negative match counts detected")

        return errors


@dataclass
class OddsFeatures:
    """赔率特征数据结构。"""

    match_id: int
    calculation_date: datetime
    bookmaker: str

    # 赔率信息
    home_win_odds: Optional[float] = field(default=None)
    draw_odds: Optional[float] = field(default=None)
    away_win_odds: Optional[float] = field(default=None)

    @property
    def home_implied_probability(self) -> Optional[float]:
        """主胜隐含概率。"""
        if self.home_win_odds and self.home_win_odds > 1:
            return 1.0 / self.home_win_odds
        return None

    @property
    def bookmaker_consensus(self) -> Optional[str]:
        """庄家倾向。"""
        if all([self.home_win_odds, self.draw_odds, self.away_win_odds]):
            min_odds = min(self.home_win_odds, self.draw_odds, self.away_win_odds)
            if min_odds == self.home_win_odds:
                return "home"
            elif min_odds == self.away_win_odds:
                return "away"
            else:
                return "draw"
        return None

    def validate(self) -> list[str]:
        """验证赔率数据的合理性。"""
        errors = []

        if self.home_win_odds is not None and self.home_win_odds <= 1.0:
            errors.append(f"Invalid home_win_odds: {self.home_win_odds}")

        if self.draw_odds is not None and self.draw_odds <= 1.0:
            errors.append(f"Invalid draw_odds: {self.draw_odds}")

        if self.away_win_odds is not None and self.away_win_odds <= 1.0:
            errors.append(f"Invalid away_win_odds: {self.away_win_odds}")

        return errors


@dataclass
class AdvancedStatsFeatures:
    """高级统计特征数据结构。"""

    match_id: int
    team_id: int
    calculation_date: datetime

    # xG (Expected Goals) 特征
    xg: Optional[float] = field(default=None)
    xga: Optional[float] = field(default=None)

    # PPDA (Passes Per Defensive Action) 特征
    ppda: Optional[float] = field(default=None)

    # 控球率
    possession: Optional[float] = field(default=None)

    def validate(self) -> list[str]:
        """验证高级统计数据。"""
        errors = []

        if self.xg is not None and (self.xg < 0 or self.xg > 10):
            errors.append(f"Invalid xg: {self.xg}")

        if self.xga is not None and (self.xga < 0 or self.xga > 10):
            errors.append(f"Invalid xga: {self.xga}")

        if self.possession is not None and (
            self.possession < 0 or self.possession > 100
        ):
            errors.append(f"Invalid possession: {self.possession}")

        if self.ppda is not None and (self.ppda < 0 or self.ppda > 50):
            errors.append(f"Invalid ppda: {self.ppda}")

        return errors


class FeatureValidator:
    """特征数据验证器。"""

    @staticmethod
    def validate_feature_data(features: dict[str, Any]) -> list[str]:
        """
        验证特征数据的有效性。

        Args:
            features: 特征数据字典

        Returns:
            验证错误列表
        """
        errors = []

        for key, definition in FEATURE_DEFINITIONS.items():
            if definition.required and key not in features:
                errors.append(f"Missing required feature: {key}")
                continue

            if key not in features:
                continue

            value = features[key]

            # 类型验证
            if definition.feature_type == FeatureType.NUMERICAL:
                if not isinstance(value, int | float):
                    errors.append(f"Feature {key} must be numerical, got {type(value)}")
                    continue

                # 范围验证
                if definition.min_value is not None and value < definition.min_value:
                    errors.append(
                        f"Feature {key} value {value} below minimum {definition.min_value}"
                    )

                if definition.max_value is not None and value > definition.max_value:
                    errors.append(
                        f"Feature {key} value {value} above maximum {definition.max_value}"
                    )

        return errors

    @staticmethod
    def sanitize_features(features: dict[str, Any]) -> dict[str, Any]:
        """
        清理和标准化特征数据。

        Args:
            features: 原始特征数据

        Returns:
            清理后的特征数据
        """
        sanitized = {}

        for key, definition in FEATURE_DEFINITIONS.items():
            if key in features:
                value = features[key]

                # 类型转换
                if definition.feature_type == FeatureType.NUMERICAL:
                    try:
                        value = float(value)
                    except (ValueError, typeError):
                        if definition.default_value is not None:
                            value = definition.default_value
                        else:
                            continue

                sanitized[key] = value
            elif definition.default_value is not None:
                sanitized[key] = definition.default_value

        return sanitized


def get_all_feature_keys() -> list[str]:
    """获取所有特征键列表。"""
    return list(FEATURE_DEFINITIONS.keys())


def get_required_feature_keys() -> list[str]:
    """获取所有必需特征键列表。"""
    return [
        key for key, definition in FEATURE_DEFINITIONS.items() if definition.required
    ]


def get_feature_definition(feature_key: str) -> Optional[FeatureDefinition]:
    """根据键获取特征定义。"""
    return FEATURE_DEFINITIONS.get(feature_key)


def validate_features_object(features_obj) -> list[str]:
    """
    验证特征对象的数据完整性。

    Args:
        features_obj: 特征对象 (RecentPerformanceFeatures, HeadToHeadFeatures, etc.)

    Returns:
        验证错误列表
    """
    if hasattr(features_obj, "validate"):
        return features_obj.validate()
    return []


@dataclass
class HistoricalMatchupFeatures:
    """历史对战特征数据结构."""

    total_matches: int = 0
    home_wins: int = 0
    away_wins: int = 0
    draws: int = 0
    home_win_rate: float = 0.0
    away_win_rate: float = 0.0
    draw_rate: float = 0.0
    avg_home_goals: float = 0.0
    avg_away_goals: float = 0.0
    total_goals: int = 0
    last_match_date: Optional[datetime] = None
    h2h_trend: str = ""  # recent form trend

    def validate(self) -> list[str]:
        """验证历史对战特征数据完整性。"""
        errors = []

        if self.total_matches < 0:
            errors.append("总比赛场次不能为负数")
        if self.home_wins < 0 or self.away_wins < 0 or self.draws < 0:
            errors.append("胜平负数据不能为负数")
        if self.total_matches != (self.home_wins + self.away_wins + self.draws):
            errors.append("胜平负数据与总场次不一致")
        if not (0 <= self.home_win_rate <= 1):
            errors.append("主队胜率必须在0-1之间")
        if not (0 <= self.away_win_rate <= 1):
            errors.append("客队胜率必须在0-1之间")
        if not (0 <= self.draw_rate <= 1):
            errors.append("平局率必须在0-1之间")

        return errors
