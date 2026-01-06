"""
AdvancedPassingProcessor - 深度传球处理器（V23.0 原子化版）
=============================================================

负责提取高级传球特征，包括:
    - 进攻三区传球成功率（final_third_pass_accuracy）
    - 长传破防效率（long_ball_success_rate）
    - 传球 DNA 分析（短传/中传/长传比例）
    - 传中威胁度（crossing_efficiency）
    - 直塞球穿透力（through_ball_efficiency）
    - 纵向推进效率（vertical_progression）
    - **V23.0 新增**: 关键位置传球特征原子化（5位置 × 15维 × 2队 = 150维）

设计模式:
    - 深度解析: 从 FotMob playerStats 提取高级传球数据
    - 维度爆破: 单个处理器输出 210+ 维特征
    - 战术建模: 引入空间传球网络分析
    - 位置原子化: 关键位置球员的传球指纹独立展开

作者: FootballPrediction Architecture Team
版本: V23.0-final
"""

from dataclasses import dataclass
import logging
from typing import Any

from ..base import BaseProcessor, ProcessorConfig, ProcessorResult
from ..models import MatchData, PlayerStats

logger = logging.getLogger(__name__)


@dataclass
class AdvancedPassingProcessorConfig(ProcessorConfig):
    """
    AdvancedPassingProcessor 配置

    Attributes:
        enable_zone_analysis: 是否启用区域分析
        enable_passing_dna: 是否启用传球 DNA 分析
        enable_crossing_analysis: 是否启用传中分析
        enable_vertical_analysis: 是否启用纵向推进分析
        enable_position_atomization: 是否启用位置原子化（V23.0）
        min_pass_threshold: 最小传球次数阈值
        long_ball_distance: 长传距离阈值（米）
    """

    enable_zone_analysis: bool = True
    enable_passing_dna: bool = True
    enable_crossing_analysis: bool = True
    enable_vertical_analysis: bool = True
    enable_position_atomization: bool = True  # V23.0 新增
    min_pass_threshold: int = 5
    long_ball_distance: float = 30.0

    # 关键位置定义（基于球衣号码）
    # GK: 1, DF: 2-6, MF: 7-11, FW: 9, 14
    KEY_POSITIONS = {
        "gk": [1],  # 门将
        "libero": [2, 4, 5],  # 中后卫/自由人（出球核心）
        "carrier": [6, 8],  # 中场核心（持球推进）
        "creator": [10, 14],  # 前腰/组织核心
        "winger": [7, 11],  # 边锋（传中威胁）
    }


# 关键位置传球特征字段（15 个高级传球指标）
POSITION_PASSING_FIELDS = [
    # 区域传球
    "final_third_passes",
    "accurate_final_third_passes",
    "middle_third_passes",
    "accurate_middle_third_passes",
    # 传球 DNA
    "short_passes",
    "medium_passes",
    "long_passes",
    "accurate_long_passes",
    # 传中与直塞
    "crosses",
    "accurate_crosses",
    "through_balls",
    "accurate_through_balls",
    # 纵向推进
    "forward_passes",
    "backward_passes",
    "vertical_progression",
]


class AdvancedPassingProcessor(BaseProcessor[MatchData]):
    """
    深度传球处理器（V23.0 原子化版）

    职责:
        1. 从 playerStats 提取高级传球数据
        2. 计算区域传球效率
        3. 分析传球 DNA
        4. 评估传中威胁度和直塞球穿透力
        5. 计算纵向推进效率
        6. **V23.0**: 关键位置传球特征原子化

    特征输出（210+ 维）:
        # 聚合维度（约 60 维）
        ... (原有聚合特征)

        # V23.0 位置原子化维度（150 维）
        - home_gk_final_third_passes, home_gk_long_passes, ...
        - home_libero_vertical_progression, home_libero_through_balls, ...
        - home_carrier_accurate_passes, home_carrier_short_passes, ...
        - home_creator_through_balls, home_creator_final_third_passes, ...
        - home_winger_crosses, home_winger_accurate_crosses, ...
        - (away 队同样 5 个位置)

        每个位置的 15 个传球指标:
            1. final_third_passes: 进攻三区传球
            2. accurate_final_third_passes: 准确进攻三区传球
            3. middle_third_passes: 中场传球
            4. accurate_middle_third_passes: 准确中场传球
            5. short_passes: 短传
            6. medium_passes: 中传
            7. long_passes: 长传
            8. accurate_long_passes: 准确长传
            9. crosses: 传中
            10. accurate_crosses: 准确传中
            11. through_balls: 直塞球
            12. accurate_through_balls: 准确直塞球
            13. forward_passes: 向前传球
            14. backward_passes: 向后传球
            15. vertical_progression: 纵向推进
    """

    processor_name = "AdvancedPassingProcessor"
    processor_version = "23.0.0"
    priority = 32

    def __init__(self, config: AdvancedPassingProcessorConfig | None = None) -> None:
        super().__init__(config or AdvancedPassingProcessorConfig())
        self.config: AdvancedPassingProcessorConfig = self.config

    def process(self, data: MatchData, context: Any) -> ProcessorResult:
        """提取高级传球特征"""
        features: dict[str, float] = {}

        try:
            # 1. 聚合维度特征（向后兼容）
            agg_features = self._extract_aggregate_features(data)
            features.update(agg_features)

            # 2. V23.0: 位置原子化维度
            if self.config.enable_position_atomization:
                if data.home_lineup and data.home_lineup.players:
                    home_pos_features = self._atomize_position_passing(data.home_lineup.players, "home")
                    features.update(home_pos_features)

                if data.away_lineup and data.away_lineup.players:
                    away_pos_features = self._atomize_position_passing(data.away_lineup.players, "away")
                    features.update(away_pos_features)

            # 3. 计算对比特征
            comparison_features = self._compute_comparison_features(features)
            features.update(comparison_features)

            # 4. V23.0: 位置交叉特征
            if self.config.enable_position_atomization:
                cross_features = self._compute_position_cross_features(features)
                features.update(cross_features)

            return ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "position_atomization_enabled": self.config.enable_position_atomization,
                },
            )

        except Exception as e:
            logger.error(f"AdvancedPassingProcessor failed: {e}")
            return ProcessorResult.failure_result(str(e))

    def _extract_aggregate_features(self, data: MatchData) -> dict[str, float]:
        """提取聚合维度特征（原有逻辑）"""
        features = {}

        # 使用 LineupInfo 中的球员数据
        if data.home_lineup and data.home_lineup.players:
            home_players = [p.model_dump() for p in data.home_lineup.players if p.is_starter]
            if home_players:
                home_features = self._analyze_team_passing(home_players, "home")
                features.update(home_features)
            else:
                features.update(self._get_default_features("home"))
        else:
            features.update(self._get_default_features("home"))

        if data.away_lineup and data.away_lineup.players:
            away_players = [p.model_dump() for p in data.away_lineup.players if p.is_starter]
            if away_players:
                away_features = self._analyze_team_passing(away_players, "away")
                features.update(away_features)
            else:
                features.update(self._get_default_features("away"))
        else:
            features.update(self._get_default_features("away"))

        return features

    def _analyze_team_passing(self, players: list[dict[str, Any]], prefix: str) -> dict[str, float]:
        """分析单队传球特征（聚合维度）"""
        features = {}

        # 基础传球统计
        basic_passing = self._calculate_basic_passing(players)
        for k, v in basic_passing.items():
            features[f"{prefix}_{k}"] = v

        # 区域传球分析
        if self.config.enable_zone_analysis:
            zone_features = self._analyze_zone_passing(players, prefix)
            features.update(zone_features)

        # 传球 DNA 分析
        if self.config.enable_passing_dna:
            dna_features = self._analyze_passing_dna(players, prefix)
            features.update(dna_features)

        # 传中分析
        if self.config.enable_crossing_analysis:
            crossing_features = self._analyze_crossing(players, prefix)
            features.update(crossing_features)

        # 直塞球分析
        through_ball_features = self._analyze_through_balls(players, prefix)
        features.update(through_ball_features)

        # 纵向推进分析
        if self.config.enable_vertical_analysis:
            vertical_features = self._analyze_vertical_progression(players, prefix)
            features.update(vertical_features)

        return features

    def _atomize_position_passing(self, players: list[PlayerStats], prefix: str) -> dict[str, float]:
        """
        原子化位置传球特征（V23.0 核心爆破）

        为关键 5 个位置的球员创建独立传球特征

        Args:
            players: 球员列表
            prefix: 特征前缀

        Returns:
            位置原子化特征字典（5 位置 × 15 维 = 75 维）
        """
        features = {}

        # 提取首发球员
        starters = [p for p in players if p.is_starter is True]

        # 按位置分组球员
        position_players = self._group_players_by_position(starters)

        # 为每个关键位置平铺传球特征
        for pos_name, pos_players in position_players.items():
            # 选择该位置的"代表性"球员（出场时间最长的）
            if pos_players:
                representative = max(pos_players, key=lambda p: p.minutes_played or 0)

                # 平铺该位置球员的 15 个传球指标
                for field in POSITION_PASSING_FIELDS:
                    value = getattr(representative, field, None) or 0
                    if value is None:
                        value = 0

                    # 特征命名: home_gk_final_third_passes, home_libero_long_passes, ...
                    features[f"{prefix}_{pos_name}_{field}"] = float(value)

                # 计算该位置的传球成功率
                total_passes = (
                    (representative.final_third_passes or 0)
                    + (representative.middle_third_passes or 0)
                    + (representative.short_passes or 0)
                    + (representative.medium_passes or 0)
                )
                accurate_passes = (
                    (representative.accurate_final_third_passes or 0)
                    + (representative.accurate_middle_third_passes or 0)
                    + (representative.short_passes or 0)  # 短传默认准确
                    + (representative.medium_passes or 0)
                )
                if total_passes > 0:
                    features[f"{prefix}_{pos_name}_pass_accuracy"] = round(accurate_passes / total_passes * 100, 2)
                else:
                    features[f"{prefix}_{pos_name}_pass_accuracy"] = 0.0

                # 该位置的长传成功率
                long_total = representative.long_passes or 0
                long_accurate = representative.accurate_long_passes or 0
                if long_total >= self.config.min_pass_threshold:
                    features[f"{prefix}_{pos_name}_long_pass_success"] = round(long_accurate / long_total * 100, 2)
                else:
                    features[f"{prefix}_{pos_name}_long_pass_success"] = -1.0

                # 该位置的传中成功率
                cross_total = representative.crosses or 0
                cross_accurate = representative.accurate_crosses or 0
                if cross_total >= self.config.min_pass_threshold:
                    features[f"{prefix}_{pos_name}_cross_success"] = round(cross_accurate / cross_total * 100, 2)
                else:
                    features[f"{prefix}_{pos_name}_cross_success"] = -1.0

                # 该位置的直塞球成功率
                through_total = representative.through_balls or 0
                through_accurate = representative.accurate_through_balls or 0
                if through_total >= self.config.min_pass_threshold:
                    features[f"{prefix}_{pos_name}_through_ball_success"] = round(
                        through_accurate / through_total * 100, 2
                    )
                else:
                    features[f"{prefix}_{pos_name}_through_ball_success"] = -1.0

            else:
                # 该位置没有球员，填充默认值
                for field in POSITION_PASSING_FIELDS:
                    features[f"{prefix}_{pos_name}_{field}"] = 0.0
                features[f"{prefix}_{pos_name}_pass_accuracy"] = 0.0
                features[f"{prefix}_{pos_name}_long_pass_success"] = -1.0
                features[f"{prefix}_{pos_name}_cross_success"] = -1.0
                features[f"{prefix}_{pos_name}_through_ball_success"] = -1.0

        return features

    def _group_players_by_position(self, players: list[PlayerStats]) -> dict[str, list[PlayerStats]]:
        """
        按关键位置分组球员

        Args:
            players: 球员列表

        Returns:
            位置到球员列表的映射
        """
        position_players = {
            "gk": [],
            "libero": [],
            "carrier": [],
            "creator": [],
            "winger": [],
        }

        for player in players:
            jersey_num = player.jersey_number

            # 根据球衣号码分配位置
            if jersey_num in self.config.KEY_POSITIONS["gk"]:
                position_players["gk"].append(player)
            elif jersey_num in self.config.KEY_POSITIONS["libero"]:
                position_players["libero"].append(player)
            elif jersey_num in self.config.KEY_POSITIONS["carrier"]:
                position_players["carrier"].append(player)
            elif jersey_num in self.config.KEY_POSITIONS["creator"]:
                position_players["creator"].append(player)
            elif jersey_num in self.config.KEY_POSITIONS["winger"]:
                position_players["winger"].append(player)
            # 其他号码归入 carrier（默认中场）
            elif jersey_num and jersey_num > 0:
                position_players["carrier"].append(player)

        return position_players

    def _compute_position_cross_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算位置交叉特征（V23.0 扩展）

        包括:
            - 后场出球能力（gk + libero 长传）
            - 中场推进能力（carrier + creator 直塞）
            - 边路传中威胁（winger 传中）
        """
        cross_features = {}

        for prefix in ["home", "away"]:
            # 后场出球能力（gk 和 libero 的长传总数）
            gk_long = features.get(f"{prefix}_gk_long_passes", 0)
            libero_long = features.get(f"{prefix}_libero_long_passes", 0)
            cross_features[f"{prefix}_backline_long_passes"] = gk_long + libero_long

            # 后场出球成功率
            gk_long_acc = features.get(f"{prefix}_gk_long_pass_success", 0)
            libero_long_acc = features.get(f"{prefix}_libero_long_pass_success", 0)
            valid_gk = 1 if gk_long_acc >= 0 else 0
            valid_libero = 1 if libero_long_acc >= 0 else 0
            if valid_gk + valid_libero > 0:
                cross_features[f"{prefix}_backline_long_success"] = round(
                    (gk_long_acc * valid_gk + libero_long_acc * valid_libero) / (valid_gk + valid_libero), 2
                )
            else:
                cross_features[f"{prefix}_backline_long_success"] = -1.0

            # 中场推进能力（carrier 和 creator 的直塞球）
            carrier_through = features.get(f"{prefix}_carrier_through_balls", 0)
            creator_through = features.get(f"{prefix}_creator_through_balls", 0)
            cross_features[f"{prefix}_midfield_through_balls"] = carrier_through + creator_through

            # 边路传中威胁（winger 传中总数）
            winger_cross = features.get(f"{prefix}_winger_crosses", 0)
            cross_features[f"{prefix}_flank_crossing_threat"] = winger_cross

            # 核心创造者评分（creator 的综合创造能力）
            creator_final_third = features.get(f"{prefix}_creator_final_third_passes", 0)
            creator_key_passes = features.get(f"{prefix}_creator_key_passes", 0)  # 需要添加这个字段
            cross_features[f"{prefix}_creator_rating"] = round(creator_final_third + creator_key_passes * 2, 2)

        # 主客队对比
        cross_features["diff_backline_long_passes"] = round(
            cross_features.get("home_backline_long_passes", 0) - cross_features.get("away_backline_long_passes", 0), 2
        )
        cross_features["diff_midfield_through_balls"] = round(
            cross_features.get("home_midfield_through_balls", 0) - cross_features.get("away_midfield_through_balls", 0),
            2,
        )
        cross_features["diff_flank_crossing_threat"] = round(
            cross_features.get("home_flank_crossing_threat", 0) - cross_features.get("away_flank_crossing_threat", 0), 2
        )

        return cross_features

    def _calculate_basic_passing(self, players: list) -> dict[str, float]:
        """计算基础传球统计"""
        total_passes = 0
        accurate_passes = 0
        key_passes = 0
        chances_created = 0

        for player in players:
            if isinstance(player, dict):
                stats = player.get("stats", player)
            else:
                stats = player

            total_passes += (
                getattr(stats, "accurate_passes", 0)
                + getattr(stats, "total_passes", getattr(stats, "totalPasses", 0)) // 2
            )
            accurate_passes += getattr(stats, "accurate_passes", getattr(stats, "accuratePasses", 0))
            key_passes += getattr(stats, "key_passes", getattr(stats, "keyPasses", 0))
            chances_created += getattr(stats, "big_chances_created", getattr(stats, "bigChancesCreated", 0))

        pass_accuracy = (accurate_passes / total_passes * 100) if total_passes > 0 else 0.0

        return {
            "total_passes": float(total_passes),
            "accurate_passes": float(accurate_passes),
            "pass_accuracy": round(pass_accuracy, 2),
            "key_passes": float(key_passes),
            "chances_created": float(chances_created),
        }

    def _analyze_zone_passing(self, players: list, prefix: str) -> dict[str, float]:
        """分析区域传球特征"""
        features = {}
        final_total = final_acc = middle_total = middle_acc = defensive_total = defensive_acc = 0

        for player in players:
            if isinstance(player, dict):
                stats = player.get("stats", player)
            else:
                stats = player

            final_total += getattr(stats, "final_third_passes", 0)
            final_acc += getattr(stats, "accurate_final_third_passes", 0)
            middle_total += getattr(stats, "middle_third_passes", 0)
            middle_acc += getattr(stats, "accurate_middle_third_passes", 0)
            defensive_total += getattr(stats, "defensive_third_passes", 0)
            defensive_acc += getattr(stats, "accurate_defensive_third_passes", 0)

        features[f"{prefix}_final_third_pass_acc"] = round(
            final_acc / final_total * 100 if final_total >= 5 else -1.0, 2
        )
        features[f"{prefix}_final_third_total"] = float(final_total)
        features[f"{prefix}_middle_third_pass_acc"] = round(
            middle_acc / middle_total * 100 if middle_total >= 5 else -1.0, 2
        )
        features[f"{prefix}_defensive_third_pass_acc"] = round(
            defensive_acc / defensive_total * 100 if defensive_total >= 5 else -1.0, 2
        )

        total_zones = final_total + middle_total + defensive_total
        features[f"{prefix}_offensive_zone_ratio"] = round(final_total / total_zones if total_zones > 0 else 0.0, 4)

        return features

    def _analyze_passing_dna(self, players: list, prefix: str) -> dict[str, float]:
        """分析传球 DNA"""
        features = {}
        short = medium = long = long_acc = 0

        for player in players:
            if isinstance(player, dict):
                stats = player.get("stats", player)
            else:
                stats = player

            short += getattr(stats, "short_passes", 0)
            medium += getattr(stats, "medium_passes", 0)
            long += getattr(stats, "long_passes", 0)
            long_acc += getattr(stats, "accurate_long_passes", 0)

        total = short + medium + long
        if total > 0:
            features[f"{prefix}_short_pass_ratio"] = round(short / total, 4)
            features[f"{prefix}_medium_pass_ratio"] = round(medium / total, 4)
            features[f"{prefix}_long_pass_ratio"] = round(long / total, 4)
        else:
            features[f"{prefix}_short_pass_ratio"] = 0.0
            features[f"{prefix}_medium_pass_ratio"] = 0.0
            features[f"{prefix}_long_pass_ratio"] = 0.0

        features[f"{prefix}_long_pass_success"] = round(long_acc / long * 100 if long >= 5 else -1.0, 2)

        ratios = [
            features.get(f"{prefix}_short_pass_ratio", 0),
            features.get(f"{prefix}_medium_pass_ratio", 0),
            features.get(f"{prefix}_long_pass_ratio", 0),
        ]
        features[f"{prefix}_passing_entropy"] = round(self._calculate_entropy(ratios), 4)

        return features

    def _analyze_crossing(self, players: list, prefix: str) -> dict[str, float]:
        """分析传中特征"""
        features = {}
        total = accurate = 0

        for player in players:
            if isinstance(player, dict):
                stats = player.get("stats", player)
            else:
                stats = player

            total += getattr(stats, "crosses", 0)
            accurate += getattr(stats, "accurate_crosses", 0)

        features[f"{prefix}_cross_accuracy"] = round(accurate / total * 100 if total >= 3 else -1.0, 2)
        features[f"{prefix}_cross_total"] = float(total)

        return features

    def _analyze_through_balls(self, players: list, prefix: str) -> dict[str, float]:
        """分析直塞球特征"""
        features = {}
        through = acc_through = key_passes = big_chances = 0

        for player in players:
            if isinstance(player, dict):
                stats = player.get("stats", player)
            else:
                stats = player

            through += getattr(stats, "through_balls", 0)
            acc_through += getattr(stats, "accurate_through_balls", 0)
            key_passes += getattr(stats, "key_passes", 0)
            big_chances += getattr(stats, "big_chances_created", 0)

        features[f"{prefix}_through_ball_acc"] = round(acc_through / through * 100 if through >= 2 else -1.0, 2)
        features[f"{prefix}_through_ball_total"] = float(through)
        features[f"{prefix}_key_pass_count"] = float(key_passes)
        features[f"{prefix}_big_chances_created"] = float(big_chances)

        return features

    def _analyze_vertical_progression(self, players: list, prefix: str) -> dict[str, float]:
        """分析纵向推进特征"""
        features = {}
        forward = backward = vertical = 0

        for player in players:
            if isinstance(player, dict):
                stats = player.get("stats", player)
            else:
                stats = player

            forward += getattr(stats, "forward_passes", 0)
            backward += getattr(stats, "backward_passes", 0)
            vertical += getattr(stats, "vertical_progression", 0)

        total_dir = forward + backward
        if total_dir > 0:
            features[f"{prefix}_forward_pass_ratio"] = round(forward / total_dir, 4)
            features[f"{prefix}_backward_pass_ratio"] = round(backward / total_dir, 4)
        else:
            features[f"{prefix}_forward_pass_ratio"] = 0.0
            features[f"{prefix}_backward_pass_ratio"] = 0.0

        features[f"{prefix}_vertical_progression"] = round(vertical, 2)
        features[f"{prefix}_aggression_index"] = round(forward / backward if backward > 0 else float(forward), 2)

        return features

    def _calculate_entropy(self, ratios: list) -> float:
        """计算熵"""
        import math

        entropy = 0.0
        for r in ratios:
            if r > 0:
                entropy -= r * math.log(r)
        return entropy

    def _compute_comparison_features(self, features: dict[str, float]) -> dict[str, float]:
        """计算对比特征"""
        comparison = {}

        # 传球成功率对比
        home_acc = features.get("home_pass_accuracy", 0)
        away_acc = features.get("away_pass_accuracy", 0)
        comparison["diff_pass_accuracy"] = round(home_acc - away_acc, 2)

        # 进攻三区传球对比
        home_final = features.get("home_final_third_pass_acc", -1)
        away_final = features.get("away_final_third_pass_acc", -1)
        if home_final >= 0 and away_final >= 0:
            comparison["diff_final_third_pass_acc"] = round(home_final - away_final, 2)
        else:
            comparison["diff_final_third_pass_acc"] = 0.0

        # 长传能力对比
        home_long = features.get("home_long_pass_success", -1)
        away_long = features.get("away_long_pass_success", -1)
        if home_long >= 0 and away_long >= 0:
            comparison["diff_long_pass_success"] = round(home_long - away_long, 2)
        else:
            comparison["diff_long_pass_success"] = 0.0

        # 纵向推进对比
        home_vertical = features.get("home_vertical_progression", 0)
        away_vertical = features.get("away_vertical_progression", 0)
        comparison["diff_vertical_progression"] = round(home_vertical - away_vertical, 2)

        return comparison

    def _get_default_features(self, prefix: str) -> dict[str, float]:
        """获取默认特征值"""
        return {
            f"{prefix}_total_passes": 0.0,
            f"{prefix}_pass_accuracy": 0.0,
            f"{prefix}_final_third_pass_acc": -1.0,
            f"{prefix}_final_third_total": 0.0,
            f"{prefix}_offensive_zone_ratio": 0.0,
            f"{prefix}_short_pass_ratio": 0.0,
            f"{prefix}_long_pass_ratio": 0.0,
            f"{prefix}_long_pass_success": -1.0,
            f"{prefix}_passing_entropy": 0.0,
            f"{prefix}_cross_accuracy": -1.0,
            f"{prefix}_cross_total": 0.0,
            f"{prefix}_through_ball_acc": -1.0,
            f"{prefix}_through_ball_total": 0.0,
            f"{prefix}_key_pass_count": 0.0,
            f"{prefix}_big_chances_created": 0.0,
            f"{prefix}_forward_pass_ratio": 0.0,
            f"{prefix}_vertical_progression": 0.0,
            f"{prefix}_aggression_index": 0.0,
        }

    def get_feature_schema(self) -> dict[str, type]:
        """
        获取输出特征的 Schema（V23.0 动态生成）

        使用 Python 循环动态生成 210+ 维特征的定义
        """
        schema = {
            # 聚合特征
            "home_total_passes": float,
            "away_total_passes": float,
            "home_pass_accuracy": float,
            "away_pass_accuracy": float,
            "diff_pass_accuracy": float,
            "home_final_third_pass_acc": float,
            "away_final_third_pass_acc": float,
            "diff_final_third_pass_acc": float,
            "home_offensive_zone_ratio": float,
            "home_short_pass_ratio": float,
            "home_long_pass_ratio": float,
            "home_long_pass_success": float,
            "home_passing_entropy": float,
            "home_cross_accuracy": float,
            "home_through_ball_acc": float,
            "home_vertical_progression": float,
            "home_aggression_index": float,
        }

        # V23.0: 动态生成位置原子化特征 Schema（150 维）
        for prefix in ["home", "away"]:
            for pos in ["gk", "libero", "carrier", "creator", "winger"]:
                # 15 个传球指标
                for field in POSITION_PASSING_FIELDS:
                    schema[f"{prefix}_{pos}_{field}"] = float
                # 额外的成功率特征
                schema[f"{prefix}_{pos}_pass_accuracy"] = float
                schema[f"{prefix}_{pos}_long_pass_success"] = float
                schema[f"{prefix}_{pos}_cross_success"] = float
                schema[f"{prefix}_{pos}_through_ball_success"] = float

        # 位置交叉特征
        for prefix in ["home", "away"]:
            schema[f"{prefix}_backline_long_passes"] = float
            schema[f"{prefix}_backline_long_success"] = float
            schema[f"{prefix}_midfield_through_balls"] = float
            schema[f"{prefix}_flank_crossing_threat"] = float
            schema[f"{prefix}_creator_rating"] = float

        schema["diff_backline_long_passes"] = float
        schema["diff_midfield_through_balls"] = float
        schema["diff_flank_crossing_threat"] = float

        return schema
