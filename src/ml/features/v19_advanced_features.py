#!/usr/bin/env python3
"""
V19.0 高级动态特征 - Step B 实现核心模块

三大核心特征：
1. Elo_Relative_Gap: 双方实时战力差值（动态 ELO）
2. Fatigue_Index: 疲劳度指数（最近7天欧战/杯赛负担）
3. Relegation_Incentive: 保级战意（最后5轮生死线）

Author: V19.0 Quant Team
Purpose: 引入高级动态特征，提升模型对"稳胆翻车"的识别能力
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CompetitionLevel(Enum):
    """比赛级别枚举"""
    LOW = 1  # 联赛杯、足总杯早期
    MEDIUM = 2  # 英超联赛
    HIGH = 3  # 欧联杯
    EXTREME = 4  # 欧冠


@dataclass
class MatchSchedule:
    """比赛赛程数据结构"""
    team: str
    match_date: datetime
    competition: str
    is_home: bool
    days_rest: int  # 距离上场比赛的休息天数
    travel_distance: Optional[int] = None  # 客场旅行距离（公里）


class EloRelativeGapFeature:
    """
    ELO 相对差距特征

    核心思想：
    - 传统 ELO 只看绝对值，但足球是相对运动
    - 强队 vs 弱队的 ELO 差 = 200，但如果是强队客场 + 疲劳，差距会缩小
    - 引入动态调整因子：主场、疲劳、赛程密度

    公式：
    ELO_Relative_Gap = (Home_Elo - Away_Elo) * Adjustment_Factor

    Adjustment_Factor = Base * Home_Advantage * Fatigue_Penalty * Schedule_Density
    """

    # ELO 基础参数
    DEFAULT_ELO = 1500.0
    HOME_ADVANTAGE_ELO = 50.0  # 主场优势 ELO 加成

    # 动态调整参数
    FATIGUE_PENALTY_PER_DAY = 5.0  # 每疲劳一天的 ELO 惩罚
    SCHEDULE_DENSITY_PENALTY = 10.0  # 密集赛程惩罚

    def __init__(self):
        """初始化 ELO 相对差距特征"""
        # 存储 ELO 评分（需要从历史数据中初始化）
        self.team_elos: Dict[str, float] = {}

        logger.info("ELO Relative Gap 特征提取器初始化完成")

    def calculate_elo_gap(
        self,
        home_team: str,
        away_team: str,
        home_fatigue: float = 0.0,
        away_fatigue: float = 0.0,
        home_schedule_density: float = 0.0,
        away_schedule_density: float = 0.0,
    ) -> Dict[str, float]:
        """
        计算调整后的 ELO 相对差距

        Args:
            home_team: 主队名称
            away_team: 客队名称
            home_fatigue: 主队疲劳度 (0-1)
            away_fatigue: 客队疲劳度 (0-1)
            home_schedule_density: 主队赛程密度 (0-1)
            away_schedule_density: 客队赛程密度 (0-1)

        Returns:
            Dict: {
                'raw_elo_gap': 原始 ELO 差距,
                'adjusted_elo_gap': 调整后 ELO 差距,
                'home_elo_effective': 主队有效 ELO,
                'away_elo_effective': 客队有效 ELO,
                'adjustment_factor': 调整因子
            }
        """
        # 获取基础 ELO
        home_elo = self.team_elos.get(home_team, self.DEFAULT_ELO)
        away_elo = self.team_elos.get(away_team, self.DEFAULT_ELO)

        # 原始差距（含主场优势）
        raw_elo_gap = (home_elo + self.HOME_ADVANTAGE_ELO) - away_elo

        # 疲劳调整因子（疲劳越多，ELO 打折越多）
        home_fatigue_penalty = home_fatigue * self.FATIGUE_PENALTY_PER_DAY * 20
        away_fatigue_penalty = away_fatigue * self.FATIGUE_PENALTY_PER_DAY * 20

        # 赛程密度调整（赛程越密，ELO 打折越多）
        home_density_penalty = home_schedule_density * self.SCHEDULE_DENSITY_PENALTY
        away_density_penalty = away_schedule_density * self.SCHEDULE_DENSITY_PENALTY

        # 有效 ELO
        home_elo_effective = home_elo - home_fatigue_penalty - home_density_penalty
        away_elo_effective = away_elo - away_fatigue_penalty - away_density_penalty

        # 调整后 ELO 差距
        adjusted_elo_gap = (home_elo_effective + self.HOME_ADVANTAGE_ELO) - away_elo_effective

        # 计算调整因子（用于特征工程）
        adjustment_factor = adjusted_elo_gap / max(abs(raw_elo_gap), 1.0)

        return {
            'raw_elo_gap': raw_elo_gap,
            'adjusted_elo_gap': adjusted_elo_gap,
            'home_elo_effective': home_elo_effective,
            'away_elo_effective': away_elo_effective,
            'adjustment_factor': adjustment_factor,
            'fatigue_impact': abs(home_fatigue_penalty - away_fatigue_penalty),
            'schedule_impact': abs(home_density_penalty - away_density_penalty),
        }

    def update_elos_from_result(
        self,
        home_team: str,
        away_team: str,
        home_goals: int,
        away_goals: int,
        k_factor: float = 20.0
    ):
        """
        根据比赛结果更新 ELO 评分

        Args:
            home_team: 主队
            away_team: 客队
            home_goals: 主队进球
            away_goals: 客队进球
            k_factor: K 因子
        """
        # 获取当前 ELO
        home_elo = self.team_elos.get(home_team, self.DEFAULT_ELO)
        away_elo = self.team_elos.get(away_team, self.DEFAULT_ELO)

        # 计算预期结果
        expected_home = 1.0 / (1.0 + 10.0 ** ((away_elo - home_elo - self.HOME_ADVANTAGE_ELO) / 400.0))

        # 实际结果
        if home_goals > away_goals:
            actual_home = 1.0
        elif home_goals < away_goals:
            actual_home = 0.0
        else:
            actual_home = 0.5

        # 更新 ELO
        home_elo_change = k_factor * (actual_home - expected_home)
        away_elo_change = -home_elo_change  # 零和游戏

        self.team_elos[home_team] = home_elo + home_elo_change
        self.team_elos[away_team] = away_elo + away_elo_change

        logger.debug(
            f"ELO 更新: {home_team} {home_elo:.1f}->{self.team_elos[home_team]:.1f} "
            f"({home_elo_change:+.1f}), {away_team} {away_elo:.1f}->{self.team_elos[away_team]:.1f} "
            f"({away_elo_change:+.1f})"
        )


class FatigueIndexFeature:
    """
    疲劳度指数特征

    核心思想：
    - 过去 7 天的比赛负担影响当前表现
    - 欧战/杯赛 = 额外疲劳（强度更高）
    - 客场长途旅行 = 额外疲劳
    - 连续作战 = 疲劳累积

    公式：
    Fatigue_Index = Base_Fatigue + Competition_Multiplier + Travel_Penalty + Accumulation_Factor
    """

    # 疲劳参数
    BASE_FATIGUE_PER_MATCH = 0.3  # 每场比赛基础疲劳
    COMPETITION_MULTIPLIER = {
        "league": 1.0,
        "fa_cup": 1.2,
        "carabao_cup": 1.1,
        "europa_league": 1.5,
        "champions_league": 1.8,
    }
    TRAVEL_PENALTY_PER_500KM = 0.1  # 每 500 公里旅行惩罚
    ACCUMULATION_FACTOR = 0.2  # 疲劳累积因子（连续作战）

    def __init__(self):
        """初始化疲劳度特征"""
        # 存储球队赛程历史
        self.team_schedules: Dict[str, List[MatchSchedule]] = {}

        logger.info("Fatigue Index 特征提取器初始化完成")

    def calculate_fatigue(
        self,
        team: str,
        match_date: datetime,
        lookback_days: int = 7
    ) -> Dict[str, float]:
        """
        计算球队疲劳度指数

        Args:
            team: 球队名称
            match_date: 当前比赛日期
            lookback_days: 回溯天数

        Returns:
            Dict: {
                'fatigue_index': 总体疲劳指数 (0-1),
                'matches_played': 过去N天比赛场次,
                'competition_fatigue': 欧战/杯赛疲劳,
                'travel_fatigue': 旅行疲劳,
                'accumulation_fatigue': 连续作战疲劳,
                'rest_days': 距离上场比赛休息天数
            }
        """
        schedules = self.team_schedules.get(team, [])

        # 筛选回溯窗口内的比赛
        cutoff_date = match_date - timedelta(days=lookback_days)
        recent_matches = [
            s for s in schedules
            if cutoff_date <= s.match_date < match_date
        ]

        if not recent_matches:
            return {
                'fatigue_index': 0.0,
                'matches_played': 0,
                'competition_fatigue': 0.0,
                'travel_fatigue': 0.0,
                'accumulation_fatigue': 0.0,
                'rest_days': 999,  # 无近期比赛
            }

        # 按时间排序
        recent_matches.sort(key=lambda x: x.match_date)

        # 基础疲劳（比赛场次）
        matches_played = len(recent_matches)
        base_fatigue = matches_played * self.BASE_FATIGUE_PER_MATCH

        # 比赛级别疲劳
        competition_fatigue = 0.0
        for match in recent_matches:
            multiplier = self.COMPETITION_MULTIPLIER.get(
                match.competition.lower().replace(" ", "_"),
                1.0
            )
            competition_fatigue += (self.BASE_FATIGUE_PER_MATCH * multiplier)

        # 旅行疲劳
        travel_fatigue = 0.0
        for match in recent_matches:
            if not match.is_home and match.travel_distance:
                travel_penalty = (match.travel_distance / 500.0) * self.TRAVEL_PENALTY_PER_500KM
                travel_fatigue += travel_penalty

        # 连续作战疲劳（检查是否有连续 3 天内 2 场比赛）
        accumulation_fatigue = 0.0
        for i in range(len(recent_matches) - 1):
            days_between = (recent_matches[i + 1].match_date - recent_matches[i].match_date).days
            if days_between <= 3:
                accumulation_fatigue += self.ACCUMULATION_FACTOR

        # 总体疲劳指数（归一化到 0-1）
        total_fatigue = base_fatigue + competition_fatigue + travel_fatigue + accumulation_fatigue
        fatigue_index = min(total_fatigue / 2.0, 1.0)  # 上限 1.0

        # 计算休息天数
        last_match = recent_matches[-1]
        rest_days = (match_date - last_match.match_date).days

        return {
            'fatigue_index': fatigue_index,
            'matches_played': matches_played,
            'competition_fatigue': min(competition_fatigue, 1.0),
            'travel_fatigue': min(travel_fatigue, 1.0),
            'accumulation_fatigue': min(accumulation_fatigue, 1.0),
            'rest_days': rest_days,
        }

    def add_match_schedule(
        self,
        team: str,
        match_date: datetime,
        competition: str,
        is_home: bool,
        travel_distance: Optional[int] = None
    ):
        """添加比赛赛程记录"""
        if team not in self.team_schedules:
            self.team_schedules[team] = []

        schedule = MatchSchedule(
            team=team,
            match_date=match_date,
            competition=competition,
            is_home=is_home,
            days_rest=0,  # 将在计算时动态确定
            travel_distance=travel_distance
        )

        self.team_schedules[team].append(schedule)


class RelegationIncentiveFeature:
    """
    保级战意特征

    核心思想：
    - 最后 5 轮的保级队战意更强
    - 保级生死线（距离降级区 ≤ 3 分）
    - 保级队对战已无欲无求的中游队 = 更强战意

    公式：
    Relegation_Incentive =
        Base_Incentive *
        (Is_Relegation_Zone ? 2.0 : 1.0) *
        (Last_5_Games ? 1.5 : 1.0) *
        (Opponent_Safe ? 1.3 : 1.0)
    """

    # 保级战意参数
    RELEGATION_ZONE_THRESHOLD = 3  # 距离降级区 3 分内
    LAST_GAMES_THRESHOLD = 5  # 最后 N 轮
    SAFE_TEAM_POINTS_BUFFER = 10  # 安全线：领先降级区 10 分以上

    def __init__(self):
        """初始化保级战意特征"""
        # 存储积分榜数据 {season: {team: points}}
        self.standings: Dict[str, Dict[str, int]] = {}

        logger.info("Relegation Incentive 特征提取器初始化完成")

    def calculate_incentive(
        self,
        team: str,
        team_points: int,
        relegation_zone_points: int,
        games_remaining: int,
        opponent_safe: bool = False
    ) -> Dict[str, float]:
        """
        计算保级战意指数

        Args:
            team: 球队名称
            team_points: 球队当前积分
            relegation_zone_points: 降级区积分
            games_remaining: 剩余轮次
            opponent_safe: 对手是否已无欲无求

        Returns:
            Dict: {
                'incentive_index': 战意指数 (0-1),
                'is_relegation_battle': 是否保级战,
                'points_from_safety': 距离安全线分差,
                'last_5_games': 是否最后5轮,
                ' desperation_level': 绝望程度 (0-1)
            }
        """
        # 计算距离降级区分差
        points_from_danger = team_points - relegation_zone_points

        # 是否在保级区
        in_relegation_zone = points_from_danger <= self.RELEGATION_ZONE_THRESHOLD

        # 是否最后 N 轮
        is_last_games = games_remaining <= self.LAST_GAMES_THRESHOLD

        # 绝望程度（分差越小，绝望程度越高）
        desperation_level = 0.0
        if in_relegation_zone:
            # 在降级区内：分差越小越绝望
            desperation_level = 1.0 - min(points_from_danger / self.RELEGATION_ZONE_THRESHOLD, 1.0)
        elif points_from_danger < self.SAFE_TEAM_POINTS_BUFFER:
            # 接近降级区：有一定压力
            desperation_level = 1.0 - (points_from_danger / self.SAFE_TEAM_POINTS_BUFFER)

        # 基础战意
        base_incentive = 0.3  # 默认战意

        # 保级战加成
        relegation_multiplier = 2.0 if in_relegation_zone else 1.0

        # 最后轮次加成
        last_games_multiplier = 1.5 if is_last_games else 1.0

        # 对手无欲无求加成
        opponent_multiplier = 1.3 if opponent_safe else 1.0

        # 计算最终战意指数
        incentive_index = (
            base_incentive *
            relegation_multiplier *
            last_games_multiplier *
            opponent_multiplier *
            (1 + desperation_level)  # 绝望程度加成
        )

        # 归一化到 0-1
        incentive_index = min(incentive_index / 1.5, 1.0)

        return {
            'incentive_index': incentive_index,
            'is_relegation_battle': in_relegation_zone,
            'points_from_safety': max(0, points_from_danger),
            'last_5_games': is_last_games,
            'desperation_level': desperation_level,
            'games_remaining': games_remaining,
        }

    def update_standings(self, season: str, team: str, points: int):
        """更新积分榜"""
        if season not in self.standings:
            self.standings[season] = {}

        self.standings[season][team] = points


class V19AdvancedFeatureExtractor:
    """
    V19.0 高级特征提取器 - 统一入口

    整合三大核心特征：
    1. Elo_Relative_Gap
    2. Fatigue_Index
    3. Relegation_Incentive
    """

    def __init__(self):
        """初始化 V19.0 高级特征提取器"""
        self.elo_feature = EloRelativeGapFeature()
        self.fatigue_feature = FatigueIndexFeature()
        self.relegation_feature = RelegationIncentiveFeature()

        logger.info("V19.0 高级特征提取器初始化完成")

    def extract_features(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        season: str,
        home_points: int,
        away_points: int,
        relegation_zone_points: int,
        games_remaining: int,
        home_recent_matches: Optional[List[Dict]] = None,
        away_recent_matches: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        提取 V19.0 高级特征

        Args:
            home_team: 主队名称
            away_team: 客队名称
            match_date: 比赛日期
            season: 赛季标识
            home_points: 主队积分
            away_points: 客队积分
            relegation_zone_points: 降级区积分
            games_remaining: 剩余轮次
            home_recent_matches: 主队近期比赛（用于疲劳度计算）
            away_recent_matches: 客队近期比赛

        Returns:
            Dict: 所有 V19.0 特征
        """
        features = {}

        # 1. ELO 相对差距特征
        home_fatigue = 0.0
        away_fatigue = 0.0

        if home_recent_matches:
            home_fatigue_data = self.fatigue_feature.calculate_fatigue(
                home_team, match_date, lookback_days=7
            )
            home_fatigue = home_fatigue_data['fatigue_index']

        if away_recent_matches:
            away_fatigue_data = self.fatigue_feature.calculate_fatigue(
                away_team, match_date, lookback_days=7
            )
            away_fatigue = away_fatigue_data['fatigue_index']

        elo_gap_data = self.elo_feature.calculate_elo_gap(
            home_team=home_team,
            away_team=away_team,
            home_fatigue=home_fatigue,
            away_fatigue=away_fatigue,
            home_schedule_density=0.0,  # 可从赛历中获取
            away_schedule_density=0.0,
        )

        features.update({f'elo_{k}': v for k, v in elo_gap_data.items()})

        # 2. 疲劳度特征（主队和客队）
        home_fatigue_data = self.fatigue_feature.calculate_fatigue(home_team, match_date)
        away_fatigue_data = self.fatigue_feature.calculate_fatigue(away_team, match_date)

        features['home_fatigue_index'] = home_fatigue_data['fatigue_index']
        features['away_fatigue_index'] = away_fatigue_data['fatigue_index']
        features['fatigue_diff'] = home_fatigue_data['fatigue_index'] - away_fatigue_data['fatigue_index']
        features['home_rest_days'] = home_fatigue_data['rest_days']
        features['away_rest_days'] = away_fatigue_data['rest_days']

        # 3. 保级战意特征（主队和客队）
        home_incentive_data = self.relegation_feature.calculate_incentive(
            team=home_team,
            team_points=home_points,
            relegation_zone_points=relegation_zone_points,
            games_remaining=games_remaining,
            opponent_safe=False  # 可根据对手积分判断
        )

        away_incentive_data = self.relegation_feature.calculate_incentive(
            team=away_team,
            team_points=away_points,
            relegation_zone_points=relegation_zone_points,
            games_remaining=games_remaining,
            opponent_safe=False
        )

        features['home_relegation_incentive'] = home_incentive_data['incentive_index']
        features['away_relegation_incentive'] = away_incentive_data['incentive_index']
        features['incentive_diff'] = home_incentive_data['incentive_index'] - away_incentive_data['incentive_index']
        features['home_desperation'] = home_incentive_data['desperation_level']
        features['away_desperation'] = away_incentive_data['desperation_level']

        return features


def main():
    """演示 V19.0 高级特征提取"""
    print("V19.0 高级特征提取器演示")
    print("=" * 80)

    extractor = V19AdvancedFeatureExtractor()

    # 模拟数据
    match_date = datetime(2024, 5, 15)  # 赛季末

    features = extractor.extract_features(
        home_team="Arsenal",
        away_team="Everton",
        match_date=match_date,
        season="23/24",
        home_points=75,
        away_points=30,
        relegation_zone_points=32,
        games_remaining=3,
    )

    print("\n📊 V19.0 高级特征:")
    for key, value in features.items():
        print(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")


if __name__ == "__main__":
    main()
