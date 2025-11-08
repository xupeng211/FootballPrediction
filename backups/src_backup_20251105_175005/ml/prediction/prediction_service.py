"""
预测服务
Prediction Service for Football Match Predictions
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from ..models.base_model import BaseModel, PredictionResult
from ..models.elo_model import EloModel
from ..models.poisson_model import PoissonModel

logger = logging.getLogger(__name__)


class PredictionStrategy(Enum):
    """预测策略"""

    SINGLE_MODEL = "single_model"
    WEIGHTED_ENSEMBLE = "weighted_ensemble"
    MAJORITY_VOTE = "majority_vote"
    BEST_PERFORMING = "best_performing"


@dataclass
class EnsemblePrediction:
    """集成预测结果"""

    match_id: str
    home_team: str
    away_team: str
    predictions: list[PredictionResult]
    ensemble_home_win_prob: float
    ensemble_draw_prob: float
    ensemble_away_win_prob: float
    ensemble_predicted_outcome: str
    ensemble_confidence: float
    strategy: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "predictions": [p.to_dict() for p in self.predictions],
    "ensemble_home_win_prob": self.ensemble_home_win_prob,
    "ensemble_draw_prob": self.ensemble_draw_prob,
    "ensemble_away_win_prob": self.ensemble_away_win_prob,

            "ensemble_predicted_outcome": self.ensemble_predicted_outcome,
            "ensemble_confidence": self.ensemble_confidence,
            "strategy": self.strategy,
            "created_at": self.created_at.isoformat(),
        }


class PredictionService:
    """预测服务"""

    def __init__(self):
        self.models = {}
        self.model_weights = {}
        self.model_performance = {}
        self.default_strategy = PredictionStrategy.WEIGHTED_ENSEMBLE

        # 注册默认模型
        self._register_default_models()

    def _register_default_models(self):
        """注册默认模型"""
        self.register_model("poisson", PoissonModel())
        self.register_model("elo", EloModel())

        # 默认权重
        self.model_weights = {"poisson": 0.4, "elo": 0.6}

    def register_model(self, name: str, model: BaseModel, weight: float = 1.0):
        """
        注册预测模型

        Args:
            name: 模型名称
            model: 模型实例
            weight: 模型权重
        """
        self.models[name] = model
        self.model_weights[name] = weight
        logger.info(f"Registered model: {name} (weight: {weight})")

    def unregister_model(self, name: str):
        """
        注销模型

        Args:
            name: 模型名称
        """
        if name in self.models:
            del self.models[name]
            del self.model_weights[name]
            logger.info(f"Unregistered model: {name}")

    def get_available_models(self) -> list[str]:
        """
        获取可用模型列表

        Returns:
            模型名称列表
        """
        return list(self.models.keys())

    def get_trained_models(self) -> list[str]:
        """
        获取已训练的模型列表

        Returns:
            已训练模型名称列表
        """
        return [name for name, model in self.models.items() if model.is_trained]

    def set_strategy(self, strategy: PredictionStrategy):
        """
        设置预测策略

        Args:
            strategy: 预测策略
        """
        self.default_strategy = strategy
        logger.info(f"Prediction strategy set to: {strategy.value}")

    def predict_match(
        self,
    match_data: dict[str,
    Any],
    model_name: str | None = None,

        strategy: PredictionStrategy | None = None,
    ) -> Any:
        """
        预测比赛结果

        Args:
            match_data: 比赛数据
            model_name: 指定模型名称（如果使用单个模型）
            strategy: 预测策略

        Returns:
            预测结果
        """
        if model_name:
            # 使用指定模型
            if model_name not in self.models:
                raise ValueError(f"Model not found: {model_name}")

            model = self.models[model_name]
            if not model.is_trained:
                raise RuntimeError(f"Model not trained: {model_name}")

            return model.predict(match_data)

        # 使用集成策略
        strategy = strategy or self.default_strategy
        return self._ensemble_predict(match_data,
    strategy)

    def _ensemble_predict(
        self,
    match_data: dict[str,
    Any],
    strategy: PredictionStrategy
    ) -> EnsemblePrediction:
        """
        集成预测

        Args:
            match_data: 比赛数据
            strategy: 预测策略

        Returns:
            集成预测结果
        """
        trained_models = self.get_trained_models()
        if not trained_models:
            raise RuntimeError("No trained models available")

        predictions = []
        for model_name in trained_models:
            model = self.models[model_name]
            try:
                prediction = model.predict(match_data)
                predictions.append(prediction)
            except Exception as e:
                logger.warning(f"Failed to get prediction from model {model_name}: {e}")
                continue

        if not predictions:
            raise RuntimeError("No successful predictions from any model")

        # 根据策略计算集成结果
        if strategy == PredictionStrategy.WEIGHTED_ENSEMBLE:
            ensemble_result = self._weighted_ensemble(predictions)
        elif strategy == PredictionStrategy.MAJORITY_VOTE:
            ensemble_result = self._majority_vote(predictions)
        elif strategy == PredictionStrategy.BEST_PERFORMING:
            ensemble_result = self._best_performing(predictions)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        home_team = match_data["home_team"]
        away_team = match_data["away_team"]
        match_id = match_data.get("match_id", f"{home_team}_vs_{away_team}")

        return EnsemblePrediction(
            match_id=match_id,
    home_team=home_team,
    away_team=away_team,
    predictions=predictions,

            ensemble_home_win_prob=ensemble_result["home_win_prob"],
            ensemble_draw_prob=ensemble_result["draw_prob"],
            ensemble_away_win_prob=ensemble_result["away_win_prob"],
            ensemble_predicted_outcome=ensemble_result["predicted_outcome"],
            ensemble_confidence=ensemble_result["confidence"],
            strategy=strategy.value,
            created_at=datetime.now(),
    )

    def _weighted_ensemble(self,
    predictions: list[PredictionResult]) -> dict[str,
    Any]:
        """
        加权集成预测

        Args:
            predictions: 各模型预测结果

        Returns:
            集成预测结果
        """
        total_weight = 0.0
        weighted_home_win = 0.0
        weighted_draw = 0.0
        weighted_away_win = 0.0

        for prediction in predictions:
            model_name = prediction.model_name
            weight = self.model_weights.get(model_name,
    1.0)

            weighted_home_win += prediction.home_win_prob * weight
            weighted_draw += prediction.draw_prob * weight
            weighted_away_win += prediction.away_win_prob * weight
            total_weight += weight

        if total_weight > 0:
            weighted_home_win /= total_weight
            weighted_draw /= total_weight
            weighted_away_win /= total_weight

        # 归一化
        total_prob = weighted_home_win + weighted_draw + weighted_away_win
        if total_prob > 0:
            weighted_home_win /= total_prob
            weighted_draw /= total_prob
            weighted_away_win /= total_prob

        # 计算预测结果和置信度
        probabilities = (weighted_home_win, weighted_draw, weighted_away_win)
        predicted_outcome = self._get_outcome_from_probabilities(probabilities)
        confidence = self._calculate_confidence(probabilities)

        return {
            "home_win_prob": weighted_home_win,
            "draw_prob": weighted_draw,
            "away_win_prob": weighted_away_win,
            "predicted_outcome": predicted_outcome,
            "confidence": confidence,
        }

    def _majority_vote(self, predictions: list[PredictionResult]) -> dict[str, Any]:
        """
        多数投票预测

        Args:
            predictions: 各模型预测结果

        Returns:
            集成预测结果
        """
        # 统计各结果的投票数
        vote_counts = {"home_win": 0, "draw": 0, "away_win": 0}
        probabilities_sum = {"home_win": 0.0, "draw": 0.0, "away_win": 0.0}

        for prediction in predictions:
            vote_counts[prediction.predicted_outcome] += 1
            probabilities_sum["home_win"] += prediction.home_win_prob
            probabilities_sum["draw"] += prediction.draw_prob
            probabilities_sum["away_win"] += prediction.away_win_prob

        # 确定多数投票结果
        predicted_outcome = max(vote_counts, key=vote_counts.get)

        # 平均概率
        num_predictions = len(predictions)
        avg_home_win = probabilities_sum["home_win"] / num_predictions
        avg_draw = probabilities_sum["draw"] / num_predictions
        avg_away_win = probabilities_sum["away_win"] / num_predictions

        # 归一化
        total_prob = avg_home_win + avg_draw + avg_away_win
        if total_prob > 0:
            avg_home_win /= total_prob
            avg_draw /= total_prob
            avg_away_win /= total_prob

        # 计算置信度（基于投票一致性）
        max_votes = max(vote_counts.values())
        confidence = max_votes / num_predictions

        return {
            "home_win_prob": avg_home_win,
            "draw_prob": avg_draw,
            "away_win_prob": avg_away_win,
            "predicted_outcome": predicted_outcome,
            "confidence": confidence,
        }

    def _best_performing(self,
    predictions: list[PredictionResult]) -> dict[str,
    Any]:
        """
        选择表现最好的模型的预测

        Args:
            predictions: 各模型预测结果

        Returns:
            集成预测结果
        """
        if not self.model_performance:
            # 如果没有性能数据，使用第一个预测
            best_prediction = predictions[0]
        else:
            # 选择性能最好的模型
            best_model_name = max(
                self.model_performance.keys(),
    key=lambda x: self.model_performance[x].get("accuracy",
    0),

            )
            best_prediction = None
            for prediction in predictions:
                if prediction.model_name == best_model_name:
                    best_prediction = prediction
                    break

            if best_prediction is None:
                best_prediction = predictions[0]

        return {
            "home_win_prob": best_prediction.home_win_prob,
            "draw_prob": best_prediction.draw_prob,
            "away_win_prob": best_prediction.away_win_prob,
            "predicted_outcome": best_prediction.predicted_outcome,
            "confidence": best_prediction.confidence,
        }

    def _get_outcome_from_probabilities(
        self,
    probabilities: tuple[float,
    float,
    float]
    ) -> str:
        """从概率分布获取预测结果"""
        outcomes = ["home_win",
    "draw",
    "away_win"]
        max_index = max(range(3),
    key=lambda i: probabilities[i])
        return outcomes[max_index]

    def _calculate_confidence(self,
    probabilities: tuple[float,
    float,
    float]) -> float:
        """计算预测置信度"""
        max_prob = max(probabilities)
        min_prob = min(probabilities)
        confidence = max_prob + (max_prob - min_prob) * 0.1  # 考虑概率分布的离散程度
        return min(max(confidence,
    0.1),
    1.0)

    def predict_batch(
        self,
    matches_data: list[dict[str,
    Any]],

        model_name: str | None = None,
        strategy: PredictionStrategy | None = None,
    ) -> list[Any]:
        """
        批量预测

        Args:
            matches_data: 比赛数据列表
            model_name: 指定模型名称
            strategy: 预测策略

        Returns:
            预测结果列表
        """
        results = []
        for match_data in matches_data:
            try:
                result = self.predict_match(match_data, model_name, strategy)
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to predict match {match_data.get('match_id',
    'unknown')}: {e}"
                )
                continue

        return results

    def update_model_weights(self, weights: dict[str, float]):
        """
        更新模型权重

        Args:
            weights: 模型权重字典
        """
        for model_name, weight in weights.items():
            if model_name in self.models:
                self.model_weights[model_name] = weight
                logger.info(f"Updated weight for {model_name}: {weight}")

    def set_model_performance(
        self, model_name: str, performance_metrics: dict[str, float]
    ):
        """
        设置模型性能指标

        Args:
            model_name: 模型名称
            performance_metrics: 性能指标
        """
        self.model_performance[model_name] = performance_metrics
        logger.info(f"Updated performance metrics for {model_name}")

    def get_model_info(self) -> dict[str, Any]:
        """
        获取模型信息

        Returns:
            模型信息字典
        """
        models_info = {}
        for name, model in self.models.items():
            models_info[name] = {
                "type": model.__class__.__name__,
                "version": model.model_version,
                "is_trained": model.is_trained,
                "weight": self.model_weights.get(name, 1.0),
                "performance": self.model_performance.get(name, {}),
            }

        return {
            "total_models": len(self.models),
    "trained_models": len(self.get_trained_models()),
    "default_strategy": self.default_strategy.value,
    "models": models_info,

            "weights": self.model_weights.copy(),
    }

    def train_all_models(self,
    training_data,
    validation_data=None) -> dict[str,
    Any]:
        """
        训练所有模型

        Args:
            training_data: 训练数据
            validation_data: 验证数据

        Returns:
            训练结果字典
        """
        training_results = {}
        total_start_time = datetime.now()

        for name, model in self.models.items():
            logger.info(f"Training model: {name}")
            try:
                start_time = datetime.now()
                result = model.train(training_data, validation_data)
                training_time = (datetime.now() - start_time).total_seconds()

                training_results[name] = {
                    "success": True,
                    "training_time": training_time,
                    "metrics": result.to_dict(),
                }

                # 更新性能指标
                self.set_model_performance(
                    name,
                    {
                        "accuracy": result.accuracy,
                        "precision": result.precision,
                        "recall": result.recall,
                        "f1_score": result.f1_score,
                    },
                )

                logger.info(
                    f"Model {name} trained successfully in {training_time:.2f}s"
                )

            except Exception as e:
                logger.error(f"Failed to train model {name}: {e}")
                training_results[name] = {"success": False, "error": str(e)}

        total_time = (datetime.now() - total_start_time).total_seconds()
        successful_trainings = sum(
            1 for r in training_results.values() if r.get("success", False)
        )

        return {
            "total_time": total_time,
            "successful_trainings": successful_trainings,
            "total_models": len(self.models),
            "training_results": training_results,
        }
