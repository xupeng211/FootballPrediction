#!/usr/bin/env python3
"""
V19.4 平局敏感度特征提取器 (Draw Sensitivity Features)
==============================================================

针对V19.3审计中发现的"平局识别率为0%"问题，引入3个针对性特征：

1. table_proximity: 双方积分榜排名接近度
2. low_scoring_tendency: 双方历史滚动总进球数的低频度
3. elo_diff_cluster: ELO差距是否处于[-20, 20]的窄区间

作者: V19.4量化策略团队
日期: 2025-12-23
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DrawSensitivityFeatureExtractor:
    """
    平局敏感度特征提取器

    核心功能:
    1. 计算积分榜接近度特征
    2. 计算低比分倾向特征
    3. 计算ELO差距聚类特征
    """

    def __init__(self):
        """初始化特征提取器"""
        self.feature_names = [
            'table_proximity',
            'low_scoring_tendency',
            'elo_diff_cluster'
        ]

    def extract(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        从比赛数据中提取平局敏感度特征

        Args:
            df: 比赛数据，必须包含以下列：
                - home_table_position: 主队积分榜排名
                - away_table_position: 客队积分榜排名
                - home_team: 主队名称
                - away_team: 客队名称
                - match_time: 比赛时间（用于历史数据计算）
                - home_rolling_xg: 主队滚动xG
                - away_rolling_xg: 客队滚动xG
                - home_rolling_shots_on_target: 主队滚动射正数
                - away_rolling_shots_on_target: 客队滚动射正数
                - home_elo_rating: 主队ELO评分（如果有）
                - away_elo_rating: 客队ELO评分（如果有）

        Returns:
            包含3个新特征的数据框
        """
        logger.info(f"开始提取平局敏感度特征，数据量: {len(df)} 场")

        # 1. 计算积分榜接近度特征
        df['table_proximity'] = self._calculate_table_proximity(
            df['home_table_position'],
            df['away_table_position']
        )

        # 2. 计算低比分倾向特征
        df['low_scoring_tendency'] = self._calculate_low_scoring_tendency(
            df['home_rolling_xg'],
            df['away_rolling_xg'],
            df['home_rolling_shots_on_target'],
            df['away_rolling_shots_on_target']
        )

        # 3. 计算ELO差距聚类特征
        if 'home_elo_rating' in df.columns and 'away_elo_rating' in df.columns:
            df['elo_diff_cluster'] = self._calculate_elo_diff_cluster(
                df['home_elo_rating'],
                df['away_elo_rating']
            )
        else:
            # 如果没有ELO数据，使用默认值
            df['elo_diff_cluster'] = 0

        logger.info("平局敏感度特征提取完成")
        return df

    def _calculate_table_proximity(self, home_pos: pd.Series, away_pos: pd.Series) -> pd.Series:
        """
        计算积分榜排名接近度

        逻辑: 排名差距越小，平局概率越高
        使用高斯函数模拟接近度效应
        """
        # 计算排名差距
        position_diff = np.abs(home_pos - away_pos)

        # 转换为接近度分数 (0-1, 1表示最接近)
        # 使用高斯函数: exp(-(diff^2) / (2 * sigma^2))
        # sigma = 5, 意味着差距在5名以内才有显著影响
        proximity = np.exp(-(position_diff ** 2) / (2 * 5 ** 2))

        return proximity

    def _calculate_low_scoring_tendency(
        self,
        home_xg: pd.Series,
        away_xg: pd.Series,
        home_shots: pd.Series,
        away_shots: pd.Series
    ) -> pd.Series:
        """
        计算低比分倾向特征

        逻辑: 双方xG低 + 射正少 = 平局概率高
        """
        # 双方xG的平均值
        avg_xg = (home_xg + away_xg) / 2

        # 双方射正数的平均值
        avg_shots = (home_shots + away_shots) / 2

        # 低分阈值
        low_xg_threshold = 1.0  # 双方场均xG小于1.0为低比分比赛
        low_shots_threshold = 3.0  # 双方场均射正数小于3.0为低比分比赛

        # 计算低比分倾向 (0-1, 1表示强低比分倾向)
        low_scoring = (
            (avg_xg < low_xg_threshold).astype(float) * 0.6 +
            (avg_shots < low_shots_threshold).astype(float) * 0.4
        )

        return low_scoring

    def _calculate_elo_diff_cluster(
        self,
        home_elo: pd.Series,
        away_elo: pd.Series
    ) -> pd.Series:
        """
        计算ELO差距聚类特征

        逻辑: ELO差距在[-20, 20]区间内时，平局概率较高
        """
        # 计算ELO差距
        elo_diff = home_elo - away_elo

        # 判断是否在窄区间内
        in_narrow_range = ((elo_diff >= -20) & (elo_diff <= 20)).astype(float)

        return in_narrow_range


def extract_draw_sensitivity_features(
    df: pd.DataFrame,
    home_pos_col: str = 'home_table_position',
    away_pos_col: str = 'away_table_position',
    home_xg_col: str = 'home_rolling_xg',
    away_xg_col: str = 'away_rolling_xg',
    home_shots_col: str = 'home_rolling_shots_on_target',
    away_shots_col: str = 'away_rolling_shots_on_target',
    home_elo_col: str = 'home_elo_rating',
    away_elo_col: str = 'away_elo_rating'
) -> pd.DataFrame:
    """
    提取平局敏感度特征的便捷函数

    Args:
        df: 比赛数据框
        home_pos_col: 主队排名列名
        away_pos_col: 客队排名列名
        home_xg_col: 主队xG列名
        away_xg_col: 客队xG列名
        home_shots_col: 主队射正列名
        away_shots_col: 客队射正列名
        home_elo_col: 主队ELO列名
        away_elo_col: 客队ELO列名

    Returns:
        添加了3个平局敏感度特征的数据框
    """
    extractor = DrawSensitivityFeatureExtractor()
    return extractor.extract(df)


# ============================================
# 单元测试
# ============================================

if __name__ == "__main__":
    # 测试数据
    test_data = pd.DataFrame({
        'home_table_position': [1, 5, 10, 15, 20, 1, 5, 10, 15, 20],
        'away_table_position': [2, 6, 11, 16, 21, 3, 7, 12, 17, 22],
        'home_team': ['Team A'] * 10 + ['Team B'] * 10,
        'away_team': ['Team B'] * 5 + ['Team A'] * 5 + ['Team C'] * 5 + ['Team D'] * 5 + ['Team A'] * 5,
        'home_rolling_xg': [1.2, 1.5, 1.0, 0.8, 1.3, 2.5, 1.8, 1.1, 0.9, 1.4],
        'away_rolling_xg': [1.1, 1.4, 1.2, 1.0, 1.2, 2.3, 1.9, 1.0, 1.1, 1.3],
        'home_rolling_shots_on_target': [4.0, 5.0, 3.0, 3.5, 4.5, 6.0, 5.5, 3.5, 4.0, 5.0],
        'away_rolling_shots_on_target': [3.5, 4.5, 3.5, 4.0, 4.0, 5.5, 5.0, 4.0, 3.5, 4.5],
        'home_elo_rating': [1500, 1480, 1460, 1440, 1420, 1520, 1500, 1480, 1460, 1440, 1420],
        'away_elo_rating': [1495, 1485, 1470, 1465, 1460, 1515, 1505, 1495, 1480, 1475]
    })

    # 测试特征提取
    result = extract_draw_sensitivity_features(test_data)

    print("=" * 60)
    print("平局敏感度特征测试结果")
    print("=" * 60)
    print(result[['home_team', 'away_team', 'table_proximity',
                   'low_scoring_tendency', 'elo_diff_cluster']].head(10))
    print("\n特征统计:")
    print(result[['table_proximity', 'low_scoring_tendency', 'elo_diff_cluster']].describe())
