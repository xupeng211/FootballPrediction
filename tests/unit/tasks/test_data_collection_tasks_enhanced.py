"""
数据采集任务测试 - 覆盖率提升版本

针对 data_collection_tasks.py 的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock, AsyncMock
from typing import Any, Dict, List, Optional
import json

from src.tasks.data_collection_tasks import (
    DataCollectionTask,
    collect_fixtures_task,
    collect_odds_task,
    collect_scores_task,
    CollectionResult,
    CollectionConfig,
    DataCollectionManager
)


class TestCollectionConfig:
    """采集配置测试类"""

    def test_init_default_values(self):
        """测试默认值初始化"""
        config = CollectionConfig()

        assert config.api_base_url == "https://api.football-data.org/v4"
        assert config.api_key == "default_api_key"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_delay == 5
        assert config.batch_size == 100
        assert config.rate_limit_per_minute == 60
        assert config.enable_caching is True
        assert config.cache_ttl == 3600

    def test_init_custom_values(self):
        """测试自定义值初始化"""
        config = CollectionConfig(
            api_base_url="https://custom.api.com/v1",
            api_key="custom_key",
            timeout=60,
            max_retries=5,
            retry_delay=10,
            batch_size=200,
            rate_limit_per_minute=120,
            enable_caching=False,
            cache_ttl=7200
        )

        assert config.api_base_url == "https://custom.api.com/v1"
        assert config.api_key == "custom_key"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_delay == 10
        assert config.batch_size == 200
        assert config.rate_limit_per_minute == 120
        assert config.enable_caching is False
        assert config.cache_ttl == 7200

    def test_dataclass_properties(self):
        """测试dataclass属性"""
        config = CollectionConfig()

        assert hasattr(config, '__dataclass_fields__')
        fields = config.__dataclass_fields__
        assert 'api_base_url' in fields
        assert 'api_key' in fields
        assert 'timeout' in fields
        assert 'max_retries' in fields
        assert 'retry_delay' in fields


class TestCollectionResult:
    """采集结果测试类"""

    def test_init_success(self):
        """测试成功初始化"""
        result = CollectionResult(
            success=True,
            data_type="fixtures",
            records_count=150,
            duration_seconds=25.5,
            api_calls_made=2
        )

        assert result.success is True
        assert result.data_type == "fixtures"
        assert result.records_count == 150
        assert result.duration_seconds == 25.5
        assert result.api_calls_made == 2
        assert result.error_message is None
        assert result.timestamp is not None

    def test_init_failure(self):
        """测试失败初始化"""
        result = CollectionResult(
            success=False,
            data_type="odds",
            records_count=0,
            duration_seconds=5.0,
            api_calls_made=1,
            error_message="API rate limit exceeded"
        )

        assert result.success is False
        assert result.data_type == "odds"
        assert result.records_count == 0
        assert result.duration_seconds == 5.0
        assert result.api_calls_made == 1
        assert result.error_message == "API rate limit exceeded"
        assert result.timestamp is not None


class TestDataCollectionTask:
    """数据采集任务基类测试"""

    def test_init(self):
        """测试初始化"""
        config = CollectionConfig(api_key="test_key")
        task = DataCollectionTask(config)

        assert task.config == config
        assert task.collector is not None
        assert task.error_logger is not None

    def test_prepare_api_headers(self):
        """测试准备API请求头"""
        config = CollectionConfig(api_key="test_key")
        task = DataCollectionTask(config)

        headers = task._prepare_api_headers()

        assert "X-Auth-Token" in headers
        assert headers["X-Auth-Token"] == "test_key"
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_calculate_rate_limit_delay(self):
        """测试计算速率限制延迟"""
        config = CollectionConfig(rate_limit_per_minute=60)
        task = DataCollectionTask(config)

        delay = task._calculate_rate_limit_delay()

        assert delay >= 0
        assert delay <= 1.0  # Should be reasonable for rate limiting

    def test_validate_response_data_valid(self):
        """测试验证响应数据有效"""
        config = CollectionConfig()
        task = DataCollectionTask(config)

        valid_data = {"matches": [{"id": 1, "homeTeam": "Team A", "awayTeam": "Team B"}]}
        is_valid = task._validate_response_data(valid_data, "fixtures")

        assert is_valid is True

    def test_validate_response_data_invalid(self):
        """测试验证响应数据无效"""
        config = CollectionConfig()
        task = DataCollectionTask(config)

        invalid_data = {"error": "Invalid request"}
        is_valid = task._validate_response_data(invalid_data, "fixtures")

        assert is_valid is False

    def test_handle_api_error(self):
        """测试处理API错误"""
        config = CollectionConfig()
        task = DataCollectionTask(config)

        error_response = {"errorCode": 404, "message": "Resource not found"}
        handled = task._handle_api_error(error_response, "fixtures")

        assert handled is True

    def test_handle_rate_limit(self):
        """测试处理速率限制"""
        config = CollectionConfig(retry_delay=10)
        task = DataCollectionTask(config)

        can_retry = task._handle_rate_limit()

        assert can_retry is True

    def test_transform_fixtures_data(self):
        """测试转换赛程数据"""
        config = CollectionConfig()
        task = DataCollectionTask(config)

        raw_data = {
            "matches": [
                {
                    "id": 123,
                    "utcDate": "2024-01-15T19:00:00Z",
                    "homeTeam": {"name": "Team A"},
                    "awayTeam": {"name": "Team B"},
                    "competition": {"name": "Premier League"}
                }
            ]
        }

        transformed = task._transform_fixtures_data(raw_data)

        assert isinstance(transformed, list)
        assert len(transformed) == 1
        assert transformed[0]["match_id"] == 123
        assert transformed[0]["home_team"] == "Team A"
        assert transformed[0]["away_team"] == "Team B"
        assert transformed[0]["competition"] == "Premier League"

    def test_transform_odds_data(self):
        """测试转换赔率数据"""
        config = CollectionConfig()
        task = DataCollectionTask(config)

        raw_data = {
            "odds": [
                {
                    "fixture": 123,
                    "bookmakers": [
                        {
                            "name": "Bet365",
                            "bets": [
                                {
                                    "name": "Match Winner",
                                    "values": [
                                        {"value": "Home", "odd": 2.10},
                                        {"value": "Draw", "odd": 3.40},
                                        {"value": "Away", "odd": 3.80}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        transformed = task._transform_odds_data(raw_data)

        assert isinstance(transformed, list)
        assert len(transformed) > 0

    def test_transform_scores_data(self):
        """测试转换比分数据"""
        config = CollectionConfig()
        task = DataCollectionTask(config)

        raw_data = {
            "matches": [
                {
                    "id": 123,
                    "score": {
                        "fullTime": {"home": 2, "away": 1},
                        "halfTime": {"home": 1, "away": 0}
                    },
                    "status": "FINISHED"
                }
            ]
        }

        transformed = task._transform_scores_data(raw_data)

        assert isinstance(transformed, list)
        assert len(transformed) == 1
        assert transformed[0]["match_id"] == 123
        assert transformed[0]["home_score"] == 2
        assert transformed[0]["away_score"] == 1
        assert transformed[0]["status"] == "FINISHED"


class TestDataCollectionManager:
    """数据采集管理器测试类"""

    def test_init(self):
        """测试初始化"""
        config = CollectionConfig(api_key="test_key")
        manager = DataCollectionManager(config)

        assert manager.config == config
        assert manager.tasks == {}
        assert manager.active_collections == {}

    def test_register_task(self):
        """测试注册任务"""
        config = CollectionConfig()
        manager = DataCollectionManager(config)

        task = DataCollectionTask(config)
        manager.register_task("fixtures", task)

        assert "fixtures" in manager.tasks
        assert manager.tasks["fixtures"] == task

    def test_start_collection(self):
        """测试开始采集"""
        config = CollectionConfig()
        manager = DataCollectionManager(config)

        task = DataCollectionTask(config)
        manager.register_task("fixtures", task)

        result = manager.start_collection("fixtures")

        assert result is True
        assert "fixtures" in manager.active_collections

    def test_stop_collection(self):
        """测试停止采集"""
        config = CollectionConfig()
        manager = DataCollectionManager(config)

        task = DataCollectionTask(config)
        manager.register_task("fixtures", task)
        manager.start_collection("fixtures")

        result = manager.stop_collection("fixtures")

        assert result is True
        assert "fixtures" not in manager.active_collections

    def test_get_collection_status(self):
        """测试获取采集状态"""
        config = CollectionConfig()
        manager = DataCollectionManager(config)

        # Test when no active collections
        status = manager.get_collection_status("fixtures")
        assert status == "inactive"

        # Test when collection is active
        task = DataCollectionTask(config)
        manager.register_task("fixtures", task)
        manager.start_collection("fixtures")

        status = manager.get_collection_status("fixtures")
        assert status == "active"

    def test_get_all_status(self):
        """测试获取所有状态"""
        config = CollectionConfig()
        manager = DataCollectionManager(config)

        task = DataCollectionTask(config)
        manager.register_task("fixtures", task)
        manager.register_task("odds", task)
        manager.start_collection("fixtures")

        status = manager.get_all_status()

        assert isinstance(status, dict)
        assert "fixtures" in status
        assert "odds" in status
        assert status["fixtures"] == "active"
        assert status["odds"] == "inactive"


class TestCollectionTasks:
    """采集任务函数测试"""

    @patch('src.tasks.data_collection_tasks.DataCollectionTask')
    @patch('src.tasks.data_collection_tasks.PROMETHEUS_METRICS')
    def test_collect_fixtures_task_success(self, mock_metrics, mock_task_class):
        """测试收集赛程任务成功"""
        # Mock task success
        mock_task = AsyncMock()
        mock_task.collect_fixtures.return_value = CollectionResult(
            success=True,
            data_type="fixtures",
            records_count=150,
            duration_seconds=25.5,
            api_calls_made=2
        )
        mock_task_class.return_value = mock_task
        mock_metrics.increment_counter = Mock()
        mock_metrics.record_gauge = Mock()

        result = asyncio.run(collect_fixtures_task())

        assert result.success is True
        assert result.data_type == "fixtures"
        assert result.records_count == 150
        mock_metrics.increment_counter.assert_called_once()
        mock_metrics.record_gauge.assert_called_once()

    @patch('src.tasks.data_collection_tasks.DataCollectionTask')
    @patch('src.tasks.data_collection_tasks.PROMETHEUS_METRICS')
    def test_collect_fixtures_task_failure(self, mock_metrics, mock_task_class):
        """测试收集赛程任务失败"""
        # Mock task failure
        mock_task = AsyncMock()
        mock_task.collect_fixtures.return_value = CollectionResult(
            success=False,
            data_type="fixtures",
            records_count=0,
            duration_seconds=5.0,
            api_calls_made=1,
            error_message="API timeout"
        )
        mock_task_class.return_value = mock_task
        mock_metrics.increment_counter = Mock()
        mock_metrics.record_gauge = Mock()

        result = asyncio.run(collect_fixtures_task())

        assert result.success is False
        assert result.data_type == "fixtures"
        assert result.records_count == 0
        assert "API timeout" in result.error_message
        mock_metrics.increment_counter.assert_called_once()

    @patch('src.tasks.data_collection_tasks.DataCollectionTask')
    @patch('src.tasks.data_collection_tasks.PROMETHEUS_METRICS')
    def test_collect_odds_task_success(self, mock_metrics, mock_task_class):
        """测试收集赔率任务成功"""
        # Mock task success
        mock_task = AsyncMock()
        mock_task.collect_odds.return_value = CollectionResult(
            success=True,
            data_type="odds",
            records_count=500,
            duration_seconds=45.0,
            api_calls_made=5
        )
        mock_task_class.return_value = mock_task
        mock_metrics.increment_counter = Mock()
        mock_metrics.record_gauge = Mock()

        result = asyncio.run(collect_odds_task())

        assert result.success is True
        assert result.data_type == "odds"
        assert result.records_count == 500
        mock_metrics.increment_counter.assert_called_once()

    @patch('src.tasks.data_collection_tasks.DataCollectionTask')
    @patch('src.tasks.data_collection_tasks.PROMETHEUS_METRICS')
    def test_collect_odds_task_failure(self, mock_metrics, mock_task_class):
        """测试收集赔率任务失败"""
        # Mock task failure
        mock_task = AsyncMock()
        mock_task.collect_odds.return_value = CollectionResult(
            success=False,
            data_type="odds",
            records_count=0,
            duration_seconds=8.0,
            api_calls_made=2,
            error_message="Invalid odds data format"
        )
        mock_task_class.return_value = mock_task
        mock_metrics.increment_counter = Mock()
        mock_metrics.record_gauge = Mock()

        result = asyncio.run(collect_odds_task())

        assert result.success is False
        assert result.data_type == "odds"
        assert result.records_count == 0
        assert "Invalid odds data format" in result.error_message
        mock_metrics.increment_counter.assert_called_once()

    @patch('src.tasks.data_collection_tasks.DataCollectionTask')
    @patch('src.tasks.data_collection_tasks.PROMETHEUS_METRICS')
    def test_collect_scores_task_success(self, mock_metrics, mock_task_class):
        """测试收集比分任务成功"""
        # Mock task success
        mock_task = AsyncMock()
        mock_task.collect_scores.return_value = CollectionResult(
            success=True,
            data_type="scores",
            records_count=50,
            duration_seconds=15.0,
            api_calls_made=1
        )
        mock_task_class.return_value = mock_task
        mock_metrics.increment_counter = Mock()
        mock_metrics.record_gauge = Mock()

        result = asyncio.run(collect_scores_task())

        assert result.success is True
        assert result.data_type == "scores"
        assert result.records_count == 50
        mock_metrics.increment_counter.assert_called_once()

    @patch('src.tasks.data_collection_tasks.DataCollectionTask')
    @patch('src.tasks.data_collection_tasks.PROMETHEUS_METRICS')
    def test_collect_scores_task_failure(self, mock_metrics, mock_task_class):
        """测试收集比分任务失败"""
        # Mock task failure
        mock_task = AsyncMock()
        mock_task.collect_scores.return_value = CollectionResult(
            success=False,
            data_type="scores",
            records_count=0,
            duration_seconds=3.0,
            api_calls_made=1,
            error_message="Network connection failed"
        )
        mock_task_class.return_value = mock_task
        mock_metrics.increment_counter = Mock()
        mock_metrics.record_gauge = Mock()

        result = asyncio.run(collect_scores_task())

        assert result.success is False
        assert result.data_type == "scores"
        assert result.records_count == 0
        assert "Network connection failed" in result.error_message
        mock_metrics.increment_counter.assert_called_once()


class TestDataCollectionIntegration:
    """数据采集集成测试"""

    @patch('src.tasks.data_collection_tasks.os.environ.get')
    def test_environment_configuration(self, mock_get):
        """测试环境配置"""
        # Mock environment variables
        mock_get.side_effect = lambda key, default=None: {
            'FOOTBALL_API_KEY': 'env_api_key',
            'FOOTBALL_API_BASE_URL': 'https://env.api.com/v4',
            'COLLECTION_TIMEOUT': '60',
            'COLLECTION_MAX_RETRIES': '5',
            'COLLECTION_RATE_LIMIT': '120'
        }.get(key, default)

        # Test that environment variables are used
        from src.tasks.data_collection_tasks import FOOTBALL_API_KEY, COLLECTION_TIMEOUT
        assert FOOTBALL_API_KEY == 'env_api_key'
        assert COLLECTION_TIMEOUT == 60

    @patch('src.tasks.data_collection_tasks.os.environ.get')
    def test_default_environment_values(self, mock_get):
        """测试默认环境值"""
        # Mock no environment variables
        mock_get.return_value = None

        # Test that default values are used
        from src.tasks.data_collection_tasks import FOOTBALL_API_KEY, COLLECTION_TIMEOUT
        assert FOOTBALL_API_KEY == "default_api_key"
        assert COLLECTION_TIMEOUT == 30

    def test_retry_logic_configuration(self):
        """测试重试逻辑配置"""
        config = CollectionConfig(max_retries=5, retry_delay=10)
        task = DataCollectionTask(config)

        assert task.config.max_retries == 5
        assert task.config.retry_delay == 10

    def test_rate_limiting_configuration(self):
        """测试速率限制配置"""
        config = CollectionConfig(rate_limit_per_minute=120)
        task = DataCollectionTask(config)

        assert task.config.rate_limit_per_minute == 120
        delay = task._calculate_rate_limit_delay()
        assert 0 <= delay <= 0.5  # 120 requests per minute = 0.5 seconds per request

    def test_batch_size_configuration(self):
        """测试批量大小配置"""
        config = CollectionConfig(batch_size=200)
        task = DataCollectionTask(config)

        assert task.config.batch_size == 200

    def test_caching_configuration(self):
        """测试缓存配置"""
        config = CollectionConfig(enable_caching=True, cache_ttl=7200)
        task = DataCollectionTask(config)

        assert task.config.enable_caching is True
        assert task.config.cache_ttl == 7200

    def test_timeout_configuration(self):
        """测试超时配置"""
        config = CollectionConfig(timeout=60)
        task = DataCollectionTask(config)

        assert task.config.timeout == 60

    def test_api_authentication(self):
        """测试API认证"""
        config = CollectionConfig(api_key="test_auth_key")
        task = DataCollectionTask(config)

        headers = task._prepare_api_headers()
        assert headers["X-Auth-Token"] == "test_auth_key"

    def test_data_validation_error_handling(self):
        """测试数据验证错误处理"""
        config = CollectionConfig()
        task = DataCollectionTask(config)

        # Test with invalid data structures
        invalid_data = None
        is_valid = task._validate_response_data(invalid_data, "fixtures")
        assert is_valid is False

        invalid_data = {}
        is_valid = task._validate_response_data(invalid_data, "fixtures")
        assert is_valid is False

    def test_transformation_error_handling(self):
        """测试转换错误处理"""
        config = CollectionConfig()
        task = DataCollectionTask(config)

        # Test with invalid data that should handle gracefully
        invalid_data = {"invalid": "data"}
        transformed = task._transform_fixtures_data(invalid_data)
        assert isinstance(transformed, list)


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])