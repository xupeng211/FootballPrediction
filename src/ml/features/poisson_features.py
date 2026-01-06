#!/usr/bin/env python3
"""
泊松分布特征计算系统 - 足球进球预期建模

Phase 5 Advanced Features 核心组件之二

基于泊松分布理论，计算足球比赛的各种进球相关特征：
- 预期进球数（xG）计算
- 进球数分布概率
- 双方进球（BTTS）概率
- 大小球概率预测
- 精确比分概率

核心理论：
P(k; λ) = (λ^k * e^(-λ)) / k!

其中：
- k: 进球数
- λ: 预期进球数（λ值）
- e: 自然常数（≈2.71828）

应用场景：
- 比赛结果预测
- 投注策略制定
- 风险管理
- 模型特征工程

Author: Football Prediction Team
Version: 1.0.0
"""

from datetime import datetime
import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

# V146.1: 修复导入 - 使用绝对路径
from src.constants import STATISTICAL

logger = logging.getLogger(__name__)


class PoissonFeatureCalculator:
    """
    泊松分布特征计算器

    主要功能：
    1. 计算球队进攻和防守λ值
    2. 预测比赛进球数分布
    3. 计算各种投注市场概率
    4. 提供模型特征工程支持
    """

    # 默认参数
    DEFAULT_HOME_LAMBDA = 1.5  # 主队默认预期进球
    DEFAULT_AWAY_LAMBDA = 1.2  # 客队默认预期进球
    LEAGUE_AVG_GOALS = 2.7  # 联赛平均进球数
    MAX_GOALS_FOR_CALC = 10  # 计算考虑的最大进球数

    # 历史权重衰减参数
    DECAY_FACTOR = 0.95  # 每周衰减因子
    MIN_SAMPLE_WEIGHT = 0.1  # 最小样本权重

    # 优化参数
    MIN_GAMES_FOR_LAMBDA = 5  # 计算λ值的最少比赛场次
    ADVANTAGE_FACTOR = 0.15  # 主场优势因子

    def __init__(
        self,
        home_lambda_default: float = DEFAULT_HOME_LAMBDA,
        away_lambda_default: float = DEFAULT_AWAY_LAMBDA,
        league_avg_goals: float = LEAGUE_AVG_GOALS,
        enable_team_strength_adjustment: bool = True,
        enable_venue_adjustment: bool = True,
        enable_time_decay: bool = True,
        max_goals_calc: int = MAX_GOALS_FOR_CALC,
    ):
        """
        初始化泊松特征计算器

        Args:
            home_lambda_default: 主队默认预期进球
            away_lambda_default: 客队默认预期进球
            league_avg_goals: 联赛平均进球数
            enable_team_strength_adjustment: 是否启用球队实力调整
            enable_venue_adjustment: 是否启用场地调整
            enable_time_decay: 是否启用时间衰减
            max_goals_calc: 计算考虑的最大进球数
        """
        self.home_lambda_default = home_lambda_default
        self.away_lambda_default = away_lambda_default
        self.league_avg_goals = league_avg_goals
        self.enable_team_strength_adjustment = enable_team_strength_adjustment
        self.enable_venue_adjustment = enable_venue_adjustment
        self.enable_time_decay = enable_time_decay
        self.max_goals_calc = max_goals_calc

        # 存储球队历史数据
        self.team_data: dict[str, dict[str, Any]] = {}

        # 统计信息
        self.stats = {
            "total_calculations": 0,
            "avg_lambda_home": 0.0,
            "avg_lambda_away": 0.0,
            "last_updated": None,
        }

        logger.info(
            f"泊松特征计算器初始化完成: 主队λ={home_lambda_default}, "
            f"客队λ={away_lambda_default}, 联赛平均={league_avg_goals}"
        )

    def calculate_team_lambdas(
        self,
        team_id: str,
        matches_data: list[dict[str, Any]],
        is_home_team: bool = True,
    ) -> tuple[float, float, dict[str, Any]]:
        """
        计算球队的进攻和防守λ值

        Args:
            team_id: 球队ID
            matches_data: 比赛数据列表
            is_home_team: 是否为主队

        Returns:
            Tuple[float, float, Dict]: (进攻λ, 防守λ, 详细信息)
        """
        if len(matches_data) < self.MIN_GAMES_FOR_LAMBDA:
            # 数据不足时使用默认值
            default_attack = self.home_lambda_default if is_home_team else self.away_lambda_default
            default_defense = self.league_avg_goals - default_attack

            return (
                default_attack,
                default_defense,
                {
                    "status": "insufficient_data",
                    "matches_used": len(matches_data),
                    "attack_lambda": default_attack,
                    "defense_lambda": default_defense,
                },
            )

        # 准备数据
        goals_scored = []
        goals_conceded = []
        venue_factors = []
        time_weights = []

        for match in matches_data:
            # 确定主客场
            team_is_home = match.get("team_is_home", is_home_team)

            # 获取进球数据
            if team_is_home:
                goals_for = match.get("home_goals", 0)
                goals_against = match.get("away_goals", 0)
            else:
                goals_for = match.get("away_goals", 0)
                goals_against = match.get("home_goals", 0)

            goals_scored.append(goals_for)
            goals_conceded.append(goals_against)

            # 场地因子（主客场调整）
            if self.enable_venue_adjustment:
                venue_factors.append(1.2 if team_is_home else 0.9)
            else:
                venue_factors.append(1.0)

            # 时间权重（新比赛权重更高）
            if self.enable_time_decay:
                match_date = match.get("match_date", datetime.now())
                if isinstance(match_date, str):
                    match_date = datetime.fromisoformat(match_date)

                days_ago = (datetime.now() - match_date).days
                weeks_ago = days_ago / 7
                weight = max(self.MIN_SAMPLE_WEIGHT, self.DECAY_FACTOR**weeks_ago)
                time_weights.append(weight)
            else:
                time_weights.append(1.0)

        # 计算加权平均
        total_weight = sum(time_weights)
        weighted_goals_scored = sum(g * w for g, w in zip(goals_scored, time_weights))
        weighted_goals_conceded = sum(g * w for g, w in zip(goals_conceded, time_weights))

        # 场地调整后的λ值
        avg_venue_factor = sum(v * w for v, w in zip(venue_factors, time_weights)) / total_weight

        # 基础λ值计算
        base_attack_lambda = weighted_goals_scored / total_weight
        base_defense_lambda = weighted_goals_conceded / total_weight

        # 场地调整
        if self.enable_venue_adjustment:
            # 调整到标准场地条件
            attack_lambda = base_attack_lambda / avg_venue_factor
            defense_lambda = base_defense_lambda * avg_venue_factor
        else:
            attack_lambda = base_attack_lambda
            defense_lambda = base_defense_lambda

        # 球队实力调整
        if self.enable_team_strength_adjustment:
            # 基于联赛平均值的调整
            strength_factor = (base_attack_lambda + base_defense_lambda) / self.league_avg_goals
            if strength_factor > 1.2:  # 强队
                attack_lambda *= 0.95  # 轻微保守估计
                defense_lambda *= 0.95
            elif strength_factor < 0.8:  # 弱队
                attack_lambda *= 1.05  # 轻微乐观估计
                defense_lambda *= 1.05

        # 确保λ值合理
        attack_lambda = max(0.3, min(5.0, attack_lambda))
        defense_lambda = max(0.3, min(5.0, defense_lambda))

        # 更新球队数据
        self.team_data[team_id] = {
            "attack_lambda": attack_lambda,
            "defense_lambda": defense_lambda,
            "matches_analyzed": len(matches_data),
            "last_updated": datetime.now(),
            "base_performance": {
                "avg_goals_scored": np.mean(goals_scored),
                "avg_goals_conceded": np.mean(goals_conceded),
                "goal_variance": np.var(goals_scored),
            },
        }

        return (
            attack_lambda,
            defense_lambda,
            {
                "status": "success",
                "matches_used": len(matches_data),
                "attack_lambda": attack_lambda,
                "defense_lambda": defense_lambda,
                "base_attack": base_attack_lambda,
                "base_defense": base_defense_lambda,
                "venue_factor": avg_venue_factor,
                "strength_applied": self.enable_team_strength_adjustment,
            },
        )

    def calculate_match_probabilities(
        self,
        home_team_id: str,
        away_team_id: str,
        home_attack_lambda: float | None = None,
        home_defense_lambda: float | None = None,
        away_attack_lambda: float | None = None,
        away_defense_lambda: float | None = None,
    ) -> dict[str, Any]:
        """
        计算比赛概率分布

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            home_attack_lambda: 主队进攻λ值
            home_defense_lambda: 主队防守λ值
            away_attack_lambda: 客队进攻λ值
            away_defense_lambda: 客队防守λ值

        Returns:
            Dict[str, Any]: 比赛概率分析
        """
        # 使用存储的λ值或默认值
        home_attack = home_attack_lambda or self.team_data.get(home_team_id, {}).get(
            "attack_lambda", self.home_lambda_default
        )
        home_defense = home_defense_lambda or self.team_data.get(home_team_id, {}).get(
            "defense_lambda", self.league_avg_goals - self.home_lambda_default
        )
        away_attack = away_attack_lambda or self.team_data.get(away_team_id, {}).get(
            "attack_lambda", self.away_lambda_default
        )
        away_defense = away_defense_lambda or self.team_data.get(away_team_id, {}).get(
            "defense_lambda", self.league_avg_goals - self.away_lambda_default
        )

        # 主场优势调整
        home_advantage = 1.0 + self.ADVANTAGE_FACTOR

        # 计算预期进球数（λ值）
        # 考虑对手防守能力
        exp_home_goals = home_attack * away_defense / self.league_avg_goals * home_advantage
        exp_away_goals = away_attack * home_defense / self.league_avg_goals

        # 确保预期值合理
        exp_home_goals = max(0.1, min(6.0, exp_home_goals))
        exp_away_goals = max(0.1, min(6.0, exp_away_goals))

        # 计算比分概率矩阵
        score_matrix = self._calculate_score_matrix(exp_home_goals, exp_away_goals)

        # 计算各种市场概率
        home_win_prob = self._calculate_home_win_probability(score_matrix)
        draw_prob = self._calculate_draw_probability(score_matrix)
        away_win_prob = 1.0 - home_win_prob - draw_prob

        # 计算大小球概率
        over_2_5_prob = self._calculate_over_probability(score_matrix, 2.5)
        over_3_5_prob = self._calculate_over_probability(score_matrix, 3.5)

        # 计算双方进球概率
        btts_prob = self._calculate_btts_probability(score_matrix)

        # 计算精确比分概率（Top 5）
        top_scores = self._get_top_probable_scores(score_matrix, 5)

        # 计算进球数分布
        home_goals_dist = self._calculate_goals_distribution(exp_home_goals)
        away_goals_dist = self._calculate_goals_distribution(exp_away_goals)

        # 更新统计信息
        self._update_calculation_stats(exp_home_goals, exp_away_goals)

        result = {
            "match_info": {
                "home_team": home_team_id,
                "away_team": away_team_id,
            },
            "expected_goals": {
                "home": exp_home_goals,
                "away": exp_away_goals,
                "total": exp_home_goals + exp_away_goals,
            },
            "team_lambdas": {
                "home": {"attack": home_attack, "defense": home_defense},
                "away": {"attack": away_attack, "defense": away_defense},
            },
            "probabilities": {
                "home_win": float(home_win_prob),
                "draw": float(draw_prob),
                "away_win": float(away_win_prob),
                "over_2_5": float(over_2_5_prob),
                "over_3_5": float(over_3_5_prob),
                "both_teams_score": float(btts_prob),
            },
            "top_scores": top_scores,
            "goals_distribution": {
                "home": {f"{k}_goals": float(v) for k, v in home_goals_dist.items()},
                "away": {f"{k}_goals": float(v) for k, v in away_goals_dist.items()},
            },
            "model_features": self._extract_model_features(exp_home_goals, exp_away_goals, score_matrix),
            "confidence_metrics": self._calculate_confidence_metrics(
                home_team_id, away_team_id, exp_home_goals, exp_away_goals
            ),
        }

        logger.info(
            f"泊松概率计算完成: {home_team_id} vs {away_team_id}, "
            f"预期比分 {exp_home_goals:.2f}-{exp_away_goals:.2f}, "
            f"主胜 {home_win_prob:.1%}, 平局 {draw_prob:.1%}, 客胜 {away_win_prob:.1%}"
        )

        return result

    def _calculate_score_matrix(self, exp_home_goals: float, exp_away_goals: float) -> np.ndarray:
        """
        计算比分概率矩阵

        Args:
            exp_home_goals: 主队预期进球
            exp_away_goals: 客队预期进球

        Returns:
            np.ndarray: 比分概率矩阵
        """
        matrix = np.zeros((self.max_goals_calc + 1, self.max_goals_calc + 1))

        for home_goals in range(self.max_goals_calc + 1):
            for away_goals in range(self.max_goals_calc + 1):
                # 泊松分布计算
                prob_home = stats.poisson.pmf(home_goals, exp_home_goals)
                prob_away = stats.poisson.pmf(away_goals, exp_away_goals)
                matrix[home_goals, away_goals] = prob_home * prob_away

        return matrix

    def _calculate_home_win_probability(self, score_matrix: np.ndarray) -> float:
        """计算主胜概率"""
        home_win_prob = 0.0
        for home_goals in range(self.max_goals_calc + 1):
            for away_goals in range(home_goals):  # home_goals > away_goals
                home_win_prob += score_matrix[home_goals, away_goals]
        return home_win_prob

    def _calculate_draw_probability(self, score_matrix: np.ndarray) -> float:
        """计算平局概率"""
        draw_prob = 0.0
        for goals in range(self.max_goals_calc + 1):
            draw_prob += score_matrix[goals, goals]
        return draw_prob

    def _calculate_over_probability(self, score_matrix: np.ndarray, threshold: float) -> float:
        """计算大小球概率"""
        over_prob = 0.0
        for home_goals in range(self.max_goals_calc + 1):
            for away_goals in range(self.max_goals_calc + 1):
                if home_goals + away_goals > threshold:
                    over_prob += score_matrix[home_goals, away_goals]
        return over_prob

    def _calculate_btts_probability(self, score_matrix: np.ndarray) -> float:
        """计算双方进球概率"""
        btts_prob = 0.0
        for home_goals in range(1, self.max_goals_calc + 1):
            for away_goals in range(1, self.max_goals_calc + 1):
                btts_prob += score_matrix[home_goals, away_goals]
        return btts_prob

    def _get_top_probable_scores(self, score_matrix: np.ndarray, top_n: int = 5) -> list[dict[str, Any]]:
        """获取最可能的比分"""
        scores = []
        for home_goals in range(self.max_goals_calc + 1):
            for away_goals in range(self.max_goals_calc + 1):
                prob = score_matrix[home_goals, away_goals]
                if prob > 0:
                    scores.append(
                        {
                            "score": f"{home_goals}-{away_goals}",
                            "probability": float(prob),
                            "home_goals": home_goals,
                            "away_goals": away_goals,
                        }
                    )

        scores.sort(key=lambda x: x["probability"], reverse=True)
        return scores[:top_n]

    def _calculate_goals_distribution(self, exp_goals: float) -> dict[int, float]:
        """计算进球数分布"""
        distribution = {}
        for goals in range(self.max_goals_calc + 1):
            distribution[goals] = float(stats.poisson.pmf(goals, exp_goals))
        return distribution

    def _extract_model_features(
        self, exp_home_goals: float, exp_away_goals: float, score_matrix: np.ndarray
    ) -> dict[str, float]:
        """
        提取用于机器学习模型的特征

        Args:
            exp_home_goals: 主队预期进球
            exp_away_goals: 客队预期进球
            score_matrix: 比分概率矩阵

        Returns:
            Dict[str, float]: 模型特征
        """
        features = {}

        # 基础预期特征
        features["expected_home_goals"] = exp_home_goals
        features["expected_away_goals"] = exp_away_goals
        features["expected_total_goals"] = exp_home_goals + exp_away_goals
        features["expected_goal_difference"] = exp_home_goals - exp_away_goals

        # 概率特征
        features["home_win_poisson_prob"] = self._calculate_home_win_probability(score_matrix)
        features["draw_poisson_prob"] = self._calculate_draw_probability(score_matrix)
        features["over_2_5_poisson_prob"] = self._calculate_over_probability(score_matrix, 2.5)
        features["btts_poisson_prob"] = self._calculate_btts_probability(score_matrix)

        # 高阶特征
        features["poisson_variance_home"] = exp_home_goals  # 泊松分布方差=λ
        features["poisson_variance_away"] = exp_away_goals
        features["poisson_skewness_home"] = 1.0 / np.sqrt(exp_home_goals)  # 泊松分布偏度
        features["poisson_skewness_away"] = 1.0 / np.sqrt(exp_away_goals)

        # 比分分散度特征
        matrix_entropy = self._calculate_matrix_entropy(score_matrix)
        features["score_entropy"] = matrix_entropy

        # 最可能比分特征
        top_score = self._get_top_probable_scores(score_matrix, 1)[0]
        features["most_likely_home_goals"] = top_score["home_goals"]
        features["most_likely_away_goals"] = top_score["away_goals"]
        features["most_likely_score_prob"] = top_score["probability"]

        return features

    def _calculate_matrix_entropy(self, score_matrix: np.ndarray) -> float:
        """计算比分概率矩阵的信息熵"""
        # 添加小值避免log(0)
        matrix_safe = score_matrix + 1e-10
        matrix_normalized = matrix_safe / np.sum(matrix_safe)
        entropy = -np.sum(matrix_normalized * np.log2(matrix_normalized + 1e-10))
        return entropy

    def _calculate_confidence_metrics(
        self,
        home_team_id: str,
        away_team_id: str,
        exp_home_goals: float,
        exp_away_goals: float,
    ) -> dict[str, float]:
        """计算预测置信度指标"""
        metrics = {}

        # 基于历史数据的置信度
        home_matches = self.team_data.get(home_team_id, {}).get("matches_analyzed", 0)
        away_matches = self.team_data.get(away_team_id, {}).get("matches_analyzed", 0)

        # 数据充足性置信度
        data_confidence = min(home_matches, away_matches) / STATISTICAL.MIN_H2H_SAMPLE_SIZE
        metrics["data_sufficiency_confidence"] = float(data_confidence)

        # 预测稳定性置信度（基于λ值的合理性）
        total_goals = exp_home_goals + exp_away_goals
        stability_confidence = 1.0 - abs(total_goals - self.league_avg_goals) / self.league_avg_goals
        metrics["stability_confidence"] = float(max(0.0, stability_confidence))

        # 综合置信度
        metrics["overall_confidence"] = float((data_confidence + stability_confidence) / 2.0)

        return metrics

    def _update_calculation_stats(self, exp_home_goals: float, exp_away_goals: float) -> None:
        """更新计算统计信息"""
        self.stats["total_calculations"] += 1
        n = self.stats["total_calculations"]

        # 更新平均λ值
        current_avg_home = self.stats["avg_lambda_home"]
        current_avg_away = self.stats["avg_lambda_away"]

        self.stats["avg_lambda_home"] = (current_avg_home * (n - 1) + exp_home_goals) / n
        self.stats["avg_lambda_away"] = (current_avg_away * (n - 1) + exp_away_goals) / n

        self.stats["last_updated"] = datetime.now().isoformat()

    def generate_features_for_dataset(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """
        为数据集批量生成泊松特征

        Args:
            matches_df: 比赛数据DataFrame

        Returns:
            pd.DataFrame: 包含泊松特征的数据集
        """
        features_list = []

        for idx, row in matches_df.iterrows():
            home_team = row["home_team_id"]
            away_team = row["away_team_id"]

            try:
                # 计算概率
                probabilities = self.calculate_match_probabilities(home_team, away_team)

                # 提取特征
                features = probabilities["model_features"]
                features.update(probabilities["confidence_metrics"])

                # 添加基础信息
                features["match_id"] = row.get("match_id", idx)
                features["home_team_id"] = home_team
                features["away_team_id"] = away_team
                features["match_date"] = row.get("match_date", datetime.now())

                features_list.append(features)

            except Exception as e:
                logger.warning(f"无法计算match {idx}的泊松特征: {e}")
                continue

        return pd.DataFrame(features_list)

    def get_team_stats(self, team_id: str) -> dict[str, Any]:
        """获取球队统计信息"""
        team_data = self.team_data.get(team_id, {})
        if not team_data:
            return {"error": f"球队 {team_id} 无数据"}

        base_perf = team_data.get("base_performance", {})

        return {
            "team_id": team_id,
            "current_lambdas": {
                "attack": team_data.get("attack_lambda", 0),
                "defense": team_data.get("defense_lambda", 0),
            },
            "performance_stats": {
                "avg_goals_scored": base_perf.get("avg_goals_scored", 0),
                "avg_goals_conceded": base_perf.get("avg_goals_conceded", 0),
                "goal_variance": base_perf.get("goal_variance", 0),
            },
            "data_quality": {
                "matches_analyzed": team_data.get("matches_analyzed", 0),
                "last_updated": team_data.get("last_updated"),
                "data_sufficient": team_data.get("matches_analyzed", 0) >= self.MIN_GAMES_FOR_LAMBDA,
            },
        }

    def get_system_stats(self) -> dict[str, Any]:
        """获取系统统计信息"""
        return {
            "configuration": {
                "home_lambda_default": self.home_lambda_default,
                "away_lambda_default": self.away_lambda_default,
                "league_avg_goals": self.league_avg_goals,
                "enable_team_strength_adjustment": self.enable_team_strength_adjustment,
                "enable_venue_adjustment": self.enable_venue_adjustment,
                "enable_time_decay": self.enable_time_decay,
                "max_goals_calc": self.max_goals_calc,
            },
            "statistics": self.stats,
            "team_data_count": len(self.team_data),
            "average_lambdas": {
                "home_attack": (
                    np.mean([data.get("attack_lambda", 0) for data in self.team_data.values()]) if self.team_data else 0
                ),
                "home_defense": (
                    np.mean([data.get("defense_lambda", 0) for data in self.team_data.values()])
                    if self.team_data
                    else 0
                ),
            },
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"PoissonFeatureCalculator(teams={len(self.team_data)}, "
            f"calculations={self.stats['total_calculations']}, "
            f"avg_home_λ={self.stats['avg_lambda_home']:.2f}, "
            f"avg_away_λ={self.stats['avg_lambda_away']:.2f})"
        )
