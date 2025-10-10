"""
预测领域服务
Prediction Domain Service

处理预测相关的复杂业务逻辑。
Handles complex business logic related to predictions.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from ..models.prediction import (
    Prediction,
    PredictionStatus,
    ConfidenceScore,
    PredictionScore,
    PredictionPoints,
)
from ..models.match import Match, MatchStatus
from ..events.prediction_events import (
    PredictionCreatedEvent,
    PredictionUpdatedEvent,
    PredictionEvaluatedEvent,
    PredictionCancelledEvent,
    PredictionExpiredEvent,
    PredictionPointsAdjustedEvent,
)


class PredictionDomainService:
    """预测领域服务"""

    def __init__(self):
        self._events: List[Any] = []

    def create_prediction(
        self,
        user_id: int,
        match: Match,
        predicted_home: int,
        predicted_away: int,
        confidence: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Prediction:
        """创建预测"""
        # 验证比赛状态
        if match.status != MatchStatus.SCHEDULED:
            raise ValueError("只能对未开始的比赛进行预测")

        # 验证预测时间
        if datetime.utcnow() >= match.match_time:  # type: ignore
            raise ValueError("预测必须在比赛开始前提交")

        # 验证比分
        if predicted_home < 0 or predicted_away < 0:
            raise ValueError("预测比分不能为负数")

        # 验证信心度
        if confidence is not None:
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("信心度必须在0-1之间")
            confidence_score = ConfidenceScore(confidence)  # type: ignore
        else:
            confidence_score = None

        prediction = Prediction(  # type: ignore
            user_id=user_id,
            match_id=match.id,  # type: ignore
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence_score,
            notes=notes,
        )

        # 记录领域事件
        event = PredictionCreatedEvent(
            prediction_id=prediction.id,  # type: ignore
            user_id=user_id,
            match_id=match.id,  # type: ignore
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence,
        )
        self._events.append(event)

        return prediction

    def update_prediction(
        self,
        prediction: Prediction,
        new_predicted_home: int,
        new_predicted_away: int,
        new_confidence: Optional[float] = None,
        new_notes: Optional[str] = None,
    ) -> None:
        """更新预测"""
        # 验证预测状态
        if prediction.status != PredictionStatus.PENDING:
            raise ValueError("只能更新待处理的预测")

        # 验证比分
        if new_predicted_home < 0 or new_predicted_away < 0:
            raise ValueError("预测比分不能为负数")

        # 记录旧值
        old_home = prediction.predicted_home  # type: ignore
        old_away = prediction.predicted_away  # type: ignore

        # 更新预测
        prediction.update_prediction(  # type: ignore
            new_predicted_home, new_predicted_away, new_confidence, new_notes
        )

        # 记录领域事件
        event = PredictionUpdatedEvent(
            prediction_id=prediction.id,  # type: ignore
            old_predicted_home=old_home,
            old_predicted_away=old_away,
            new_predicted_home=new_predicted_home,
            new_predicted_away=new_predicted_away,
        )
        self._events.append(event)

    def evaluate_prediction(
        self,
        prediction: Prediction,
        actual_home: int,
        actual_away: int,
        scoring_rules: Optional[Dict[str, Any]] = None,
    ) -> None:
        """评估预测"""
        if prediction.status != PredictionStatus.PENDING:
            raise ValueError("只能评估待处理的预测")

        # 评估预测
        prediction.evaluate(actual_home, actual_away, scoring_rules)

        # 记录领域事件
        event = PredictionEvaluatedEvent(
            prediction_id=prediction.id,  # type: ignore
            actual_home=actual_home,
            actual_away=actual_away,
            is_correct=prediction.is_correct,  # type: ignore
            points_earned=prediction.points.total_points if prediction.points else None,  # type: ignore
            accuracy_score=prediction.accuracy_score.value  # type: ignore
            if prediction.accuracy_score
            else None,
        )
        self._events.append(event)

    def cancel_prediction(
        self, prediction: Prediction, reason: str, cancelled_by: Optional[int] = None
    ) -> None:
        """取消预测"""
        if prediction.status != PredictionStatus.PENDING:
            raise ValueError("只能取消待处理的预测")

        prediction.cancel()

        # 记录领域事件
        event = PredictionCancelledEvent(
            prediction_id=prediction.id,
            reason=reason,
            cancelled_by=cancelled_by,  # type: ignore
        )
        self._events.append(event)

    def expire_prediction(self, prediction: Prediction) -> None:
        """使预测过期"""
        if prediction.status != PredictionStatus.PENDING:
            raise ValueError("只能使待处理的预测过期")

        prediction.expire()  # type: ignore

        # 记录领域事件
        event = PredictionExpiredEvent(
            prediction_id=prediction.id,  # type: ignore
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

        old_points = prediction.points.total_points if prediction.points else 0  # type: ignore

        # 创建新的积分对象
        prediction.points = PredictionPoints(  # type: ignore
            exact_score=new_points,
            outcome_diff=0,
            goals_diff=0,
            total_points=new_points,
        )

        # 记录领域事件
        event = PredictionPointsAdjustedEvent(
            prediction_id=prediction.id,  # type: ignore
            user_id=prediction.user_id,
            old_points=old_points,
            new_points=new_points,
            adjustment_reason=adjustment_reason,
        )
        self._events.append(event)

    def calculate_prediction_confidence(
        self,
        user_history: Dict[str, Any],
        match重要性: float,
        team_form_diff: Optional[float] = None,
    ) -> float:
        """计算预测信心度"""
        base_confidence = 0.5

        # 根据用户历史准确率调整
        if "accuracy_rate" in user_history:
            accuracy_rate = user_history["accuracy_rate"]
            base_confidence += (accuracy_rate - 0.5) * 0.3

        # 根据比赛重要性调整
        base_confidence += (match重要性 - 0.5) * 0.2

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
    ) -> List[str]:
        """验证预测规则"""
        errors = []

        # 检查每日预测限制
        if user_predictions_today >= max_predictions_per_day:
            errors.append(f"每日预测次数不能超过{max_predictions_per_day}次")

        # 检查预测内容
        if prediction.predicted_home < 0 or prediction.predicted_away < 0:  # type: ignore
            errors.append("预测比分不能为负数")

        # 检查信心度
        if prediction.confidence and not 0.0 <= prediction.confidence.value <= 1.0:
            errors.append("信心度必须在0-1之间")

        # 检查备注长度
        if prediction.notes and len(prediction.notes) > 500:  # type: ignore
            errors.append("备注不能超过500个字符")

        return errors

    def get_domain_events(self) -> List[Any]:
        """获取领域事件"""
        return self._events.copy()

    def clear_domain_events(self) -> None:
        """清除领域事件"""
        self._events.clear()
