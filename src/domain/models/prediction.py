"""
预测领域模型
Prediction Domain Model

封装预测相关的业务逻辑和不变性约束.
Encapsulates prediction-related business logic and invariants.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from src.core.exceptions import DomainError


class PredictionStatus(Enum):
    """预测状态"""

    PENDING = "pending"  # 待处理
    EVALUATED = "evaluated"  # 已评估
    CANCELLED = "cancelled"  # 已取消
    EXPIRED = "expired"  # 已过期


@dataclass
class ConfidenceScore:
    """类文档字符串"""

    pass  # 添加pass语句
    """置信度值对象"""

    value: Decimal

    def __post_init__(self):
        """验证预测数据"""
        if self.value < 0 or self.value > 1:
            raise DomainError("置信度必须在 0 到 1 之间")
        # 转换为两位小数
        self.value = self.value.quantize(Decimal("0.01"))

    @property
    def level(self) -> str:
        """置信度等级"""
        if self.value >= Decimal("0.8"):
            return "high"
        elif self.value >= Decimal("0.6"):
            return "medium"
        else:
            return "low"

    def __str__(self) -> str:
        return f"{self.value:.2f} ({self.level})"


@dataclass
class PredictionScore:
    """类文档字符串"""

    pass  # 添加pass语句
    """预测比分值对象"""

    predicted_home: int
    predicted_away: int
    actual_home: int | None = None
    actual_away: int | None = None

    def __post_init__(self):
        """函数文档字符串"""
        # 添加pass语句
        """验证比分"""
        if self.predicted_home < 0 or self.predicted_away < 0:
            raise DomainError("预测比分不能为负数")

        if self.actual_home is not None and self.actual_home < 0:
            raise DomainError("实际主队比分不能为负数")
        if self.actual_away is not None and self.actual_away < 0:
            raise DomainError("实际客队比分不能为负数")

    @property
    def is_evaluated(self) -> bool:
        """是否已评估"""
        return self.actual_home is not None and self.actual_away is not None

    @property
    def is_correct_score(self) -> bool:
        """是否预测正确比分"""
        if not self.is_evaluated:
            return False
        return (
            self.predicted_home == self.actual_home
            and self.predicted_away == self.actual_away
        )

    @property
    def is_correct_result(self) -> bool:
        """是否预测正确结果（胜平负）"""
        if not self.is_evaluated:
            return False

        predicted_diff = self.predicted_home - self.predicted_away
        actual_diff = self.actual_home - self.actual_away

        if predicted_diff > 0 and actual_diff > 0:
            return True  # 主队获胜
        if predicted_diff < 0 and actual_diff < 0:
            return True  # 客队获胜
        if predicted_diff == 0 and actual_diff == 0:
            return True  # 平局

        return False

    @property
    def goal_difference_error(self) -> int:
        """净胜球误差"""
        if not self.is_evaluated:
            return 0
        predicted_diff = self.predicted_home - self.predicted_away
        actual_diff = self.actual_home - self.actual_away
        return abs(predicted_diff - actual_diff)

    def __str__(self) -> str:
        if self.is_evaluated:
            return f"{self.predicted_home}-{self.predicted_away} (实际: {self.actual_home}-{self.actual_away})"
        return f"{self.predicted_home}-{self.predicted_away}"


@dataclass
class PredictionPoints:
    """类文档字符串"""

    pass  # 添加pass语句
    """预测积分值对象"""

    total: Decimal = Decimal("0")
    score_bonus: Decimal = Decimal("0")  # 精确比分奖励
    result_bonus: Decimal = Decimal("0")  # 结果正确奖励
    confidence_bonus: Decimal = Decimal("0")  # 置信度奖励

    def __post_init__(self):
        """函数文档字符串"""
        # 添加pass语句
        """四舍五入到两位小数"""
        self.total = self.total.quantize(Decimal("0.01"))
        self.score_bonus = self.score_bonus.quantize(Decimal("0.01"))
        self.result_bonus = self.result_bonus.quantize(Decimal("0.01"))
        self.confidence_bonus = self.confidence_bonus.quantize(Decimal("0.01"))

    @property
    def breakdown(self) -> dict[str, Decimal]:
        """积分明细"""
        return {
            "score_bonus": self.score_bonus,
            "result_bonus": self.result_bonus,
            "confidence_bonus": self.confidence_bonus,
            "total": self.total,
        }

    def __str__(self) -> str:
        return f"{self.total} 分"


@dataclass
class Prediction:
    """类文档字符串"""

    pass  # 添加pass语句
    """
    预测领域模型

    封装预测的核心业务逻辑和不变性约束.
    """

    id: int | None = None
    user_id: int = 0
    match_id: int = 0
    score: PredictionScore | None = None
    confidence: ConfidenceScore | None = None
    status: PredictionStatus = PredictionStatus.PENDING
    model_version: str | None = None
    points: PredictionPoints | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    evaluated_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None

    # 领域事件
    _domain_events: list[Any] = field(default_factory=list, init=False)

    def __post_init__(self):
        """函数文档字符串"""
        # 添加pass语句
        """初始化后的验证"""
        if self.user_id <= 0:
            raise DomainError("用户ID必须大于0")
        if self.match_id <= 0:
            raise DomainError("比赛ID必须大于0")

    # ========================================
    # 业务方法
    # ========================================

    def make_prediction(
        self,
        predicted_home: int,
        predicted_away: int,
        confidence: float | None = None,
        model_version: str | None = None,
    ) -> None:
        """创建预测"""
        if self.status != PredictionStatus.PENDING:
            raise DomainError(f"预测状态为 {self.status.value},无法修改")

        self.score = PredictionScore(
            predicted_home=predicted_home, predicted_away=predicted_away
        )

        if confidence is not None:
            self.confidence = ConfidenceScore(Decimal(str(confidence)))

        if model_version:
            self.model_version = model_version

        # 发布领域事件
        from src.domain.events import PredictionCreatedEvent

        self._add_domain_event(
            PredictionCreatedEvent(
                prediction_id=self.id or 0,
                user_id=self.user_id,
                match_id=self.match_id,
                predicted_home=self.score.predicted_home,
                predicted_away=self.score.predicted_away,
                confidence=float(self.confidence.value) if self.confidence else None,
            )
        )

    def evaluate(
        self,
        actual_home: int,
        actual_away: int,
        scoring_rules: dict[str, Decimal] | None = None,
    ) -> None:
        """评估预测结果"""
        if self.status != PredictionStatus.PENDING:
            raise DomainError(f"预测状态为 {self.status.value},无法评估")

        if not self.score:
            raise DomainError("预测必须包含比分才能评估")

        # 更新实际比分
        self.score.actual_home = actual_home
        self.score.actual_away = actual_away
        self.status = PredictionStatus.EVALUATED
        self.evaluated_at = datetime.utcnow()

        # 计算积分
        self.points = self._calculate_points(
            scoring_rules or self._default_scoring_rules()
        )

        # 发布领域事件
        from src.domain.events import PredictionEvaluatedEvent

        self._add_domain_event(
            PredictionEvaluatedEvent(
                prediction_id=self.id or 0,
                actual_home=actual_home,
                actual_away=actual_away,
                is_correct=self.score.is_correct_score,
                points_earned=(
                    int(self.points.total) if self.points is not None else None
                ),
                accuracy_score=self.accuracy_score,
            )
        )

    def cancel(self, reason: str | None = None) -> None:
        """取消预测"""
        if self.status in [PredictionStatus.EVALUATED, PredictionStatus.CANCELLED]:
            raise DomainError(f"预测状态为 {self.status.value},无法取消")

        self.status = PredictionStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.cancellation_reason = reason

    def mark_expired(self) -> None:
        """标记为过期"""
        if self.status != PredictionStatus.PENDING:
            raise DomainError(f"预测状态为 {self.status.value},无法标记为过期")

        self.status = PredictionStatus.EXPIRED

    @staticmethod
    def _default_scoring_rules() -> dict[str, Decimal]:
        """默认积分规则"""
        return {
            "exact_score": Decimal("10"),
            # 精确比分
            "correct_result": Decimal("3"),
            # 正确结果
            "confidence_multiplier": Decimal("1"),
            # 置信度倍数
        }

    def _calculate_points(self, rules: dict[str, Decimal]) -> PredictionPoints:
        """计算积分"""
        points = PredictionPoints()

        # 精确比分奖励
        if self.score.is_correct_score:
            points.score_bonus = rules["exact_score"]
        # 结果正确奖励
        elif self.score.is_correct_result:
            points.result_bonus = rules["correct_result"]

        # 置信度奖励
        if self.confidence:
            base_points = points.score_bonus + points.result_bonus
            confidence_multiplier = (
                Decimal("1")
                + (self.confidence.value - Decimal("0.5"))
                * rules["confidence_multiplier"]
            )
            confidence_bonus = base_points * confidence_multiplier - base_points
            points.confidence_bonus = confidence_bonus.quantize(Decimal("0.01"))

        # 计算总积分
        points.total = (
            points.score_bonus + points.result_bonus + points.confidence_bonus
        )
        points.total = points.total.quantize(Decimal("0.01"))

        return points

    # ========================================
    # 查询方法
    # ========================================

    @property
    def is_pending(self) -> bool:
        """是否待处理"""
        return self.status == PredictionStatus.PENDING

    @property
    def is_evaluated(self) -> bool:
        """是否已评估"""
        return self.status == PredictionStatus.EVALUATED

    @property
    def is_cancelled(self) -> bool:
        """是否已取消"""
        return self.status == PredictionStatus.CANCELLED

    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        return self.status == PredictionStatus.EXPIRED

    @property
    def accuracy_score(self) -> float:
        """准确度分数 (0-1)"""
        if not self.is_evaluated or not self.score:
            return 0.0

        score_accuracy = 1.0 if self.score.is_correct_score else 0.0
        result_accuracy = 1.0 if self.score.is_correct_result else 0.0

        # 加权平均
        return score_accuracy * 0.7 + result_accuracy * 0.3

    def get_prediction_summary(self) -> dict[str, Any]:
        """获取预测摘要"""
        if not self.score:
            return {"status": "no_prediction"}

        return {
            "predicted": f"{self.score.predicted_home}-{self.score.predicted_away}",
            "actual": (
                f"{self.score.actual_home}-{self.score.actual_away}"
                if self.score.is_evaluated
                else None
            ),
            "confidence": str(self.confidence) if self.confidence else None,
            "points": float(self.points.total) if self.points else None,
            "is_correct_score": (
                self.score.is_correct_score if self.score.is_evaluated else None
            ),
            "is_correct_result": (
                self.score.is_correct_result if self.score.is_evaluated else None
            ),
            "accuracy": self.accuracy_score,
        }

    # ========================================
    # 领域事件管理
    # ========================================

    def _add_domain_event(self, event: Any) -> None:
        """添加领域事件"""
        self._domain_events.append(event)

    def get_domain_events(self) -> list[Any]:
        """获取领域事件"""
        return self._domain_events.copy()

    def clear_domain_events(self) -> None:
        """清除领域事件"""
        self._domain_events.clear()

    # ========================================
    # 序列化方法
    # ========================================

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "match_id": self.match_id,
            "score": (
                {
                    "predicted_home": self.score.predicted_home,
                    "predicted_away": self.score.predicted_away,
                    "actual_home": self.score.actual_home,
                    "actual_away": self.score.actual_away,
                }
                if self.score
                else None
            ),
            "confidence": float(self.confidence.value) if self.confidence else None,
            "status": self.status.value,
            "model_version": self.model_version,
            "points": (
                {
                    "total": float(self.points.total),
                    "breakdown": {
                        k: float(v) for k, v in self.points.breakdown.items()
                    },
                }
                if self.points
                else None
            ),
            "created_at": self.created_at.isoformat(),
            "evaluated_at": (
                self.evaluated_at.isoformat() if self.evaluated_at else None
            ),
            "cancelled_at": (
                self.cancelled_at.isoformat() if self.cancelled_at else None
            ),
            "cancellation_reason": self.cancellation_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Prediction":
        """从字典创建实例"""
        score_data = data.pop("score", None)
        score = PredictionScore(**score_data) if score_data else None

        confidence_data = data.pop("confidence", None)
        confidence = (
            ConfidenceScore(Decimal(str(confidence_data))) if confidence_data else None
        )

        points_data = data.pop("points", None)
        points = (
            PredictionPoints(
                total=Decimal(str(points_data["total"])),
                score_bonus=Decimal(str(points_data["breakdown"]["score_bonus"])),
                result_bonus=Decimal(str(points_data["breakdown"]["result_bonus"])),
                confidence_bonus=Decimal(
                    str(points_data["breakdown"]["confidence_bonus"])
                ),
            )
            if points_data
            else None
        )

        # 处理日期
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("evaluated_at"):
            data["evaluated_at"] = datetime.fromisoformat(data["evaluated_at"])
        if data.get("cancelled_at"):
            data["cancelled_at"] = datetime.fromisoformat(data["cancelled_at"])

        # 处理状态枚举
        if data.get("status"):
            data["status"] = PredictionStatus(data["status"])

        return cls(score=score, confidence=confidence, points=points, **data)

    def __str__(self) -> str:
        score_str = str(self.score) if self.score else "未预测"
        points_str = f" - {self.points}" if self.points else ""
        return f"预测: {score_str}{points_str} ({self.status.value})"
