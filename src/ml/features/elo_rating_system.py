#!/usr/bin/env python3
"""
Elo评级系统 - 足球队实时战力动态评估

Phase 5 Advanced Features 核心组件之一

基于传统Elo评级系统，针对足球比赛特点进行优化：
- 支持主客场优势调整
- 考虑净胜球对评分变化的影响
- 动态K值调整（基于比赛重要性和球队实力差距）

核心公式：
R_new = R_old + K × (Actual - Expected)

其中：
- R_new: 更新后的评分
- R_old: 当前评分
- K: K因子（权重参数）
- Actual: 实际比赛结果（1=胜, 0.5=平, 0=负）
- Expected: 预期得分

Author: Football Prediction Team
Version: 1.0.0
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class EloRatingSystem:
    """
    Elo评级系统 - 足球专用版本

    主要功能：
    1. 动态更新球队Elo评分
    2. 计算比赛预期结果
    3. 支持主客场优势调整
    4. 基于净胜球的评分调整
    5. 历史评分趋势追踪
    """

    # 默认Elo参数
    DEFAULT_RATING = 1500.0  # 初始评分
    K_FACTOR = 40.0  # 基础K因子
    HOME_ADVANTAGE = 50.0  # 主场优势（Elo分）

    # K因子动态调整参数
    K_ADJUSTMENT = {
        "friendly": 20.0,  # 友谊赛
        "league": 40.0,  # 联赛比赛
        "cup": 50.0,  # 杯赛
        "continental": 60.0,  # 大洲俱乐部比赛
        "world_cup": 70.0,  # 世界杯
    }

    # 净胜球调整参数
    GOAL_MARGIN_MULTIPLIER = {
        1: 1.0,  # 1球险胜
        2: 1.5,  # 2球优势
        3: 1.75,  # 3球优势
        4: 1.875,  # 4球优势
        5: 1.9375,  # 5球+优势
    }

    def __init__(
        self,
        initial_rating: float = DEFAULT_RATING,
        home_advantage: float = HOME_ADVANTAGE,
        base_k_factor: float = K_FACTOR,
        enable_goal_margin: bool = True,
        enable_dynamic_k: bool = True,
        rating_decay_days: int = 365,  # 评分衰减周期
    ):
        """
        初始化Elo评级系统

        Args:
            initial_rating: 初始评分
            home_advantage: 主场优势评分
            base_k_factor: 基础K因子
            enable_goal_margin: 是否启用净胜球调整
            enable_dynamic_k: 是否启用动态K因子
            rating_decay_days: 评分衰减天数
        """
        self.initial_rating = initial_rating
        self.home_advantage = home_advantage
        self.base_k_factor = base_k_factor
        self.enable_goal_margin = enable_goal_margin
        self.enable_dynamic_k = enable_dynamic_k
        self.rating_decay_days = rating_decay_days

        # 存储球队当前评分
        self.team_ratings: dict[str, float] = {}

        # 存储评分历史（用于趋势分析）
        self.rating_history: dict[str, list[tuple[datetime, float]]] = {}

        # 统计信息
        self.stats = {
            "total_updates": 0,
            "avg_rating_change": 0.0,
            "max_rating": initial_rating,
            "min_rating": initial_rating,
            "last_updated": None,
        }

        logger.info(
            f"Elo评级系统初始化完成: 初始评分={initial_rating}, 主场优势={home_advantage}, K因子={base_k_factor}"
        )

    def get_team_rating(self, team_id: str, as_of_date: datetime | None = None) -> float:
        """
        获取球队Elo评分

        Args:
            team_id: 球队ID
            as_of_date: 指定日期的评分（考虑历史评分）

        Returns:
            float: Elo评分
        """
        if team_id not in self.team_ratings:
            return self.initial_rating

        base_rating = self.team_ratings[team_id]

        # 如果指定了日期，考虑评分衰减
        if as_of_date and team_id in self.rating_history:
            current_time = datetime.now()
            if isinstance(as_of_date, str):
                as_of_date = datetime.fromisoformat(as_of_date)

            days_diff = (current_time - as_of_date).days
            if days_diff > self.rating_decay_days:
                # 应用时间衰减：每天衰减0.1%
                decay_factor = 1.0 - (days_diff * 0.001)
                base_rating *= max(0.5, decay_factor)  # 最低保留50%评分

        return base_rating

    def calculate_expected_score(
        self,
        home_team_id: str,
        away_team_id: str,
        home_rating_override: float | None = None,
        away_rating_override: float | None = None,
    ) -> tuple[float, float, float]:
        """
        计算比赛预期得分

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            home_rating_override: 主队评分覆盖（用于假设分析）
            away_rating_override: 客队评分覆盖（用于假设分析）

        Returns:
            Tuple[float, float, float]: (主队预期得分, 客队预期得分, 主胜概率)
        """
        # 获取球队评分
        home_rating = home_rating_override or self.get_team_rating(home_team_id)
        away_rating = away_rating_override or self.get_team_rating(away_team_id)

        # 应用主场优势
        home_rating_adjusted = home_rating + self.home_advantage

        # 计算预期得分
        # 预期得分公式：E_A = 1 / (1 + 10^((R_B - R_A) / 400))
        rating_diff = away_rating - home_rating_adjusted
        expected_home = 1.0 / (1.0 + pow(10.0, rating_diff / 400.0))
        expected_away = 1.0 - expected_home

        # 计算主胜概率
        home_win_prob = expected_home

        return expected_home, expected_away, home_win_prob

    def update_ratings(
        self,
        home_team_id: str,
        away_team_id: str,
        home_goals: int,
        away_goals: int,
        match_date: datetime | None = None,
        competition_type: str = "league",
        home_k_factor_override: float | None = None,
        away_k_factor_override: float | None = None,
    ) -> dict[str, Any]:
        """
        更新球队Elo评分

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            home_goals: 主队进球数
            away_goals: 客队进球数
            match_date: 比赛日期
            competition_type: 比赛类型（影响K因子）
            home_k_factor_override: 主队K因子覆盖
            away_k_factor_override: 客队K因子覆盖

        Returns:
            Dict[str, Any]: 更新结果详情
        """
        match_date = match_date or datetime.now()

        # 确保球队有初始评分
        for team_id in [home_team_id, away_team_id]:
            if team_id not in self.team_ratings:
                self.team_ratings[team_id] = self.initial_rating
                self.rating_history[team_id] = [(match_date, self.initial_rating)]

        # 获取当前评分
        old_home_rating = self.team_ratings[home_team_id]
        old_away_rating = self.team_ratings[away_team_id]

        # 计算预期得分
        expected_home, expected_away, _ = self.calculate_expected_score(home_team_id, away_team_id)

        # 确定实际得分
        if home_goals > away_goals:
            actual_home = 1.0
            actual_away = 0.0
        elif home_goals < away_goals:
            actual_home = 0.0
            actual_away = 1.0
        else:
            actual_home = 0.5
            actual_away = 0.5

        # 计算K因子
        home_k_factor = home_k_factor_override or self._calculate_k_factor(home_team_id, competition_type)
        away_k_factor = away_k_factor_override or self._calculate_k_factor(away_team_id, competition_type)

        # 应用净胜球调整
        goal_multiplier = 1.0
        if self.enable_goal_margin:
            goal_diff = abs(home_goals - away_goals)
            goal_multiplier = self.GOAL_MARGIN_MULTIPLIER.get(min(goal_diff, 5), self.GOAL_MARGIN_MULTIPLIER[5])

        # 计算评分变化
        home_rating_change = home_k_factor * goal_multiplier * (actual_home - expected_home)
        away_rating_change = away_k_factor * goal_multiplier * (actual_away - expected_away)

        # 更新评分
        new_home_rating = old_home_rating + home_rating_change
        new_away_rating = old_away_rating + away_rating_change

        # 更新存储
        self.team_ratings[home_team_id] = new_home_rating
        self.team_ratings[away_team_id] = new_away_rating

        # 更新历史记录
        self.rating_history[home_team_id].append((match_date, new_home_rating))
        self.rating_history[away_team_id].append((match_date, new_away_rating))

        # 更新统计信息
        self._update_statistics(home_rating_change, away_rating_change, match_date)

        # 构建返回结果
        result = {
            "match_info": {
                "home_team": home_team_id,
                "away_team": away_team_id,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "match_date": match_date.isoformat(),
                "competition_type": competition_type,
            },
            "ratings": {
                "home": {
                    "before": old_home_rating,
                    "after": new_home_rating,
                    "change": home_rating_change,
                    "k_factor": home_k_factor,
                },
                "away": {
                    "before": old_away_rating,
                    "after": new_away_rating,
                    "change": away_rating_change,
                    "k_factor": away_k_factor,
                },
            },
            "expectations": {
                "home_expected": expected_home,
                "away_expected": expected_away,
                "home_actual": actual_home,
                "away_actual": actual_away,
            },
            "adjustments": {
                "goal_margin_multiplier": goal_multiplier,
                "home_advantage_applied": self.home_advantage,
            },
        }

        logger.info(
            f"Elo评分更新: {home_team_id} {old_home_rating:.1f}->{new_home_rating:.1f} "
            f"({home_rating_change:+.1f}), {away_team_id} {old_away_rating:.1f}->{new_away_rating:.1f} "
            f"({away_rating_change:+.1f})"
        )

        return result

    def _calculate_k_factor(self, team_id: str, competition_type: str) -> float:
        """
        计算动态K因子

        Args:
            team_id: 球队ID
            competition_type: 比赛类型

        Returns:
            float: K因子
        """
        if not self.enable_dynamic_k:
            return self.base_k_factor

        # 基于比赛类型的K因子
        base_k = self.K_ADJUSTMENT.get(competition_type, self.base_k_factor)

        # 基于球队评分的调整（新球队或低评分球队使用更高K因子）
        team_rating = self.get_team_rating(team_id)
        if team_rating < 1400:
            base_k *= 1.5  # 低评分球队学习更快
        elif team_rating > 1800:
            base_k *= 0.8  # 高评分球队更稳定

        # 基于比赛场次调整
        match_count = len(self.rating_history.get(team_id, []))
        if match_count < 10:
            base_k *= 1.3  # 新球队学习更快
        elif match_count > 100:
            base_k *= 0.9  # 经验丰富的球队更稳定

        return base_k

    def _update_statistics(self, home_change: float, away_change: float, match_date: datetime) -> None:
        """更新统计信息"""
        self.stats["total_updates"] += 1

        # 计算平均变化
        total_change = abs(home_change) + abs(away_change)
        current_avg = self.stats["avg_rating_change"]
        n = self.stats["total_updates"]
        self.stats["avg_rating_change"] = (current_avg * (n - 1) + total_change) / n

        # 更新最大最小值
        if self.team_ratings:
            current_ratings = list(self.team_ratings.values())
            self.stats["max_rating"] = max(current_ratings)
            self.stats["min_rating"] = min(current_ratings)

        self.stats["last_updated"] = match_date.isoformat()

    def get_rating_trend(self, team_id: str, days: int = 30) -> dict[str, Any]:
        """
        获取球队评分趋势

        Args:
            team_id: 球队ID
            days: 分析天数

        Returns:
            Dict[str, Any]: 趋势分析结果
        """
        if team_id not in self.rating_history:
            return {"error": f"球队 {team_id} 无评分历史"}

        history = self.rating_history[team_id]
        cutoff_date = datetime.now() - timedelta(days=days)

        # 筛选指定时间范围内的记录
        recent_history = [(date, rating) for date, rating in history if date >= cutoff_date]

        if len(recent_history) < 2:
            return {"error": f"球队 {team_id} 在过去{days}天内记录不足"}

        # 计算趋势指标
        ratings = [rating for _, rating in recent_history]
        dates = [date for date, _ in recent_history]

        first_rating = ratings[0]
        last_rating = ratings[-1]
        change = last_rating - first_rating

        # 计算线性回归趋势
        x = np.arange(len(ratings))
        y = np.array(ratings)
        trend_slope = np.polyfit(x, y, 1)[0]

        # 计算波动率（标准差）
        volatility = np.std(ratings)

        return {
            "team_id": team_id,
            "period_days": days,
            "match_count": len(recent_history),
            "rating_change": change,
            "rating_start": first_rating,
            "rating_end": last_rating,
            "trend_slope": trend_slope,
            "volatility": volatility,
            "current_rating": self.get_team_rating(team_id),
            "performance_classification": self._classify_performance(change, trend_slope),
        }

    def _classify_performance(self, rating_change: float, trend_slope: float) -> str:
        """
        基于评分变化和趋势斜率分类表现

        Args:
            rating_change: 评分变化
            trend_slope: 趋势斜率

        Returns:
            str: 表现分类
        """
        if rating_change > 50 and trend_slope > 1:
            return "EXCELLENT"
        elif rating_change > 20 and trend_slope > 0.5:
            return "GOOD"
        elif rating_change > -10 and abs(trend_slope) < 0.3:
            return "STABLE"
        elif rating_change < -20 or trend_slope < -0.5:
            return "DECLINING"
        else:
            return "AVERAGE"

    def get_top_teams(self, limit: int = 20, min_matches: int = 10) -> list[dict[str, Any]]:
        """
        获取评分最高的球队

        Args:
            limit: 返回数量限制
            min_matches: 最少比赛场次

        Returns:
            List[Dict[str, Any]]: 排行榜
        """
        team_data = []

        for team_id, rating in self.team_ratings.items():
            match_count = len(self.rating_history.get(team_id, []))

            if match_count >= min_matches:
                # 获取趋势信息
                trend = self.get_rating_trend(team_id, days=30)

                team_data.append(
                    {
                        "team_id": team_id,
                        "current_rating": rating,
                        "match_count": match_count,
                        "rating_change_30d": trend.get("rating_change", 0),
                        "trend_classification": trend.get("performance_classification", "UNKNOWN"),
                        "volatility": trend.get("volatility", 0),
                    }
                )

        # 按评分排序
        team_data.sort(key=lambda x: x["current_rating"], reverse=True)

        return team_data[:limit]

    def predict_match_probabilities(
        self, home_team_id: str, away_team_id: str, num_simulations: int = 10000
    ) -> dict[str, Any]:
        """
        基于Elo评分预测比赛概率

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            num_simulations: 蒙特卡洛模拟次数

        Returns:
            Dict[str, Any]: 预测结果
        """
        # 获取基本预期
        expected_home, expected_away, home_win_prob = self.calculate_expected_score(home_team_id, away_team_id)

        # 使用泊松分布模拟进球数
        home_rating = self.get_team_rating(home_team_id)
        away_rating = self.get_team_rating(away_team_id)

        # 基于Elo差异估算预期进球数
        rating_diff = (home_rating + self.home_advantage - away_rating) / 100
        exp_home_goals = max(0.5, 1.5 + rating_diff * 0.3)  # 主队预期进球
        exp_away_goals = max(0.5, 1.5 - rating_diff * 0.3)  # 客队预期进球

        # 蒙特卡洛模拟
        np.random.seed(42)  # 固定种子保证可重复性
        home_sim = np.random.poisson(exp_home_goals, num_simulations)
        away_sim = np.random.poisson(exp_away_goals, num_simulations)

        # 计算各种结果的概率
        home_wins = np.sum(home_sim > away_sim) / num_simulations
        draws = np.sum(home_sim == away_sim) / num_simulations
        away_wins = np.sum(home_sim < away_sim) / num_simulations

        # 计算预期比分
        home_goals_mode = int(np.bincount(home_sim).argmax())
        away_goals_mode = int(np.bincount(away_sim).argmax())

        # 最可能的具体比分
        score_matrix = np.zeros((6, 6))  # 0-5球的矩阵
        for h_goals in range(6):
            for a_goals in range(6):
                prob = (np.sum(home_sim == h_goals) * np.sum(away_sim == a_goals)) / (num_simulations**2)
                score_matrix[h_goals, a_goals] = prob

        most_likely_score = np.unravel_index(np.argmax(score_matrix), score_matrix.shape)

        return {
            "teams": {
                "home": home_team_id,
                "away": away_team_id,
                "home_elo": home_rating,
                "away_elo": away_rating,
            },
            "probabilities": {
                "home_win": float(home_wins),
                "draw": float(draws),
                "away_win": float(away_wins),
                "over_2_5": float(np.sum(home_sim + away_sim > 2.5) / num_simulations),
                "both_teams_score": float(np.sum((home_sim > 0) & (away_sim > 0)) / num_simulations),
            },
            "expected_goals": {
                "home": exp_home_goals,
                "away": exp_away_goals,
                "total": exp_home_goals + exp_away_goals,
            },
            "most_likely_score": f"{most_likely_score[0]}-{most_likely_score[1]}",
            "mode_goals": {
                "home": home_goals_mode,
                "away": away_goals_mode,
            },
            "simulation_stats": {
                "simulations": num_simulations,
                "expected_home_based_on_elo": expected_home,
                "home_win_probability_elo": home_win_prob,
            },
        }

    def export_ratings(self, format: str = "dict") -> dict[str, Any] | str:
        """
        导出所有球队评分

        Args:
            format: 导出格式 ("dict", "json", "csv")

        Returns:
            Union[Dict[str, Any], str]: 导出数据
        """
        export_data = []

        for team_id, rating in self.team_ratings.items():
            history_count = len(self.rating_history.get(team_id, []))
            trend = self.get_rating_trend(team_id, days=30)

            export_data.append(
                {
                    "team_id": team_id,
                    "current_elo": rating,
                    "matches_played": history_count,
                    "rating_change_30d": trend.get("rating_change", 0),
                    "trend": trend.get("performance_classification", "UNKNOWN"),
                }
            )

        if format == "json":
            import json

            return json.dumps(export_data, indent=2, ensure_ascii=False)
        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            if export_data:
                writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)

            return output.getvalue()
        else:  # dict
            return {
                "export_timestamp": datetime.now().isoformat(),
                "total_teams": len(export_data),
                "system_stats": self.stats,
                "ratings": export_data,
            }

    def get_system_stats(self) -> dict[str, Any]:
        """获取系统统计信息"""
        return {
            "configuration": {
                "initial_rating": self.initial_rating,
                "home_advantage": self.home_advantage,
                "base_k_factor": self.base_k_factor,
                "enable_goal_margin": self.enable_goal_margin,
                "enable_dynamic_k": self.enable_dynamic_k,
                "rating_decay_days": self.rating_decay_days,
            },
            "statistics": self.stats,
            "team_count": len(self.team_ratings),
            "rating_distribution": {
                "average": (np.mean(list(self.team_ratings.values())) if self.team_ratings else 0),
                "std_dev": (np.std(list(self.team_ratings.values())) if self.team_ratings else 0),
                "min": (min(self.team_ratings.values()) if self.team_ratings else self.initial_rating),
                "max": (max(self.team_ratings.values()) if self.team_ratings else self.initial_rating),
            },
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"EloRatingSystem(teams={len(self.team_ratings)}, "
            f"avg_rating={np.mean(list(self.team_ratings.values())):.1f:.1f if self.team_ratings else 0}, "
            f"updates={self.stats['total_updates']})"
        )
