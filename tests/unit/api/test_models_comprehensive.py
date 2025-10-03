"""
模型API端点测试 / Tests for Models API Endpoints

测试覆盖：
- 获取当前活跃模型
- 获取模型性能指标
- 模型版本管理
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.models import router


class TestModelsAPI:
    """模型API测试类"""

    @pytest.fixture
    def mock_registered_model(self):
        """模拟注册模型"""
        model = MagicMock()
        model.name = "football_prediction_v1"
        model.description = "足球预测模型"
        model.creation_timestamp = datetime.now()
        model.last_updated_timestamp = datetime.now()
        return model

    @pytest.fixture
    def mock_model_version(self):
        """模拟模型版本"""
        version = MagicMock()
        version.name = "football_prediction_v1"
        version.version = "3"
        version.creation_timestamp = datetime.now()
        version.last_updated_timestamp = datetime.now()
        version.description = "模型版本3"
        version.tags = {"stage": "Production"}
        version.run_id = "run_123"
        return version

    @pytest.mark.asyncio
    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_success(self, mock_client):
        """测试成功获取活跃模型"""
        # 设置模拟
        mock_client.search_registered_models.return_value = [mock_registered_model()]
        mock_client.get_latest_versions.return_value = [mock_model_version()]

        # 执行测试
        from src.api.models import get_active_models
        response = await get_active_models()

        # 验证结果
        assert response["success"] is True
        assert "active_models" in response["data"]
        assert len(response["data"]["active_models"]) > 0

    @pytest.mark.asyncio
    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_no_models(self, mock_client):
        """测试没有注册模型的情况"""
        # 设置模拟
        mock_client.search_registered_models.return_value = []

        # 执行测试
        from src.api.models import get_active_models
        response = await get_active_models()

        # 验证结果
        assert response["success"] is True
        assert response["data"]["active_models"] == []

    @pytest.mark.asyncio
    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_mlflow_error(self, mock_client):
        """测试MLflow服务错误"""
        from src.api.models import get_active_models
        from fastapi import HTTPException

        # 设置模拟
        mock_client.search_registered_models.side_effect = Exception("Connection failed")

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await get_active_models()

        assert exc_info.value.status_code == 500
        assert "获取活跃模型失败" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_runtime_error(self, mock_client):
        """测试MLflow运行时错误"""
        from src.api.models import get_active_models
        from fastapi import HTTPException

        # 设置模拟
        mock_client.search_registered_models.return_value = [mock_registered_model()]
        mock_client.get_latest_versions.side_effect = RuntimeError("Service unavailable")

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await get_active_models()

        assert exc_info.value.status_code == 500
        assert "MLflow服务错误" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_with_staging_version(self, mock_client):
        """测试使用Staging版本的情况"""
        from src.api.models import get_active_models

        # 设置模拟
        mock_client.search_registered_models.return_value = [mock_registered_model()]
        # 第一次返回空的生产版本列表，第二次返回Staging版本
        mock_client.get_latest_versions.side_effect = [
            [],  # 没有生产版本
            [mock_model_version()]  # 有Staging版本
        ]

        # 执行测试
        response = await get_active_models()

        # 验证结果
        assert response["success"] is True
        assert "active_models" in response["data"]

    @pytest.mark.asyncio
    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_no_versions(self, mock_client):
        """测试没有版本的情况"""
        from src.api.models import get_active_models

        # 设置模拟
        mock_client.search_registered_models.return_value = [mock_registered_model()]
        mock_client.get_latest_versions.return_value = []  # 没有任何版本

        # 执行测试
        response = await get_active_models()

        # 验证结果
        assert response["success"] is True
        assert "active_models" in response["data"]

    @pytest.mark.asyncio
    @patch('src.api.models.mlflow_client')
    async def test_get_active_models_multiple_models(self, mock_client):
        """测试多个模型的情况"""
        from src.api.models import get_active_models

        # 设置模拟
        model1 = mock_registered_model()
        model1.name = "model_1"
        model2 = mock_registered_model()
        model2.name = "model_2"

        mock_client.search_registered_models.return_value = [model1, model2]
        mock_client.get_latest_versions.return_value = [mock_model_version()]

        # 执行测试
        response = await get_active_models()

        # 验证结果
        assert response["success"] is True
        assert len(response["data"]["active_models"]) == 2