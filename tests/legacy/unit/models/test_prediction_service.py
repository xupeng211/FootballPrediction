from datetime import datetime

from src.models.prediction_service import PredictionResult, PredictionService
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import numpy
import pytest
import os

"""
测试预测服务模块
"""

class TestPredictionResult:
    """测试PredictionResult数据类"""
    def test_prediction_result_creation(self):
        """测试预测结果创建"""
        result = PredictionResult(
        match_id=1,
        model_version="v1.0[",": home_win_probability=0.5,": draw_probability=0.3,": away_win_probability=0.2,"
            predicted_result = os.getenv("TEST_PREDICTION_SERVICE_PREDICTED_RESULT_19"),": confidence_score=0.5)": assert result.match_id ==1[" assert result.model_version =="]]v1.0[" assert result.home_win_probability ==0.5[""""
    assert result.predicted_result =="]]home[" def test_prediction_result_to_dict("
    """"
        "]""测试预测结果转换为字典"""
        created_at = datetime.now()
        result = PredictionResult(
        match_id=1, model_version="v1.0[", created_at=created_at[""""
        )
        result_dict = result.to_dict()
    assert result_dict["]]match_id["] ==1[" assert result_dict["]]model_version["] =="]v1.0[" assert result_dict["]created_at["] ==created_at.isoformat()" def test_prediction_result_to_dict_none_dates(self):"""
        "]""测试预测结果转换为字典（日期为None）"""
        result = PredictionResult(match_id=1, model_version="v1.0[")": result_dict = result.to_dict()": assert result_dict["]created_at["] is None[" assert result_dict["]]verified_at["] is None[""""
class TestPredictionService:
    "]]""测试预测服务"""
    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        with patch("src.models.prediction_service.DatabaseManager[") as mock:": yield mock.return_value["""
    @pytest.fixture
    def mock_feature_store(self):
        "]]""模拟特征存储"""
        with patch("src.models.prediction_service.FootballFeatureStore[") as mock:": yield mock.return_value["""
    @pytest.fixture
    def mock_metrics_exporter(self):
        "]]""模拟指标导出器"""
        with patch("src.models.prediction_service.ModelMetricsExporter[") as mock:": yield mock.return_value["""
    @pytest.fixture
    def prediction_service(
        self, mock_db_manager, mock_feature_store, mock_metrics_exporter
    ):
        "]]""创建预测服务实例"""
        with patch("src.models.prediction_service.mlflow.set_tracking_uri["):": service = PredictionService()": return service[": def test_init(self, prediction_service):"
        "]]""测试初始化"""
        from src.cache.ttl_cache import TTLCache
    assert prediction_service.mlflow_tracking_uri =="http_/localhost5002[" assert isinstance(prediction_service.model_cache, TTLCache)""""
    assert isinstance(prediction_service.feature_order, list)
    @pytest.mark.asyncio
    async def test_get_production_model_success(self, prediction_service):
        "]""测试成功获取生产模型"""
        mock_client = Mock()
        mock_version_info = Mock()
        mock_version_info.version = "1[": mock_version_info.current_stage = os.getenv("TEST_PREDICTION_SERVICE_CURRENT_STAGE_60"): mock_client.get_latest_versions.return_value = ["]mock_version_info[": mock_model = Mock()": with patch(:"""
            "]src.models.prediction_service.MlflowClient[", return_value=mock_client[""""
        ), patch(
            "]]src.models.prediction_service.mlflow.sklearn.load_model[",": return_value=mock_model):": model, version = await prediction_service.get_production_model()": assert model ==mock_model"
    assert version =="]1["""""
    @pytest.mark.asyncio
    async def test_get_production_model_from_cache(self, prediction_service):
        "]""测试从缓存获取模型"""
        model_name = os.getenv("TEST_PREDICTION_SERVICE_MODEL_NAME_66"): cache_key = f["]model{model_name}"]: cached_model = Mock()": cached_version = "1["""""
        # 使用正确的缓存键设置缓存
        await prediction_service.model_cache.set(
        cache_key, (cached_model, cached_version)
        )
        mock_client = Mock()
        mock_version_info = Mock()
        mock_version_info.version = "]1[": mock_client.get_latest_versions.return_value = ["]mock_version_info[": with patch(:""""
            "]src.models.prediction_service.MlflowClient[", return_value=mock_client[""""
        ):
            model, version = await prediction_service.get_production_model()
    assert model ==cached_model
    assert version ==cached_version
    @pytest.mark.asyncio
    async def test_get_production_model_staging_fallback(self, prediction_service):
        "]]""测试回退到Staging版本"""
        mock_client = Mock()
        mock_version_info = Mock()
        mock_version_info.version = "1[": mock_version_info.current_stage = os.getenv("TEST_PREDICTION_SERVICE_CURRENT_STAGE_84")""""
        # 第一次调用返回空（没有Production版本）
        # 第二次调用返回Staging版本
        mock_client.get_latest_versions.side_effect = [[], "]mock_version_info[": mock_model = Mock()": with patch(:"""
            "]src.models.prediction_service.MlflowClient[", return_value=mock_client[""""
        ), patch(
            "]]src.models.prediction_service.mlflow.sklearn.load_model[",": return_value=mock_model):": model, version = await prediction_service.get_production_model()": assert model ==mock_model"
    assert version =="]1["""""
    @pytest.mark.asyncio
    async def test_get_production_model_no_versions(self, prediction_service):
        "]""测试没有可用版本的情况"""
        mock_client = Mock()
        mock_client.get_latest_versions.return_value = []
        with patch(:
            "src.models.prediction_service.MlflowClient[", return_value=mock_client[""""
        ):
            with pytest.raises(:
                ValueError, match = os.getenv("TEST_PREDICTION_SERVICE_MATCH_100")""""
            ):
                await prediction_service.get_production_model()
    @pytest.mark.asyncio
    async def test_get_production_model_updates_cache_and_metadata(
        self, prediction_service
    ):
        "]""测试成功加载模型时缓存与元数据会被更新"""
        prediction_service.model_cache.get = AsyncMock(return_value=None)
        prediction_service.model_cache.set = AsyncMock()
        mock_model = Mock()
        mock_version = "2[": with patch.object(:": prediction_service,"""
            "]get_production_model_with_retry[",": new=AsyncMock(return_value=(mock_model, mock_version))):": model, version = await prediction_service.get_production_model("]custom[")": assert model is mock_model[" assert version ==mock_version[""
        prediction_service.model_cache.set.assert_awaited_once_with(
        "]]]model:custom[",""""
        (mock_model, mock_version),
        ttl=prediction_service.model_cache_ttl)
        metadata = prediction_service.model_metadata_cache["]models_custom/2["]: assert metadata["]name["] =="]custom[" assert metadata["]version["] ==mock_version[" assert metadata["]]stage["] =="]unknown[" assert "]loaded_at[" in metadata[""""
    @pytest.mark.asyncio
    async def test_get_production_model_failure_bubbles_up(self, prediction_service):
        "]]""测试加载模型失败时异常会继续传播且不会写入缓存"""
        prediction_service.model_cache.get = AsyncMock(return_value=None)
        prediction_service.model_cache.set = AsyncMock()
        with patch.object(:
            prediction_service,
            "get_production_model_with_retry[",": new=AsyncMock(side_effect=RuntimeError("]mlflow down["))):": with pytest.raises(RuntimeError, match = os.getenv("TEST_PREDICTION_SERVICE_MATCH_127"))": await prediction_service.get_production_model("]unstable[")": prediction_service.model_cache.set.assert_not_awaited()": assert "]models_unstable[" not in prediction_service.model_metadata_cache[""""
    def test_get_default_features(self, prediction_service):
        "]]""测试获取默认特征"""
        features = prediction_service._get_default_features()
    assert isinstance(features, dict)
    assert "home_recent_wins[" in features[""""
    assert "]]away_recent_wins[" in features[""""
    assert features["]]home_recent_wins["] ==2[" def test_prepare_features_for_prediction(self, prediction_service):"""
        "]]""测试准备预测特征"""
        features = {
        "home_recent_wins[": 3,""""
        "]home_recent_goals_for[": 8,""""
        "]home_recent_goals_against[": 2,""""
        "]away_recent_wins[": 1,""""
            "]away_recent_goals_for[": 4,""""
            "]away_recent_goals_against[": 6,""""
            "]h2h_home_advantage[": 0.6,""""
            "]home_implied_probability[": 0.5,""""
            "]draw_implied_probability[": 0.25,""""
            "]away_implied_probability[": 0.25}": features_array = prediction_service._prepare_features_for_prediction(features)": assert isinstance(features_array, np.ndarray)" assert features_array.shape ==(1, 10)"
    assert features_array[0][0] ==3.0  # home_recent_wins
    def test_prepare_features_missing_values(self, prediction_service):
        "]""测试缺失特征值的处理"""
        features = {"home_recent_wins[": 3}  # 只有部分特征[": features_array = prediction_service._prepare_features_for_prediction(features)": assert isinstance(features_array, np.ndarray)" assert features_array.shape ==(1, 10)"
    assert features_array[0][0] ==3.0  # home_recent_wins
    assert features_array[0][1] ==0.0  # 缺失的特征默认为0
    def test_calculate_actual_result(self, prediction_service):
        "]]""测试计算实际比赛结果"""
    assert prediction_service._calculate_actual_result(2, 1) =="home[" assert prediction_service._calculate_actual_result(1, 2) =="]away[" assert prediction_service._calculate_actual_result(1, 1) =="]draw["""""
    @pytest.mark.asyncio
    async def test_get_match_info_success(self, prediction_service, mock_db_manager):
        "]""测试成功获取比赛信息"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
        )
        mock_result = Mock()
        mock_match = Mock()
        mock_match.id = 1
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime.now()
        mock_match.match_status = os.getenv("TEST_PREDICTION_SERVICE_MATCH_STATUS_166"): mock_match.season = os.getenv("TEST_PREDICTION_SERVICE_SEASON_167"): mock_result.first.return_value = mock_match[": mock_session.execute.return_value = mock_result[": match_info = await prediction_service._get_match_info(1)": assert match_info is not None"
    assert match_info["]]]id["] ==1[" assert match_info["]]home_team_id["] ==10[" assert match_info["]]away_team_id["] ==20[""""
    @pytest.mark.asyncio
    async def test_get_match_info_not_found(self, prediction_service, mock_db_manager):
        "]]""测试比赛不存在的情况"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
        )
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result
        match_info = await prediction_service._get_match_info(999)
    assert match_info is None
    @pytest.mark.asyncio
    async def test_store_prediction_success(self, prediction_service, mock_db_manager):
        """测试成功存储预测结果"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
        )
        result = PredictionResult(
        match_id=1,
        model_version="v1.0[",": home_win_probability=0.5,": draw_probability=0.3,": away_win_probability=0.2,"
            predicted_result = os.getenv("TEST_PREDICTION_SERVICE_PREDICTED_RESULT_19"),": confidence_score=0.5)": await prediction_service._store_prediction(result)": mock_session.add.assert_called_once()"
        mock_session.commit.assert_called_once()
    @pytest.mark.asyncio
    async def test_store_prediction_failure(self, prediction_service, mock_db_manager):
        "]""测试存储预测结果失败"""
        mock_session = AsyncMock()
        mock_session.commit.side_effect = Exception("Database error[")": mock_db_manager.get_async_session.return_value.__aenter__.return_value = (": mock_session[""
        )
        result = PredictionResult(match_id=1, model_version = os.getenv("TEST_PREDICTION_SERVICE_MODEL_VERSION_198"))": with pytest.raises(Exception, match = os.getenv("TEST_PREDICTION_SERVICE_MATCH_199"))": await prediction_service._store_prediction(result)": mock_session.rollback.assert_called_once()""
    @pytest.mark.asyncio
    async def test_predict_match_success(
        self, prediction_service, mock_feature_store, mock_metrics_exporter
    ):
        "]""测试成功预测比赛"""
        # Mock模型
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array(
        [[0.2, 0.3, 0.5]]
        )  # ["away[", draw, home]": mock_model.predict.return_value = np.array("]home[")""""
        # Mock获取生产模型
        match_info = {"]id[": 1, "]home_team_id[": 10, "]away_team_id[" 20}": with patch.object(:": prediction_service,""
            "]get_production_model[",": return_value=(mock_model, "]v1.0[")), patch.object(": prediction_service, "]_get_match_info[", return_value=match_info[""""
        ), patch.object(
            prediction_service, "]]_store_prediction[", new_callable=AsyncMock[""""
        ), patch.object(
            prediction_service.metrics_exporter,
            "]]export_prediction_metrics[",": new_callable=AsyncMock):"""
            # Mock特征存储
            features = {
            "]home_recent_wins[": 3,""""
            "]home_recent_goals_for[": 8,""""
            "]home_recent_goals_against[": 2,""""
            "]away_recent_wins[": 1,""""
                "]away_recent_goals_for[": 4,""""
                "]away_recent_goals_against[": 6,""""
                "]h2h_home_advantage[": 0.6,""""
                "]home_implied_probability[": 0.5,""""
                "]draw_implied_probability[": 0.25,""""
                "]away_implied_probability[": 0.25}": mock_feature_store.get_match_features_for_prediction = AsyncMock(": return_value=features[""
            )
            result = await prediction_service.predict_match(1)
    assert result.match_id ==1
    assert result.predicted_result =="]]home[" assert result.confidence_score ==0.5[""""
    assert result.home_win_probability ==0.5
    @pytest.mark.asyncio
    async def test_predict_match_no_features(
        self, prediction_service, mock_feature_store, mock_metrics_exporter
    ):
        "]]""测试无特征时使用默认特征预测"""
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.3, 0.4, 0.3]])
        mock_model.predict.return_value = np.array("draw[")": match_info = {"]id[": 1, "]home_team_id[": 10, "]away_team_id[" 20}": with patch.object(:": prediction_service,""
            "]get_production_model[",": return_value=(mock_model, "]v1.0[")), patch.object(": prediction_service, "]_get_match_info[", return_value=match_info[""""
        ), patch.object(
            prediction_service, "]]_store_prediction[", new_callable=AsyncMock[""""
        ), patch.object(
            prediction_service.metrics_exporter,
            "]]export_prediction_metrics[",": new_callable=AsyncMock):"""
            # 返回空特征
            mock_feature_store.get_match_features_for_prediction = AsyncMock(
            return_value=None
            )
            result = await prediction_service.predict_match(1)
    assert result.match_id ==1
    assert result.predicted_result =="]draw["""""
    @pytest.mark.asyncio
    async def test_predict_match_no_match(self, prediction_service):
        "]""测试比赛不存在的情况"""
        with patch.object(:
            prediction_service, "get_production_model[", return_value=(Mock(), "]v1.0[")""""
        ), patch.object(prediction_service, "]_get_match_info[", return_value = None)": with pytest.raises(ValueError, match = os.getenv("TEST_PREDICTION_SERVICE_MATCH_259"))": await prediction_service.predict_match(999)"""
    @pytest.mark.asyncio
    async def test_verify_prediction_success(self, prediction_service, mock_db_manager):
        "]""测试成功验证预测结果"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
        )
        # Mock比赛结果查询
        mock_match_result = Mock()
        mock_match = Mock()
        mock_match.id = 1
        mock_match.home_score = 2
        mock_match.away_score = 1
        mock_match.match_status = os.getenv("TEST_PREDICTION_SERVICE_MATCH_STATUS_267"): mock_match_result.first.return_value = mock_match[": mock_session.execute.side_effect = ["]]mock_match_result[", Mock()]": result = await prediction_service.verify_prediction(1)": assert result is True[" assert mock_session.execute.call_count ==2"
        mock_session.commit.assert_called_once()
    @pytest.mark.asyncio
    async def test_verify_prediction_match_not_completed(
        self, prediction_service, mock_db_manager
    ):
        "]]""测试比赛未完成的情况"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
        )
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result
        result = await prediction_service.verify_prediction(1)
    assert result is False
    @pytest.mark.asyncio
    async def test_get_model_accuracy_success(
        self, prediction_service, mock_db_manager
    ):
        """测试成功获取模型准确率"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
        )
        mock_result = Mock()
        mock_row = Mock()
        mock_row.total = 10
        mock_row.correct = 8
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result
        accuracy = await prediction_service.get_model_accuracy()
    assert accuracy ==0.8
    @pytest.mark.asyncio
    async def test_get_model_accuracy_no_data(
        self, prediction_service, mock_db_manager
    ):
        """测试无数据时获取模型准确率"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
        )
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result
        accuracy = await prediction_service.get_model_accuracy()
    assert accuracy is None
    @pytest.mark.asyncio
    async def test_batch_predict_matches_success(self, prediction_service):
        """测试批量预测成功"""
        match_ids = [1, 2, 3]
        # Mock predict_match to return a dummy result
        async def predict_match_side_effect(match_id):
        return PredictionResult(match_id=match_id, model_version="v1.0[")": with patch.object(:": prediction_service, "]get_production_model[", return_value=(Mock(), "]v1.0[")""""
        ):
            with patch.object(:
                prediction_service,
                "]predict_match[",": side_effect=predict_match_side_effect):": results = await prediction_service.batch_predict_matches(match_ids)": assert len(results) ==3"
    assert [r.match_id for r in results] ==[1, 2, 3]
        # The mock is on the instance, so it's called inside the loop, not on the service itself directly.
        # We can't easily assert call count here without more complex mocking.
    @pytest.mark.asyncio
    async def test_batch_predict_matches_with_failures(self, prediction_service):
        "]""测试批量预测中部分失败的情况"""
        match_ids = [1, 99, 3]  # 99 will fail
        async def predict_match_side_effect(match_id):
        if match_id ==99
        raise ValueError("Prediction failed[")": return PredictionResult(match_id=match_id, model_version = os.getenv("TEST_PREDICTION_SERVICE_MODEL_VERSION_338"))": with patch.object(:": prediction_service, "]get_production_model[", return_value=(Mock(), "]v1.0[")""""
        ):
            with patch.object(:
                prediction_service,
                "]predict_match[",": side_effect=predict_match_side_effect):": results = await prediction_service.batch_predict_matches(match_ids)": assert len(results) ==2"
    assert [r.match_id for r in results] ==[1, 3]
    @pytest.mark.asyncio
    async def test_get_prediction_statistics_success(
        self, prediction_service, mock_db_manager
    ):
        "]""测试成功获取预测统计信息"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
        )
        mock_result = MagicMock()
        mock_row = Mock()
        mock_row.model_version = "v1.0[": mock_row.total_predictions = 100[": mock_row.avg_confidence = 0.75[": mock_row.home_predictions = 50[": mock_row.draw_predictions = 30"
        mock_row.away_predictions = 20
        mock_row.correct_predictions = 70
        mock_row.verified_predictions = 90
        # Make the mock result iterable
        mock_result.__iter__.return_value = ["]]]]mock_row[": mock_session.execute.return_value = mock_result[": stats = await prediction_service.get_prediction_statistics()": assert stats["]]period_days["] ==30[" assert len(stats["]]statistics["]) ==1[" stat_item = stats["]]statistics["][0]": assert stat_item["]model_version["] =="]v1.0[" assert stat_item["]total_predictions["] ==100[" assert stat_item["]]accuracy["] ==70 / 90[""""
    @pytest.mark.asyncio
    async def test_get_prediction_statistics_no_data(
        self, prediction_service, mock_db_manager
    ):
        "]]""测试无数据时获取预测统计信息"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
        )
        mock_result = MagicMock()
        mock_result.__iter__.return_value = []  # Empty result
        mock_session.execute.return_value = mock_result
        stats = await prediction_service.get_prediction_statistics()
    assert stats["statistics["] ==[]"]" from src.cache.ttl_cache import TTLCache