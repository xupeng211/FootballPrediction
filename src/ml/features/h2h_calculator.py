"""
历史交锋统计计算器 - Head-to-Head Calculator

Phase 5 Advanced Features 核心组件之一

专门用于计算两队之间的历史对战统计，解决Phase 4中识别的"克星"效应问题。
历史交锋记录能够捕捉传统优势、心理优势和战术克制等因素。

主要功能：
1. 计算两队历史胜率统计
2. 计算平均进球差
3. 计算平均总进球数
4. 统计历史交锋场次数量

目标：通过历史交锋特征将模型准确率提升3-5%
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class H2HStats:
    """历史交锋统计数据结构"""
    home_win_rate: float = 0.5  # 主队历史胜率
    avg_goal_diff: float = 0.0  # 平均进球差
    avg_total_goals: float = 2.5  # 平均总进球数
    matches_count: int = 0  # 交锋场次

    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式"""
        return {
            'h2h_home_win_rate': self.home_win_rate,
            'h2h_avg_goal_diff': self.avg_goal_diff,
            'h2h_avg_total_goals': self.avg_total_goals,
            'h2h_matches_count': self.matches_count
        }


class H2HCalculator:
    """
    历史交锋统计计算器

    基于两队的历史对战记录，计算多维度统计数据，为模型提供历史交锋特征。
    这些特征能够捕捉"克星"效应、传统优势和心理因素。
    """

    def __init__(self, min_matches: int = 0):
        """
        初始化历史交锋计算器

        Args:
            min_matches: 最小历史交锋场次，少于该场次的比赛使用默认值
        """
        self.min_matches = min_matches
        logger.info(f"H2HCalculator 初始化完成，最小交锋场次: {min_matches}")

    def calculate_h2h_for_match(self, df: pd.DataFrame, home_id: int, away_id: int,
                               match_date: pd.Timestamp) -> H2HStats:
        """
        为特定比赛计算历史交锋统计

        Args:
            df: 包含所有历史比赛的DataFrame
            home_id: 主队ID
            away_id: 客队ID
            match_date: 当前比赛日期

        Returns:
            H2HStats: 历史交锋统计数据
        """
        try:
            # 获取两队历史交锋记录（排除当前比赛）
            past_matches = self._get_historical_matches(df, home_id, away_id, match_date)

            if len(past_matches) < self.min_matches:
                logger.debug(f"历史交锋场次不足: {len(past_matches)} < {self.min_matches}")
                return self._get_default_stats()

            # 计算各项统计指标
            stats = self._calculate_match_stats(past_matches, home_id)

            logger.debug(f"H2H统计完成: {home_id} vs {away_id}, "
                        f"场次: {stats.matches_count}, 主队胜率: {stats.home_win_rate:.3f}")

            return stats

        except Exception as e:
            logger.error(f"计算H2H统计失败: {str(e)}")
            return self._get_default_stats()

    def calculate_h2h_for_all_matches(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        为DataFrame中的所有比赛计算历史交锋统计

        Args:
            df: 包含所有比赛的DataFrame

        Returns:
            pd.DataFrame: 添加了H2H特征的DataFrame
        """
        logger.info("开始计算所有比赛的历史交锋统计...")

        # 按日期排序确保时间顺序
        df_sorted = df.sort_values('match_date').copy()

        # 初始化H2H特征列
        h2h_features = []

        for idx, match in df_sorted.iterrows():
            home_id = int(match['home_team_id'])
            away_id = int(match['away_team_id'])
            match_date = pd.to_datetime(match['match_date'])

            # 计算该场比赛的历史交锋统计
            h2h_stats = self.calculate_h2h_for_match(df_sorted, home_id, away_id, match_date)

            # 将统计结果添加到特征列表
            h2h_features.append(h2h_stats.to_dict())

        # 将H2H特征添加到DataFrame
        h2h_df = pd.DataFrame(h2h_features)
        result_df = pd.concat([df_sorted.reset_index(drop=True), h2h_df], axis=1)

        logger.info(f"H2H特征计算完成，新增特征: {list(h2h_df.columns)}")

        return result_df

    def _get_historical_matches(self, df: pd.DataFrame, home_id: int, away_id: int,
                               match_date: pd.Timestamp) -> pd.DataFrame:
        """获取两队在指定日期前的历史交锋记录"""

        # 查找两队之间的历史比赛（不考虑主客场顺序）
        h2h_mask = (
            ((df['home_team_id'] == home_id) & (df['away_team_id'] == away_id)) |
            ((df['home_team_id'] == away_id) & (df['away_team_id'] == home_id))
        )

        # 只获取当前日期前的比赛
        date_mask = pd.to_datetime(df['match_date']) < match_date

        past_matches = df[h2h_mask & date_mask].sort_values('match_date')

        return past_matches

    def _calculate_match_stats(self, past_matches: pd.DataFrame, target_home_id: int) -> H2HStats:
        """基于历史比赛计算统计数据"""

        if past_matches.empty:
            return self._get_default_stats()

        # 1. 计算主队历史胜率
        home_wins = 0
        goal_diffs = []
        total_goals = []

        for _, match in past_matches.iterrows():
            home_score = int(match['home_score'])
            away_score = int(match['away_score'])

            # 判断目标主队是否获胜
            if match['home_team_id'] == target_home_id:
                # 目标队是主队
                if home_score > away_score:
                    home_wins += 1
                goal_diff = home_score - away_score
            else:
                # 目标队是客队
                if away_score > home_score:
                    home_wins += 1
                goal_diff = away_score - home_score

            goal_diffs.append(goal_diff)
            total_goals.append(home_score + away_score)

        # 2. 计算统计指标
        stats = H2HStats()
        stats.matches_count = len(past_matches)
        stats.home_win_rate = home_wins / stats.matches_count if stats.matches_count > 0 else 0.5
        stats.avg_goal_diff = np.mean(goal_diffs) if goal_diffs else 0.0
        stats.avg_total_goals = np.mean(total_goals) if total_goals else 2.5

        return stats

    def _get_default_stats(self) -> H2HStats:
        """获取默认统计数据（用于无历史交锋记录的情况）"""
        return H2HStats(
            home_win_rate=0.5,  # 默认50%胜率
            avg_goal_diff=0.0,  # 默认0进球差
            avg_total_goals=2.5,  # 默认平均2.5球
            matches_count=0
        )

    def get_h2h_summary(self, df: pd.DataFrame, team1_id: int, team2_id: int) -> Dict:
        """
        获取两队历史交锋的详细摘要

        Args:
            df: 包含所有比赛的DataFrame
            team1_id: 第一队ID
            team2_id: 第二队ID

        Returns:
            Dict: 详细的历史交锋摘要
        """
        # 获取所有交锋记录
        all_matches = self._get_historical_matches(
            df, team1_id, team2_id, pd.Timestamp.max
        )

        if all_matches.empty:
            return {
                'teams': [team1_id, team2_id],
                'total_matches': 0,
                'team1_wins': 0,
                'team2_wins': 0,
                'draws': 0,
                'team1_goals': 0,
                'team2_goals': 0,
                'last_match_date': None
            }

        # 统计各项数据
        team1_wins = team2_wins = draws = 0
        team1_goals = team2_goals = 0
        last_match_date = None

        for _, match in all_matches.iterrows():
            home_id = int(match['home_team_id'])
            away_id = int(match['away_team_id'])
            home_score = int(match['home_score'])
            away_score = int(match['away_score'])
            match_date = pd.to_datetime(match['match_date'])

            # 统计进球
            if home_id == team1_id:
                team1_goals += home_score
                team2_goals += away_score
            else:
                team1_goals += away_score
                team2_goals += home_score

            # 统计胜负
            if home_score > away_score:
                if home_id == team1_id:
                    team1_wins += 1
                else:
                    team2_wins += 1
            elif away_score > home_score:
                if away_id == team1_id:
                    team1_wins += 1
                else:
                    team2_wins += 1
            else:
                draws += 1

            # 记录最近比赛日期
            if last_match_date is None or match_date > last_match_date:
                last_match_date = match_date

        return {
            'teams': [team1_id, team2_id],
            'total_matches': len(all_matches),
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'draws': draws,
            'team1_goals': team1_goals,
            'team2_goals': team2_goals,
            'team1_win_rate': team1_wins / len(all_matches) if len(all_matches) > 0 else 0,
            'last_match_date': last_match_date.isoformat() if last_match_date else None,
            'avg_goals_per_match': (team1_goals + team2_goals) / len(all_matches) if len(all_matches) > 0 else 0
        }


# 使用示例
if __name__ == "__main__":
    # 示例数据
    sample_data = {
        'home_team_id': [1, 2, 1, 3, 2],
        'away_team_id': [2, 1, 2, 1, 1],
        'home_score': [2, 1, 0, 1, 3],
        'away_score': [1, 2, 0, 0, 1],
        'match_date': ['2024-01-01', '2024-01-15', '2024-02-01', '2024-02-15', '2024-03-01']
    }

    df = pd.DataFrame(sample_data)
    df['match_date'] = pd.to_datetime(df['match_date'])

    # 创建H2H计算器
    h2h_calc = H2HCalculator(min_matches=1)

    # 计算H2H统计
    h2h_stats = h2h_calc.calculate_h2h_for_match(df, 1, 2, pd.Timestamp('2024-03-15'))
    print(f"H2H统计结果: {h2h_stats.to_dict()}")

    # 获取详细摘要
    summary = h2h_calc.get_h2h_summary(df, 1, 2)
    print(f"交锋摘要: {summary}")