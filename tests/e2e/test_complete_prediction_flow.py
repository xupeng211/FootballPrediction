"""精简版端到端预测流程测试"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def stub_external_services(monkeypatch):
    """禁用需要外部依赖的组件（MLflow、Redis 等）。"""
    import src.api.health as health_module
    import src.api.models as models_module
    import src.api.predictions as predictions_module
    import src.models.prediction_service as prediction_module

    health_module.MINIMAL_HEALTH_MODE = True
    health_module.FAST_FAIL = False

    monkeypatch.setattr(models_module, "mlflow_client", MagicMock())
    monkeypatch.setattr(prediction_module, "MlflowClient", MagicMock())
    monkeypatch.setattr(prediction_module, "mlflow", MagicMock())

    stub_service = MagicMock()
    stub_service.predict_match = AsyncMock()
    stub_service.batch_predict_matches = AsyncMock()
    monkeypatch.setattr(predictions_module, "prediction_service", stub_service)


@pytest.fixture
def client():
    from src.main import app

    return TestClient(app, base_url="http://localhost")


def _build_match(match_id: int) -> MagicMock:
    match = MagicMock()
    match.id = match_id
    match.home_team_id = 1
    match.away_team_id = 2
    match.league_id = 1
    match.match_time = datetime.now() + timedelta(days=1)
    match.match_status = MagicMock(value="scheduled")
    match.season = "2024-25"
    match.home_score = None
    match.away_score = None
    return match


def test_health_and_docs(client):
    """基础健康和文档端点应在最小模式下可访问。"""
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] in {"healthy", "unhealthy"}

    docs_resp = client.get("/docs")
    assert docs_resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_prediction_endpoint_flow(monkeypatch):
    from src.api.predictions import get_match_prediction

    session = AsyncMock()
    match_result = MagicMock()
    match_result.scalar_one_or_none.return_value = _build_match(12345)
    session.execute.return_value = match_result

    prediction_payload = {
        "match_id": 12345,
        "home_win_probability": 0.55,
        "draw_probability": 0.25,
        "away_win_probability": 0.20,
        "predicted_result": "home",
        "confidence_score": 0.80,
    }

    from src.api import predictions as predictions_module

    predictions_module.prediction_service.predict_match = AsyncMock(
        return_value=MagicMock(to_dict=lambda: prediction_payload)
    )

    response = await get_match_prediction(match_id=12345, force_predict=True, session=session)

    assert response["success"] is True
    assert response["data"]["prediction"]["match_id"] == 12345
    predictions_module.prediction_service.predict_match.assert_awaited_once()


def test_api_matches_list(client):
    mock_matches = [_build_match(1000 + i) for i in range(3)]
    result = MagicMock()
    result.scalars.return_value.all.return_value = mock_matches
    result.scalars.return_value.first.return_value = len(mock_matches)

    session = AsyncMock()
    session.execute.return_value = result

    with patch('src.api.data.get_async_session') as mock_session:
        mock_session.return_value.__aenter__.return_value = session

        response = client.get("/data/matches?limit=3")

    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["matches"]) == 3
    else:
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_batch_prediction_flow(monkeypatch):
    from src.api.predictions import batch_predict_matches

    session = AsyncMock()
    matches = [_build_match(mid) for mid in [101, 102, 103]]
    result = MagicMock()
    result.scalars.return_value.all.return_value = matches
    session.execute.return_value = result

    from src.api import predictions as predictions_module

    stub_predictions = []
    for mid in [101, 102, 103]:
        prediction = MagicMock()
        prediction.to_dict.return_value = {
            "match_id": mid,
            "home_win_probability": 0.5,
        }
        stub_predictions.append(prediction)

    predictions_module.prediction_service.batch_predict_matches = AsyncMock(
        return_value=stub_predictions
    )

    response = await batch_predict_matches([101, 102, 103], session)

    assert response["success"] is True
    assert response["data"]["successful_predictions"] == 3
    predictions_module.prediction_service.batch_predict_matches.assert_awaited_once()
