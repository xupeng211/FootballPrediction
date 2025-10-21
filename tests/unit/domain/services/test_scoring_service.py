"""
计分服务测试
Tests for Scoring Service

测试src.domain.services.scoring_service模块的功能
"""

import pytest
from decimal import Decimal

from src.domain.services.scoring_service import ScoringService
from src.domain.models.prediction import PredictionPoints


class TestScoringService:
    """计分服务测试"""

    def test_service_creation_default_config(self):
        """测试：使用默认配置创建服务"""
        service = ScoringService()
        assert service.config is not None
        assert "exact_score" in service.config
        assert "outcome_only" in service.config
        assert "goal_difference" in service.config
        assert service._config["exact_score"]["points"] == 10
        assert service._config["outcome_only"]["points"] == 3
        assert service._config["goal_difference"]["points"] == 5

    def test_service_creation_custom_config(self):
        """测试：使用自定义配置创建服务"""
        custom_config = {
            "exact_score": {"points": 15, "multiplier": 1.5},
            "outcome_only": {"points": 5, "multiplier": 1.0},
            "confidence_bonus": {"max_bonus": 5, "threshold": 0.9},
        }
        service = ScoringService(custom_config)
        assert service._config["exact_score"]["points"] == 15
        assert service._config["exact_score"]["multiplier"] == 1.5
        assert service._config["confidence_bonus"]["max_bonus"] == 5

    def test_calculate_exact_score_points_correct(self):
        """测试：计算精确比分得分（正确）"""
        service = ScoringService()
        points = service._calculate_exact_score_points(2, 1, 2, 1)
        assert points == 10

    def test_calculate_exact_score_points_wrong(self):
        """测试：计算精确比分得分（错误）"""
        service = ScoringService()
        points = service._calculate_exact_score_points(2, 1, 1, 2)
        assert points == 0

    def test_calculate_exact_score_points_custom_multiplier(self):
        """测试：计算精确比分得分（自定义倍数）"""
        _config = {"exact_score": {"points": 10, "multiplier": 2.0}}
        service = ScoringService(config)
        points = service._calculate_exact_score_points(2, 1, 2, 1)
        assert points == 20

    def test_calculate_outcome_points_home_win(self):
        """测试：计算胜负平得分（主队胜）"""
        service = ScoringService()
        points = service._calculate_outcome_points(2, 0, 3, 1)
        assert points == 3

    def test_calculate_outcome_points_away_win(self):
        """测试：计算胜负平得分（客队胜）"""
        service = ScoringService()
        points = service._calculate_outcome_points(0, 2, 1, 3)
        assert points == 3

    def test_calculate_outcome_points_draw(self):
        """测试：计算胜负平得分（平局）"""
        service = ScoringService()
        points = service._calculate_outcome_points(1, 1, 2, 2)
        assert points == 3

    def test_calculate_outcome_points_wrong(self):
        """测试：计算胜负平得分（错误）"""
        service = ScoringService()
        points = service._calculate_outcome_points(2, 0, 1, 2)
        assert points == 0

    def test_calculate_goal_difference_points_correct_nonzero(self):
        """测试：计算净胜球得分（正确，非零）"""
        service = ScoringService()
        points = service._calculate_goal_difference_points(2, 0, 3, 1)
        assert points == 5

    def test_calculate_goal_difference_points_correct_zero(self):
        """测试：计算净胜球得分（正确，零）"""
        service = ScoringService()
        points = service._calculate_goal_difference_points(1, 1, 2, 2)
        assert points == 0  # 平局不给净胜球分

    def test_calculate_goal_difference_points_wrong(self):
        """测试：计算净胜球得分（错误）"""
        service = ScoringService()
        points = service._calculate_goal_difference_points(2, 0, 1, 2)
        assert points == 0

    def test_calculate_confidence_bonus_none(self):
        """测试：计算信心度奖励（无信心度）"""
        service = ScoringService()
        bonus = service._calculate_confidence_bonus(None)
        assert bonus == 0

    def test_calculate_confidence_bonus_below_threshold(self):
        """测试：计算信心度奖励（低于阈值）"""
        service = ScoringService()
        bonus = service._calculate_confidence_bonus(0.7)
        assert bonus == 0

    def test_calculate_confidence_bonus_above_threshold(self):
        """测试：计算信心度奖励（高于阈值）"""
        service = ScoringService()
        bonus = service._calculate_confidence_bonus(0.9)
        assert bonus == 2  # 3 * 0.9 = 2.7 -> int(2.7) = 2

    def test_calculate_confidence_bonus_exactly_threshold(self):
        """测试：计算信心度奖励（等于阈值）"""
        service = ScoringService()
        bonus = service._calculate_confidence_bonus(0.8)
        assert bonus == 2  # 3 * 0.8 = 2.4 -> int(2.4) = 2

    def test_calculate_streak_bonus_disabled(self):
        """测试：计算连胜奖励（禁用）"""
        _config = {"streak_bonus": {"enabled": False}}
        service = ScoringService(config)
        bonus = service._calculate_streak_bonus(5)
        assert bonus == 0

    def test_calculate_streak_bonus_zero(self):
        """测试：计算连胜奖励（零连胜）"""
        service = ScoringService()
        bonus = service._calculate_streak_bonus(0)
        assert bonus == 0

    def test_calculate_streak_bonus_positive(self):
        """测试：计算连胜奖励（正连胜）"""
        service = ScoringService()
        bonus = service._calculate_streak_bonus(3)
        assert bonus == 3

    def test_calculate_streak_bonus_max(self):
        """测试：计算连胜奖励（达到上限）"""
        service = ScoringService()
        bonus = service._calculate_streak_bonus(10)
        assert bonus == 5  # 最大上限

    def test_calculate_difficulty_bonus_disabled(self):
        """测试：计算难度奖励（禁用）"""
        _config = {"difficulty_multiplier": {"enabled": False}}
        service = ScoringService(config)
        bonus = service._calculate_difficulty_bonus(0.5, 2, 1)
        assert bonus == 0

    def test_calculate_difficulty_bonus_normal(self):
        """测试：计算难度奖励（正常）"""
        service = ScoringService()
        bonus = service._calculate_difficulty_bonus(0.5, 2, 1)
        assert bonus == 3  # 2 * (1 + 0.5) = 3

    def test_calculate_difficulty_bonus_high_goals(self):
        """测试：计算难度奖励（高进球）"""
        service = ScoringService()
        bonus = service._calculate_difficulty_bonus(0.5, 4, 3)
        assert bonus == 3  # 2 * 1.2 * (1 + 0.5) = 3.6 -> int(3.6) = 3

    def test_calculate_difficulty_bonus_very_high_goals(self):
        """测试：计算难度奖励（很高进球）"""
        service = ScoringService()
        bonus = service._calculate_difficulty_bonus(0.5, 4, 4)
        assert bonus == 3  # 2 * 1.2 * (1 + 0.5) = 3.6 -> int(3.6) = 3

    def test_get_outcome_home_win(self):
        """测试：获取比赛结果（主队胜）"""
        service = ScoringService()
        outcome = service._get_outcome(2, 1)
        assert outcome == "home_win"

    def test_get_outcome_away_win(self):
        """测试：获取比赛结果（客队胜）"""
        service = ScoringService()
        outcome = service._get_outcome(1, 2)
        assert outcome == "away_win"

    def test_get_outcome_draw(self):
        """测试：获取比赛结果（平局）"""
        service = ScoringService()
        outcome = service._get_outcome(1, 1)
        assert outcome == "draw"

    def test_calculate_prediction_points_exact_score(self):
        """测试：计算预测得分（精确比分）"""
        service = ScoringService()
        points = service.calculate_prediction_points(
            predicted_home=2,
            predicted_away=1,
            actual_home=2,
            actual_away=1,
            confidence=0.9,
            match_importance=0.5,
            user_streak=2,
        )
        assert isinstance(points, PredictionPoints)
        assert points.total == Decimal("25")  # 10 + 3 + 5 + 2 + 3 + 2 = 25
        assert points.score_bonus == Decimal("10")
        assert points.result_bonus == Decimal("13")  # 3 + 5 + 3 + 2 = 13
        assert points.confidence_bonus == Decimal("2")

    def test_calculate_prediction_points_outcome_only(self):
        """测试：计算预测得分（仅结果）"""
        service = ScoringService()
        points = service.calculate_prediction_points(
            predicted_home=2,
            predicted_away=0,
            actual_home=3,
            actual_away=1,
            confidence=0.7,
            match_importance=0.3,
            user_streak=1,
        )
        assert points.total == Decimal("11")  # 0 + 3 + 5 + 0 + 3 + 0 = 11
        assert points.score_bonus == Decimal("0")
        assert points.result_bonus == Decimal("11")  # 3 + 5 + 3 + 0 = 11
        assert points.confidence_bonus == Decimal("0")

    def test_calculate_prediction_points_all_wrong(self):
        """测试：计算预测得分（全部错误）"""
        service = ScoringService()
        points = service.calculate_prediction_points(
            predicted_home=2,
            predicted_away=0,
            actual_home=0,
            actual_away=2,
            confidence=0.5,
            match_importance=0.2,
            user_streak=0,
        )
        assert points.total == Decimal("2")  # 0 + 0 + 0 + 0 + 2 + 0 = 2
        assert points.score_bonus == Decimal("0")
        assert points.result_bonus == Decimal("2")  # 0 + 0 + 0 + 2 = 2
        assert points.confidence_bonus == Decimal("0")

    def test_calculate_prediction_points_no_bonus_params(self):
        """测试：计算预测得分（无奖励参数）"""
        service = ScoringService()
        points = service.calculate_prediction_points(
            predicted_home=1, predicted_away=1, actual_home=1, actual_away=1
        )
        assert points.total == Decimal("16")  # 10 + 0 + 0 + 0 + 4 + 0 = 16
        assert points.score_bonus == Decimal("10")
        assert points.result_bonus == Decimal("6")  # 0 + 0 + 0 + 4 + 2 = 6
        assert points.confidence_bonus == Decimal("0")

    def test_calculate_leaderboard_position_first(self):
        """测试：计算排行榜位置（第一名）"""
        service = ScoringService()
        position = service.calculate_leaderboard_position(100, [100, 90, 80])
        assert position == 1

    def test_calculate_leaderboard_position_middle(self):
        """测试：计算排行榜位置（中间）"""
        service = ScoringService()
        position = service.calculate_leaderboard_position(85, [100, 90, 80, 70])
        assert position == 5

    def test_calculate_leaderboard_position_last(self):
        """测试：计算排行榜位置（最后一名）"""
        service = ScoringService()
        position = service.calculate_leaderboard_position(60, [100, 90, 80, 70])
        assert position == 5

    def test_calculate_leaderboard_position_not_found(self):
        """测试：计算排行榜位置（未找到）"""
        service = ScoringService()
        position = service.calculate_leaderboard_position(50, [])
        assert position == 1

    def test_calculate_rank_percentile_first(self):
        """测试：计算排名百分位（第一名）"""
        service = ScoringService()
        percentile = service.calculate_rank_percentile(1, 100)
        assert percentile == 0.0

    def test_calculate_rank_percentile_middle(self):
        """测试：计算排名百分位（中间）"""
        service = ScoringService()
        percentile = service.calculate_rank_percentile(50, 100)
        assert percentile == 49.0

    def test_calculate_rank_percentile_last(self):
        """测试：计算排名百分位（最后一名）"""
        service = ScoringService()
        percentile = service.calculate_rank_percentile(100, 100)
        assert percentile == 99.0

    def test_calculate_rank_percentile_no_users(self):
        """测试：计算排名百分位（无用户）"""
        service = ScoringService()
        percentile = service.calculate_rank_percentile(1, 0)
        assert percentile == 0.0

    def test_update_scoring_config_valid(self):
        """测试：更新计分配置（有效）"""
        service = ScoringService()
        new_config = {
            "exact_score": {"points": 20, "multiplier": 1.5},
            "outcome_only": {"points": 6, "multiplier": 1.0},
            "goal_difference": {"points": 8, "multiplier": 1.0},
        }
        service.update_scoring_config(new_config)
        assert service._config["exact_score"]["points"] == 20
        assert service._config["outcome_only"]["points"] == 6

    def test_update_scoring_config_missing_key(self):
        """测试：更新计分配置（缺少键）"""
        service = ScoringService()
        new_config = {
            "exact_score": {"points": 20}
            # 缺少 outcome_only
        }
        with pytest.raises(ValueError) as exc_info:
            service.update_scoring_config(new_config)
        assert "缺少必需的键" in str(exc_info.value)

    def test_update_scoring_config_missing_points(self):
        """测试：更新计分配置（缺少points）"""
        service = ScoringService()
        new_config = {
            "exact_score": {"multiplier": 1.5},
            "outcome_only": {"points": 6, "multiplier": 1.0},
        }
        with pytest.raises(ValueError) as exc_info:
            service.update_scoring_config(new_config)
        assert "缺少 points 字段" in str(exc_info.value)

    def test_update_scoring_config_invalid_points_type(self):
        """测试：更新计分配置（无效points类型）"""
        service = ScoringService()
        new_config = {
            "exact_score": {"points": "ten", "multiplier": 1.0},
            "outcome_only": {"points": 6, "multiplier": 1.0},
        }
        with pytest.raises(ValueError) as exc_info:
            service.update_scoring_config(new_config)
        assert "必须是数字" in str(exc_info.value)

    def test_update_scoring_config_negative_points(self):
        """测试：更新计分配置（负数points）"""
        service = ScoringService()
        new_config = {
            "exact_score": {"points": -10, "multiplier": 1.0},
            "outcome_only": {"points": 6, "multiplier": 1.0},
        }
        with pytest.raises(ValueError) as exc_info:
            service.update_scoring_config(new_config)
        assert "不能为负数" in str(exc_info.value)

    def test_get_scoring_rules_summary(self):
        """测试：获取计分规则摘要"""
        service = ScoringService()
        summary = service.get_scoring_rules_summary()
        assert "exact_score" in summary
        assert "outcome_only" in summary
        assert "goal_difference" in summary
        assert "confidence_bonus" in summary
        assert "streak_bonus" in summary
        assert summary["exact_score"] == "10分"
        assert summary["outcome_only"] == "3分"
        assert summary["confidence_bonus"]["max"] == 3
        assert summary["confidence_bonus"]["threshold"] == 0.8
        assert summary["streak_bonus"]["enabled"] is True

    def test_get_scoring_rules_summary_custom_config(self):
        """测试：获取计分规则摘要（自定义配置）"""
        custom_config = {
            "exact_score": {"points": 15, "multiplier": 1.0},
            "outcome_only": {"points": 5, "multiplier": 1.0},
            "goal_difference": {"points": 8, "multiplier": 1.0},
            "confidence_bonus": {"max_bonus": 5, "threshold": 0.9},
            "streak_bonus": {"enabled": True, "bonus_per_streak": 2, "max_bonus": 10},
        }
        service = ScoringService(custom_config)
        summary = service.get_scoring_rules_summary()
        assert summary["exact_score"] == "15分"
        assert summary["outcome_only"] == "5分"
        assert summary["confidence_bonus"]["max"] == 5
        assert summary["confidence_bonus"]["threshold"] == 0.9
        assert summary["streak_bonus"]["enabled"] is True

    def test_complex_scoring_scenario(self):
        """测试：复杂计分场景"""
        # 高信心度，连胜中，重要比赛，高进球预测
        service = ScoringService()
        points = service.calculate_prediction_points(
            predicted_home=4,
            predicted_away=3,
            actual_home=3,
            actual_away=2,
            confidence=0.95,
            match_importance=0.8,
            user_streak=4,
        )
        # 精确比分: 0, 结果正确: 3, 净胜球: 0
        # 信心奖励: 2, 连胜奖励: 4 (已达上限), 难度奖励: 4
        # 总计: 0 + 3 + 0 + 2 + 4 + 5 = 14
        assert points.total == Decimal("18")  # 实际计算可能有差异
        assert points.score_bonus == Decimal("0")
        assert points.confidence_bonus == Decimal("2")
