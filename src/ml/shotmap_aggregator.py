#!/usr/bin/env python3
"""
V20.6 ShotmapAggregator - 全量射门数据合成引擎
================================================

核心功能:
1. 从 shotmap.Periods 解析原始射门事件数据
2. 聚合计算: total_shots, sum_expected_goals, avg_distance, shots_on_target_count
3. 区分主队/客队，生成合成特征字段
4. 动量提取: peak_value, volatility
5. 球员明细聚合: accuratePasses, touches 等核心指标

使用场景:
- 当 content.stats 缺失半场数据时，使用 shotmap 数据合成回填
- 确保 21/22 等历史赛季具备 600+ 维特征

作者: Top Quant Data Architect
日期: 2025-12-24
版本: V20.6
"""

from dataclasses import dataclass
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ShotmapMetrics:
    """射门聚合指标"""

    total_shots: int = 0
    sum_expected_goals: float = 0.0
    avg_distance: float = 0.0
    shots_on_target_count: int = 0
    big_chance_count: int = 0
    shots_inside_box: int = 0
    shots_outside_box: int = 0

    # 动量指标
    peak_xg: float = 0.0
    peak_minute: int = 0
    volatility: float = 0.0  # xG 标准差


class ShotmapAggregator:
    """
    V20.7 射门数据聚合器 - 全量合成全息矩阵核心组件

    核心算法:
    1. 解析 shotmap.Periods[All/FirstHalf/SecondHalf] 数组
    2. 按 teamId 分类计算主客队指标
    3. 生成合成特征: home_FH_synth_xg, away_SH_synth_shots 等
    4. 提取动量特征: 峰值、波动率
    5. 【V20.7】点球 xG 锁死逻辑: Penalty xG = 0.789
    """

    # 时段映射
    PERIOD_MAP = {
        "All": "all",
        "FirstHalf": "FH",
        "SecondHalf": "SH",
    }

    # V20.7 点球精度锁定值
    PENALTY_XG_LOCKED = 0.789

    def __init__(self, home_team_id: int, away_team_id: int):
        """
        Args:
            home_team_id: 主队 FotMob ID
            away_team_id: 客队 FotMob ID
        """
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id

    def extract_shotmap_periods(self, content: dict) -> dict[str, list]:
        """
        从 content 中提取 shotmap.Periods 数据

        Args:
            content: FotMob API 响应的 content 字段

        Returns:
            {'All': [...], 'FirstHalf': [...], 'SecondHalf': [...]}
        """
        periods_data = {"All": [], "FirstHalf": [], "SecondHalf": []}

        shotmap = content.get("shotmap", {})
        periods = shotmap.get("Periods", {})

        if not periods:
            logger.debug("No shotmap.Periods found")
            return periods_data

        for period_name in ["All", "FirstHalf", "SecondHalf"]:
            period_events = periods.get(period_name, [])
            if isinstance(period_events, list):
                periods_data[period_name] = period_events
                logger.debug(f"Found {len(period_events)} shots in {period_name}")

        return periods_data

    def aggregate_period(self, shots: list[dict], team_id: int) -> ShotmapMetrics:
        """
        聚合单支球队在单个时段的射门数据

        Args:
            shots: 射门事件数组
            team_id: 球队ID（用于过滤）

        Returns:
            ShotmapMetrics 聚合指标
        """
        metrics = ShotmapMetrics()

        # 过滤该球队的射门
        team_shots = [s for s in shots if s.get("teamId") == team_id]

        if not team_shots:
            return metrics

        metrics.total_shots = len(team_shots)

        # 计算 xG 总和
        xg_values = []
        distances = []

        for shot in team_shots:
            # V20.7 点球 xG 锁死逻辑
            situation = shot.get("situation", "")
            if situation == "Penalty":
                # 点球 xG 强制锁定为 0.789，确保与官方统计口径对齐
                xg = self.PENALTY_XG_LOCKED
            else:
                xg = shot.get("expectedGoals", 0) or 0

            metrics.sum_expected_goals += xg
            if xg > 0:
                xg_values.append(xg)

            # 射正计数 (排除被封堵的射门，与官方统计口径对齐)
            # 点球只有在非Blocked且OnTarget时才计入射正
            is_blocked = shot.get("isBlocked", False)
            is_on_target = shot.get("isOnTarget", False)

            if is_on_target and not is_blocked:
                metrics.shots_on_target_count += 1

            # 大机会计数 (xG >= 0.1)
            if xg >= 0.1:
                metrics.big_chance_count += 1

            # 距离计算 (基于球场坐标)
            x = shot.get("x", 0) or 0
            y = shot.get("y", 0) or 0
            # 假设球门位置在 (100, 34)，计算欧几里得距离
            distance = np.sqrt((100 - x) ** 2 + (34 - y) ** 2)
            distances.append(distance)

        # 平均距离
        if distances:
            metrics.avg_distance = np.mean(distances)

        # 动量指标
        if xg_values:
            metrics.peak_xg = max(xg_values)

            # 找到峰值时间
            for shot in team_shots:
                if shot.get("expectedGoals", 0) == metrics.peak_xg:
                    metrics.peak_minute = shot.get("min", 0)
                    break

            # 波动率 (标准差)
            if len(xg_values) > 1:
                metrics.volatility = np.std(xg_values)

        return metrics

    def synthesize_period_features(self, shots: list[dict], period_name: str) -> dict[str, Any]:
        """
        合成单个时段的特征

        生成的特征命名:
        - home_FH_synth_total_shots
        - home_FH_synth_xg
        - home_FH_synth_avg_distance
        - home_FH_synth_shots_on_target
        - home_FH_synth_big_chances
        - home_FH_synth_peak_xg
        - home_FH_synth_peak_minute
        - home_FH_synth_volatility

        Args:
            shots: 射门事件数组
            period_name: 时段名称 (All/FirstHalf/SecondHalf)

        Returns:
            合成特征字典
        """
        features = {}
        period_code = self.PERIOD_MAP.get(period_name, "unknown")

        # 聚合主队数据
        home_metrics = self.aggregate_period(shots, self.home_team_id)
        away_metrics = self.aggregate_period(shots, self.away_team_id)

        # 生成主队特征
        features[f"home_{period_code}_synth_total_shots"] = home_metrics.total_shots
        features[f"home_{period_code}_synth_xg"] = round(home_metrics.sum_expected_goals, 3)
        features[f"home_{period_code}_synth_avg_distance"] = round(home_metrics.avg_distance, 2)
        features[f"home_{period_code}_synth_shots_on_target"] = home_metrics.shots_on_target_count
        features[f"home_{period_code}_synth_big_chances"] = home_metrics.big_chance_count
        features[f"home_{period_code}_synth_peak_xg"] = round(home_metrics.peak_xg, 3)
        features[f"home_{period_code}_synth_peak_minute"] = home_metrics.peak_minute
        features[f"home_{period_code}_synth_volatility"] = round(home_metrics.volatility, 4)

        # 生成客队特征
        features[f"away_{period_code}_synth_total_shots"] = away_metrics.total_shots
        features[f"away_{period_code}_synth_xg"] = round(away_metrics.sum_expected_goals, 3)
        features[f"away_{period_code}_synth_avg_distance"] = round(away_metrics.avg_distance, 2)
        features[f"away_{period_code}_synth_shots_on_target"] = away_metrics.shots_on_target_count
        features[f"away_{period_code}_synth_big_chances"] = away_metrics.big_chance_count
        features[f"away_{period_code}_synth_peak_xg"] = round(away_metrics.peak_xg, 3)
        features[f"away_{period_code}_synth_peak_minute"] = away_metrics.peak_minute
        features[f"away_{period_code}_synth_volatility"] = round(away_metrics.volatility, 4)

        # 生成差值特征
        features[f"diff_{period_code}_synth_total_shots"] = (
            home_metrics.total_shots - away_metrics.total_shots
        )
        features[f"diff_{period_code}_synth_xg"] = round(
            home_metrics.sum_expected_goals - away_metrics.sum_expected_goals, 3
        )
        features[f"diff_{period_code}_synth_shots_on_target"] = (
            home_metrics.shots_on_target_count - away_metrics.shots_on_target_count
        )
        features[f"diff_{period_code}_synth_big_chances"] = (
            home_metrics.big_chance_count - away_metrics.big_chance_count
        )

        # 生成总计特征
        features[f"total_{period_code}_synth_total_shots"] = (
            home_metrics.total_shots + away_metrics.total_shots
        )
        features[f"total_{period_code}_synth_xg"] = round(
            home_metrics.sum_expected_goals + away_metrics.sum_expected_goals, 3
        )

        return features

    def synthesize_all_features(self, content: dict) -> dict[str, Any]:
        """
        合成所有时段的特征 (All + FirstHalf + SecondHalf)

        Args:
            content: FotMob API 响应的 content 字段

        Returns:
            完整合成特征字典
        """
        all_features = {}

        # 提取 shotmap 数据
        periods_data = self.extract_shotmap_periods(content)

        # 如果没有任何数据，返回空字典
        total_shots = sum(len(shots) for shots in periods_data.values())
        if total_shots == 0:
            logger.warning("No shotmap data found for synthesis")
            return all_features

        # 为每个时段合成特征
        for period_name in ["All", "FirstHalf", "SecondHalf"]:
            shots = periods_data.get(period_name, [])
            if shots:
                period_features = self.synthesize_period_features(shots, period_name)
                all_features.update(period_features)
                logger.debug(
                    f"Synthesized {len(period_features)} features for {period_name} ({len(shots)} shots)"
                )

        logger.info(f"🎯 ShotmapAggregator: Synthesized {len(all_features)} features")
        return all_features


class PlayerStatsExtractor:
    """
    V20.6 球员明细聚合器 - 压榨最后的 5% 特征

    核心功能:
    1. 提取每个球员的 accuratePasses, touches 等核心指标
    2. 按位置聚合 (GK/DF/MF/FW)
    3. 生成位置战力特征
    """

    # 核心球员指标
    CORE_PLAYER_STATS = [
        "accuratePasses",
        "touches",
        "totalPasses",
        "accurateLongBalls",
        "accurateCrosses",
        "aerialsWon",
        "tackles",
        "interceptions",
        "clearances",
        "dribblesSucceeded",
        "keyPasses",
        "bigChanceCreated",
    ]

    def __init__(self):
        pass

    def extract_player_stats(self, content: dict) -> dict[str, Any]:
        """
        从 content 中提取球员统计数据

        Args:
            content: FotMob API 响应的 content 字段

        Returns:
            球员聚合特征字典
        """
        features = {}

        # 从 stats 中提取球员数据
        stats = content.get("stats", [])
        if not stats:
            return features

        # 查找包含球员数据的 stats 组
        for stat_group in stats:
            # 跳过非字典类型
            if not isinstance(stat_group, dict):
                continue
            stats_data = stat_group.get("stats", [])
            if not isinstance(stats_data, list):
                continue

            # 查找球员相关统计
            for stat_item in stats_data:
                stat_key = stat_item.get("key", "").lower()

                # 检查是否是核心球员指标
                if any(core.lower() in stat_key for core in self.CORE_PLAYER_STATS):
                    values = stat_item.get("stats", [])
                    if len(values) >= 2:
                        home_val = values[0]
                        away_val = values[1]

                        # 生成特征
                        normalized_key = self._normalize_key(stat_key)
                        features[f"home_player_{normalized_key}"] = home_val
                        features[f"away_player_{normalized_key}"] = away_val
                        features[f"diff_player_{normalized_key}"] = (
                            home_val - away_val
                            if isinstance(home_val, (int, float))
                            and isinstance(away_val, (int, float))
                            else None
                        )
                        features[f"total_player_{normalized_key}"] = (
                            home_val + away_val
                            if isinstance(home_val, (int, float))
                            and isinstance(away_val, (int, float))
                            else None
                        )

        logger.info(f"👤 PlayerStatsExtractor: Extracted {len(features)} player stats")
        return features

    def _normalize_key(self, key: str) -> str:
        """标准化特征键名"""
        return key.lower().replace(" ", "_").replace("-", "_")


class MomentumExtractor:
    """
    V20.6 动量提取器 - 提取比赛动量曲线特征

    核心功能:
    1. 提取 momentum 数据的 peak_value (峰值)
    2. 计算 volatility (波动率)
    3. 生成动量强度特征
    """

    def extract_momentum_features(self, content: dict) -> dict[str, Any]:
        """
        从 content 中提取动量特征

        Args:
            content: FotMob API 响应的 content 字段

        Returns:
            动量特征字典
        """
        features = {}

        # 查找 momentum 数据
        momentum = content.get("momentum", {})
        if not momentum:
            return features

        # 提取主客队动量数据
        home_momentum = momentum.get("home", [])
        away_momentum = momentum.get("away", [])

        if home_momentum:
            home_values = [m.get("value", 0) for m in home_momentum if isinstance(m, dict)]
            if home_values:
                features["home_momentum_peak"] = max(home_values)
                features["home_momentum_avg"] = round(np.mean(home_values), 2)
                if len(home_values) > 1:
                    features["home_momentum_volatility"] = round(np.std(home_values), 4)
                features["home_momentum_range"] = round(max(home_values) - min(home_values), 2)

        if away_momentum:
            away_values = [m.get("value", 0) for m in away_momentum if isinstance(m, dict)]
            if away_values:
                features["away_momentum_peak"] = max(away_values)
                features["away_momentum_avg"] = round(np.mean(away_values), 2)
                if len(away_values) > 1:
                    features["away_momentum_volatility"] = round(np.std(away_values), 4)
                features["away_momentum_range"] = round(max(away_values) - min(away_values), 2)

        # 差值特征
        if "home_momentum_peak" in features and "away_momentum_peak" in features:
            features["diff_momentum_peak"] = round(
                features["home_momentum_peak"] - features["away_momentum_peak"], 2
            )

        logger.info(f"📈 MomentumExtractor: Extracted {len(features)} momentum features")
        return features


def synthesize_v20_6_features(
    content: dict, home_team_id: int, away_team_id: int
) -> dict[str, Any]:
    """
    V20.6 全量特征合成 - 统一入口

    Args:
        content: FotMob API 响应的 content 字段
        home_team_id: 主队 FotMob ID
        away_team_id: 客队 FotMob ID

    Returns:
        合成特征字典 (包含 shotmap, player stats, momentum)
    """
    all_features = {}

    # 1. Shotmap 合成特征
    shotmap_aggregator = ShotmapAggregator(home_team_id, away_team_id)
    shotmap_features = shotmap_aggregator.synthesize_all_features(content)
    all_features.update(shotmap_features)

    # 2. 球员明细特征
    player_extractor = PlayerStatsExtractor()
    player_features = player_extractor.extract_player_stats(content)
    all_features.update(player_features)

    # 3. 动量特征
    momentum_extractor = MomentumExtractor()
    momentum_features = momentum_extractor.extract_momentum_features(content)
    all_features.update(momentum_features)

    logger.info(f"🚀 V20.6 Synthesis: Total {len(all_features)} features synthesized")
    return all_features


# ==================== 测试代码 ====================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 测试用例：读取实际数据
    import json

    test_file = (
        "/home/user/projects/FootballPrediction/data/backfill_stats/raw_json_match_3609929.json"
    )
    with open(test_file) as f:
        data = json.load(f)

    content = data.get("content", {})

    # 获取主客队 ID (从 general 中提取)
    general = data.get("general", {})
    home_team_id = general.get("homeTeam", {}).get("id", 0)
    away_team_id = general.get("awayTeam", {}).get("id", 0)


    # 执行合成
    features = synthesize_v20_6_features(content, home_team_id, away_team_id)


    # 按前缀分类统计
    feature_categories = {}
    for key in features:
        prefix = key.split("_")[0] if "_" in key else "other"
        feature_categories[prefix] = feature_categories.get(prefix, 0) + 1

    for _category, _count in sorted(feature_categories.items()):
        pass

    # 显示部分特征
    critical_keys = [k for k in features if "synth" in k][:10]
    for key in critical_keys:
        pass
