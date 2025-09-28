"""
data_processing.py 测试文件
测试数据处理服务功能，包括数据清洗、缺失值处理、批量处理和Bronze到Silver层转换
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime
from typing import Dict, Any, List
import asyncio
import sys
import os
import pandas as pd

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# 模拟外部依赖
with patch.dict('sys.modules', {
    'src.cache': Mock(),
    'src.cache.redis_manager': Mock(),
    'src.cache.ttl_cache': Mock(),
    'src.data.processing.football_data_cleaner': Mock(),
    'src.data.processing.missing_data_handler': Mock(),
    'src.data.storage.data_lake_storage': Mock(),
    'src.database.connection': Mock(),
    'src.database.models.raw_data': Mock(),
    'src.database.models': Mock(),
    'src.services.base': Mock(),
    'src.core': Mock(),
    'src.models': Mock(),
    'src.models.prediction_service': Mock(),
    'src.utils': Mock()
}):
    from services.data_processing import DataProcessingService


class TestDataProcessingServiceInitialization:
    """测试数据处理服务初始化"""

    def setup_method(self):
        """设置测试环境"""
        self.service = DataProcessingService()

    def test_service_initialization(self):
        """测试服务初始化"""
        assert self.service.name == "DataProcessingService"
        assert self.service.data_cleaner is None
        assert self.service.missing_handler is None
        assert self.service.data_lake is None
        assert self.service.db_manager is None
        assert self.service.cache_manager is None

    @patch('services.data_processing.FootballDataCleaner')
    @patch('services.data_processing.MissingDataHandler')
    @patch('services.data_processing.DataLakeStorage')
    @patch('services.data_processing.DatabaseManager')
    @patch('services.data_processing.RedisManager')
    async def test_initialize_success(self, mock_redis, mock_db, mock_lake, mock_missing, mock_cleaner):
        """测试成功初始化"""
        # 设置mock返回值
        mock_cleaner.return_value = Mock()
        mock_missing.return_value = Mock()
        mock_lake.return_value = Mock()
        mock_db.return_value = Mock()
        mock_redis.return_value = Mock()

        result = await self.service.initialize()

        assert result is True
        assert self.service.data_cleaner is not None
        assert self.service.missing_handler is not None
        assert self.service.data_lake is not None
        assert self.service.db_manager is not None
        assert self.service.cache_manager is not None

    @patch('services.data_processing.FootballDataCleaner')
    async def test_initialize_failure(self, mock_cleaner):
        """测试初始化失败"""
        mock_cleaner.side_effect = Exception("Initialization failed")

        result = await self.service.initialize()

        assert result is False


class TestDataProcessingServiceCore:
    """测试数据处理服务核心功能"""

    def setup_method(self):
        """设置测试环境"""
        self.service = DataProcessingService()
        self.service.data_cleaner = Mock()
        self.service.missing_handler = Mock()
        self.service.data_lake = Mock()
        self.service.db_manager = Mock()
        self.service.cache_manager = Mock()

    async def test_process_raw_match_data_single_dict(self):
        """测试处理单个字典比赛数据"""
        raw_data = {"external_match_id": 123, "home_team_id": 1, "away_team_id": 2}

        # 模拟数据清洗
        self.service.data_cleaner.clean_match_data.return_value = raw_data
        self.service.missing_handler.handle_missing_match_data.return_value = raw_data

        result = await self.service.process_raw_match_data(raw_data)

        assert result == raw_data
        self.service.data_cleaner.clean_match_data.assert_called_once_with(raw_data)
        self.service.missing_handler.handle_missing_match_data.assert_called_once_with(raw_data)

    async def test_process_raw_match_data_list(self):
        """测试处理列表比赛数据"""
        raw_data = [
            {"external_match_id": 123, "home_team_id": 1, "away_team_id": 2},
            {"external_match_id": 124, "home_team_id": 3, "away_team_id": 4}
        ]

        # 模拟数据清洗
        self.service.data_cleaner.clean_match_data.side_effect = raw_data
        self.service.missing_handler.handle_missing_match_data.side_effect = raw_data

        result = await self.service.process_raw_match_data(raw_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    async def test_process_raw_match_data_empty_list(self):
        """测试处理空列表比赛数据"""
        result = await self.service.process_raw_match_data([])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    async def test_process_raw_match_data_cleaner_not_initialized(self):
        """测试数据清洗器未初始化"""
        self.service.data_cleaner = None

        result = await self.service.process_raw_match_data({"test": "data"})

        assert result is None

    async def test_process_raw_match_data_cleaning_failure(self):
        """测试数据清洗失败"""
        raw_data = {"external_match_id": 123}

        # 模拟清洗失败
        self.service.data_cleaner.clean_match_data.return_value = None

        result = await self.service.process_raw_match_data(raw_data)

        assert result is None

    async def test_process_raw_odds_data(self):
        """测试处理原始赔率数据"""
        raw_odds = [{"match_id": 123, "price": 2.0}, {"match_id": 124, "price": 3.0}]
        cleaned_odds = [{"match_id": 123, "price": 2.0}, {"match_id": 124, "price": 3.0}]

        # 模拟清洗
        self.service.data_cleaner.clean_odds_data.return_value = cleaned_odds

        result = await self.service.process_raw_odds_data(raw_odds)

        assert result == cleaned_odds
        self.service.data_cleaner.clean_odds_data.assert_called_once_with(raw_odds)

    async def test_process_raw_odds_data_cleaner_not_initialized(self):
        """测试赔率数据清洗器未初始化"""
        self.service.data_cleaner = None

        result = await self.service.process_raw_odds_data([{"test": "data"}])

        assert result == []

    async def test_process_features_data(self):
        """测试处理特征数据"""
        match_id = 123
        features_df = pd.DataFrame({"feature1": [1, 2], "feature2": [3, 4]})
        processed_features = pd.DataFrame({"feature1": [1, 2], "feature2": [3, 4]})

        # 模拟缺失值处理
        self.service.missing_handler.handle_missing_features.return_value = processed_features

        result = await self.service.process_features_data(match_id, features_df)

        assert result.equals(processed_features)
        self.service.missing_handler.handle_missing_features.assert_called_once_with(match_id, features_df)

    async def test_process_features_data_handler_not_initialized(self):
        """测试特征数据处理器未初始化"""
        self.service.missing_handler = None

        features_df = pd.DataFrame({"feature1": [1, 2]})
        result = await self.service.process_features_data(123, features_df)

        assert result.equals(features_df)

    async def test_process_batch_matches(self):
        """测试批量处理比赛数据"""
        raw_matches = [
            {"external_match_id": 123, "home_team_id": 1, "away_team_id": 2},
            {"external_match_id": 124, "home_team_id": 3, "away_team_id": 4}
        ]

        # 模拟单个处理成功
        self.service.process_raw_match_data.side_effect = raw_matches

        result = await self.service.process_batch_matches(raw_matches)

        assert result == raw_matches
        assert len(result) == 2

    async def test_process_batch_matches_with_errors(self):
        """测试批量处理比赛数据时处理错误"""
        raw_matches = [
            {"external_match_id": 123, "home_team_id": 1, "away_team_id": 2},
            {"external_match_id": 124, "home_team_id": 3, "away_team_id": 4}
        ]

        # 模拟第一个成功，第二个失败
        self.service.process_raw_match_data.side_effect = [raw_matches[0], Exception("处理失败")]

        result = await self.service.process_batch_matches(raw_matches)

        assert len(result) == 1
        assert result[0] == raw_matches[0]

    async def test_process_batch_matches_empty_input(self):
        """测试批量处理空列表"""
        result = await self.service.process_batch_matches([])

        assert result == []

    async def test_validate_data_quality_match_data(self):
        """测试验证比赛数据质量"""
        match_data = {
            "external_match_id": 123,
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2024-01-01T12:00:00",
            "home_score": 2,
            "away_score": 1
        }

        result = await self.service.validate_data_quality(match_data, "match")

        assert result["data_type"] == "match"
        assert result["is_valid"] is True
        assert len(result["issues"]) == 0

    async def test_validate_data_quality_match_missing_fields(self):
        """测试验证比赛数据缺失字段"""
        match_data = {
            "external_match_id": 123,
            # 缺少必需字段
        }

        result = await self.service.validate_data_quality(match_data, "match")

        assert result["is_valid"] is False
        assert len(result["issues"]) > 0
        assert any("home_team_id" in issue for issue in result["issues"])

    async def test_validate_data_quality_match_negative_scores(self):
        """测试验证比赛数据负分"""
        match_data = {
            "external_match_id": 123,
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2024-01-01T12:00:00",
            "home_score": -1,
            "away_score": 1
        }

        result = await self.service.validate_data_quality(match_data, "match")

        assert result["is_valid"] is False
        assert any("Negative scores" in issue for issue in result["issues"])

    async def test_validate_data_quality_match_high_scores(self):
        """测试验证比赛数据高分警告"""
        match_data = {
            "external_match_id": 123,
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2024-01-01T12:00:00",
            "home_score": 25,
            "away_score": 1
        }

        result = await self.service.validate_data_quality(match_data, "match")

        assert result["is_valid"] is True
        assert len(result["warnings"]) > 0
        assert any("high scores" in warning for warning in result["warnings"])

    async def test_validate_data_quality_odds_data(self):
        """测试验证赔率数据质量"""
        odds_data = {
            "outcomes": [
                {"price": 2.0},
                {"price": 3.0}
            ]
        }

        result = await self.service.validate_data_quality(odds_data, "odds")

        assert result["data_type"] == "odds"
        assert result["is_valid"] is True
        assert len(result["issues"]) == 0

    async def test_validate_data_quality_odds_no_outcomes(self):
        """测试验证赔率数据无结果"""
        odds_data = {"outcomes": []}

        result = await self.service.validate_data_quality(odds_data, "odds")

        assert result["is_valid"] is False
        assert any("No odds outcomes" in issue for issue in result["issues"])

    async def test_validate_data_quality_odds_invalid_price(self):
        """测试验证赔率数据无效价格"""
        odds_data = {
            "outcomes": [
                {"price": 0.5}  # 小于1.01
            ]
        }

        result = await self.service.validate_data_quality(odds_data, "odds")

        assert result["is_valid"] is False
        assert any("Invalid odds price" in issue for issue in result["issues"])

    async def test_validate_data_quality_unknown_type(self):
        """测试验证未知数据类型"""
        data = {"test": "data"}

        result = await self.service.validate_data_quality(data, "unknown")

        assert result["data_type"] == "unknown"
        assert result["is_valid"] is True
        assert len(result["issues"]) == 0

    async def test_validate_data_quality_validation_error(self):
        """测试验证过程错误"""
        # 模拟验证过程中的异常
        with patch.object(self.service, 'logger') as mock_logger:
            mock_logger.error.side_effect = Exception("Logger error")

            data = {"test": "data"}
            result = await self.service.validate_data_quality(data, "match")

            assert result["is_valid"] is False
            assert len(result["issues"]) > 0


class TestDataProcessingServiceBackwardCompatibility:
    """测试数据处理服务向后兼容性"""

    def setup_method(self):
        """设置测试环境"""
        self.service = DataProcessingService()

    async def test_process_text(self):
        """测试处理文本数据"""
        text = "  Hello World  "

        result = await self.service.process_text(text)

        assert result["processed_text"] == "Hello World"
        assert result["word_count"] == 2
        assert result["character_count"] == len(text)

    async def test_process_text_empty(self):
        """测试处理空文本"""
        text = ""

        result = await self.service.process_text(text)

        assert result["processed_text"] == ""
        assert result["word_count"] == 0
        assert result["character_count"] == 0

    async def test_process_batch_strings(self):
        """测试批量处理字符串"""
        data_list = ["Hello", "World", "Test"]

        result = await self.service.process_batch(data_list)

        assert len(result) == 3
        for i, item in enumerate(result):
            assert item["processed_text"] == data_list[i]
            assert "word_count" in item

    async def test_process_batch_dicts(self):
        """测试批量处理字典"""
        data_list = [{"key1": "value1"}, {"key2": "value2"}]

        result = await self.service.process_batch(data_list)

        assert len(result) == 2
        for item in result:
            assert "processed" in item
            assert item["processed"] is True

    async def test_process_batch_mixed_types(self):
        """测试批量处理混合类型"""
        data_list = ["string", {"key": "value"}, 123]

        result = await self.service.process_batch(data_list)

        assert len(result) == 3
        assert "processed_text" in result[0]  # 字符串处理
        assert "processed" in result[1]        # 字典处理
        assert "original_data" in result[2]     # 其他类型处理

    async def test_process_batch_empty_list(self):
        """测试批量处理空列表"""
        result = await self.service.process_batch([])

        assert result == []


class TestDataProcessingServiceBronzeToSilver:
    """测试Bronze到Silver层处理"""

    def setup_method(self):
        """设置测试环境"""
        self.service = DataProcessingService()
        self.service.data_cleaner = Mock()
        self.service.missing_handler = Mock()
        self.service.data_lake = Mock()
        self.service.db_manager = Mock()

    async def test_process_bronze_to_silver_success(self):
        """测试成功处理Bronze到Silver层"""
        # 设置所有必需组件
        self.service.data_cleaner.clean_match_data.return_value = {"cleaned": True}
        self.service.missing_handler.handle_missing_match_data.return_value = {"processed": True}
        self.service.data_lake.save_historical_data = AsyncMock()

        # 模拟数据库会话和查询
        mock_session = Mock()
        mock_match = Mock()
        mock_match.id = 1
        mock_match.raw_data = {"test": "data"}
        mock_match.mark_processed = Mock()
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_match]
        self.service.db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.service.db_manager.get_session.return_value.__exit__.return_value = None

        # 模拟其他表查询返回空结果
        original_all = mock_session.query.return_value.filter.return_value.limit.return_value.all
        def mock_query_all(*args, **kwargs):
            if "RawOddsData" in str(args[0]) or "RawScoresData" in str(args[0]):
                return []
            return original_all(*args, **kwargs)
        mock_session.query.return_value.filter.return_value.limit.return_value.all = mock_query_all

        result = await self.service.process_bronze_to_silver()

        assert result["processed_matches"] == 1
        assert result["processed_odds"] == 0
        assert result["processed_scores"] == 0
        assert result["errors"] == 0

    async def test_process_bronze_to_silver_incomplete_initialization(self):
        """测试未完全初始化的处理"""
        self.service.data_cleaner = None

        result = await self.service.process_bronze_to_silver()

        assert "error" in result

    async def test_process_bronze_to_silver_exception_handling(self):
        """测试处理异常"""
        # 模拟处理过程中的异常
        self.service.data_cleaner.clean_match_data.side_effect = Exception("处理失败")

        mock_session = Mock()
        mock_match = Mock()
        mock_match.id = 1
        mock_match.raw_data = {"test": "data"}
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_match]
        self.service.db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.service.db_manager.get_session.return_value.__exit__.return_value = None

        # 模拟其他表查询返回空结果
        def mock_query_all(*args, **kwargs):
            if "RawOddsData" in str(args[0]) or "RawScoresData" in str(args[0]):
                return []
            return [mock_match]
        mock_session.query.return_value.filter.return_value.limit.return_value.all = mock_query_all

        result = await self.service.process_bronze_to_silver()

        assert result["errors"] == 1

    async def test_process_raw_matches_bronze_to_silver_no_data(self):
        """测试处理比赛数据无数据"""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        self.service.db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.service.db_manager.get_session.return_value.__exit__.return_value = None

        result = await self.service._process_raw_matches_bronze_to_silver(100)

        assert result == 0

    async def test_process_raw_matches_bronze_to_silver_success(self):
        """测试成功处理比赛数据到Silver层"""
        mock_session = Mock()
        mock_match = Mock()
        mock_match.id = 1
        mock_match.raw_data = {"test": "data"}
        mock_match.mark_processed = Mock()
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_match]
        self.service.db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.service.db_manager.get_session.return_value.__exit__.return_value = None

        self.service.data_cleaner.clean_match_data.return_value = {"cleaned": True}
        self.service.missing_handler.handle_missing_match_data.return_value = {"processed": True}
        self.service.data_lake.save_historical_data = AsyncMock()

        result = await self.service._process_raw_matches_bronze_to_silver(100)

        assert result == 1
        mock_match.mark_processed.assert_called_once()

    async def test_process_raw_odds_bronze_to_silver_no_data(self):
        """测试处理赔率数据无数据"""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        self.service.db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.service.db_manager.get_session.return_value.__exit__.return_value = None

        result = await self.service._process_raw_odds_bronze_to_silver(100)

        assert result == 0

    async def test_process_raw_odds_bronze_to_silver_success(self):
        """测试成功处理赔率数据到Silver层"""
        mock_session = Mock()
        mock_odds = Mock()
        mock_odds.id = 1
        mock_odds.external_match_id = 123
        mock_odds.raw_data = {"match_id": 123, "price": 2.0}
        mock_odds.mark_processed = Mock()
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_odds]
        self.service.db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.service.db_manager.get_session.return_value.__exit__.return_value = None

        self.service.data_cleaner.clean_odds_data.return_value = [{"match_id": 123, "price": 2.0}]
        self.service.data_lake.save_historical_data = AsyncMock()

        result = await self.service._process_raw_odds_bronze_to_silver(100)

        assert result == 1
        mock_odds.mark_processed.assert_called_once()

    async def test_process_raw_scores_bronze_to_silver_no_data(self):
        """测试处理比分数据无数据"""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        self.service.db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.service.db_manager.get_session.return_value.__exit__.return_value = None

        result = await self.service._process_raw_scores_bronze_to_silver(100)

        assert result == 0

    async def test_process_raw_scores_bronze_to_silver_success(self):
        """测试成功处理比分数据到Silver层"""
        mock_session = Mock()
        mock_scores = Mock()
        mock_scores.id = 1
        mock_scores.external_match_id = 123
        mock_scores.get_score_info.return_value = {
            "home_score": 2,
            "away_score": 1,
            "half_time_home": 1,
            "half_time_away": 0,
            "status": "finished",
            "minute": 90,
            "events": []
        }
        mock_scores.is_live = False
        mock_scores.is_finished = True
        mock_scores.collected_at = datetime.now()
        mock_scores.mark_processed = Mock()
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_scores]
        self.service.db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.service.db_manager.get_session.return_value.__exit__.return_value = None

        # 模拟数据清洗器方法
        self.service.data_cleaner._validate_score = Mock(side_effect=lambda x: x)
        self.service.data_cleaner._standardize_match_status = Mock(return_value="finished")
        self.service.data_lake.save_historical_data = AsyncMock()

        result = await self.service._process_raw_scores_bronze_to_silver(100)

        assert result == 1
        mock_scores.mark_processed.assert_called_once()

    async def test_get_bronze_layer_status_success(self):
        """测试成功获取Bronze层状态"""
        mock_session = Mock()
        # 模拟查询结果
        mock_session.query.return_value.count.return_value = 10
        mock_session.query.return_value.filter.return_value.count.return_value = 5
        self.service.db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.service.db_manager.get_session.return_value.__exit__.return_value = None

        result = await self.service.get_bronze_layer_status()

        assert "matches" in result
        assert "odds" in result
        assert "scores" in result
        assert result["matches"]["total"] == 10
        assert result["matches"]["processed"] == 5
        assert result["matches"]["pending"] == 5

    async def test_get_bronze_layer_status_no_database(self):
        """测试无数据库连接获取Bronze层状态"""
        self.service.db_manager = None

        result = await self.service.get_bronze_layer_status()

        assert "error" in result

    async def test_get_bronze_layer_status_exception(self):
        """测试获取Bronze层状态异常"""
        mock_session = Mock()
        mock_session.query.side_effect = Exception("Database error")
        self.service.db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.service.db_manager.get_session.return_value.__exit__.return_value = None

        result = await self.service.get_bronze_layer_status()

        assert "error" in result


class TestDataProcessingServiceMissingDataHandling:
    """测试缺失值处理功能"""

    def setup_method(self):
        """设置测试环境"""
        self.service = DataProcessingService()
        self.service.missing_handler = Mock()

    async def test_handle_missing_scores_success(self):
        """测试成功处理分数缺失值"""
        data = pd.DataFrame({"score": [1, None, 3]})
        processed_data = pd.DataFrame({"score": [1, 2, 3]})

        self.service.missing_handler.interpolate_scores.return_value = processed_data

        result = await self.service.handle_missing_scores(data)

        assert result.equals(processed_data)
        self.service.missing_handler.interpolate_scores.assert_called_once_with(data)

    async def test_handle_missing_scores_handler_not_initialized(self):
        """测试处理器未初始化"""
        self.service.missing_handler = None

        data = pd.DataFrame({"score": [1, None, 3]})
        result = await self.service.handle_missing_scores(data)

        assert result is None

    async def test_handle_missing_scores_handler_no_method(self):
        """测试处理器不支持分数插值"""
        self.service.missing_handler.interpolate_scores = Mock(side_effect=AttributeError("No method"))

        data = pd.DataFrame({"score": [1, None, 3]})
        result = await self.service.handle_missing_scores(data)

        assert result.equals(data)

    async def test_handle_missing_team_data_success(self):
        """测试成功处理球队数据缺失值"""
        data = pd.DataFrame({"team": [1, None, 3]})
        processed_data = pd.DataFrame({"team": [1, 2, 3]})

        self.service.missing_handler.impute_team_data.return_value = processed_data

        result = await self.service.handle_missing_team_data(data)

        assert result.equals(processed_data)
        self.service.missing_handler.impute_team_data.assert_called_once_with(data)

    async def test_handle_missing_team_data_handler_not_initialized(self):
        """测试球队数据处理器未初始化"""
        self.service.missing_handler = None

        data = pd.DataFrame({"team": [1, None, 3]})
        result = await self.service.handle_missing_team_data(data)

        assert result is None

    async def test_handle_missing_team_data_handler_no_method(self):
        """测试处理器不支持球队数据填充"""
        self.service.missing_handler.impute_team_data = Mock(side_effect=AttributeError("No method"))

        data = pd.DataFrame({"team": [1, None, 3]})
        result = await self.service.handle_missing_team_data(data)

        assert result.equals(data)

    async def test_detect_anomalies_success(self):
        """测试成功检测异常"""
        data = pd.DataFrame({"value": [1, 2, 10]})
        anomalies = [{"index": 2, "value": 10, "severity": "high"}]

        self.service.missing_handler.detect_anomalies.return_value = anomalies

        result = await self.service.detect_anomalies(data)

        assert result == anomalies
        self.service.missing_handler.detect_anomalies.assert_called_once_with(data)

    async def test_detect_anomalies_handler_not_initialized(self):
        """测试异常检测处理器未初始化"""
        self.service.missing_handler = None

        data = pd.DataFrame({"value": [1, 2, 10]})
        result = await self.service.detect_anomalies(data)

        assert result == []

    async def test_detect_anomalies_handler_no_method(self):
        """测试处理器不支持异常检测"""
        self.service.missing_handler.detect_anomalies = Mock(side_effect=AttributeError("No method"))

        data = pd.DataFrame({"value": [1, 2, 10]})
        result = await self.service.detect_anomalies(data)

        assert result == []

    async def test_detect_anomalies_async_result(self):
        """测试异步异常检测结果"""
        data = pd.DataFrame({"value": [1, 2, 10]})
        anomalies = [{"index": 2, "value": 10, "severity": "high"}]

        async def async_detect(data):
            return anomalies

        self.service.missing_handler.detect_anomalies.return_value = async_detect(data)

        result = await self.service.detect_anomalies(data)

        assert result == anomalies


class TestDataProcessingServiceStorage:
    """测试数据存储功能"""

    def setup_method(self):
        """设置测试环境"""
        self.service = DataProcessingService()
        self.service.data_lake = Mock()
        self.service.db_manager = Mock()
        self.service.cache_manager = Mock()

    async def test_store_processed_data_success(self):
        """测试成功存储处理后的数据"""
        data = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        table_name = "test_table"

        # 模拟所有存储成功
        self.service.data_lake.store_dataframe = Mock()
        self.service.db_manager.bulk_insert = Mock()
        self.service.cache_manager.set_json = Mock()

        result = await self.service.store_processed_data(data, table_name, cache_results=True)

        assert result is True

    async def test_store_processed_data_data_lake_failure(self):
        """测试数据湖存储失败"""
        data = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        table_name = "test_table"

        # 模拟数据湖存储失败
        self.service.data_lake.store_dataframe.side_effect = Exception("Data lake error")
        self.service.db_manager.bulk_insert = Mock()
        self.service.cache_manager.set_json = Mock()

        result = await self.service.store_processed_data(data, table_name, cache_results=True)

        assert result is False

    async def test_store_processed_data_no_data_lake(self):
        """测试无数据湖存储"""
        self.service.data_lake = None

        data = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        table_name = "test_table"

        self.service.db_manager.bulk_insert = Mock()
        self.service.cache_manager.set_json = Mock()

        result = await self.service.store_processed_data(data, table_name, cache_results=True)

        assert result is True

    async def test_store_processed_data_database_failure(self):
        """测试数据库存储失败"""
        data = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        table_name = "test_table"

        # 模拟数据库存储失败
        self.service.data_lake.store_dataframe = Mock()
        self.service.db_manager.bulk_insert.side_effect = Exception("Database error")
        self.service.cache_manager.set_json = Mock()

        result = await self.service.store_processed_data(data, table_name, cache_results=True)

        assert result is False

    async def test_store_processed_data_cache_failure(self):
        """测试缓存失败但不影响存储"""
        data = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        table_name = "test_table"

        # 模拟缓存失败
        self.service.data_lake.store_dataframe = Mock()
        self.service.db_manager.bulk_insert = Mock()
        self.service.cache_manager.set_json.side_effect = Exception("Cache error")

        result = await self.service.store_processed_data(data, table_name, cache_results=True)

        assert result is True  # 缓存失败不影响整体结果

    async def test_cache_processing_results_success(self):
        """测试成功缓存处理结果"""
        cache_key = "test_key"
        data = {"result": "success"}
        ttl = 1800

        self.service.cache_manager.set_json.return_value = True

        result = await self.service.cache_processing_results(cache_key, data, ttl)

        assert result is True
        self.service.cache_manager.set_json.assert_called_once_with(cache_key, data, ttl=ttl)

    async def test_cache_processing_results_no_cache_manager(self):
        """测试无缓存管理器"""
        self.service.cache_manager = None

        result = await self.service.cache_processing_results("test_key", {"data": "test"})

        assert result is False

    async def test_cache_processing_results_no_json_method(self):
        """测试缓存管理器不支持JSON存储"""
        self.service.cache_manager.set_json = Mock(side_effect=AttributeError("No method"))

        result = await self.service.cache_processing_results("test_key", {"data": "test"})

        assert result is False

    async def test_get_cached_results_success(self):
        """测试成功获取缓存结果"""
        cache_key = "test_key"
        cached_data = {"result": "cached"}

        self.service.cache_manager.get_json.return_value = cached_data

        result = await self.service.get_cached_results(cache_key)

        assert result == cached_data
        self.service.cache_manager.get_json.assert_called_once_with(cache_key)

    async def test_get_cached_results_no_cache_manager(self):
        """测试无缓存管理器获取缓存"""
        self.service.cache_manager = None

        result = await self.service.get_cached_results("test_key")

        assert result is None

    async def test_get_cached_results_no_json_method(self):
        """测试缓存管理器不支持JSON获取"""
        self.service.cache_manager.get_json = Mock(side_effect=AttributeError("No method"))

        result = await self.service.get_cached_results("test_key")

        assert result is None

    async def test_get_cached_results_async_result(self):
        """测试异步获取缓存结果"""
        cache_key = "test_key"
        cached_data = {"result": "cached"}

        async def async_get(key):
            return cached_data

        self.service.cache_manager.get_json.return_value = async_get(cache_key)

        result = await self.service.get_cached_results(cache_key)

        assert result == cached_data


class TestDataProcessingServiceAdvanced:
    """测试高级功能"""

    def setup_method(self):
        """设置测试环境"""
        self.service = DataProcessingService()

    async def test_batch_process_datasets_success(self):
        """测试成功批量处理数据集"""
        datasets = {
            "matches": [{"id": 1}, {"id": 2}],
            "odds": [{"match_id": 1, "price": 2.0}]
        }

        # 模拟处理函数
        self.service.process_batch_matches = AsyncMock(return_value=datasets["matches"])
        self.service.process_raw_odds_data = AsyncMock(return_value=datasets["odds"])

        result = await self.service.batch_process_datasets(datasets)

        assert result["processed_counts"]["matches"] == 2
        assert result["processed_counts"]["odds"] == 1
        assert result["total_processed"] == 3
        assert len(result["errors"]) == 0

    async def test_batch_process_datasets_with_errors(self):
        """测试批量处理数据集时出现错误"""
        datasets = {
            "matches": [{"id": 1}, {"id": 2}],
            "odds": [{"match_id": 1, "price": 2.0}],
            "unknown": [{"test": "data"}]
        }

        # 模拟处理函数
        self.service.process_batch_matches = AsyncMock(return_value=datasets["matches"])
        self.service.process_raw_odds_data = AsyncMock(return_value=datasets["odds"])
        self.service.process_batch = AsyncMock(side_effect=Exception("Unknown data type"))

        result = await self.service.batch_process_datasets(datasets)

        assert result["processed_counts"]["matches"] == 2
        assert result["processed_counts"]["odds"] == 1
        assert result["total_processed"] == 3
        assert "unknown" in result["errors"]

    async def test_process_with_retry_success(self):
        """测试带重试逻辑的成功处理"""
        def test_func(data):
            return f"processed_{data}"

        data = "test_data"

        result = await self.service.process_with_retry(test_func, data)

        assert result == "processed_test_data"

    async def test_process_with_retry_async_success(self):
        """测试带重试逻辑的异步成功处理"""
        async def async_test_func(data):
            return f"async_processed_{data}"

        data = "test_data"

        result = await self.service.process_with_retry(async_test_func, data)

        assert result == "async_processed_test_data"

    async def test_process_with_retry_success_after_failures(self):
        """测试重试后成功处理"""
        call_count = 0

        def failing_then_succeeding_func(data):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return f"processed_{data}"

        data = "test_data"

        result = await self.service.process_with_retry(failing_then_succeeding_func, data, max_retries=3)

        assert result == "processed_test_data"
        assert call_count == 3

    async def test_process_with_retry_all_attempts_fail(self):
        """测试所有重试都失败"""
        def always_failing_func(data):
            raise Exception("Always fails")

        data = "test_data"

        with pytest.raises(RuntimeError) as exc_info:
            await self.service.process_with_retry(always_failing_func, data, max_retries=3)

        assert "处理持续失败" in str(exc_info.value)

    async def test_process_in_batches(self):
        """测试分批处理"""
        dataset = [1, 2, 3, 4, 5, 6, 7]
        batch_size = 3

        batches = []
        async for batch in self.service._process_in_batches(dataset, batch_size):
            batches.append(batch)

        assert len(batches) == 3
        assert batches[0] == [1, 2, 3]
        assert batches[1] == [4, 5, 6]
        assert batches[2] == [7]

    async def test_collect_performance_metrics(self):
        """测试收集性能指标"""
        async def mock_processing_function(*args, **kwargs):
            await asyncio.sleep(0.1)  # 模拟处理时间
            return [1, 2, 3]  # 模拟处理结果

        result = await self.service.collect_performance_metrics(mock_processing_function, "test_arg")

        assert "total_time" in result
        assert "items_processed" in result
        assert "items_per_second" in result
        assert result["items_processed"] == 3
        assert result["total_time"] > 0
        assert result["items_per_second"] > 0

    async def test_process_large_dataset(self):
        """测试处理大型数据集"""
        dataset = list(range(100))  # 100个项目
        batch_size = 25

        # 模拟批处理
        self.service.process_batch = AsyncMock(side_effect=lambda batch: [{"processed": item} for item in batch])

        result = await self.service.process_large_dataset(dataset, batch_size)

        assert len(result) == 100
        assert all("processed" in item for item in result)


class TestDataProcessingServiceLifecycle:
    """测试服务生命周期"""

    def setup_method(self):
        """设置测试环境"""
        self.service = DataProcessingService()

    async def test_shutdown_with_cache_manager(self):
        """测试带缓存管理器的关闭"""
        mock_cache_manager = Mock()
        mock_cache_manager.close = Mock()
        self.service.cache_manager = mock_cache_manager

        mock_db_manager = AsyncMock()
        self.service.db_manager = mock_db_manager

        await self.service.shutdown()

        assert self.service.data_cleaner is None
        assert self.service.missing_handler is None
        assert self.service.data_lake is None
        assert self.service.cache_manager is None
        assert self.service.db_manager is None

    async def test_shutdown_with_async_cache_manager(self):
        """测试异步缓存管理器的关闭"""
        mock_cache_manager = Mock()
        mock_cache_manager.close = AsyncMock()
        self.service.cache_manager = mock_cache_manager

        mock_db_manager = AsyncMock()
        self.service.db_manager = mock_db_manager

        await self.service.shutdown()

        mock_cache_manager.close.assert_called_once()

    async def test_shutdown_without_cache_manager(self):
        """测试无缓存管理器的关闭"""
        self.service.cache_manager = None

        mock_db_manager = AsyncMock()
        self.service.db_manager = mock_db_manager

        await self.service.shutdown()

        assert self.service.cache_manager is None

    async def test_cleanup_success(self):
        """测试成功清理"""
        self.service.db_manager = AsyncMock()

        result = await self.service.cleanup()

        assert result is True

    async def test_cleanup_with_cache(self):
        """测试带缓存的清理"""
        self.service._cache = {"key": "value"}
        self.service.db_manager = AsyncMock()

        result = await self.service.cleanup()

        assert result is True
        assert len(self.service._cache) == 0

    async def test_cleanup_failure(self):
        """测试清理失败"""
        self.service.db_manager = Mock()
        self.service.db_manager.close = Mock(side_effect=Exception("Cleanup failed"))

        result = await self.service.cleanup()

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])