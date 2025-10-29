"""
Prediction领域模型边界条件测试 - 修复版本
基于实际Prediction模型API的完整测试覆盖，目标达到90%+覆盖率
"""

from decimal import Decimal

import pytest

from src.core.exceptions import DomainError
from src.domain.models.prediction import (
    ConfidenceScore,
    Prediction,
    PredictionPoints,
    PredictionScore,
    PredictionStatus,
)


@pytest.mark.unit
class TestConfidenceScore:
    """ConfidenceScore值对象边界条件测试"""

    def test_confidence_score_initialization_valid(self) -> None:
        """✅ 成功用例：有效置信度初始化"""
        # 中等置信度
        confidence = ConfidenceScore(Decimal("0.75"))
        assert confidence.value == Decimal("0.75")
        assert confidence.level == "medium"

        # 高置信度
        confidence = ConfidenceScore(Decimal("0.85"))
        assert confidence.value == Decimal("0.85")
        assert confidence.level == "high"

        # 低置信度
        confidence = ConfidenceScore(Decimal("0.45"))
        assert confidence.value == Decimal("0.45")
        assert confidence.level == "low"

    def test_confidence_score_quantization(self) -> None:
        """✅ 成功用例：置信度四舍五入"""
        # 多位小数应该被四舍五入
        confidence = ConfidenceScore(Decimal("0.786"))
        assert confidence.value == Decimal("0.79")

        confidence = ConfidenceScore(Decimal("0.784"))
        assert confidence.value == Decimal("0.78")

        confidence = ConfidenceScore(Decimal("0.785"))
        assert confidence.value == Decimal("0.78")  # 银行家舍入法

    def test_confidence_score_boundary_values(self) -> None:
        """✅ 边界用例：边界值测试"""
        # 最小值
        confidence = ConfidenceScore(Decimal("0"))
        assert confidence.value == Decimal("0")
        assert confidence.level == "low"

        # 最大值
        confidence = ConfidenceScore(Decimal("1"))
        assert confidence.value == Decimal("1")
        assert confidence.level == "high"

        # 高置信度边界
        confidence = ConfidenceScore(Decimal("0.8"))
        assert confidence.level == "high"

        confidence = ConfidenceScore(Decimal("0.799"))
        assert confidence.level == "high"  # 0.799四舍五入为0.80

        # 中等置信度边界
        confidence = ConfidenceScore(Decimal("0.6"))
        assert confidence.level == "medium"

        confidence = ConfidenceScore(Decimal("0.599"))
        assert confidence.level == "medium"  # 0.599四舍五入为0.60

    def test_confidence_score_negative_values(self) -> None:
        """✅ 边界用例：负值验证"""
        with pytest.raises(DomainError, match="置信度必须在 0 到 1 之间"):
            ConfidenceScore(Decimal("-0.1"))

        with pytest.raises(DomainError, match="置信度必须在 0 到 1 之间"):
            ConfidenceScore(Decimal("-1"))

        with pytest.raises(DomainError, match="置信度必须在 0 到 1 之间"):
            ConfidenceScore(Decimal("-10"))

    def test_confidence_score_over_limit_values(self) -> None:
        """✅ 边界用例：超限值验证"""
        with pytest.raises(DomainError, match="置信度必须在 0 到 1 之间"):
            ConfidenceScore(Decimal("1.1"))

        with pytest.raises(DomainError, match="置信度必须在 0 到 1 之间"):
            ConfidenceScore(Decimal("2"))

        with pytest.raises(DomainError, match="置信度必须在 0 到 1 之间"):
            ConfidenceScore(Decimal("10"))

    def test_confidence_score_string_representation(self) -> None:
        """✅ 成功用例：字符串表示"""
        confidence = ConfidenceScore(Decimal("0.85"))
        assert str(confidence) == "0.85 (high)"

        confidence = ConfidenceScore(Decimal("0.65"))
        assert str(confidence) == "0.65 (medium)"

        confidence = ConfidenceScore(Decimal("0.45"))
        assert str(confidence) == "0.45 (low)"

    def test_confidence_score_edge_cases(self) -> None:
        """✅ 边界用例：极端情况测试"""
        # 极小正值
        confidence = ConfidenceScore(Decimal("0.001"))
        assert confidence.value == Decimal("0.00")
        assert confidence.level == "low"

        # 接近1的值
        confidence = ConfidenceScore(Decimal("0.999"))
        assert confidence.value == Decimal("1.00")
        assert confidence.level == "high"


@pytest.mark.unit
class TestPredictionScore:
    """PredictionScore值对象边界条件测试"""

    def test_prediction_score_initialization_valid(self) -> None:
        """✅ 成功用例：有效比分初始化"""
        score = PredictionScore(predicted_home=2, predicted_away=1)
        assert score.predicted_home == 2
        assert score.predicted_away == 1
        assert score.actual_home is None
        assert score.actual_away is None
        assert not score.is_evaluated

    def test_prediction_score_with_actual_results(self) -> None:
        """✅ 成功用例：包含实际比分的初始化"""
        score = PredictionScore(predicted_home=2, predicted_away=1, actual_home=3, actual_away=1)
        assert score.predicted_home == 2
        assert score.predicted_away == 1
        assert score.actual_home == 3
        assert score.actual_away == 1
        assert score.is_evaluated

    def test_prediction_score_negative_predicted_values(self) -> None:
        """✅ 边界用例：负预测比分验证"""
        with pytest.raises(DomainError, match="预测比分不能为负数"):
            PredictionScore(predicted_home=-1, predicted_away=0)

        with pytest.raises(DomainError, match="预测比分不能为负数"):
            PredictionScore(predicted_home=0, predicted_away=-1)

        with pytest.raises(DomainError, match="预测比分不能为负数"):
            PredictionScore(predicted_home=-1, predicted_away=-1)

    def test_prediction_score_negative_actual_values(self) -> None:
        """✅ 边界用例：负实际比分验证"""
        with pytest.raises(DomainError, match="实际主队比分不能为负数"):
            PredictionScore(predicted_home=2, predicted_away=1, actual_home=-1, actual_away=1)

        with pytest.raises(DomainError, match="实际客队比分不能为负数"):
            PredictionScore(predicted_home=2, predicted_away=1, actual_home=1, actual_away=-1)

    def test_prediction_score_zero_values(self) -> None:
        """✅ 边界用例：零比分测试"""
        score = PredictionScore(predicted_home=0, predicted_away=0)
        assert score.predicted_home == 0
        assert score.predicted_away == 0

        score = PredictionScore(predicted_home=2, predicted_away=1, actual_home=0, actual_away=0)
        assert score.actual_home == 0
        assert score.actual_away == 0

    def test_prediction_score_correct_score_check(self) -> None:
        """✅ 成功用例：正确比分检查"""
        # 完全正确的比分
        score = PredictionScore(predicted_home=2, predicted_away=1, actual_home=2, actual_away=1)
        assert score.is_correct_score is True

        # 错误的比分
        score = PredictionScore(predicted_home=2, predicted_away=1, actual_home=1, actual_away=2)
        assert score.is_correct_score is False

        # 未评估的比分
        score = PredictionScore(predicted_home=2, predicted_away=1)
        assert score.is_correct_score is False

    def test_prediction_score_correct_result_check(self) -> None:
        """✅ 成功用例：正确结果检查"""
        # 主队获胜预测正确
        score = PredictionScore(predicted_home=2, predicted_away=1, actual_home=3, actual_away=1)
        assert score.is_correct_result is True

        # 客队获胜预测正确
        score = PredictionScore(predicted_home=1, predicted_away=2, actual_home=0, actual_away=3)
        assert score.is_correct_result is True

        # 平局预测正确
        score = PredictionScore(predicted_home=1, predicted_away=1, actual_home=2, actual_away=2)
        assert score.is_correct_result is True

        # 主队获胜预测错误
        score = PredictionScore(predicted_home=2, predicted_away=1, actual_home=1, actual_away=2)
        assert score.is_correct_result is False

        # 未评估的结果
        score = PredictionScore(predicted_home=2, predicted_away=1)
        assert score.is_correct_result is False

    def test_prediction_score_goal_difference_error(self) -> None:
        """✅ 成功用例：净胜球误差计算"""
        # 完全正确的比分
        score = PredictionScore(predicted_home=2, predicted_away=1, actual_home=2, actual_away=1)
        assert score.goal_difference_error == 0

        # 预测主队胜2球，实际胜1球
        score = PredictionScore(predicted_home=3, predicted_away=1, actual_home=2, actual_away=1)
        assert score.goal_difference_error == 1

        # 预测客队胜，实际主队胜
        score = PredictionScore(predicted_home=1, predicted_away=3, actual_home=2, actual_away=1)
        assert score.goal_difference_error == 3

        # 未评估的比分
        score = PredictionScore(predicted_home=2, predicted_away=1)
        assert score.goal_difference_error == 0

    def test_prediction_score_string_representation(self) -> None:
        """✅ 成功用例：字符串表示"""
        # 未评估的比分
        score = PredictionScore(predicted_home=2, predicted_away=1)
        assert str(score) == "2-1"

        # 已评估的比分
        score = PredictionScore(predicted_home=2, predicted_away=1, actual_home=3, actual_away=1)
        assert str(score) == "2-1 (实际: 3-1)"

    def test_prediction_score_edge_cases(self) -> None:
        """✅ 边界用例：极端比分测试"""
        # 大比分预测
        score = PredictionScore(predicted_home=10, predicted_away=8)
        assert score.predicted_home == 10
        assert score.predicted_away == 8

        # 大比分实际
        score = PredictionScore(predicted_home=2, predicted_away=1, actual_home=15, actual_away=12)
        assert score.goal_difference_error == 2  # |(2-1) - (15-12)| = |1 - 3| = 2

        # 0-0平局
        score = PredictionScore(predicted_home=0, predicted_away=0, actual_home=0, actual_away=0)
        assert score.is_correct_score is True
        assert score.is_correct_result is True


@pytest.mark.unit
class TestPredictionPoints:
    """PredictionPoints值对象边界条件测试"""

    def test_prediction_points_initialization_default(self) -> None:
        """✅ 成功用例：默认初始化"""
        points = PredictionPoints()
        assert points.total == Decimal("0")
        assert points.score_bonus == Decimal("0")
        assert points.result_bonus == Decimal("0")
        assert points.confidence_bonus == Decimal("0")

    def test_prediction_points_initialization_with_values(self) -> None:
        """✅ 成功用例：指定值初始化"""
        points = PredictionPoints(
            total=Decimal("15.5"),
            score_bonus=Decimal("10"),
            result_bonus=Decimal("3"),
            confidence_bonus=Decimal("2.5"),
        )
        assert points.total == Decimal("15.5")
        assert points.score_bonus == Decimal("10")
        assert points.result_bonus == Decimal("3")
        assert points.confidence_bonus == Decimal("2.5")

    def test_prediction_points_quantization(self) -> None:
        """✅ 成功用例：四舍五入处理"""
        # 多位小数应该被四舍五入
        points = PredictionPoints(total=Decimal("15.786"))
        assert points.total == Decimal("15.79")

        points = PredictionPoints(score_bonus=Decimal("10.784"))
        assert points.score_bonus == Decimal("10.78")

        points = PredictionPoints(result_bonus=Decimal("3.785"))
        assert points.result_bonus == Decimal("3.78")  # 银行家舍入法

    def test_prediction_points_breakdown_property(self) -> None:
        """✅ 成功用例：积分明细属性"""
        points = PredictionPoints(
            total=Decimal("15.5"),
            score_bonus=Decimal("10"),
            result_bonus=Decimal("3"),
            confidence_bonus=Decimal("2.5"),
        )

        breakdown = points.breakdown
        assert breakdown["score_bonus"] == Decimal("10")
        assert breakdown["result_bonus"] == Decimal("3")
        assert breakdown["confidence_bonus"] == Decimal("2.5")
        assert breakdown["total"] == Decimal("15.5")

    def test_prediction_points_string_representation(self) -> None:
        """✅ 成功用例：字符串表示"""
        points = PredictionPoints(total=Decimal("15.5"))
        assert str(points) == "15.50 分"  # 两位小数格式

        points = PredictionPoints(total=Decimal("0"))
        assert str(points) == "0.00 分"

    def test_prediction_points_edge_cases(self) -> None:
        """✅ 边界用例：极端积分情况"""
        # 大积分
        points = PredictionPoints(total=Decimal("999.99"))
        assert points.total == Decimal("999.99")
        assert str(points) == "999.99 分"

        # 极小积分
        points = PredictionPoints(total=Decimal("0.01"))
        assert points.total == Decimal("0.01")
        assert str(points) == "0.01 分"

        # 零积分各组件
        points = PredictionPoints(
            total=Decimal("5"),
            score_bonus=Decimal("0"),
            result_bonus=Decimal("0"),
            confidence_bonus=Decimal("5"),
        )
        breakdown = points.breakdown
        assert breakdown["score_bonus"] == Decimal("0")
        assert breakdown["result_bonus"] == Decimal("0")


@pytest.mark.unit
class TestPrediction:
    """Prediction领域模型边界条件测试"""

    def test_prediction_initialization_minimal(self) -> None:
        """✅ 成功用例：最小初始化"""
        prediction = Prediction(user_id=1, match_id=100)

        assert prediction.user_id == 1
        assert prediction.match_id == 100
        assert prediction.status == PredictionStatus.PENDING
        assert prediction.score is None
        assert prediction.confidence is None
        assert prediction.points is None
        assert prediction.created_at is not None
        assert prediction.evaluated_at is None
        assert prediction.cancelled_at is None

    def test_prediction_initialization_full(self) -> None:
        """✅ 成功用例：完整初始化"""
        prediction_score = PredictionScore(
            predicted_home=2, predicted_away=1, actual_home=3, actual_away=1
        )
        confidence = ConfidenceScore(Decimal("0.85"))
        points = PredictionPoints(total=Decimal("15"))

        prediction = Prediction(
            id=1,
            user_id=100,
            match_id=200,
            score=prediction_score,
            confidence=confidence,
            status=PredictionStatus.EVALUATED,
            points=points,
            model_version="v1.0",
            created_at=datetime(2023, 6, 15, 10, 0),
            evaluated_at=datetime(2023, 6, 15, 18, 0),
        )

        assert prediction.id == 1
        assert prediction.user_id == 100
        assert prediction.match_id == 200
        assert prediction.status == PredictionStatus.EVALUATED
        assert prediction.points.total == Decimal("15")
        assert prediction.model_version == "v1.0"

    def test_prediction_validation_invalid_user_id(self) -> None:
        """✅ 边界用例：无效用户ID验证"""
        with pytest.raises(DomainError, match="用户ID必须大于0"):
            Prediction(user_id=0, match_id=100)

        with pytest.raises(DomainError, match="用户ID必须大于0"):
            Prediction(user_id=-1, match_id=100)

    def test_prediction_validation_invalid_match_id(self) -> None:
        """✅ 边界用例：无效比赛ID验证"""
        with pytest.raises(DomainError, match="比赛ID必须大于0"):
            Prediction(user_id=1, match_id=0)

        with pytest.raises(DomainError, match="比赛ID必须大于0"):
            Prediction(user_id=1, match_id=-1)

    def test_prediction_make_prediction_method(self) -> None:
        """✅ 成功用例：创建预测方法"""
        prediction = Prediction(user_id=1, match_id=100)

        prediction.make_prediction(
            predicted_home=2, predicted_away=1, confidence=0.75, model_version="v1.0"
        )

        assert prediction.score is not None
        assert prediction.score.predicted_home == 2
        assert prediction.score.predicted_away == 1
        assert prediction.confidence is not None
        assert prediction.confidence.value == Decimal("0.75")
        assert prediction.model_version == "v1.0"

    def test_prediction_make_prediction_invalid_status(self) -> None:
        """✅ 边界用例：无效状态创建预测"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.status = PredictionStatus.EVALUATED

        with pytest.raises(DomainError, match="预测状态为 evaluated，无法修改"):
            prediction.make_prediction(predicted_home=2, predicted_away=1)

        prediction.status = PredictionStatus.CANCELLED
        with pytest.raises(DomainError, match="预测状态为 cancelled，无法修改"):
            prediction.make_prediction(predicted_home=2, predicted_away=1)

    def test_prediction_evaluate_method(self) -> None:
        """✅ 成功用例：评估预测"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(predicted_home=2, predicted_away=1, confidence=0.75)

        original_evaluated_at = prediction.evaluated_at  # 应该是None

        prediction.evaluate(actual_home=3, actual_away=1)

        assert prediction.status == PredictionStatus.EVALUATED
        assert prediction.score.actual_home == 3
        assert prediction.score.actual_away == 1
        assert prediction.score.is_evaluated is True
        assert prediction.points is not None
        assert prediction.evaluated_at is not None
        assert prediction.evaluated_at > prediction.created_at  # 评估时间应该晚于创建时间

    def test_prediction_evaluate_invalid_status(self) -> None:
        """✅ 边界用例：无效状态评估"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(predicted_home=2, predicted_away=1)

        # 设为已评估状态
        prediction.status = PredictionStatus.EVALUATED

        with pytest.raises(DomainError, match="预测状态为 evaluated，无法评估"):
            prediction.evaluate(actual_home=3, actual_away=1)

        # 设为已取消状态
        prediction.status = PredictionStatus.CANCELLED

        with pytest.raises(DomainError, match="预测状态为 cancelled，无法评估"):
            prediction.evaluate(actual_home=3, actual_away=1)

    def test_prediction_evaluate_without_score(self) -> None:
        """✅ 边界用例：无比分评估"""
        prediction = Prediction(user_id=1, match_id=100)

        with pytest.raises(DomainError, match="预测必须包含比分才能评估"):
            prediction.evaluate(actual_home=3, actual_away=1)

    def test_prediction_cancel_method(self) -> None:
        """✅ 成功用例：取消预测"""
        prediction = Prediction(user_id=1, match_id=100)

        prediction.cancel(reason="用户主动取消")

        assert prediction.status == PredictionStatus.CANCELLED
        assert prediction.cancelled_at is not None
        assert prediction.cancellation_reason == "用户主动取消"

    def test_prediction_is_evaluated_property(self) -> None:
        """✅ 成功用例：已评估属性"""
        prediction = Prediction(user_id=1, match_id=100)

        assert prediction.is_evaluated is False

        prediction.status = PredictionStatus.EVALUATED
        assert prediction.is_evaluated is True

        prediction.status = PredictionStatus.CANCELLED
        assert prediction.is_evaluated is False

    def test_prediction_is_successful_property(self) -> None:
        """✅ 成功用例：成功预测属性"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(predicted_home=2, predicted_away=1, confidence=0.75)

        # 未评估的预测
        assert prediction.accuracy_score == 0.0

        # 评估但错误的预测
        prediction.evaluate(actual_home=1, actual_away=2)
        assert prediction.accuracy_score == 0.0  # 完全错误，结果和比分都不对

        # 评估且正确的预测（精确比分）
        prediction2 = Prediction(user_id=2, match_id=101)
        prediction2.make_prediction(predicted_home=2, predicted_away=1, confidence=0.75)
        prediction2.evaluate(actual_home=2, actual_away=1)
        assert prediction2.accuracy_score == 1.0  # 精确预测，满分

    def test_prediction_can_be_modified_property(self) -> None:
        """✅ 成功用例：可修改属性"""
        prediction = Prediction(user_id=1, match_id=100)

        # 待处理状态可以修改
        assert prediction.is_pending is True

        # 已评估状态不能修改
        prediction.status = PredictionStatus.EVALUATED
        assert prediction.is_pending is False

        # 已取消状态不能修改
        prediction.status = PredictionStatus.CANCELLED
        assert prediction.is_pending is False

        # 已过期状态不能修改
        prediction.status = PredictionStatus.EXPIRED
        assert prediction.is_pending is False

    def test_prediction_domain_events(self) -> None:
        """✅ 成功用例：领域事件"""
        prediction = Prediction(user_id=1, match_id=100)

        # 初始状态无事件
        assert len(prediction.get_domain_events()) == 0

        # 创建预测应该触发事件
        prediction.make_prediction(predicted_home=2, predicted_away=1, confidence=0.75)

        events = prediction.get_domain_events()
        assert len(events) > 0

    def test_prediction_edge_cases(self) -> None:
        """✅ 边界用例：边界条件测试"""
        # 最小ID
        prediction = Prediction(user_id=1, match_id=1)
        assert prediction.user_id == 1
        assert prediction.match_id == 1

        # 大ID
        prediction = Prediction(user_id=999999, match_id=999999)
        assert prediction.user_id == 999999
        assert prediction.match_id == 999999

        # 零置信度
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(predicted_home=0, predicted_away=0, confidence=0.0)
        assert prediction.confidence.level == "low"

        # 最高置信度
        prediction = Prediction(user_id=2, match_id=101)
        prediction.make_prediction(predicted_home=2, predicted_away=1, confidence=1.0)
        assert prediction.confidence.level == "high"

    def test_prediction_comprehensive_workflow(self) -> None:
        """✅ 综合用例：完整预测工作流"""
        # 创建预测
        prediction = Prediction(id=1, user_id=100, match_id=200)

        # 验证初始状态
        assert prediction.status == PredictionStatus.PENDING
        assert prediction.is_evaluated is False
        assert prediction.accuracy_score == 0.0
        assert prediction.is_pending is True

        # 创建预测
        prediction.make_prediction(
            predicted_home=2, predicted_away=1, confidence=0.85, model_version="v1.0"
        )

        # 验证预测创建后状态
        assert prediction.score is not None
        assert prediction.score.predicted_home == 2
        assert prediction.score.predicted_away == 1
        assert prediction.confidence is not None
        assert prediction.confidence.level == "high"
        assert prediction.model_version == "v1.0"

        # 评估预测
        prediction.evaluate(actual_home=2, actual_away=1)

        # 验证评估后状态
        assert prediction.status == PredictionStatus.EVALUATED
        assert prediction.is_evaluated is True
        assert prediction.accuracy_score == 1.0  # 精确预测
        assert prediction.is_pending is False  # 已评估状态不能修改
        assert prediction.points is not None
        assert prediction.points.total > 0
        assert prediction.evaluated_at is not None

        # 验证有领域事件产生
        events = prediction.get_domain_events()
        assert len(events) > 0

    def test_prediction_performance_considerations(self) -> None:
        """✅ 性能用例：性能考虑"""
        import time

        # 测试大量Prediction对象创建性能
        start_time = time.perf_counter()

        for i in range(1000):
            prediction = Prediction(user_id=i + 1, match_id=i + 1000)
            prediction.make_prediction(predicted_home=2, predicted_away=1, confidence=0.75)

        end_time = time.perf_counter()

        # 1000个Prediction对象创建和预测应该在1秒内完成
        assert end_time - start_time < 1.0

    def test_prediction_thread_safety_considerations(self) -> None:
        """✅ 并发用例：线程安全考虑"""
        import threading

        results = []
        errors = []

        def create_prediction(prediction_id: int):
            try:
                prediction = Prediction(user_id=prediction_id, match_id=prediction_id + 1000)
                prediction.make_prediction(predicted_home=2, predicted_away=1, confidence=0.75)
                results.append(prediction.user_id)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时创建Prediction对象
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_prediction, args=(i + 1,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        assert len(errors) == 0
        assert len(results) == 10

    def test_prediction_boundary_scores_calculation(self) -> None:
        """✅ 边界用例：边界积分计算"""
        # 完全正确的预测
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(predicted_home=2, predicted_away=1, confidence=0.9)
        prediction.evaluate(actual_home=2, actual_away=1)

        # 应该获得最高积分
        assert prediction.points is not None
        assert prediction.points.total > Decimal("0")

        # 完全错误的预测
        prediction2 = Prediction(user_id=2, match_id=101)
        prediction2.make_prediction(predicted_home=2, predicted_away=1, confidence=0.9)
        prediction2.evaluate(actual_home=0, actual_away=3)

        # 应该获得较低积分或零积分
        assert prediction2.points is not None
        assert prediction2.points.total >= Decimal("0")

    def test_prediction_zero_scores_edge_case(self) -> None:
        """✅ 边界用例：零比分预测"""
        prediction = Prediction(user_id=1, match_id=100)
        prediction.make_prediction(predicted_home=0, predicted_away=0, confidence=0.8)
        prediction.evaluate(actual_home=0, actual_away=0)

        # 0-0预测正确
        assert prediction.accuracy_score == 1.0
        assert prediction.points is not None
        assert prediction.points.total > Decimal("0")

    def test_prediction_model_version_handling(self) -> None:
        """✅ 成功用例：模型版本处理"""
        prediction = Prediction(user_id=1, match_id=100)

        # 不带模型版本
        prediction.make_prediction(predicted_home=2, predicted_away=1, confidence=0.75)
        assert prediction.model_version is None

        # 带模型版本
        prediction2 = Prediction(user_id=2, match_id=101)
        prediction2.make_prediction(
            predicted_home=1, predicted_away=1, confidence=0.6, model_version="v2.1.0"
        )
        assert prediction2.model_version == "v2.1.0"
