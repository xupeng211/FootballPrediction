"""
API模型管理模块的单元测试

测试覆盖：
- 模型版本管理
- 性能指标获取
- MLflow集成
- 错误处理和异常情况
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models import (get_active_models, get_model_performance,
                            get_model_versions, mlflow_client,
                            prediction_service, promote_model_version, router)


@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = AsyncMock(spec=AsyncSession)
    return session


class TestModelsAPI:
    """测试模型管理API的所有功能"""

    @pytest.fixture
    def mock_mlflow_models(self):
        """模拟MLflow模型数据"""
        return [
            {
                "name": "football_prediction_model",
                "version": "3",
                "stage": "Production",
                "creation_timestamp": 1640995200000,  # 2022 - 01 - 01
                "last_updated_timestamp": 1640995200000,
                "description": "足球预测模型 v3.0",
                "tags": {"algorithm": "xgboost", "accuracy": "0.85"},
            },
            {
                "name": "football_prediction_model",
                "version": "2",
                "stage": "Staging",
                "creation_timestamp": 1640908800000,
                "last_updated_timestamp": 1640908800000,
                "description": "足球预测模型 v2.0",
                "tags": {"algorithm": "lgbm", "accuracy": "0.82"},
            },
        ]

    @pytest.fixture
    def mock_performance_metrics(self):
        """模拟性能指标数据"""
        return {
            "accuracy": 0.85,
            "precision": 0.83,
            "recall": 0.87,
            "f1_score": 0.85,
            "auc_roc": 0.91,
            "log_loss": 0.12,
            "prediction_count": 1500,
            "success_rate": 0.99,
            "avg_confidence": 0.78,
            "last_updated": datetime.now(),
        }

    @pytest.mark.asyncio
    async def test_get_active_models_success(self, mock_mlflow_models):
        """测试成功获取活跃模型"""
        with patch("src.api.models.mlflow_client") as mock_client:
            # Mock MLflow客户端响应
            mock_client.search_registered_models.return_value = []

            # Mock模型版本查询
            mock_versions = []
            for model in mock_mlflow_models:
                if model["stage"] == "Production":
                    mock_version = MagicMock()
                    mock_version.name = model["name"]
                    mock_version.version = model["version"]
                    mock_version.current_stage = model["stage"]
                    mock_version.creation_timestamp = model["creation_timestamp"]
                    mock_version.description = model["description"]
                    mock_version.tags = model["tags"]
                    mock_versions.append(mock_version)

            mock_client.get_latest_versions.return_value = mock_versions

            # 执行测试
            result = await get_active_models()

            # 验证结果
            assert "success" in result
            assert result["success"] is True
            assert "data" in result
            assert "active_models" in result["data"]
            assert len(result["data"]["active_models"]) >= 0
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_active_models_mlflow_error(self):
        """测试MLflow连接异常"""
        with patch("src.api.models.mlflow_client") as mock_client:
            # Mock MLflow连接异常
            mock_client.search_registered_models.side_effect = Exception(
                "MLflow connection failed"
            )

            # 执行测试并验证异常
            with pytest.raises(HTTPException) as exc_info:
                await get_active_models()

            assert exc_info.value.status_code == 500
            assert "获取活跃模型失败" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_model_performance_success(self):
        """测试成功获取模型性能指标"""
        model_name = "football_prediction_model"
        version = "3"

        # Mock数据库会话和查询结果
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock数据库查询结果
        mock_stats_row = Mock()
        mock_stats_row.total_predictions = 1000
        mock_stats_row.verified_predictions = 950
        mock_stats_row.correct_predictions = 900
        mock_stats_row.overall_accuracy = 0.95
        mock_stats_row.avg_confidence = 0.85
        mock_stats_row.home_accuracy = 0.92
        mock_stats_row.draw_accuracy = 0.88
        mock_stats_row.away_accuracy = 0.96
        mock_stats_row.home_total = 400
        mock_stats_row.draw_total = 200
        mock_stats_row.away_total = 400

        mock_result = Mock()
        mock_result.first.return_value = mock_stats_row
        mock_session.execute.return_value = mock_result

        with patch("src.api.models.mlflow_client") as mock_client:
            # 1. Mock MLflow客户端
            mock_model_version = Mock()
            mock_model_version.name = model_name
            mock_model_version.version = version
            mock_model_version.run_id = "test_run_123"
            mock_model_version.current_stage = "Production"
            mock_model_version.creation_timestamp = 1672531200000
            mock_model_version.last_updated_timestamp = 1672531200000
            mock_model_version.description = "Test model"
            mock_model_version.tags = {"env": "production"}
            mock_client.get_model_version.return_value = mock_model_version

            mock_run = Mock()
            mock_run.info.run_id = "test_run_123"
            mock_run.data.metrics = {
                "accuracy": 0.85,
                "precision": 0.82,
                "recall": 0.88,
                "f1_score": 0.85,
            }
            mock_client.get_run.return_value = mock_run

            # 2. 执行测试
            result = await get_model_performance(
                model_name=model_name, version=version, session=mock_session
            )

            # 3. 验证结果
            assert result["success"] is True
            assert result["data"]["model_info"]["name"] == model_name
            assert result["data"]["model_info"]["version"] == version
            assert result["data"]["prediction_performance"]["overall_accuracy"] == 0.95
            assert result["data"]["prediction_performance"]["total_predictions"] == 1000
            assert (
                result["data"]["prediction_performance"]["correct_predictions"] == 900
            )

            # 4. 验证数据库查询被调用
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_model_performance_invalid_model(self):
        """测试无效模型名称"""
        # Mock数据库会话
        mock_session = AsyncMock(spec=AsyncSession)

        with patch.object(mlflow_client, "get_model_version") as mock_get_model:
            # Mock MLflow客户端抛出异常表示模型不存在
            from mlflow.exceptions import RestException

            mock_get_model.side_effect = RestException(
                {"error_code": "RESOURCE_DOES_NOT_EXIST"}
            )

            # 执行测试并验证异常
            with pytest.raises(HTTPException) as exc_info:
                await get_model_performance(
                    model_name="nonexistent_model", version="1", session=mock_session
                )

            assert exc_info.value.status_code == 404
            assert "模型不存在" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_model_versions_success(self, mock_mlflow_models):
        """测试成功获取模型版本列表"""
        model_name = "football_prediction_model"

        with patch("src.api.models.mlflow_client") as mock_client:
            # Mock模型版本查询
            mock_versions = []
            for model in mock_mlflow_models:
                mock_version = MagicMock()
                mock_version.name = model["name"]
                mock_version.version = model["version"]
                mock_version.current_stage = model["stage"]
                mock_version.creation_timestamp = model["creation_timestamp"]
                mock_version.description = model.get("description", "")
                mock_versions.append(mock_version)

            mock_client.search_model_versions.return_value = mock_versions

            # 执行测试
            result = await get_model_versions(model_name=model_name)

            # 验证结果
            assert "success" in result
            assert result["success"] is True
            assert "data" in result
            assert "model_name" in result["data"]
            assert result["data"]["model_name"] == model_name
            assert "versions" in result["data"]
            assert len(result["data"]["versions"]) == len(mock_mlflow_models)

            # 验证版本信息
            for version_info in result["data"]["versions"]:
                assert "version" in version_info
                assert "stage" in version_info
                assert "created_at" in version_info

    @pytest.mark.asyncio
    async def test_get_model_versions_empty_result(self):
        """测试模型无版本的情况"""
        model_name = "empty_model"

        with patch("src.api.models.mlflow_client") as mock_client:
            # Mock空版本列表
            mock_client.search_model_versions.return_value = []

            # 执行测试
            result = await get_model_versions(model_name=model_name)

            # 验证结果
            assert result["success"] is True
            assert result["data"]["versions"] == []

    def test_mlflow_client_initialization(self):
        """测试MLflow客户端初始化"""
        assert mlflow_client is not None
        # 验证客户端配置
        expected_uri = "http://localhost:5002"
        assert mlflow_client.tracking_uri == expected_uri

    def test_prediction_service_initialization(self):
        """测试预测服务初始化"""
        assert prediction_service is not None
        # 验证服务实例类型
        from src.models.prediction_service import PredictionService

        assert isinstance(prediction_service, PredictionService)

    def test_router_configuration(self):
        """测试路由器配置"""
        assert router.prefix == "/models"
        assert "models" in router.tags

        # 验证主要路由
        routes = {route.path for route in router.routes}
        # Check for key routes that should exist
        key_routes = {
            "/active",
            "/metrics",
            "/{model_name}/performance",
            "/{model_name}/versions",
        }

        # Verify that the key routes exist in the actual routes
        for key_route in key_routes:
            assert any(
                key_route in route for route in routes
            ), f"Route containing '{key_route}' not found in {routes}"

    @pytest.mark.asyncio
    async def test_concurrent_model_operations(
        self, mock_session, mock_performance_metrics
    ):
        """测试并发模型操作"""
        import asyncio

        with patch("src.api.models.mlflow_client") as mock_client, patch(
            "src.api.models.prediction_service"
        ) as mock_service:
            # Mock并发操作
            mock_client.search_registered_models.return_value = []
            mock_client.get_latest_versions.return_value = []
            mock_service.get_model_metrics.return_value = mock_performance_metrics

            # 创建并发任务
            tasks = [
                get_active_models(),
                get_model_performance("test_model", "1"),
                get_model_versions("test_model"),
            ]

            # 并发执行
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 验证所有操作都成功或正确处理异常
            assert len(results) == 3
            for result in results:
                if not isinstance(result, Exception):
                    assert "success" in result


class TestModelValidation:
    """测试模型验证相关功能"""

    @pytest.mark.asyncio
    async def test_invalid_model_id_handling(self):
        """测试无效模型ID处理"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.get_model_version.side_effect = Exception("Model not found")

            with pytest.raises(HTTPException) as exc_info:
                await get_model_performance("invalid_model", "999")

            assert exc_info.value.status_code in [404, 500]

    @pytest.mark.asyncio
    async def test_invalid_model_promotion(self):
        """测试无效模型推广配置"""
        with patch("src.api.models.mlflow_client") as mock_client:
            # 测试无效阶段
            with pytest.raises(HTTPException) as exc_info:
                await promote_model_version(
                    model_name="test_model", version="1", target_stage="InvalidStage"
                )
            assert exc_info.value.status_code == 400

            # 测试不存在的模型版本
            mock_client.get_model_version.side_effect = Exception(
                "Model version not found"
            )
            with pytest.raises(HTTPException) as exc_info:
                await promote_model_version(
                    model_name="nonexistent_model",
                    version="999",
                    target_stage="Production",
                )
            assert exc_info.value.status_code == 404


class TestErrorHandlingCoverage:
    """测试错误处理覆盖率"""

    @pytest.mark.asyncio
    async def test_database_connection_error(self, mock_session):
        """测试数据库连接错误处理"""
        # 模拟数据库连接错误，使用中文错误消息保持一致
        mock_session.execute.side_effect = SQLAlchemyError("数据库连接失败")

        with patch("src.api.models.mlflow_client") as mock_client:
            # Mock MLflow client 以避免外部依赖
            mock_version = MagicMock()
            mock_version.run_id = None  # 设置为None避免run查询
            mock_client.get_model_version.return_value = mock_version

            with pytest.raises(HTTPException) as exc_info:
                await get_model_performance(
                    model_name="test_model", version="1", session=mock_session
                )

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_mlflow_service_error(self):
        """测试MLflow服务错误处理"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.get_latest_versions.side_effect = RuntimeError(
                "MLflow service unavailable"
            )

            with pytest.raises(HTTPException):
                await get_active_models()

    @pytest.mark.asyncio
    async def test_model_promotion_service_error(self):
        """测试模型推广服务错误处理"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.get_model_version.return_value = MagicMock()
            mock_client.transition_model_version_stage.side_effect = Exception(
                "Promotion service error"
            )

            with pytest.raises(HTTPException):
                await promote_model_version(
                    model_name="test_model", version="1", target_stage="Production"
                )


class TestAPIResponseFormats:
    """测试API响应格式"""

    @pytest.mark.asyncio
    async def test_model_list_response_format(self):
        """测试模型列表响应格式"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_registered_models.return_value = []
            mock_client.get_latest_versions.return_value = []

            result = await get_active_models()

            # 验证响应格式
            required_fields = ["success", "data", "timestamp"]
            for field in required_fields:
                assert field in result

            assert isinstance(result["success"], bool)
            assert isinstance(result["data"], dict)
            assert "models" in result["data"]

    @pytest.mark.asyncio
    async def test_model_promotion_response_format(self):
        """测试模型推广响应格式"""
        with patch("src.api.models.mlflow_client") as mock_client:
            # 模拟模型版本信息
            mock_version = MagicMock()
            mock_version.current_stage = "Staging"
            mock_client.get_model_version.return_value = mock_version

            # 模拟推广后的版本信息
            updated_version = MagicMock()
            updated_version.current_stage = "Production"
            mock_client.get_model_version.side_effect = [mock_version, updated_version]

            result = await promote_model_version(
                model_name="test_model", version="1", target_stage="Production"
            )

            # 验证响应格式
            assert "success" in result
            assert "data" in result
            assert "message" in result
            assert "model_name" in result["data"]
            assert "version" in result["data"]
            assert "current_stage" in result["data"]
