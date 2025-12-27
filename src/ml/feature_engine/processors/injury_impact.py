"""
InjuryImpactProcessor - 战损与伤停深度处理器
=============================================

负责提取伤停与阵容变动对比赛影响的相关特征，包括:
    - 缺阵主力球员身价占比（战损评估）
    - 阵容稳定性分析（近 3 场变动率）
    - 替补席深度（下半场逆转能力）

设计模式:
    - 历史对比: 对比当前阵容与近 5 场常用首发
    - 深度分析: 评估替补席质量
    - 稳定性指标: 阵容连续性评分

作者: FootballPrediction Architecture Team
版本: V23.0-alpha
"""

import logging
import statistics
from collections import Counter
from dataclasses import dataclass
from typing import Any

from ..base import BaseProcessor, ProcessorConfig, ProcessorResult
from ..models import HomeAway, LineupInfo, MatchData, PlayerStats

logger = logging.getLogger(__name__)


@dataclass
class LineupSnapshot:
    """阵容快照（用于历史对比）"""

    match_id: str
    starter_ids: set[str]
    total_value: float
    avg_rating: float
    date: str


class InjuryImpactProcessorConfig(ProcessorConfig):
    """
    InjuryImpactProcessor 配置

    Attributes:
        enable_value_analysis: 是否启用身价分析
        enable_stability_analysis: 是否启用稳定性分析
        enable_bench_analysis: 是否启用替补分析
        history_window: 历史阵容对比窗口（场数）
        min_history_matches: 最少历史比赛数量
    """

    enable_value_analysis: bool = True
    enable_stability_analysis: bool = True
    enable_bench_analysis: bool = True
    history_window: int = 5
    min_history_matches: int = 3


class InjuryImpactProcessor(BaseProcessor[MatchData]):
    """
    战损与伤停深度处理器

    职责:
        1. 对比当前阵容与历史常用首发（识别缺阵主力）
        2. 计算缺阵主力身价占比（战损评估）
        3. 分析阵容稳定性（近 3 场变动率）
        4. 评估替补席深度（下半场逆转能力）

    特征输出:
        - home_missing_starter_value_ratio: 主队缺阵主力身价占比
        - away_missing_starter_value_ratio: 客队缺阵主力身价占比
        - home_availability_stability: 主队阵容稳定性指数
        - away_availability_stability: 客队阵容稳定性指数
        - home_bench_impact_potential: 主队替补影响力
        - away_bench_impact_potential: 客队替补影响力
        - home_expected_starters_present: 主队预期主力在场率
        - away_expected_starters_present: 客队预期主力在场率

    数据来源:
        - data.home_lineup / data.away_lineup (当前阵容)
        - context.history_lineups (历史阵容数据，需外部注入)

    Example:
        >>> processor = InjuryImpactProcessor()
        >>> result = processor.execute(match_data)
        >>> print(result.data["home_missing_starter_value_ratio"])
        0.15  # 15% 的主力身价缺阵
    """

    processor_name = "InjuryImpactProcessor"
    processor_version = "23.0.0"
    priority = 58  # 在 MarketOddsProcessor 之后执行

    def __init__(self, config: InjuryImpactProcessorConfig | None = None) -> None:
        super().__init__(config or InjuryImpactProcessorConfig())
        self.config: InjuryImpactProcessorConfig = self.config

    def process(self, data: MatchData, context: Any) -> ProcessorResult:
        """
        提取战损与伤停特征

        Args:
            data: 比赛数据
            context: 处理上下文（需要包含历史阵容数据）

        Returns:
            ProcessorResult: 包含战损特征的处理器结果
        """
        features: dict[str, float] = {}
        warnings: list[str] = []

        try:
            # 1. 获取历史阵容数据
            home_history = self._get_history_lineups(context, HomeAway.HOME)
            away_history = self._get_history_lineups(context, HomeAway.AWAY)

            # 2. 分析主队
            if data.home_lineup:
                home_features = self._analyze_team_impact(
                    data.home_lineup,
                    home_history,
                    "home",
                )
                features.update(home_features)
            else:
                warnings.append("home_lineup_missing")
                features.update(self._create_default_team_features("home"))

            # 3. 分析客队
            if data.away_lineup:
                away_features = self._analyze_team_impact(
                    data.away_lineup,
                    away_history,
                    "away",
                )
                features.update(away_features)
            else:
                warnings.append("away_lineup_missing")
                features.update(self._create_default_team_features("away"))

            # 4. 对比特征（主客对比）
            comparison_features = self._compute_comparison_features(features)
            features.update(comparison_features)

            # 5. 综合战损评分
            impact_score_features = self._compute_impact_scores(features)
            features.update(impact_score_features)

            result = ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "home_history_available": len(home_history) >= self.config.min_history_matches,
                    "away_history_available": len(away_history) >= self.config.min_history_matches,
                },
            )

            # 添加警告
            for warning in warnings:
                result.with_warning(warning)

            return result

        except Exception as e:
            logger.error(f"InjuryImpactProcessor failed for match {data.match_id}: {e}")
            return ProcessorResult.failure_result(str(e))

    def _get_history_lineups(self, context: Any, side: HomeAway) -> list[LineupSnapshot]:
        """
        获取历史阵容数据

        数据来源:
            - context.history_lineups.{home|away} (外部注入)
            - context.cache (缓存)

        Args:
            context: 处理上下文
            side: 主/客队标识

        Returns:
            历史阵容快照列表（按时间倒序）
        """
        history_key = f"{side.value}_history_lineups"

        # 从 context 获取
        if context:
            cached = context.get_cached(history_key)
            if cached:
                return cached

        # 从 metadata 获取
        if context and context.metadata:
            history = context.metadata.get(f"{side.value}_lineup_history")
            if history:
                # 转换为 LineupSnapshot
                snapshots = []
                for h in history[: self.config.history_window]:
                    snapshots.append(
                        LineupSnapshot(
                            match_id=h.get("match_id", "unknown"),
                            starter_ids=set(h.get("starter_ids", [])),
                            total_value=h.get("total_value", 0.0),
                            avg_rating=h.get("avg_rating", 0.0),
                            date=h.get("date", ""),
                        )
                    )
                return snapshots

        return []

    def _analyze_team_impact(
        self,
        lineup: LineupInfo,
        history: list[LineupSnapshot],
        prefix: str,
    ) -> dict[str, float]:
        """
        分析单支球队的战损情况

        Args:
            lineup: 当前阵容信息
            history: 历史阵容数据
            prefix: 特征名前缀（home/away）

        Returns:
            战损特征字典
        """
        features = {}

        # 提取当前首发球员
        current_starters = self._extract_starters(lineup)

        # 计算当前阵容总身价
        current_value = self._compute_lineup_value(current_starters)

        # 识别"预期主力"（基于历史）
        expected_starters = self._identify_expected_starters(history, current_starters)

        if expected_starters:
            # 1. 缺阵主力分析
            missing_features = self._analyze_missing_starters(
                current_starters,
                expected_starters,
                prefix,
            )
            features.update(missing_features)

            # 2. 阵容稳定性分析
            if self.config.enable_stability_analysis and len(history) >= self.config.min_history_matches:
                stability_features = self._analyze_stability(
                    current_starters,
                    history,
                    prefix,
                )
                features.update(stability_features)
            else:
                features[f"{prefix}_availability_stability"] = 0.5

            # 3. 预期主力在场率
            present_count = sum(1 for s in expected_starters if s.player_id in {p.player_id for p in current_starters})
            features[f"{prefix}_expected_starters_present"] = round(
                present_count / len(expected_starters) if expected_starters else 1.0, 4
            )
        else:
            # 无历史数据，使用默认值
            features[f"{prefix}_missing_starter_value_ratio"] = 0.0
            features[f"{prefix}_availability_stability"] = 0.5
            features[f"{prefix}_expected_starters_present"] = 1.0

        # 4. 替补席分析（不需要历史数据）
        if self.config.enable_bench_analysis:
            bench_features = self._analyze_bench_impact(lineup, prefix)
            features.update(bench_features)
        else:
            features[f"{prefix}_bench_impact_potential"] = 0.5
            features[f"{prefix}_bench_depth_score"] = 0.5

        # 5. 阵容连续性（是否与上一场相同）
        if history:
            last_starters = history[0].starter_ids if history else set()
            current_ids = {p.player_id for p in current_starters if p.player_id}
            overlap = len(current_ids & last_starters)
            total = len(current_ids | last_starters)
            features[f"{prefix}_lineup_continuity"] = round(overlap / total if total > 0 else 0.0, 4)
        else:
            features[f"{prefix}_lineup_continuity"] = 0.5

        return features

    def _extract_starters(self, lineup: LineupInfo) -> list[PlayerStats]:
        """提取首发球员列表"""
        return [p for p in lineup.players if p.is_starter is True]

    def _compute_lineup_value(self, players: list[PlayerStats]) -> float:
        """计算阵容总身价（百万欧元）"""
        return sum(p.market_value or 0.0 for p in players)

    def _identify_expected_starters(
        self,
        history: list[LineupSnapshot],
        current_players: list[PlayerStats],
    ) -> list[PlayerStats]:
        """
        识别"预期主力"（基于历史首发频率）

        逻辑:
            - 统计近 N 场各球员的首发次数
            - 首发频率 >= 60% 的球员视为"预期主力"
        """
        if not history or len(history) < self.config.min_history_matches:
            return []

        # 统计首发频率
        starter_counts: Counter[str] = Counter()
        for snapshot in history:
            starter_counts.update(snapshot.starter_ids)

        # 确定预期主力（首发频率 >= 60%）
        threshold = len(history) * 0.6
        expected_ids = {pid for pid, count in starter_counts.items() if count >= threshold}

        # 从当前球员列表中找到预期主力
        expected_starters = [p for p in current_players if p.player_id and p.player_id in expected_ids]

        return expected_starters

    def _analyze_missing_starters(
        self,
        current_starters: list[PlayerStats],
        expected_starters: list[PlayerStats],
        prefix: str,
    ) -> dict[str, float]:
        """
        分析缺阵主力的影响

        评估:
            - 缺阵主力人数
            - 缺阵主力总身价占比
        """
        features = {}

        current_ids = {p.player_id for p in current_starters if p.player_id}
        expected_ids = {p.player_id for p in expected_starters if p.player_id}

        # 缺阵主力
        missing_ids = expected_ids - current_ids
        missing_players = [p for p in expected_starters if p.player_id in missing_ids]

        if not expected_starters:
            features[f"{prefix}_missing_starter_count"] = 0.0
            features[f"{prefix}_missing_starter_value_ratio"] = 0.0
            return features

        # 缺阵人数
        features[f"{prefix}_missing_starter_count"] = float(len(missing_players))

        # 缺阵主力身价占比
        total_expected_value = sum(p.market_value or 0.0 for p in expected_starters)
        missing_value = sum(p.market_value or 0.0 for p in missing_players)

        if total_expected_value > 0:
            features[f"{prefix}_missing_starter_value_ratio"] = round(missing_value / total_expected_value, 4)
        else:
            features[f"{prefix}_missing_starter_value_ratio"] = 0.0

        # 战损严重程度分类
        ratio = features[f"{prefix}_missing_starter_value_ratio"]
        if ratio > 0.3:
            features[f"{prefix}_impact_severity"] = 3  # 严重
        elif ratio > 0.15:
            features[f"{prefix}_impact_severity"] = 2  # 中等
        elif ratio > 0.05:
            features[f"{prefix}_impact_severity"] = 1  # 轻微
        else:
            features[f"{prefix}_impact_severity"] = 0  # 无影响

        return features

    def _analyze_stability(
        self,
        current_starters: list[PlayerStats],
        history: list[LineupSnapshot],
        prefix: str,
    ) -> dict[str, float]:
        """
        分析阵容稳定性

        评估:
            - 近 3 场阵容变动率
            - 首发连续性
        """
        features = {}

        if not history:
            features[f"{prefix}_availability_stability"] = 0.5
            return features

        current_ids = {p.player_id for p in current_starters if p.player_id}

        # 计算近 N 场的阵容相似度
        similarities = []
        for snapshot in history[: min(3, len(history))]:
            if not snapshot.starter_ids:
                continue
            overlap = len(current_ids & snapshot.starter_ids)
            total = len(current_ids | snapshot.starter_ids)
            similarity = overlap / total if total > 0 else 0.0
            similarities.append(similarity)

        if similarities:
            features[f"{prefix}_availability_stability"] = round(statistics.mean(similarities), 4)
            # 变动率（1 - 稳定性）
            features[f"{prefix}_turnover_rate"] = round(1 - features[f"{prefix}_availability_stability"], 4)
        else:
            features[f"{prefix}_availability_stability"] = 0.5
            features[f"{prefix}_turnover_rate"] = 0.5

        return features

    def _analyze_bench_impact(
        self,
        lineup: LineupInfo,
        prefix: str,
    ) -> dict[str, float]:
        """
        分析替补席影响力

        评估:
            - 替补平均身价
            - 替补平均评分（如果可用）
            - 替补深度（人数）
        """
        features = {}

        # 提取替补球员
        bench_players = [p for p in lineup.players if p.is_starter is False]

        if not bench_players:
            features[f"{prefix}_bench_impact_potential"] = 0.0
            features[f"{prefix}_bench_depth_score"] = 0.0
            return features

        # 替补人数
        bench_count = len(bench_players)
        features[f"{prefix}_bench_count"] = float(bench_count)

        # 替补平均身价
        bench_values = [p.market_value or 0.0 for p in bench_players]
        avg_bench_value = statistics.mean(bench_values) if bench_values else 0.0
        features[f"{prefix}_bench_avg_value"] = round(avg_bench_value, 2)

        # 替补平均评分（如果可用）
        ratings = [p.team_rating for p in bench_players if p.team_rating is not None]
        if ratings:
            avg_rating = statistics.mean(ratings)
            # 归一化到 0-1（假设评分范围 6-8）
            features[f"{prefix}_bench_avg_rating"] = round(avg_rating, 2)
            features[f"{prefix}_bench_impact_potential"] = round(
                (avg_rating - 6.0) / 2.0,  # 6.0=低, 8.0=高
                4,
            )
        else:
            features[f"{prefix}_bench_avg_rating"] = 6.5
            features[f"{prefix}_bench_impact_potential"] = 0.25

        # 替补深度评分（综合人数和质量）
        depth_score = min(bench_count / 10.0, 1.0) * 0.5 + features[f"{prefix}_bench_impact_potential"] * 0.5
        features[f"{prefix}_bench_depth_score"] = round(depth_score, 4)

        return features

    def _compute_comparison_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算主客队对比特征

        评估:
            - 主客队战损对比
            - 主客队稳定性对比
        """
        comparison = {}

        # 战损差值
        home_missing = features.get("home_missing_starter_value_ratio", 0.0)
        away_missing = features.get("away_missing_starter_value_ratio", 0.0)
        comparison["diff_missing_value_ratio"] = round(home_missing - away_missing, 4)

        # 稳定性差值
        home_stability = features.get("home_availability_stability", 0.5)
        away_stability = features.get("away_availability_stability", 0.5)
        comparison["diff_stability"] = round(home_stability - away_stability, 4)

        # 替补深度差值
        home_bench = features.get("home_bench_depth_score", 0.5)
        away_bench = features.get("away_bench_depth_score", 0.5)
        comparison["diff_bench_depth"] = round(home_bench - away_bench, 4)

        # 综合战损优势（负值表示主队受损更重）
        comparison["overall_impact_advantage"] = round(
            away_missing - home_missing,  # 主队少缺阵 = 优势
            4,
        )

        return comparison

    def _compute_impact_scores(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算综合战损评分

        综合考虑:
            - 缺阵主力
            - 阵容稳定性
            - 替补深度
        """
        scores = {}

        # 主队综合评分（0 = 严重受损, 1 = 完整无损）
        home_missing = features.get("home_missing_starter_value_ratio", 0.0)
        home_stability = features.get("home_availability_stability", 0.5)
        home_bench = features.get("home_bench_depth_score", 0.5)

        scores["home_composite_health"] = round((1 - home_missing) * 0.5 + home_stability * 0.3 + home_bench * 0.2, 4)

        # 客队综合评分
        away_missing = features.get("away_missing_starter_value_ratio", 0.0)
        away_stability = features.get("away_availability_stability", 0.5)
        away_bench = features.get("away_bench_depth_score", 0.5)

        scores["away_composite_health"] = round((1 - away_missing) * 0.5 + away_stability * 0.3 + away_bench * 0.2, 4)

        # 健康差值
        scores["diff_composite_health"] = round(scores["home_composite_health"] - scores["away_composite_health"], 4)

        return scores

    def _create_default_team_features(self, prefix: str) -> dict[str, float]:
        """创建默认球队特征（无数据时）"""
        return {
            f"{prefix}_missing_starter_count": 0.0,
            f"{prefix}_missing_starter_value_ratio": 0.0,
            f"{prefix}_impact_severity": 0,
            f"{prefix}_availability_stability": 0.5,
            f"{prefix}_turnover_rate": 0.5,
            f"{prefix}_bench_count": 7.0,
            f"{prefix}_bench_avg_value": 10.0,
            f"{prefix}_bench_avg_rating": 6.5,
            f"{prefix}_bench_impact_potential": 0.25,
            f"{prefix}_bench_depth_score": 0.5,
            f"{prefix}_lineup_continuity": 0.5,
            f"{prefix}_expected_starters_present": 1.0,
        }

    def get_feature_schema(self) -> dict[str, type]:
        """获取输出特征的 Schema"""
        return {
            # 主队
            "home_missing_starter_count": float,
            "home_missing_starter_value_ratio": float,
            "home_impact_severity": int,
            "home_availability_stability": float,
            "home_turnover_rate": float,
            "home_bench_count": float,
            "home_bench_avg_value": float,
            "home_bench_avg_rating": float,
            "home_bench_impact_potential": float,
            "home_bench_depth_score": float,
            "home_lineup_continuity": float,
            "home_expected_starters_present": float,
            "home_composite_health": float,
            # 客队
            "away_missing_starter_count": float,
            "away_missing_starter_value_ratio": float,
            "away_impact_severity": int,
            "away_availability_stability": float,
            "away_turnover_rate": float,
            "away_bench_count": float,
            "away_bench_avg_value": float,
            "away_bench_avg_rating": float,
            "away_bench_impact_potential": float,
            "away_bench_depth_score": float,
            "away_lineup_continuity": float,
            "away_expected_starters_present": float,
            "away_composite_health": float,
            # 对比
            "diff_missing_value_ratio": float,
            "diff_stability": float,
            "diff_bench_depth": float,
            "overall_impact_advantage": float,
            "diff_composite_health": float,
        }
