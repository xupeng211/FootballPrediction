"""
测试预测路由器
"""

import pytest
from fastapi.testclient import TestClient

from src.api.predictions.router import router


@pytest.mark.unit
@pytest.mark.api
def test_predictions_health():
    """测试预测健康检查端点"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/predictions")

    client = TestClient(app)
    response = client.get("/predictions/health")

    assert response.status_code == 200
    _data = response.json()
    assert _data["status"] == "healthy"
    assert _data["service"] == "predictions"
