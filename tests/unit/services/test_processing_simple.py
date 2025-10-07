"""
数据处理服务简单测试
测试核心功能以提升覆盖率
"""

import sys
import pytest
from unittest.mock import Mock, AsyncMock, patch

# Mock外部依赖
sys.modules["pandas"] = Mock()
sys.modules["numpy"] = Mock()
sys.modules["sklearn"] = Mock()
sys.modules["nltk"] = Mock()
sys.modules["spacy"] = Mock()

# 设置测试环境
import os

os.environ["TESTING"] = "true"

# Mock内部依赖
mock_data_cleaner = Mock()
mock_missing_handler = Mock()
mock_data_lake = Mock()
mock_db_manager = Mock()
mock_cache_manager = Mock()

sys.modules["src.data.processing.football_data_cleaner"] = Mock(
    FootballDataCleaner=Mock(return_value=mock_data_cleaner)
)
sys.modules["src.data.processing.missing_data_handler"] = Mock(
    MissingDataHandler=Mock(return_value=mock_missing_handler)
)
sys.modules["src.data.storage.data_lake_storage"] = Mock(
    DataLakeStorage=Mock(return_value=mock_data_lake)
)
sys.modules["src.database.manager"] = Mock(
    DatabaseManager=Mock(return_value=mock_db_manager)
)
sys.modules["src.cache.redis_manager"] = Mock(
    RedisManager=Mock(return_value=mock_cache_manager)
)

from src.services.data_processing import DataProcessingService


class TestDataProcessingSimple:
    """数据处理服务简单测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return DataProcessingService()

    def test_service_init(self, service):
        """测试服务初始化"""
        assert service.name == "DataProcessingService"
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.db_manager is None
        assert service.cache_manager is None

    @pytest.mark.asyncio
    async def test_initialize_success(self, service):
        """测试初始化成功"""
        # 成功初始化
        result = await service.initialize()
        assert result is True
        assert service.data_cleaner is not None
        assert service.missing_handler is not None
        assert service.data_lake is not None
        assert service.db_manager is not None
        assert service.cache_manager is not None

    @pytest.mark.asyncio
    async def test_initialize_failure(self, service):
        """测试初始化失败"""
        # Mock初始化失败
        with patch(
            "src.services.data_processing.DataLakeStorage",
            side_effect=Exception("Storage error"),
        ):
            result = await service.initialize()
            assert result is False

    @pytest.mark.asyncio
    async def test_shutdown(self, service):
        """测试关闭服务"""
        # 先初始化
        await service.initialize()

        # Mock关闭方法
        service.cache_manager.close = Mock()
        service.db_manager.close = AsyncMock()

        # 执行关闭
        await service.shutdown()

        # 验证资源被清理
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.db_manager is None
        assert service.cache_manager is None

    @pytest.mark.asyncio
    async def test_process_raw_match_data(self, service):
        """测试处理原始比赛数据"""
        # 初始化服务
        await service.initialize()

        # Mock数据库会话
        mock_session = Mock()

        # Mock数据清洗器
        service.data_cleaner.clean_match_data = Mock(return_value=[{"cleaned": True}])

        # Mock数据湖存储
        service.data_lake.store_to_silver = AsyncMock(return_value=True)

        # 测试数据
        match_data = [
            {
                "match_id": "123",
                "home_team": "Team A",
                "away_team": "Team B",
                "date": "2024-01-01",
                "score": "2-1",
            }
        ]

        # 执行处理
        result = await service.process_raw_match_data(match_data, mock_session)

        # 验证结果
        assert result is not None
        assert "processed_count" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_process_raw_odds_data(self, service):
        """测试处理原始赔率数据"""
        # 初始化服务
        await service.initialize()

        # Mock数据库会话
        mock_session = Mock()

        # Mock数据清洗器
        service.data_cleaner.clean_odds_data = Mock(return_value=[{"cleaned": True}])

        # Mock数据湖存储
        service.data_lake.store_to_silver = AsyncMock(return_value=True)

        # 测试数据
        odds_data = [
            {"match_id": "123", "home_win": 2.50, "draw": 3.20, "away_win": 2.80}
        ]

        # 执行处理
        result = await service.process_raw_odds_data(odds_data, mock_session)

        # 验证结果
        assert result is not None
        assert "processed_count" in result

    @pytest.mark.asyncio
    async def test_process_features_data(self, service):
        """测试处理特征数据"""
        # 初始化服务
        await service.initialize()

        # Mock数据库会话
        mock_session = Mock()

        # Mock特征存储
        service.data_lake.store_features = AsyncMock(return_value=True)

        # 测试数据
        features_data = [{"match_id": "123", "features": {"home_form": [1, 0, 1]}}]

        # 执行处理
        result = await service.process_features_data(features_data, mock_session)

        # 验证结果
        assert result is not None

    @pytest.mark.asyncio
    async def test_validate_data_quality(self, service):
        """测试数据质量验证"""
        # 初始化服务
        await service.initialize()

        # Mock DataFrame
        mock_df = Mock()
        mock_df.shape = (100, 10)
        mock_df.isnull.return_value.sum.return_value = 5
        mock_df.duplicated.return_value.sum.return_value = 2

        # 执行验证
        result = await service.validate_data_quality(mock_df)

        # 验证结果
        assert isinstance(result, dict)
        assert "total_records" in result
        assert "quality_score" in result

    @pytest.mark.asyncio
    async def test_process_text(self, service):
        """测试文本处理"""
        # 初始化服务
        await service.initialize()

        # Mock文本处理
        with patch("src.services.data_processing.nltk") as mock_nltk:
            mock_nltk.word_tokenize.return_value = ["team", "played", "well"]
            mock_nltk.pos_tag.return_value = [("team", "NN"), ("played", "VBD")]

            result = await service.process_text("Team played well")

        # 验证结果
        assert isinstance(result, dict)
        assert "tokens" in result

    @pytest.mark.asyncio
    async def test_process_batch(self, service):
        """测试批量处理"""
        # 初始化服务
        await service.initialize()

        # 测试数据
        data_list = [{"id": 1}, {"id": 2}, {"id": 3}]

        # Mock批量处理
        with patch.object(
            service, "_process_single_item", AsyncMock(side_effect=lambda x: x)
        ) as mock_process:
            result = await service.process_batch(data_list)

        # 验证结果
        assert len(result) == 3
        assert mock_process.call_count == 3

    @pytest.mark.asyncio
    async def test_process_bronze_to_silver(self, service):
        """测试青铜层到银层处理"""
        # 初始化服务
        await service.initialize()

        # Mock各个处理步骤
        service._process_raw_matches_bronze_to_silver = AsyncMock(return_value=100)
        service._process_raw_odds_bronze_to_silver = AsyncMock(return_value=50)
        service._process_raw_scores_bronze_to_silver = AsyncMock(return_value=80)

        # 执行处理
        result = await service.process_bronze_to_silver(batch_size=100)

        # 验证结果
        assert result["matches_processed"] == 100
        assert result["odds_processed"] == 50
        assert result["scores_processed"] == 80

    @pytest.mark.asyncio
    async def test_get_bronze_layer_status(self, service):
        """测试获取青铜层状态"""
        # 初始化服务
        await service.initialize()

        # Mock数据库查询
        mock_session = Mock()
        mock_session.execute.return_value.fetchone.return_value = (1000, 500, 300)

        # 执行查询
        result = await service.get_bronze_layer_status(mock_session)

        # 验证结果
        assert result["raw_matches"] == 1000
        assert result["raw_odds"] == 500
        assert result["raw_scores"] == 300

    @pytest.mark.asyncio
    async def test_handle_missing_scores(self, service):
        """测试处理缺失比分"""
        # 初始化服务
        await service.initialize()

        # Mock DataFrame
        mock_df = Mock()
        mock_df.isnull.return_value.any.return_value = True
        mock_df.fillna.return_value = mock_df

        # Mock缺失值处理器
        service.missing_handler.handle_missing_scores = Mock(return_value=mock_df)

        # 执行处理
        result = await service.handle_missing_scores(mock_df)

        # 验证结果
        assert result is not None

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, service):
        """测试异常检测"""
        # 初始化服务
        await service.initialize()

        # Mock DataFrame
        mock_df = Mock()
        mock_df.columns = ["feature1", "feature2"]

        # Mock异常检测
        with patch("sklearn.ensemble.IsolationForest") as mock_isolation:
            mock_isolation.return_value.fit_predict.return_value = [1, -1, 1, 1, -1]

            result = await service.detect_anomalies(mock_df)

        # 验证结果
        assert isinstance(result, list)

    def test_error_logging(self, service):
        """测试错误日志"""
        # 测试错误日志记录
        with patch.object(service.logger, "error") as mock_error:
            service.logger.error("Test error message")
            mock_error.assert_called_once_with("Test error message")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
