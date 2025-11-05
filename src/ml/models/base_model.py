"""
基础预测模型
Base Prediction Model for Football Matches
"""

import abc
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """预测结果"""

    match_id: str
    home_team: str
    away_team: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    predicted_outcome: str  # 'home_win', 'draw', 'away_win'
    confidence: float
    model_name: str
    model_version: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_win_prob": self.home_win_prob,
            "draw_prob": self.draw_prob,
            "away_win_prob": self.away_win_prob,
            "predicted_outcome": self.predicted_outcome,
            "confidence": self.confidence,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TrainingResult:
    """训练结果"""

    model_name: str
    model_version: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: list[list[int]]
    training_samples: int
    validation_samples: int
    training_time: float
    features_used: list[str]
    hyperparameters: dict[str, Any]
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "confusion_matrix": self.confusion_matrix,
            "training_samples": self.training_samples,
            "validation_samples": self.validation_samples,
            "training_time": self.training_time,
            "features_used": self.features_used,
            "hyperparameters": self.hyperparameters,
            "created_at": self.created_at.isoformat(),
        }


class BaseModel(abc.ABC):
    """基础预测模型抽象类"""

    def __init__(self, model_name: str, version: str = "1.0"):
        self.model_name = model_name
        self.model_version = version
        self.is_trained = False
        self.model = None
        self.feature_names = []
        self.hyperparameters = {}
        self.training_history = []
        self.last_training_time = None

    @abc.abstractmethod
    def prepare_features(self,
    match_data: dict[str,
    Any]) -> np.ndarray:
        """
        准备特征

        Args:
            match_data: 比赛数据

        Returns:
            特征向量
        """

    @abc.abstractmethod
    def train(
        self,
    training_data: pd.DataFrame,

        validation_data: pd.DataFrame | None = None,
    ) -> TrainingResult:
        """
        训练模型

        Args:
            training_data: 训练数据
            validation_data: 验证数据

        Returns:
            训练结果
        """

    @abc.abstractmethod
    def predict(self,
    match_data: dict[str,
    Any]) -> PredictionResult:
        """
        预测比赛结果

        Args:
            match_data: 比赛数据

        Returns:
            预测结果
        """

    @abc.abstractmethod
    def predict_proba(self,
    match_data: dict[str,
    Any]) -> tuple[float,
    float,
    float]:
        """
        预测概率分布

        Args:
            match_data: 比赛数据

        Returns:
            (主胜概率, 平局概率, 客胜概率)
        """

    @abc.abstractmethod
    def evaluate(self,
    test_data: pd.DataFrame) -> dict[str,
    float]:
        """
        评估模型性能

        Args:
            test_data: 测试数据

        Returns:
            评估指标
        """

    @abc.abstractmethod
    def save_model(self,
    file_path: str) -> bool:
        """
        保存模型

        Args:
            file_path: 模型文件路径

        Returns:
            是否保存成功
        """

    @abc.abstractmethod
    def load_model(self,
    file_path: str) -> bool:
        """
        加载模型

        Args:
            file_path: 模型文件路径

        Returns:
            是否加载成功
        """

    def get_feature_importance(self) -> dict[str, float]:
        """
        获取特征重要性

        Returns:
            特征重要性字典
        """
        if not hasattr(self.model, "feature_importances_"):
            return {}

        if not self.feature_names:
            return {}

        return dict(
            zip(self.feature_names, self.model.feature_importances_, strict=False)
        )

    def get_model_info(self) -> dict[str, Any]:
        """
        获取模型信息

        Returns:
            模型信息字典
        """
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "is_trained": self.is_trained,
            "feature_count": len(self.feature_names),
    "feature_names": self.feature_names,
    "hyperparameters": self.hyperparameters,
    "last_training_time": self.last_training_time,

            "training_history_count": len(self.training_history),
    "feature_importance": self.get_feature_importance(),
    }

    def validate_prediction_input(self,
    match_data: dict[str,
    Any]) -> bool:
        """
        验证预测输入数据

        Args:
            match_data: 比赛数据

        Returns:
            是否有效
        """
        required_fields = ["home_team", "away_team"]

        for field in required_fields:
            if field not in match_data:
                logger.error(f"Missing required field: {field}")
                return False

        # 检查主客队不能相同
        if match_data["home_team"] == match_data["away_team"]:
            logger.error("Home team and away team cannot be the same")
            return False

        return True

    def calculate_confidence(self,
    probabilities: tuple[float,
    float,
    float]) -> float:
        """
        计算预测置信度

        Args:
            probabilities: (主胜概率,
    平局概率,
    客胜概率)

        Returns:
            置信度 (0-1)
        """
        # 使用最大概率作为置信度
        max_prob = max(probabilities)

        # 计算概率分布的熵
        probs = np.array(probabilities)
        probs = probs[probs > 0]  # 避免log(0)
        entropy = -np.sum(probs * np.log2(probs))

        # 熵越小，置信度越高
        max_entropy = np.log2(3)  # 3个结果的最大熵
        confidence_factor = 1 - (entropy / max_entropy)

        # 综合最大概率和熵因子
        confidence = max_prob * 0.7 + confidence_factor * 0.3

        return min(max(confidence,
    0.1),
    1.0)  # 限制在0.1-1.0之间

    def get_outcome_from_probabilities(
        self,
    probabilities: tuple[float,
    float,
    float]
    ) -> str:
        """
        从概率分布获取预测结果

        Args:
            probabilities: (主胜概率, 平局概率, 客胜概率)

        Returns:
            预测结果
        """
        outcomes = ["home_win", "draw", "away_win"]
        max_index = np.argmax(probabilities)
        return outcomes[max_index]

    def validate_training_data(self, training_data: pd.DataFrame) -> bool:
        """
        验证训练数据

        Args:
            training_data: 训练数据

        Returns:
            是否有效
        """
        if training_data.empty:
            logger.error("Training data is empty")
            return False

        required_columns = ["home_team", "away_team", "result"]
        for col in required_columns:
            if col not in training_data.columns:
                logger.error(f"Missing required column: {col}")
                return False

        # 检查数据质量
        if training_data.isnull().any().any():
            logger.warning("Training data contains null values")

        # 检查样本数量
        min_samples = 100
        if len(training_data) < min_samples:
            logger.warning(
                f"Training data has only {len(training_data)} samples, which may be insufficient"
            )

        return True

    def log_training_step(self, step: int, metrics: dict[str, float]):
        """
        记录训练步骤

        Args:
            step: 训练步骤
            metrics: 评估指标
        """
        log_entry = {"step": step, "timestamp": datetime.now(), "metrics": metrics}
        self.training_history.append(log_entry)

        logger.info(f"Training step {step}: {metrics}")

    def get_training_curve(self) -> dict[str, list[float]]:
        """
        获取训练曲线

        Returns:
            指标名称到值列表的映射
        """
        if not self.training_history:
            return {}

        curves = {}
        for metric_name in self.training_history[0]["metrics"].keys():
            curves[metric_name] = [
                entry["metrics"][metric_name] for entry in self.training_history
            ]

        return curves

    def update_hyperparameters(self, **kwargs):
        """
        更新超参数

        Args:
            **kwargs: 超参数键值对
        """
        self.hyperparameters.update(kwargs)
        logger.info(f"Updated hyperparameters: {kwargs}")

    def reset_model(self):
        """重置模型"""
        self.model = None
        self.is_trained = False
        self.training_history = []
        self.last_training_time = None
        logger.info("Model has been reset")

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.model_name}', version='{self.model_version}', trained={self.is_trained})>"
