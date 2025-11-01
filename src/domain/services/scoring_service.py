"""
计分领域服务
Scoring Domain Service

处理预测计分相关的复杂业务逻辑.
Handles complex business logic related to prediction scoring.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.domain.models.prediction import PredictionPoints


class ScoringService:
    """计分服务"""

    def __init__(self, scoring_config: Optional[Dict[str, Any]] = None):
        """初始化计分服务"""
        self.config = scoring_config or self._default_scoring_config()

    def _default_scoring_config(self) -> Dict[str, Any]:
        """默认计分配置"""
        return {
            "exact_score": {"points": 10, "multiplier": 1.0},
            "outcome_only": {"points": 3, "multiplier": 1.0},
            "goal_difference": {"points": 5, "multiplier": 1.0},
            "confidence_bonus": {"max_bonus": 3, "threshold": 0.8},
            "streak_bonus": {"enabled": True, "bonus_per_streak": 1, "max_bonus": 5},
            "difficulty_multiplier": {"enabled": True, "base_multiplier": 1.0},
        }

    def calculate_prediction_points(
        self,
        predicted_home: int,
        predicted_away: int,
        actual_home: int,
        actual_away: int,
        confidence: Optional[float] = None,
        match_importance: float = 0.5,
        user_streak: int = 0,
    ) -> PredictionPoints:
        """计算预测得分"""
        # 计算基础得分
        exact_score_points = self._calculate_exact_score_points(
            predicted_home, predicted_away, actual_home, actual_away
        )

        outcome_points = self._calculate_outcome_points(
            predicted_home, predicted_away, actual_home, actual_away
        )

        goal_diff_points = self._calculate_goal_difference_points(
            predicted_home, predicted_away, actual_home, actual_away
        )

        # 计算奖励得分
        confidence_bonus = self._calculate_confidence_bonus(confidence)
        streak_bonus = self._calculate_streak_bonus(user_streak)
        difficulty_bonus = self._calculate_difficulty_bonus(
            match_importance, predicted_home, predicted_away
        )

        score_bonus = Decimal(exact_score_points)
        outcome_total = Decimal(
            outcome_points + goal_diff_points + streak_bonus + difficulty_bonus
        )
        confidence_bonus_value = Decimal(confidence_bonus)

        total_points = score_bonus + outcome_total + confidence_bonus_value

        return PredictionPoints(
            total=total_points,
            score_bonus=score_bonus,
            result_bonus=outcome_total,
            confidence_bonus=confidence_bonus_value,
        )

    def _calculate_exact_score_points(
        self,
        predicted_home: int,
        predicted_away: int,
        actual_home: int,
        actual_away: int,
    ) -> int:
        """计算精确比分得分"""
        if predicted_home == actual_home and predicted_away == actual_away:
            return int(
                self.config["exact_score"]["points"]
                * self.config["exact_score"]["multiplier"]
            )
        return 0

    def _calculate_outcome_points(
        self,
        predicted_home: int,
        predicted_away: int,
        actual_home: int,
        actual_away: int,
    ) -> int:
        """计算胜负平得分"""
        predicted_outcome = self._get_outcome(predicted_home, predicted_away)
        actual_outcome = self._get_outcome(actual_home, actual_away)

        if predicted_outcome == actual_outcome:
            return int(
                self.config["outcome_only"]["points"]
                * self.config["outcome_only"]["multiplier"]
            )
        return 0

    def _calculate_goal_difference_points(
        self,
        predicted_home: int,
        predicted_away: int,
        actual_home: int,
        actual_away: int,
    ) -> int:
        """计算净胜球得分"""
        predicted_diff = predicted_home - predicted_away
        actual_diff = actual_home - actual_away

        if predicted_diff == actual_diff and predicted_diff != 0:
            return int(
                self.config["goal_difference"]["points"]
                * self.config["goal_difference"]["multiplier"]
            )
        return 0

    def _calculate_confidence_bonus(self, confidence: Optional[float]) -> int:
        """计算信心度奖励"""
        if not confidence:
            return 0

        threshold = self.config["confidence_bonus"]["threshold"]
        max_bonus = self.config["confidence_bonus"]["max_bonus"]

        if confidence >= threshold:
            return int(max_bonus * confidence)
        return 0

    def _calculate_streak_bonus(self, streak: int) -> int:
        """计算连胜奖励"""
        if not self.config["streak_bonus"]["enabled"]:
            return 0

        bonus_per_streak = self.config["streak_bonus"]["bonus_per_streak"]
        max_bonus = self.config["streak_bonus"]["max_bonus"]

        if streak > 0:
            return min(streak * bonus_per_streak, max_bonus)
        return 0

    def _calculate_difficulty_bonus(
        self, match_importance: float, predicted_home: int, predicted_away: int
    ) -> int:
        """计算难度奖励"""
        if not self.config["difficulty_multiplier"]["enabled"]:
            return 0

        # 基础难度系数
        base_multiplier = self.config["difficulty_multiplier"]["base_multiplier"]

        # 根据预测比分调整难度
        # 大比分预测难度更高
        total_goals = predicted_home + predicted_away
        if total_goals > 5:
            difficulty_multiplier = base_multiplier * 1.2
        elif total_goals > 3:
            difficulty_multiplier = base_multiplier * 1.1
        else:
            difficulty_multiplier = base_multiplier

        # 根据比赛重要性调整
        difficulty_multiplier *= 1 + match_importance

        # 返回整数奖励分
        return int(difficulty_multiplier * 2)  # 基础2分,根据难度调整

    def _get_outcome(self, home: int, away: int) -> str:
        """获取比赛结果"""
        if home > away:
            return "home_win"
        elif home < away:
            return "away_win"
        else:
            return "draw"

    def calculate_leaderboard_position(
        self, user_points: int, all_users_points: List[int]
    ) -> int:
        """计算排行榜位置"""
        # 排序（降序）
        sorted_points = sorted(all_users_points, reverse=True)

        # 找到位置（从1开始）
        try:
            return sorted_points.index(user_points) + 1
        except ValueError:
            return len(sorted_points) + 1

    def calculate_rank_percentile(self, position: int, total_users: int) -> float:
        """计算排名百分位"""
        if total_users == 0:
            return 0.0

        # 百分位计算（越小越好）
        percentile = (position - 1) / total_users * 100
        return round(percentile, 2)

    def update_scoring_config(self, new_config: Dict[str, Any]) -> None:
        """更新计分配置"""
        # 验证配置
        self._validate_config(new_config)

        # 合并配置
        self.config.update(new_config)

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """验证计分配置"""
        required_keys = ["exact_score", "outcome_only", "goal_difference"]

        for key in required_keys:
            if key not in config:
                raise ValueError(f"计分配置缺少必需的键: {key}")

            if "points" not in config[key]:
                raise ValueError(f"计分配置 {key} 缺少 points 字段")

            if not isinstance(config[key]["points"], (int, float)):
                raise ValueError(f"计分配置 {key}.points 必须是数字")

            if config[key]["points"] < 0:
                raise ValueError(f"计分配置 {key}.points 不能为负数")

    def get_scoring_rules_summary(self) -> Dict[str, Any]:
        """获取计分规则摘要"""
        return {
            "exact_score": f"{self.config['exact_score']['points']}分",
            "outcome_only": f"{self.config['outcome_only']['points']}分",
            "goal_difference": f"{self.config['goal_difference']['points']}分",
            "confidence_bonus": {
                "max": self.config["confidence_bonus"]["max_bonus"],
                "threshold": self.config["confidence_bonus"]["threshold"],
            },
            "streak_bonus": {
                "enabled": self.config["streak_bonus"]["enabled"],
                "per_streak": self.config["streak_bonus"]["bonus_per_streak"],
                "max": self.config["streak_bonus"]["max_bonus"],
            },
        }
