from datetime import datetime

from prometheus_client import CollectorRegistry
from src.models.prediction_service import PredictionService, PredictionResult
from tests.mocks import (
from unittest.mock import MagicMock, patch
import asyncio
import numpy
import pytest
import os

"""
PredictionService 完整测试套件
目标：100% 覆盖率，覆盖所有业务逻辑、异常处理和边界条件
"""

    MockDatabaseManager,
    MockRedisManager,
    MockMLflowClient,
    MockFeatureStoreImpl)
class TestPredictionServiceComplete:
    """PredictionService 完整测试套件"""
    @pytest.fixture
    def prediction_service(self):
        """创建预测服务实例"""
        return PredictionService(mlflow_tracking_uri = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_MLFLOW_TRACKING_U"))""""
    @pytest.fixture
    def mock_dependencies(self):
        "]""Mock 所有外部依赖"""
        return {
            "database[": MockDatabaseManager()""""
    @pytest.fixture
    def sample_match_data(self):
        "]""示例比赛数据"""
        return {
            "match_id[": 12345,""""
            "]home_team[: "Team A[","]"""
            "]away_team[: "Team B[","]"""
            "]league_id[": 1,""""
            "]season[: "2024[","]"""
            "]match_date[": datetime.now()""""
    @pytest.fixture
    def sample_features(self):
        "]""示例特征数据"""
        return {
            "match_id[": 12345,""""
            "]home_team_form[": 0.8,""""
            "]away_team_form[": 0.6,""""
            "]head_to_head[": {"]home_wins[": 3, "]draws[": 1, "]away_wins[": 1},""""
            "]home_goals_avg[": 2.1,""""
            "]away_goals_avg[": 1.4,""""
            "]home_defense_strength[": 0.7,""""
            "]away_defense_strength[": 0.8,""""
            "]home_attack_strength[": 0.9,""""
            "]away_attack_strength[": 0.6,""""
            # ... 更多特征
        }
    class TestInitialization:
        "]""测试服务初始化"""
        def test_init_with_defaults(self):
            """测试默认参数初始化"""
            service = PredictionService()
            assert service.mlflow_tracking_uri =="http//localhost5002[" assert service.model_cache_ttl.total_seconds() / 3600 ==1  # 1 hour[""""
            assert service.prediction_cache_ttl.total_seconds() / 60 ==30  # 30 minutes
        def test_init_with_custom_params(self):
            "]]""测试自定义参数初始化"""
            service = PredictionService(
                mlflow_tracking_uri = "http://custom5000[",": model_cache_ttl_hours=2,": prediction_cache_ttl_minutes=60,": mlflow_retry_max_attempts=5,"
                mlflow_retry_base_delay=1.0)
            assert service.mlflow_tracking_uri =="]http//custom5000[" assert service.model_cache_ttl_hours ==2[""""
            assert service.prediction_cache_ttl_minutes ==60
            assert service.mlflow_retry_max_attempts ==5
            assert service.mlflow_retry_base_delay ==1.0
        def test_metrics_initialization(self, prediction_service):
            "]]""测试 Prometheus 指标初始化"""
            assert hasattr(prediction_service, "prediction_requests_total[")" assert hasattr(prediction_service, "]prediction_errors_total[")" assert hasattr(prediction_service, "]prediction_duration_seconds[")" assert hasattr(prediction_service, "]model_load_errors_total[")" assert hasattr(prediction_service, "]cache_hits_total[")" class TestModelLoading:"""
        "]""测试模型加载"""
        @pytest.mark.asyncio
        async def test_load_model_from_mlflow_success(
            self, prediction_service, mock_dependencies
        ):
            """测试成功从 MLflow 加载模型"""
            mock_dependencies["mlflow["].get_latest_model_version.return_value = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_RETURN_VALUE_82"): mock_dependencies["]mlflow["].load_model.return_value = mock_dependencies[""""
                "]model["""""
            ]
            with patch("]src.models.prediction_service.MlflowClient[") as mlflow_mock:": mlflow_mock.return_value = mock_dependencies["]mlflow["]: model = await prediction_service._load_model_from_mlflow(""""
                    "]football-predictor["""""
                )
                assert model is not None
                mock_dependencies[
                    "]mlflow["""""
                ].get_latest_model_version.assert_called_once_with("]football-predictor[")": mock_dependencies["]mlflow["].load_model.assert_called_once_with(""""
                    "]football-predictor[", "]1.0.0["""""
                )
        @pytest.mark.asyncio
        async def test_load_model_retry_on_failure(
            self, prediction_service, mock_dependencies
        ):
            "]""测试模型加载失败时的重试机制"""
            mock_dependencies["mlflow["].get_latest_model_version.side_effect = ["]": Exception("Network error["),": Exception("]Network error["),""""
                "]1.0.0["]": mock_dependencies["]mlflow["].load_model.return_value = mock_dependencies[""""
                "]model["""""
            ]
            with patch(:
                "]src.models.prediction_service.MlflowClient["""""
            ) as mlflow_mock, patch("]asyncio.sleep[") as sleep_mock:": mlflow_mock.return_value = mock_dependencies["]mlflow["]: model = await prediction_service._load_model_from_mlflow(""""
                    "]football-predictor["""""
                )
                assert model is not None
                assert (
                    mock_dependencies["]mlflow["].get_latest_model_version.call_count ==3[""""
                )
                assert sleep_mock.call_count ==2
        @pytest.mark.asyncio
        async def test_load_model_max_attempts_exceeded(
            self, prediction_service, mock_dependencies
        ):
            "]]""测试超过最大重试次数"""
            mock_dependencies["mlflow["].get_latest_model_version.side_effect = ("]": Exception("Network error[")""""
            )
            with patch(:
                "]src.models.prediction_service.MlflowClient["""""
            ) as mlflow_mock, patch("]asyncio.sleep[") as sleep_mock:": mlflow_mock.return_value = mock_dependencies["]mlflow["]: with pytest.raises(Exception, match = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_MATCH_122"))": await prediction_service._load_model_from_mlflow("""
                        "]football-predictor["""""
                    )
                assert (
                    mock_dependencies["]mlflow["].get_latest_model_version.call_count ==3[""""
                )
                assert sleep_mock.call_count ==3
        @pytest.mark.asyncio
        async def test_model_cache_functionality(
            self, prediction_service, mock_dependencies
        ):
            "]]""测试模型缓存功能"""
            # 第一次加载
            mock_dependencies["mlflow["].get_latest_model_version.return_value = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_RETURN_VALUE_82"): mock_dependencies["]mlflow["].load_model.return_value = mock_dependencies[""""
                "]model["""""
            ]
            with patch("]src.models.prediction_service.MlflowClient[") as mlflow_mock:": mlflow_mock.return_value = mock_dependencies["]mlflow["]: model1 = await prediction_service._get_cached_model(""""
                    "]football-predictor["""""
                )
                model2 = await prediction_service._get_cached_model(
                    "]football-predictor["""""
                )
                # 验证缓存生效
                assert model1 is model2
                assert (
                    mock_dependencies["]mlflow["].get_latest_model_version.call_count ==1[""""
                )
    class TestFeatureRetrieval:
        "]]""测试特征获取"""
        @pytest.mark.asyncio
        async def test_get_features_success(self, prediction_service, sample_features):
            """测试成功获取特征"""
            with patch.object(:
                prediction_service, "_get_features_from_store["""""
            ) as mock_get_features:
                mock_get_features.return_value = sample_features
                features = await prediction_service._get_features(12345)
                assert features ==sample_features
                mock_get_features.assert_called_once_with(12345)
        @pytest.mark.asyncio
        async def test_get_features_not_found(self, prediction_service):
            "]""测试特征不存在"""
            with patch.object(:
                prediction_service, "_get_features_from_store["""""
            ) as mock_get_features:
                mock_get_features.return_value = None
                features = await prediction_service._get_features(12345)
                assert features is None
        @pytest.mark.asyncio
        async def test_get_features_exception_handling(self, prediction_service):
            "]""测试特征获取异常处理"""
            with patch.object(:
                prediction_service, "_get_features_from_store["""""
            ) as mock_get_features:
                mock_get_features.side_effect = Exception("]Feature store error[")": features = await prediction_service._get_features(12345)": assert features is None[" class TestPredictionLogic:"
        "]]""测试预测逻辑"""
        @pytest.mark.asyncio
        async def test_predict_match_success(
            self, prediction_service, mock_dependencies, sample_features
        ):
            """测试成功预测比赛"""
            # Mock 模型预测
            mock_dependencies["model["].predict.return_value = np.array("]"""
                [[0.6, 0.3, 0.1]]
            )
            with patch.object(:
                prediction_service, "_get_cached_model["""""
            ) as mock_get_model, patch.object(
                prediction_service, "]_get_features["""""
            ) as mock_get_features, patch.object(
                prediction_service, "]_save_prediction_to_db["""""
            ) as mock_save:
                mock_get_model.return_value = mock_dependencies["]model["]: mock_get_features.return_value = sample_features[": result = await prediction_service.predict_match(12345)": assert result is not None[" assert result.match_id ==12345"
                assert result.home_win_probability ==0.6
                assert result.draw_probability ==0.3
                assert result.away_win_probability ==0.1
                assert result.predicted_result =="]]]home[" assert result.confidence_score ==0.6[""""
                mock_save.assert_called_once()
        @pytest.mark.asyncio
        async def test_predict_match_model_not_loaded(self, prediction_service):
            "]]""测试模型未加载的情况"""
            with patch.object(:
                prediction_service, "_get_cached_model["""""
            ) as mock_get_model:
                mock_get_model.return_value = None
                result = await prediction_service.predict_match(12345)
                assert result is None
        @pytest.mark.asyncio
        async def test_predict_match_features_not_found(
            self, prediction_service, mock_dependencies
        ):
            "]""测试特征不存在的情况"""
            mock_dependencies["model["].predict.return_value = np.array("]"""
                [[0.6, 0.3, 0.1]]
            )
            with patch.object(:
                prediction_service, "_get_cached_model["""""
            ) as mock_get_model, patch.object(
                prediction_service, "]_get_features["""""
            ) as mock_get_features:
                mock_get_model.return_value = mock_dependencies["]model["]: mock_get_features.return_value = None[": result = await prediction_service.predict_match(12345)": assert result is None[""
        @pytest.mark.asyncio
        async def test_predict_match_prediction_exception(
            self, prediction_service, mock_dependencies, sample_features
        ):
            "]]]""测试预测过程中的异常"""
            mock_dependencies["model["].predict.side_effect = Exception("]"""
                "Model prediction error["""""
            )
            with patch.object(:
                prediction_service, "]_get_cached_model["""""
            ) as mock_get_model, patch.object(
                prediction_service, "]_get_features["""""
            ) as mock_get_features:
                mock_get_model.return_value = mock_dependencies["]model["]: mock_get_features.return_value = sample_features[": result = await prediction_service.predict_match(12345)": assert result is None[" class TestBatchPrediction:"
        "]]]""测试批量预测"""
        @pytest.mark.asyncio
        async def test_batch_predict_matches_success(
            self, prediction_service, mock_dependencies, sample_features
        ):
            """测试成功批量预测"""
            match_ids = [12345, 67890]
            mock_dependencies["model["].predict.return_value = np.array("]"""
                [[0.6, 0.3, 0.1], [0.4, 0.4, 0.2]]
            )
            with patch.object(:
                prediction_service, "_get_cached_model["""""
            ) as mock_get_model, patch.object(
                prediction_service, "]_get_features["""""
            ) as mock_get_features, patch.object(
                prediction_service, "]_save_prediction_to_db["""""
            ) as mock_save:
                mock_get_model.return_value = mock_dependencies["]model["]: mock_get_features.side_effect = ["]sample_features[", sample_features]": results = await prediction_service.batch_predict_matches(match_ids)": assert len(results) ==2[" assert all(result is not None for result in results)"
                assert mock_save.call_count ==2
        @pytest.mark.asyncio
        async def test_batch_predict_matches_empty_list(self, prediction_service):
            "]]""测试空列表批量预测"""
            results = await prediction_service.batch_predict_matches([])
            assert results ==[]
        @pytest.mark.asyncio
        async def test_batch_predict_matches_partial_failure(
            self, prediction_service, mock_dependencies, sample_features
        ):
            """测试部分失败的情况"""
            match_ids = [12345, 67890]
            mock_dependencies["model["].predict.side_effect = ["]": np.array([[0.6, 0.3, 0.1]]),": Exception("Model error[")]": with patch.object(:": prediction_service, "]_get_cached_model["""""
            ) as mock_get_model, patch.object(
                prediction_service, "]_get_features["""""
            ) as mock_get_features:
                mock_get_model.return_value = mock_dependencies["]model["]: mock_get_features.side_effect = ["]sample_features[", sample_features]": results = await prediction_service.batch_predict_matches(match_ids)": assert len(results) ==2[" assert results[0] is not None"
                assert results[1] is None
    class TestPredictionVerification:
        "]]""测试预测结果验证"""
        def test_verify_prediction_valid_probabilities(self):
            """测试有效概率验证"""
            result = PredictionResult(
                match_id=123,
                model_version="1.0.0[",": home_win_probability=0.6,": draw_probability=0.3,": away_win_probability=0.1,"
                predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_"),": confidence_score=0.6)": is_valid = PredictionService.verify_prediction(result)": assert is_valid is True"
        def test_verify_prediction_invalid_probabilities(self):
            "]""测试无效概率验证"""
            result = PredictionResult(
                match_id=123,
                model_version="1.0.0[",": home_win_probability=0.8,": draw_probability=0.3,": away_win_probability=0.1,"
                predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_"),": confidence_score=0.8)": is_valid = PredictionService.verify_prediction(result)": assert is_valid is False  # 总和 > 1"
        def test_verify_prediction_negative_probabilities(self):
            "]""测试负概率验证"""
            result = PredictionResult(
                match_id=123,
                model_version="1.0.0[",": home_win_probability=-0.1,": draw_probability=0.3,": away_win_probability=0.8,"
                predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_"),": confidence_score=0.8)": is_valid = PredictionService.verify_prediction(result)": assert is_valid is False"
        def test_verify_prediction_mismatch_result(self):
            "]""测试预测结果不匹配"""
            result = PredictionResult(
                match_id=123,
                model_version="1.0.0[",": home_win_probability=0.3,": draw_probability=0.6,": away_win_probability=0.1,"
                predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_"),  # 应该是 draw[": confidence_score=0.6)": is_valid = PredictionService.verify_prediction(result)": assert is_valid is False"
    class TestCacheOperations:
        "]]""测试缓存操作"""
        @pytest.mark.asyncio
        async def test_get_cached_prediction_found(
            self, prediction_service, mock_dependencies
        ):
            """测试获取缓存的预测结果"""
            cached_result = {
                "match_id[": 12345,""""
                "]model_version[: "1.0.0[","]"""
                "]home_win_probability[": 0.6,""""
                "]draw_probability[": 0.3,""""
                "]away_win_probability[": 0.1,""""
                "]predicted_result[": ["]home[",""""
                "]confidence_score[": 0.6,""""
                "]created_at[": datetime.now()": with patch.object(:": prediction_service, "]_get_cached_result["""""
            ) as mock_get_cache:
                mock_get_cache.return_value = cached_result
                result = await prediction_service._get_cached_prediction(12345)
                assert result is not None
                assert result.match_id ==12345
        @pytest.mark.asyncio
        async def test_get_cached_prediction_not_found(self, prediction_service):
            "]""测试缓存未找到"""
            with patch.object(:
                prediction_service, "_get_cached_result["""""
            ) as mock_get_cache:
                mock_get_cache.return_value = None
                result = await prediction_service._get_cached_prediction(12345)
                assert result is None
        @pytest.mark.asyncio
        async def test_cache_prediction_result(self, prediction_service):
            "]""测试缓存预测结果"""
            result = PredictionResult(
                match_id=12345,
                model_version="1.0.0[",": home_win_probability=0.6,": draw_probability=0.3,": away_win_probability=0.1,"
                predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_"),": confidence_score=0.6)": with patch.object(prediction_service, "]_cache_result[") as mock_cache:": await prediction_service._cache_prediction_result(result)": mock_cache.assert_called_once()": class TestDatabaseOperations:"
        "]""测试数据库操作"""
        @pytest.mark.asyncio
        async def test_save_prediction_to_db_success(
            self, prediction_service, mock_dependencies
        ):
            """测试成功保存预测结果到数据库"""
            result = PredictionResult(
                match_id=12345,
                model_version="1.0.0[",": home_win_probability=0.6,": draw_probability=0.3,": away_win_probability=0.1,"
                predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_"),": confidence_score=0.6)": with patch.object(prediction_service, "]_save_to_database[") as mock_save:": mock_save.return_value = True[": success = await prediction_service._save_prediction_to_db(result)": assert success is True"
                mock_save.assert_called_once_with(result)
        @pytest.mark.asyncio
        async def test_save_prediction_to_db_failure(self, prediction_service):
            "]]""测试数据库保存失败"""
            result = PredictionResult(
                match_id=12345,
                model_version="1.0.0[",": home_win_probability=0.6,": draw_probability=0.3,": away_win_probability=0.1,"
                predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_"),": confidence_score=0.6)": with patch.object(prediction_service, "]_save_to_database[") as mock_save:": mock_save.side_effect = Exception("]Database error[")": success = await prediction_service._save_prediction_to_db(result)": assert success is False[" class TestMetricsCollection:"
        "]]""测试指标收集"""
        def test_metrics_counter_increment(self, prediction_service):
            """测试指标计数器递增"""
            CollectorRegistry()
            # 模拟指标收集
            prediction_service.prediction_requests_total.inc()
            prediction_service.prediction_errors_total.inc()
            # 验证指标值
            assert prediction_service.prediction_requests_total._value.get() ==1
            assert prediction_service.prediction_errors_total._value.get() ==1
        def test_metrics_histogram_observation(self, prediction_service):
            """测试指标直方图观察"""
            prediction_service.prediction_duration_seconds.observe(1.5)
            # 验证直方图记录了观察值
            assert prediction_service.prediction_duration_seconds._sum.get() ==1.5
    class TestErrorHandling:
        """测试错误处理"""
        @pytest.mark.asyncio
        async def test_graceful_degradation_on_mlflow_failure(self, prediction_service):
            """测试 MLflow 失败时的优雅降级"""
            with patch("src.models.prediction_service.MlflowClient[") as mlflow_mock:": mlflow_mock.side_effect = Exception("]MLflow connection failed[")": model = await prediction_service._load_model_from_mlflow("]test-model[")": assert model is None["""
        @pytest.mark.asyncio
        async def test_retry_with_exponential_backoff(
            self, prediction_service, mock_dependencies
        ):
            "]]""测试指数退避重试"""
            call_count = 0
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Temporary failure[")": return "]1.0.0[": mock_dependencies["]mlflow["].get_latest_model_version.side_effect = (": side_effect["""
            )
            mock_dependencies["]]mlflow["].load_model.return_value = mock_dependencies[""""
                "]model["""""
            ]
            with patch(:
                "]src.models.prediction_service.MlflowClient["""""
            ) as mlflow_mock, patch("]asyncio.sleep[") as sleep_mock:": mlflow_mock.return_value = mock_dependencies["]mlflow["]: model = await prediction_service._load_model_from_mlflow("]test-model[")": assert model is not None[" assert call_count ==3[""
                # 验证指数退避
                expected_delays = [2.0, 4.0]  # 2^1, 2^2
                actual_delays = [call[0][0] for call in sleep_mock.call_args_list]
                assert actual_delays ==expected_delays
    class TestUtilityMethods:
        "]]]""测试工具方法"""
        def test_probability_validation(self):
            """测试概率验证"""
            # 有效概率
            assert PredictionService._validate_probabilities([0.6, 0.3, 0.1]) is True
            assert PredictionService._validate_probabilities([0.33, 0.33, 0.34]) is True
            # 无效概率
            assert (
                PredictionService._validate_probabilities([0.8, 0.3, 0.1]) is False
            )  # 总和 > 1
            assert (
                PredictionService._validate_probabilities([-0.1, 0.6, 0.5]) is False
            )  # 负数
            assert (
                PredictionService._validate_probabilities([0.4, 0.4, 0.4]) is False
            )  # 总和 > 1
        def test_result_determination(self):
            """测试结果确定"""
            assert PredictionService._determine_result([0.6, 0.3, 0.1]) =="home[" assert PredictionService._determine_result([0.3, 0.6, 0.1]) =="]draw[" assert PredictionService._determine_result([0.1, 0.3, 0.6]) =="]away[" assert (""""
                PredictionService._determine_result([0.4, 0.4, 0.2]) =="]home["""""
            )  # 平局时取第一个
        def test_confidence_calculation(self):
            "]""测试置信度计算"""
            assert PredictionService._calculate_confidence([0.6, 0.3, 0.1]) ==0.6
            assert PredictionService._calculate_confidence([0.4, 0.4, 0.2]) ==0.4
            assert PredictionService._calculate_confidence([0.33, 0.33, 0.34]) ==0.34
    class TestIntegrationScenarios:
        """测试集成场景"""
        @pytest.mark.asyncio
        async def test_end_to_end_prediction_flow(
            self, prediction_service, mock_dependencies, sample_features
        ):
            """测试端到端预测流程"""
            # Mock 所有依赖
            mock_dependencies["model["].predict.return_value = np.array("]"""
                [[0.6, 0.3, 0.1]]
            )
            with patch.object(:
                prediction_service, "_get_cached_model["""""
            ) as mock_get_model, patch.object(
                prediction_service, "]_get_features["""""
            ) as mock_get_features, patch.object(
                prediction_service, "]_save_prediction_to_db["""""
            ) as mock_save, patch.object(
                prediction_service, "]_cache_prediction_result["""""
            ) as mock_cache:
                mock_get_model.return_value = mock_dependencies["]model["]: mock_get_features.return_value = sample_features[": mock_save.return_value = True["""
                # 执行预测
                result = await prediction_service.predict_match(12345)
                # 验证完整流程
                assert result is not None
                assert result.match_id ==12345
                mock_get_model.assert_called_once()
                mock_get_features.assert_called_once()
                mock_save.assert_called_once()
                mock_cache.assert_called_once()
        @pytest.mark.asyncio
        async def test_concurrent_predictions(
            self, prediction_service, mock_dependencies, sample_features
        ):
            "]]]""测试并发预测"""
            mock_dependencies["model["].predict.return_value = np.array("]"""
                [[0.6, 0.3, 0.1]]
            )
            with patch.object(:
                prediction_service, "_get_cached_model["""""
            ) as mock_get_model, patch.object(
                prediction_service, "]_get_features["""""
            ) as mock_get_features:
                mock_get_model.return_value = mock_dependencies["]model["]: mock_get_features.return_value = sample_features["]"]""
                # 并发执行多个预测
                tasks = [
                    prediction_service.predict_match(match_id)
                    for match_id in [12345, 67890, 11111]:
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                # 验证所有预测都成功
                assert all(
                    result is not None and not isinstance(result, Exception)
                    for result in results:
                )