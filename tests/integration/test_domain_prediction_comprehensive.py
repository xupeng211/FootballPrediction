#!/usr/bin/env python3
"""
Phase 3.3 - Domain模块高价值深度优化
预测领域模型comprehensive测试，业务逻辑全覆盖
"""

from decimal import Decimal

import pytest

import logging

from src.domain.models.prediction import (

    ConfidenceScore,
    DomainError,
    Prediction,
    PredictionPoints,
    PredictionScore,
    PredictionStatus,
)


class TestConfidenceScoreComprehensive:
    """ConfidenceScore值对象全面测试"""

    def test_confidence_score_valid_range(self):
        """测试有效置信度范围"""
        # 边界值测试
        score = ConfidenceScore(Decimal("0"))
        assert score.value == Decimal("0")
        assert score.level == "low"

        score = ConfidenceScore(Decimal("1"))
        assert score.value == Decimal("1")
        assert score.level == "high"

        score = ConfidenceScore(Decimal("0.8"))
        assert score.level == "high"

        score = ConfidenceScore(Decimal("0.6"))
        assert score.level == "medium"

        score = ConfidenceScore(Decimal("0.59"))
        assert score.level == "low"

    def test_confidence_score_quantization(self):
        """测试置信度四舍五入"""
        score = ConfidenceScore(Decimal("0.856"))
        assert score.value == Decimal("0.86")

        score = ConfidenceScore(Decimal("0.123"))
        assert score.value == Decimal("0.12")

    def test_confidence_score_invalid_range(self):
        """测试无效置信度范围"""
        with pytest.raises(DomainError, match="置信度必须在 0 到 1 之间"):
            ConfidenceScore(Decimal("-0.1"))

        with pytest.raises(DomainError, match="置信度必须在 0 到 1 之间"):
            ConfidenceScore(Decimal("1.1"))

    def test_confidence_score_string_representation(self):
        """测试置信度字符串表示"""
        score = ConfidenceScore(Decimal("0.85"))
        assert str(score) == "0.85 (high)"

        score = ConfidenceScore(Decimal("0.60"))
        assert str(score) == "0.60 (medium)"

        score = ConfidenceScore(Decimal("0.45"))
        assert str(score) == "0.45 (low)"


class TestPredictionScoreComprehensive:
    """PredictionScore值对象全面测试"""

    def test_prediction_score_creation(self):
        """测试预测比分创建"""
        score = PredictionScore(predicted_home=2, predicted_away=1)
        assert score.predicted_home == 2
        assert score.predicted_away == 1
        assert score.actual_home is None
        assert score.actual_away is None
        assert not score.is_evaluated

    def test_prediction_score_negative_prediction(self):
        """测试负数预测比分"""
        with pytest.raises(DomainError, match="预测比分不能为负数"):
            PredictionScore(predicted_home=-1, predicted_away=1)

        with pytest.raises(DomainError, match="预测比分不能为负数"):
            PredictionScore(predicted_home=1, predicted_away=-1)

    def test_prediction_score_negative_actual(self):
        """测试负数实际比分"""
        with pytest.raises(DomainError, match="实际主队比分不能为负数"):
            PredictionScore(predicted_home=2, predicted_away=1, actual_home=-1)

        with pytest.raises(DomainError, match="实际客队比分不能为负数"):
            PredictionScore(predicted_home=2, predicted_away=1, actual_away=-1)

    def test_prediction_score_correct_score(self):
        """测试精确比分判断"""
        score = PredictionScore(predicted_home=2, predicted_away=1)
        assert not score.is_correct_score

        # 添加实际比分
        score.actual_home = 2
        score.actual_away = 1
        assert score.is_correct_score
        assert score.is_evaluated

    def test_prediction_score_correct_result(self):
        """测试结果正确判断"""
        score = PredictionScore(predicted_home=2, predicted_away=1)

        # 主队获胜
        score.actual_home = 3
        score.actual_away = 1
        assert score.is_correct_result

        # 客队获胜
        score = PredictionScore(predicted_home=1, predicted_away=2)
        score.actual_home = 0
        score.actual_away = 2
        assert score.is_correct_result

        # 平局
        score = PredictionScore(predicted_home=1, predicted_away=1)
        score.actual_home = 2
        score.actual_away = 2
        assert score.is_correct_result

        # 结果错误
        score = PredictionScore(predicted_home=2, predicted_away=1)
        score.actual_home = 0
        score.actual_away = 2
        assert not score.is_correct_result

    def test_prediction_score_goal_difference_error(self):
        """测试净胜球误差计算"""
        score = PredictionScore(predicted_home=2, predicted_away=1)

        # 未评估时误差为0
        assert score.goal_difference_error == 0

        # 评估后计算误差
        score.actual_home = 3
        score.actual_away = 1
        assert score.goal_difference_error == 1  # (2-1) - (3-1) = -1, abs=1

        score.actual_home = 1
        score.actual_away = 3
        assert score.goal_difference_error == 3  # (2-1) - (1-3) = 3

    def test_prediction_score_string_representation(self):
        """测试比分字符串表示"""
        # 未评估
        score = PredictionScore(predicted_home=2, predicted_away=1)
        assert str(score) == "2-1"

        # 已评估
        score.actual_home = 2
        score.actual_away = 1
        assert str(score) == "2-1 (实际: 2-1)"


class TestPredictionPointsComprehensive:
    """PredictionPoints值对象全面测试"""

    def test_prediction_points_default(self):
        """测试默认积分"""
        points = PredictionPoints()
        assert points.total == Decimal("0")
        assert points.score_bonus == Decimal("0")
        assert points.result_bonus == Decimal("0")
        assert points.confidence_bonus == Decimal("0")

    def test_prediction_points_quantization(self):
        """测试积分四舍五入"""
        points = PredictionPoints(
            total=Decimal("10.567"),
            score_bonus=Decimal("5.234"),
            result_bonus=Decimal("3.876"),
            confidence_bonus=Decimal("1.456"),
        )

        assert points.total == Decimal("10.57")
        assert points.score_bonus == Decimal("5.23")
        assert points.result_bonus == Decimal("3.88")
        assert points.confidence_bonus == Decimal("1.46")

    def test_prediction_points_breakdown(self):
        """测试积分明细"""
        points = PredictionPoints(
            total=Decimal("15.50"),
            score_bonus=Decimal("10.00"),
            result_bonus=Decimal("3.00"),
            confidence_bonus=Decimal("2.50"),
        )

        breakdown = points.breakdown
        expected = {
            "score_bonus": Decimal("10.00"),
            "result_bonus": Decimal("3.00"),
            "confidence_bonus": Decimal("2.50"),
            "total": Decimal("15.50"),
        }
        assert breakdown == expected

    def test_prediction_points_string_representation(self):
        """测试积分字符串表示"""
        points = PredictionPoints(total=Decimal("15.50"))
        assert str(points) == "15.50 分"


class TestPredictionDomainComprehensive:
    """Prediction领域模型全面测试"""

    def test_prediction_creation_valid(self):
        """测试有效预测创建"""
        prediction = Prediction(user_id=1, match_id=100)

        assert prediction.user_id == 1
        assert prediction.match_id == 100
        assert prediction.status == PredictionStatus.PENDING
        assert prediction.is_pending
        assert not prediction.is_evaluated
        assert not prediction.is_cancelled
        assert not prediction.is_expired
        assert prediction.score is None
        assert prediction.confidence is None
        assert prediction.points is None

    def test_prediction_creation_invalid(self):
        """测试无效预测创建"""
        # 无效用户ID
        with pytest.raises(DomainError, match="用户ID必须大于0"):
            Prediction(user_id=0, match_id=100)

        with pytest.raises(DomainError, match="用户ID必须大于0"):
            Prediction(user_id=-1, match_id=100)

        # 无效比赛ID
        with pytest.raises(DomainError, match="比赛ID必须大于0"):
            Prediction(user_id=1, match_id=0)

        with pytest.raises(DomainError, match="比赛ID必须大于0"):
            Prediction(user_id=1, match_id=-1)

    def test_make_prediction_success(self):
        """测试成功创建预测"""
        prediction = Prediction(user_id=1, match_id=100)

        prediction.make_prediction(
            predicted_home=2, predicted_away=1, confidence=0.85, model_version="v1.0"
        )

        assert prediction.score.predicted_home == 2
        assert prediction.score.predicted_away == 1
        assert prediction.confidence.value == Decimal("0.85")
        assert prediction.confidence.level == "high"
        assert prediction.model_version == "v1.0"

    def test_make_prediction_invalid_confidence(self):
        """测试无效置信度创建预测"""
        prediction = Prediction(user_id=1, match_id=100)

        with pytest.raises(DomainError):
            prediction.make_prediction(
                predicted_home=2, predicted_away=1, confidence=1.5  # 超出范围
            )

    def test_make_prediction_non_pending_status(self):
        """测试非待处理状态创建预测"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.status = PredictionStatus.EVALUATED

        with pytest.raises(DomainError, match="预测状态为 evaluated，无法修改"):
            prediction.make_prediction(2, 1)

    def test_evaluate_prediction_success(self):
        """测试成功评估预测"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(predicted_home=2, predicted_away=1, confidence=0.8)

        # 精确比分
        prediction.evaluate(actual_home=2, actual_away=1)

        assert prediction.is_evaluated
        assert prediction.status == PredictionStatus.EVALUATED
        assert prediction.evaluated_at is not None
        assert prediction.score.is_correct_score
        assert prediction.points is not None
        assert prediction.points.score_bonus > 0
        assert prediction.accuracy_score == 1.0

    def test_evaluate_prediction_correct_result(self):
        """测试评估预测结果正确"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(predicted_home=2, predicted_away=0, confidence=0.7)

        # 结果正确但比分不准确
        prediction.evaluate(actual_home=3, actual_away=1)

        assert prediction.is_evaluated
        assert not prediction.score.is_correct_score
        assert prediction.score.is_correct_result
        assert prediction.points.result_bonus > 0
        assert prediction.points.score_bonus == 0

    def test_evaluate_prediction_incorrect(self):
        """测试评估预测错误"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(predicted_home=2, predicted_away=1, confidence=0.6)

        # 完全错误
        prediction.evaluate(actual_home=0, actual_away=2)

        assert prediction.is_evaluated
        assert not prediction.score.is_correct_score
        assert not prediction.score.is_correct_result
        assert prediction.points.total == Decimal("0")

    def test_evaluate_prediction_no_score(self):
        """测试评估没有比分的预测"""
        prediction = Prediction(user_id=1, match_id=100)

        with pytest.raises(DomainError, match="预测必须包含比分才能评估"):
            prediction.evaluate(actual_home=2, actual_away=1)

    def test_evaluate_prediction_non_pending_status(self):
        """评估非待处理状态的预测"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(2, 1)
        prediction.status = PredictionStatus.CANCELLED

        with pytest.raises(DomainError, match="预测状态为 cancelled，无法评估"):
            prediction.evaluate(2, 1)

    def test_cancel_prediction_success(self):
        """测试成功取消预测"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(2, 1)

        prediction.cancel("用户主动取消")

        assert prediction.is_cancelled
        assert prediction.status == PredictionStatus.CANCELLED
        assert prediction.cancelled_at is not None
        assert prediction.cancellation_reason == "用户主动取消"

    def test_cancel_prediction_evaluated(self):
        """测试取消已评估的预测"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(2, 1)
        prediction.evaluate(2, 1)

        with pytest.raises(DomainError, match="预测状态为 evaluated，无法取消"):
            prediction.cancel()

    def test_cancel_prediction_already_cancelled(self):
        """测试取消已取消的预测"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(2, 1)
        prediction.cancel()

        with pytest.raises(DomainError, match="预测状态为 cancelled，无法取消"):
            prediction.cancel()

    def test_mark_expired_success(self):
        """测试成功标记过期"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(2, 1)

        prediction.mark_expired()

        assert prediction.is_expired
        assert prediction.status == PredictionStatus.EXPIRED

    def test_mark_expired_non_pending(self):
        """测试标记非待处理状态为过期"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(2, 1)
        prediction.status = PredictionStatus.EVALUATED

        with pytest.raises(DomainError, match="预测状态为 evaluated，无法标记为过期"):
            prediction.mark_expired()

    def test_scoring_rules_custom(self):
        """测试自定义积分规则"""
        custom_rules = {
            "exact_score": Decimal("15"),
            "correct_result": Decimal("5"),
            "confidence_multiplier": Decimal("2"),
        }

        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(2, 1, confidence=0.9)
        prediction.evaluate(2, 1, custom_rules)

        assert prediction.points.score_bonus == Decimal("15")
        assert prediction.points.total > Decimal("15")  # 包含置信度奖励

    def test_confidence_bonus_calculation(self):
        """测试置信度奖励计算"""
        # 高置信度
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(2, 1, confidence=0.9)
        prediction.evaluate(2, 1)

        high_confidence_bonus = prediction.points.confidence_bonus

        # 低置信度
        prediction2 = Prediction(user_id=1, match_id=101)
        prediction2.make_prediction(2, 1, confidence=0.6)
        prediction2.evaluate(2, 1)

        low_confidence_bonus = prediction2.points.confidence_bonus

        assert high_confidence_bonus > low_confidence_bonus

    def test_accuracy_score_calculation(self):
        """测试准确度分数计算"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(2, 1, confidence=0.8)

        # 未评估时准确度为0
        assert prediction.accuracy_score == 0.0

        # 精确比分
        prediction.evaluate(2, 1)
        assert prediction.accuracy_score == 1.0

        # 只有结果正确
        prediction2 = Prediction(user_id=1, match_id=101)
        prediction2.make_prediction(2, 0, confidence=0.7)
        prediction2.evaluate(3, 1)  # 都是主队胜
        expected_accuracy = 0.0 * 0.7 + 1.0 * 0.3  # 0.3
        assert abs(prediction2.accuracy_score - expected_accuracy) < 0.001

    def test_get_prediction_summary(self):
        """测试获取预测摘要"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(2, 1, confidence=0.85)
        prediction.evaluate(2, 1)

        summary = prediction.get_prediction_summary()

        assert summary["predicted"] == "2-1"
        assert summary["actual"] == "2-1"
        assert summary["confidence"] == "0.85 (high)"
        assert summary["points"] is not None
        assert summary["is_correct_score"] is True
        assert summary["is_correct_result"] is True
        assert summary["accuracy"] == 1.0

    def test_get_prediction_summary_no_prediction(self):
        """测试获取无预测的摘要"""
        prediction = Prediction(user_id=1, match_id=100)

        summary = prediction.get_prediction_summary()

        assert summary["status"] == "no_prediction"

    def test_domain_event_management(self):
        """测试领域事件管理"""
        prediction = Prediction(user_id=1, match_id=100)

        # 创建预测时产生事件
        prediction.make_prediction(2, 1, confidence=0.8)
        events = prediction.get_domain_events()
        assert len(events) == 1

        # 评估预测时产生事件
        prediction.evaluate(2, 1)
        events = prediction.get_domain_events()
        assert len(events) == 2

        # 清除事件
        prediction.clear_domain_events()
        events = prediction.get_domain_events()
        assert len(events) == 0

    def test_to_dict_serialization(self):
        """测试字典序列化"""
        prediction = Prediction(id=1, user_id=100, match_id=200, model_version="v1.0")
        prediction.make_prediction(2, 1, confidence=0.85)
        prediction.evaluate(2, 1)

        data = prediction.to_dict()

        assert data["id"] == 1
        assert data["user_id"] == 100
        assert data["match_id"] == 200
        assert data["status"] == "evaluated"
        assert data["model_version"] == "v1.0"
        assert data["confidence"] == 0.85
        assert data["score"]["predicted_home"] == 2
        assert data["score"]["predicted_away"] == 1
        assert data["score"]["actual_home"] == 2
        assert data["score"]["actual_away"] == 1
        assert data["points"]["total"] > 0

    def test_from_dict_deserialization(self):
        """测试字典反序列化"""
        data = {
            "id": 1,
            "user_id": 100,
            "match_id": 200,
            "status": "evaluated",
            "model_version": "v1.0",
            "confidence": 0.85,
            "score": {
                "predicted_home": 2,
                "predicted_away": 1,
                "actual_home": 2,
                "actual_away": 1,
            },
            "points": {
                "total": 12.50,
                "breakdown": {
                    "score_bonus": 10.00,
                    "result_bonus": 0.00,
                    "confidence_bonus": 2.50,
                },
            },
            "created_at": "2024-01-01T10:00:00",
            "evaluated_at": "2024-01-01T12:00:00",
        }

        prediction = Prediction.from_dict(data)

        assert prediction.id == 1
        assert prediction.user_id == 100
        assert prediction.match_id == 200
        assert prediction.status == PredictionStatus.EVALUATED
        assert prediction.model_version == "v1.0"
        assert prediction.confidence.value == Decimal("0.85")
        assert prediction.score.predicted_home == 2
        assert prediction.score.actual_home == 2
        assert prediction.points.total == Decimal("12.50")

    def test_string_representation(self):
        """测试字符串表示"""
        prediction = Prediction(user_id=1, match_id=100)

        # 未预测
        assert "未预测" in str(prediction)

        # 已预测
        prediction.make_prediction(2, 1, confidence=0.8)
        assert "2-1" in str(prediction)

        # 已评估
        prediction.evaluate(2, 1)
        assert "2-1" in str(prediction)
        assert "evaluated" in str(prediction)


def test_prediction_domain_comprehensive_suite(client):
    """预测领域模型综合测试套件"""
    # 快速验证核心功能
    prediction = Prediction(user_id=1, match_id=100)
    assert prediction.is_pending

    prediction.make_prediction(2, 1, confidence=0.8)
    assert prediction.score is not None
    assert prediction.confidence is not None

    prediction.evaluate(2, 1)
    assert prediction.is_evaluated
    assert prediction.points is not None

    logger.debug("✅ 预测领域模型综合测试套件通过")  # TODO: Add logger import if needed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
