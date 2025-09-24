"""
足球预测系统数据处理服务测试模块

全面测试 src/services/data_processing.py 的所有功能
包括数据清洗、缺失值处理、质量验证、批量处理和层间数据转换。

基于 DATA_DESIGN.md 第4节数据处理设计。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pandas as pd
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
            "external_match_id": "12345",
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2024-01-15T15:00:00",
            "home_score": 2,
            "away_score": 1,
            "league": "Premier League",
            "status": "finished",
        }

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return [
            {
                "match_id": "12345",
                "bookmaker": "Bet365",
                "home_odds": 1.85,
                "draw_odds": 3.40,
                "away_odds": 4.20,
                "timestamp": "2024-01-14T10:00:00",
            },
            {
                "match_id": "12345",
                "bookmaker": "William Hill",
                "home_odds": 1.90,
                "draw_odds": 3.30,
                "away_odds": 4.10,
                "timestamp": "2024-01-14T11:00:00",
            },
        ]

    @pytest.fixture
    def sample_features_data(self):
        """示例特征数据"""
        return pd.DataFrame(
            {
                "match_id": [1001, 1002],
                "home_form": [0.8, 0.6],
                "away_form": [0.7, 0.5],
                "home_goals_avg": [2.1, 1.8],
                "away_goals_avg": [1.2, 1.5],
            }
        )

    @pytest.fixture
    def sample_batch_matches(self):
        """示例批量比赛数据"""
        return [
            {
                "external_match_id": "12345",
                "home_team_id": 1,
                "away_team_id": 2,
                "match_time": "2024-01-15T15:00:00",
            },
            {
                "external_match_id": "12346",
                "home_team_id": 3,
                "away_team_id": 4,
                "match_time": "2024-01-16T15:00:00",
            },
            {
                "external_match_id": "12347",
                "home_team_id": 5,
                "away_team_id": 6,
                "match_time": "2024-01-17T15:00:00",
            },
        ]

    # 测试服务初始化
    def test_service_name(self, service):
        """测试服务名称"""
        assert service.name == "DataProcessingService"

    def test_initial_components_none(self, service):
        """测试初始组件为None"""
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.db_manager is None
        assert service.cache_manager is None

    # 测试服务初始化过程
    @pytest.mark.asyncio
    async def test_initialize_success(self, service):
        """测试成功初始化服务"""
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
    async def test_initialize_failure(self, service):
        """测试初始化失败"""
        with patch(
            "src.services.data_processing.FootballDataCleaner",
            side_effect=Exception("Init failed"),
        ):
            result = await service.initialize()

        assert result is False

    # 测试服务关闭
    @pytest.mark.asyncio
    async def test_shutdown_success(self, service):
        """测试成功关闭服务"""
        # 设置mock组件
        cache_manager_mock = AsyncMock()
        cache_manager_mock.close = AsyncMock()
        db_manager_mock = AsyncMock()
        db_manager_mock.close = AsyncMock()

        service.cache_manager = cache_manager_mock
        service.db_manager = db_manager_mock

        await service.shutdown()

        # 验证组件被清理
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.cache_manager is None
        assert service.db_manager is None

        # 验证关闭方法被调用
        cache_manager_mock.close.assert_called_once()
        db_manager_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_with_sync_cache_manager(self, service):
        """测试同步缓存管理器的关闭"""
        cache_manager_mock = Mock()
        cache_manager_mock.close = Mock()  # 同步方法
        db_manager_mock = AsyncMock()
        db_manager_mock.close = AsyncMock()

        service.cache_manager = cache_manager_mock
        service.db_manager = db_manager_mock

        await service.shutdown()

        cache_manager_mock.close.assert_called_once()
        db_manager_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_with_mock_cache_manager(self, service):
        """测试mock缓存管理器的关闭"""
        cache_manager_mock = Mock()
        cache_manager_mock.close = Mock()
        cache_manager_mock.close._mock_name = "mock_close"  # mock属性
        db_manager_mock = AsyncMock()
        db_manager_mock.close = AsyncMock()

        service.cache_manager = cache_manager_mock
        service.db_manager = db_manager_mock

        await service.shutdown()

        cache_manager_mock.close.assert_called_once()
        db_manager_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_with_none_components(self, service):
        """测试组件为None时的关闭"""
        service.cache_manager = None
        service.db_manager = None

        await service.shutdown()

        # 不应该抛出异常
        assert True

    # 测试处理原始比赛数据
    @pytest.mark.asyncio
    async def test_process_raw_match_data_single_success(
        self, service, sample_match_data
    ):
        """测试成功处理单个比赛数据"""
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
        assert result == sample_match_data
        service.data_cleaner.clean_match_data.assert_called_once_with(sample_match_data)
        service.missing_handler.handle_missing_match_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_raw_match_data_list_success(
        self, service, sample_batch_matches
    ):
        """测试成功处理比赛数据列表"""
        # 设置mock组件
        processed_match = {"external_match_id": "12345", "processed": True}
        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_match_data = AsyncMock(return_value=processed_match)
        service.missing_handler = AsyncMock()
        service.missing_handler.handle_missing_match_data = AsyncMock(
            return_value=processed_match
        )

        result = await service.process_raw_match_data(sample_batch_matches)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert service.data_cleaner.clean_match_data.call_count == 3

    @pytest.mark.asyncio
    async def test_process_raw_match_data_empty_list(self, service):
        """测试处理空的比赛数据列表"""
        result = await service.process_raw_match_data([])

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @pytest.mark.asyncio
    async def test_process_raw_match_data_none_input(self, service):
        """测试处理None输入"""
        result = await service.process_raw_match_data(None)

        assert result is None

    @pytest.mark.asyncio
    async def test_process_raw_match_data_cleaner_failure(
        self, service, sample_match_data
    ):
        """测试数据清洗失败"""
        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_match_data = AsyncMock(return_value=None)

        result = await service.process_raw_match_data(sample_match_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_process_raw_match_data_cleaner_empty_result(
        self, service, sample_match_data
    ):
        """测试数据清洗返回空结果"""
        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_match_data = AsyncMock(return_value=pd.DataFrame())

        result = await service.process_raw_match_data(sample_match_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_process_raw_match_data_with_caching(
        self, service, sample_match_data
    ):
        """测试带缓存的比赛数据处理"""
        # 设置缓存管理器
        service.cache_manager = AsyncMock()
        service.cache_manager.aget = AsyncMock(return_value=None)  # 缓存未命中
        service.cache_manager.aset = AsyncMock()

        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_match_data = AsyncMock(
            return_value=sample_match_data
        )
        service.missing_handler = AsyncMock()
        service.missing_handler.handle_missing_match_data = AsyncMock(
            return_value=sample_match_data
        )

        result = await service.process_raw_match_data(sample_match_data)

        # 验证缓存操作
        service.cache_manager.aget.assert_called_once()
        service.cache_manager.aset.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_raw_match_data_cache_hit(self, service, sample_match_data):
        """测试缓存命中时的处理"""
        # 设置缓存管理器
        service.cache_manager = AsyncMock()
        service.cache_manager.aget = AsyncMock(return_value=sample_match_data)  # 缓存命中

        service.data_cleaner = AsyncMock()
        service.missing_handler = AsyncMock()

        result = await service.process_raw_match_data(sample_match_data)

        # 验证从缓存获取数据
        assert result == sample_match_data
        service.cache_manager.aget.assert_called_once()
        service.data_cleaner.clean_match_data.assert_not_called()

    # 测试处理原始赔率数据
    @pytest.mark.asyncio
    async def test_process_raw_odds_data_success(self, service, sample_odds_data):
        """测试成功处理赔率数据"""
        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_odds_data = AsyncMock(return_value=sample_odds_data)

        result = await service.process_raw_odds_data(sample_odds_data)

        assert result == sample_odds_data
        service.data_cleaner.clean_odds_data.assert_called_once_with(sample_odds_data)

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_cleaner_failure(
        self, service, sample_odds_data
    ):
        """测试赔率数据清洗失败"""
        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_odds_data = AsyncMock(return_value=[])

        result = await service.process_raw_odds_data(sample_odds_data)

        assert result == []

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_no_cleaner(self, service, sample_odds_data):
        """测试没有数据清洗器时的处理"""
        service.data_cleaner = None

        result = await service.process_raw_odds_data(sample_odds_data)

        assert result == []

    # 测试处理特征数据
    @pytest.mark.asyncio
    async def test_process_features_data_success(self, service, sample_features_data):
        """测试成功处理特征数据"""
        service.missing_handler = AsyncMock()
        processed_features = sample_features_data.copy()
        processed_features["processed"] = True
        service.missing_handler.handle_missing_features = AsyncMock(
            return_value=processed_features
        )

        result = await service.process_features_data(1001, sample_features_data)

        assert result.equals(processed_features)
        service.missing_handler.handle_missing_features.assert_called_once_with(
            1001, sample_features_data
        )

    @pytest.mark.asyncio
    async def test_process_features_data_no_handler(
        self, service, sample_features_data
    ):
        """测试没有缺失值处理器时的处理"""
        service.missing_handler = None

        result = await service.process_features_data(1001, sample_features_data)

        assert result.equals(sample_features_data)

    @pytest.mark.asyncio
    async def test_process_features_data_handler_failure(
        self, service, sample_features_data
    ):
        """测试特征数据处理失败"""
        service.missing_handler = AsyncMock()
        service.missing_handler.handle_missing_features = AsyncMock(
            side_effect=Exception("Processing failed")
        )

        result = await service.process_features_data(1001, sample_features_data)

        assert result.equals(sample_features_data)  # 失败时返回原始数据

    # 测试批量处理比赛数据
    @pytest.mark.asyncio
    async def test_process_batch_matches_success(self, service, sample_batch_matches):
        """测试成功批量处理比赛数据"""
        processed_match = {"external_match_id": "12345", "processed": True}
        service.process_raw_match_data = AsyncMock(return_value=processed_match)

        result = await service.process_batch_matches(sample_batch_matches)

        assert len(result) == 3
        assert service.process_raw_match_data.call_count == 3

    @pytest.mark.asyncio
    async def test_process_batch_matches_partial_failure(
        self, service, sample_batch_matches
    ):
        """测试批量处理部分失败"""

        def side_effect(match_data):
            if match_data.get("external_match_id") == "12346":
                raise Exception("Processing failed")
            return {
                "external_match_id": match_data["external_match_id"],
                "processed": True,
            }

        service.process_raw_match_data = AsyncMock(side_effect=side_effect)

        result = await service.process_batch_matches(sample_batch_matches)

        assert len(result) == 2  # 只有2个成功
        assert service.process_raw_match_data.call_count == 3

    @pytest.mark.asyncio
    async def test_process_batch_matches_empty_input(self, service):
        """测试批量处理空输入"""
        result = await service.process_batch_matches([])

        assert result == []

    # 测试数据质量验证
    @pytest.mark.asyncio
    async def test_validate_data_quality_valid_match(self, service):
        """测试验证有效比赛数据"""
        valid_match = {
            "external_match_id": "12345",
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2024-01-15T15:00:00",
            "home_score": 2,
            "away_score": 1,
        }

        result = await service.validate_data_quality(valid_match, "match")

        assert result["is_valid"] is True
        assert len(result["issues"]) == 0
        assert result["data_type"] == "match"

    @pytest.mark.asyncio
    async def test_validate_data_quality_invalid_match_missing_fields(self, service):
        """测试验证缺失字段的比赛数据"""
        invalid_match = {
            "external_match_id": "",  # 空字段
            "home_team_id": 1,
            # 缺少 away_team_id 和 match_time
            "home_score": -1,  # 负分数
            "away_score": 25,  # 异常高分
        }

        result = await service.validate_data_quality(invalid_match, "match")

        assert result["is_valid"] is False
        assert len(result["issues"]) > 0
        assert any("Missing required field" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_data_quality_match_warnings(self, service):
        """测试比赛数据警告"""
        match_with_warnings = {
            "external_match_id": "12345",
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2024-01-15T15:00:00",
            "home_score": 15,  # 高分警告
            "away_score": 12,  # 高分警告
        }

        result = await service.validate_data_quality(match_with_warnings, "match")

        assert result["is_valid"] is True  # 仍然有效，但有警告
        assert len(result["warnings"]) > 0
        assert any("Unusually high scores" in warning for warning in result["warnings"])

    @pytest.mark.asyncio
    async def test_validate_data_quality_valid_odds(self, service):
        """测试验证有效赔率数据"""
        valid_odds = {
            "outcomes": [
                {"price": 1.85},
                {"price": 3.40},
                {"price": 4.20},
            ]
        }

        result = await service.validate_data_quality(valid_odds, "odds")

        assert result["is_valid"] is True
        assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_validate_data_quality_invalid_odds(self, service):
        """测试验证无效赔率数据"""
        invalid_odds = {
            "outcomes": [
                {"price": 0.5},  # 低于最小赔率
                {"price": 1.01},  # 边界值
                {"price": "invalid"},  # 无效类型
            ]
        }

        result = await service.validate_data_quality(invalid_odds, "odds")

        assert result["is_valid"] is False
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_validate_data_quality_no_outcomes(self, service):
        """测试没有outcomes的赔率数据"""
        no_outcomes_odds = {}

        result = await service.validate_data_quality(no_outcomes_odds, "odds")

        assert result["is_valid"] is False
        assert any("No odds outcomes found" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_data_quality_validation_error(self, service):
        """测试验证过程中的错误"""
        with patch.object(
            service, "validate_data_quality", side_effect=Exception("Validation error")
        ):
            result = await service.validate_data_quality({}, "match")

        assert result["is_valid"] is False
        assert any("Validation error" in issue for issue in result["issues"])

    # 测试向后兼容方法
    @pytest.mark.asyncio
    async def test_process_text(self, service):
        """测试文本处理"""
        text = "  This is a test text  "

        result = await service.process_text(text)

        assert result["processed_text"] == text.strip()
        assert result["word_count"] == len(text.split())
        assert result["character_count"] == len(text)

    @pytest.mark.asyncio
    async def test_process_batch_mixed_data(self, service):
        """测试批量处理混合数据类型"""
        data_list = [
            "text data",
            {"key": "value"},
            123,
            ["list", "data"],
        ]

        result = await service.process_batch(data_list)

        assert len(result) == 4
        assert result[0]["processed_text"] == "text data"
        assert result[1]["processed"] is True
        assert result[2]["original_data"] == 123
        assert result[3]["original_data"] == ["list", "data"]

    # 测试Bronze到Silver层数据处理
    @pytest.mark.asyncio
    async def test_process_bronze_to_silver_success(self, service):
        """测试成功处理Bronze到Silver层"""
        # 设置mock组件
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = AsyncMock()
        service.db_manager = Mock()

        # Mock各个处理方法
        service._process_raw_matches_bronze_to_silver = AsyncMock(return_value=10)
        service._process_raw_odds_bronze_to_silver = AsyncMock(return_value=25)
        service._process_raw_scores_bronze_to_silver = AsyncMock(return_value=5)

        result = await service.process_bronze_to_silver(batch_size=50)

        assert result["processed_matches"] == 10
        assert result["processed_odds"] == 25
        assert result["processed_scores"] == 5
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_process_bronze_to_silver_incomplete_initialization(self, service):
        """测试初始化不完整的Bronze到Silver处理"""
        service.data_cleaner = None  # 缺少组件

        result = await service.process_bronze_to_silver()

        assert "error" in result

    @pytest.mark.asyncio
    async def test_process_bronze_to_silver_processing_error(self, service):
        """测试Bronze到Silver处理错误"""
        # 设置mock组件
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = AsyncMock()
        service.db_manager = Mock()

        # Mock处理方法出错
        service._process_raw_matches_bronze_to_silver = AsyncMock(
            side_effect=Exception("Processing failed")
        )

        result = await service.process_bronze_to_silver()

        assert result["errors"] == 1

    # 测试处理原始比赛数据到Silver层
    @pytest.mark.asyncio
    async def test_process_raw_matches_bronze_to_silver_success(self, service):
        """测试成功处理原始比赛数据到Silver层"""
        # 设置数据库mock
        mock_session = Mock()
        mock_raw_match = Mock()
        mock_raw_match.id = 1
        mock_raw_match.raw_data = sample_match_data
        mock_raw_match.mark_processed = Mock()

        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = [
            mock_raw_match
        ]
        mock_session.query.return_value = mock_query
        mock_session.commit = Mock()
        mock_session.rollback = Mock()

        service.db_manager = Mock()
        service.db_manager.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        service.db_manager.get_session.return_value.__exit__ = Mock(return_value=None)

        # 设置数据清洗器
        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_match_data = AsyncMock(
            return_value=sample_match_data
        )

        # 设置缺失值处理器
        service.missing_handler = AsyncMock()
        service.missing_handler.handle_missing_match_data = AsyncMock(
            return_value=sample_match_data
        )

        # 设置数据湖
        service.data_lake = AsyncMock()
        service.data_lake.save_historical_data = AsyncMock()

        result = await service._process_raw_matches_bronze_to_silver(batch_size=50)

        assert result == 1
        mock_raw_match.mark_processed.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_raw_matches_bronze_to_silver_no_data(self, service):
        """测试没有数据需要处理的情况"""
        # 设置数据库mock
        mock_session = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = []
        mock_session.query.return_value = mock_query

        service.db_manager = Mock()
        service.db_manager.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        service.db_manager.get_session.return_value.__exit__ = Mock(return_value=None)

        result = await service._process_raw_matches_bronze_to_silver(batch_size=50)

        assert result == 0

    @pytest.mark.asyncio
    async def test_process_raw_matches_bronze_to_silver_cleaning_failure(self, service):
        """测试数据清洗失败的情况"""
        # 设置数据库mock
        mock_session = Mock()
        mock_raw_match = Mock()
        mock_raw_match.id = 1
        mock_raw_match.raw_data = sample_match_data

        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = [
            mock_raw_match
        ]
        mock_session.query.return_value = mock_query
        mock_session.commit = Mock()

        service.db_manager = Mock()
        service.db_manager.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        service.db_manager.get_session.return_value.__exit__ = Mock(return_value=None)

        # 设置数据清洗器失败
        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_match_data = AsyncMock(return_value=None)

        # 设置缺失值处理器
        service.missing_handler = AsyncMock()

        result = await service._process_raw_matches_bronze_to_silver(batch_size=50)

        assert result == 0  # 没有成功处理的记录
        mock_raw_match.mark_processed.assert_not_called()

    # 测试处理原始赔率数据到Silver层
    @pytest.mark.asyncio
    async def test_process_raw_odds_bronze_to_silver_success(self, service):
        """测试成功处理原始赔率数据到Silver层"""
        # 设置数据库mock
        mock_session = Mock()
        mock_raw_odds = Mock()
        mock_raw_odds.id = 1
        mock_raw_odds.external_match_id = 12345
        mock_raw_odds.raw_data = {"home_odds": 1.85}
        mock_raw_odds.mark_processed = Mock()

        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = [
            mock_raw_odds
        ]
        mock_session.query.return_value = mock_query
        mock_session.commit = Mock()

        service.db_manager = Mock()
        service.db_manager.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        service.db_manager.get_session.return_value.__exit__ = Mock(return_value=None)

        # 设置数据清洗器
        service.data_cleaner = AsyncMock()
        service.data_cleaner.clean_odds_data = AsyncMock(
            return_value=[{"home_odds": 1.85}]
        )

        # 设置数据湖
        service.data_lake = AsyncMock()
        service.data_lake.save_historical_data = AsyncMock()

        result = await service._process_raw_odds_bronze_to_silver(batch_size=50)

        assert result == 1
        mock_raw_odds.mark_processed.assert_called_once()
        mock_session.commit.assert_called_once()

    # 测试处理原始比分数据到Silver层
    @pytest.mark.asyncio
    async def test_process_raw_scores_bronze_to_silver_success(self, service):
        """测试成功处理原始比分数据到Silver层"""
        # 设置数据库mock
        mock_session = Mock()
        mock_raw_scores = Mock()
        mock_raw_scores.id = 1
        mock_raw_scores.external_match_id = 12345
        mock_raw_scores.get_score_info = Mock(
            return_value={
                "home_score": 2,
                "away_score": 1,
                "half_time_home": 1,
                "half_time_away": 0,
                "status": "finished",
                "minute": 90,
                "events": [],
            }
        )
        mock_raw_scores.mark_processed = Mock()
        mock_raw_scores.is_live = False
        mock_raw_scores.is_finished = True
        mock_raw_scores.collected_at = datetime.now()

        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = [
            mock_raw_scores
        ]
        mock_session.query.return_value = mock_query
        mock_session.commit = Mock()

        service.db_manager = Mock()
        service.db_manager.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        service.db_manager.get_session.return_value.__exit__ = Mock(return_value=None)

        # 设置数据清洗器
        service.data_cleaner = Mock()
        service.data_cleaner._validate_score = Mock(side_effect=lambda x: x)
        service.data_cleaner._standardize_match_status = Mock(return_value="finished")

        # 设置数据湖
        service.data_lake = AsyncMock()
        service.data_lake.save_historical_data = AsyncMock()

        result = await service._process_raw_scores_bronze_to_silver(batch_size=50)

        assert result == 1
        mock_raw_scores.mark_processed.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_raw_scores_bronze_to_silver_invalid_data(self, service):
        """测试无效比分数据的处理"""
        # 设置数据库mock
        mock_session = Mock()
        mock_raw_scores = Mock()
        mock_raw_scores.id = 1
        mock_raw_scores.get_score_info = Mock(return_value=None)  # 无效数据

        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = [
            mock_raw_scores
        ]
        mock_session.query.return_value = mock_query
        mock_session.commit = Mock()

        service.db_manager = Mock()
        service.db_manager.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        service.db_manager.get_session.return_value.__exit__ = Mock(return_value=None)

        result = await service._process_raw_scores_bronze_to_silver(batch_size=50)

        assert result == 0  # 没有成功处理的记录

    # 测试获取Bronze层状态
    @pytest.mark.asyncio
    async def test_get_bronze_layer_status_success(self, service):
        """测试成功获取Bronze层状态"""
        # 设置数据库mock
        mock_session = Mock()

        # Mock比赛数据查询
        mock_query_matches = Mock()
        mock_query_matches.count.return_value = 100
        mock_query_matches.filter.return_value.count.return_value = 80

        # Mock赔率数据查询
        mock_query_odds = Mock()
        mock_query_odds.count.return_value = 200
        mock_query_odds.filter.return_value.count.return_value = 150

        # Mock比分数据查询
        mock_query_scores = Mock()
        mock_query_scores.count.return_value = 50
        mock_query_scores.filter.return_value.count.return_value = 40

        def query_side_effect(model):
            if model.__name__ == "RawMatchData":
                return mock_query_matches
            elif model.__name__ == "RawOddsData":
                return mock_query_odds
            elif model.__name__ == "RawScoresData":
                return mock_query_scores
            return Mock()

        mock_session.query.side_effect = query_side_effect

        service.db_manager = Mock()
        service.db_manager.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        service.db_manager.get_session.return_value.__exit__ = Mock(return_value=None)

        result = await service.get_bronze_layer_status()

        assert result["matches"]["total"] == 100
        assert result["matches"]["processed"] == 80
        assert result["matches"]["pending"] == 20
        assert result["odds"]["total"] == 200
        assert result["odds"]["processed"] == 150
        assert result["odds"]["pending"] == 50
        assert result["scores"]["total"] == 50
        assert result["scores"]["processed"] == 40
        assert result["scores"]["pending"] == 10

    @pytest.mark.asyncio
    async def test_get_bronze_layer_status_no_db_manager(self, service):
        """测试没有数据库管理器时的状态获取"""
        service.db_manager = None

        result = await service.get_bronze_layer_status()

        assert "error" in result

    # 测试处理缺失值的方法
    @pytest.mark.asyncio
    async def test_handle_missing_scores_success(self, service, sample_features_data):
        """测试成功处理分数缺失值"""
        service.missing_handler = AsyncMock()
        service.missing_handler.interpolate_scores = AsyncMock(
            return_value=sample_features_data
        )

        result = await service.handle_missing_scores(sample_features_data)

        assert result.equals(sample_features_data)
        service.missing_handler.interpolate_scores.assert_called_once_with(
            sample_features_data
        )

    @pytest.mark.asyncio
    async def test_handle_missing_scores_no_handler(
        self, service, sample_features_data
    ):
        """测试没有缺失值处理器时的分数处理"""
        service.missing_handler = None

        result = await service.handle_missing_scores(sample_features_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_handle_missing_scores_handler_no_support(
        self, service, sample_features_data
    ):
        """测试缺失值处理器不支持分数插值"""
        service.missing_handler = Mock()
        # 没有interpolate_scores方法

        result = await service.handle_missing_scores(sample_features_data)

        assert result.equals(sample_features_data)  # 返回原始数据

    @pytest.mark.asyncio
    async def test_handle_missing_team_data_success(
        self, service, sample_features_data
    ):
        """测试成功处理球队数据缺失值"""
        service.missing_handler = AsyncMock()
        service.missing_handler.impute_team_data = AsyncMock(
            return_value=sample_features_data
        )

        result = await service.handle_missing_team_data(sample_features_data)

        assert result.equals(sample_features_data)
        service.missing_handler.impute_team_data.assert_called_once_with(
            sample_features_data
        )

    @pytest.mark.asyncio
    async def test_handle_missing_team_data_failure(
        self, service, sample_features_data
    ):
        """测试球队数据缺失值处理失败"""
        service.missing_handler = AsyncMock()
        service.missing_handler.impute_team_data = AsyncMock(
            side_effect=Exception("Imputation failed")
        )

        result = await service.handle_missing_team_data(sample_features_data)

        assert result is None

    # 测试异常检测
    @pytest.mark.asyncio
    async def test_detect_anomalies_success(self, service, sample_features_data):
        """测试成功检测异常"""
        expected_anomalies = [{"type": "outlier", "value": 100}]
        service.missing_handler = AsyncMock()
        service.missing_handler.detect_anomalies = AsyncMock(
            return_value=expected_anomalies
        )

        result = await service.detect_anomalies(sample_features_data)

        assert result == expected_anomalies
        service.missing_handler.detect_anomalies.assert_called_once_with(
            sample_features_data
        )

    @pytest.mark.asyncio
    async def test_detect_anomalies_no_handler(self, service, sample_features_data):
        """测试没有缺失值处理器时的异常检测"""
        service.missing_handler = None

        result = await service.detect_anomalies(sample_features_data)

        assert result == []

    # 测试存储处理后的数据
    @pytest.mark.asyncio
    async def test_store_processed_data_success(self, service, sample_features_data):
        """测试成功存储处理后的数据"""
        service.data_lake = AsyncMock()
        service.data_lake.store_dataframe = AsyncMock()
        service.db_manager = AsyncMock()
        service.db_manager.bulk_insert = AsyncMock()
        service.cache_manager = AsyncMock()
        service.cache_manager.set_json = AsyncMock()

        result = await service.store_processed_data(
            sample_features_data, "test_table", cache_results=True
        )

        assert result is True
        service.data_lake.store_dataframe.assert_called_once()
        service.db_manager.bulk_insert.assert_called_once()
        service.cache_manager.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_processed_data_partial_failure(
        self, service, sample_features_data
    ):
        """测试存储部分失败"""
        service.data_lake = AsyncMock()
        service.data_lake.store_dataframe = AsyncMock(
            side_effect=Exception("Lake failed")
        )
        service.db_manager = AsyncMock()
        service.db_manager.bulk_insert = AsyncMock()
        service.cache_manager = AsyncMock()
        service.cache_manager.set_json = AsyncMock()

        result = await service.store_processed_data(
            sample_features_data, "test_table", cache_results=True
        )

        assert result is False  # 部分失败返回False

    @pytest.mark.asyncio
    async def test_store_processed_data_cache_failure(
        self, service, sample_features_data
    ):
        """测试缓存失败但不影响整体存储"""
        service.data_lake = AsyncMock()
        service.data_lake.store_dataframe = AsyncMock()
        service.db_manager = AsyncMock()
        service.db_manager.bulk_insert = AsyncMock()
        service.cache_manager = AsyncMock()
        service.cache_manager.set_json = AsyncMock(
            side_effect=Exception("Cache failed")
        )

        result = await service.store_processed_data(
            sample_features_data, "test_table", cache_results=True
        )

        assert result is True  # 缓存失败不影响整体结果

    # 测试缓存处理结果
    @pytest.mark.asyncio
    async def test_cache_processing_results_success(self, service):
        """测试成功缓存处理结果"""
        test_data = {"result": "test"}
        service.cache_manager = AsyncMock()
        service.cache_manager.set_json = AsyncMock(return_value=True)

        result = await service.cache_processing_results("test_key", test_data, ttl=3600)

        assert result is True
        service.cache_manager.set_json.assert_called_once_with(
            "test_key", test_data, ttl=3600
        )

    @pytest.mark.asyncio
    async def test_cache_processing_results_no_manager(self, service):
        """测试没有缓存管理器时的缓存操作"""
        service.cache_manager = None

        result = await service.cache_processing_results("test_key", {"result": "test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_cache_processing_results_no_json_support(self, service):
        """测试缓存管理器不支持JSON存储"""
        service.cache_manager = Mock()
        # 没有set_json方法

        result = await service.cache_processing_results("test_key", {"result": "test"})

        assert result is False

    # 测试获取缓存结果
    @pytest.mark.asyncio
    async def test_get_cached_results_success(self, service):
        """测试成功获取缓存结果"""
        expected_data = {"result": "cached"}
        service.cache_manager = AsyncMock()
        service.cache_manager.get_json = AsyncMock(return_value=expected_data)

        result = await service.get_cached_results("test_key")

        assert result == expected_data
        service.cache_manager.get_json.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_cached_results_no_manager(self, service):
        """测试没有缓存管理器时获取缓存结果"""
        service.cache_manager = None

        result = await service.get_cached_results("test_key")

        assert result is None

    # 测试批量处理数据集
    @pytest.mark.asyncio
    async def test_batch_process_datasets_success(self, service):
        """测试成功批量处理数据集"""
        datasets = {
            "matches": sample_batch_matches,
            "odds": sample_odds_data,
            "other": ["text1", "text2"],
        }

        service.process_batch_matches = AsyncMock(return_value=[{"processed": True}])
        service.process_raw_odds_data = AsyncMock(return_value=[{"processed": True}])
        service.process_batch = AsyncMock(return_value=[{"processed": True}])

        result = await service.batch_process_datasets(datasets)

        assert result["processed_counts"]["matches"] == 1
        assert result["processed_counts"]["odds"] == 1
        assert result["total_processed"] == 3
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_batch_process_datasets_partial_failure(self, service):
        """测试批量处理数据集部分失败"""
        datasets = {
            "matches": sample_batch_matches,
            "odds": sample_odds_data,
        }

        service.process_batch_matches = AsyncMock(
            side_effect=Exception("Matches failed")
        )
        service.process_raw_odds_data = AsyncMock(return_value=[{"processed": True}])

        result = await service.batch_process_datasets(datasets)

        assert result["processed_counts"]["odds"] == 1
        assert result["total_processed"] == 1
        assert "matches" in result["errors"]

    # 测试带重试的处理
    @pytest.mark.asyncio
    async def test_process_with_retry_success(self, service):
        """测试带重试的成功处理"""
        test_data = {"test": "data"}
        mock_func = AsyncMock(return_value={"processed": True})

        result = await service.process_with_retry(mock_func, test_data, max_retries=3)

        assert result == {"processed": True}
        mock_func.assert_called_once_with(test_data)

    @pytest.mark.asyncio
    async def test_process_with_retry_eventual_success(self, service):
        """测试重试后最终成功"""
        test_data = {"test": "data"}
        mock_func = AsyncMock(
            side_effect=[
                Exception("First attempt failed"),
                Exception("Second attempt failed"),
                {"processed": True},
            ]
        )

        result = await service.process_with_retry(
            mock_func, test_data, max_retries=3, delay=0.01
        )

        assert result == {"processed": True}
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_process_with_retry_all_attempts_fail(self, service):
        """测试所有重试尝试都失败"""
        test_data = {"test": "data"}
        mock_func = AsyncMock(side_effect=Exception("Always failed"))

        with pytest.raises(RuntimeError, match="处理持续失败"):
            await service.process_with_retry(
                mock_func, test_data, max_retries=3, delay=0.01
            )

        assert mock_func.call_count == 3

    # 测试分批处理
    @pytest.mark.asyncio
    async def test_process_in_batches(self, service):
        """测试分批处理"""
        large_dataset = list(range(100))  # 100个项目
        batch_size = 25

        batches = []
        async for batch in service._process_in_batches(large_dataset, batch_size):
            batches.append(batch)

        assert len(batches) == 4  # 100 / 25 = 4
        assert all(len(batch) == 25 for batch in batches[:3])  # 前3批是满的
        assert len(batches[3]) == 25  # 最后一批也是满的

    @pytest.mark.asyncio
    async def test_process_in_batches_remainder(self, service):
        """测试分批处理的余数"""
        dataset = list(range(95))  # 95个项目
        batch_size = 30

        batches = []
        async for batch in service._process_in_batches(dataset, batch_size):
            batches.append(batch)

        assert len(batches) == 4  # 95 / 30 = 3 + 1
        assert len(batches[0]) == 30
        assert len(batches[1]) == 30
        assert len(batches[2]) == 30
        assert len(batches[3]) == 5  # 最后一批有5个

    # 测试性能指标收集
    @pytest.mark.asyncio
    async def test_collect_performance_metrics(self, service):
        """测试性能指标收集"""

        async def mock_processing_function(*args, **kwargs):
            await asyncio.sleep(0.01)  # 模拟处理时间
            return [{"result": 1}, {"result": 2}]

        result = await service.collect_performance_metrics(mock_processing_function)

        assert "total_time" in result
        assert "items_processed" in result
        assert "items_per_second" in result
        assert result["items_processed"] == 2
        assert result["total_time"] > 0

    # 测试处理大型数据集
    @pytest.mark.asyncio
    async def test_process_large_dataset(self, service):
        """测试处理大型数据集"""
        large_dataset = list(range(1000))  # 1000个项目
        batch_size = 100

        service.process_batch = AsyncMock(
            side_effect=lambda batch: [{"processed": True} * len(batch)]
        )

        result = await service.process_large_dataset(large_dataset, batch_size)

        assert len(result) == 1000
        assert service.process_batch.call_count == 10  # 1000 / 100 = 10

    # 测试清理资源
    @pytest.mark.asyncio
    async def test_cleanup_success(self, service):
        """测试成功清理资源"""
        service.db_manager = AsyncMock()
        service.db_manager.close = AsyncMock()

        result = await service.cleanup()

        assert result is True
        service.db_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_failure(self, service):
        """测试清理失败"""
        service.db_manager = AsyncMock()
        service.db_manager.close = AsyncMock(side_effect=Exception("Close failed"))

        result = await service.cleanup()

        assert result is False

    # 测试边界情况
    @pytest.mark.asyncio
    async def test_edge_cases_empty_inputs(self, service):
        """测试空输入的边界情况"""
        # 测试各种空输入
        assert await service.process_raw_match_data([]) == pd.DataFrame()
        assert await service.process_raw_odds_data([]) == []
        assert await service.process_batch_matches([]) == []

        empty_df = pd.DataFrame()
        assert await service.process_features_data(1, empty_df).equals(empty_df)

    @pytest.mark.asyncio
    async def test_edge_cases_none_components(self, service):
        """测试组件为None的边界情况"""
        service.data_cleaner = None
        service.missing_handler = None
        service.data_lake = None
        service.db_manager = None
        service.cache_manager = None

        # 应该优雅处理None组件
        result = await service.process_raw_match_data(sample_match_data)
        assert result is None

        result = await service.process_raw_odds_data(sample_odds_data)
        assert result == []

    # 测试并发处理
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, service):
        """测试并发处理能力"""
        service.process_raw_match_data = AsyncMock(return_value={"processed": True})

        # 并发处理多个请求
        tasks = []
        for i in range(5):
            task = service.process_raw_match_data({"match_id": i})
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有任务都完成
        assert len(results) == 5
        assert all(not isinstance(r, Exception) for r in results)
        assert service.process_raw_match_data.call_count == 5

    # 测试错误恢复
    @pytest.mark.asyncio
    async def test_error_recovery(self, service):
        """测试错误恢复能力"""
        # 模拟处理失败后的恢复
        service.process_raw_match_data = AsyncMock(
            side_effect=[Exception("First failure"), {"processed": True}]
        )

        # 第一次调用失败
        with pytest.raises(Exception):
            await service.process_raw_match_data(sample_match_data)

        # 第二次调用成功
        result = await service.process_raw_match_data(sample_match_data)
        assert result == {"processed": True}

    # 测试配置和参数验证
    def test_configuration_validation(self):
        """测试配置验证"""
        # 测试服务名称
        service = DataProcessingService()
        assert service.name == "DataProcessingService"

        # 测试组件初始状态
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.db_manager is None
        assert service.cache_manager is None

    # 测试日志记录
    @patch("src.services.data_processing.logging.getLogger")
    def test_logging_configuration(self, mock_get_logger):
        """测试日志配置"""
        DataProcessingService()

        # 验证日志器被调用
        mock_get_logger.assert_called()

    # 测试服务继承
    def test_service_inheritance(self, service):
        """测试服务继承关系"""
        from src.services.base import BaseService

        assert isinstance(service, BaseService)


# 导入asyncio用于并发测试
import asyncio
