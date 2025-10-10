"""
预测领域模型

封装预测相关的业务逻辑和规则。
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from .match import Match, MatchStatus, MatchResult
from .team import Team


class PredictionType(Enum):
    """预测类型枚举"""

    MATCH_RESULT = "match_result"  # 比赛结果
    OVER_UNDER = "over_under"  # 大小球
    BOTH_TEAMS_SCORE = "both_teams_score"  # 双方进球
    CORRECT_SCORE = "correct_score"  # 精确比分
    FIRST_GOAL_SCORER = "first_goal_scorer"  # 首个进球者
    HANDICAP = "handicap"  # 让球


class PredictionConfidence(Enum):
    """预测置信度枚举"""

    VERY_LOW = (0.0, 0.5, "极低置信度")
    LOW = (0.5, 0.6, "低置信度")
    MEDIUM = (0.6, 0.75, "中等置信度")
    HIGH = (0.75, 0.85, "高置信度")
    VERY_HIGH = (0.85, 1.0, "极高置信度")

    def __init__(self, min_val: float, max_val: float, description: str):
        self.min_val = min_val
        self.max_val = max_val
        self.description = description

    @classmethod
    def from_value(cls, value: float) -> "PredictionConfidence":
        """从置信度值获取枚举"""
        for level in cls:
            if level.min_val <= value < level.max_val:
                return level
        return cls.VERY_LOW


class PredictionStatus(Enum):
    """预测状态枚举"""

    PENDING = "pending"  # 待验证
    CORRECT = "correct"  # 预测正确
    INCORRECT = "incorrect"  # 预测错误
    VOID = "void"  # 无效（比赛取消等）
    UNKNOWN = "unknown"  # 未知状态


@dataclass
class PredictionMetrics:
    """预测指标"""

    total_predictions: int = 0
    correct_predictions: int = 0
    incorrect_predictions: int = 0
    void_predictions: int = 0
    pending_predictions: int = 0

    @property
    def accuracy(self) -> float:
        """准确率"""
        if self.total_predictions == 0:
            return 0.0
        completed = self.correct_predictions + self.incorrect_predictions
        return self.correct_predictions / completed if completed > 0 else 0.0

    @property
    def completion_rate(self) -> float:
        """完成率"""
        if self.total_predictions == 0:
            return 0.0
        completed = (
            self.correct_predictions
            + self.incorrect_predictions
            + self.void_predictions
        )
        return completed / self.total_predictions

    @property
    def confidence_distribution(self) -> Dict[str, int]:
        """置信度分布"""
        return {}  # 由子类实现


@dataclass
class PredictionValue:
    """预测价值评估"""

    predicted_probability: float  # 预测概率
    market_odds: float  # 市场赔率
    implied_probability: float  # 隐含概率
    value_score: float  # 价值分数
    recommended_stake: float  # 建议投注比例
    expected_value: float  # 期望收益

    @classmethod
    def calculate(cls, predicted_prob: float, market_odds: float) -> "PredictionValue":
        """计算预测价值"""
        implied_prob = 1.0 / market_odds if market_odds > 0 else 0.0
        value_score = predicted_prob * market_odds - 1.0
        recommended_stake = max(0, min(1, value_score * 2))  # Kelly公式简化版
        expected_value = predicted_prob * (market_odds - 1) - (1 - predicted_prob)

        return cls(
            predicted_probability=predicted_prob,
            market_odds=market_odds,
            implied_probability=implied_prob,
            value_score=value_score,
            recommended_stake=recommended_stake,
            expected_value=expected_value,
        )


class Prediction:
    """预测领域模型

    封装预测的核心业务逻辑和评估方法。
    """

    def __init__(
        self,
        id: Optional[int] = None,
        match: Optional[Match] = None,
        user_id: Optional[int] = None,
        prediction_type: PredictionType = PredictionType.MATCH_RESULT,
        predicted_result: Optional[str] = None,
        confidence: float = 0.5,
        predicted_odds: Optional[float] = None,
        actual_odds: Optional[float] = None,
        model_name: Optional[str] = None,
        features: Optional[Dict[str, Any]] = None,
        reasoning: Optional[str] = None,
    ):
        self.id = id
        self.match = match
        self.user_id = user_id
        self.prediction_type = prediction_type
        self.predicted_result = predicted_result
        self.confidence = max(0.0, min(1.0, confidence))  # 确保在0-1之间
        self.predicted_odds = predicted_odds
        self.actual_odds = actual_odds
        self.model_name = model_name
        self.features = features or {}
        self.reasoning = reasoning

        # 价值评估
        self.value_assessment: Optional[PredictionValue] = None

        # 验证相关
        self.status = PredictionStatus.PENDING
        self.actual_result: Optional[str] = None
        self.is_correct: Optional[bool] = None
        self.settled_at: Optional[datetime] = None

        # 元数据
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # 业务规则验证
        self._validate_initialization()

        # 计算价值评估
        if predicted_odds and confidence:
            self.value_assessment = PredictionValue.calculate(
                confidence, predicted_odds
            )

    def _validate_initialization(self):
        """验证初始化数据"""
        if (
            self.prediction_type == PredictionType.MATCH_RESULT
            and not self.predicted_result
        ):
            raise ValueError("比赛结果预测必须指定预测结果")

        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("置信度必须在0-1之间")

        if self.predicted_odds and self.predicted_odds <= 0:
            raise ValueError("赔率必须大于0")

    # ==================== 状态管理 ====================

    def can_be_settled(self) -> bool:
        """检查是否可以结算"""
        return (
            self.status == PredictionStatus.PENDING
            and self.match
            and self.match.is_finished()
            and self.match.current_score.is_valid()
        )

    def settle_prediction(self) -> bool:
        """结算预测"""
        if not self.can_be_settled():
            return False

        try:
            # 获取实际结果
            actual_result = self._get_actual_result()
            if not actual_result:
                self.status = PredictionStatus.UNKNOWN
                return False

            self.actual_result = actual_result
            self.is_correct = self._check_if_correct(actual_result)
            self.status = (
                PredictionStatus.CORRECT
                if self.is_correct
                else PredictionStatus.INCORRECT
            )
            self.settled_at = datetime.now()
            self.updated_at = datetime.now()

            return True

        except Exception:
            self.status = PredictionStatus.UNKNOWN
            self.updated_at = datetime.now()
            return False

    def _get_actual_result(self) -> Optional[str]:
        """获取实际比赛结果"""
        if not self.match or not self.match.current_score.is_valid():
            return None

        if self.prediction_type == PredictionType.MATCH_RESULT:
            result = self.match.current_score.get_result()
            return result.value if result else None

        elif self.prediction_type == PredictionType.OVER_UNDER:
            # 需要从predicted_result解析门槛值
            # 格式: "over_2.5" 或 "under_2.5"
            if self.predicted_result and "_" in self.predicted_result:
                threshold = float(self.predicted_result.split("_")[1])
                total_goals = (
                    self.match.current_score.home_score
                    + self.match.current_score.away_score
                )
                return (
                    f"over_{threshold}"
                    if total_goals > threshold
                    else f"under_{threshold}"
                )

        elif self.prediction_type == PredictionType.BOTH_TEAMS_SCORE:
            both_scored = (
                self.match.current_score.home_score > 0
                and self.match.current_score.away_score > 0
            )
            return "yes" if both_scored else "no"

        return None

    def _check_if_correct(self, actual_result: str) -> bool:
        """检查预测是否正确"""
        return self.predicted_result == actual_result

    def void_prediction(self, reason: Optional[str] = None) -> bool:
        """使预测无效"""
        if self.status != PredictionStatus.PENDING:
            return False

        self.status = PredictionStatus.VOID
        self.settled_at = datetime.now()
        self.updated_at = datetime.now()

        if reason:
            self.reasoning = f"[VOID] {reason}"

        return True

    # ==================== 置信度管理 ====================

    def get_confidence_level(self) -> PredictionConfidence:
        """获取置信度等级"""
        return PredictionConfidence.from_value(self.confidence)

    def update_confidence(
        self, new_confidence: float, reason: Optional[str] = None
    ) -> bool:
        """更新置信度"""
        if self.status != PredictionStatus.PENDING:
            return False

        old_confidence = self.confidence
        self.confidence = max(0.0, min(1.0, new_confidence))
        self.updated_at = datetime.now()

        # 更新价值评估
        if self.predicted_odds:
            self.value_assessment = PredictionValue.calculate(
                self.confidence, self.predicted_odds
            )

        # 记录变更原因
        if reason:
            self.reasoning = f"[Confidence updated: {old_confidence:.2f}→{self.confidence:.2f}] {reason}"

        return True

    # ==================== 价值分析 ====================

    def is_value_bet(self, threshold: float = 0.0) -> bool:
        """判断是否为价值投注"""
        if not self.value_assessment:
            return False
        return self.value_assessment.value_score > threshold

    def get_expected_value(self) -> float:
        """获取期望收益"""
        if not self.value_assessment:
            return 0.0
        return self.value_assessment.expected_value

    def get_recommended_stake(self, max_stake: float = 0.1) -> float:
        """获取建议投注比例"""
        if not self.value_assessment or self.value_assessment.value_score <= 0:
            return 0.0
        return min(self.value_assessment.recommended_stake, max_stake)

    # ==================== 特征分析 ====================

    def add_feature(self, name: str, value: Any) -> None:
        """添加特征"""
        self.features[name] = value
        self.updated_at = datetime.now()

    def get_feature(self, name: str, default: Any = None) -> Any:
        """获取特征值"""
        return self.features.get(name, default)

    def analyze_key_factors(self) -> List[str]:
        """分析关键影响因素"""
        factors = []

        # 基于置信度分析
        if self.confidence > 0.8:
            factors.append("模型置信度极高")
        elif self.confidence < 0.5:
            factors.append("模型置信度较低，存在不确定性")

        # 基于价值分析
        if self.value_assessment:
            if self.value_assessment.value_score > 0.3:
                factors.append("高价值投注机会")
            elif self.value_assessment.value_score < -0.2:
                factors.append("预期收益为负，不建议投注")

        # 基于历史表现
        if self.model_name:
            # 这里可以查询模型历史表现
            factors.append(f"使用模型: {self.model_name}")

        return factors

    # ==================== 导出和序列化 ====================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "match_id": self.match.id if self.match else None,
            "user_id": self.user_id,
            "prediction_type": self.prediction_type.value,
            "predicted_result": self.predicted_result,
            "confidence": self.confidence,
            "confidence_level": self.get_confidence_level().description,
            "predicted_odds": self.predicted_odds,
            "actual_odds": self.actual_odds,
            "model_name": self.model_name,
            "features": self.features,
            "reasoning": self.reasoning,
            "status": self.status.value,
            "actual_result": self.actual_result,
            "is_correct": self.is_correct,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
            "is_value_bet": self.is_value_bet(),
            "expected_value": self.get_expected_value(),
            "recommended_stake": self.get_recommended_stake(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Prediction":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            match=data.get("match"),  # 需要外部设置
            user_id=data.get("user_id"),
            prediction_type=PredictionType(data.get("prediction_type", "match_result")),
            predicted_result=data.get("predicted_result"),
            confidence=data.get("confidence", 0.5),
            predicted_odds=data.get("predicted_odds"),
            actual_odds=data.get("actual_odds"),
            model_name=data.get("model_name"),
            features=data.get("features"),
            reasoning=data.get("reasoning"),
        )

    # ==================== 比较和哈希 ====================

    def __eq__(self, other) -> bool:
        """比较两个预测是否相同"""
        if not isinstance(other, Prediction):
            return False
        return (
            self.id == other.id
            if self.id and other.id
            else (
                self.match == other.match
                and self.user_id == other.user_id
                and self.prediction_type == other.prediction_type
                and self.predicted_result == other.predicted_result
            )
        )

    def __hash__(self) -> int:
        """生成哈希值"""
        if self.id:
            return hash(self.id)
        return hash(
            (
                self.match.id if self.match else None,
                self.user_id,
                self.prediction_type,
                self.predicted_result,
            )
        )

    def __str__(self) -> str:
        """字符串表示"""
        match_info = f"Match {self.match.id}" if self.match else "Unknown Match"
        return f"{match_info} - {self.prediction_type.value}: {self.predicted_result} ({self.confidence:.2f})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"Prediction(id={self.id}, "
            f"match={self.match.id if self.match else None}, "
            f"type={self.prediction_type.value}, "
            f"result={self.predicted_result}, "
            f"confidence={self.confidence:.2f}, "
            f"status={self.status.value})"
        )
