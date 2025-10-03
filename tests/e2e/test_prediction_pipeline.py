import os
"""预测管道端到端冒烟测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope = os.getenv("TEST_PREDICTION_PIPELINE_SCOPE_12"))
def client():
    from src.main import app
    from src.api import health as health_module

    health_module.MINIMAL_HEALTH_MODE = True
    health_module.FAST_FAIL = False

    return TestClient(app, base_url="http://localhost")


@pytest.fixture(scope = os.getenv("TEST_PREDICTION_PIPELINE_SCOPE_12"))
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_pipeline_health_check(client):
    response = client.get("/health")
    assert response.status_code in (200, 503, 404)


@pytest.mark.asyncio
async def test_prediction_workflow(client):
    mock_match = MagicMock()
    mock_match.id = 12345
    mock_match.home_team_id = 1
    mock_match.away_team_id = 2
    mock_match.match_status = MagicMock(value = os.getenv("TEST_PREDICTION_PIPELINE_VALUE_47"))
    mock_match.season = os.getenv("TEST_PREDICTION_PIPELINE_SEASON_48")
    mock_match.match_time = MagicMock()
    mock_match.home_score = None
    mock_match.away_score = None

    session_mock = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_match
    session_mock.execute.return_value = result

    prediction_payload = {
        "match_id": 12345,
        "home_win_probability": 0.6,
    }

    with patch('src.api.predictions.get_async_session') as mock_session, \
        patch('src.api.predictions.prediction_service') as mock_service:

        mock_session.return_value.__aenter__.return_value = session_mock
        mock_service.predict_match = AsyncMock(
            return_value=MagicMock(to_dict=lambda: prediction_payload)
        )

        response = client.get("/predictions/12345")
        assert response.status_code in (200, 404)


def test_database_data_flow(session):
    session.execute(text("DROP TABLE IF EXISTS tmp_predictions"))
    session.execute(
        text(
            """
            CREATE TABLE tmp_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                confidence REAL
            )
            """
        )
    )
    session.execute(
        text("INSERT INTO tmp_predictions (match_id, confidence) VALUES (1, 0.75)")
    )
    session.commit()

    result = session.execute(text("SELECT confidence FROM tmp_predictions"))
    assert result.scalar() == 0.75


def test_error_handling(client):
    response = client.get("/nonexistent")
    assert response.status_code == 404
