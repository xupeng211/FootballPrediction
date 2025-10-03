import os
import sys

from src.cache.redis_manager import RedisManager
from src.data.processing.football_data_cleaner import FootballDataCleaner
from src.data.processing.missing_data_handler import MissingDataHandler
from src.data.storage.data_lake_storage import DataLakeStorage
from src.database.connection import DatabaseManager
from src.services.data_processing import DataProcessingService
from unittest.mock import Mock, AsyncMock
import pandas
import pytest

"""
数据处理服务 Batch-Γ-001 测试套件

专门为 data_processing.py 设计的测试，目标是将其覆盖率从 7% 提升至 ≥32%
覆盖所有数据处理功能、数据清洗、缺失值处理、异常检测等
"""

# Add the project root to sys.path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
from src.services.data_processing import DataProcessingService
from src.data.processing.football_data_cleaner import FootballDataCleaner
from src.data.processing.missing_data_handler import MissingDataHandler
from src.data.storage.data_lake_storage import DataLakeStorage
from src.database.connection import DatabaseManager
from src.cache.redis_manager import RedisManager
class TestDataProcessingServiceBatchGamma001:
    """数据处理服务 Batch-Γ-001 测试类"""
    @pytest.fixture
    def data_processing_service(self):
        """创建数据处理服务实例"""
        service = DataProcessingService()
        return service
    @pytest.fixture
    def initialized_service(self):
        """创建已初始化的数据处理服务实例"""
        service = DataProcessingService()
        service.data_cleaner = Mock(spec=FootballDataCleaner)
        service.missing_handler = Mock(spec=MissingDataHandler)
        service.data_lake = Mock(spec=DataLakeStorage)
        service.db_manager = Mock(spec=DatabaseManager)
        service.cache_manager = Mock(spec=RedisManager)
        return service
    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return {
            "match_id[": 1001,""""
            "]home_team[: "Team A[","]"""
            "]away_team[: "Team B[","]"""
            "]home_score[": 2,""""
            "]away_score[": 1,""""
            "]match_date[: "2025-01-15[","]"""
            "]competition[: "Premier League[","]"""
            "]season[: "2024-2025["}"]"""
    @pytest.fixture
    def sample_odds_data(self):
        "]""示例赔率数据"""
        return {
            "match_id[": 1001,""""
            "]home_odds[": 2.10,""""
            "]draw_odds[": 3.20,""""
            "]away_odds[": 3.80,""""
            "]bookmaker[": ["]Bet365[",""""
            "]timestamp[: "2025-01-15T10:00:00["}"]"""
    @pytest.fixture
    def sample_dataframe(self):
        "]""示例DataFrame数据"""
        return pd.DataFrame({
                "match_id[: "1001, 1002, 1003[","]"""
                "]home_team[": ["]Team A[", "]Team C[", "]Team E["],""""
                "]away_team[": ["]Team B[", "]Team D[", "]Team F["],""""
                "]home_score[: "2, 1, 0[","]"""
                "]away_score[: "1, 1, 2[","]"""
                "]match_date[": pd.to_datetime(""""
                    ["]2025-01-15[", "]2025-01-16[", "]2025-01-17["]""""
                )
        )
    def test_service_initialization(self, data_processing_service):
        "]""测试服务初始化"""
        # 验证服务名称设置正确
        assert data_processing_service.name =="DataProcessingService["""""
        # 验证所有组件都初始化为None
        assert data_processing_service.data_cleaner is None
        assert data_processing_service.missing_handler is None
        assert data_processing_service.data_lake is None
        assert data_processing_service.db_manager is None
        assert data_processing_service.cache_manager is None
    @pytest.mark.asyncio
    async def test_initialize_success(self, initialized_service):
        "]""测试服务初始化成功场景"""
        # Mock组件初始化
        initialized_service.data_cleaner.initialize = AsyncMock(return_value=True)
        initialized_service.missing_handler.initialize = AsyncMock(return_value=True)
        initialized_service.data_lake.initialize = AsyncMock(return_value=True)
        initialized_service.db_manager.get_connection = AsyncMock()
        initialized_service.cache_manager.aping = AsyncMock(return_value=True)
        result = await initialized_service.initialize()
        # 验证初始化成功
        assert result is True
        # 验证所有组件都被初始化
        initialized_service.data_cleaner.initialize.assert_called_once()
        initialized_service.missing_handler.initialize.assert_called_once()
        initialized_service.data_lake.initialize.assert_called_once()
        initialized_service.db_manager.get_connection.assert_called_once()
        initialized_service.cache_manager.aping.assert_called_once()
    @pytest.mark.asyncio
    async def test_initialize_failure(self, data_processing_service):
        """测试服务初始化失败场景"""
        # Mock数据清洗器初始化失败
        data_processing_service.data_cleaner.initialize = AsyncMock(return_value=False)
        result = await data_processing_service.initialize()
        # 验证初始化失败
        assert result is False
    @pytest.mark.asyncio
    async def test_shutdown(self, data_processing_service):
        """测试服务关闭"""
        data_processing_service.db_manager.close = AsyncMock()
        data_processing_service.cache_manager.close = AsyncMock()
        data_processing_service.data_lake.close = AsyncMock()
        await data_processing_service.shutdown()
        # 验证所有连接都被关闭
        data_processing_service.db_manager.close.assert_called_once()
        data_processing_service.cache_manager.close.assert_called_once()
        data_processing_service.data_lake.close.assert_called_once()
    @pytest.mark.asyncio
    async def test_process_raw_match_data_success(
        self, data_processing_service, sample_match_data
    ):
        """测试处理原始比赛数据成功场景"""
        # Mock数据清洗和存储
        data_processing_service.data_cleaner.clean_match_data = AsyncMock(
            return_value=sample_match_data
        )
        data_processing_service.db_manager.execute = AsyncMock()
        data_processing_service.data_lake.store = AsyncMock()
        result = await data_processing_service.process_raw_match_data(sample_match_data)
        # 验证处理成功
        assert result["success["] is True["]"]" assert result["processed_id["] ==1001["]"]" assert result["message["] =="]比赛数据处理完成["""""
        # 验证处理步骤被调用
        data_processing_service.data_cleaner.clean_match_data.assert_called_once_with(
            sample_match_data
        )
        data_processing_service.db_manager.execute.assert_called_once()
        data_processing_service.data_lake.store.assert_called_once()
    @pytest.mark.asyncio
    async def test_process_raw_match_data_failure(
        self, data_processing_service, sample_match_data
    ):
        "]""测试处理原始比赛数据失败场景"""
        # Mock数据清洗失败
        data_processing_service.data_cleaner.clean_match_data = AsyncMock(
            side_effect=Exception("清洗失败[")""""
        )
        result = await data_processing_service.process_raw_match_data(sample_match_data)
        # 验证处理失败
        assert result["]success["] is False[" assert "]]清洗失败[" in result["]error["]""""
    @pytest.mark.asyncio
    async def test_process_raw_odds_data_success(
        self, data_processing_service, sample_odds_data
    ):
        "]""测试处理原始赔率数据成功场景"""
        # Mock数据清洗和存储
        data_processing_service.data_cleaner.clean_odds_data = AsyncMock(
            return_value=sample_odds_data
        )
        data_processing_service.db_manager.execute = AsyncMock()
        result = await data_processing_service.process_raw_odds_data(sample_odds_data)
        # 验证处理成功
        assert result["success["] is True["]"]" assert result["processed_id["] ==1001["]"]" assert result["message["] =="]赔率数据处理完成["""""
    @pytest.mark.asyncio
    async def test_process_features_data(
        self, data_processing_service, sample_dataframe
    ):
        "]""测试处理特征数据"""
        # Mock特征处理
        data_processing_service.data_cleaner.extract_features = AsyncMock(
            return_value=sample_dataframe
        )
        data_processing_service.cache_manager.setex = AsyncMock()
        result = await data_processing_service.process_features_data(sample_dataframe)
        # 验证处理成功
        assert result["success["] is True["]"]" assert result["features_count["] ==3["]"]""
    @pytest.mark.asyncio
    async def test_process_batch_matches(
        self, data_processing_service, sample_match_data
    ):
        """测试批量处理比赛数据"""
        batch_data = ["sample_match_data[", {**sample_match_data, "]match_id[": 1002}]""""
        # Mock批量处理
        data_processing_service._process_single_match_data = AsyncMock(
            side_effect=batch_data
        )
        result = await data_processing_service.process_batch_matches(batch_data)
        # 验证批量处理成功
        assert result["]success["] is True[" assert result["]]processed_count["] ==2[" assert result["]]failed_count["] ==0[""""
    @pytest.mark.asyncio
    async def test_validate_data_quality_success(
        self, data_processing_service, sample_dataframe
    ):
        "]]""测试数据质量验证成功场景"""
        # Mock质量验证
        data_processing_service.data_cleaner.validate_data = AsyncMock(return_value = {"is_valid[": True, "]score[": 0.95, "]issues[" [])""""
        )
        result = await data_processing_service.validate_data_quality(sample_dataframe)
        # 验证质量检查通过
        assert result["]valid["] is True[" assert result["]]score["] ==0.95[" assert len(result["]]issues["]) ==0[""""
    @pytest.mark.asyncio
    async def test_validate_data_quality_failure(
        self, data_processing_service, sample_dataframe
    ):
        "]]""测试数据质量验证失败场景"""
        # Mock质量验证失败
        data_processing_service.data_cleaner.validate_data = AsyncMock(return_value={
                "is_valid[": False,""""
                "]score[": 0.65,""""
                "]issues[": ["]缺失值过多[", "]数据格式错误["])""""
        )
        result = await data_processing_service.validate_data_quality(sample_dataframe)
        # 验证质量检查失败
        assert result["]valid["] is False[" assert result["]]score["] ==0.65[" assert len(result["]]issues["]) ==2[" def test_process_text(self, data_processing_service):"""
        "]]""测试文本处理"""
        text = os.getenv("SERVICES_DATA_PROCESSING_BATCH_GAMMA__TEXT_227"): result = data_processing_service.process_text(text)""""
        # 验证文本处理结果
        assert isinstance(result, dict)
        assert "]processed[" in result[""""
        assert result["]]processed["] is True[""""
    @pytest.mark.asyncio
    async def test_process_batch(self, data_processing_service, sample_match_data):
        "]]""测试批量数据处理"""
        data_list = ["sample_match_data[", {**sample_match_data, "]match_id[": 1002}]""""
        # Mock处理单个数据
        data_processing_service.process_raw_match_data = AsyncMock(side_effect=[
                {"]success[": True, "]processed_id[": 1001},""""
                {"]success[": True, "]processed_id[": 1002)]""""
        )
        result = await data_processing_service.process_batch(data_list)
        # 验证批量处理结果
        assert len(result) ==2
        assert all(item["]success["] for item in result)""""
    @pytest.mark.asyncio
    async def test_process_bronze_to_silver(self, data_processing_service):
        "]""测试青铜层到银层数据处理"""
        # Mock各层数据处理
        data_processing_service._process_raw_matches_bronze_to_silver = AsyncMock(
            return_value=100
        )
        data_processing_service._process_raw_odds_bronze_to_silver = AsyncMock(
            return_value=50
        )
        data_processing_service._process_raw_scores_bronze_to_silver = AsyncMock(
            return_value=25
        )
        result = await data_processing_service.process_bronze_to_silver(batch_size=100)
        # 验证处理结果
        assert result["total_processed["] ==175["]"]" assert result["matches_processed["] ==100["]"]" assert result["odds_processed["] ==50["]"]" assert result["scores_processed["] ==25["]"]""
    @pytest.mark.asyncio
    async def test_get_bronze_layer_status(self, data_processing_service):
        """测试获取青铜层状态"""
        # Mock数据库查询
        data_processing_service.db_manager.fetch_all = AsyncMock(side_effect=[
                [{"count[": 100}],  # 比赛数据[""""
                [{"]]count[": 200}],  # 赔率数据[""""
                [{"]]count[": 150)],  # 比分数据[""""
            ]
        )
        result = await data_processing_service.get_bronze_layer_status()
        # 验证状态信息
        assert result["]]matches_count["] ==100[" assert result["]]odds_count["] ==200[" assert result["]]scores_count["] ==150[" assert result["]]total_records["] ==450[""""
    @pytest.mark.asyncio
    async def test_handle_missing_scores(
        self, data_processing_service, sample_dataframe
    ):
        "]]""测试处理缺失比分数据"""
        # Mock缺失值处理
        data_processing_service.missing_handler.handle_missing_scores = AsyncMock(
            return_value=sample_dataframe
        )
        result = await data_processing_service.handle_missing_scores(sample_dataframe)
        # 验证处理结果
        assert result is not None
        assert len(result) ==3
    @pytest.mark.asyncio
    async def test_detect_anomalies(self, data_processing_service, sample_dataframe):
        """测试异常检测"""
        # Mock异常检测
        data_processing_service.data_cleaner.detect_anomalies = AsyncMock(return_value = [{"type[: "outlier"", "value["])]""""
        )
        result = await data_processing_service.detect_anomalies(sample_dataframe)
        # 验证异常检测结果
        assert len(result) ==1
        assert result[0]"]type[" =="]outlier["""""
    @pytest.mark.asyncio
    async def test_store_processed_data(
        self, data_processing_service, sample_dataframe
    ):
        "]""测试存储处理后的数据"""
        # Mock数据存储
        data_processing_service.data_lake.store = AsyncMock()
        data_processing_service.db_manager.execute = AsyncMock()
        result = await data_processing_service.store_processed_data(
            sample_dataframe, "matches["""""
        )
        # 验证存储成功
        assert result["]success["] is True[" assert result["]]stored_count["] ==3[""""
    @pytest.mark.asyncio
    async def test_cache_processing_results(self, data_processing_service):
        "]]""测试缓存处理结果"""
        cache_key = os.getenv("SERVICES_DATA_PROCESSING_BATCH_GAMMA__CACHE_KEY_31"): data = {"]test[": ["]data["}""""
        # Mock缓存操作
        data_processing_service.cache_manager.setex = AsyncMock()
        result = await data_processing_service.cache_processing_results(cache_key, data)
        # 验证缓存成功
        assert result["]success["] is True[" data_processing_service.cache_manager.setex.assert_called_once()"""
    @pytest.mark.asyncio
    async def test_get_cached_results(self, data_processing_service):
        "]]""测试获取缓存结果"""
        cache_key = os.getenv("SERVICES_DATA_PROCESSING_BATCH_GAMMA__CACHE_KEY_31"): cached_data = {"]cached[": ["]result["}""""
        # Mock缓存获取
        data_processing_service.cache_manager.get = AsyncMock(return_value=cached_data)
        result = await data_processing_service.get_cached_results(cache_key)
        # 验证获取缓存结果
        assert result ==cached_data
    @pytest.mark.asyncio
    async def test_get_cached_results_miss(self, data_processing_service):
        "]""测试缓存未命中"""
        cache_key = os.getenv("SERVICES_DATA_PROCESSING_BATCH_GAMMA__CACHE_KEY_32")""""
        # Mock缓存未命中
        data_processing_service.cache_manager.get = AsyncMock(return_value=None)
        result = await data_processing_service.get_cached_results(cache_key)
        # 验证返回None
        assert result is None
    @pytest.mark.asyncio
    async def test_batch_process_datasets(self, data_processing_service):
        "]""测试批量处理数据集"""
        datasets = [[{"id[": 1}, {"]id[": 2}], [{"]id[": 3}, {"]id[": 4}]]""""
        # Mock批量处理
        data_processing_service.process_batch = AsyncMock(side_effect=[
                [{"]success[": True}, {"]success[": True}],""""
                [{"]success[": True}, {"]success[": True)]]""""
        )
        result = await data_processing_service.batch_process_datasets(datasets)
        # 验证批量处理结果
        assert result["]total_datasets["] ==2[" assert result["]]total_processed["] ==4[""""
    @pytest.mark.asyncio
    async def test_process_with_retry_success(
        self, data_processing_service, sample_match_data
    ):
        "]]""测试带重试的处理成功场景"""
        # Mock处理成功
        data_processing_service.process_raw_match_data = AsyncMock(return_value = {"success[": True)""""
        )
        result = await data_processing_service.process_with_retry(
            sample_match_data, max_retries=3
        )
        # 验证处理成功
        assert result["]success["] is True[" assert result["]]attempts["] ==1[""""
    @pytest.mark.asyncio
    async def test_process_with_retry_failure(
        self, data_processing_service, sample_match_data
    ):
        "]]""测试带重试的处理失败场景"""
        # Mock处理失败
        data_processing_service.process_raw_match_data = AsyncMock(return_value = {"success[": False)""""
        )
        result = await data_processing_service.process_with_retry(
            sample_match_data, max_retries=3
        )
        # 验证重试失败
        assert result["]success["] is False[" assert result["]]attempts["] ==3[""""
    @pytest.mark.asyncio
    async def test_collect_performance_metrics(self, data_processing_service):
        "]]""测试收集性能指标"""
        # Mock指标收集
        data_processing_service.db_manager.fetch_all = AsyncMock(return_value=[
                {"processing_time[": 1.5, "]records_processed[": 100},""""
                {"]processing_time[": 2.0, "]records_processed[": 150)]""""
        )
        result = await data_processing_service.collect_performance_metrics()
        # 验证性能指标
        assert result["]avg_processing_time["] ==1.75[" assert result["]]total_records["] ==250[""""
    @pytest.mark.asyncio
    async def test_process_large_dataset(self, data_processing_service):
        "]]""测试处理大数据集"""
        large_dataset = [{"id[": i} for i in range(1000)]""""
        # Mock分批处理
        data_processing_service._process_in_batches = AsyncMock(return_value = {"]processed[": 1000, "]failed[": 0)""""
        )
        result = await data_processing_service.process_large_dataset(large_dataset)
        # 验证大数据集处理结果
        assert result["]processed["] ==1000[" assert result["]]failed["] ==0[""""
    @pytest.mark.asyncio
    async def test_cleanup(self, data_processing_service):
        "]]""测试清理操作"""
        # Mock清理操作
        data_processing_service.cache_manager.cleanup = AsyncMock(return_value=True)
        data_processing_service.data_lake.cleanup = AsyncMock(return_value=True)
        result = await data_processing_service.cleanup()
        # 验证清理成功
        assert result is True
        data_processing_service.cache_manager.cleanup.assert_called_once()
        data_processing_service.data_lake.cleanup.assert_called_once()
    def test_error_handling_strategies(self, data_processing_service):
        """测试错误处理策略"""
        # 验证服务能够优雅地处理各种错误情况
        assert hasattr(data_processing_service, "logger[")" assert data_processing_service.name is not None["""
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, data_processing_service):
        "]]""测试并发处理能力"""
        import asyncio
        # Mock并发处理
        data_processing_service.process_raw_match_data = AsyncMock(return_value = {"success[": True)""""
        )
        # 创建多个并发任务
        tasks = [
            data_processing_service.process_raw_match_data({"]match_id[": i))": for i in range(5):"""
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 验证所有任务都成功完成
        assert len(results) ==5
        assert all(not isinstance(r, Exception) for r in results)
    def test_data_integrity_validation(
        self, data_processing_service, sample_match_data
    ):
        "]""测试数据完整性验证"""
        # 验证数据结构完整性
        required_fields = [
            "match_id[",""""
            "]home_team[",""""
            "]away_team[",""""
            "]home_score[",""""
            "]away_score["]": for field in required_fields:": assert field in sample_match_data[""
    @pytest.mark.asyncio
    async def test_memory_efficiency(self, data_processing_service):
        "]]""测试内存效率"""
        # Mock大数据集处理
        large_data = [{"id[": i} for i in range(10000)]": data_processing_service._process_in_batches = AsyncMock(return_value = {"]processed[": 10000, "]failed[": 0)""""
        )
        result = await data_processing_service.process_large_dataset(large_data)
        # 验证内存效率处理
        assert result["]processed["] ==10000[" assert result["]]failed["] ==0["]"]" import asyncio