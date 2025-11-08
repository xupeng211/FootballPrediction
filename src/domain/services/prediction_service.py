from datetime import datetime
from decimal import Decimal
from typing import Any

from src.domain.events.prediction_events import (
    PredictionCancelledEvent,
    PredictionCreatedEvent,
    PredictionEvaluatedEvent,
    PredictionExpiredEvent,
    PredictionPointsAdjustedEvent,
    PredictionUpdatedEvent,
)
from src.domain.models.match import Match, MatchStatus
from src.domain.models.prediction import Prediction, PredictionPoints, PredictionStatus

"""
预测领域服务
Prediction Domain Service

处理预测相关的复杂业务逻辑.
Handles complex business logic related to predictions.
"""


class PredictionDomainService:
    """类文档字符串"""

    pass  # 添加pass语句
    """预测领域服务"""

    def __init__(self):
        """函数文档字符串"""
        # 添加pass语句
        self._events: list[Any] = []

    def create_prediction(
        self,
        user_id: int,
        match: Match,
        predicted_home: int,
        predicted_away: int,
        confidence: float | None = None,
        notes: str | None = None,
    ) -> Prediction:
        """创建预测"""
        # 验证比赛状态
        if match.status != MatchStatus.SCHEDULED:
            raise ValueError("只能对未开始的比赛进行预测")

        # 验证预测时间
        if datetime.utcnow() >= match.match_date:
            raise ValueError("预测必须在比赛开始前提交")

        # 验证比分
        if predicted_home < 0 or predicted_away < 0:
            raise ValueError("预测比分不能为负数")

        # 验证信心度
        if confidence is not None:
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("信心度必须在0-1之间")

        if match.id is None:
            raise ValueError("比赛ID不能为空")

        _prediction = Prediction(
            id=1,  # 在实际应用中，ID应该由数据库生成
            user_id=user_id,
            match_id=match.id,
        )
        # 创建预测
        _prediction.make_prediction(
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence,
        )
        # Note: notes 字段在当前模型中不存在,需要时可以扩展模型

        # 记录领域事件
        if _prediction.id is None:
            raise ValueError("预测ID不能为空")

        event = PredictionCreatedEvent(
            prediction_id=_prediction.id,
            user_id=user_id,
            match_id=match.id,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence,
            prediction=_prediction,
        )
        self._events.append(event)

        return _prediction

    def update_prediction(
        self,
        prediction: Prediction,
        new_predicted_home: int | None = None,
        new_predicted_away: int | None = None,
        confidence: float | None = None,
        new_confidence: float | None = None,
        new_notes: str | None = None,
        notes: str | None = None,  # 兼容性参数
    ) -> Prediction:
        """更新预测"""
        # 验证预测状态
        if prediction.status != PredictionStatus.PENDING:
            raise ValueError("只能更新待处理的预测")

        # 记录旧值
        old_home = prediction.score.predicted_home if prediction.score else None
        old_away = prediction.score.predicted_away if prediction.score else None

        # 确定新的预测值
        final_home = new_predicted_home if new_predicted_home is not None else old_home
        final_away = new_predicted_away if new_predicted_away is not None else old_away

        # 验证比分（如果提供）
        if final_home is not None and final_home < 0:
            raise ValueError("预测比分不能为负数")
        if final_away is not None and final_away < 0:
            raise ValueError("预测比分不能为负数")

        # 使用confidence或new_confidence（向后兼容）
        final_confidence = confidence or new_confidence

        # 如果没有提供任何更新参数，只更新confidence
        if final_home is None or final_away is None:
            # 只更新confidence
            if final_confidence is not None and prediction.score:
                prediction.make_prediction(
                    final_home or 0, final_away or 0, final_confidence
                )
            return prediction

        # 更新预测
        prediction.make_prediction(final_home, final_away, final_confidence)

        # 记录领域事件
        if prediction.id is None:
            raise ValueError("预测ID不能为空")

        event = PredictionUpdatedEvent(
            prediction_id=prediction.id,
            old_predicted_home=old_home or 0,
            old_predicted_away=old_away or 0,
            new_predicted_home=final_home,
            new_predicted_away=final_away,
        )
        self._events.append(event)

        return prediction

    def evaluate_prediction(
        self,
        prediction: Prediction,
        actual_home: int,
        actual_away: int,
        scoring_rules: dict[str, Any] | None = None,
    ) -> Prediction:
        """评估预测"""
        if prediction.status != PredictionStatus.PENDING:
            raise ValueError("只能评估待处理的预测")

        # 评估预测
        prediction.evaluate(actual_home, actual_away, scoring_rules)

        # 记录领域事件
        if prediction.id is None:
            raise ValueError("预测ID不能为空")

        # Get points earned as int
        points_earned = None
        if prediction.points:
            if isinstance(prediction.points.total, Decimal):
                points_earned = int(prediction.points.total)
            else:
                points_earned = prediction.points.total

        event = PredictionEvaluatedEvent(
            prediction_id=prediction.id,
            actual_home=actual_home,
            actual_away=actual_away,
            is_correct=(
                prediction.score.is_correct_result if prediction.score else False
            ),
            points_earned=points_earned,
        )
        self._events.append(event)

        return prediction

    def cancel_prediction(
        self, prediction: Prediction, reason: str = "用户取消"
    ) -> Prediction:
        """取消预测"""
        if prediction.status != PredictionStatus.PENDING:
            raise ValueError("只能取消待处理的预测")

        prediction.cancel()

        # 记录领域事件
        if prediction.id is None:
            raise ValueError("预测ID不能为空")

        event = PredictionCancelledEvent(prediction_id=prediction.id, reason=reason)
        self._events.append(event)

        return prediction

    def expire_prediction(self, prediction: Prediction) -> None:
        """使预测过期"""
        if prediction.status != PredictionStatus.PENDING:
            raise ValueError("只能使待处理的预测过期")

        prediction.status = PredictionStatus.EXPIRED
        prediction.cancelled_at = datetime.utcnow()

        # 记录领域事件
        if prediction.id is None:
            raise ValueError("预测ID不能为空")

        event = PredictionExpiredEvent(
            prediction_id=prediction.id,
            match_id=prediction.match_id,
            expired_at=datetime.utcnow().isoformat(),
        )
        self._events.append(event)

    def adjust_prediction_points(
        self, prediction: Prediction, new_points: int, adjustment_reason: str
    ) -> None:
        """调整预测积分"""
        if prediction.status != PredictionStatus.EVALUATED:
            raise ValueError("只能调整已评估的预测积分")

        old_points = int(float(prediction.points.total)) if prediction.points else 0

        # 创建新的积分对象
        from decimal import Decimal

        prediction.points = PredictionPoints(
            base_points=Decimal(str(new_points)), total=Decimal(str(new_points))
        )

        # 记录领域事件
        if prediction.id is None:
            raise ValueError("预测ID不能为空")

        event = PredictionPointsAdjustedEvent(
            prediction_id=prediction.id,
            user_id=prediction.user_id,
            old_points=old_points,
            new_points=new_points,
            adjustment_reason=adjustment_reason,
        )
        self._events.append(event)

    def calculate_prediction_confidence(
        self,
        user_history: dict[str, Any],
        match_importance: float,
        team_form_diff: float | None = None,
    ) -> float:
        """计算预测信心度"""
        base_confidence = 0.5

        # 根据用户历史准确率调整
        if "accuracy_rate" in user_history:
            accuracy_rate = user_history["accuracy_rate"]
            base_confidence += (accuracy_rate - 0.5) * 0.3

        # 根据比赛重要性调整
        base_confidence += (match_importance - 0.5) * 0.2

        # 根据球队状态差异调整
        if team_form_diff:
            base_confidence += team_form_diff * 0.1

        # 确保在0-1范围内
        return max(0.0, min(1.0, base_confidence))

    def validate_prediction_rules(
        self,
        prediction: Prediction,
        user_predictions_today: int,
        max_predictions_per_day: int = 10,
    ) -> list[str]:
        """验证预测规则"""
        errors = []

        # 检查每日预测限制
        if user_predictions_today >= max_predictions_per_day:
            errors.append(f"每日预测次数不能超过{max_predictions_per_day}次")

        # 检查预测内容
        if prediction.score:
            if (
                prediction.score.predicted_home < 0
                or prediction.score.predicted_away < 0
            ):
                errors.append("预测比分不能为负数")

        # 检查信心度
        if prediction.confidence:
            if not 0.0 <= float(prediction.confidence.value) <= 1.0:
                errors.append("信心度必须在0-1之间")

        # Note: notes 字段在当前模型中不存在,需要时可以扩展模型
        # if prediction.notes and len(prediction.notes) > 500:
        #     errors.append("备注不能超过500个字符")

        return errors

    def get_domain_events(self) -> list[Any]:
        """获取领域事件"""
        return self._events.copy()

    def clear_domain_events(self) -> None:
        """清除领域事件"""
        self._events.clear()

    def clear_events(self) -> None:
        """清除事件（别名方法）"""
        self.clear_domain_events()

    def get_events(self) -> list[Any]:
        """获取事件（别名方法）"""
        return self.get_domain_events()
