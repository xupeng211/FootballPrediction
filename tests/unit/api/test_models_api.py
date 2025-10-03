"""
模型API端点测试
测试覆盖src/api/models.py中的所有路由
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi import HTTPException

from src.api.models import router


@pytest.mark.asyncio
class TestActiveModels:
    """测试活跃模型相关端点"""

    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_success(self, mock_client):
        """测试获取活跃模型成功"""
        # 模拟注册模型
        mock_model = MagicMock()
        mock_model.name = "test_model"
        mock_client.search_registered_models.return_value = [mock_model]

        # 模拟模型版本
        mock_version = MagicMock()
        mock_version.version = "1"
        mock_version.run_id = "run_123"
        mock_version.current_stage = "Production"
        mock_client.get_latest_versions.return_value = [mock_version]

        from src.api.models import get_active_models
        result = await get_active_models()

        assert result is not None
        assert "data" in result
        assert result["success"] is True

    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_mlflow_unavailable(self, mock_client):
        """测试MLflow服务不可用"""
        mock_client.search_registered_models.side_effect = Exception("Connection failed")

        from src.api.models import get_active_models

        with pytest.raises(HTTPException) as exc_info:
            await get_active_models()

        assert exc_info.value.status_code == 500
        assert "获取活跃模型失败" in str(exc_info.value.detail)

    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_runtime_error(self, mock_client):
        """测试MLflow运行时错误"""
        # 模拟search_registered_models成功
        mock_client.search_registered_models.return_value = []

        # 模拟健康检查失败
        mock_client.get_latest_versions.side_effect = RuntimeError("MLflow server error")

        from src.api.models import get_active_models

        with pytest.raises(HTTPException) as exc_info:
            await get_active_models()

        assert exc_info.value.status_code == 500
        assert "MLflow服务错误" in str(exc_info.value.detail)

    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_no_models(self, mock_client):
        """测试没有注册模型时"""
        mock_client.search_registered_models.return_value = []
        mock_client.get_latest_versions.side_effect = Exception("Model not found")

        from src.api.models import get_active_models
        result = await get_active_models()

        assert result is not None
        assert result["success"] is True
        assert result["data"]["active_models"] == []


@pytest.mark.asyncio
class TestModelMetrics:
    """测试模型指标相关端点"""

    @patch('src.api.models.mlflow_client')
    async def test_get_model_metrics_success(self, mock_client):
        """测试获取模型指标成功"""
        # 模拟模型存在
        mock_model = MagicMock()
        mock_model.name = "test_model"
        mock_client.get_registered_model.return_value = mock_model

        # 模拟模型版本
        mock_version = MagicMock()
        mock_version.version = "1"
        mock_version.run_id = "run_123"
        mock_client.get_latest_versions.return_value = [mock_version]

        # 模拟运行指标
        mock_run = MagicMock()
        mock_run.info.start_time = datetime.now()
        mock_run.data.metrics = {
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.88
        }
        mock_client.get_run.return_value = mock_run

        from src.api.models import get_model_metrics
        result = await get_model_metrics("test_model")

        assert result is not None
        assert "data" in result
        assert result["success"] is True
        assert "metrics" in result["data"]

    @patch('src.api.models.mlflow_client')
    async def test_get_model_metrics_not_found(self, mock_client):
        """测试获取不存在模型的指标"""
        mock_client.get_registered_model.side_effect = Exception("Model not found")

        from src.api.models import get_model_metrics

        with pytest.raises(HTTPException) as exc_info:
            await get_model_metrics("nonexistent_model")

        assert exc_info.value.status_code == 404

    @patch('src.api.models.mlflow_client')
    async def test_get_model_metrics_no_versions(self, mock_client):
        """测试模型没有版本时"""
        mock_model = MagicMock()
        mock_model.name = "test_model"
        mock_client.get_registered_model.return_value = mock_model
        mock_client.get_latest_versions.return_value = []

        from src.api.models import get_model_metrics

        with pytest.raises(HTTPException) as exc_info:
            await get_model_metrics("test_model")

        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
class TestModelComparison:
    """测试模型比较相关端点"""

    @patch('src.api.models.mlflow_client')
    async def test_compare_models_success(self, mock_client):
        """测试比较模型成功"""
        # 模拟两个模型
        mock_model1 = MagicMock()
        mock_model1.name = "model_v1"
        mock_model2 = MagicMock()
        mock_model2.name = "model_v2"
        mock_client.get_registered_model.side_effect = [mock_model1, mock_model2]

        # 模拟版本和指标
        mock_version = MagicMock()
        mock_version.version = "1"
        mock_version.run_id = "run_123"
        mock_client.get_latest_versions.return_value = [mock_version]

        mock_run = MagicMock()
        mock_run.data.metrics = {"accuracy": 0.85}
        mock_client.get_run.return_value = mock_run

        from src.api.models import compare_models
        result = await compare_models("model_v1", "model_v2")

        assert result is not None
        assert "data" in result
        assert result["success"] is True
        assert "comparison" in result["data"]

    @patch('src.api.models.mlflow_client')
    async def test_compare_models_same_model(self, mock_client):
        """测试比较相同的模型"""
        from src.api.models import compare_models

        with pytest.raises(HTTPException) as exc_info:
            await compare_models("model_v1", "model_v1")

        assert exc_info.value.status_code == 400
        assert "模型名称不能相同" in str(exc_info.value.detail)

    @patch('src.api.models.mlflow_client')
    async def test_compare_models_one_not_found(self, mock_client):
        """测试比较时一个模型不存在"""
        mock_client.get_registered_model.side_effect = [MagicMock(), Exception("Not found")]

        from src.api.models import compare_models

        with pytest.raises(HTTPException) as exc_info:
            await compare_models("model_v1", "nonexistent_model")

        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
class TestModelPromotion:
    """测试模型提升相关端点"""

    @patch('src.api.models.mlflow_client')
    async def test_promote_model_success(self, mock_client):
        """测试提升模型版本成功"""
        # 模拟模型存在
        mock_model = MagicMock()
        mock_model.name = "test_model"
        mock_client.get_registered_model.return_value = mock_model

        # 模拟版本存在
        mock_version = MagicMock()
        mock_version.version = "2"
        mock_version.run_id = "run_456"
        mock_client.get_model_version.return_value = mock_version

        from src.api.models import promote_model
        result = await promote_model("test_model", "2", "Production")

        assert result is not None
        assert "data" in result
        assert result["success"] is True
        mock_client.transition_model_version_stage.assert_called_once()

    @patch('src.api.models.mlflow_client')
    async def test_promote_model_not_found(self, mock_client):
        """测试提升不存在的模型"""
        mock_client.get_registered_model.side_effect = Exception("Model not found")

        from src.api.models import promote_model

        with pytest.raises(HTTPException) as exc_info:
            await promote_model("nonexistent_model", "1", "Production")

        assert exc_info.value.status_code == 404

    @patch('src.api.models.mlflow_client')
    async def test_promote_model_version_not_found(self, mock_client):
        """测试提升不存在的版本"""
        mock_model = MagicMock()
        mock_client.get_registered_model.return_value = mock_model
        mock_client.get_model_version.side_effect = Exception("Version not found")

        from src.api.models import promote_model

        with pytest.raises(HTTPException) as exc_info:
            await promote_model("test_model", "999", "Production")

        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
class TestModelPrediction:
    """测试模型预测相关端点"""

    @patch('src.api.models.prediction_service')
    async def test_predict_with_model_success(self, mock_service):
        """测试使用指定模型预测成功"""
        # 模拟预测服务
        mock_service.predict.return_value = {
            "prediction": 0.75,
            "probabilities": {"home_win": 0.75, "draw": 0.15, "away_win": 0.10},
            "model_version": "v1.2.3"
        }

        from src.api.models import predict_with_model
        result = await predict_with_model(
            model_name="test_model",
            model_version="1",
            features={
                "home_team_form": 0.8,
                "away_team_form": 0.6,
                "head_to_head": {"home_wins": 5, "away_wins": 3}
            }
        )

        assert result is not None
        assert "data" in result
        assert result["success"] is True
        assert "prediction" in result["data"]

    @patch('src.api.models.prediction_service')
    async def test_predict_with_model_invalid_features(self, mock_service):
        """测试使用无效特征预测"""
        from src.api.models import predict_with_model

        with pytest.raises(HTTPException) as exc_info:
            await predict_with_model(
                model_name="test_model",
                model_version="1",
                features={}
            )

        assert exc_info.value.status_code == 400
        assert "特征数据不能为空" in str(exc_info.value.detail)

    @patch('src.api.models.prediction_service')
    async def test_predict_with_model_service_error(self, mock_service):
        """测试预测服务错误"""
        mock_service.predict.side_effect = Exception("Prediction service unavailable")

        from src.api.models import predict_with_model

        with pytest.raises(HTTPException) as exc_info:
            await predict_with_model(
                model_name="test_model",
                model_version="1",
                features={"test": "data"}
            )

        assert exc_info.value.status_code == 500


@pytest.mark.asyncio
class TestModelHealth:
    """测试模型健康检查"""

    @patch('src.api.models.mlflow_client')
    @patch('src.api.models.prediction_service')
    async def test_get_model_health_healthy(self, mock_service, mock_client):
        """测试模型服务健康检查 - 健康"""
        mock_client.search_registered_models.return_value = []
        mock_service.health_check.return_value = {"status": "healthy"}

        from src.api.models import get_model_health
        result = await get_model_health()

        assert result is not None
        assert result["status"] == "healthy"
        assert result["services"]["mlflow"]["status"] == "healthy"
        assert result["services"]["prediction_service"]["status"] == "healthy"

    @patch('src.api.models.mlflow_client')
    @patch('src.api.models.prediction_service')
    async def test_get_model_health_mlflow_down(self, mock_service, mock_client):
        """测试模型服务健康检查 - MLflow不可用"""
        mock_client.search_registered_models.side_effect = Exception("MLflow down")
        mock_service.health_check.return_value = {"status": "healthy"}

        from src.api.models import get_model_health
        result = await get_model_health()

        assert result is not None
        assert result["status"] == "unhealthy"
        assert result["services"]["mlflow"]["status"] == "unhealthy"


@pytest.mark.asyncio
class TestExperiments:
    """测试实验相关端点"""

    @patch('src.api.models.mlflow_client')
    async def test_get_experiments_success(self, mock_client):
        """测试获取实验列表成功"""
        # 模拟实验
        mock_experiment = MagicMock()
        mock_experiment.experiment_id = "123"
        mock_experiment.name = "test_experiment"
        mock_client.list_experiments.return_value = [mock_experiment]

        from src.api.models import get_experiments
        result = await get_experiments()

        assert result is not None
        assert "data" in result
        assert result["success"] is True
        assert len(result["data"]["experiments"]) == 1

    @patch('src.api.models.mlflow_client')
    async def test_get_experiments_with_view_type(self, mock_client):
        """测试按视图类型获取实验"""
        mock_experiment = MagicMock()
        mock_client.list_experiments.return_value = [mock_experiment]

        from src.api.models import get_experiments
        result = await get_experiments(view_type="ACTIVE_ONLY")

        assert result is not None
        assert result["success"] is True
        mock_client.list_experiments.assert_called_with(view_type="ACTIVE_ONLY")


class TestRouterConfiguration:
    """测试路由配置"""

    def test_router_exists(self):
        """测试路由器存在"""
        assert router is not None
        assert hasattr(router, 'routes')

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/models"

    def test_router_tags(self):
        """测试路由标签"""
        assert router.tags == ["models"]

    def test_router_has_endpoints(self):
        """测试路由器有端点"""
        route_count = len(list(router.routes))
        assert route_count > 0

        # 检查关键路径存在
        route_paths = [route.path for route in router.routes]
        expected_paths = [
            "/active",
            "/metrics",
            "/compare",
            "/promote",
            "/predict",
            "/health",
            "/experiments"
        ]

        for path in expected_paths:
            assert any(path in route_path for route_path in route_paths), f"路径 {path} 不存在"


class TestModuleInitialization:
    """测试模块初始化"""

    def test_mlflow_client_initialization(self):
        """测试MLflow客户端初始化"""
        from src.api.models import mlflow_client

        assert mlflow_client is not None
        assert hasattr(mlflow_client, 'search_registered_models')

    def test_prediction_service_initialization(self):
        """测试预测服务初始化"""
        from src.api.models import prediction_service

        assert prediction_service is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])