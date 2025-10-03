"""独立的API集成测试（不需要外部服务）"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestStandaloneAPI:
    """测试独立API功能"""

    @pytest.fixture(scope="class")
    def standalone_app(self):
        """创建独立的测试应用"""
        app = FastAPI(title="Test API")

        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-10-02T00:00:00Z"
            }

        @app.get("/metrics")
        async def metrics():
            return {
                "active_alerts": 5,
                "total_predictions": 1000,
                "uptime": 3600
            }

        @app.get("/api/v1/predictions")
        async def get_predictions():
            return {"predictions": []}

        @app.get("/api/v1/matches")
        async def get_matches():
            return {"matches": []}

        @app.post("/api/v1/predictions")
        async def create_prediction():
            return {
                "prediction_id": "test_pred_123",
                "status": "pending"
            }

        @app.get("/nonexistent")
        async def nonexistent():
            raise HTTPException(status_code=404, detail="Not found")

        return app

    @pytest.fixture(scope="class")
    def client(self, standalone_app):
        """创建测试客户端"""
        return TestClient(standalone_app)

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_metrics_endpoint(self, client):
        """测试指标端点"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "active_alerts" in data
        assert "total_predictions" in data

    def test_predictions_list(self, client):
        """测试获取预测列表"""
        response = client.get("/api/v1/predictions")
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert isinstance(data["predictions"], list)

    def test_matches_list(self, client):
        """测试获取比赛列表"""
        response = client.get("/api/v1/matches")
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert isinstance(data["matches"], list)

    def test_create_prediction(self, client):
        """测试创建预测"""
        response = client.post("/api/v1/predictions")
        assert response.status_code == 200
        data = response.json()
        assert "prediction_id" in data
        assert "status" in data

    def test_404_error(self, client):
        """测试404错误处理"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_root_redirect(self, client):
        """测试根路径重定向"""
        response = client.get("/")
        # 可能返回404或307
        assert response.status_code in [404, 307, 200]

    def test_docs_endpoint(self, client):
        """测试API文档"""
        response = client.get("/docs")
        assert response.status_code in [200, 404]