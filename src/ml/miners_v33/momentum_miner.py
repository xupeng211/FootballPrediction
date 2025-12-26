#!/usr/bin/env python3
"""
V33.0 Momentum Miner - 动量波动分析器
====================================
从 content.momentum.main 中提取动量变化特征
"""

import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MomentumFeatures:
    """动量特征数据类"""
    # 全场压制力统计
    total_pressure_home: float
    total_pressure_away: float
    pressure_diff: float

    # 压制力波动
    pressure_variance: float
    pressure_std: float
    pressure_cv: float  # 变异系数

    # 关键时间段
    first_15_min_pressure_home: float
    first_15_min_pressure_away: float
    last_15_min_pressure_home: float
    last_15_min_pressure_away: float

    # 动量转换次数
    momentum_shifts: int
    max_momentum_swing: float

    # 主场优势时段
    home_dominance_minutes: int
    away_dominance_minutes: int


class MomentumMiner:
    """
    动量波动分析器

    核心功能:
    1. 全场压制力分析 - 累积动量值
    2. 压制力波动率 - 动量稳定性指标
    3. 关键时段分析 - 开场/收尾阶段
    4. 动量转换检测 - 比赛流向变化
    """

    def __init__(self):
        """初始化动量采矿器"""
        pass

    def extract_features(self, json_data: Dict) -> Optional[MomentumFeatures]:
        """
        从 FotMob JSON 中提取动量特征

        Args:
            json_data: FotMob API 响应数据

        Returns:
            MomentumFeatures 或 None
        """
        try:
            # 提取 momentum 数据
            content = json_data.get('content', {})
            momentum = content.get('momentum', {})
            main = momentum.get('main', {})

            # 提取动量数据点
            data = main.get('data', [])

            if not data:
                logger.debug("没有动量数据")
                return None

            # 解析动量数据结构
            momentum_series = self._parse_momentum_data(data)

            if not momentum_series:
                return None

            # 计算特征
            features = self._calculate_momentum_features(momentum_series)
            return features

        except Exception as e:
            logger.error(f"动量特征提取失败: {e}")
            return None

    def _parse_momentum_data(self, data: List) -> List[Dict]:
        """
        解析动量数据

        Args:
            data: 原始动量数据列表

        Returns:
            解析后的动量时间序列
        """
        momentum_series = []

        for item in data:
            try:
                # 动量数据通常包含时间和值
                # 格式可能是: {"minute": 5, "home": 0.3, "away": 0.2}
                # 或者: {"time": 300, "value": 0.5}
                minute = item.get('minute', item.get('time', 0))
                home_value = item.get('home', item.get('value', 0))
                away_value = item.get('away', 0)

                momentum_series.append({
                    'minute': minute,
                    'home': float(home_value),
                    'away': float(away_value),
                    'net': float(home_value) - float(away_value)
                })
            except Exception as e:
                logger.debug(f"解析动量数据点失败: {e}")
                continue

        return momentum_series

    def _calculate_momentum_features(self, series: List[Dict]) -> MomentumFeatures:
        """
        计算动量特征

        Args:
            series: 动量时间序列

        Returns:
            MomentumFeatures 特征对象
        """
        # 计算全场压制力总和
        total_pressure_home = sum(s['home'] for s in series)
        total_pressure_away = sum(s['away'] for s in series)
        pressure_diff = total_pressure_home - total_pressure_away

        # 计算压制力波动
        net_momentum = [s['net'] for s in series]
        pressure_variance = np.var(net_momentum) if net_momentum else 0.0
        pressure_std = np.std(net_momentum) if net_momentum else 0.0

        # 变异系数 (标准化波动率)
        mean_pressure = np.mean(np.abs(net_momentum)) if net_momentum else 1.0
        pressure_cv = pressure_std / mean_pressure if mean_pressure > 0 else 0.0

        # 前 15 分钟动量
        first_15 = [s for s in series if s['minute'] <= 15]
        first_15_pressure_home = sum(s['home'] for s in first_15)
        first_15_pressure_away = sum(s['away'] for s in first_15)

        # 后 15 分钟动量
        last_15 = [s for s in series if s['minute'] >= 75]
        last_15_pressure_home = sum(s['home'] for s in last_15)
        last_15_pressure_away = sum(s['away'] for s in last_15)

        # 动量转换次数
        momentum_shifts = self._count_momentum_shifts(net_momentum)

        # 最大动量摆动
        max_swing = max(net_momentum) - min(net_momentum) if net_momentum else 0.0

        # 主客队统治时间
        home_dominance = sum(1 for s in series if s['net'] > 0)
        away_dominance = sum(1 for s in series if s['net'] < 0)

        return MomentumFeatures(
            total_pressure_home=total_pressure_home,
            total_pressure_away=total_pressure_away,
            pressure_diff=pressure_diff,
            pressure_variance=pressure_variance,
            pressure_std=pressure_std,
            pressure_cv=pressure_cv,
            first_15_min_pressure_home=first_15_pressure_home,
            first_15_min_pressure_away=first_15_pressure_away,
            last_15_min_pressure_home=last_15_pressure_home,
            last_15_min_pressure_away=last_15_pressure_away,
            momentum_shifts=momentum_shifts,
            max_momentum_swing=max_swing,
            home_dominance_minutes=home_dominance,
            away_dominance_minutes=away_dominance,
        )

    def _count_momentum_shifts(self, net_momentum: List[float]) -> int:
        """
        计算动量转换次数

        Args:
            net_momentum: 净动量序列

        Returns:
            转换次数
        """
        if not net_momentum:
            return 0

        shifts = 0
        current_sign = 1 if net_momentum[0] > 0 else (-1 if net_momentum[0] < 0 else 0)

        for value in net_momentum[1:]:
            sign = 1 if value > 0 else (-1 if value < 0 else 0)
            if sign != 0 and sign != current_sign:
                shifts += 1
                current_sign = sign

        return shifts

    def to_feature_dict(self, features: MomentumFeatures) -> Dict[str, float]:
        """
        将 MomentumFeatures 转换为特征字典

        Args:
            features: 动量特征对象

        Returns:
            特征字典
        """
        if not features:
            return {}

        return {
            'momentum_total_home': features.total_pressure_home,
            'momentum_total_away': features.total_pressure_away,
            'momentum_diff': features.pressure_diff,
            'momentum_variance': features.pressure_variance,
            'momentum_std': features.pressure_std,
            'momentum_cv': features.pressure_cv,
            'momentum_first_15_home': features.first_15_min_pressure_home,
            'momentum_first_15_away': features.first_15_min_pressure_away,
            'momentum_first_15_diff': features.first_15_min_pressure_home - features.first_15_min_pressure_away,
            'momentum_last_15_home': features.last_15_min_pressure_home,
            'momentum_last_15_away': features.last_15_min_pressure_away,
            'momentum_last_15_diff': features.last_15_min_pressure_home - features.last_15_min_pressure_away,
            'momentum_shifts': features.momentum_shifts,
            'momentum_max_swing': features.max_momentum_swing,
            'momentum_home_dominance_min': features.home_dominance_minutes,
            'momentum_away_dominance_min': features.away_dominance_minutes,
        }
