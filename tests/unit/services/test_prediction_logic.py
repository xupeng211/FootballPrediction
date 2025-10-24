"""
预测逻辑核心业务测试
测试预测计算和验证逻辑
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple
import math


# 测试预测计算逻辑
@pytest.mark.unit

class TestPredictionCalculations:
    """预测计算测试"""

    def test_confidence_calculation(self):
        """测试置信度计算"""

        # 基础置信度计算
        def calculate_confidence(
            historical_accuracy: float,
            team_form_diff: float,
            home_advantage: float = 0.1,
        ) -> float:
            """计算预测置信度"""
            base_confidence = historical_accuracy * 0.6
            form_weight = team_form_diff * 0.3
            home_weight = home_advantage * 0.1

            confidence = base_confidence + form_weight + home_weight
            return max(0.0, min(1.0, confidence))

        # 测试不同场景
        test_cases = [
            # (历史准确率, 队伍状态差, 主场优势, 期望范围)
            (0.8, 0.2, 0.1, (0.5, 1.0)),
            (0.6, 0.0, 0.0, (0.3, 0.7)),
            (0.5, -0.1, 0.1, (0.2, 0.6)),
            (0.9, 0.3, 0.15, (0.6, 1.0)),
            (0.3, -0.2, 0.0, (0.1, 0.4)),
        ]

        for hist_acc, form_diff, home_adv, expected_range in test_cases:
            confidence = calculate_confidence(hist_acc, form_diff, home_adv)
            assert expected_range[0] <= confidence <= expected_range[1]
            assert 0.0 <= confidence <= 1.0

    def test_score_prediction_probability(self):
        """测试比分预测概率"""

        def calculate_score_probability(
            home_attack: float,
            home_defense: float,
            away_attack: float,
            away_defense: float,
        ) -> Tuple[float, float]:
            """计算预期进球数"""
            # 基础预期进球
            expected_home = (home_attack * away_defense) / 100
            expected_away = (away_attack * home_defense) / 100

            # 应用泊松分布的简化版本
            home_goals = max(0, min(10, expected_home))
            away_goals = max(0, min(10, expected_away))

            return home_goals, away_goals

        test_cases = [
            (80, 70, 60, 75, (0.6, 0.5)),
            (90, 50, 70, 60, (1.0, 0.8)),
            (50, 80, 90, 70, (0.4, 1.1)),
            (70, 70, 70, 70, (0.5, 0.5)),
        ]

        for home_att, home_def, away_att, away_def, expected in test_cases:
            home_goals, away_goals = calculate_score_probability(
                home_att, home_def, away_att, away_def
            )
            assert 0 <= home_goals <= 10
            assert 0 <= away_goals <= 10
            # 验证大致范围
            assert abs(home_goals - expected[0]) < 0.5
            assert abs(away_goals - expected[1]) < 0.5

    def test_prediction_accuracy_calculation(self):
        """测试预测准确率计算"""

        def calculate_accuracy(predictions: List[Dict]) -> float:
            """计算预测准确率"""
            if not predictions:
                return 0.0

            correct = sum(1 for p in predictions if p.get("is_correct", False))
            return correct / len(predictions)

        # 测试数据
        test_cases = [
            ([], 0.0),
            ([{"is_correct": True}], 1.0),
            ([{"is_correct": False}], 0.0),
            ([{"is_correct": True}, {"is_correct": False}], 0.5),
            (
                [
                    {"is_correct": True},
                    {"is_correct": True},
                    {"is_correct": True},
                    {"is_correct": False},
                    {"is_correct": False},
                ],
                0.6,
            ),
            ([{"is_correct": True} for _ in range(5)], 1.0),
            ([{"is_correct": False} for _ in range(10)], 0.0),
        ]

        for predictions, expected in test_cases:
            accuracy = calculate_accuracy(predictions)
            assert abs(accuracy - expected) < 0.001

    def test_streak_calculation(self):
        """测试连胜/连败计算"""

        def calculate_streak(results: List[bool]) -> int:
            """计算当前连胜/连败"""
            if not results:
                return 0

            streak = 0
            current = results[-1]

            for result in reversed(results):
                if _result == current:
                    streak += 1
                else:
                    break

            return streak if current else -streak

        test_cases = [
            ([], 0),
            ([True], 1),
            ([False], -1),
            ([True, True, True], 3),
            ([False, False, False], -3),
            ([True, False, True], 1),
            ([False, True, False, False], -2),
        ]

        for results, expected in test_cases:
            streak = calculate_streak(results)
            assert streak == expected


class TestPredictionValidation:
    """预测验证测试"""

    def test_score_validation(self):
        """测试比分验证"""

        def validate_score(home_score: int, away_score: int) -> bool:
            """验证比分是否合理"""
            if not isinstance(home_score, int) or not isinstance(away_score, int):
                return False
            if home_score < 0 or away_score < 0:
                return False
            if home_score > 20 or away_score > 20:  # 足球比赛通常不会有太多进球
                return False
            return True

        # 测试有效比分
        valid_scores = [(0, 0), (1, 0), (0, 1), (1, 1), (2, 1), (3, 2), (5, 0), (10, 9)]

        for home, away in valid_scores:
            assert validate_score(home, away) is True

        # 测试无效比分
        invalid_scores = [
            (-1, 0),
            (0, -1),
            (-1, -1),  # 负数
            (2.5, 1),
            (1, 3.5),  # 非整数
            (25, 0),
            (0, 30),  # 过大的数字
            ("1", 0),
            (0, "2"),  # 字符串
            (None, 0),
            (0, None),  # None值
        ]

        for home, away in invalid_scores:
            assert validate_score(home, away) is False

    def test_confidence_validation(self):
        """测试置信度验证"""

        def validate_confidence(confidence: float) -> bool:
            """验证置信度是否在有效范围内"""
            if not isinstance(confidence, (int, float)):
                return False
            if not (0.0 <= confidence <= 1.0):
                return False
            if math.isnan(confidence) or math.isinf(confidence):
                return False
            return True

        # 测试有效置信度
        valid_confidences = [0.0, 0.5, 0.85, 1.0, 0.333, 0.666]

        for confidence in valid_confidences:
            assert validate_confidence(confidence) is True

        # 测试无效置信度
        invalid_confidences = [
            -0.1,
            1.1,  # 超出范围
            None,
            "0.5",  # 错误类型
            float("nan"),
            float("inf"),
            float("-inf"),  # 特殊值
        ]

        for confidence in invalid_confidences:
            assert validate_confidence(confidence) is False

    def test_match_time_validation(self):
        """测试比赛时间验证"""

        def validate_match_time(
            match_time: datetime, prediction_time: datetime
        ) -> bool:
            """验证预测时间是否在比赛开始前"""
            if not isinstance(match_time, datetime) or not isinstance(
                prediction_time, datetime
            ):
                return False
            # 必须在比赛开始前至少1小时预测
            time_diff = match_time - prediction_time
            return time_diff >= timedelta(hours=1)

        now = datetime.now(timezone.utc)

        # 测试有效时间
        valid_cases = [
            (now + timedelta(hours=2), now),
            (now + timedelta(days=1), now),
            (now + timedelta(hours=24), now + timedelta(hours=10)),
        ]

        for match_time, pred_time in valid_cases:
            assert validate_match_time(match_time, pred_time) is True

        # 测试无效时间
        invalid_cases = [
            (now - timedelta(hours=1), now),  # 比赛已开始
            (now, now),  # 比赛正在进行
            (now + timedelta(minutes=30), now),  # 不足1小时
            (
                now + timedelta(hours=2),
                now + timedelta(hours=3),
            ),  # 预测时间晚于比赛时间
        ]

        for match_time, pred_time in invalid_cases:
            assert validate_match_time(match_time, pred_time) is False


class TestPredictionBusinessRules:
    """预测业务规则测试"""

    def test_max_predictions_per_user(self):
        """测试用户每场比赛最大预测数限制"""
        MAX_PREDICTIONS_PER_MATCH = 3

        def can_add_prediction(user_predictions: List[int], match_id: int) -> bool:
            """检查用户是否可以添加预测"""
            count = sum(1 for p in user_predictions if p == match_id)
            return count < MAX_PREDICTIONS_PER_MATCH

        # 测试用例
        user_predictions = [1, 1, 2, 3, 1, 4]

        assert can_add_prediction(user_predictions, 1) is False  # 已有3个预测
        assert can_add_prediction(user_predictions, 2) is True  # 只有1个预测
        assert can_add_prediction(user_predictions, 5) is True  # 没有预测

    def test_prediction_deadline(self):
        """测试预测截止时间"""
        PREDICTION_DEADLINE_HOURS = 1  # 比赛前1小时

        def is_prediction_open(match_time: datetime, current_time: datetime) -> bool:
            """检查预测是否开放"""
            deadline = match_time - timedelta(hours=PREDICTION_DEADLINE_HOURS)
            return current_time < deadline

        now = datetime.now(timezone.utc)

        # 测试开放状态
        open_cases = [
            now + timedelta(hours=2),
            now + timedelta(days=1),
            now + timedelta(hours=1, minutes=1),  # 刚好超过1小时
        ]

        for match_time in open_cases:
            assert is_prediction_open(match_time, now) is True

        # 测试关闭状态
        closed_cases = [
            now - timedelta(hours=1),
            now,
            now + timedelta(minutes=59),  # 不足1小时
        ]

        for match_time in closed_cases:
            assert is_prediction_open(match_time, now) is False

    def test_user_eligibility(self):
        """测试用户预测资格"""

        def check_eligibility(
            is_active: bool, has_suspended: bool, min_predictions: int = 0
        ) -> bool:
            """检查用户是否有资格进行预测"""
            if not is_active:
                return False
            if has_suspended:
                return False
            # 这里可以添加更多规则，如最小预测数等
            return True

        # 测试用户状态
        test_cases = [
            (True, False, True),  # 正常用户
            (False, False, False),  # 非活跃用户
            (True, True, False),  # 被暂停用户
            (False, True, False),  # 非活跃且被暂停
        ]

        for is_active, suspended, expected in test_cases:
            assert check_eligibility(is_active, suspended) == expected

    def test_prediction_scoring(self):
        """测试预测得分计算"""

        def calculate_score(
            predicted_home: int, predicted_away: int, actual_home: int, actual_away: int
        ) -> int:
            """计算预测得分"""
            # 完全正确：10分
            if predicted_home == actual_home and predicted_away == actual_away:
                return 10

            # 正确预测胜负平：3分
            pred_result = (
                "home"
                if predicted_home > predicted_away
                else "away"
                if predicted_home < predicted_away
                else "draw"
            )
            actual_result = (
                "home"
                if actual_home > actual_away
                else "away"
                if actual_home < actual_away
                else "draw"
            )

            if pred_result == actual_result:
                return 3

            # 预测正确进球数差：1分
            pred_diff = abs(predicted_home - predicted_away)
            actual_diff = abs(actual_home - actual_away)

            if pred_diff == actual_diff:
                return 1

            # 其他情况：0分
            return 0

        # 测试用例
        test_cases = [
            # (预测比分, 实际比分, 期望得分)
            ((2, 1), (2, 1), 10),  # 完全正确
            ((1, 0), (2, 0), 3),  # 预测主胜
            ((0, 0), (1, 1), 3),  # 预测平局
            ((1, 2), (1, 3), 3),  # 预测客胜
            ((2, 0), (3, 1), 1),  # 预测1球差距
            ((3, 1), (2, 0), 1),  # 预测2球差距
            ((2, 1), (1, 2), 0),  # 完全错误
        ]

        for (pred_h, pred_a), (act_h, act_a), expected in test_cases:
            score = calculate_score(pred_h, pred_a, act_h, act_a)
            assert score == expected
