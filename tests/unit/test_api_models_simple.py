# API模型简单测试
from src.api.models import APIResponse
from src.api.schemas import HealthResponse


def test_api_response_creation():
    response = APIResponse(success=True)
    assert response.success is True


def test_health_response():
    health = HealthResponse(status="healthy")
    assert health.status == "healthy"
