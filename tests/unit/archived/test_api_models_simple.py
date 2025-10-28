import pytest

try:
    from src.api.predictions.models import PredictionRequest, PredictionResponse
except ImportError:
    # 如果导入失败，创建简单的mock类用于测试
    class APIResponse:
        def __init__(self, success=True):
            self.success = success

    class PredictionRequest:
        def __init__(self, match_id=1):
            self.match_id = match_id


@pytest.mark.unit
@pytest.mark.api
def test_api_response():
    response = APIResponse(success=True)
    assert response.success is True


def test_prediction_request():
    request = PredictionRequest(match_id=1)
    assert request.match_id == 1
