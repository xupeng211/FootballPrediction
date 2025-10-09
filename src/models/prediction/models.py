"""
预测结果数据模型
Prediction Result Data Models

定义预测结果相关的数据结构和类型。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


@dataclass
class PredictionResult:
    """
    预测结果数据类 / Prediction Result Data Class

    存储比赛预测的完整结果，包括概率、置信度和元数据。
    Stores complete match prediction results including probabilities, confidence scores and metadata.

    Attributes:
        match_id (int): 比赛唯一标识符 / Unique match identifier
        model_version (str): 使用的模型版本 / Model version used
        model_name (str): 模型名称，默认为"football_baseline_model" / Model name, defaults to "football_baseline_model"
        home_win_probability (float): 主队获胜概率，范围0-1 / Home win probability, range 0-1
        draw_probability (float): 平局概率，范围0-1 / Draw probability, range 0-1
        away_win_probability (float): 客队获胜概率，范围0-1 / Away win probability, range 0-1
        predicted_result (str): 预测结果，'home'/'draw'/'away' / Predicted result, 'home'/'draw'/'away'
        confidence_score (float): 预测置信度，范围0-1 / Prediction confidence score, range 0-1
        features_used (Optional[Dict[str, Any]]): 使用的特征字典 / Dictionary of features used
        prediction_metadata (Optional[Dict[str, Any]]): 预测元数据 / Prediction metadata
        created_at (Optional[datetime]): 预测创建时间 / Prediction creation time
        actual_result (Optional[str]): 实际比赛结果 / Actual match result
        is_correct (Optional[bool]): 预测是否正确 / Whether prediction is correct
        verified_at (Optional[datetime]): 验证时间 / Verification time
    """

    match_id: int
    model_version: str
    model_name: str = "football_baseline_model"

    # 预测概率 / Prediction probabilities
    home_win_probability: float = 0.0
    draw_probability: float = 0.0
    away_win_probability: float = 0.0

    # 预测结果 / Prediction result
    predicted_result: str = "draw"  # 'home', 'draw', 'away'
    confidence_score: float = 0.0

    # 元数据 / Metadata
    features_used: Optional[Dict[str, Any]] = None
    prediction_metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    # 结果验证（比赛结束后更新） / Result verification (updated after match)
    actual_result: Optional[str] = None
    is_correct: Optional[bool] = None
    verified_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式 / Convert to dictionary format

        Returns:
            Dict[str, Any]: 包含所有预测结果属性的字典 / Dictionary containing all prediction result attributes
        """
        return {
            "match_id": self.match_id,
            "model_version": self.model_version,
            "model_name": self.model_name,
            "home_win_probability": self.home_win_probability,
            "draw_probability": self.draw_probability,
            "away_win_probability": self.away_win_probability,
            "predicted_result": self.predicted_result,
            "confidence_score": self.confidence_score,
            "features_used": self.features_used,
            "prediction_metadata": self.prediction_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "actual_result": self.actual_result,
            "is_correct": self.is_correct,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredictionResult":
        """
        从字典创建预测结果对象 / Create PredictionResult from dictionary

        Args:
            data (Dict[str, Any]): 包含预测结果的字典 / Dictionary containing prediction result

        Returns:
            PredictionResult: 预测结果对象 / Prediction result object
        """
        # 处理日期时间字符串
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("verified_at"):
            data["verified_at"] = datetime.fromisoformat(data["verified_at"])

        return cls(**data)

    def is_probabilities_valid(self) -> bool:
        """
        验证概率值是否有效 / Validate probability values

        Returns:
            bool: 概率值是否有效（总和是否等于1） / Whether probabilities are valid (sum equals 1)
        """
        total = self.home_win_probability + self.draw_probability + self.away_win_probability
        return abs(total - 1.0) < 0.001  # 允许小数点误差

    def get_highest_probability(self) -> Tuple[str, float]:
        """
        获取最高概率及其对应的结果 / Get highest probability and its corresponding result

        Returns:
            Tuple[str, float]: (结果, 概率) / (result, probability)
        """
        probabilities = {
            "home": self.home_win_probability,
            "draw": self.draw_probability,
            "away": self.away_win_probability,
        }

        highest_result = max(probabilities, key=probabilities.get)
        return highest_result, probabilities[highest_result]

    def update_actual_result(self, home_score: int, away_score: int) -> None:
        """
        更新实际比赛结果 / Update actual match result

        Args:
            home_score (int): 主队得分 / Home team score
            away_score (int): 客队得分 / Away team score
        """
        if home_score > away_score:
            self.actual_result = "home"
        elif home_score < away_score:
            self.actual_result = "away"
        else:
            self.actual_result = "draw"

        self.is_correct = self.actual_result == self.predicted_result
        self.verified_at = datetime.now()