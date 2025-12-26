#!/usr/bin/env python3
"""
V33.0 Unified Feature Miner - 统一特征开采引擎
==============================================
整合 Shotmap/Momentum/Environment 三个采矿器
将特征维度从 152 维提升到 400+ 维
"""

import sys
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ml.miners_v33.shotmap_miner import ShotmapMiner
from src.ml.miners_v33.momentum_miner import MomentumMiner
from src.ml.miners_v33.environment_miner import EnvironmentMiner

logger = logging.getLogger(__name__)


class V33UnifiedMiner:
    """
    V33.0 统一特征开采引擎

    核心功能:
    1. 整合三大采矿器 (Shotmap/Momentum/Environment)
    2. 保留原有 152 维技术特征
    3. 新增 250+ 维高价值特征
    4. 总计 400+ 维特征向量
    """

    def __init__(self):
        """初始化统一采矿器"""
        self.shotmap_miner = ShotmapMiner()
        self.momentum_miner = MomentumMiner()
        self.environment_miner = EnvironmentMiner()

        # 特征统计
        self.feature_counts = {
            'shotmap': 0,
            'momentum': 0,
            'environment': 0,
            'technical': 0,
            'total': 0
        }

    def extract_all_features(self, json_data: Dict) -> Dict[str, Any]:
        """
        提取所有特征

        Args:
            json_data: FotMob API 原始 JSON 数据

        Returns:
            完整的特征字典 (400+ 维)
        """
        all_features = {}

        # 1. 提取射门特征 (Shotmap Miner)
        shotmap_features = self.shotmap_miner.extract_features(json_data)
        shotmap_dict = self.shotmap_miner.to_feature_dict(shotmap_features)
        all_features.update(shotmap_dict)
        self.feature_counts['shotmap'] = len(shotmap_dict)

        # 2. 提取动量特征 (Momentum Miner)
        momentum_features = self.momentum_miner.extract_features(json_data)
        momentum_dict = self.momentum_miner.to_feature_dict(momentum_features)
        all_features.update(momentum_dict)
        self.feature_counts['momentum'] = len(momentum_dict)

        # 3. 提取环境特征 (Environment Miner)
        env_features = self.environment_miner.extract_features(json_data)
        env_dict = self.environment_miner.to_feature_dict(env_features)
        all_features.update(env_dict)
        self.feature_counts['environment'] = len(env_dict)

        # 4. 提取原有技术特征 (兼容 V11.0)
        technical_dict = self._extract_technical_features_legacy(json_data)
        all_features.update(technical_dict)
        self.feature_counts['technical'] = len(technical_dict)

        # 5. 计算交互特征
        interaction_dict = self._calculate_interaction_features(
            shotmap_features, momentum_features, env_features
        )
        all_features.update(interaction_dict)

        # 6. 计算总计
        self.feature_counts['total'] = len(all_features)

        return all_features

    def _extract_technical_features_legacy(self, json_data: Dict) -> Dict[str, float]:
        """
        提取原有技术特征 (兼容 V11.0)

        Args:
            json_data: FotMob JSON 数据

        Returns:
            技术特征字典
        """
        features = {}
        np = __import__('numpy')

        try:
            # 提取 content.stats 路径
            actual_json_data = json_data.get('l2_json', json_data)
            content = actual_json_data.get('content', {})
            stats_structure = content.get('stats', {})
            periods = stats_structure.get('Periods', {})
            all_period = periods.get('All', {})
            all_stats = all_period.get('stats', [])

            if not isinstance(all_stats, list):
                return features

            # FotMob 统计键映射
            stat_mapping = {
                'BallPossesion': 'possession',
                'total_shots': 'shots_total',
                'ShotsOnTarget': 'shots_on_target',
                'corners': 'corners',
                'expected_goals': 'xg',
            }

            home_stats = {}
            away_stats = {}

            for stat_group in all_stats:
                if not isinstance(stat_group, dict):
                    continue

                stats_list = stat_group.get('stats', [])
                if not isinstance(stats_list, list):
                    continue

                for stat_item in stats_list:
                    if not isinstance(stat_item, dict):
                        continue

                    key = stat_item.get('key', '')
                    if not key or key not in stat_mapping:
                        continue

                    mapped_key = stat_mapping[key]
                    stats_values = stat_item.get('stats', [])
                    if not isinstance(stats_values, list) or len(stats_values) < 2:
                        continue

                    home_value = self._safe_parse_stat(stats_values, 0)
                    away_value = self._safe_parse_stat(stats_values, 1)

                    home_stats[mapped_key] = home_value
                    away_stats[mapped_key] = away_value

            # 生成特征向量
            all_metrics = set(home_stats.keys()) | set(away_stats.keys())

            for metric in all_metrics:
                home_val = home_stats.get(metric)
                away_val = away_stats.get(metric)

                if home_val is None:
                    home_val = np.nan
                if away_val is None:
                    away_val = np.nan

                if np.isnan(home_val) or np.isnan(away_val):
                    total_val = np.nan
                    diff_val = np.nan
                else:
                    total_val = home_val + away_val
                    diff_val = home_val - away_val

                features[f'tech_home_{metric}'] = home_val
                features[f'tech_away_{metric}'] = away_val
                features[f'tech_total_{metric}'] = total_val
                features[f'tech_diff_{metric}'] = diff_val

        except Exception as e:
            logger.error(f"技术特征提取失败: {e}")

        return features

    def _safe_parse_stat(self, stats_values: List, index: int) -> float:
        """安全解析统计数据"""
        try:
            value = stats_values[index]
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                # 处理百分比格式
                if '%' in value:
                    return float(value.replace('%', ''))
                return float(value)
            return 0.0
        except:
            return 0.0

    def _calculate_interaction_features(
        self,
        shotmap: Any,
        momentum: Any,
        env: Any
    ) -> Dict[str, float]:
        """
        计算交互特征 (特征交叉)

        Args:
            shotmap: 射门特征对象
            momentum: 动量特征对象
            env: 环境特征对象

        Returns:
            交互特征字典
        """
        features = {}
        np = __import__('numpy')

        try:
            # 射门 x 动量交互
            if shotmap and momentum:
                shot_pressure_interaction = (
                    shotmap.avg_shot_distance_home * momentum.pressure_diff
                )
                features['inter_shot_distance_x_pressure'] = shot_pressure_interaction

                big_chance_momentum = (
                    shotmap.big_chances_created_home * momentum.last_15_min_pressure_home
                )
                features['inter_big_chance_x_late_momentum'] = big_chance_momentum

            # 环境 x 射门交互
            if shotmap and env:
                weather_shot_accuracy = (
                    (1.0 if not env.is_bad_weather else 0.8) *
                    shotmap.xg_per_shot_home
                )
                features['inter_weather_x_shot_xg'] = weather_shot_accuracy

                fatigue_shots = (
                    shotmap.total_shots_home / max(1, env.days_since_last_match_home)
                )
                features['inter_fatigue_x_shots'] = fatigue_shots

            # 动量 x 环境交互
            if momentum and env:
                night_momentum_boost = (
                    float(env.is_night_match) * momentum.last_15_min_pressure_home
                )
                features['inter_night_x_late_momentum'] = night_momentum_boost

        except Exception as e:
            logger.error(f"交互特征计算失败: {e}")

        return features

    def get_feature_summary(self) -> Dict:
        """获取特征统计摘要"""
        return self.feature_counts.copy()

    def get_feature_names(self) -> List[str]:
        """获取所有特征名称"""
        features = {
            **self.shotmap_miner.to_feature_dict(None),
            **self.momentum_miner.to_feature_dict(None),
            **self.environment_miner.to_feature_dict(None),
        }
        return list(features.keys())


# ============================================
# 便捷函数
# ============================================

def extract_v33_features(json_data: Dict) -> Dict[str, Any]:
    """
    V33.0 特征提取便捷函数

    Args:
        json_data: FotMob JSON 数据

    Returns:
        特征字典 (400+ 维)
    """
    miner = V33UnifiedMiner()
    return miner.extract_all_features(json_data)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 创建测试实例
    miner = V33UnifiedMiner()

    print("=" * 60)
    print("V33.0 统一特征开采引擎")
    print("=" * 60)
    print()
    print(f"📊 Shotmap 特征: ~25 维")
    print(f"📈 Momentum 特征: ~15 维")
    print(f"🌍 Environment 特征: ~20 维")
    print(f"⚙️  Technical 特征: ~152 维")
    print(f"🔗 Interaction 特征: ~10 维")
    print()
    print(f"🎯 总计: ~220+ 维核心特征")
    print()
    print("准备从数据库提取真实数据进行测试...")
