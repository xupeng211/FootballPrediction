"""
预测结果数据类

定义预测结果的完整数据结构
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


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
    updated_at: Optional[datetime] = None

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
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }