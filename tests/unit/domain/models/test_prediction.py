from decimal import Decimal

import pytest

from src.core.exceptions import DomainError
from src.domain.models.prediction import (ConfidenceScore, Prediction,
                                          PredictionPoints, PredictionScore,
                                          PredictionStatus)


@pytest.fixture
def prediction() -> Prediction:
    return Prediction(user_id=1, match_id=2)


@pytest.mark.unit
class TestPredictionInitialization:
    def test_should_validate_basic_constraints(self):
        with pytest.raises(DomainError):
            Prediction(user_id=0, match_id=1)

        with pytest.raises(DomainError):
            Prediction(user_id=1, match_id=0)

    def test_should_create_prediction(self, prediction):
        assert prediction.is_pending is True
        assert prediction.score is None
        assert prediction.get_domain_events() == []


class TestPredictionOperations:
    def test_should_make_prediction_and_emit_event(self, prediction):
        prediction.make_prediction(2, 1, confidence=0.85, model_version="v1")

        assert prediction.score.predicted_home == 2
        assert float(prediction.confidence.value) == pytest.approx(0.85, rel=1e-3)
        assert prediction.model_version == "v1"

        events = prediction.get_domain_events()
        assert len(events) == 1
        created_event = events[0]
        assert created_event.predicted_home == 2
        assert created_event.predicted_away == 1
        assert created_event.confidence == pytest.approx(0.85)

    def test_should_reject_make_prediction_when_not_pending(self, prediction):
        prediction.status = PredictionStatus.EVALUATED
        with pytest.raises(DomainError):
            prediction.make_prediction(1, 0)

    def test_should_evaluate_prediction_with_points_and_event(self, prediction):
        prediction.make_prediction(2, 1, confidence=0.9)
        prediction.evaluate(actual_home=2, actual_away=1)

        assert prediction.is_evaluated is True
        assert prediction.score.actual_away == 1
        assert prediction.points.total == Decimal("14.00")
        assert prediction.accuracy_score == pytest.approx(1.0)

        events = prediction.get_domain_events()
        evaluated_event = events[-1]
        assert evaluated_event.actual_home == 2
        assert evaluated_event.actual_away == 1
        assert evaluated_event.is_correct is True
        assert evaluated_event.points_earned == 14

    def test_should_not_evaluate_when_status_invalid(self, prediction):
        with pytest.raises(DomainError):
            prediction.evaluate(1, 0)

        prediction.make_prediction(1, 0)
        prediction.status = PredictionStatus.CANCELLED
        with pytest.raises(DomainError):
            prediction.evaluate(1, 0)

    def test_should_cancel_and_expire(self, prediction):
        prediction.cancel("user request")
        assert prediction.is_cancelled is True
        assert prediction.cancellation_reason == "user request"

        with pytest.raises(DomainError):
            prediction.cancel("again")

        fresh_prediction = Prediction(user_id=3, match_id=4)
        fresh_prediction.mark_expired()
        assert fresh_prediction.is_expired is True


class TestPredictionValueObjects:
    def test_prediction_score_validation(self):
        score = PredictionScore(predicted_home=2, predicted_away=1)
        assert score.is_evaluated is False
        assert score.is_correct_result is False

        score.actual_home = 2
        score.actual_away = 1
        assert score.is_correct_score is True
        assert score.goal_difference_error == 0

        with pytest.raises(DomainError):
            PredictionScore(predicted_home=-1, predicted_away=0)

    def test_confidence_score_bounds(self):
        confidence = ConfidenceScore(Decimal("0.755"))
        assert confidence.value == Decimal("0.76")
        assert confidence.level == "medium"

        with pytest.raises(DomainError):
            ConfidenceScore(Decimal("1.5"))

    def test_prediction_points_quantization(self):
        points = PredictionPoints(
            total=Decimal("10.555"),
            score_bonus=Decimal("5.123"),
            result_bonus=Decimal("3.456"),
            confidence_bonus=Decimal("2.789"),
        )
        assert points.total == Decimal("10.56")
        assert points.breakdown["score_bonus"] == Decimal("5.12")


class TestPredictionSummary:
    def test_should_return_no_prediction_when_score_missing(self, prediction):
        assert prediction.get_prediction_summary() == {"status": "no_prediction"}

    def test_should_provide_summary_after_evaluation(self, prediction):
        prediction.make_prediction(1, 0, confidence=0.7)
        prediction.evaluate(actual_home=0, actual_away=1)

        summary = prediction.get_prediction_summary()
        assert summary["predicted"] == "1-0"
        assert summary["actual"] == "0-1"
        assert summary["is_correct_result"] is False
