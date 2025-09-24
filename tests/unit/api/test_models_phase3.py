"""
Phase 3：模型API接口综合测试
目标：全面提升models.py模块覆盖率到14%+
重点：测试所有模型管理API端点、MLflow集成、错误处理和性能指标查询
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest


class MockAsyncResult:
    """Mock for SQLAlchemy async result with proper scalars().all() support"""

    def __init__(self, scalars_result=None, scalar_one_or_none_result=None):
        self._scalars_result = scalars_result or []
        self._scalar_one_or_none_result = scalar_one_or_none_result

    def scalars(self):
        return MockScalarResult(self._scalars_result)

    def scalar_one_or_none(self):
        return self._scalar_one_or_none_result


class MockScalarResult:
    """Mock for SQLAlchemy scalars() result"""

    def __init__(self, result):
        self._result = result if isinstance(result, list) else [result]

    def all(self):
        return self._result

    def first(self):
        return self._result[0] if self._result else None


from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models import (
    get_active_models,
    get_experiments,
    get_model_metrics,
    get_model_performance,
    get_model_versions,
    promote_model_version,
)


class TestModelsAPIActiveModels:
    """模型API活跃模型测试"""

    @pytest.mark.asyncio
    async def test_get_active_models_success(self):
        """测试成功获取活跃模型"""
        with patch("src.api.models.mlflow_client") as mock_client:
            # Mock registered models
            mock_registered_model = Mock()
            mock_registered_model.name = "football_baseline_model"

            mock_client.search_registered_models.return_value = [mock_registered_model]

            # Mock model versions
            mock_version = Mock()
            mock_version.version = "1"
            mock_version.current_stage = "Production"
            mock_version.creation_timestamp = 1634567890
            mock_version.last_updated_timestamp = 1634567890
            mock_version.description = "Test model"
            mock_version.tags = {}
            mock_version.status = "READY"
            mock_version.user_id = "test_user"

            mock_client.get_latest_versions.return_value = [mock_version]

            # Mock model details
            mock_model_details = Mock()
            mock_model_details.run_id = "test_run_id"

            mock_client.get_model_version.return_value = mock_model_details

            # Mock run info
            mock_run = Mock()
            mock_run.info.run_id = "test_run_id"
            mock_run.info.experiment_id = "1"
            mock_run.info.status = "FINISHED"
            mock_run.info.start_time = 1634567890
            mock_run.info.end_time = 1634567990
            mock_run.data.metrics = {"accuracy": 0.85}
            mock_run.data.params = {"learning_rate": 0.01}

            mock_client.get_run.return_value = mock_run

            result = await get_active_models()

            assert result["success"] is True
            assert "models" in result["data"]
            assert "active_models" in result["data"]
            assert result["data"]["count"] == 1
            assert result["data"]["mlflow_tracking_uri"] == "http://localhost:5002"

            # Verify MLflow client calls
            mock_client.search_registered_models.assert_called_once()
            mock_client.get_latest_versions.assert_called()

    @pytest.mark.asyncio
    async def test_get_active_models_mlflow_connection_error(self):
        """测试MLflow连接错误"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_registered_models.side_effect = Exception(
                "Connection failed"
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_active_models()

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == {"error": "获取活跃模型失败"}

    @pytest.mark.asyncio
    async def test_get_active_models_runtime_error(self):
        """测试MLflow运行时错误"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_registered_model = Mock()
            mock_registered_model.name = "football_baseline_model"

            mock_client.search_registered_models.return_value = [mock_registered_model]
            mock_client.get_latest_versions.side_effect = RuntimeError(
                "MLflow service unavailable"
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_active_models()

            assert exc_info.value.status_code == 500
            assert "MLflow服务错误" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_get_active_models_no_models(self):
        """测试没有注册模型的情况"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_registered_models.return_value = []

            result = await get_active_models()

            assert result["success"] is True
            assert result["data"]["count"] == 0
            assert result["data"]["models"] == []

    @pytest.mark.asyncio
    async def test_get_active_models_model_version_error(self):
        """测试获取模型版本时的错误处理"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_registered_model = Mock()
            mock_registered_model.name = "football_baseline_model"

            mock_client.search_registered_models.return_value = [mock_registered_model]
            mock_client.get_latest_versions.side_effect = RuntimeError("Version error")

            with pytest.raises(HTTPException) as exc_info:
                await get_active_models()

            assert exc_info.value.status_code == 500
            assert "MLflow服务错误" in exc_info.value.detail["error"]


class TestModelsAPIMetrics:
    """模型API性能指标测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_get_model_metrics_success(self):
        """测试成功获取模型指标"""
        mock_row = Mock()
        mock_row.model_version = "1"
        mock_row.total_predictions = 100
        mock_row.avg_confidence = 0.85
        mock_row.accuracy = 0.82
        mock_row.home_predictions = 40
        mock_row.draw_predictions = 30
        mock_row.away_predictions = 30
        mock_row.verified_predictions = 80
        mock_row.correct_predictions = 66
        mock_row.first_prediction = datetime.now() - timedelta(days=1)
        mock_row.last_prediction = datetime.now()

        async def mock_execute(query, params):
            result = Mock()
            if "metrics_query" in str(query):
                result.all.return_value = [mock_row]
            else:
                trend_row = Mock()
                trend_row.prediction_date = datetime.now().date()
                trend_row.daily_predictions = 10
                trend_row.daily_avg_confidence = 0.85
                result.all.return_value = [trend_row]
            return result

        self.mock_session.execute = mock_execute

        result = await get_model_metrics(
            model_name="football_baseline_model",
            time_window="7d",
            session=self.mock_session,
        )

        assert result["success"] is True
        assert result["data"]["model_name"] == "football_baseline_model"
        assert result["data"]["time_window"] == "7d"
        assert "overall_statistics" in result["data"]
        assert "metrics_by_version" in result["data"]
        assert "daily_trends" in result["data"]

    @pytest.mark.asyncio
    async def test_get_model_metrics_invalid_time_window(self):
        """测试无效时间窗口"""
        with pytest.raises(HTTPException) as exc_info:
            await get_model_metrics(
                model_name="football_baseline_model",
                time_window="invalid",
                session=self.mock_session,
            )

        assert exc_info.value.status_code == 400
        assert "无效的时间窗口" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_get_model_metrics_database_error(self):
        """测试数据库错误"""
        self.mock_session.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_model_metrics(
                model_name="football_baseline_model",
                time_window="7d",
                session=self.mock_session,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {"error": "获取模型指标失败"}

    @pytest.mark.asyncio
    async def test_get_model_metrics_different_time_windows(self):
        """测试不同时间窗口"""
        mock_row = Mock()
        mock_row.model_version = "1"
        mock_row.total_predictions = 100
        mock_row.avg_confidence = 0.85
        mock_row.accuracy = 0.82
        mock_row.home_predictions = 40
        mock_row.draw_predictions = 30
        mock_row.away_predictions = 30
        mock_row.verified_predictions = 80
        mock_row.correct_predictions = 66
        mock_row.first_prediction = datetime.now() - timedelta(days=1)
        mock_row.last_prediction = datetime.now()

        async def mock_execute(query, params):
            result = Mock()
            if "metrics_query" in str(query):
                result.all.return_value = [mock_row]
            else:
                trend_row = Mock()
                trend_row.prediction_date = datetime.now().date()
                trend_row.daily_predictions = 10
                trend_row.daily_avg_confidence = 0.85
                result.all.return_value = [trend_row]
            return result

        self.mock_session.execute = mock_execute

        # Test 1d window
        result = await get_model_metrics(
            model_name="football_baseline_model",
            time_window="1d",
            session=self.mock_session,
        )
        assert result["success"] is True

        # Test 7d window
        result = await get_model_metrics(
            model_name="football_baseline_model",
            time_window="7d",
            session=self.mock_session,
        )
        assert result["success"] is True

        # Test 30d window
        result = await get_model_metrics(
            model_name="football_baseline_model",
            time_window="30d",
            session=self.mock_session,
        )
        assert result["success"] is True


class TestModelsAPIVersions:
    """模型API版本管理测试"""

    @pytest.mark.asyncio
    async def test_get_model_versions_success(self):
        """测试成功获取模型版本"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_version = Mock()
            mock_version.version = "1"
            mock_version.creation_timestamp = 1634567890
            mock_version.last_updated_timestamp = 1634567890
            mock_version.description = "Test version"
            mock_version.user_id = "test_user"
            mock_version.current_stage = "Production"
            mock_version.source = "/path/to/model"
            mock_version.tags = {}
            mock_version.status = "READY"
            mock_version.run_id = "test_run_id"

            mock_client.search_model_versions.return_value = [mock_version]

            # Mock run info
            mock_run = Mock()
            mock_run.info.run_id = "test_run_id"
            mock_run.info.start_time = 1634567890
            mock_run.info.end_time = 1634567990
            mock_run.info.status = "FINISHED"
            mock_run.data.metrics = {"accuracy": 0.85}

            mock_client.get_run.return_value = mock_run

            result = await get_model_versions(
                model_name="football_baseline_model", limit=10
            )

            assert result["success"] is True
            assert result["data"]["model_name"] == "football_baseline_model"
            assert result["data"]["total_versions"] == 1
            assert len(result["data"]["versions"]) == 1

            version_info = result["data"]["versions"][0]
            assert version_info["version"] == "1"
            assert version_info["stage"] == "Production"
            assert "run_info" in version_info

    @pytest.mark.asyncio
    async def test_get_model_versions_no_versions(self):
        """测试没有模型版本的情况"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_model_versions.return_value = []

            result = await get_model_versions(model_name="nonexistent_model", limit=10)

            assert result["success"] is True
            assert result["data"]["total_versions"] == 0
            assert result["data"]["versions"] == []

    @pytest.mark.asyncio
    async def test_get_model_versions_mlflow_error(self):
        """测试MLflow错误"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_model_versions.side_effect = Exception("MLflow error")

            with pytest.raises(HTTPException) as exc_info:
                await get_model_versions(model_name="football_baseline_model", limit=10)

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == {"error": "获取模型版本失败"}

    @pytest.mark.asyncio
    async def test_get_model_versions_limit_validation(self):
        """测试版本数量限制验证"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_model_versions.return_value = []

            # Test minimum limit
            result = await get_model_versions(
                model_name="football_baseline_model", limit=1
            )
            assert result["success"] is True

            # Test maximum limit
            result = await get_model_versions(
                model_name="football_baseline_model", limit=100
            )
            assert result["success"] is True


class TestModelsAPIPromotion:
    """模型API版本推广测试"""

    @pytest.mark.asyncio
    async def test_promote_model_version_success(self):
        """测试成功推广模型版本"""
        with patch("src.api.models.mlflow_client") as mock_client:
            # Mock existing model version
            mock_existing_version = Mock()
            mock_existing_version.current_stage = "Staging"

            # Mock updated model version
            mock_updated_version = Mock()
            mock_updated_version.current_stage = "Production"

            mock_client.get_model_version.return_value = mock_existing_version
            mock_client.transition_model_version_stage.return_value = None

            # Return updated version after promotion
            def mock_get_model_version_side_effect(name, version):
                if mock_client.get_model_version.call_count > 1:
                    return mock_updated_version
                return mock_existing_version

            mock_client.get_model_version.side_effect = (
                mock_get_model_version_side_effect
            )

            result = await promote_model_version(
                model_name="football_baseline_model",
                version="1",
                target_stage="Production",
            )

            assert result["success"] is True
            assert result["data"]["model_name"] == "football_baseline_model"
            assert result["data"]["version"] == "1"
            assert result["data"]["previous_stage"] == "Staging"
            assert result["data"]["current_stage"] == "Production"
            assert "promoted_at" in result["data"]

            # Verify MLflow calls
            mock_client.get_model_version.assert_called()
            mock_client.transition_model_version_stage.assert_called_once_with(
                name="football_baseline_model",
                version="1",
                stage="Production",
                archive_existing_versions=True,
            )

    @pytest.mark.asyncio
    async def test_promote_model_version_invalid_target_stage(self):
        """测试无效目标阶段"""
        with pytest.raises(HTTPException) as exc_info:
            await promote_model_version(
                model_name="football_baseline_model",
                version="1",
                target_stage="Invalid",
            )

        assert exc_info.value.status_code == 400
        assert "目标阶段必须是 Staging 或 Production" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_promote_model_version_not_found(self):
        """测试模型版本不存在"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.get_model_version.side_effect = Exception(
                "Model version not found"
            )

            with pytest.raises(HTTPException) as exc_info:
                await promote_model_version(
                    model_name="football_baseline_model",
                    version="999",
                    target_stage="Production",
                )

            assert exc_info.value.status_code == 404
            assert "模型版本不存在" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_promote_model_version_mlflow_error(self):
        """测试MLflow错误"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_version = Mock()
            mock_version.current_stage = "Staging"

            mock_client.get_model_version.return_value = mock_version
            mock_client.transition_model_version_stage.side_effect = Exception(
                "MLflow error"
            )

            with pytest.raises(HTTPException) as exc_info:
                await promote_model_version(
                    model_name="football_baseline_model",
                    version="1",
                    target_stage="Production",
                )

            assert exc_info.value.status_code == 500
            assert "推广模型版本失败" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_promote_model_version_to_staging(self):
        """测试推广到Staging阶段"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_existing_version = Mock()
            mock_existing_version.current_stage = "None"

            mock_updated_version = Mock()
            mock_updated_version.current_stage = "Staging"

            def mock_get_model_version_side_effect(name, version):
                if mock_client.get_model_version.call_count > 1:
                    return mock_updated_version
                return mock_existing_version

            mock_client.get_model_version.side_effect = (
                mock_get_model_version_side_effect
            )
            mock_client.transition_model_version_stage.return_value = None

            result = await promote_model_version(
                model_name="football_baseline_model",
                version="1",
                target_stage="Staging",
            )

            assert result["success"] is True
            assert result["data"]["current_stage"] == "Staging"

            # Verify archive_existing_versions is False for Staging
            mock_client.transition_model_version_stage.assert_called_once_with(
                name="football_baseline_model",
                version="1",
                stage="Staging",
                archive_existing_versions=False,
            )


class TestModelsAPIPerformance:
    """模型API性能分析测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_get_model_performance_success(self):
        """测试成功获取模型性能"""
        with patch("src.api.models.mlflow_client") as mock_client:
            # Mock production version
            mock_production_version = Mock()
            mock_production_version.version = "1"

            mock_client.get_latest_versions.return_value = [mock_production_version]

            # Mock model version details
            mock_model_version = Mock()
            mock_model_version.current_stage = "Production"
            mock_model_version.creation_timestamp = 1634567890
            mock_model_version.description = "Test model"
            mock_model_version.tags = {}
            mock_model_version.run_id = "test_run_id"

            mock_client.get_model_version.return_value = mock_model_version

            # Mock run info
            mock_run = Mock()
            mock_run.info.run_id = "test_run_id"
            mock_run.info.experiment_id = "1"
            mock_run.data.metrics = {"accuracy": 0.85}
            mock_run.data.params = {"learning_rate": 0.01}
            mock_run.data.tags = {"version": "1"}

            mock_client.get_run.return_value = mock_run

            # Mock performance stats
            mock_stats = Mock()
            mock_stats.total_predictions = 100
            mock_stats.verified_predictions = 80
            mock_stats.correct_predictions = 66
            mock_stats.avg_confidence = 0.85
            mock_stats.overall_accuracy = 0.825
            mock_stats.home_accuracy = 0.80
            mock_stats.draw_accuracy = 0.85
            mock_stats.away_accuracy = 0.85
            mock_stats.home_correct = 32
            mock_stats.draw_correct = 17
            mock_stats.away_correct = 17
            mock_stats.home_total = 40
            mock_stats.draw_total = 20
            mock_stats.away_total = 40

            async def mock_execute(query, params):
                result = Mock()
                result.first.return_value = mock_stats
                return result

            self.mock_session.execute = mock_execute

            result = await get_model_performance(
                model_name="football_baseline_model", session=self.mock_session
            )

            assert result["success"] is True
            assert "model_info" in result["data"]
            assert "training_info" in result["data"]
            assert "prediction_performance" in result["data"]

            model_info = result["data"]["model_info"]
            assert model_info["name"] == "football_baseline_model"
            assert model_info["version"] is not None
            assert model_info["stage"] == "Production"

            performance = result["data"]["prediction_performance"]
            assert performance["total_predictions"] == 100
            assert performance["verified_predictions"] == 80
            assert performance["correct_predictions"] == 66
            assert performance["overall_accuracy"] == 0.825

    @pytest.mark.asyncio
    async def test_get_model_performance_with_version(self):
        """测试指定版本的模型性能"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_model_version = Mock()
            mock_model_version.current_stage = "Production"
            mock_model_version.creation_timestamp = 1634567890
            mock_model_version.description = "Test model"
            mock_model_version.tags = {}
            mock_model_version.run_id = "test_run_id"

            mock_client.get_model_version.return_value = mock_model_version

            mock_run = Mock()
            mock_run.info.run_id = "test_run_id"
            mock_run.info.experiment_id = "1"
            mock_run.data.metrics = {"accuracy": 0.85}
            mock_run.data.params = {"learning_rate": 0.01}
            mock_run.data.tags = {"version": "1"}

            mock_client.get_run.return_value = mock_run

            mock_stats = Mock()
            mock_stats.total_predictions = 50
            mock_stats.verified_predictions = 40
            mock_stats.correct_predictions = 33
            mock_stats.avg_confidence = 0.85
            mock_stats.overall_accuracy = 0.825

            async def mock_execute(query, params):
                result = Mock()
                result.first.return_value = mock_stats
                return result

            self.mock_session.execute = mock_execute

            result = await get_model_performance(
                model_name="football_baseline_model",
                version="1",
                session=self.mock_session,
            )

            assert result["success"] is True
            assert result["data"]["model_info"]["version"] == "1"

    @pytest.mark.asyncio
    async def test_get_model_performance_no_production_version(self):
        """测试没有生产版本"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.get_latest_versions.return_value = []

            with pytest.raises(HTTPException) as exc_info:
                await get_model_performance(
                    model_name="football_baseline_model", session=self.mock_session
                )

            assert exc_info.value.status_code == 404
            assert "模型没有生产版本" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_get_model_performance_model_not_found(self):
        """测试模型不存在"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.get_latest_versions.side_effect = Exception("Model not found")

            with pytest.raises(HTTPException) as exc_info:
                await get_model_performance(
                    model_name="nonexistent_model", session=self.mock_session
                )

            assert exc_info.value.status_code == 404
            assert "无法获取模型生产版本" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_get_model_performance_version_not_found(self):
        """测试指定版本不存在"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.get_model_version.side_effect = Exception(
                "RESOURCE_DOES_NOT_EXIST"
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_model_performance(
                    model_name="football_baseline_model",
                    version="999",
                    session=self.mock_session,
                )

            assert exc_info.value.status_code == 404
            assert "模型不存在" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_get_model_performance_database_error(self):
        """测试数据库错误"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_production_version = Mock()
            mock_production_version.version = "1"

            mock_client.get_latest_versions.return_value = [mock_production_version]

            mock_model_version = Mock()
            mock_model_version.current_stage = "Production"
            mock_model_version.run_id = "test_run_id"

            mock_client.get_model_version.return_value = mock_model_version

            self.mock_session.execute.side_effect = Exception("Database error")

            with pytest.raises(HTTPException) as exc_info:
                await get_model_performance(
                    model_name="football_baseline_model", session=self.mock_session
                )

            assert exc_info.value.status_code == 500
            assert "获取模型性能分析失败" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_get_model_performance_no_predictions(self):
        """测试没有预测记录的情况"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_production_version = Mock()
            mock_production_version.version = "1"

            mock_client.get_latest_versions.return_value = [mock_production_version]

            mock_model_version = Mock()
            mock_model_version.current_stage = "Production"
            mock_model_version.creation_timestamp = 1634567890
            mock_model_version.description = "Test model"
            mock_model_version.tags = {}
            mock_model_version.run_id = None

            mock_client.get_model_version.return_value = mock_model_version

            async def mock_execute(query, params):
                result = Mock()
                result.first.return_value = None
                return result

            self.mock_session.execute = mock_execute

            result = await get_model_performance(
                model_name="football_baseline_model", session=self.mock_session
            )

            assert result["success"] is True
            performance = result["data"]["prediction_performance"]
            assert performance["total_predictions"] == 0
            assert performance["verified_predictions"] == 0
            assert performance["correct_predictions"] == 0
            assert performance["overall_accuracy"] is None


class TestModelsAPIExperiments:
    """模型API实验管理测试"""

    @pytest.mark.asyncio
    async def test_get_experiments_success(self):
        """测试成功获取实验列表"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_experiment = Mock()
            mock_experiment.experiment_id = "1"
            mock_experiment.name = "football_experiment"
            mock_experiment.artifact_location = "/path/to/artifacts"
            mock_experiment.lifecycle_stage = "active"
            mock_experiment.creation_time = 1634567890
            mock_experiment.last_update_time = 1634567990
            mock_experiment.tags = {"version": "1"}

            mock_client.search_experiments.return_value = [mock_experiment]

            result = await get_experiments(limit=10)

            assert result["success"] is True
            assert "experiments" in result["data"]
            assert "count" in result["data"]
            assert result["data"]["count"] == 1

            experiment = result["data"]["experiments"][0]
            assert experiment["experiment_id"] == "1"
            assert experiment["name"] == "football_experiment"
            assert experiment["lifecycle_stage"] == "active"
            assert experiment["tags"]["version"] == "1"

    @pytest.mark.asyncio
    async def test_get_experiments_no_experiments(self):
        """测试没有实验的情况"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_experiments.return_value = []

            result = await get_experiments(limit=10)

            assert result["success"] is True
            assert result["data"]["count"] == 0
            assert result["data"]["experiments"] == []

    @pytest.mark.asyncio
    async def test_get_experiments_mlflow_error(self):
        """测试MLflow错误"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_experiments.side_effect = Exception("MLflow error")

            with pytest.raises(HTTPException) as exc_info:
                await get_experiments(limit=10)

            assert exc_info.value.status_code == 500
            assert "获取实验列表失败" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_get_experiments_limit_validation(self):
        """测试实验数量限制验证"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_experiments.return_value = []

            # Test minimum limit
            result = await get_experiments(limit=1)
            assert result["success"] is True

            # Test maximum limit
            result = await get_experiments(limit=100)
            assert result["success"] is True


class TestModelsAPIIntegration:
    """模型API集成测试"""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求"""
        import asyncio

        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_registered_models.return_value = []

            # Test concurrent requests
            tasks = []
            for i in range(3):
                task = get_active_models()
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All requests should succeed
            assert all(not isinstance(r, Exception) for r in results)
            assert all(r["success"] is True for r in results)

    @pytest.mark.asyncio
    async def test_response_structure_consistency(self):
        """测试响应结构一致性"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_registered_models.return_value = []

            result = await get_active_models()

            # Check response structure
            assert "success" in result
            assert "data" in result
            assert "message" in result
            assert "models" in result["data"]
            assert "active_models" in result["data"]
            assert "count" in result["data"]
            assert "mlflow_tracking_uri" in result["data"]

    @pytest.mark.asyncio
    async def test_error_response_consistency(self):
        """测试错误响应一致性"""
        with patch("src.api.models.mlflow_client") as mock_client:
            mock_client.search_registered_models.side_effect = Exception(
                "Connection failed"
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_active_models()

            # Check error response format
            assert "error" in exc_info.value.detail
            assert isinstance(exc_info.value.detail["error"], str)

    @pytest.mark.asyncio
    async def test_mlflow_service_integration(self):
        """测试MLflow服务集成"""
        with patch("src.api.models.mlflow_client") as mock_client:
            # Test multiple MLflow operations
            mock_registered_model = Mock()
            mock_registered_model.name = "football_baseline_model"

            mock_client.search_registered_models.return_value = [mock_registered_model]
            mock_client.get_latest_versions.return_value = []

            result = await get_active_models()

            # Verify MLflow client was called
            mock_client.search_registered_models.assert_called_once()
            mock_client.get_latest_versions.assert_called_once()

            assert result["success"] is True
