"""
测试模块化的模型API
Test Modular Models API

验证拆分后的模型API模块功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.models.active import get_active_models
from src.api.models.metrics import get_model_metrics
from src.api.models.versions import get_model_versions, promote_model_version
from src.api.models.performance import get_model_performance
from src.api.models.experiments import get_experiments
from src.api.models.endpoints import router
from src.api.models.model_info import get_model_info as get_module_model_info


@pytest.mark.unit
class TestModelsModular:
    """测试模块化的模型API"""

    @pytest.fixture
    def mock_mlflow_client(self):
        """模拟MLflow客户端"""
        client = MagicMock()
        return client

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_active_models_modular(self, mock_mlflow_client):
        """测试获取活跃模型模块"""
        # 模拟返回数据
        mock_model = MagicMock()
        mock_model.name = "test_model"
        mock_version = MagicMock()
        mock_version.version = "1"
        mock_version.current_stage = "Production"
        mock_version.creation_timestamp = 1234567890
        mock_version.last_updated_timestamp = 1234567890
        mock_version.description = "Test model"
        mock_version.tags = {}
        mock_version.status = "READY"
        mock_version.user_id = "user1"
        mock_version.run_id = "run123"

        mock_mlflow_client.search_registered_models.return_value = [mock_model]
        mock_mlflow_client.get_latest_versions.return_value = [mock_version]
        mock_mlflow_client.get_model_version.return_value = mock_version

        mock_run = MagicMock()
        mock_run.info.run_id = "run123"
        mock_run.info.experiment_id = "exp123"
        mock_run.info.status = "FINISHED"
        mock_run.info.start_time = 1234567890
        mock_run.info.end_time = 1234567900
        mock_run.data.metrics = {"accuracy": 0.85}
        mock_run.data.params = {"learning_rate": 0.001}
        mock_run.data.tags = {"version": "1.0"}

        mock_mlflow_client.get_run.return_value = mock_run

        # 调用模块化函数
        result = await get_active_models(mock_mlflow_client)

        # 验证结果
        assert result["success"] is True
        assert "data" in result
        assert "models" in result["data"]
        assert len(result["data"]["models"]) == 1
        assert result["data"]["models"][0]["name"] == "test_model"
        assert result["data"]["models"][0]["version"] == "1"

    @pytest.mark.asyncio
    async def test_get_model_metrics_modular(self, mock_mlflow_client, mock_session):
        """测试获取模型指标模块"""
        # 模拟查询结果
        mock_row = MagicMock()
        mock_row.model_version = "1"
        mock_row.total_predictions = 100
        mock_row.avg_confidence = 0.85
        mock_row.accuracy = 0.82
        mock_row.home_predictions = 40
        mock_row.draw_predictions = 30
        mock_row.away_predictions = 30
        mock_row.verified_predictions = 90
        mock_row.correct_predictions = 74
        mock_row.first_prediction = None
        mock_row.last_prediction = None

        mock_session.execute.return_value.fetchall.return_value = [mock_row]

        # 模拟趋势数据
        mock_trend_row = MagicMock()
        mock_trend_row.prediction_date = "2024-01-01"
        mock_trend_row.daily_predictions = 10
        mock_trend_row.daily_avg_confidence = 0.85
        mock_session.execute.return_value.__aiter__.return_value = [mock_trend_row]

        # 调用模块化函数
        with patch('src.api.models.metrics.text'):
            result = await get_model_metrics("test_model", "7d", mock_session)

        # 验证结果
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["model_name"] == "test_model"
        assert result["data"]["time_window"] == "7d"

    @pytest.mark.asyncio
    async def test_get_model_versions_modular(self, mock_mlflow_client):
        """测试获取模型版本模块"""
        # 模拟版本数据
        mock_version = MagicMock()
        mock_version.version = "1"
        mock_version.creation_timestamp = 1234567890
        mock_version.last_updated_timestamp = 1234567890
        mock_version.description = "Test version"
        mock_version.user_id = "user1"
        mock_version.current_stage = "Production"
        mock_version.source = "path/to/model"
        mock_version.tags = {}
        mock_version.status = "READY"
        mock_version.run_id = "run123"

        mock_mlflow_client.search_model_versions.return_value = [mock_version]

        mock_run = MagicMock()
        mock_run.info.run_id = "run123"
        mock_run.info.start_time = 1234567890
        mock_run.info.end_time = 1234567900
        mock_run.info.status = "FINISHED"
        mock_run.data.metrics = {"accuracy": 0.85}

        mock_mlflow_client.get_run.return_value = mock_run

        # 调用模块化函数
        result = await get_model_versions("test_model", 20, mock_mlflow_client)

        # 验证结果
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["model_name"] == "test_model"
        assert result["data"]["total_versions"] == 1
        assert result["data"]["versions"][0]["version"] == "1"

    @pytest.mark.asyncio
    async def test_promote_model_version_modular(self, mock_mlflow_client):
        """测试推广模型版本模块"""
        # 模拟版本数据
        mock_old_version = MagicMock()
        mock_old_version.current_stage = "Staging"

        mock_new_version = MagicMock()
        mock_new_version.current_stage = "Production"

        mock_mlflow_client.get_model_version.return_value = mock_old_version
        mock_mlflow_client.transition_model_version_stage.return_value = None
        # 第二次调用应该返回更新后的版本
        mock_mlflow_client.get_model_version.side_effect = [mock_old_version, mock_new_version]

        # 调用模块化函数
        result = await promote_model_version(
            "test_model", "1", "Production", mock_mlflow_client
        )

        # 验证结果
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["model_name"] == "test_model"
        assert result["data"]["version"] == "1"
        assert result["data"]["current_stage"] == "Production"

    @pytest.mark.asyncio
    async def test_get_model_performance_modular(
        self, mock_mlflow_client, mock_session
    ):
        """测试获取模型性能模块"""
        # 模拟版本数据
        mock_version = MagicMock()
        mock_version.current_stage = "Production"
        mock_version.creation_timestamp = 1234567890
        mock_version.description = "Test model"
        mock_version.tags = {}
        mock_version.run_id = "run123"

        mock_mlflow_client.get_latest_versions.return_value = [mock_version]
        mock_mlflow_client.get_model_version.return_value = mock_version

        mock_run = MagicMock()
        mock_run.info.run_id = "run123"
        mock_run.info.experiment_id = "exp123"
        mock_run.data.metrics = {"accuracy": 0.85}
        mock_run.data.params = {"learning_rate": 0.001}
        mock_run.data.tags = {}

        mock_mlflow_client.get_run.return_value = mock_run

        # 模拟性能统计
        mock_stats = MagicMock()
        mock_stats.total_predictions = 100
        mock_stats.verified_predictions = 90
        mock_stats.correct_predictions = 74
        mock_stats.avg_confidence = 0.85
        mock_stats.home_correct = 30
        mock_stats.draw_correct = 22
        mock_stats.away_correct = 22
        mock_stats.home_total = 40
        mock_stats.draw_total = 30
        mock_stats.away_total = 30
        mock_stats.overall_accuracy = 0.8222
        mock_stats.home_accuracy = 0.75
        mock_stats.draw_accuracy = 0.7333
        mock_stats.away_accuracy = 0.7333

        # 创建一个模拟的Result对象
        mock_result = MagicMock()
        mock_result.first.return_value = mock_stats

        # 正确设置异步模拟
        mock_session.execute.return_value = mock_result

        # 调用模块化函数
        with patch('src.api.models.performance.text'):
            result = await get_model_performance(
                "test_model", "1", mock_session, mock_mlflow_client
            )

        # 验证结果
        assert result["success"] is True
        assert "data" in result
        assert "model_info" in result["data"]
        assert "training_info" in result["data"]
        assert "prediction_performance" in result["data"]

    @pytest.mark.asyncio
    async def test_get_experiments_modular(self, mock_mlflow_client):
        """测试获取实验列表模块"""
        # 模拟实验数据
        mock_experiment = MagicMock()
        mock_experiment.experiment_id = "exp123"
        mock_experiment.name = "test_experiment"
        mock_experiment.artifact_location = "path/to/artifacts"
        mock_experiment.lifecycle_stage = "Active"
        mock_experiment.creation_time = 1234567890
        mock_experiment.last_update_time = 1234567900
        mock_experiment.tags = {}

        mock_mlflow_client.search_experiments.return_value = [mock_experiment]

        # 调用模块化函数
        result = await get_experiments(20, mock_mlflow_client)

        # 验证结果
        assert result["success"] is True
        assert "data" in result
        assert "experiments" in result["data"]
        assert "count" in result["data"]
        assert len(result["data"]["experiments"]) == 1
        assert result["data"]["experiments"][0]["name"] == "test_experiment"

    def test_model_info_modular(self):
        """测试模型信息模块"""
        # 调用模块化函数
        result = get_module_model_info()

        # 验证结果
        assert isinstance(result, dict)
        assert "api" in result
        assert "prefix" in result
        assert "tags" in result
        assert "prediction_service" in result
        assert result["prefix"] == "/models"
        assert result["tags"] == ["models"]

    def test_router_existence(self):
        """测试路由器存在"""
        # 验证路由器已创建
        assert router is not None
        assert hasattr(router, "routes")
        assert len(router.routes) > 0

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 测试从主模块导入
        from src.api.models import get_model_info as main_get_model_info
        from src.api.models import router as main_router
        from src.api.models import mlflow_client as main_mlflow_client
        from src.api.models import prediction_service as main_prediction_service

        # 验证所有导入都成功
        assert main_get_model_info is not None
        assert main_router is not None
        assert main_mlflow_client is not None
        assert main_prediction_service is not None

        # 验证功能正常
        result = main_get_model_info()
        assert isinstance(result, dict)
        assert "api" in result