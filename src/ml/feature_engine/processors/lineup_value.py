"""
LineupValueProcessor - 阵容价值处理器（V23.0 全量平铺版）
==========================================================

负责提取高级阵容价值特征，包括:
    - 球队阵容总价值（首发 11 人身价加总）
    - 身价倍率差（两队身价比）
    - 首发平均年龄（研究老龄球队体能极限）
    - 年龄结构分布（U23、黄金期、老将比例）
    - 身价效率比（身价 vs 预期进球）
    - **V23.0 新增**: 球员级别特征全平铺（11人 × 10维 × 2队 = 220维）

设计模式:
    - 深度解析: 从 FotMob content.lineup 提取球员身价
    - 维度爆破: 单个处理器输出 270+ 维特征
    - 财务建模: 引入足球经济学建模
    - 原子化展开: 每一名首发球员的战术指纹独立平铺

作者: FootballPrediction Architecture Team
版本: V23.0-final
"""

import logging
from dataclasses import dataclass
from typing import Any

from ..base import BaseProcessor, ProcessorConfig, ProcessorResult
from ..models import LineupInfo, MatchData, PlayerStats

logger = logging.getLogger(__name__)


@dataclass
class LineupValueProcessorConfig(ProcessorConfig):
    """
    LineupValueProcessor 配置

    Attributes:
        enable_market_value: 是否启用身价分析
        enable_age_analysis: 是否启用年龄结构分析
        enable_efficiency_ratio: 是否计算身价效率比
        enable_player_flattening: 是否启用球员特征平铺（V23.0）
        default_age: 缺失年龄的默认值（-1 表示未知）
        value_currency_unit: 身价单位（百万欧元）
        u23_threshold: U23 球员年龄阈值
        veteran_threshold: 老将年龄阈值
        player_feature_count: 每个球员的特征维度数
    """

    enable_market_value: bool = True
    enable_age_analysis: bool = True
    enable_efficiency_ratio: bool = True
    enable_player_flattening: bool = True  # V23.0 新增
    default_age: float = -1.0
    value_currency_unit: str = "M_EUR"  # 百万欧元
    u23_threshold: int = 23
    veteran_threshold: int = 30
    player_feature_count: int = 10  # 每个球员 10 个核心维度


class LineupValueProcessor(BaseProcessor[MatchData]):
    """
    阵容价值处理器（V23.0 全量平铺版）

    职责:
        1. 深度解析首发阵容身价数据
        2. 计算身价倍率差和相对优势
        3. 分析年龄结构对体能的影响
        4. 计算身价效率比（投入产出分析）
        5. **V23.0**: 球员级别特征全平铺（11人独立展开）

    特征输出（270+ 维）:
        # 传统聚合维度
        - home_squad_value, away_squad_value: 首发总身价
        - value_gap_ratio: 两队身价倍率差
        - home_age_average, away_age_average: 首发平均年龄
        ... (约 50 维聚合特征)

        # V23.0 球员平铺维度（220 维）
        - home_p1_rating, home_p1_market_value, home_p1_age, ...
        - home_p2_rating, home_p2_market_value, home_p2_age, ...
        ...
        - home_p11_rating, home_p11_market_value, home_p11_age, ...
        - away_p1_rating, away_p1_market_value, away_p1_age, ...
        ...
        - away_p11_rating, away_p11_market_value, away_p11_age, ...

        每个球员的 10 个核心维度:
            1. rating: 球员评分
            2. market_value: 市场身价（百万欧元）
            3. age: 年龄
            4. minutes_played: 出场时间
            5. expected_goals: 预期进球
            6. total_shots: 总射门数
            7. touches: 触球数
            8. accurate_passes: 成功传球数
            9. key_passes: 关键传球
            10. big_chances_created: 创造机会数

    Example:
        >>> processor = LineupValueProcessor()
        >>> result = processor.execute(match_data)
        >>> print(f"主队第5号球员身价: {result.data['home_p5_market_value']}")
        >>> print(f"主队第5号球员评分: {result.data['home_p5_rating']}")
    """

    processor_name = "LineupValueProcessor"
    processor_version = "23.0.0"
    priority = 35  # 在 LineupProcessor 之后执行

    # 球员特征字段定义（10 个核心维度）
    PLAYER_FEATURE_FIELDS = [
        "team_rating",  # 球员评分
        "market_value",  # 市场身价
        "age",  # 年龄
        "minutes_played",  # 出场时间
        "expected_goals",  # 预期进球
        "total_shots",  # 总射门数
        "touches",  # 触球数
        "accurate_passes",  # 成功传球数
        "key_passes",  # 关键传球
        "big_chances_created",  # 创造机会数
    ]

    def __init__(self, config: LineupValueProcessorConfig | None = None) -> None:
        super().__init__(config or LineupValueProcessorConfig())
        self.config: LineupValueProcessorConfig = self.config

    def process(self, data: MatchData, context: Any) -> ProcessorResult:
        """
        提取阵容价值特征

        Args:
            data: 比赛数据
            context: 处理上下文

        Returns:
            ProcessorResult: 包含阵容价值特征的处理器结果
        """
        features: dict[str, float] = {}

        try:
            # 1. 传统聚合特征（保留向后兼容）
            agg_features = self._extract_aggregate_features(data)
            features.update(agg_features)

            # 2. V23.0: 球员级别特征全平铺
            if self.config.enable_player_flattening:
                # 主队球员平铺
                if data.home_lineup and data.home_lineup.players:
                    home_player_features = self._flatten_player_features(data.home_lineup.players, "home")
                    features.update(home_player_features)

                # 客队球员平铺
                if data.away_lineup and data.away_lineup.players:
                    away_player_features = self._flatten_player_features(data.away_lineup.players, "away")
                    features.update(away_player_features)

            # 3. 计算对比特征
            comparison_features = self._compute_comparison_features(features)
            features.update(comparison_features)

            # 4. V23.0: 球员级别交叉特征
            if self.config.enable_player_flattening:
                cross_features = self._compute_player_cross_features(features)
                features.update(cross_features)

            return ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "value_analysis_enabled": self.config.enable_market_value,
                    "age_analysis_enabled": self.config.enable_age_analysis,
                    "player_flattening_enabled": self.config.enable_player_flattening,
                },
            )

        except Exception as e:
            logger.error(f"LineupValueProcessor failed for match {data.match_id}: {e}")
            return ProcessorResult.failure_result(str(e))

    def _extract_aggregate_features(self, data: MatchData) -> dict[str, float]:
        """提取传统聚合特征（向后兼容）"""
        features = {}

        # 主队阵容价值分析
        if data.home_lineup and data.home_lineup.players:
            home_features = self._analyze_team_value(data.home_lineup, "home", data.home_stats)
            features.update(home_features)
        else:
            features.update(self._get_default_features("home"))

        # 客队阵容价值分析
        if data.away_lineup and data.away_lineup.players:
            away_features = self._analyze_team_value(data.away_lineup, "away", data.away_stats)
            features.update(away_features)
        else:
            features.update(self._get_default_features("away"))

        return features

    def _analyze_team_value(self, lineup: LineupInfo, prefix: str, team_stats: Any) -> dict[str, float]:
        """
        分析单队阵容价值特征（聚合维度）

        Args:
            lineup: 球队阵容信息
            prefix: 特征前缀（home 或 away）
            team_stats: 球队统计数据（用于计算效率比）

        Returns:
            阵容价值特征字典
        """
        features = {}

        # 提取首发球员
        starters = [p for p in lineup.players if p.is_starter is True]

        if not starters:
            return self._get_default_features(prefix)

        # ========== 身价维度 ==========
        if self.config.enable_market_value:
            squad_value = self._calculate_squad_value(starters)
            features[f"{prefix}_squad_value"] = squad_value
            features[f"{prefix}_avg_player_value"] = round(squad_value / len(starters), 2) if len(starters) > 0 else 0.0

        # ========== 年龄维度 ==========
        if self.config.enable_age_analysis:
            age_features = self._analyze_age_structure(starters, prefix)
            features.update(age_features)

        # ========== 效率维度 ==========
        if self.config.enable_efficiency_ratio and team_stats:
            squad_value = features.get(f"{prefix}_squad_value", 0.0)
            efficiency = self._calculate_value_efficiency(squad_value, team_stats)
            features[f"{prefix}_value_efficiency"] = efficiency

        return features

    def _flatten_player_features(self, players: list[PlayerStats], prefix: str) -> dict[str, float]:
        """
        平铺球员级别特征（V23.0 核心爆破）

        为首发 11 人（按 jersey_number 排序）创建独立特征位

        Args:
            players: 球员列表
            prefix: 特征前缀（home 或 away）

        Returns:
            平铺后的球员特征字典（11 人 × 10 维 = 110 维）
        """
        features = {}

        # 提取首发球员并按球衣号码排序（保持位置一致性）
        starters = [p for p in players if p.is_starter is True]
        starters.sort(key=lambda p: p.jersey_number or 999)

        # 限制为前 11 人
        starters = starters[:11]

        # 为每个位置（1-11）平铺特征
        for position_idx, player in enumerate(starters, start=1):
            p_num = position_idx  # p1, p2, ... p11

            # 跳过不存在的位置（填充默认值）
            if position_idx > len(starters):
                # 填充默认值
                for field in self.PLAYER_FEATURE_FIELDS:
                    features[f"{prefix}_p{p_num}_{field}"] = 0.0
                continue

            # 提取球员的 10 个核心维度
            features[f"{prefix}_p{p_num}_team_rating"] = float(player.team_rating or 0.0)
            features[f"{prefix}_p{p_num}_market_value"] = float(player.market_value or 0.0)
            features[f"{prefix}_p{p_num}_age"] = float(player.age or self.config.default_age)
            features[f"{prefix}_p{p_num}_minutes_played"] = float(player.minutes_played or 0)
            features[f"{prefix}_p{p_num}_expected_goals"] = float(player.expected_goals or 0.0)
            features[f"{prefix}_p{p_num}_total_shots"] = float(player.total_shots or 0)
            features[f"{prefix}_p{p_num}_touches"] = float(player.touches or 0)
            features[f"{prefix}_p{p_num}_accurate_passes"] = float(player.accurate_passes or 0)
            features[f"{prefix}_p{p_num}_key_passes"] = float(player.key_passes or 0)
            features[f"{prefix}_p{p_num}_big_chances_created"] = float(player.big_chances_created or 0)

        # 如果不足 11 人，填充剩余位置
        for position_idx in range(len(starters) + 1, 12):
            p_num = position_idx
            for field in self.PLAYER_FEATURE_FIELDS:
                features[f"{prefix}_p{p_num}_{field}"] = 0.0

        return features

    def _compute_player_cross_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算球员级别交叉特征（V23.0 扩展）

        包括:
            - 核心球员总身价（前5名）
            - 关键球员总 xG（前3名）
            - 阵容深度评分（方差分析）
        """
        cross_features = {}

        for prefix in ["home", "away"]:
            # 收集该队所有球员的身价和 xG
            player_values = []
            player_xgs = []
            player_ratings = []

            for p_idx in range(1, 12):  # p1 到 p11
                value_key = f"{prefix}_p{p_idx}_market_value"
                xg_key = f"{prefix}_p{p_idx}_expected_goals"
                rating_key = f"{prefix}_p{p_idx}_team_rating"

                player_values.append(features.get(value_key, 0.0))
                player_xgs.append(features.get(xg_key, 0.0))
                player_ratings.append(features.get(rating_key, 0.0))

            # 核心球员总身价（前5名）
            player_values_sorted = sorted(player_values, reverse=True)
            cross_features[f"{prefix}_top5_value"] = round(sum(player_values_sorted[:5]), 2)

            # 关键球员总 xG（前3名）
            player_xgs_sorted = sorted(player_xgs, reverse=True)
            cross_features[f"{prefix}_top3_xg"] = round(sum(player_xgs_sorted[:3]), 4)

            # 阵容深度评分（身高的方差）
            if player_values:
                mean_value = sum(player_values) / len(player_values)
                variance = sum((v - mean_value) ** 2 for v in player_values) / len(player_values)
                cross_features[f"{prefix}_lineup_variance"] = round(variance, 4)

            # 评分最高球员（王牌球员）
            if player_ratings:
                cross_features[f"{prefix}_star_rating"] = round(max(player_ratings), 2)

        # 主客队对比
        cross_features["diff_top5_value"] = round(
            cross_features.get("home_top5_value", 0) - cross_features.get("away_top5_value", 0), 2
        )
        cross_features["diff_top3_xg"] = round(
            cross_features.get("home_top3_xg", 0) - cross_features.get("away_top3_xg", 0), 4
        )
        cross_features["diff_star_rating"] = round(
            cross_features.get("home_star_rating", 0) - cross_features.get("away_star_rating", 0), 2
        )

        return cross_features

    def _calculate_squad_value(self, players: list[PlayerStats]) -> float:
        """计算阵容总价值"""
        total_value = sum(p.market_value or 0.0 for p in players)
        return round(total_value, 2)

    def _analyze_age_structure(self, players: list[PlayerStats], prefix: str) -> dict[str, float]:
        """分析年龄结构特征"""
        features = {}

        ages = [float(p.age or self.config.default_age) for p in players]

        if not ages:
            return self._get_default_age_features(prefix)

        # 平均年龄
        avg_age = sum(ages) / len(ages)
        features[f"{prefix}_age_average"] = round(avg_age, 2)

        # 年龄方差
        if len(ages) > 1:
            variance = sum((a - avg_age) ** 2 for a in ages) / len(ages)
            features[f"{prefix}_age_variance"] = round(variance, 2)
        else:
            features[f"{prefix}_age_variance"] = 0.0

        # U23 统计
        u23_count = sum(1 for age in ages if age < self.config.u23_threshold)
        features[f"{prefix}_u23_count"] = float(u23_count)
        features[f"{prefix}_u23_ratio"] = round(u23_count / len(ages), 4)

        # 老将统计
        veteran_count = sum(1 for age in ages if age >= self.config.veteran_threshold)
        features[f"{prefix}_veteran_count"] = float(veteran_count)
        features[f"{prefix}_veteran_ratio"] = round(veteran_count / len(ages), 4)

        # 黄金期球员
        prime_count = sum(1 for age in ages if self.config.u23_threshold <= age < self.config.veteran_threshold)
        features[f"{prefix}_prime_count"] = float(prime_count)
        features[f"{prefix}_prime_ratio"] = round(prime_count / len(ages), 4)

        # 年龄结构平衡度（熵）
        ratios = [
            features[f"{prefix}_u23_ratio"],
            features[f"{prefix}_prime_ratio"],
            features[f"{prefix}_veteran_ratio"],
        ]
        features[f"{prefix}_age_balance_entropy"] = round(self._calculate_entropy(ratios), 4)

        return features

    def _calculate_entropy(self, ratios: list[float]) -> float:
        """计算熵（衡量分布均衡程度）"""
        import math

        entropy = 0.0
        for r in ratios:
            if r > 0:
                entropy -= r * math.log(r)
        return entropy

    def _calculate_value_efficiency(self, squad_value: float, team_stats: Any) -> float:
        """计算身价效率比（每百万身价产生的 xG）"""
        if squad_value <= 0:
            return 0.0

        xg = 0.0
        if hasattr(team_stats, "expected_goals") and team_stats.expected_goals:
            xg = team_stats.expected_goals
        elif isinstance(team_stats, dict):
            xg = team_stats.get("expected_goals", team_stats.get("expectedGoals", 0.0))

        efficiency = xg / squad_value if squad_value > 0 else 0.0
        return round(efficiency, 4)

    def _compute_comparison_features(self, features: dict[str, float]) -> dict[str, float]:
        """计算对比特征"""
        comparison_features = {}

        # 身价倍率差
        home_value = features.get("home_squad_value", 0)
        away_value = features.get("away_squad_value", 0)

        if home_value > 0 and away_value > 0:
            comparison_features["value_gap_ratio"] = round(home_value / away_value, 4)
            comparison_features["home_value_share"] = round(home_value / (home_value + away_value), 4)
            comparison_features["diff_squad_value"] = round(home_value - away_value, 2)
            comparison_features["value_disparity_index"] = round(
                abs(home_value - away_value) / (home_value + away_value), 4
            )
        else:
            comparison_features["value_gap_ratio"] = 1.0
            comparison_features["home_value_share"] = 0.5
            comparison_features["diff_squad_value"] = 0.0
            comparison_features["value_disparity_index"] = 0.0

        # 年龄对比
        home_age = features.get("home_age_average", 0)
        away_age = features.get("away_age_average", 0)
        comparison_features["diff_age_average"] = round(home_age - away_age, 2)

        # 效率对比
        home_efficiency = features.get("home_value_efficiency", 0)
        away_efficiency = features.get("away_value_efficiency", 0)
        comparison_features["diff_value_efficiency"] = round(home_efficiency - away_efficiency, 4)

        # 综合财富评分
        home_wealth = self._calculate_wealth_score(features, "home", home_value, home_age)
        away_wealth = self._calculate_wealth_score(features, "away", away_value, away_age)
        comparison_features["home_wealth_score"] = round(home_wealth, 4)
        comparison_features["away_wealth_score"] = round(away_wealth, 4)
        comparison_features["diff_wealth_score"] = round(home_wealth - away_wealth, 4)

        return comparison_features

    def _calculate_wealth_score(self, features: dict[str, float], prefix: str, value: float, age: float) -> float:
        """计算综合财富评分"""
        # 身价分（归一化到 0-50）
        value_score = min(value / 10, 50)

        # 年龄经验分（0-30）
        if 26 <= age <= 28:
            age_score = 30
        elif 24 <= age <= 30:
            age_score = 25
        elif 22 <= age < 24 or 30 < age <= 32:
            age_score = 20
        else:
            age_score = 10

        # 阵容稳定性分（0-20）
        balance_entropy = features.get(f"{prefix}_age_balance_entropy", 0)
        stability_score = min(balance_entropy / 1.1 * 20, 20)

        return value_score + age_score + stability_score

    def _get_default_features(self, prefix: str) -> dict[str, float]:
        """获取默认特征值（数据缺失时）"""
        return {
            f"{prefix}_squad_value": 0.0,
            f"{prefix}_avg_player_value": 0.0,
            **self._get_default_age_features(prefix),
            f"{prefix}_value_efficiency": 0.0,
        }

    def _get_default_age_features(self, prefix: str) -> dict[str, float]:
        """获取默认年龄特征"""
        return {
            f"{prefix}_age_average": self.config.default_age,
            f"{prefix}_age_variance": 0.0,
            f"{prefix}_u23_count": 0.0,
            f"{prefix}_u23_ratio": 0.0,
            f"{prefix}_veteran_count": 0.0,
            f"{prefix}_veteran_ratio": 0.0,
            f"{prefix}_prime_count": 0.0,
            f"{prefix}_prime_ratio": 0.0,
            f"{prefix}_age_balance_entropy": 0.0,
        }

    def get_feature_schema(self) -> dict[str, type]:
        """
        获取输出特征的 Schema（V23.0 动态生成）

        使用 Python 循环动态生成 270+ 维特征的定义
        """
        schema = {
            # 聚合特征
            "home_squad_value": float,
            "away_squad_value": float,
            "value_gap_ratio": float,
            "home_avg_player_value": float,
            "value_disparity_index": float,
            "home_age_average": float,
            "away_age_average": float,
            "home_u23_ratio": float,
            "home_veteran_ratio": float,
            "home_age_variance": float,
            "home_value_efficiency": float,
            "diff_value_efficiency": float,
            "home_wealth_score": float,
            "diff_wealth_score": float,
        }

        # V23.0: 动态生成球员级别特征 Schema（220 维）
        for prefix in ["home", "away"]:
            for p_idx in range(1, 12):  # p1 到 p11
                for field in self.PLAYER_FEATURE_FIELDS:
                    schema[f"{prefix}_p{p_idx}_{field}"] = float

        # 球员交叉特征
        for prefix in ["home", "away"]:
            schema[f"{prefix}_top5_value"] = float
            schema[f"{prefix}_top3_xg"] = float
            schema[f"{prefix}_lineup_variance"] = float
            schema[f"{prefix}_star_rating"] = float

        schema["diff_top5_value"] = float
        schema["diff_top3_xg"] = float
        schema["diff_star_rating"] = float

        return schema
