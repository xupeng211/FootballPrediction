"""
目标性覆盖率提升测试

针对覆盖率报告中未覆盖的代码行，逐一添加测试用例，
目标是将关键模块的覆盖率提升至80%以上。
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest

from src.database.models import Prediction
from src.models.prediction_service import PredictionResult, PredictionService


@pytest.fixture
def service():
    """提供一个 PredictionService 的测试实例"""
    with patch("src.models.prediction_service.DatabaseManager"), patch(
        "src.models.prediction_service.FootballFeatureStore"
    ), patch("src.models.prediction_service.ModelMetricsExporter"), patch(
        "src.models.prediction_service.mlflow"
    ):
        yield PredictionService()


class TestPredictionServiceCoverage:
    """针对 prediction_service.py 的覆盖率提升测试"""

    @pytest.mark.asyncio
    async def test_get_production_model_fallback_and_latest(self, service):
        """测试模型获取逻辑：从 Production -> Staging -> Latest 的回退"""
        mock_client = MagicMock()
        mock_staging_version = Mock()
        mock_staging_version.version = "0.9.0-staging"
        mock_staging_version.current_stage = "Staging"

        mock_latest_version = Mock()
        mock_latest_version.version = "0.8.0-latest"
        mock_latest_version.current_stage = "None"

        # 模拟 Production 无版本，Staging 有版本
        mock_client.get_latest_versions.side_effect = [[], [mock_staging_version]]

        with patch(
            "src.models.prediction_service.MlflowClient", return_value=mock_client
        ), patch(
            "src.models.prediction_service.mlflow.sklearn.load_model",
            return_value=Mock(),
        ):
            model, version = await service.get_production_model("fallback_model")
            assert version == "0.9.0-staging"
            assert mock_client.get_latest_versions.call_count == 2

        # 模拟 Production 和 Staging 均无版本，只有最新版本
        mock_client.get_latest_versions.reset_mock()
        mock_client.get_latest_versions.side_effect = [[], [], [mock_latest_version]]
        with patch(
            "src.models.prediction_service.mlflow.sklearn.load_model",
            return_value=Mock(),
        ):
            model, version = await service.get_production_model("latest_model")
            assert version == "0.8.0-latest"
            assert mock_client.get_latest_versions.call_count == 3

    @pytest.mark.asyncio
    async def test_store_prediction_and_metrics_export(self, service):
        """测试 _store_prediction 和 metrics_exporter 的调用"""
        result = PredictionResult(match_id=1, model_version="1.0")

        mock_session = AsyncMock()
        service.db_manager.get_async_session = MagicMock()
        service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        service.metrics_exporter = AsyncMock()

        await service._store_prediction(result)
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_match_info(self, service):
        """测试 _get_match_info 方法"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        # 模拟 SQLAlchemy 的 Row 对象
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.home_team_id = 10
        mock_row.away_team_id = 11
        mock_row.league_id = 1
        mock_row.match_time = datetime.now()
        mock_row.match_status = "scheduled"
        mock_row.season = "2024"
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        service.db_manager.get_async_session = MagicMock()
        service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        match_info = await service._get_match_info(1)
        assert match_info is not None
        assert match_info["id"] == 1

        # 测试找不到比赛的情况
        mock_result.first.return_value = None
        match_info_none = await service._get_match_info(999)
        assert match_info_none is None

    def test_prepare_features_with_missing_values(self, service):
        """测试 _prepare_features_for_prediction 对缺失值的处理"""
        # 故意缺少一些特征
        features = {"home_team_form": 0.8, "away_goals_avg": 1.2}

        feature_array = service._prepare_features_for_prediction(features)

        assert isinstance(feature_array, np.ndarray)
        assert feature_array.shape == (1, len(service.feature_order))
        # 验证缺失值被填充为 0
        # home_team_form 是第一个特征，应该为 0.8
        assert feature_array[0, 0] == 0.8
        # away_goals_avg 是第五个特征，应该为 1.2
        assert feature_array[0, 4] == 1.2
        # head_to_head_ratio 是第三个特征，缺失，应该为 0
        assert feature_array[0, 2] == 0.0
