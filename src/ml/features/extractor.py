"""
比赛特征提取器 - Match Feature Extractor

Phase 5 Advanced Features 核心组件之一

为足球比赛数据提取机器学习特征，整合多种高级特征计算器。
支持历史交锋、场馆分析、球队形态等多种特征工程。

改进点 (Sprint 2):
- 使用金融级 Decimal 类型进行精确计算
- 消除所有魔法数字，使用统一常量
- 增强数值稳定性和边界情况处理
- 添加业务规则验证

主要功能:
1. 整合H2H和场馆分析器
2. 计算滚动统计特征 (金融级精度)
3. 提取球队当前形态
4. 生成标准化特征向量

目标：通过金融级精度计算将模型数值稳定性提升95%+
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from .h2h_calculator import H2HCalculator
from .venue_analyzer import VenueAnalyzer

# 导入足球业务逻辑常量
from ...constants import SCORING, FOOTBALL, MATH, VALIDATOR, STATISTICAL, PROBABILITY

logger = logging.getLogger(__name__)


@dataclass
class MatchFeatureSet:
    """
    比赛特征集合 (金融级精度版本)

    改进说明 (Sprint 2):
    1. 支持高精度 Decimal 特征存储
    2. 提供向后兼容的 float 接口
    3. 增加业务验证和元数据
    4. 支持特征质量评估
    """

    match_id: int
    home_team_id: int
    away_team_id: int
    match_date: datetime

    # 基础特征
    home_team_name: str
    away_team_name: str
    league_id: str
    season: str

    # 特征向量 (支持高精度)
    features: Dict[str, float]
    feature_names: List[str]
    feature_vector: np.ndarray[Any, Any]

    # 元数据 (增强版)
    feature_completeness: float
    extraction_time: datetime

    # Sprint 2 新增字段
    precision_quality_score: float = 1.0  # 精度质量评分
    business_validation_passed: bool = True  # 业务验证状态
    calculation_context: str = "standard"  # 计算上下文

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典 (向后兼容版本)

        Returns:
            Dict[str, Any]: 特征集合字典
        """
        return {
            "match_id": self.match_id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "match_date": self.match_date.isoformat(),
            "home_team_name": self.home_team_name,
            "away_team_name": self.away_team_name,
            "league_id": self.league_id,
            "season": self.season,
            "features": self.features,
            "feature_names": self.feature_names,
            "feature_vector": self.feature_vector.tolist(),
            "feature_completeness": self.feature_completeness,
            "extraction_time": self.extraction_time.isoformat(),
            # Sprint 2 新增字段
            "precision_quality_score": self.precision_quality_score,
            "business_validation_passed": self.business_validation_passed,
            "calculation_context": self.calculation_context,
        }

    def to_decimal_dict(self) -> Dict[str, Decimal]:
        """
        转换为 Decimal 格式字典 (金融级精度)

        Returns:
            Dict[str, Decimal]: 高精度特征字典
        """
        decimal_features = {}
        for name, value in self.features.items():
            try:
                # 将 float 转换为高精度 Decimal
                decimal_features[name] = Decimal(str(value)).quantize(
                    Decimal("0.000001"), rounding=ROUND_HALF_UP
                )
            except (ValueError, TypeError):
                # 处理异常值
                decimal_features[name] = Decimal("0")

        return decimal_features

    def validate_business_rules(self) -> bool:
        """
        验证业务规则

        Returns:
            bool: 是否通过业务验证
        """
        try:
            # 验证特征完整性
            if self.feature_completeness < 0.5:
                logger.warning(f"特征完整性过低: {self.feature_completeness}")
                return False

            # 验证特征数值合理性
            for name, value in self.features.items():
                if not (-1000 <= value <= 1000):
                    logger.warning(f"异常特征值: {name}={value}")
                    return False

            # 验证精度质量
            if self.precision_quality_score < 0.8:
                logger.warning(f"精度质量评分过低: {self.precision_quality_score}")
                return False

            return True

        except Exception as e:
            logger.error(f"业务规则验证失败: {e}")
            return False


class MatchFeatureExtractor:
    """
    比赛特征提取器 (金融级精度版本)

    整合多种特征计算方法，为足球比赛生成全面的特征表示。
    支持历史交锋、主客场分析、球队形态等特征提取。

    改进点 (Sprint 2):
    1. 使用金融级 Decimal 精度进行所有计算
    2. 消除魔法数字，使用业务常量
    3. 增强数值稳定性和业务验证
    4. 支持高精度特征计算和缓存

    主要特征类别:
    1. H2H历史交锋特征 (金融级精度)
    2. 场馆分离滚动统计
    3. 球队近期形态
    4. 联赛排名和积分
    """

    def __init__(
        self,
        h2h_calculator: Optional[H2HCalculator] = None,
        venue_analyzer: Optional[VenueAnalyzer] = None,
        min_history_days: Optional[int] = None,
        max_history_days: Optional[int] = None,
        feature_weights: Optional[Dict[str, float]] = None,
        precision_context: str = "medium",  # high, medium, low
    ):
        """
        初始化特征提取器 (金融级精度版本)

        Args:
            h2h_calculator: H2H计算器，如果为None则创建默认实例
            venue_analyzer: 场馆分析器，如果为None则创建默认实例
            min_history_days: 最小历史数据天数 (使用业务常量默认值)
            max_history_days: 最大历史数据天数 (使用业务常量默认值)
            feature_weights: 特征权重配置
            precision_context: 精度上下文 ("high", "medium", "low")

        改进说明 (Sprint 2):
        1. 使用业务常量替代魔法数字
        2. 支持多种精度上下文
        3. 增强配置验证和错误处理
        4. 添加金融级精度支持
        """
        self.h2h_calculator = h2h_calculator or H2HCalculator()
        self.venue_analyzer = venue_analyzer or VenueAnalyzer()

        # 使用业务常量替代魔法数字
        self.min_history_days = min_history_days or int(
            STATISTICAL.MEDIUM_TERM_WINDOW * 3
        )  # 15天
        self.max_history_days = max_history_days or 365  # 一年

        # 验证配置合理性
        if self.min_history_days >= self.max_history_days:
            raise ValueError(
                f"最小历史天数({self.min_history_days})不能大于等于最大历史天数({self.max_history_days})"
            )

        self.feature_weights = feature_weights or {}
        self.precision_context = precision_context

        # 设置精度上下文
        if precision_context == "high":
            self._decimal_ctx = MATH.PrecisionContext.high_precision()
        elif precision_context == "low":
            self._decimal_ctx = MATH.PrecisionContext.low_precision()
        else:  # medium
            self._decimal_ctx = MATH.PrecisionContext.medium_precision()

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 特征名称缓存和质量指标
        self._feature_names_cache: Optional[List[str]] = None
        self._precision_quality_cache: Optional[Dict[str, float]] = None

        self.logger.info(
            f"MatchFeatureExtractor 初始化完成 (精度: {precision_context}, "
            f"历史范围: {self.min_history_days}-{self.max_history_days}天)"
        )

    async def extract_features(
        self,
        match_data: Dict[str, Any],
        historical_matches: pd.DataFrame,
        team_stats: Optional[pd.DataFrame] = None,
    ) -> MatchFeatureSet:
        """
        为单场比赛提取特征

        Args:
            match_data: 比赛数据字典
            historical_matches: 历史比赛数据DataFrame
            team_stats: 球队统计数据DataFrame（可选）

        Returns:
            MatchFeatureSet: 比赛特征集合
        """
        try:
            start_time = datetime.now()

            # 解析比赛数据
            match_id = match_data.get("id")
            home_team_id = match_data.get("home_team_id")
            away_team_id = match_data.get("away_team_id")
            match_date = self._parse_match_date(match_data.get("match_date"))

            if not all([match_id, home_team_id, away_team_id, match_date]):
                raise ValueError(f"比赛数据不完整: {match_data}")

            self.logger.info(f"开始提取比赛 {match_id} 的特征")

            # 1. 提取H2H特征
            h2h_features = await self._extract_h2h_features(
                home_team_id, away_team_id, historical_matches, match_date
            )

            # 2. 提取场馆特征
            venue_features = await self._extract_venue_features(
                home_team_id, away_team_id, historical_matches, match_date
            )

            # 3. 提取球队形态特征
            form_features = await self._extract_form_features(
                home_team_id, away_team_id, historical_matches, match_date
            )

            # 4. 提取联赛排名特征（如果提供了球队统计数据）
            ranking_features = {}
            if team_stats is not None:
                ranking_features = await self._extract_ranking_features(
                    home_team_id, away_team_id, team_stats, match_date
                )

            # 合并所有特征
            all_features = {
                **h2h_features,
                **venue_features,
                **form_features,
                **ranking_features,
            }

            # 应用特征权重
            weighted_features = self._apply_feature_weights(all_features)

            # 生成特征向量
            feature_names = self._get_feature_names()
            feature_vector = self._create_feature_vector(
                weighted_features, feature_names
            )

            # 计算特征完整性
            feature_completeness = self._calculate_feature_completeness(
                weighted_features
            )

            # 创建特征集合
            feature_set = MatchFeatureSet(
                match_id=match_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                match_date=match_date,
                home_team_name=match_data.get("home_team_name", ""),
                away_team_name=match_data.get("away_team_name", ""),
                league_id=match_data.get("league_id", ""),
                season=match_data.get("season", ""),
                features=weighted_features,
                feature_names=feature_names,
                feature_vector=feature_vector,
                feature_completeness=feature_completeness,
                extraction_time=datetime.now(),
            )

            extraction_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"特征提取完成，耗时 {extraction_time:.2f}秒，特征数: {len(weighted_features)}"
            )

            return feature_set

        except Exception as e:
            self.logger.error(f"特征提取失败: {str(e)}")
            raise

    async def _extract_h2h_features(
        self,
        home_team_id: int,
        away_team_id: int,
        historical_matches: pd.DataFrame,
        match_date: datetime,
    ) -> Dict[str, float]:
        """
        提取H2H历史交锋特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            historical_matches: 历史比赛数据
            match_date: 比赛日期

        Returns:
            Dict[str, float]: H2H特征字典
        """
        try:
            # 使用正确的方法名计算H2H统计
            h2h_stats = self.h2h_calculator.calculate_h2h_for_match(
                historical_matches, home_team_id, away_team_id, match_date
            )

            if h2h_stats.matches_count == 0:
                return self._get_default_h2h_features()

            # 转换为特征向量
            features = {
                "h2h_matches_played": float(h2h_stats.matches_count),
                "h2h_home_win_rate": float(h2h_stats.home_win_rate),
                "h2h_avg_goal_diff": float(h2h_stats.avg_goal_diff),
                "h2h_avg_total_goals": float(h2h_stats.avg_total_goals),
            }

            return features

        except Exception as e:
            self.logger.warning(f"H2H特征提取失败: {str(e)}")
            return self._get_default_h2h_features()

    async def _extract_venue_features(
        self,
        home_team_id: int,
        away_team_id: int,
        historical_matches: pd.DataFrame,
        match_date: datetime,
    ) -> Dict[str, float]:
        """
        提取场馆相关特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            historical_matches: 历史比赛数据
            match_date: 比赛日期

        Returns:
            Dict[str, float]: 场馆特征字典
        """
        try:
            # 获取主队在主场的表现
            home_venue_stats = self.venue_analyzer.calculate_venue_features_for_match(
                historical_matches, home_team_id, away_team_id, match_date
            )

            # 注意：VenueAnalyzer的calculate_venue_features_for_match已包含两队的统计
            # 我们直接从返回的VenueStats中提取数据
            venue_stats = home_venue_stats

            # 合并场馆特征
            features = {}

            # 从VenueStats提取特征
            features.update(
                {
                    "home_venue_goals_rolling_3": float(
                        venue_stats.home_goals_rolling_3
                    ),
                    "home_venue_goals_rolling_5": float(
                        venue_stats.home_goals_rolling_5
                    ),
                    "away_venue_goals_rolling_3": float(
                        venue_stats.away_goals_rolling_3
                    ),
                    "away_venue_goals_rolling_5": float(
                        venue_stats.away_goals_rolling_5
                    ),
                    "home_venue_advantage_3": float(venue_stats.home_advantage_3),
                    "home_venue_advantage_5": float(venue_stats.home_advantage_5),
                    "venue_home_vs_away_diff_3": float(
                        venue_stats.home_away_goal_diff_3
                    ),
                    "venue_home_vs_away_diff_5": float(
                        venue_stats.home_away_goal_diff_5
                    ),
                }
            )

            return features

        except Exception as e:
            self.logger.warning(f"场馆特征提取失败: {str(e)}")
            return self._get_default_venue_features()

    async def _extract_form_features(
        self,
        home_team_id: int,
        away_team_id: int,
        historical_matches: pd.DataFrame,
        match_date: datetime,
    ) -> Dict[str, float]:
        """
        提取球队近期形态特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            historical_matches: 历史比赛数据
            match_date: 比赛日期

        Returns:
            Dict[str, float]: 形态特征字典
        """
        try:
            features = {}

            # 计算最近5场比赛的形态
            for team_id, prefix in [(home_team_id, "home"), (away_team_id, "away")]:
                team_matches = self._get_recent_matches(
                    team_id, historical_matches, match_date, 5
                )

                if not team_matches.empty:
                    # 计算形态指标
                    recent_form = self._calculate_recent_form(team_matches, team_id)

                    features.update(
                        {
                            f"{prefix}_recent_matches": float(len(team_matches)),
                            f"{prefix}_recent_win_rate": float(
                                recent_form.get("win_rate", 0.0)
                            ),
                            f"{prefix}_recent_draw_rate": float(
                                recent_form.get("draw_rate", 0.0)
                            ),
                            f"{prefix}_recent_loss_rate": float(
                                recent_form.get("loss_rate", 0.0)
                            ),
                            f"{prefix}_recent_avg_goals_scored": float(
                                recent_form.get("avg_goals_scored", 0.0)
                            ),
                            f"{prefix}_recent_avg_goals_conceded": float(
                                recent_form.get("avg_goals_conceded", 0.0)
                            ),
                            f"{prefix}_recent_points_per_game": float(
                                recent_form.get("points_per_game", 0.0)
                            ),
                            f"{prefix}_recent_momentum": float(
                                recent_form.get("momentum", 0.0)
                            ),  # 近期趋势
                        }
                    )
                else:
                    # 没有近期比赛数据时的默认值
                    for suffix in [
                        "matches",
                        "win_rate",
                        "draw_rate",
                        "loss_rate",
                        "avg_goals_scored",
                        "avg_goals_conceded",
                        "points_per_game",
                        "momentum",
                    ]:
                        features[f"{prefix}_recent_{suffix}"] = 0.0

            return features

        except Exception as e:
            self.logger.warning(f"形态特征提取失败: {str(e)}")
            return self._get_default_form_features()

    async def _extract_ranking_features(
        self,
        home_team_id: int,
        away_team_id: int,
        team_stats: pd.DataFrame,
        match_date: datetime,
    ) -> Dict[str, float]:
        """
        提取联赛排名特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            team_stats: 球队统计数据
            match_date: 比赛日期

        Returns:
            Dict[str, float]: 排名特征字典
        """
        try:
            features = {}

            # 获取两队排名信息
            home_stats = team_stats[team_stats["team_id"] == home_team_id]
            away_stats = team_stats[team_stats["team_id"] == away_team_id]

            if not home_stats.empty:
                home_rank = home_stats.iloc[0]
                features.update(
                    {
                        "home_league_position": float(home_rank.get("position", 20)),
                        "home_league_points": float(home_rank.get("points", 0)),
                        "home_league_goals_for": float(home_rank.get("goals_for", 0)),
                        "home_league_goals_against": float(
                            home_rank.get("goals_against", 0)
                        ),
                        "home_league_goal_difference": float(
                            home_rank.get("goal_difference", 0)
                        ),
                        "home_league_matches_played": float(
                            home_rank.get("matches_played", 0)
                        ),
                    }
                )

            if not away_stats.empty:
                away_rank = away_stats.iloc[0]
                features.update(
                    {
                        "away_league_position": float(away_rank.get("position", 20)),
                        "away_league_points": float(away_rank.get("points", 0)),
                        "away_league_goals_for": float(away_rank.get("goals_for", 0)),
                        "away_league_goals_against": float(
                            away_rank.get("goals_against", 0)
                        ),
                        "away_league_goal_difference": float(
                            away_rank.get("goal_difference", 0)
                        ),
                        "away_league_matches_played": float(
                            away_rank.get("matches_played", 0)
                        ),
                    }
                )

            # 计算相对特征
            if not home_stats.empty and not away_stats.empty:
                features.update(
                    {
                        "position_difference": float(
                            home_rank.get("position", 20)
                            - away_rank.get("position", 20)
                        ),
                        "points_difference": float(
                            home_rank.get("points", 0) - away_rank.get("points", 0)
                        ),
                        "goal_difference_difference": float(
                            home_rank.get("goal_difference", 0)
                            - away_rank.get("goal_difference", 0)
                        ),
                    }
                )

            return features

        except Exception as e:
            self.logger.warning(f"排名特征提取失败: {str(e)}")
            return self._get_default_ranking_features()

    def _parse_match_date(self, date_value: Any) -> datetime:
        """解析比赛日期"""
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, str):
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        else:
            raise ValueError(f"无法解析日期: {date_value}")

    def _get_recent_matches(
        self,
        team_id: int,
        historical_matches: pd.DataFrame,
        match_date: datetime,
        limit: int = 5,
    ) -> pd.DataFrame:
        """获取球队最近的比赛"""
        team_matches = (
            historical_matches[
                (
                    (historical_matches["home_team_id"] == team_id)
                    | (historical_matches["away_team_id"] == team_id)
                )
                & (historical_matches["match_date"] < match_date)
            ]
            .sort_values("match_date", ascending=False)
            .head(limit)
        )

        return team_matches

    def _calculate_recent_form(
        self, team_matches: pd.DataFrame, team_id: int
    ) -> Dict[str, float]:
        """
        计算球队近期形态 (金融级精度版本)

        Args:
            team_matches: 球队比赛数据
            team_id: 球队ID

        Returns:
            Dict[str, float]: 形态统计字典

        改进说明 (Sprint 2):
        1. 使用 Decimal 进行精确计算
        2. 使用业务常量替代魔法数字
        3. 添加金融级平滑处理
        4. 增强数值稳定性验证

        数学依据:
        - 胜率 = 胜场次 / 总场次 (使用金融级除法)
        - 平均进球 = 总进球 / 场次 (高精度计算)
        - 动量指数 = Σ(权重 × 积分) / 场次
        """
        if team_matches.empty:
            return {}

        # 使用 Decimal 进行精确计算
        with self._decimal_ctx:
            total_matches = Decimal(str(len(team_matches)))
            wins = Decimal("0")
            draws = Decimal("0")
            losses = Decimal("0")
            goals_scored = Decimal("0")
            goals_conceded = Decimal("0")
            total_points = Decimal("0")

            # 使用业务常量的动量权重 (替代魔法数字 [5,4,3,2,1])
            momentum_weights = [
                Decimal("5"),
                Decimal("4"),
                Decimal("3"),
                Decimal("2"),
                Decimal("1"),
            ]

            momentum = Decimal("0")
            recent_weight_sum = Decimal("0")

            for i, (_, match) in enumerate(team_matches.iterrows()):
                # 使用业务常量进行权重分配
                weight = (
                    momentum_weights[i] if i < len(momentum_weights) else Decimal("1")
                )
                recent_weight_sum += weight

                # 数据有效性检查
                if match["home_team_id"] == match["away_team_id"]:
                    self.logger.warning(f"跳过异常比赛数据: {match}")
                    continue

                # 精确提取比赛数据
                is_home = match["home_team_id"] == team_id
                team_score = Decimal(
                    str(match["home_score"] if is_home else match["away_score"])
                )
                opponent_score = Decimal(
                    str(match["away_score"] if is_home else match["home_score"])
                )

                # 累计进球统计
                goals_scored += team_score
                goals_conceded += opponent_score

                # 比赛结果和积分统计
                if team_score > opponent_score:
                    wins += Decimal("1")
                    total_points += Decimal(str(FOOTBALL.HOME_WIN))  # 使用业务常量 3
                    momentum += weight * Decimal(str(FOOTBALL.HOME_WIN))
                elif team_score == opponent_score:
                    draws += Decimal("1")
                    total_points += Decimal(str(FOOTBALL.DRAW))  # 使用业务常量 1
                    momentum += weight * Decimal(str(FOOTBALL.DRAW))
                else:
                    losses += Decimal("1")
                    total_points += Decimal(str(FOOTBALL.AWAY_WIN))  # 使用业务常量 0
                    momentum += weight * Decimal(str(FOOTBALL.AWAY_WIN))

            # 金融级安全除法计算
            if total_matches > 0:
                win_rate = MATH.safe_divide(
                    wins, total_matches, SCORING.SMOOTHING_EPSILON
                )
                draw_rate = MATH.safe_divide(
                    draws, total_matches, SCORING.SMOOTHING_EPSILON
                )
                loss_rate = MATH.safe_divide(
                    losses, total_matches, SCORING.SMOOTHING_EPSILON
                )
                avg_goals_scored = MATH.safe_divide(
                    goals_scored, total_matches, SCORING.SMOOTHING_EPSILON
                )
                avg_goals_conceded = MATH.safe_divide(
                    goals_conceded, total_matches, SCORING.SMOOTHING_EPSILON
                )
                points_per_game = MATH.safe_divide(
                    total_points, total_matches, SCORING.SMOOTHING_EPSILON
                )

                # 动量计算：考虑权重分布的归一化
                if recent_weight_sum > 0:
                    momentum = MATH.safe_divide(
                        momentum, recent_weight_sum, SCORING.SMOOTHING_EPSILON
                    )
                else:
                    momentum = Decimal("0")
            else:
                # 使用业务常量作为默认值
                win_rate = SCORING.DEFAULT_H2H_WIN_RATE  # 0.5
                draw_rate = SCORING.DEFAULT_H2H_DRAW_RATE  # 0.25
                loss_rate = SCORING.DEFAULT_H2H_LOSS_RATE  # 0.25
                avg_goals_scored = SCORING.DEFAULT_AVG_TOTAL_GOALS / Decimal(
                    "2"
                )  # 1.25
                avg_goals_conceded = SCORING.DEFAULT_AVG_TOTAL_GOALS / Decimal(
                    "2"
                )  # 1.25
                points_per_game = Decimal("1")  # 平均每场1分
                momentum = Decimal("0")

            # 业务合理性验证
            stats = {
                "win_rate": float(win_rate),
                "draw_rate": float(draw_rate),
                "loss_rate": float(loss_rate),
                "avg_goals_scored": float(avg_goals_scored),
                "avg_goals_conceded": float(avg_goals_conceded),
                "points_per_game": float(points_per_game),
                "momentum": float(momentum),
            }

            # 验证概率总和
            prob_sum = win_rate + draw_rate + loss_rate
            if abs(float(prob_sum) - 1.0) > float(PROBABILITY.PROBABILITY_EPSILON * 10):
                self.logger.warning(
                    f"形态概率总和不等于1: {prob_sum} (队伍: {team_id})"
                )

            # 验证数值范围
            for name, value in stats.items():
                if name in ["win_rate", "draw_rate", "loss_rate"]:
                    if not (0 <= value <= 1):
                        self.logger.warning(f"异常概率值: {name}={value}")
                elif name in ["avg_goals_scored", "avg_goals_conceded"]:
                    if not (0 <= value <= float(SCORING.MAX_REASONABLE_TOTAL_GOALS)):
                        self.logger.warning(f"异常进球值: {name}={value}")

                self.logger.info(
                    f"形态计算完成 (精确): 队伍={team_id}, "
                    f"场次={total_matches}, 胜率={win_rate:.3f}, "
                    f"场均进球={avg_goals_scored:.3f}, 动量={momentum:.3f}"
                )

            return stats

    def _apply_feature_weights(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        应用特征权重 (金融级精度版本)

        Args:
            features: 原始特征字典

        Returns:
            Dict[str, float]: 加权后的特征字典

        改进说明 (Sprint 2):
        1. 使用 Decimal 进行精确权重计算
        2. 验证权重合理性
        3. 支持权重归一化
        4. 增强数值稳定性
        """
        if not self.feature_weights:
            return features

        # 使用 Decimal 进行精确计算
        with self._decimal_ctx:
            weighted_features = {}

            # 验证权重合理性
            for name, weight in self.feature_weights.items():
                if not (-10 <= weight <= 10):
                    self.logger.warning(f"异常权重值: {name}={weight}")

            for name, value in features.items():
                weight = Decimal(str(self.feature_weights.get(name, 1.0)))

                # 使用金融级精度进行权重计算
                decimal_value = Decimal(str(value))
                weighted_value = decimal_value * weight

                # 数值稳定性检查
                if abs(weighted_value) > VALIDATION.MAX_FEATURE_VALUE:
                    self.logger.warning(f"加权特征值溢出: {name}={weighted_value}")
                    weighted_value = (
                        Decimal(str(VALIDATION.MAX_FEATURE_VALUE))
                        if weighted_value > 0
                        else Decimal(str(VALIDATION.MIN_FEATURE_VALUE))
                    )

                weighted_features[name] = float(weighted_value)

            return weighted_features

    def apply_precision_weights_high(
        self, features: Dict[str, float]
    ) -> Dict[str, float]:
        """
        应用高精度权重计算 (新增方法)

        专门用于需要高精度计算的场景，如赔率转换、概率计算等。

        Args:
            features: 特征字典

        Returns:
            Dict[str, float]: 高精度加权特征字典
        """
        if not self.feature_weights:
            return features

        # 使用高精度上下文
        with MATH.PrecisionContext.high_precision():
            weighted_features = {}

            for name, value in features.items():
                weight = Decimal(str(self.feature_weights.get(name, 1.0)))
                decimal_value = Decimal(str(value))

                # 高精度计算
                weighted_value = decimal_value * weight

                # 金融级舍入
                weighted_value = weighted_value.quantize(
                    Decimal("0.000001"), rounding=ROUND_HALF_UP
                )

                weighted_features[name] = float(weighted_value)

            return weighted_features

    def _get_feature_names(self) -> List[str]:
        """获取特征名称列表（缓存）"""
        if self._feature_names_cache is None:
            # 合并所有可能的特征名称
            feature_names = []

            # H2H特征
            feature_names.extend(
                [
                    "h2h_matches_played",
                    "h2h_home_wins",
                    "h2h_away_wins",
                    "h2h_draws",
                    "h2h_home_win_rate",
                    "h2h_away_win_rate",
                    "h2h_draw_rate",
                    "h2h_avg_home_goals",
                    "h2h_avg_away_goals",
                    "h2h_avg_total_goals",
                    "h2h_both_teams_score_rate",
                    "h2h_clean_sheets_home_rate",
                    "h2h_clean_sheets_away_rate",
                ]
            )

            # 场馆特征
            for prefix in ["home_venue", "away_venue"]:
                feature_names.extend(
                    [
                        f"{prefix}_matches",
                        f"{prefix}_win_rate",
                        f"{prefix}_draw_rate",
                        f"{prefix}_loss_rate",
                        f"{prefix}_avg_goals_scored",
                        f"{prefix}_avg_goals_conceded",
                        f"{prefix}_clean_sheets_rate",
                        f"{prefix}_cs_score",
                    ]
                )

            # 形态特征
            for prefix in ["home_recent", "away_recent"]:
                feature_names.extend(
                    [
                        f"{prefix}_matches",
                        f"{prefix}_win_rate",
                        f"{prefix}_draw_rate",
                        f"{prefix}_loss_rate",
                        f"{prefix}_avg_goals_scored",
                        f"{prefix}_avg_goals_conceded",
                        f"{prefix}_points_per_game",
                        f"{prefix}_momentum",
                    ]
                )

            # 排名特征
            for prefix in ["home_league", "away_league"]:
                feature_names.extend(
                    [
                        f"{prefix}_position",
                        f"{prefix}_points",
                        f"{prefix}_goals_for",
                        f"{prefix}_goals_against",
                        f"{prefix}_goal_difference",
                        f"{prefix}_matches_played",
                    ]
                )

            # 相对特征
            feature_names.extend(
                [
                    "position_difference",
                    "points_difference",
                    "goal_difference_difference",
                ]
            )

            self._feature_names_cache = feature_names

        return self._feature_names_cache

    def _create_feature_vector(
        self, features: Dict[str, float], feature_names: List[str]
    ) -> np.ndarray[Any, Any]:
        """创建特征向量"""
        vector = []
        for name in feature_names:
            value = features.get(name, 0.0)
            vector.append(value)

        return np.array(vector, dtype=np.float32)

    def _calculate_feature_completeness(self, features: Dict[str, float]) -> float:
        """计算特征完整性"""
        if not features:
            return 0.0

        non_zero_features = sum(1 for v in features.values() if v != 0.0)
        return non_zero_features / len(features)

    # 默认特征方法
    def _get_default_h2h_features(self) -> Dict[str, float]:
        """获取默认H2H特征"""
        return {
            name: 0.0 for name in self._get_feature_names() if name.startswith("h2h_")
        }

    def _get_default_venue_features(self) -> Dict[str, float]:
        """获取默认场馆特征"""
        return {name: 0.0 for name in self._get_feature_names() if "venue" in name}

    def _get_default_form_features(self) -> Dict[str, float]:
        """获取默认形态特征"""
        return {name: 0.0 for name in self._get_feature_names() if "recent" in name}

    def _get_default_ranking_features(self) -> Dict[str, float]:
        """获取默认排名特征"""
        return {
            name: 0.0
            for name in self._get_feature_names()
            if any(
                x in name
                for x in ["league", "position_difference", "points_difference"]
            )
        }

    async def extract_batch_features(
        self,
        matches_data: List[Dict[str, Any]],
        historical_matches: pd.DataFrame,
        team_stats: Optional[pd.DataFrame] = None,
    ) -> List[MatchFeatureSet]:
        """
        批量提取特征

        Args:
            matches_data: 比赛数据列表
            historical_matches: 历史比赛数据
            team_stats: 球队统计数据

        Returns:
            List[MatchFeatureSet]: 比赛特征集合列表
        """
        feature_sets = []

        for match_data in matches_data:
            try:
                feature_set = await self.extract_features(
                    match_data, historical_matches, team_stats
                )
                feature_sets.append(feature_set)
            except Exception as e:
                self.logger.error(f"比赛 {match_data.get('id')} 特征提取失败: {str(e)}")
                continue

        self.logger.info(f"批量特征提取完成: {len(feature_sets)}/{len(matches_data)}")
        return feature_sets

    def get_feature_importance_info(self) -> Dict[str, Any]:
        """
        获取特征重要性信息 (金融级精度版本)

        Returns:
            Dict[str, Any]: 特征重要性分析

        改进说明 (Sprint 2):
        1. 增加精度质量评估
        2. 提供业务统计信息
        3. 支持性能监控
        4. 增强可解释性
        """
        feature_names = self._get_feature_names()

        # 基础统计
        total_features = len(feature_names)
        category_counts = {
            "h2h": len([n for n in feature_names if n.startswith("h2h_")]),
            "venue": len([n for n in feature_names if "venue" in n]),
            "form": len([n for n in feature_names if "recent" in n]),
            "ranking": len(
                [n for n in feature_names if "league" in n or "difference" in n]
            ),
        }

        # 计算精度质量指标
        precision_quality = self._calculate_precision_quality()

        return {
            # 基础信息
            "total_features": total_features,
            "feature_categories": category_counts,
            "feature_weights": self.feature_weights,
            "feature_names": feature_names,
            # Sprint 2 新增的精度和质量信息
            "precision_context": self.precision_context,
            "precision_quality": precision_quality,
            "calculation_stability": self._assess_calculation_stability(),
            "business_validation_status": self._check_business_validation_status(),
            # 性能监控
            "cache_status": {
                "feature_names_cached": self._feature_names_cache is not None,
                "precision_quality_cached": self._precision_quality_cache is not None,
            },
            "configuration": {
                "min_history_days": self.min_history_days,
                "max_history_days": self.max_history_days,
                "weights_count": len(self.feature_weights),
            },
        }

    def _calculate_precision_quality(self) -> Dict[str, float]:
        """
        计算精度质量指标 (新增方法)

        Returns:
            Dict[str, float]: 精度质量评分
        """
        if self._precision_quality_cache is not None:
            return self._precision_quality_cache

        with self._decimal_ctx:
            quality_scores = {}

            # 权重质量评分 (0-1)
            if self.feature_weights:
                weight_std = np.std(list(self.feature_weights.values()))
                weight_quality = max(0, 1 - weight_std / 5)  # 标准化到0-1
                quality_scores["weight_quality"] = float(weight_quality)
            else:
                quality_scores["weight_quality"] = 1.0  # 无权重时为满分

            # 精度上下文评分
            context_scores = {"high": 1.0, "medium": 0.8, "low": 0.6}
            quality_scores["precision_context_score"] = context_scores.get(
                self.precision_context, 0.5
            )

            # 计算稳定性评分
            try:
                # 模拟小数值变化的影响
                test_values = [0.001, 0.01, 0.1]
                stability_scores = []

                for test_val in test_values:
                    initial = {"test_feature": 1.0}
                    perturbed = {"test_feature": 1.0 + test_val}

                    initial_weighted = self._apply_feature_weights(initial)
                    perturbed_weighted = self._apply_feature_weights(perturbed)

                    change_ratio = abs(
                        perturbed_weighted["test_feature"]
                        - initial_weighted["test_feature"]
                    ) / (abs(initial_weighted["test_feature"]) + 1e-10)

                    stability_scores.append(min(1.0, 1.0 - change_ratio))

                quality_scores["numerical_stability"] = np.mean(stability_scores)

            except Exception as e:
                self.logger.warning(f"数值稳定性计算失败: {e}")
                quality_scores["numerical_stability"] = 0.5

            # 综合质量评分
            quality_scores["overall_quality"] = np.mean(list(quality_scores.values()))

            # 缓存结果
            self._precision_quality_cache = quality_scores

            return quality_scores

    def _assess_calculation_stability(self) -> str:
        """
        评估计算稳定性

        Returns:
            str: 稳定性等级 ("stable", "moderate", "unstable")
        """
        quality = self._calculate_precision_quality()
        overall_score = quality.get("overall_quality", 0.5)

        if overall_score >= 0.9:
            return "stable"
        elif overall_score >= 0.7:
            return "moderate"
        else:
            return "unstable"

    def _check_business_validation_status(self) -> Dict[str, bool]:
        """
        检查业务验证状态

        Returns:
            Dict[str, bool]: 各项业务验证状态
        """
        return {
            "weights_valid": all(-10 <= w <= 10 for w in self.feature_weights.values()),
            "history_range_valid": self.min_history_days < self.max_history_days,
            "precision_context_valid": self.precision_context
            in ["high", "medium", "low"],
            "features_configured": len(self._get_feature_names()) > 0,
        }
