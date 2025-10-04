from datetime import datetime

from contextlib import ExitStack
from sqlalchemy.exc import DatabaseError
from src.models.prediction_service import PredictionResult, PredictionService
from unittest.mock import AsyncMock, Mock, patch
import asyncio
import numpy
import pytest
import time

"""
边缘情况和故障场景测试

测试范围: 系统在边缘情况和故障场景下的行为
测试重点:
- 输入验证和边界条件
- 网络故障和超时处理
- 数据库连接问题
- 模型加载失败
- 并发和竞争条件
- 资源限制和性能边界
"""

# 项目导入
from src.models.prediction_service import PredictionResult, PredictionService
@pytest.mark.edge_case
@pytest.mark.failure_scenario
class TestEdgeCasesAndFailureScenarios:
    """边缘情况和故障场景测试类"""
    @pytest.fixture
    def db_manager(self, mock_db_session):
        """数据库管理器"""
        mock_manager = Mock()
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_session_context.__aenter__.return_value = mock_db_session
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_async_session = Mock(return_value=mock_session_context)
        return mock_manager
    @pytest.fixture
    def feature_store(self, mock_feature_store):
        """特征存储"""
        return mock_feature_store
    @pytest.fixture
    def prediction_service(
        self, mock_mlflow_module, mock_mlflow_client, db_manager, feature_store
    ):
        """预测服务，确保外部依赖在整个测试生命周期内保持mock"""
        with ExitStack() as stack:
            stack.enter_context(
            patch("src.models.prediction_service.mlflow[", mock_mlflow_module)""""
            )
            stack.enter_context(
            patch(
            "]src.models.prediction_service.MlflowClient[",": return_value=mock_mlflow_client)"""
            )
            stack.enter_context(
                patch(
                "]src.models.prediction_service.DatabaseManager[",": return_value=db_manager)"""
            )
            stack.enter_context(
                patch(
                "]src.models.prediction_service.FootballFeatureStore[",": return_value=feature_store)"""
            )
            service = PredictionService()
            service.db_manager = db_manager
            service.feature_store = feature_store
            yield service
    @pytest.fixture
    def sample_match_data(self):
        "]""示例比赛数据"""
        return {
        "id[": 1,""""
        "]home_team_id[": 10,""""
        "]away_team_id[": 20,""""
        "]league_id[": 1,""""
            "]match_time[": datetime.now()""""
    # ================================
    # 输入验证和边界条件测试
    # ================================
    @pytest.mark.asyncio
    async def test_predict_match_with_invalid_id(self, prediction_service):
        "]""测试使用无效比赛ID进行预测"""
        # Mock _get_match_info to return None for invalid IDs
        with patch.object(:
            prediction_service, "_get_match_info[", return_value=None[""""
        ), patch.object(prediction_service, "]]get_production_model[") as mock_get_model:""""
            # Mock the model to avoid MLflow connection
            mock_model = Mock()
            mock_model.predict_proba = Mock(return_value=np.array([[0.33, 0.33, 0.34]]))
            mock_model.predict = Mock(return_value=np.array("]draw["))": mock_get_model.return_value = (mock_model, "]1.0[")": with pytest.raises(ValueError, match = "]比赛 0 不存在[")": await prediction_service.predict_match(0)": with pytest.raises(ValueError, match = "]比赛 -1 不存在[")": await prediction_service.predict_match(-1)"""
    @pytest.mark.asyncio
    async def test_predict_match_with_extreme_id_values(self, prediction_service):
        "]""测试使用极端比赛ID值进行预测"""
        # Mock _get_match_info to return None for extreme IDs
        with patch.object(:
            prediction_service, "_get_match_info[", return_value=None[""""
        ), patch.object(prediction_service, "]]get_production_model[") as mock_get_model:""""
            # Mock the model to avoid MLflow connection
            mock_model = Mock()
            mock_model.predict_proba = Mock(return_value=np.array([[0.33, 0.33, 0.34]]))
            mock_model.predict = Mock(return_value=np.array("]draw["))": mock_get_model.return_value = (mock_model, "]1.0[")""""
            # 测试非常大的ID
            with pytest.raises(ValueError):
                await prediction_service.predict_match(999999999999999999)
            # 测试字符串ID（如果类型检查不严格）
            with pytest.raises(ValueError):
                await prediction_service.predict_match("]invalid_id[")""""
    @pytest.mark.asyncio
    async def test_get_model_accuracy_with_invalid_days(self, prediction_service):
        "]""测试使用无效天数获取模型准确率"""
        # 测试负数天数
        result = await prediction_service.get_model_accuracy(days=-1)
        # 应该返回None或处理负数情况
    assert result is None or isinstance(result, (float, int))
        # 测试零天数
        result = await prediction_service.get_model_accuracy(days=0)
    assert result is None or isinstance(result, (float, int))
    # ================================
    # 网络故障和超时处理测试
    # ================================
    @pytest.mark.asyncio
    async def test_mlflow_network_timeout(self, prediction_service, mock_mlflow_client):
        """测试MLflow网络超时"""
        # Configure the mock client to raise TimeoutError
        mock_mlflow_client.get_latest_versions.side_effect = TimeoutError(
        "MLflow服务器连接超时["""""
        )
        with pytest.raises(TimeoutError):
            await prediction_service.get_production_model()
    @pytest.mark.asyncio
    async def test_mlflow_network_failure(self, prediction_service, mock_mlflow_client):
        "]""测试MLflow网络故障"""
        # Configure the mock client to raise ConnectionError
        mock_mlflow_client.get_latest_versions.side_effect = ConnectionError(
        "无法连接到MLflow服务器["""""
        )
        with pytest.raises(ConnectionError):
            await prediction_service.get_production_model()
    @pytest.mark.asyncio
    async def test_feature_store_network_failure(self, prediction_service):
        "]""测试特征存储网络故障"""
        with patch.object(:
            prediction_service,
            "_get_match_info[",": return_value={"""
            "]id[": 1,""""
            "]home_team_id[": 10,""""
            "]away_team_id[": 20,""""
            "]league_id[": 1,""""
                "]match_time[": datetime.now()), patch.object(": prediction_service.feature_store, "]get_match_features_for_prediction["""""
        ) as mock_get_features, patch.object(
            prediction_service, "]get_production_model["""""
        ) as mock_get_model:
            # Mock网络故障
            mock_get_features.side_effect = ConnectionError("]无法连接到特征存储[")""""
            # Mock模型返回
            mock_model = Mock()
            mock_model.predict_proba = Mock(return_value=np.array([[0.33, 0.33, 0.34]]))
            mock_model.predict = Mock(return_value=np.array("]draw["))": mock_get_model.return_value = (mock_model, "]1.0[")""""
            # 应该回退到默认特征而不是失败
            result = await prediction_service.predict_match(1)
    assert result is not None
    # ================================
    # 数据库连接问题测试
    # ================================
    @pytest.mark.asyncio
    async def test_database_connection_failure(self, prediction_service):
        "]""测试数据库连接失败"""
        # Mock数据库连接异常 by setting side_effect on the existing mock
        # Since the db_manager is already a mock from the fixture, we can directly set its behavior
        prediction_service.db_manager.get_async_session.side_effect = DatabaseError(
        "数据库连接失败[", "]", """
        )
        # 测试获取比赛信息失败
        result = await prediction_service._get_match_info(1)
    assert result is None
    @pytest.mark.asyncio
    async def test_database_query_timeout(self, prediction_service):
        """测试数据库查询超时"""
        # Mock数据库超时异常
        # Create a mock session context manager
        mock_session_context = AsyncMock()
        mock_session = AsyncMock()
        mock_session.execute.side_effect = TimeoutError("数据库查询超时[")": mock_session_context.__aenter__.return_value = mock_session["""
        # Since the db_manager is already a mock from the fixture, we can directly set its return value
        prediction_service.db_manager.get_async_session.return_value = (
        mock_session_context
        )
        # 测试获取比赛信息失败
        result = await prediction_service._get_match_info(1)
    assert result is None
    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, prediction_service):
        "]]""测试数据库事务回滚"""
        # Mock数据库提交失败
        mock_session = AsyncMock()
        mock_session.commit.side_effect = Exception("数据库提交失败[")": mock_session_context = AsyncMock()": mock_session_context.__aenter__.return_value = mock_session[""
        # Since the db_manager is already a mock from the fixture, we can directly set its behavior
        prediction_service.db_manager.get_async_session.return_value = (
        mock_session_context
        )
        # 创建预测结果
        prediction_result = PredictionResult(match_id=1, model_version="]]1.0[")""""
        # 存储预测结果应该失败并触发回滚
        with pytest.raises(Exception):
            await prediction_service._store_prediction(prediction_result)
        # 验证回滚被调用
        mock_session.rollback.assert_called_once()
    # ================================
    # 模型加载失败测试
    # ================================
    @pytest.mark.asyncio
    async def test_model_loading_failure(
        self, prediction_service, mock_mlflow_module, mock_mlflow_client
    ):
        "]""测试模型加载失败"""
        # Mock模型加载失败
        mock_mlflow_module.sklearn.load_model.side_effect = Exception("模型文件损坏[")""""
        # 获取模型应该失败
        with pytest.raises(Exception, match = "]模型文件损坏[")": await prediction_service.get_production_model()"""
    @pytest.mark.asyncio
    async def test_model_version_not_found(
        self, prediction_service, mock_mlflow_client
    ):
        "]""测试模型版本不存在"""
        # Mock MLflow客户端返回空版本列表
        mock_mlflow_client.get_latest_versions.return_value = []
        # 获取模型应该失败
        with pytest.raises(:
            ValueError, match="模型 football_baseline_model 没有可用版本["""""
        ):
            await prediction_service.get_production_model()
    # ================================
    # 并发和竞争条件测试
    # ================================
    @pytest.mark.asyncio
    async def test_concurrent_model_loading(
        self, prediction_service, mock_mlflow_module, mock_mlflow_client
    ):
        "]""测试并发模型加载"""
        # Reset the mock to ensure clean state
        mock_mlflow_client.reset_mock()
        mock_mlflow_module.reset_mock()
        # Mock模型
        mock_model = Mock()
        mock_model.predict_proba = Mock(return_value=np.array([[0.33, 0.33, 0.34]]))
        mock_model.predict = Mock(return_value=np.array("draw["))": mock_mlflow_module.sklearn.load_model.return_value = mock_model["""
        # 创建并发任务
        async def load_model_task():
        return await prediction_service.get_production_model()
        # 并发执行多个任务
        tasks = [load_model_task() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 验证所有任务都成功完成
        successful_results = [r for r in results if not isinstance(r, Exception)]
    assert len(successful_results) ==5
        # 验证所有结果都相同
        models, versions = zip(*successful_results)
    assert len(set(id(m) for m in models)) ==1  # 所有模型对象相同
    assert len(set(versions)) ==1  # 所有版本号相同
    @pytest.mark.asyncio
    async def test_concurrent_prediction_requests(self, prediction_service):
        "]]""测试并发预测请求"""
        with patch.object(prediction_service, "_get_match_info[") as mock_get_match_info:""""
            # Mock比赛信息
            mock_get_match_info.return_value = {
            "]id[": 1,""""
            "]home_team_id[": 10,""""
            "]away_team_id[": 20,""""
            "]league_id[": 1,""""
                "]match_time[": datetime.now()""""
            # 创建并发预测任务
            async def predict_task(match_id):
                return await prediction_service.predict_match(match_id)
            # 并发执行多个预测任务
            tasks = [predict_task(i) for i in range(1, 6)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # 验证所有任务都成功完成
            successful_results = [r for r in results if not isinstance(r, Exception)]
    assert len(successful_results) ==5
            # 验证所有结果都有效
            for result in successful_results:
    assert isinstance(result, PredictionResult)
    assert 0 <= result.confidence_score <= 1
    # ================================
    # 资源限制和性能边界测试
    # ================================
    @pytest.mark.asyncio
    async def test_large_batch_prediction(self, prediction_service):
        "]""测试大批量预测"""
        with patch.object(:
            prediction_service, "get_production_model["""""
        ) as mock_get_model, patch.object(
            prediction_service, "]predict_match["""""
        ) as mock_predict:
            # Mock模型
            mock_model = Mock()
            mock_get_model.return_value = (mock_model, "]1.0[")""""
            # Mock单个预测
            mock_predict.side_effect = lambda match_id PredictionResult(
            match_id=match_id, model_version="]1.0[", confidence_score=0.75[""""
            )
            # 创建大批量比赛ID
            match_ids = list(range(1, 101))  # 100场比赛
            # 执行批量预测
            results = await prediction_service.batch_predict_matches(match_ids)
            # 验证结果
    assert len(results) ==100
    assert all(isinstance(r, PredictionResult) for r in results)
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, prediction_service):
        "]]""测试负载下的内存使用"""
        import os
        import psutil
        # 获取初始内存使用
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        with patch.object(prediction_service, "_get_match_info[") as mock_get_match_info:""""
            # Mock比赛信息
            mock_get_match_info.return_value = {
            "]id[": 1,""""
            "]home_team_id[": 10,""""
            "]away_team_id[": 20,""""
            "]league_id[": 1,""""
                "]match_time[": datetime.now()""""
            # 执行多次预测
            for i in range(50):
                await prediction_service.predict_match(1)
            # 获取最终内存使用
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            # 验证内存增长在合理范围内（不超过50MB增长）
            memory_growth = final_memory - initial_memory
    assert memory_growth < 50, f["]内存增长过大["] [{memory_growth.2f}MB]""""
    @pytest.mark.asyncio
    async def test_prediction_service_under_high_concurrency(self, prediction_service):
        "]""测试高并发下的预测服务"""
        with patch.object(prediction_service, "_get_match_info[") as mock_get_match_info:""""
            # Mock比赛信息
            mock_get_match_info.return_value = {
            "]id[": 1,""""
            "]home_team_id[": 10,""""
            "]away_team_id[": 20,""""
            "]league_id[": 1,""""
                "]match_time[": datetime.now()""""
            # 记录开始时间
            start_time = time.time()
            # 创建高并发任务（50个并发）
            async def predict_task():
                return await prediction_service.predict_match(1)
            tasks = [predict_task() for _ in range(50)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # 计算总时间
            total_time = time.time() - start_time
            # 验证性能（50个请求应该在5秒内完成）
    assert total_time < 5.0, f["]高并发性能不佳["] [{total_time.2f}秒]""""
            # 验证成功率
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            success_rate = success_count / len(results)
    assert success_rate >= 0.9, f["]高并发成功率过低["] [{success_rate.2%}]""""
    # ================================
    # 异常输入和数据完整性测试
    # ================================
    @pytest.mark.asyncio
    async def test_predict_match_with_corrupted_match_data(self, prediction_service):
        "]""测试比赛数据损坏的情况"""
        with patch.object(prediction_service, "_get_match_info[") as mock_get_match_info:""""
            # Mock损坏的比赛数据
            mock_get_match_info.return_value = {
            "]id[": 1,""""
            "]home_team_id[": None,  # 缺失关键字段[""""
            "]]away_team_id[": None,""""
            "]league_id[": None,""""
                "]match_time[": None,""""
                "]match_status[": ["]invalid_status[",  # 无效状态[""""
                "]]season[": None}""""
            # 应该能够处理损坏的数据
            result = await prediction_service.predict_match(1)
    assert isinstance(result, PredictionResult)
    @pytest.mark.asyncio
    async def test_predict_match_with_unusual_match_status(self, prediction_service):
        "]""测试异常比赛状态"""
        with patch.object(prediction_service, "_get_match_info[") as mock_get_match_info:""""
            # Mock异常比赛状态
            mock_get_match_info.return_value = {
            "]id[": 1,""""
            "]home_team_id[": 10,""""
            "]away_team_id[": 20,""""
            "]league_id[": 1,""""
                "]match_time[": datetime.now()""""
            # 应该能够处理异常状态
            result = await prediction_service.predict_match(1)
    assert isinstance(result, PredictionResult)
    @pytest.mark.asyncio
    async def test_feature_preparation_with_missing_features(self, prediction_service):
        "]""测试特征准备时缺失特征"""
        # 提供不完整的特征
        incomplete_features = {
        "home_recent_wins[": 3,""""
        # 缺失其他关键特征
        }
        # 应该能够处理缺失特征
        features_array = prediction_service._prepare_features_for_prediction(
        incomplete_features
        )
        # 验证结果数组的形状
    assert isinstance(features_array, np.ndarray)
    assert features_array.shape ==(1, 10)  # 应该填充缺失值为0
    @pytest.mark.asyncio
    async def test_verify_prediction_for_nonexistent_match(
        self, prediction_service, db_manager
    ):
        "]""测试验证不存在的比赛预测"""
        # Mock数据库返回空结果
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.first.return_value = None  # 比赛不存在
        mock_session.execute.return_value = mock_result
        db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        # 验证应该返回False
        result = await prediction_service.verify_prediction(999999)
    assert result is False
        import os
        import psutil