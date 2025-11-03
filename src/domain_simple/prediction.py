"""
预测领域模型
"""

from datetime import datetime
from enum import Enum
from typing import Any


class PredictionType(Enum):
    """预测类型枚举"""

    MATCH_RESULT = "match_result"  # 比赛结果
    OVER_UNDER = "over_under"  # 大小球
    BTTS = "btts"  # 双方进球
    CORRECT_SCORE = "correct_score"  # 正确比分
    HALF_TIME = "half_time"  # 半场结果


class PredictionConfidence(Enum):
    """预测置信度"""

    LOW = 0.3  # 低
    MEDIUM = 0.6  # 中
    HIGH = 0.8  # 高
    VERY_HIGH = 0.95  # 极高


class Prediction:
    """类文档字符串"""

    pass  # 添加pass语句
    """预测领域模型"""

    def __init__(
        self,
        id: int | None = None,
        match_id: int = 0,
        user_id: int = 0,
        prediction_type: PredictionType = PredictionType.MATCH_RESULT,
        predicted_value: str = "",
        confidence: float = 0.5,
        odds: float | None = None,
        stake: float = 1.0,
    ):
        self.id = id
        self.match_id = match_id
        self.user_id = user_id
        self.prediction_type = prediction_type
        self.predicted_value = predicted_value
        self.confidence = max(0, min(1, confidence))  # 确保在0-1之间
        self.odds = odds
        self.stake = stake

        # 状态
        self.is_settled = False
        self.is_correct = False
        self.actual_value = None
        self.profit_loss = 0.0
        self.return_amount = 0.0

        # 时间戳
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.settled_at: datetime | None = None

        # 附加信息
        self.reasoning: str = ""
        self.analysis_data: dict[str, Any] = {}

        # 兼容性属性
        self.predicted_home: int | None = None
        self.predicted_away: int | None = None

        # 如果 predicted_value 包含比分,解析它
        if ":" in predicted_value:
            try:
                home, away = predicted_value.split(":")
                self.predicted_home = int(home.strip())
                self.predicted_away = int(away.strip())
            except (ValueError, AttributeError):
                pass

    def settle(self, actual_value: str) -> None:
        """结算预测"""
        if self.is_settled:
            return None
        self.actual_value = actual_value
        self.is_settled = True
        self.settled_at = datetime.now()

        # 判断预测是否正确
        self.is_correct = self._check_correctness(actual_value)

        # 计算盈亏
        if self.odds and self.is_correct:
            self.return_amount = self.stake * self.odds
            self.profit_loss = self.return_amount - self.stake
        else:
            self.return_amount = 0.0
            self.profit_loss = -self.stake

        self.updated_at = datetime.now()

    def _check_correctness(self, actual_value: str) -> bool:
        """检查预测是否正确"""
        if self.prediction_type == PredictionType.MATCH_RESULT:
            # 直接比较比赛结果
            return self.predicted_value.upper() == actual_value.upper()
        elif self.prediction_type == PredictionType.OVER_UNDER:
            # 大小球预测（例如 "Over 2.5" vs "3"）
            try:
                predicted_parts = self.predicted_value.split()
                if len(predicted_parts) >= 2:
                    threshold = float(predicted_parts[1])
                    actual_goals = float(actual_value)
                    if predicted_parts[0].upper() == "OVER":
                        return actual_goals > threshold
                    else:  # UNDER
                        return actual_goals < threshold
            except ValueError:
                pass
        elif self.prediction_type == PredictionType.BTTS:
            # 双方进球预测
            return self.predicted_value.upper() == actual_value.upper()
        elif self.prediction_type == PredictionType.CORRECT_SCORE:
            # 正确比分预测
            return self.predicted_value == actual_value

        return False

    def get_confidence_level(self) -> PredictionConfidence:
        """获取置信度等级"""
        if self.confidence >= PredictionConfidence.VERY_HIGH.value:
            return PredictionConfidence.VERY_HIGH
        elif self.confidence >= PredictionConfidence.HIGH.value:
            return PredictionConfidence.HIGH
        elif self.confidence >= PredictionConfidence.MEDIUM.value:
            return PredictionConfidence.MEDIUM
        else:
            return PredictionConfidence.LOW

    def is_value_bet(self, threshold: float = 1.0) -> bool:
        """判断是否为价值投注"""
        if not self.odds or self.odds <= 1:
            return False

        # 简单的价值计算:预测概率 * 赔率 > 1 + 阈值
        expected_value = self.confidence * self.odds
        return expected_value > (1 + threshold)

    def get_expected_value(self) -> float:
        """获取期望值"""
        if not self.odds:
            return -self.stake

        win_ev = self.confidence * (self.odds - 1) * self.stake
        lose_ev = (1 - self.confidence) * (-self.stake)
        return win_ev + lose_ev

    def add_reasoning(self, reasoning: str) -> None:
        """添加预测理由"""
        self.reasoning = reasoning
        self.updated_at = datetime.now()

    def add_analysis_data(self, key: str, value: Any) -> None:
        """添加分析数据"""
        self.analysis_data[key] = value
        self.updated_at = datetime.now()

    def get_roi(self) -> float:
        """获取投资回报率"""
        if self.stake == 0:
            return 0.0
        return (self.profit_loss / self.stake) * 100

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "match_id": self.match_id,
            "user_id": self.user_id,
            "prediction_type": self.prediction_type.value,
            "predicted_value": self.predicted_value,
            "confidence": self.confidence,
            "confidence_level": self.get_confidence_level().value,
            "odds": self.odds,
            "stake": self.stake,
            "is_settled": self.is_settled,
            "is_correct": self.is_correct,
            "actual_value": self.actual_value,
            "profit_loss": self.profit_loss,
            "return_amount": self.return_amount,
            "roi": self.get_roi(),
            "is_value_bet": self.is_value_bet(),
            "expected_value": self.get_expected_value(),
            "reasoning": self.reasoning,
            "analysis_data": self.analysis_data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Prediction":
        """从字典创建实例"""
        _prediction = cls(
            id=data.get("id"),
            match_id=data.get("match_id", 0),
            user_id=data.get("user_id", 0),
            prediction_type=PredictionType(data.get("prediction_type", "match_result")),
            predicted_value=data.get("predicted_value", ""),
            confidence=data.get("confidence", 0.5),
            odds=data.get("odds"),
            stake=data.get("stake", 1.0),
        )

        # 设置状态
        _prediction.is_settled = data.get("is_settled", False)
        _prediction.is_correct = data.get("is_correct", False)
        _prediction.actual_value = data.get("actual_value")
        _prediction.profit_loss = data.get("profit_loss", 0.0)
        _prediction.return_amount = data.get("return_amount", 0.0)

        # 设置附加信息
        _prediction.reasoning = data.get("reasoning", "")
        _prediction.analysis_data = data.get("analysis_data", {})

        # 设置时间戳
        if data.get("created_at"):
            _prediction.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            _prediction.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("settled_at"):
            _prediction.settled_at = datetime.fromisoformat(data["settled_at"])

        return _prediction

    def __str__(self) -> str:
        return f"Prediction({self.prediction_type.value}: {self.predicted_value} @ {self.odds})"

    def __repr__(self) -> str:
        return f"<Prediction(id={self.id}, match_id={self.match_id}, confidence={self.confidence})>"
