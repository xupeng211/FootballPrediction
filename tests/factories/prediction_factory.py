"""Predictions 模型工厂。"""

from __future__ import annotations

import random
from datetime import datetime
from decimal import Decimal

import factory

from tests.factories.base import BaseFactory
from src.database.models.predictions import PredictedResult, Predictions
from src.database.models.match import Match


class PredictionFactory(BaseFactory):
    """创建机器学习预测记录。"""

    class Meta:
        model = Predictions

    match = factory.SubFactory("tests.factories.match_factory.MatchFactory")
    model_name = "baseline-model"
    model_version = "v1.0.0"
    predicted_result = PredictedResult.HOME_WIN
    home_win_probability = factory.LazyFunction(lambda: Decimal("0.55"))
    draw_probability = factory.LazyFunction(lambda: Decimal("0.25"))
    away_win_probability = factory.LazyFunction(lambda: Decimal("0.20"))
    confidence_score = factory.LazyFunction(lambda: Decimal("0.82"))
    predicted_home_score = factory.LazyFunction(lambda: Decimal("2.0"))
    predicted_away_score = factory.LazyFunction(lambda: Decimal("1.0"))
    over_under_prediction = factory.LazyFunction(lambda: Decimal("3.5"))
    btts_probability = factory.LazyFunction(lambda: Decimal("0.48"))
    features_used = factory.LazyFunction(
        lambda: {"team_form_last_5": "WWDLW", "injuries": 1, "home_advantage": True}
    )
    prediction_metadata = factory.LazyFunction(
        lambda: {"model": "gradient_boosting", "training_version": "2024.10"}
    )
    predicted_at = factory.LazyFunction(datetime.utcnow)

    @classmethod
    def _attach_match(cls, payload: dict) -> dict:
        if "match" in payload:
            return payload

        match_id = payload.get("match_id")
        if match_id is None:
            return payload

        session = cls._meta.sqlalchemy_session
        payload["match"] = session.get(Match, match_id) if session else None
        return payload

    @classmethod
    def create_for_match(cls, match_id: int, **kwargs) -> Predictions:
        data = cls._attach_match({"match_id": match_id, **kwargs})
        return cls(**data)

    @classmethod
    def create_home_win_prediction(cls, **kwargs) -> Predictions:
        base = {
            "predicted_result": PredictedResult.HOME_WIN,
            "home_win_probability": Decimal("0.65"),
            "draw_probability": Decimal("0.20"),
            "away_win_probability": Decimal("0.15"),
            "predicted_home_score": Decimal("2.0"),
            "predicted_away_score": Decimal("1.0"),
        }
        base.update(kwargs)
        return cls(**cls._attach_match(base))

    @classmethod
    def create_draw_prediction(cls, **kwargs) -> Predictions:
        base = {
            "predicted_result": PredictedResult.DRAW,
            "home_win_probability": Decimal("0.30"),
            "draw_probability": Decimal("0.40"),
            "away_win_probability": Decimal("0.30"),
            "predicted_home_score": Decimal("1.0"),
            "predicted_away_score": Decimal("1.0"),
        }
        base.update(kwargs)
        return cls(**cls._attach_match(base))

    @classmethod
    def create_away_win_prediction(cls, **kwargs) -> Predictions:
        base = {
            "predicted_result": PredictedResult.AWAY_WIN,
            "home_win_probability": Decimal("0.15"),
            "draw_probability": Decimal("0.20"),
            "away_win_probability": Decimal("0.65"),
            "predicted_home_score": Decimal("1.0"),
            "predicted_away_score": Decimal("2.0"),
        }
        base.update(kwargs)
        return cls(**cls._attach_match(base))

    @classmethod
    def create_correct_prediction(
        cls, actual_home_score: int, actual_away_score: int, **kwargs
    ):
        if actual_home_score > actual_away_score:
            result = PredictedResult.HOME_WIN
        elif actual_home_score < actual_away_score:
            result = PredictedResult.AWAY_WIN
        else:
            result = PredictedResult.DRAW
        base = {
            "predicted_result": result,
            "home_win_probability": Decimal("0.60")
            if result == PredictedResult.HOME_WIN
            else Decimal("0.20"),
            "draw_probability": Decimal("0.60")
            if result == PredictedResult.DRAW
            else Decimal("0.20"),
            "away_win_probability": Decimal("0.60")
            if result == PredictedResult.AWAY_WIN
            else Decimal("0.20"),
            "predicted_home_score": Decimal(str(actual_home_score)),
            "predicted_away_score": Decimal(str(actual_away_score)),
            "is_correct": True,
        }
        base.update(kwargs)
        data = cls._attach_match(base)
        return cls(**data)

    @classmethod
    def create_incorrect_prediction(
        cls, actual_home_score: int, actual_away_score: int, **kwargs
    ):
        result_pool = [
            PredictedResult.HOME_WIN,
            PredictedResult.DRAW,
            PredictedResult.AWAY_WIN,
        ]
        if actual_home_score > actual_away_score:
            actual = PredictedResult.HOME_WIN
        elif actual_home_score < actual_away_score:
            actual = PredictedResult.AWAY_WIN
        else:
            actual = PredictedResult.DRAW
        result_pool.remove(actual)
        wrong_result = random.choice(result_pool)
        base = {
            "predicted_result": wrong_result,
            "is_correct": False,
        }
        base.update(kwargs)
        data = cls._attach_match(base)
        return cls(**data)


class MLModelPredictionFactory(PredictionFactory):
    """特定模型版本。"""

    class Meta:
        model = Predictions

    model_name = "ml-service"
    model_version = "ML-v2.1.0"


class EnsemblePredictionFactory(PredictionFactory):
    """集成模型预测。"""

    class Meta:
        model = Predictions

    model_name = "ensemble-model"
    model_version = "Ensemble-v3.0.0"
