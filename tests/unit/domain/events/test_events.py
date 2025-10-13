from datetime import datetime

from src.domain.events.base import DomainEvent
from src.domain.events.match_events import (
    MatchCancelledEvent,
    MatchFinishedEvent,
    MatchPostponedEvent,
    MatchStartedEvent,
)
from src.domain.events.prediction_events import (
    PredictionCancelledEvent,
    PredictionCreatedEvent,
    PredictionEvaluatedEvent,
    PredictionExpiredEvent,
    PredictionPointsAdjustedEvent,
    PredictionUpdatedEvent,
)
from src.domain.models.match import MatchResult, MatchScore


class DummyEvent(DomainEvent):
    def __init__(self, aggregate_id: int, payload: str):
        super().__init__(aggregate_id)
        self.payload = payload

    def _get_event_data(self):
        return {"payload": self.payload}


class TestBaseEvent:
    def test_should_convert_event_to_dict(self):
        event = DummyEvent(aggregate_id=10, payload="data")
        event_dict = event.to_dict()

        assert event_dict["aggregate_id"] == 10
        assert event_dict["event_type"] == "DummyEvent"
        assert event_dict["data"] == {"payload": "data"}
        assert "occurred_at" in event_dict


class TestMatchEvents:
    def test_match_started_event_data(self):
        event = MatchStartedEvent(match_id=1, home_team_id=2, away_team_id=3)
        _data = event.to_dict()["data"]

        assert data["match_id"] == 1
        assert data["home_team_id"] == 2
        assert data["away_team_id"] == 3

    def test_match_finished_event_data(self):
        score = MatchScore(home_score=2, away_score=1)
        event = MatchFinishedEvent(
            match_id=5,
            home_team_id=1,
            away_team_id=2,
            final_score=score,
            _result =MatchResult.HOME_WIN,
        )

        payload = event.to_dict()["data"]
        assert payload["final_score"]["result"] == MatchResult.HOME_WIN.value
        assert payload["final_score"]["home_score"] == 2
        assert payload["final_score"]["away_score"] == 1

    def test_match_cancelled_and_postponed_events(self):
        cancel_event = MatchCancelledEvent(match_id=9, reason="weather")
        postpone_event = MatchPostponedEvent(
            match_id=9,
            new_date=datetime(2024, 12, 1, 20, 0).isoformat(),
            reason="broadcast",
        )

        assert cancel_event.to_dict()["data"]["reason"] == "weather"
        postpone_data = postpone_event.to_dict()["data"]
        assert postpone_data["new_date"].startswith("2024-12-01")
        assert postpone_data["reason"] == "broadcast"


class TestPredictionEvents:
    def test_prediction_created_event(self):
        event = PredictionCreatedEvent(
            prediction_id=10,
            user_id=1,
            match_id=2,
            predicted_home=2,
            predicted_away=1,
            confidence=0.75,
        )

        _data = event.to_dict()["data"]
        assert data["predicted_home"] == 2
        assert data["confidence"] == 0.75

    def test_prediction_updated_and_cancelled_events(self):
        update_event = PredictionUpdatedEvent(
            prediction_id=11,
            old_predicted_home=1,
            old_predicted_away=0,
            new_predicted_home=2,
            new_predicted_away=1,
        )
        cancel_event = PredictionCancelledEvent(
            prediction_id=11,
            reason="user cancelled",
            cancelled_by=5,
        )

        update_data = update_event.to_dict()["data"]
        assert update_data["new_prediction"]["home"] == 2

        cancel_data = cancel_event.to_dict()["data"]
        assert cancel_data["cancelled_by"] == 5

    def test_prediction_evaluated_and_expired_events(self):
        evaluated_event = PredictionEvaluatedEvent(
            prediction_id=12,
            actual_home=3,
            actual_away=1,
            is_correct=True,
            points_earned=15,
            accuracy_score=0.8,
        )
        expired_event = PredictionExpiredEvent(
            prediction_id=13,
            match_id=4,
            expired_at="2024-01-01T12:00:00Z",
        )

        evaluated_data = evaluated_event.to_dict()["data"]
        assert evaluated_data["actual_score"]["home"] == 3
        assert evaluated_data["points_earned"] == 15

        expired_data = expired_event.to_dict()["data"]
        assert expired_data["expired_at"] == "2024-01-01T12:00:00Z"

    def test_prediction_points_adjusted_event(self):
        event = PredictionPointsAdjustedEvent(
            prediction_id=20,
            user_id=7,
            old_points=10,
            new_points=15,
            adjustment_reason="manual correction",
        )

        _data = event.to_dict()["data"]
        assert data["points_difference"] == 5
        assert data["adjustment_reason"] == "manual correction"
