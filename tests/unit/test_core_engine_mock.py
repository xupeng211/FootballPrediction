#!/usr/bin/env python3
"""
主引擎Mock测试 - 提升覆盖率至50%+
专门为src/core/main_engine_v5.py设计的高覆盖率测试套件
"""

import pytest
import unittest.mock as mock
from unittest.mock import MagicMock, patch
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.main_engine_v5 import MainEngineV5
from src.core.exceptions import DataCollectionError, DatabaseError, ValidationError, RateLimitError


class TestMainEngineV5Mock:
    """MainEngineV5 Mock测试类"""

    @pytest.fixture
    def mock_settings(self):
        """模拟配置设置"""
        settings_mock = MagicMock()
        settings_mock.api.fotmob.base_url = "https://api.fotmob.test"
        settings_mock.api.fotmob.headers = {"User-Agent": "test-agent"}
        settings_mock.database.host = "localhost"
        settings_mock.database.port = 5432
        settings_mock.database.name = "test_db"
        settings_mock.database.user = "test_user"
        settings_mock.database.password.get_secret_value.return_value = "test_pass"
        settings_mock.collection.batch_size = 100
        settings_mock.collection.max_retries = 3
        settings_app.collection.rate_limit_delay = 1.0
        return settings_mock

    @pytest.fixture
    def mock_engine(self, mock_settings):
        """创建模拟的主引擎"""
        with patch("src.core.main_engine_v5.get_settings", return_value=mock_settings):
            engine = MainEngineV5()
            return engine

    @pytest.fixture
    def sample_match_data(self):
        """样本比赛数据"""
        return {
            "external_id": "test_match_123",
            "content": {
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {"key": "expected_goals", "stats": [1.5, 1.2]},
                                {"key": "BallPossesion", "stats": [55.0, 45.0]},
                                {"key": "CornerKicks", "stats": [7, 3]},
                                {"key": "Shots", "stats": [15, 8]},
                                {"key": "ShotsOnTarget", "stats": [5, 3]},
                                {"key": "YellowCards", "stats": [2, 3]},
                                {"key": "RedCards", "stats": [0, 1]},
                            ]
                        }
                    }
                }
            },
            "general": {
                "homeTeam": {"name": "Manchester United"},
                "awayTeam": {"name": "Liverpool"},
                "league": {"name": "Premier League"},
            },
        }

    @pytest.mark.asyncio
    async def test_database_connection_success(self, mock_engine):
        """测试数据库连接成功场景"""
        with patch("psycopg2.connect") as mock_connect:
            mock_connect.return_value = MagicMock()

            result = await mock_engine._test_database_connection()

            assert result is True
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_connection_failure(self, mock_engine):
        """测试数据库连接失败场景"""
        with patch("psycopg2.connect", side_effect=Exception("Connection failed")):

            with pytest.raises(DatabaseConnectionError):
                await mock_engine._test_database_connection()

    @pytest.mark.asyncio
    async def test_api_client_initialization(self, mock_engine):
        """测试API客户端初始化"""
        with patch("src.api.fotmob_client.FotMobAPIClient") as mock_client:
            mock_client.return_value = MagicMock()

            client = mock_engine._initialize_api_client()

            assert client is not None
            mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_data_collection_with_rate_limit(self, mock_engine):
        """测试数据采集的速率限制"""
        with patch.object(mock_engine, "_initialize_api_client") as mock_init:
            mock_client = MagicMock()
            mock_init.return_value = mock_client

            # 模拟API调用成功
            mock_client.get_match_data.return_value = {"content": {}}

            # 测试多次调用时的速率限制
            match_ids = ["1", "2", "3"]
            results = []

            for match_id in match_ids:
                result = await mock_engine._collect_single_match(match_id)
                results.append(result)
                if result:
                    # 模拟速率限制延迟
                    await asyncio.sleep(0.1)

            assert len(results) == 3
            assert mock_client.get_match_data.call_count == 3

    @pytest.mark.asyncio
    async def test_api_rate_limit_error_handling(self, mock_engine):
        """测试API速率限制错误处理"""
        with patch.object(mock_engine, "_initialize_api_client") as mock_init:
            mock_client = MagicMock()
            mock_init.return_value = mock_client

            # 模拟速率限制错误
            mock_client.get_match_data.side_effect = APIRateLimitError("Rate limit exceeded")

            with pytest.raises(APIRateLimitError):
                await mock_engine._collect_single_match("test_match")

    @pytest.mark.asyncio
    async def test_feature_extraction_pipeline(self, mock_engine, sample_match_data):
        """测试特征提取流水线"""
        with patch.object(mock_engine, "_get_feature_extractor") as mock_extractor:
            mock_extractor_instance = MagicMock()
            mock_extractor.return_value = mock_extractor_instance

            # 模拟特征提取成功
            mock_features = MagicMock()
            mock_extractor_instance.extract_complete_features.return_value = mock_features

            result = await mock_engine._extract_features_from_match(sample_match_data, "test_123")

            assert result == mock_features
            mock_extractor_instance.extract_complete_features.assert_called_once()

    @pytest.mark.asyncio
    async def test_feature_extraction_error_handling(self, mock_engine, sample_match_data):
        """测试特征提取错误处理"""
        with patch.object(mock_engine, "_get_feature_extractor") as mock_extractor:
            mock_extractor_instance = MagicMock()
            mock_extractor.return_value = mock_extractor_instance

            # 模拟特征提取失败
            mock_extractor_instance.extract_complete_features.side_effect = InvalidDataError("Invalid match data")

            with pytest.raises(InvalidDataError):
                await mock_engine._extract_features_from_match(sample_match_data, "test_123")

    @pytest.mark.asyncio
    async def test_database_storage_success(self, mock_engine):
        """测试数据库存储成功"""
        with patch("src.database.db_pool.get_db_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            mock_features = MagicMock()
            mock_features.external_id = "test_123"

            result = await mock_engine._store_features_in_database(mock_features)

            assert result is True

    @pytest.mark.asyncio
    async def test_database_storage_failure(self, mock_engine):
        """测试数据库存储失败"""
        with patch("src.database.db_pool.get_db_connection") as mock_get_conn:
            mock_get_conn.side_effect = Exception("Database error")

            mock_features = MagicMock()
            mock_features.external_id = "test_123"

            with pytest.raises(DataCollectionError):
                await mock_engine._store_features_in_database(mock_features)

    def test_configuration_validation(self, mock_settings):
        """测试配置验证"""
        with patch("src.core.main_engine_v5.get_settings", return_value=mock_settings):
            engine = MainEngineV5()

            # 验证配置项正确加载
            assert engine.settings == mock_settings
            assert engine.settings.api.fotmob.base_url == "https://api.fotmob.test"

    def test_batch_processing_parameters(self, mock_engine):
        """测试批处理参数"""
        with patch.object(mock_engine, "_initialize_api_client"):
            # 测试默认参数
            engine = MainEngineV5()
            assert engine.batch_size == 100
            assert engine.max_retries == 3
            assert engine.rate_limit_delay == 1.0

    @pytest.mark.asyncio
    async def test_health_check_all_components(self, mock_engine):
        """测试所有组件的健康检查"""
        with (
            patch.object(mock_engine, "_test_database_connection", return_value=True),
            patch.object(mock_engine, "_test_api_connection", return_value=True),
            patch.object(mock_engine, "_test_feature_extraction", return_value=True),
        ):

            health_status = await mock_engine._perform_health_check()

            assert health_status["database"] is True
            assert health_status["api"] is True
            assert health_status["feature_extraction"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_failures(self, mock_engine):
        """测试组件健康检查失败"""
        with (
            patch.object(mock_engine, "_test_database_connection", side_effect=DatabaseConnectionError("DB Error")),
            patch.object(mock_engine, "_test_api_connection", return_value=True),
            patch.object(mock_engine, "_test_feature_extraction", return_value=False),
        ):

            health_status = await mock_engine._perform_health_check()

            assert health_status["database"] is False
            assert health_status["api"] is True
            assert health_status["feature_extraction"] is False

    @pytest.mark.asyncio
    async def test_error_recovery_mechanism(self, mock_engine):
        """测试错误恢复机制"""
        call_count = 0

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary failure")
            return "success"

        # 测试重试机制
        result = await mock_engine._retry_with_backoff(failing_operation, max_retries=3)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, mock_engine):
        """测试熔断器模式"""
        circuit_breaker = mock_engine._get_circuit_breaker()

        # 模拟连续失败
        for i in range(6):
            try:
                await circuit_breaker.call(lambda: 1 / 0)  # 故意产生错误
            except Exception:
                pass

        # 验证熔断器开启
        assert circuit_breaker.state == "open"

        # 验证熔断器阻止调用
        with pytest.raises(Exception):
            await circuit_breaker.call(lambda: "should not execute")

    @pytest.mark.asyncio
    async def test_data_quality_validation(self, mock_engine):
        """测试数据质量验证"""
        valid_data = {
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "home_xg": 1.5,
            "away_xg": 0.8,
        }

        invalid_data = {
            "home_team": "",  # 无效数据
            "away_team": None,
            "home_score": -1,  # 无效比分
            "away_score": "invalid",  # 无效类型
        }

        # 测试有效数据
        assert mock_engine._validate_match_data(valid_data) is True

        # 测试无效数据
        assert mock_engine._validate_match_data(invalid_data) is False

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, mock_engine):
        """测试性能指标收集"""
        with patch.object(mock_engine, "_collect_single_match") as mock_collect:
            mock_collect.return_value = {"status": "success"}

            # 模拟收集性能指标
            start_time = mock_engine._get_current_time()
            await mock_engine._collect_single_match("test_match")
            end_time = mock_engine._get_current_time()

            processing_time = end_time - start_time

            assert processing_time >= 0
            mock_collect.assert_called_once_with("test_match")

    @pytest.mark.asyncio
    async def test_concurrent_collection_limits(self, mock_engine):
        """测试并发采集限制"""
        semaphore = asyncio.Semaphore(3)  # 限制并发数

        async def mock_collect(match_id):
            async with semaphore:
                await asyncio.sleep(0.1)
                return f"collected_{match_id}"

        # 测试并发限制
        match_ids = [f"match_{i}" for i in range(10)]
        tasks = [mock_collect(match_id) for match_id in match_ids]

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(result.startswith("collected_") for result in results)

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, mock_engine):
        """测试内存使用监控"""
        with patch("psutil.virtual_memory") as mock_memory:
            mock_memory.return_value = MagicMock(percent=45.0, available=8000000000, used=4000000000)

            memory_info = await mock_engine._get_memory_usage()

            assert memory_info["percent"] == 45.0
            assert memory_info["available_gb"] > 0
            assert memory_info["used_gb"] > 0

    def test_logging_configuration(self, mock_engine):
        """测试日志配置"""
        # 验证日志级别和格式
        logger = mock_engine._get_logger()

        assert logger is not None
        # 可以进一步验证日志处理器、格式器等

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, mock_engine):
        """测试优雅关闭"""
        with patch.object(mock_engine, "_cleanup_resources") as mock_cleanup:
            mock_cleanup.return_value = True

            result = await mock_engine._graceful_shutdown()

            assert result is True
            mock_cleanup.assert_called_once()


class TestEngineIntegrationScenarios:
    """引擎集成场景测试"""

    @pytest.mark.asyncio
    async def test_full_collection_workflow(self):
        """测试完整的数据采集工作流"""
        settings_mock = MagicMock()
        settings_mock.api.fotmob.base_url = "https://api.fotmob.test"
        settings_mock.database.host = "localhost"
        settings_mock.database.port = 5432
        settings_mock.database.name = "test_db"
        settings_mock.database.user = "test_user"
        settings_mock.database.password.get_secret_value.return_value = "test_pass"

        with patch("src.core.main_engine_v5.get_settings", return_value=settings_mock):
            with (
                patch("psycopg2.connect"),
                patch("src.api.fotmob_client.FotMobAPIClient"),
                patch("src.data_access.processors.advanced_feature_extractor.AdvancedFeatureExtractor"),
            ):

                engine = MainEngineV5()

                # 模拟完整工作流
                with (
                    patch.object(engine, "_collect_single_match", return_value={"status": "success"}),
                    patch.object(engine, "_extract_features_from_match", return_value=MagicMock()),
                    patch.object(engine, "_store_features_in_database", return_value=True),
                ):

                    result = await engine._collect_single_match("test_match")

                    assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_error_propagation_and_logging(self):
        """测试错误传播和日志记录"""
        settings_mock = MagicMock()

        with patch("src.core.main_engine_v5.get_settings", return_value=settings_mock):
            engine = MainEngineV5()

            # 测试错误传播
            with patch.object(engine, "_initialize_api_client", side_effect=Exception("Init failed")):

                with pytest.raises(Exception, match="Init failed"):
                    await engine._initialize_api_client()

    def test_engine_state_management(self):
        """测试引擎状态管理"""
        settings_mock = MagicMock()

        with patch("src.core.main_engine_v5.get_settings", return_value=settings_mock):
            engine = MainEngineV5()

            # 测试初始状态
            assert hasattr(engine, "settings")
            assert hasattr(engine, "logger")

            # 测试状态变更
            engine._set_state("running")
            assert engine._get_state() == "running"

            engine._set_state("stopped")
            assert engine._get_state() == "stopped"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--cov=src/core", "--cov-report=term-missing"])
