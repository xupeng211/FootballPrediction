"""
预测工厂 - 用于测试数据创建
"""

import random
from datetime import datetime, timezone

from .base import BaseFactory, DataFactoryMixin, TimestampMixin


class PredictionFactory(BaseFactory, DataFactoryMixin, TimestampMixin):
    """预测测试数据工厂"""

    # 预测结果类型
    PREDICTION_RESULTS = ["win", "draw", "lose", "postponed", "cancelled"]

    # 预测模型类型
    MODEL_TYPES = [
        "neural_network",
        "random_forest",
        "logistic_regression",
        "xgboost",
        "svm",
        "ensemble",
        "deep_learning",
    ]

    # 联赛名称
    LEAGUE_NAMES = ["西甲", "英超", "意甲", "德甲", "法甲", "中超", "日职联", "韩K联"]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建单个预测实例"""
        default_data = {
            "id": cls.generate_id(),
            "match_id": kwargs.get("match_id", cls.generate_id()),
            "home_team_id": kwargs.get("home_team_id", cls.generate_id()),
            "away_team_id": kwargs.get("away_team_id", cls.generate_id()),
            "league": kwargs.get("league", random.choice(cls.LEAGUE_NAMES)),
            "predicted_result": random.choice(cls.PREDICTION_RESULTS),
            "confidence": round(random.uniform(0.5, 1.0), 3),
            "home_win_prob": round(random.uniform(0.0, 1.0), 3),
            "draw_prob": round(random.uniform(0.0, 1.0), 3),
            "away_win_prob": round(random.uniform(0.0, 1.0), 3),
            "model_name": random.choice(cls.MODEL_TYPES),
            "model_version": f"v{random.randint(1, 5)}.{random.randint(0, 9)}",
            "features": cls._generate_features(),
            "prediction_date": cls.generate_timestamp(),
            "match_date": cls._generate_match_date(),
            "created_at": cls.generate_timestamp(),
            "updated_at": cls.generate_timestamp(),
            "is_correct": random.choice([True, False]),
            "actual_result": None,
            "accuracy_score": None,
            "risk_level": random.choice(["low", "medium", "high"]),
            "status": "pending",
        }

        # 确保概率总和为1
        probs = [
            default_data["home_win_prob"],
            default_data["draw_prob"],
            default_data["away_win_prob"],
        ]
        total = sum(probs)
        if total > 0:
            default_data["home_win_prob"] = round(probs[0] / total, 3)
            default_data["draw_prob"] = round(probs[1] / total, 3)
            default_data["away_win_prob"] = round(probs[2] / total, 3)

        # 合并用户提供的参数
        default_data.update(kwargs)
        return cls.with_timestamps(**default_data)

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> List[Dict[str, Any]]:
        """批量创建预测实例"""
        predictions = []
        for i in range(count):
            prediction_data = cls.create(**kwargs)
            predictions.append(prediction_data)
        return predictions

    @classmethod
    def create_with_result(cls, actual_result: str, **kwargs) -> Dict[str, Any]:
        """创建带实际结果的预测"""
        prediction = cls.create(**kwargs)
        prediction["actual_result"] = actual_result
        prediction["status"] = "completed"
        prediction["is_correct"] = prediction["predicted_result"] == actual_result
        prediction["accuracy_score"] = 1.0 if prediction["is_correct"] else 0.0
        return prediction

    @classmethod
    def create_high_confidence(cls, **kwargs) -> Dict[str, Any]:
        """创建高置信度预测"""
        return cls.create(confidence=random.uniform(0.8, 1.0), risk_level="low", **kwargs)

    @classmethod
    def create_low_confidence(cls, **kwargs) -> Dict[str, Any]:
        """创建低置信度预测"""
        return cls.create(confidence=random.uniform(0.5, 0.7), risk_level="high", **kwargs)

    @classmethod
    def create_for_teams(cls, home_team_id: int, away_team_id: int, **kwargs) -> Dict[str, Any]:
        """为特定球队创建预测"""
        return cls.create(home_team_id=home_team_id, away_team_id=away_team_id, **kwargs)

    @classmethod
    def create_correct_prediction(cls, **kwargs) -> Dict[str, Any]:
        """创建正确预测"""
        predicted_result = kwargs.get("predicted_result", random.choice(cls.PREDICTION_RESULTS[:3]))
        return cls.create_with_result(
            actual_result=predicted_result, predicted_result=predicted_result, **kwargs
        )

    @classmethod
    def create_incorrect_prediction(cls, **kwargs) -> Dict[str, Any]:
        """创建错误预测"""
        predicted_result = kwargs.get("predicted_result", random.choice(cls.PREDICTION_RESULTS[:3]))
        actual_results = cls.PREDICTION_RESULTS[:3]
        actual_results = [r for r in actual_results if r != predicted_result]
        actual_result = random.choice(actual_results) if actual_results else "draw"

        return cls.create_with_result(
            actual_result=actual_result, predicted_result=predicted_result, **kwargs
        )

    @classmethod
    def create_for_today(cls, **kwargs) -> Dict[str, Any]:
        """创建今日预测"""
        today = datetime.now(timezone.utc)
        return cls.create(match_date=today, prediction_date=today, **kwargs)

    @classmethod
    def create_for_future(cls, days_ahead: int = 7, **kwargs) -> Dict[str, Any]:
        """创建未来预测"""
        future_date = datetime.now(timezone.utc).replace(
            day=datetime.now(timezone.utc).day + days_ahead
        )
        return cls.create(match_date=future_date, **kwargs)

    @classmethod
    def _generate_features(cls) -> Dict[str, float]:
        """生成特征数据"""
        return {
            "home_team_form": round(random.uniform(-1, 1), 3),
            "away_team_form": round(random.uniform(-1, 1), 3),
            "head_to_head_home_win": round(random.uniform(0, 1), 3),
            "head_to_head_draw": round(random.uniform(0, 1), 3),
            "head_to_head_away_win": round(random.uniform(0, 1), 3),
            "home_goals_scored_avg": round(random.uniform(0, 5), 2),
            "away_goals_scored_avg": round(random.uniform(0, 5), 2),
            "home_goals_conceded_avg": round(random.uniform(0, 5), 2),
            "away_goals_conceded_avg": round(random.uniform(0, 5), 2),
            "home_team_ranking": random.randint(1, 20),
            "away_team_ranking": random.randint(1, 20),
            "days_since_last_match_home": random.randint(0, 14),
            "days_since_last_match_away": random.randint(0, 14),
            "home_team_injuries": random.randint(0, 5),
            "away_team_injuries": random.randint(0, 5),
        }

    @classmethod
    def _generate_match_date(cls) -> datetime:
        """生成比赛日期"""
        days_ahead = random.randint(0, 30)
        return datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day + days_ahead)


class MatchPredictionFactory(PredictionFactory):
    """比赛预测工厂"""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建比赛预测"""
        prediction = super().create(**kwargs)

        # 添加比赛特有字段
        prediction.update(
            {
                "match_venue": kwargs.get(
                    "match_venue", random.choice(["主场", "客场", "中性场地"])
                ),
                "weather_condition": kwargs.get(
                    "weather_condition", random.choice(["晴", "雨", "雪", "多云"])
                ),
                "attendance": random.randint(1000, 100000),
                "referee": f"裁判_{random.randint(1, 100)}",
                "match_importance": random.choice(["low", "medium", "high", "critical"]),
            }
        )

        return prediction


class TournamentPredictionFactory(PredictionFactory):
    """锦标赛预测工厂"""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建锦标赛预测"""
        prediction = super().create(**kwargs)

        # 添加锦标赛特有字段
        prediction.update(
            {
                "tournament_name": kwargs.get(
                    "tournament_name",
                    random.choice(["世界杯", "欧洲杯", "亚洲杯", "美洲杯", "非洲杯"]),
                ),
                "tournament_stage": kwargs.get(
                    "tournament_stage",
                    random.choice(
                        [
                            "group_stage",
                            "round_of-16",
                            "quarter-finals",
                            "semi-finals",
                            "final",
                        ]
                    ),
                ),
                "knockout_match": kwargs.get("knockout_match", random.choice([True, False])),
                "extra_time_possible": kwargs.get("extra_time_possible", False),
                "penalties_possible": kwargs.get("penalties_possible", False),
            }
        )

        return prediction


class MLModelPredictionFactory(PredictionFactory):
    """机器学习模型预测工厂"""

    # ML模型类型
    ML_MODEL_TYPES = [
        "deep_neural_network",
        "random_forest",
        "gradient_boosting",
        "logistic_regression",
        "support_vector_machine",
        "ensemble_stacking",
        "lstm_neural_network",
        "transformer_model",
        "cnn_model",
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建ML模型预测"""
        prediction = super().create(**kwargs)

        # 添加ML特有字段
        model_name = kwargs.get("model_name", random.choice(cls.ML_MODEL_TYPES))
        prediction.update(
            {
                "model_name": model_name,
                "model_type": "machine_learning",
                "model_framework": kwargs.get(
                    "model_framework",
                    random.choice(["tensorflow", "pytorch", "scikit_learn", "xgboost", "lightgbm"]),
                ),
                "model_version": f"ml_v{random.randint(1, 10)}.{random.randint(0, 9)}.{random.randint(0, 99)}",
                "training_data_version": f"data_v{random.randint(1, 5)}",
                "feature_importance": cls._generate_feature_importance(),
                "model_confidence": round(random.uniform(0.7, 0.95), 3),
                "prediction_probability": round(random.uniform(0.5, 1.0), 3),
                "training_accuracy": round(random.uniform(0.75, 0.95), 3),
                "validation_accuracy": round(random.uniform(0.70, 0.92), 3),
                "cross_val_score": round(random.uniform(0.68, 0.90), 3),
                "prediction_shap_values": cls._generate_shap_values(),
                "model_explainability": kwargs.get(
                    "model_explainability", random.choice(["high", "medium", "low"])
                ),
                "ensemble_weight": round(random.uniform(0.1, 0.9), 3),
                "model_bias_score": round(random.uniform(-0.1, 0.1), 3),
                "data_drift_detected": random.choice([True, False]),
                "model_performance_trend": kwargs.get(
                    "model_performance_trend",
                    random.choice(["improving", "stable", "declining"]),
                ),
            }
        )

        return prediction

    @classmethod
    def _generate_feature_importance(cls) -> Dict[str, float]:
        """生成特征重要性"""
        features = [
            "home_team_form",
            "away_team_form",
            "head_to_head_stats",
            "home_goals_scored",
            "away_goals_conceded",
            "team_rankings",
            "injury_status",
            "weather_conditions",
            "home_advantage",
            "recent_performance",
            "historical_patterns",
        ]

        # 生成归一化的特征重要性
        importance_values = [random.uniform(0.01, 0.3) for _ in features]
        total = sum(importance_values)
        normalized_importance = [round(val / total, 4) for val in importance_values]

        return dict(zip(features, normalized_importance))

    @classmethod
    def _generate_shap_values(cls) -> Dict[str, float]:
        """生成SHAP值"""
        features = [
            "home_team_form",
            "away_team_form",
            "head_to_head_stats",
            "home_goals_scored",
            "away_goals_conceded",
            "team_rankings",
        ]

        return {feature: round(random.uniform(-0.2, 0.2), 4) for feature in features}
