"""
from unittest.mock import AsyncMock, Mock, patch
import asyncio
数据处理服务测试模块

测试 src/services/data_processing.py 的核心功能
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.data_processing import DataProcessingService


class TestDataProcessingService:
    """测试数据处理服务"""

    @pytest.fixture
    def service(self):
        """创建数据处理服务实例"""
        with patch("src.services.data_processing.FootballDataCleaner"):
            with patch("src.services.data_processing.MissingDataHandler"):
                with patch("src.services.data_processing.DataLakeStorage"):
                    with patch("src.services.data_processing.DatabaseManager"):
                        with patch("src.services.data_processing.RedisManager"):
                            service = DataProcessingService()
                            return service

    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return {
            "match_id": "12345",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "match_date": "2024-01-15",
            "home_score": 2,
            "away_score": 1,
            "league": "Premier League",
            "status": "finished",
        }

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return {
            "match_id": "12345",
            "bookmaker": "Bet365",
            "home_odds": 2.5,
            "draw_odds": 3.2,
            "away_odds": 2.8,
            "timestamp": "2024-01-14T10:00:00",
        }

    def test_init_service_name(self, service):
        """测试服务初始化时设置正确的名称"""
        assert service.name == "DataProcessingService"

    def test_init_components_none(self, service):
        """测试初始化时组件为None"""
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.db_manager is None
        assert service.cache_manager is None

    @pytest.mark.asyncio
    async def test_initialize_success(self, service):
        """测试服务初始化成功"""
        # Mock所有组件的创建
        mock_cleaner = Mock()
        mock_handler = Mock()
        mock_data_lake = Mock()
        mock_db_manager = Mock()
        mock_cache_manager = Mock()

        with patch(
            "src.services.data_processing.FootballDataCleaner",
            return_value=mock_cleaner,
        ):
            with patch(
                "src.services.data_processing.MissingDataHandler",
                return_value=mock_handler,
            ):
                with patch(
                    "src.services.data_processing.DataLakeStorage",
                    return_value=mock_data_lake,
                ):
                    with patch(
                        "src.services.data_processing.DatabaseManager",
                        return_value=mock_db_manager,
                    ):
                        with patch(
                            "src.services.data_processing.RedisManager",
                            return_value=mock_cache_manager,
                        ):
                            result = await service.initialize()

        assert result is True
        assert service.data_cleaner is not None
        assert service.missing_handler is not None
        assert service.data_lake is not None
        assert service.db_manager is not None
        assert service.cache_manager is not None

    @pytest.mark.asyncio
    async def test_shutdown_success(self, service):
        """测试服务关闭成功"""
        # 设置mock组件
        service.cache_manager = Mock()
        service.cache_manager.close = AsyncMock()
        service.db_manager = Mock()
        service.db_manager.close = AsyncMock()

        await service.shutdown()

        # 验证关闭方法被调用
        service.cache_manager.close.assert_called_once()
        service.db_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_raw_match_data_success(self, service, sample_match_data):
        """测试处理原始比赛数据 - 成功"""
        # 设置mock组件
        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_match_data = AsyncMock(
            return_value=sample_match_data
        )
        service.missing_handler = AsyncMock()
        service.missing_handler.handle_missing_match_data = AsyncMock(
            return_value=sample_match_data
        )

        result = await service.process_raw_match_data(sample_match_data)

        assert result is not None
        assert isinstance(result, dict)
        service.data_cleaner.clean_match_data.assert_called_once()
        service.missing_handler.handle_missing_match_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_raw_match_data_invalid_input(self, service):
        """测试处理原始比赛数据 - 无效输入"""
        result = await service.process_raw_match_data(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_success(self, service, sample_odds_data):
        """测试处理原始赔率数据 - 成功"""
        # 设置mock组件
        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_odds_data = AsyncMock(return_value=sample_odds_data)
        service.missing_handler = AsyncMock()
        service.missing_handler.handle_missing_odds_data = AsyncMock(
            return_value=sample_odds_data
        )

        result = await service.process_raw_odds_data(sample_odds_data)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_process_batch_matches_success(self, service, sample_match_data):
        """测试批量处理比赛数据 - 成功"""
        match_list = [sample_match_data.copy() for _ in range(3)]

        # Mock process_raw_match_data方法
        service.process_raw_match_data = AsyncMock(return_value=sample_match_data)

        results = await service.process_batch_matches(match_list)

        assert isinstance(results, list)
        assert len(results) == 3
        assert service.process_raw_match_data.call_count == 3

    @pytest.mark.asyncio
    async def test_process_batch_matches_empty_list(self, service):
        """测试批量处理比赛数据 - 空列表"""
        results = await service.process_batch_matches([])

        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_validate_data_quality_valid_match(self, service):
        """测试数据质量验证 - 有效比赛数据"""
        valid_match_data = {
            "match_id": "12345",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "match_date": "2024-01-15",
            "home_score": 2,
            "away_score": 1,
        }

        result = await service.validate_data_quality(valid_match_data, "match")

        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "issues" in result

    @pytest.mark.asyncio
    async def test_validate_data_quality_invalid_match(self, service):
        """测试数据质量验证 - 无效比赛数据"""
        invalid_match_data = {
            "match_id": "",  # 空的match_id
            "home_team": "Arsenal",
            "away_team": "Arsenal",  # 相同的队伍
            "home_score": -1,  # 无效分数
            "away_score": 10,  # 可疑高分
        }

        result = await service.validate_data_quality(invalid_match_data, "match")

        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "issues" in result

    @pytest.mark.asyncio
    async def test_validate_data_quality_valid_odds(self, service):
        """测试数据质量验证 - 有效赔率数据"""
        valid_odds_data = {
            "match_id": "12345",
            "bookmaker": "Bet365",
            "home_odds": 2.5,
            "draw_odds": 3.2,
            "away_odds": 2.8,
        }

        result = await service.validate_data_quality(valid_odds_data, "odds")

        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "issues" in result

    @pytest.mark.asyncio
    async def test_process_text(self, service):
        """测试处理文本数据"""
        text = "This is a test text for processing"

        result = await service.process_text(text)

        assert isinstance(result, dict)
        assert "processed_text" in result
        assert result["processed_text"] == text

    @pytest.mark.asyncio
    async def test_process_batch_data_list(self, service):
        """测试批量处理数据列表"""
        data_list = [
            {"id": 1, "data": "test1"},
            {"id": 2, "data": "test2"},
            {"id": 3, "data": "test3"},
        ]

        result = await service.process_batch(data_list)

        assert isinstance(result, list)
        assert len(result) == len(data_list)

    @pytest.mark.asyncio
    async def test_get_bronze_layer_status(self, service):
        """测试获取青铜层状态"""
        # Mock数据库查询
        service.db_manager = Mock()
        service.db_manager.execute_query = AsyncMock(
            return_value=[
                {"table_name": "raw_matches", "count": 100},
                {"table_name": "raw_odds", "count": 250},
            ]
        )

        status = await service.get_bronze_layer_status()

        assert isinstance(status, dict)
        assert "raw_matches" in status or "total_records" in status

    def test_service_inheritance(self, service):
        """测试服务继承关系"""
        from src.services.base import BaseService

        assert isinstance(service, BaseService)

    def test_service_has_required_methods(self, service):
        """测试服务具有必需的方法"""
        assert hasattr(service, "initialize")
        assert hasattr(service, "shutdown")
        assert hasattr(service, "process_raw_match_data")
        assert hasattr(service, "process_raw_odds_data")
        assert hasattr(service, "validate_data_quality")

    def test_service_components_attributes(self, service):
        """测试服务组件属性存在"""
        assert hasattr(service, "data_cleaner")
        assert hasattr(service, "missing_handler")
        assert hasattr(service, "data_lake")
        assert hasattr(service, "db_manager")
        assert hasattr(service, "cache_manager")

    @pytest.mark.asyncio
    async def test_process_bronze_to_silver_basic(self, service):
        """测试青铜层到白银层的基础处理"""
        # Mock相关方法
        service._process_raw_matches_bronze_to_silver = AsyncMock(return_value=10)
        service._process_raw_odds_bronze_to_silver = AsyncMock(return_value=25)
        service._process_raw_scores_bronze_to_silver = AsyncMock(return_value=5)

        result = await service.process_bronze_to_silver(batch_size=50)

        assert isinstance(result, dict)
        assert "matches_processed" in result or "total_processed" in result
