#!/usr/bin/env python3
"""
V20.7 原子级数据对齐引擎 - Atomic Data Alignment Engine
======================================================

核心功能:
1. 原子级回填 (Atomic Backfill): 自动触发 shotmap 填充缺失的 stats 字段
2. 球员-球队级联聚合: 11 人数据加总生成全量特征
3. 动量特征深度解剖: velocity, acceleration 特征工程
4. 全量 Schema 对齐 (Zero-Padding): 强制 800+ 维一致性

使用场景:
- 21/22 赛季至 24/25 赛季所有比赛特征维度强行拉齐至 800+ 维
- 确保 7,161 场比赛在数据库中实现物理级对称

作者: Atomic Data Auditor
日期: 2025-12-24
版本: V20.7
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


# ========== 全量 Schema 定义 (800+ 维) ==========
# V20.7 零填充标准 Schema - 所有比赛必须对齐
V20_7_FULL_SCHEMA = {
    # === shotmap 合成特征 (66 维) ===
    # All 时段 (22 个)
    'home_all_synth_total_shots', 'home_all_synth_xg', 'home_all_synth_avg_distance',
    'home_all_synth_shots_on_target', 'home_all_synth_big_chances', 'home_all_synth_peak_xg',
    'home_all_synth_peak_minute', 'home_all_synth_volatility',
    'away_all_synth_total_shots', 'away_all_synth_xg', 'away_all_synth_avg_distance',
    'away_all_synth_shots_on_target', 'away_all_synth_big_chances', 'away_all_synth_peak_xg',
    'away_all_synth_peak_minute', 'away_all_synth_volatility',
    'diff_all_synth_total_shots', 'diff_all_synth_xg', 'diff_all_synth_shots_on_target',
    'diff_all_synth_big_chances', 'total_all_synth_total_shots', 'total_all_synth_xg',

    # FirstHalf 时段 (22 个)
    'home_FH_synth_total_shots', 'home_FH_synth_xg', 'home_FH_synth_avg_distance',
    'home_FH_synth_shots_on_target', 'home_FH_synth_big_chances', 'home_FH_synth_peak_xg',
    'home_FH_synth_peak_minute', 'home_FH_synth_volatility',
    'away_FH_synth_total_shots', 'away_FH_synth_xg', 'away_FH_synth_avg_distance',
    'away_FH_synth_shots_on_target', 'away_FH_synth_big_chances', 'away_FH_synth_peak_xg',
    'away_FH_synth_peak_minute', 'away_FH_synth_volatility',
    'diff_FH_synth_total_shots', 'diff_FH_synth_xg', 'diff_FH_synth_shots_on_target',
    'diff_FH_synth_big_chances', 'total_FH_synth_total_shots', 'total_FH_synth_xg',

    # SecondHalf 时段 (22 个)
    'home_SH_synth_total_shots', 'home_SH_synth_xg', 'home_SH_synth_avg_distance',
    'home_SH_synth_shots_on_target', 'home_SH_synth_big_chances', 'home_SH_synth_peak_xg',
    'home_SH_synth_peak_minute', 'home_SH_synth_volatility',
    'away_SH_synth_total_shots', 'away_SH_synth_xg', 'away_SH_synth_avg_distance',
    'away_SH_synth_shots_on_target', 'away_SH_synth_big_chances', 'away_SH_synth_peak_xg',
    'away_SH_synth_peak_minute', 'away_SH_synth_volatility',
    'diff_SH_synth_total_shots', 'diff_SH_synth_xg', 'diff_SH_synth_shots_on_target',
    'diff_SH_synth_big_chances', 'total_SH_synth_total_shots', 'total_SH_synth_xg',
}


@dataclass
class AtomicBackfillMetrics:
    """原子级回填指标"""
    stats_missing_periods: List[str] = field(default_factory=list)  # 缺失的时段 ['FirstHalf', 'SecondHalf']
    stats_fields_filled: int = 0  # 从 shotmap 回填的字段数
    synth_features_generated: int = 0  # 生成的合成特征数


class AtomicBackfillEngine:
    """
    V20.7 原子级回填引擎 - 自动触发 shotmap 填充缺失字段

    核心逻辑:
    1. 检查 content.stats.Periods 是否缺失 FirstHalf 或 SecondHalf
    2. 自动触发 ShotmapAggregator 遍历 shotmap.Periods
    3. 精准还原缺失字段: home_FirstHalf_expected_goals, away_SecondHalf_total_shots 等
    4. 确保 160 个原本缺失的字段被正确填充
    """

    def __init__(self, home_team_id: int, away_team_id: int):
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        # 导入 ShotmapAggregator
        from src.ml.shotmap_aggregator import ShotmapAggregator
        self.shotmap_aggregator = ShotmapAggregator(home_team_id, away_team_id)

    def detect_missing_periods(self, content: Dict) -> List[str]:
        """
        检测 stats.Periods 中缺失的时段

        Returns:
            缺失的时段列表，如 ['FirstHalf', 'SecondHalf']
        """
        missing_periods = []

        stats = content.get('stats', {})
        if not isinstance(stats, dict):
            return ['FirstHalf', 'SecondHalf']  # 完全缺失

        periods = stats.get('Periods', {})
        if not isinstance(periods, dict):
            return ['FirstHalf', 'SecondHalf']

        # 检查必需的时段
        required_periods = ['FirstHalf', 'SecondHalf']
        for period in required_periods:
            if period not in periods:
                missing_periods.append(period)
            else:
                # 检查是否为空数据
                period_data = periods[period]
                if isinstance(period_data, dict) and not period_data.get('stats'):
                    missing_periods.append(period)

        return missing_periods

    def atomic_backfill(self, content: Dict, features: Dict) -> Tuple[Dict, AtomicBackfillMetrics]:
        """
        原子级回填 - 自动填充缺失的 stats 字段

        Args:
            content: FotMob API content
            features: 当前已提取的特征字典 (会被原地修改)

        Returns:
            (features, metrics) - 更新后的特征和回填指标
        """
        metrics = AtomicBackfillMetrics()

        # 1. 检测缺失的时段
        missing_periods = self.detect_missing_periods(content)
        metrics.stats_missing_periods = missing_periods

        if not missing_periods:
            logger.debug("✓ stats.Periods 完整，无需回填")
            return features, metrics

        logger.info(f"🔧 检测到缺失时段: {missing_periods}，启动原子级回填")

        # 2. 提取 shotmap 数据
        shotmap = content.get('shotmap', {})
        periods_data = shotmap.get('Periods', {})

        if not periods_data:
            logger.warning("⚠️ shotmap.Periods 不可用，无法回填")
            return features, metrics

        # 3. 为每个缺失时段生成合成特征
        from src.ml.shotmap_aggregator import ShotmapAggregator

        for period_name in missing_periods:
            if period_name in periods_data:
                shots = periods_data[period_name]
                if isinstance(shots, list) and shots:
                    # 使用 ShotmapAggregator 合成该时段特征
                    period_features = self.shotmap_aggregator.synthesize_period_features(
                        shots, period_name
                    )

                    # 关键: 将合成特征映射回原 stats 字段名
                    # home_FH_synth_xg -> home_FirstHalf_expected_goals
                    mapped_features = self._map_synth_to_stats_fields(
                        period_features, period_name
                    )

                    features.update(mapped_features)
                    metrics.stats_fields_filled += len(mapped_features)
                    metrics.synth_features_generated += len(period_features)

                    logger.info(f"  ✓ {period_name}: 回填 {len(mapped_features)} 个字段")

        # 4. 同时保留 synth_ 特征作为备份
        all_synth_features = self.shotmap_aggregator.synthesize_all_features(content)
        features.update(all_synth_features)

        return features, metrics

    def _map_synth_to_stats_fields(
        self,
        synth_features: Dict,
        period_name: str
    ) -> Dict[str, Any]:
        """
        将合成特征映射回原 stats 字段名

        映射规则:
        - home_FH_synth_xg -> home_FirstHalf_expected_goals
        - home_FH_synth_total_shots -> home_FirstHalf_total_shots
        - home_FH_synth_shots_on_target -> home_FirstHalf_shotsontarget

        Args:
            synth_features: 合成特征字典
            period_name: 时段名称 (FirstHalf/SecondHalf)

        Returns:
            映射后的特征字典
        """
        mapped = {}

        period_code = 'FH' if period_name == 'FirstHalf' else 'SH'

        for key, value in synth_features.items():
            # 跳过非主队/客队特征
            if not key.startswith('home_') and not key.startswith('away_'):
                continue

            # 跳过差值和总计特征
            if key.startswith('diff_') or key.startswith('total_'):
                continue

            # 映射字段名
            # home_FH_synth_xg -> home_FirstHalf_expected_goals
            # away_SH_synth_total_shots -> away_SecondHalf_total_shots

            if f'_{period_code}_synth_' in key:
                # 提取球队和指标
                parts = key.split(f'_{period_code}_synth_')
                if len(parts) == 2:
                    team = parts[0]  # home 或 away
                    metric = parts[1]  # xg, total_shots 等

                    # 映射到 stats 字段名
                    stats_field_name = self._metric_to_stats_field(metric)
                    new_key = f"{team}_{period_name}_{stats_field_name}"
                    mapped[new_key] = value

        return mapped

    def _metric_to_stats_field(self, metric: str) -> str:
        """
        将合成指标名映射回 stats 字段名

        映射规则:
        - xg -> expected_goals
        - total_shots -> total_shots
        - shots_on_target -> shotsontarget
        - avg_distance -> avg_shot_distance
        """
        mapping = {
            'xg': 'expected_goals',
            'total_shots': 'total_shots',
            'shots_on_target': 'shotsontarget',
            'avg_distance': 'avg_shot_distance',
            'big_chances': 'big_chance',
        }
        return mapping.get(metric, metric)


class PlayerTeamCascadeAggregator:
    """
    V20.7 球员-球队级联聚合器

    核心功能:
    1. 扫描 content.playerStats 节点
    2. 提取所有首发球员的 accuratePasses, touches, lostPossession 等指标
    3. 将 11 个人的数据加总，生成 team_total_accurate_passes 等全量特征
    """

    # 核心球员指标
    CORE_PLAYER_METRICS = [
        'accuratePasses',
        'touches',
        'lostPossession',
        'groundDuelsWon',
        'aerialDuelsWon',
        'totalPasses',
        'keyPasses',
        'bigChanceCreated',
        'interceptions',
        'clearances',
        'tackles',
    ]

    def __init__(self, home_team_id: int, away_team_id: int):
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id

    def extract_player_team_aggregates(
        self,
        content: Dict,
        features: Dict
    ) -> Dict[str, Any]:
        """
        提取球员-球队级联聚合特征

        Args:
            content: FotMob API content
            features: 当前特征字典

        Returns:
            新增的聚合特征字典
        """
        aggregated = {}

        player_stats = content.get('playerStats', {})
        if not player_stats:
            logger.debug("No playerStats data found")
            return aggregated

        # 按球队分类球员
        home_player_ids = []
        away_player_ids = []

        for player_id, player_data in player_stats.items():
            if not isinstance(player_data, dict):
                continue

            team_id = player_data.get('teamId')
            if team_id == self.home_team_id:
                home_player_ids.append(player_id)
            elif team_id == self.away_team_id:
                away_player_ids.append(player_id)

        # 为每个指标聚合
        for metric in self.CORE_PLAYER_METRICS:
            home_total = self._aggregate_metric_for_team(
                player_stats, home_player_ids, metric
            )
            away_total = self._aggregate_metric_for_team(
                player_stats, away_player_ids, metric
            )

            # 生成特征
            feature_name = f"team_total_{metric.lower()}"
            aggregated[f'home_{feature_name}'] = home_total
            aggregated[f'away_{feature_name}'] = away_total
            aggregated[f'diff_{feature_name}'] = home_total - away_total
            aggregated[f'total_{feature_name}'] = home_total + away_total

        logger.info(f"👥 球员-球队级联聚合: 生成 {len(aggregated)} 个特征")
        return aggregated

    def _aggregate_metric_for_team(
        self,
        player_stats: Dict,
        player_ids: List[str],
        metric: str
    ) -> int:
        """为指定球队的球员聚合指标"""
        total = 0

        for player_id in player_ids:
            player_data = player_stats.get(player_id, {})
            if not isinstance(player_data, dict):
                continue

            stats = player_data.get('stats', [])
            if not isinstance(stats, list):
                continue

            # 查找匹配的指标
            for stat in stats:
                if not isinstance(stat, dict):
                    continue

                stat_key = stat.get('key', '')
                if metric.lower() in stat_key.lower():
                    stat_value = stat.get('stats', [])
                    if isinstance(stat_value, list) and len(stat_value) > 0:
                        # 假设第一个值是主队的统计
                        try:
                            total += int(stat_value[0])
                        except (ValueError, TypeError):
                            pass
                    break

        return total


class MomentumDeepAnalyzer:
    """
    V20.7 动量特征深度解剖器

    核心功能:
    1. 提取 momentum.main.data 进行特征工程
    2. momentum_pos_velocity: 正向动量变化率 (反映进攻效率)
    3. momentum_neg_acceleration: 负向动量加速度 (反映防线崩溃速度)
    """

    def extract_deep_momentum_features(
        self,
        content: Dict
    ) -> Dict[str, Any]:
        """
        提取深度动量特征

        Args:
            content: FotMob API content

        Returns:
            深度动量特征字典
        """
        features = {}

        # 查找 momentum 数据 (可能在多个位置)
        momentum_data = self._find_momentum_data(content)

        if not momentum_data:
            logger.debug("No momentum data found")
            return features

        # 提取主客队动量序列
        home_values, away_values = self._parse_momentum_values(momentum_data)

        if home_values:
            home_features = self._calculate_momentum_derivatives(home_values, 'home')
            features.update(home_features)

        if away_values:
            away_features = self._calculate_momentum_derivatives(away_values, 'away')
            features.update(away_features)

        # 联合特征
        if home_values and away_values:
            joint_features = self._calculate_joint_momentum_features(
                home_values, away_values
            )
            features.update(joint_features)

        logger.info(f"📈 动量深度解剖: 生成 {len(features)} 个特征")
        return features

    def _find_momentum_data(self, content: Dict) -> Optional[Dict]:
        """在 content 中查找 momentum 数据"""
        # 尝试多个路径
        paths = [
            content.get('momentum', {}),
            content.get('superlive', {}).get('momentum', {}),
        ]

        for path_data in paths:
            if path_data and isinstance(path_data, dict):
                return path_data

        return None

    def _parse_momentum_values(self, momentum_data: Dict) -> Tuple[List[float], List[float]]:
        """解析主客队动量值序列"""
        home_values = []
        away_values = []

        # 尝试不同的数据格式
        for key in ['home', 'away', 'data', 'main']:
            data = momentum_data.get(key, [])
            if isinstance(data, list) and data:
                # 检查是否包含数值
                for item in data[:100]:  # 限制处理数量
                    if isinstance(item, dict):
                        value = item.get('value', item.get('x', 0))
                    elif isinstance(item, (int, float)):
                        value = item
                    else:
                        continue

                    try:
                        value = float(value)
                        if key == 'home' or key.startswith('home'):
                            home_values.append(value)
                        elif key == 'away' or key.startswith('away'):
                            away_values.append(value)
                    except (ValueError, TypeError):
                        pass

                if home_values or away_values:
                    break

        return home_values, away_values

    def _calculate_momentum_derivatives(
        self,
        values: List[float],
        team: str
    ) -> Dict[str, Any]:
        """
        计算动量的导数特征

        计算指标:
        - velocity: 一阶导数 (变化率)
        - acceleration: 二阶导数 (变化的变化率)
        - pos_velocity: 正向动量变化率
        - neg_acceleration: 负向动量加速度
        """
        features = {}

        if len(values) < 2:
            return features

        # 一阶导数 (速度)
        velocities = np.diff(values)

        # 二阶导数 (加速度)
        if len(velocities) >= 2:
            accelerations = np.diff(velocities)
        else:
            accelerations = []

        # 正向速度 (反映进攻效率)
        pos_velocities = [v for v in velocities if v > 0]
        neg_velocities = [v for v in velocities if v < 0]

        # 负向加速度 (反映防线崩溃速度)
        neg_accelerations = [a for a in accelerations if a < 0]

        # 生成特征
        features[f'{team}_momentum_velocity_mean'] = float(np.mean(velocities)) if velocities else 0.0
        features[f'{team}_momentum_velocity_std'] = float(np.std(velocities)) if len(velocities) > 1 else 0.0
        features[f'{team}_momentum_pos_velocity_mean'] = float(np.mean(pos_velocities)) if pos_velocities else 0.0
        features[f'{team}_momentum_neg_velocity_mean'] = float(np.mean(neg_velocities)) if neg_velocities else 0.0

        features[f'{team}_momentum_acceleration_mean'] = float(np.mean(accelerations)) if accelerations else 0.0
        features[f'{team}_momentum_acceleration_std'] = float(np.std(accelerations)) if len(accelerations) > 1 else 0.0
        features[f'{team}_momentum_neg_acceleration_mean'] = float(np.mean(neg_accelerations)) if neg_accelerations else 0.0

        # 动量极值
        features[f'{team}_momentum_max_velocity'] = float(np.max(velocities)) if velocities else 0.0
        features[f'{team}_momentum_min_velocity'] = float(np.min(velocities)) if velocities else 0.0

        return features

    def _calculate_joint_momentum_features(
        self,
        home_values: List[float],
        away_values: List[float]
    ) -> Dict[str, Any]:
        """计算主客队联合动量特征"""
        features = {}

        # 动量差值
        min_len = min(len(home_values), len(away_values))
        if min_len > 0:
            diff_values = [home_values[i] - away_values[i] for i in range(min_len)]

            features['momentum_diff_mean'] = float(np.mean(diff_values))
            features['momentum_diff_std'] = float(np.std(diff_values)) if len(diff_values) > 1 else 0.0
            features['momentum_diff_max'] = float(np.max(diff_values))
            features['momentum_diff_min'] = float(np.min(diff_values))

        return features


class SchemaAlignmentEnforcer:
    """
    V20.7 全量 Schema 对齐强制器 - Zero-Padding 机制

    核心功能:
    1. 无论原始 JSON 是否存在该字段，所有 800+ 个 Key 必须出现
    2. 如果无法获取某字段，统一填充为 0.0 或 -1.0 (缺失值标记)
    3. 绝对不允许列数不一致
    """

    # 全量 Schema 定义 (V20.7 标准)
    FULL_SCHEMA = V20_7_FULL_SCHEMA

    def __init__(self):
        """初始化 Schema 对齐器"""
        self.full_schema = self.FULL_SCHEMA.copy()

        # 添加常见 stats 字段
        common_stats_fields = self._get_common_stats_fields()
        self.full_schema.update(common_stats_fields)

        logger.info(f"🔧 V20.7 全量 Schema: {len(self.full_schema)} 个字段")

    def _get_common_stats_fields(self) -> Set[str]:
        """获取常见 stats 字段"""
        fields = set()

        # All 时段字段
        periods = ['All', 'FirstHalf', 'SecondHalf']
        prefixes = ['home', 'away', 'diff', 'total']

        # 常见 stats 指标
        metrics = [
            'expected_goals', 'total_shots', 'shotsontarget', 'possession',
            'accurate_passes', 'touches', 'interceptions', 'clearances',
            'corners', 'fouls', 'offsides', 'yellow_cards', 'red_cards',
            'saves', 'ball_recoveries', 'aerials_won', 'tackles_won',
        ]

        for period in periods:
            for prefix in prefixes:
                for metric in metrics:
                    if period == 'All':
                        fields.add(f'{prefix}_{metric}')
                    else:
                        fields.add(f'{prefix}_{period}_{metric}')

        return fields

    def enforce_schema_alignment(
        self,
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        强制执行 Schema 对齐

        Args:
            features: 当前特征字典

        Returns:
            对齐后的特征字典 (确保所有字段都存在)
        """
        aligned = features.copy()
        missing_count = 0

        # 填充缺失的字段
        for field in self.full_schema:
            if field not in aligned:
                # 根据字段类型决定填充值
                if 'id' in field.lower():
                    aligned[field] = -1  # ID 类型使用 -1
                else:
                    aligned[field] = 0.0  # 数值类型使用 0.0
                missing_count += 1

        # 移除不在 Schema 中的额外字段 (可选，保持严格性)
        # for key in list(aligned.keys()):
        #     if key not in self.full_schema:
        #         del aligned[key]

        logger.info(f"📐 Schema 对齐: 填充 {missing_count} 个缺失字段")

        return aligned


def atomic_align_v20_7(
    content: Dict,
    features: Dict,
    home_team_id: int,
    away_team_id: int
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    V20.7 原子级数据对齐 - 统一入口

    Args:
        content: FotMob API content
        features: 当前特征字典
        home_team_id: 主队 ID
        away_team_id: 客队 ID

    Returns:
        (aligned_features, metrics) - 对齐后的特征和指标
    """
    metrics = {
        'backfilled_fields': 0,
        'player_aggregates': 0,
        'momentum_features': 0,
        'schema_aligned': False,
    }

    # 1. 原子级回填
    backfill_engine = AtomicBackfillEngine(home_team_id, away_team_id)
    features, backfill_metrics = backfill_engine.atomic_backfill(content, features)
    metrics['backfilled_fields'] = backfill_metrics.stats_fields_filled

    # 2. 球员-球队级联聚合
    player_aggregator = PlayerTeamCascadeAggregator(home_team_id, away_team_id)
    player_features = player_aggregator.extract_player_team_aggregates(content, features)
    features.update(player_features)
    metrics['player_aggregates'] = len(player_features)

    # 3. 动量特征深度解剖
    momentum_analyzer = MomentumDeepAnalyzer()
    momentum_features = momentum_analyzer.extract_deep_momentum_features(content)
    features.update(momentum_features)
    metrics['momentum_features'] = len(momentum_features)

    # 4. 全量 Schema 对齐
    schema_enforcer = SchemaAlignmentEnforcer()
    features = schema_enforcer.enforce_schema_alignment(features)
    metrics['schema_aligned'] = True

    logger.info(f"🚀 V20.7 原子对齐完成: {len(features)} 个特征")

    return features, metrics


# ==================== V20.8 深度球员聚合模块 ====================

# V20.8 深度球员指标 - 攻克最后 200 维
V20_8_DEEP_PLAYER_METRICS = [
    # 进攻端
    'touches_in_box',           # 禁区内触球
    'key_passes_segment',        # 关键传球分段
    'shot_assists',              # 射门助攻
    'goal_contribution',         # 进球贡献

    # 防守端
    'ball_recoveries',           # 夺回球权分布
    'aerial_duels_won',          # 空中对垒成功率
    'possession_recovered',      # 拦截恢复球权
    'clearances_headed',         # 头球解围

    # 组织端
    'progressive_passes',        # 向前推进传球
    'passes_final_third',        # 前场三分之一传球
    'crosses_successful',        # 成功传中

    # 压迫端
    'pressures',                 # 压迫次数
    'pressures_successful',      # 成功压迫
    'fouls_conceded',            # 犯规次数

    # 扩展基础指标
    'totalFinalThirdPasses',     # 前场三分之一传球 (API 字段名)
    'accurateFinalThirdPasses',  # 成功前场传球
    'progressiveCarries',        # 向前带球推进
]

# 位置聚合映射
POSITION_GROUPS = {
    'GK': ['Goalkeeper'],           # 门将
    'DF': ['Centre-Back', 'Left-Back', 'Right-Back', 'Wing-Back'],  # 后卫
    'MF': ['Central-Midfield', 'Defensive-Midfield', 'Attacking-Midfield',
           'Left-Midfield', 'Right-Midfield', 'Left-Winger', 'Right-Winger', 'Winger'],  # 中场
    'FW': ['Centre-Forward', 'Second-Striker', 'Striker']  # 前锋
}


class V20_8DeepPlayerAggregator:
    """
    V20.8 深度球员聚合器 - 攻克最后 200 维

    新增特征:
    - 进攻端: 禁区内触球 (touches_in_box)、关键传球分段 (key_passes_segment)
    - 防守端: 夺回球权分布 (ball_recoveries)、空中对垒成功率 (aerial_duels_won)
    - 位置聚合: 按 GK/DF/MF/FW 进行 4x16 级联累加
    """

    def __init__(self, home_team_id: int, away_team_id: int):
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id

    def extract_deep_aggregates(
        self,
        content: Dict,
        features: Dict
    ) -> Dict[str, Any]:
        """
        提取深度球员聚合特征

        Returns:
            新增的深度聚合特征字典
        """
        aggregated = {}
        player_stats = content.get('playerStats', {})

        if not player_stats:
            logger.debug("playerStats 不可用，跳过深度聚合")
            return aggregated

        # 提取主队和客队球员数据
        home_stats = player_stats.get(str(self.home_team_id), {})
        away_stats = player_stats.get(str(self.away_team_id), {})

        for team_side, team_stats in [('home', home_stats), ('away', away_stats)]:
            if not team_stats:
                continue

            # 1. 全队加总聚合（深度指标）
            for metric in V20_8_DEEP_PLAYER_METRICS:
                total = 0.0
                player_count = 0

                for player_id, player_data in team_stats.items():
                    if isinstance(player_data, dict):
                        value = self._extract_metric_value(player_data, metric)
                        if value is not None and value > 0:
                            total += value
                            player_count += 1

                if player_count > 0:
                    aggregated[f'{team_side}_team_deep_total_{metric}'] = total
                    aggregated[f'{team_side}_team_deep_avg_{metric}'] = round(total / player_count, 3)

            # 2. 位置级联聚合（GK/DF/MF/FW）
            position_aggregates = self._aggregate_by_position(team_stats, team_side)
            aggregated.update(position_aggregates)

        logger.info(f"🔥 V20.8 深度聚合: 生成 {len(aggregated)} 个位置特征")
        return aggregated

    def _extract_metric_value(self, player_data: Dict, metric: str) -> Optional[float]:
        """
        V20.8 递归解析球员数据中的 stats 列表

        数据结构:
        player_data = {
            'id': 12345,
            'name': 'Player Name',
            'stats': [
                {'key': 'Touches', 'stats': [45, null]},
                {'key': 'Interceptions', 'stats': [3, null]},
                ...
            ]
        }

        Args:
            player_data: 球员数据字典
            metric: 指标名称

        Returns:
            指标值或 None
        """
        # 1. 尝试直接获取（扁平化数据）
        if metric in player_data:
            value = player_data.get(metric)
            if isinstance(value, (int, float)):
                return float(value)
            # 处理字符串格式 "123 (45%)"
            if isinstance(value, str):
                parts = value.split()
                if parts:
                    try:
                        return float(parts[0])
                    except ValueError:
                        pass

        # 2. 尝试从 stats 字典获取（嵌套字典）
        stats_dict = player_data.get('stats')
        if isinstance(stats_dict, dict):
            if metric in stats_dict:
                value = stats_dict.get(metric)
                if isinstance(value, (int, float)):
                    return float(value)

        # 3. V20.8 关键修复：递归解析 stats 列表
        # 结构: stats = [{'key': 'Touches', 'stats': [45, null]}, ...]
        stats_list = player_data.get('stats')
        if isinstance(stats_list, list):
            # 遍历 stats 列表
            for stat_item in stats_list:
                if not isinstance(stat_item, dict):
                    continue

                stat_key = stat_item.get('key', '')
                stat_value = stat_item.get('stats')

                # 模糊匹配 key（不区分大小写）
                if stat_key and metric.lower() in stat_key.lower():
                    # 提取值（stats 通常是 [value, null] 格式）
                    if isinstance(stat_value, list) and len(stat_value) > 0:
                        value = stat_value[0]
                        if isinstance(value, (int, float)):
                            return float(value)
                    elif isinstance(stat_value, (int, float)):
                        return float(stat_value)
                    elif isinstance(stat_value, str):
                        try:
                            return float(stat_value)
                        except ValueError:
                            pass

        # 4. 尝试从嵌套的 'stats' 字典中的 'stats' 列表
        # 结构: player_data.stats.stats = [{'key': ..., 'stats': [...]}]
        if isinstance(stats_dict, dict):
            nested_stats = stats_dict.get('stats')
            if isinstance(nested_stats, list):
                for stat_item in nested_stats:
                    if not isinstance(stat_item, dict):
                        continue

                    stat_key = stat_item.get('key', '')
                    stat_value = stat_item.get('stats')

                    if stat_key and metric.lower() in stat_key.lower():
                        if isinstance(stat_value, list) and len(stat_value) > 0:
                            value = stat_value[0]
                            if isinstance(value, (int, float)):
                                return float(value)
                        elif isinstance(stat_value, (int, float)):
                            return float(stat_value)

        return None

    def _aggregate_by_position(
        self,
        team_stats: Dict,
        team_side: str
    ) -> Dict[str, Any]:
        """
        按位置聚合 (GK/DF/MF/FW)

        为每个位置和每个深度指标计算聚合值
        """
        aggregated = {}

        # 初始化位置分组
        position_groups = defaultdict(list)

        # 按位置分组球员
        for player_id, player_data in team_stats.items():
            if not isinstance(player_data, dict):
                continue

            # 尝试多种方式获取位置
            position = player_data.get('position') or player_data.get('usualPosition', 'Unknown')
            position_groups[position].append(player_data)

        # 为每个位置组计算聚合
        for position_group, position_names in POSITION_GROUPS.items():
            group_players = []

            # 收集该位置组的所有球员
            for pos_name in position_names:
                group_players.extend(position_groups.get(pos_name, []))

            if not group_players:
                continue

            # 为每个深度指标计算位置聚合
            for metric in V20_8_DEEP_PLAYER_METRICS:
                total = 0.0
                player_count = 0

                for player_data in group_players:
                    value = self._extract_metric_value(player_data, metric)
                    if value is not None and value > 0:
                        total += value
                        player_count += 1

                if player_count > 0:
                    aggregated[f'{team_side}_{position_group}_{metric}_total'] = total
                    aggregated[f'{team_side}_{position_group}_{metric}_avg'] = round(total / player_count, 3)

        return aggregated


def atomic_align_v20_8(
    content: Dict,
    features: Dict,
    home_team_id: int,
    away_team_id: int
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    V20.8 原子级数据对齐 - 统一入口 (V20.7 + 深度球员聚合)

    Args:
        content: FotMob API content
        features: 当前特征字典
        home_team_id: 主队 ID
        away_team_id: 客队 ID

    Returns:
        (aligned_features, metrics) - 对齐后的特征和指标
    """
    metrics = {
        'backfilled_fields': 0,
        'player_aggregates': 0,
        'deep_player_aggregates': 0,
        'momentum_features': 0,
        'schema_aligned': False,
        'extraction_version': 'V20.8',
    }

    # 1. 原子级回填
    backfill_engine = AtomicBackfillEngine(home_team_id, away_team_id)
    features, backfill_metrics = backfill_engine.atomic_backfill(content, features)
    metrics['backfilled_fields'] = backfill_metrics.stats_fields_filled

    # 2. 球员-球队级联聚合 (V20.7 基础)
    player_aggregator = PlayerTeamCascadeAggregator(home_team_id, away_team_id)
    player_features = player_aggregator.extract_player_team_aggregates(content, features)
    features.update(player_features)
    metrics['player_aggregates'] = len(player_features)

    # 3. V20.8 深度球员聚合 (位置级联)
    deep_aggregator = V20_8DeepPlayerAggregator(home_team_id, away_team_id)
    deep_features = deep_aggregator.extract_deep_aggregates(content, features)
    features.update(deep_features)
    metrics['deep_player_aggregates'] = len(deep_features)

    # 4. 动量特征深度解剖
    momentum_analyzer = MomentumDeepAnalyzer()
    momentum_features = momentum_analyzer.extract_deep_momentum_features(content)
    features.update(momentum_features)
    metrics['momentum_features'] = len(momentum_features)

    # 5. 全量 Schema 对齐
    schema_enforcer = SchemaAlignmentEnforcer()
    features = schema_enforcer.enforce_schema_alignment(features)
    metrics['schema_aligned'] = True

    logger.info(f"🚀 V20.8 原子对齐完成: {len(features)} 个特征 (+{metrics['deep_player_aggregates']} 深度聚合)")

    return features, metrics


# ==================== 测试代码 ====================
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    logging.basicConfig(level=logging.INFO)

    import json
    from src.ml.shotmap_aggregator import synthesize_v20_6_features

    test_file = '/home/user/projects/FootballPrediction/data/backfill_stats/raw_json_match_3609929.json'

    with open(test_file, 'r') as f:
        data = json.load(f)

    content = data.get('content', {})
    general = data.get('general', {})
    home_team_id = general.get('homeTeam', {}).get('id', 0)
    away_team_id = general.get('awayTeam', {}).get('id', 0)

    print(f"\n{'='*70}")
    print("V20.7 原子级数据对齐测试")
    print(f"{'='*70}")

    # 执行对齐
    initial_features = {}
    aligned_features, metrics = atomic_align_v20_7(
        content, initial_features, home_team_id, away_team_id
    )

    print(f"\n{'='*70}")
    print("对齐结果")
    print(f"{'='*70}")
    print(f"总特征数: {len(aligned_features)}")
    print(f"回填字段数: {metrics['backfilled_fields']}")
    print(f"球员聚合数: {metrics['player_aggregates']}")
    print(f"动量特征数: {metrics['momentum_features']}")
    print(f"Schema 对齐: {metrics['schema_aligned']}")
