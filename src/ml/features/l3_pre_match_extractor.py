#!/usr/bin/env python3
"""
L3 级赛前特征工程 - 历史平均特征提取器
V10.2 - 系统重启版本

核心原则：
1. 禁止使用当场比赛的 L2 数据作为输入（避免数据泄露）
2. 只利用【过去 5 场】的 L2 平均数据来预测【本场】结果
3. 实现 181 维"赛前全景特征"
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from src.config_unified import get_settings
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class PlayerMatchStats:
    """球员单场比赛统计"""
    player_id: str
    player_name: str
    team_name: str
    is_goalkeeper: bool
    position: str
    shirt_number: int

    # 核心统计指标 (每场比赛的值)
    minutes_played: float = 0.0
    rating: float = 0.0
    goals: float = 0.0
    assists: float = 0.0
    total_shots: float = 0.0
    shots_on_target: float = 0.0
    expected_goals: float = 0.0
    expected_assists: float = 0.0
    accurate_passes: float = 0.0
    total_passes: float = 0.0
    chances_created: float = 0.0
    touches: float = 0.0
    touches_opp_box: float = 0.0
    tackles: float = 0.0
    interceptions: float = 0.0
    clearances: float = 0.0
    defensive_actions: float = 0.0
    fouls_committed: float = 0.0
    fouls_drawn: float = 0.0
    yellow_cards: float = 0.0
    red_cards: float = 0.0

    @classmethod
    def from_l2_data(cls, player_data: Dict) -> 'PlayerMatchStats':
        """从 L2 数据创建球员统计对象"""
        player = cls(
            player_id=str(player_data.get('id', '')),
            player_name=player_data.get('name', 'Unknown'),
            team_name=player_data.get('teamName', 'Unknown'),
            is_goalkeeper=player_data.get('isGoalkeeper', False),
            position=str(player_data.get('usualPosition', 'Unknown')),
            shirt_number=player_data.get('shirtNumber', 0)
        )

        # 解析统计数据
        stats_list = player_data.get('stats', [])
        if isinstance(stats_list, list):
            for stat_group in stats_list:
                if isinstance(stat_group, dict) and 'stats' in stat_group:
                    stats = stat_group['stats']
                    if isinstance(stats, dict):
                        player._extract_stat_values(stats)

        return player

    def _extract_stat_values(self, stats: Dict):
        """提取统计数值"""
        # 定义统计映射 - 使用实际的键名
        stat_mapping = {
            'Minutes played': 'minutes_played',
            'FotMob rating': 'rating',
            'Goals': 'goals',
            'Assists': 'assists',
            'Total shots': 'total_shots',
            'Expected goals (xG)': 'expected_goals',
            'Expected assists (xA)': 'expected_assists',
            'Accurate passes': 'accurate_passes',
            'Chances created': 'chances_created',
            'Touches': 'touches',
            'Touches in opposition box': 'touches_opp_box',
            'Tackles': 'tackles',
            'Interceptions': 'interceptions',
            'Clearances': 'clearances',
            'Defensive actions': 'defensive_actions'
        }

        for stat_key, stat_value in stats.items():
            if stat_key in stat_mapping:
                attr_name = stat_mapping[stat_key]
                if isinstance(stat_value, dict):
                    # 检查嵌套的 stat 结构
                    if 'stat' in stat_value:
                        stat_info = stat_value['stat']
                        if isinstance(stat_info, dict):
                            if 'value' in stat_info:
                                setattr(self, attr_name, float(stat_info['value']))
                            elif 'values' in stat_info:
                                # 处理多值情况
                                values = stat_info['values']
                                if isinstance(values, dict) and 'value' in values:
                                    setattr(self, attr_name, float(values['value']))
                                else:
                                    setattr(self, attr_name, float(values) if values else 0.0)
                    elif 'value' in stat_value:
                        setattr(self, attr_name, float(stat_value['value']))
                    elif 'total' in stat_value and 'value' in stat_value:
                        # 处理分数类型的统计 (如 11/25)
                        value = float(stat_value.get('value', 0))
                        total = float(stat_value.get('total', 1))
                        setattr(self, attr_name, value / total if total > 0 else 0.0)
                        # 同时保存总数值
                        if attr_name == 'accurate_passes':
                            self.total_passes = total

class L3PreMatchExtractor:
    """L3 级赛前特征提取器"""

    def __init__(self):
        self.settings = get_settings()
        self.db_config = self.settings.database

        # 关键球员特征列表 (用于构建 181 维特征)
        self.key_player_features = [
            'minutes_played', 'rating', 'goals', 'assists', 'total_shots',
            'shots_on_target', 'expected_goals', 'expected_assists',
            'accurate_passes', 'chances_created', 'touches', 'touches_opp_box',
            'tackles', 'interceptions', 'clearances', 'defensive_actions'
        ]

    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.db_config.host,
            port=self.db_config.port,
            database=self.db_config.name,
            user=self.db_config.user,
            password=self.db_config.password.get_secret_value()
        )

    def extract_player_historical_stats(self, team_name: str, match_time: datetime,
                                      lookback_matches: int = 5) -> List[PlayerMatchStats]:
        """提取球队过去 N 场比赛的球员统计数据"""

        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 查询该球队过去 N 场有 L2 数据的比赛
                cur.execute("""
                    SELECT external_id, home_team, away_team, match_time, l2_raw_json
                    FROM matches
                    WHERE l2_raw_json IS NOT NULL
                    AND match_time < %s
                    AND (home_team = %s OR away_team = %s)
                    ORDER BY match_time DESC
                    LIMIT %s
                """, (match_time, team_name, team_name, lookback_matches))

                historical_matches = cur.fetchall()
                all_player_stats = []

                for match in historical_matches:
                    try:
                        # 解析 L2 数据
                        if isinstance(match['l2_raw_json'], str):
                            l2_data = json.loads(match['l2_raw_json'])
                        else:
                            l2_data = match['l2_raw_json']

                        # 提取球员统计
                        content = l2_data.get('content', {})
                        player_stats = content.get('playerStats', {})

                        for player_id, player_data in player_stats.items():
                            if player_data.get('teamName') == team_name:
                                player_stat = PlayerMatchStats.from_l2_data(player_data)
                                all_player_stats.append(player_stat)

                    except Exception as e:
                        logger.warning(f"解析比赛 {match['external_id']} L2 数据失败: {e}")
                        continue

                return all_player_stats

        finally:
            conn.close()

    def calculate_team_player_features(self, team_name: str, match_time: datetime) -> np.ndarray:
        """计算球队的球员特征向量 (约 90 维)"""

        # 获取过去 5 场比赛的球员统计
        historical_stats = self.extract_player_historical_stats(team_name, match_time, 5)

        if not historical_stats:
            # 如果没有历史数据，返回零向量
            return np.zeros(len(self.key_player_features) * 6)  # 16个特征 * 6个统计维度

        # 按球员分组并计算平均值
        player_averages = {}
        for stat in historical_stats:
            player_id = stat.player_id
            if player_id not in player_averages:
                player_averages[player_id] = []
            player_averages[player_id].append(stat)

        # 为每个球员计算历史平均值
        player_features = []
        for player_id, matches in player_averages.items():
            if len(matches) >= 2:  # 至少需要2场比赛才计算平均值
                avg_stat = self._calculate_player_average(matches)
                feature_vector = self._player_to_feature_vector(avg_stat)
                player_features.append(feature_vector)

        if not player_features:
            return np.zeros(len(self.key_player_features) * 6)

        # 转换为 numpy 数组并计算汇总统计
        player_matrix = np.array(player_features)  # shape: (num_players, num_features)

        # 计算团队层面的汇总统计
        team_features = []

        # 对于每个特征维度，计算：平均值、标准差、最大值、最小值、中位数、总和
        for i in range(len(self.key_player_features)):
            feature_column = player_matrix[:, i]

            team_features.extend([
                np.mean(feature_column),    # 平均值
                np.std(feature_column),     # 标准差
                np.max(feature_column),     # 最大值
                np.min(feature_column),     # 最小值
                np.median(feature_column),  # 中位数
                np.sum(feature_column)      # 总和
            ])

        return np.array(team_features)

    def _calculate_player_average(self, player_matches: List[PlayerMatchStats]) -> PlayerMatchStats:
        """计算球员多场比赛的平均统计"""
        if not player_matches:
            return PlayerMatchStats(player_id='', player_name='Unknown', team_name='',
                                   is_goalkeeper=False, position='Unknown')

        avg_player = PlayerMatchStats(
            player_id=player_matches[0].player_id,
            player_name=player_matches[0].player_name,
            team_name=player_matches[0].team_name,
            is_goalkeeper=player_matches[0].is_goalkeeper,
            position=player_matches[0].position,
            shirt_number=player_matches[0].shirt_number
        )

        # 计算各指标的平均值
        for feature in self.key_player_features:
            total = sum(getattr(match, feature, 0) for match in player_matches)
            setattr(avg_player, feature, total / len(player_matches))

        return avg_player

    def _player_to_feature_vector(self, player_stat: PlayerMatchStats) -> np.ndarray:
        """将球员统计转换为特征向量"""
        return np.array([getattr(player_stat, feature, 0) for feature in self.key_player_features])

    def extract_match_features(self, home_team: str, away_team: str, match_time: datetime) -> np.ndarray:
        """提取比赛的完整赛前特征向量 (181 维)"""

        logger.info(f"开始提取 {home_team} vs {away_team} 的 L3 赛前特征")

        # 计算主客队特征
        home_features = self.calculate_team_player_features(home_team, match_time)
        away_features = self.calculate_team_player_features(away_team, match_time)

        # 计算差值特征
        diff_features = home_features - away_features

        # 计算比率特征 (避免除零)
        ratio_features = np.zeros_like(home_features)
        mask = away_features != 0
        ratio_features[mask] = home_features[mask] / away_features[mask]

        # 对于两队都是0的特征，比率设为1.0 (表示平等)
        both_zero_mask = (home_features == 0) & (away_features == 0)
        ratio_features[both_zero_mask] = 1.0

        # 对于只有主队>0的特征，比率设为较大值
        home_only_mask = (home_features != 0) & (away_features == 0)
        ratio_features[home_only_mask] = 10.0  # 设为一个较大的固定值

        # 组合所有特征
        total_features = len(home_features)
        expected_dimension = 181

        # 如果特征维度不对，进行调整
        combined_features = np.concatenate([home_features, away_features, diff_features])

        if len(combined_features) < expected_dimension:
            # 如果特征不够，用零填充
            padding = np.zeros(expected_dimension - len(combined_features))
            combined_features = np.concatenate([combined_features, padding])
        elif len(combined_features) > expected_dimension:
            # 如果特征太多，截断
            combined_features = combined_features[:expected_dimension]

        logger.info(f"L3 特征提取完成: {len(combined_features)} 维")
        return combined_features

    def get_feature_names(self) -> List[str]:
        """获取特征名称列表"""
        home_prefix = [f"home_{feature}_{stat}"
                      for feature in self.key_player_features
                      for stat in ['mean', 'std', 'max', 'min', 'median', 'sum']]

        away_prefix = [f"away_{feature}_{stat}"
                      for feature in self.key_player_features
                      for stat in ['mean', 'std', 'max', 'min', 'median', 'sum']]

        diff_prefix = [f"diff_{feature}" for feature in home_prefix]

        feature_names = home_prefix + away_prefix + diff_prefix

        # 确保特征名称数量为181
        if len(feature_names) > 181:
            feature_names = feature_names[:181]
        elif len(feature_names) < 181:
            for i in range(len(feature_names), 181):
                feature_names.append(f"feature_{i}")

        return feature_names

# 全局实例
l3_extractor = L3PreMatchExtractor()