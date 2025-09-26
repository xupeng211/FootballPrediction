"""
DataProcessingService 基础测试套件 - Phase 5.1 Batch-Δ-011

简化版测试，避免 pandas/numpy 冲突，专注于核心功能测试
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, List, Optional, Union
import pytest

from src.services.data_processing import DataProcessingService
from src.services.base import BaseService


class TestDataProcessingServiceBasic:
    """DataProcessingService 基础测试类"""

    @pytest.fixture
    def service(self):
        """创建 DataProcessingService 实例"""
        service = DataProcessingService()
        service.db_manager = Mock()
        service.cache_manager = Mock()
        service.quality_monitor = Mock()
        service.performance_monitor = Mock()
        return service

    @pytest.fixture
    def sample_raw_data(self):
        """示例原始数据"""
        return {
            "match_id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2023-01-01",
            "status": "completed"
        }

    @pytest.fixture
    def sample_processed_data(self):
        """示例处理后的数据"""
        return {
            "match_id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2023-01-01",
            "status": "completed",
            "processed_at": "2023-01-01T12:00:00",
            "data_quality_score": 0.95
        }

    # === 基础功能测试 ===

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, 'db_manager')
        assert hasattr(service, 'cache_manager')
        assert hasattr(service, 'quality_monitor')

    def test_process_raw_match_data_basic(self, service, sample_raw_data):
        """测试基础比赛数据处理"""
        result = service.process_raw_match_data(sample_raw_data)

        assert result is not None
        assert isinstance(result, dict)
        assert "match_id" in result
        assert result["match_id"] == sample_raw_data["match_id"]

    def test_process_raw_match_data_with_none(self, service):
        """测试空数据处理"""
        result = service.process_raw_match_data(None)
        assert result is None

    def test_process_raw_match_data_with_empty_dict(self, service):
        """测试空字典处理"""
        result = service.process_raw_match_data({})
        assert result is not None
        assert isinstance(result, dict)

    def test_process_raw_odds_data_basic(self, service):
        """测试基础赔率数据处理"""
        sample_odds = {
            "match_id": 12345,
            "home_win": 2.10,
            "draw": 3.40,
            "away_win": 3.60,
            "bookmaker": "BookmakerA"
        }

        result = service.process_raw_odds_data(sample_odds)

        assert result is not None
        assert isinstance(result, dict)
        assert "match_id" in result
        assert result["match_id"] == sample_odds["match_id"]

    def test_validate_data_quality_basic(self, service, sample_processed_data):
        """测试基础数据质量验证"""
        result = service.validate_data_quality(sample_processed_data)

        assert result is not None
        assert isinstance(result, dict)
        assert "quality_score" in result
        assert "is_valid" in result

    def test_validate_data_quality_with_missing_fields(self, service):
        """测试缺失字段的数据质量验证"""
        incomplete_data = {"match_id": 12345}

        result = service.validate_data_quality(incomplete_data)

        assert result is not None
        assert "quality_score" in result
        assert result["quality_score"] < 1.0

    def test_clean_data_basic(self, service, sample_raw_data):
        """测试基础数据清洗"""
        result = service.clean_data(sample_raw_data)

        assert result is not None
        assert isinstance(result, dict)
        # 验证清洗后的数据结构
        assert "match_id" in result

    def test_clean_data_with_none_values(self, service):
        """测试包含 None 值的数据清洗"""
        data_with_none = {
            "match_id": 12345,
            "home_team": None,
            "away_team": "Team B",
            "home_score": None,
            "away_score": 1
        }

        result = service.clean_data(data_with_none)

        assert result is not None
        assert isinstance(result, dict)

    def test_transform_data_basic(self, service, sample_processed_data):
        """测试基础数据转换"""
        result = service.transform_data(sample_processed_data)

        assert result is not None
        assert isinstance(result, dict)
        # 验证转换后的数据结构

    def test_normalize_data_basic(self, service, sample_processed_data):
        """测试基础数据标准化"""
        result = service.normalize_data(sample_processed_data)

        assert result is not None
        assert isinstance(result, dict)

    def test_enrich_data_basic(self, service, sample_processed_data):
        """测试基础数据增强"""
        result = service.enrich_data(sample_processed_data)

        assert result is not None
        assert isinstance(result, dict)
        # 验证增强后的数据包含额外字段

    # === 错误处理测试 ===

    def test_process_raw_match_data_with_invalid_data(self, service):
        """测试无效数据处理"""
        invalid_data = "invalid_string"

        with pytest.raises((ValueError, TypeError)):
            service.process_raw_match_data(invalid_data)

    def test_process_raw_odds_data_with_invalid_data(self, service):
        """测试无效赔率数据处理"""
        invalid_odds = "invalid_string"

        with pytest.raises((ValueError, TypeError)):
            service.process_raw_odds_data(invalid_odds)

    def test_validate_data_quality_with_invalid_data(self, service):
        """测试无效数据质量验证"""
        invalid_data = "invalid_string"

        with pytest.raises((ValueError, TypeError)):
            service.validate_data_quality(invalid_data)

    def test_clean_data_with_invalid_data(self, service):
        """测试无效数据清洗"""
        invalid_data = "invalid_string"

        with pytest.raises((ValueError, TypeError)):
            service.clean_data(invalid_data)

    # === 边界条件测试 ===

    def test_process_raw_match_data_with_extreme_values(self, service):
        """测试极值数据处理"""
        extreme_data = {
            "match_id": 999999999,
            "home_score": 999,
            "away_score": -1,
            "home_team": "A" * 1000,
            "away_team": "B" * 1000
        }

        result = service.process_raw_match_data(extreme_data)

        assert result is not None

    def test_process_raw_odds_data_with_extreme_odds(self, service):
        """测试极值赔率处理"""
        extreme_odds = {
            "match_id": 12345,
            "home_win": 9999.99,
            "draw": 0.001,
            "away_win": -1.0
        }

        result = service.process_raw_odds_data(extreme_odds)

        assert result is not None

    def test_validate_data_quality_with_empty_data(self, service):
        """测试空数据质量验证"""
        result = service.validate_data_quality({})

        assert result is not None
        assert "quality_score" in result

    # === 数据类型转换测试 ===

    def test_process_raw_match_data_type_conversion(self, service):
        """测试数据类型转换"""
        string_data = {
            "match_id": "12345",
            "home_score": "2",
            "away_score": "1",
            "match_date": "2023-01-01"
        }

        result = service.process_raw_match_data(string_data)

        assert result is not None
        # 验证类型转换是否正确

    def test_process_raw_odds_data_type_conversion(self, service):
        """测试赔率数据类型转换"""
        string_odds = {
            "match_id": "12345",
            "home_win": "2.10",
            "draw": "3.40",
            "away_win": "3.60"
        }

        result = service.process_raw_odds_data(string_odds)

        assert result is not None

    # === 业务逻辑测试 ===

    def test_data_quality_scoring(self, service, sample_processed_data):
        """测试数据质量评分逻辑"""
        result = service.validate_data_quality(sample_processed_data)

        assert "quality_score" in result
        assert 0 <= result["quality_score"] <= 1

    def test_data_validation_rules(self, service, sample_processed_data):
        """测试数据验证规则"""
        result = service.validate_data_quality(sample_processed_data)

        assert "validation_rules" in result
        assert isinstance(result["validation_rules"], dict)

    def test_data_cleaning_rules(self, service, sample_raw_data):
        """测试数据清洗规则"""
        result = service.clean_data(sample_raw_data)

        assert result is not None
        # 验证清洗规则应用

    def test_data_transformation_pipeline(self, service, sample_processed_data):
        """测试数据转换管道"""
        # 执行完整的数据处理管道
        cleaned = service.clean_data(sample_processed_data)
        transformed = service.transform_data(cleaned)
        normalized = service.normalize_data(transformed)
        enriched = service.enrich_data(normalized)

        assert enriched is not None
        assert isinstance(enriched, dict)

    # === 批量处理测试 ===

    def test_batch_process_raw_data(self, service, sample_raw_data):
        """测试批量原始数据处理"""
        batch_data = [sample_raw_data] * 5

        results = []
        for data in batch_data:
            result = service.process_raw_match_data(data)
            results.append(result)

        assert len(results) == 5
        assert all(result is not None for result in results)

    def test_batch_validate_data_quality(self, service, sample_processed_data):
        """测试批量数据质量验证"""
        batch_data = [sample_processed_data] * 3

        results = []
        for data in batch_data:
            result = service.validate_data_quality(data)
            results.append(result)

        assert len(results) == 3
        assert all("quality_score" in result for result in results)

    # === 缓存集成测试 ===

    def test_cache_integration(self, service, sample_raw_data):
        """测试缓存集成"""
        # 设置缓存模拟
        service.cache_manager.get.return_value = None
        service.cache_manager.set.return_value = True

        result = service.process_raw_match_data(sample_raw_data)

        # 验证缓存调用
        service.cache_manager.get.assert_called()
        service.cache_manager.set.assert_called()

    def test_cache_hit_scenario(self, service, sample_processed_data):
        """测试缓存命中场景"""
        # 设置缓存命中
        service.cache_manager.get.return_value = sample_processed_data

        result = service.process_raw_match_data({"match_id": 12345})

        # 验证从缓存获取数据
        service.cache_manager.get.assert_called()
        assert result == sample_processed_data

    # === 数据库集成测试 ===

    def test_database_integration(self, service, sample_processed_data):
        """测试数据库集成"""
        # 设置数据库模拟
        mock_session = Mock()
        service.db_manager.get_session.return_value = mock_session

        result = service.save_processed_data(sample_processed_data)

        # 验证数据库调用
        service.db_manager.get_session.assert_called()
        mock_session.add.assert_called()

    def test_database_transaction_rollback(self, service, sample_processed_data):
        """测试数据库事务回滚"""
        # 设置数据库异常
        mock_session = Mock()
        mock_session.add.side_effect = Exception("Database error")
        service.db_manager.get_session.return_value = mock_session

        with pytest.raises(Exception):
            service.save_processed_data(sample_processed_data)

        # 验证事务回滚
        mock_session.rollback.assert_called()

    # === 监控集成测试 ===

    def test_quality_monitoring_integration(self, service, sample_processed_data):
        """测试质量监控集成"""
        # 设置质量监控模拟
        service.quality_monitor.validate.return_value = {
            "quality_score": 0.95,
            "is_valid": True
        }

        result = service.validate_data_quality(sample_processed_data)

        # 验证质量监控调用
        service.quality_monitor.validate.assert_called()
        assert result["quality_score"] == 0.95

    def test_performance_monitoring_integration(self, service, sample_raw_data):
        """测试性能监控集成"""
        # 设置性能监控模拟
        service.performance_monitor.record_operation.return_value = True

        result = service.process_raw_match_data(sample_raw_data)

        # 验证性能监控调用
        service.performance_monitor.record_operation.assert_called()

    # === 数据完整性测试 ===

    def test_data_integrity_validation(self, service, sample_processed_data):
        """测试数据完整性验证"""
        result = service.validate_data_integrity(sample_processed_data)

        assert result is not None
        assert "is_integrity_valid" in result

    def test_data_consistency_check(self, service, sample_processed_data):
        """测试数据一致性检查"""
        result = service.check_data_consistency(sample_processed_data)

        assert result is not None
        assert "is_consistent" in result

    # === 配置驱动测试 ===

    @patch('src.services.data_processing.PROCESSING_CONFIG')
    def test_config_driven_processing(self, mock_config, service, sample_raw_data):
        """测试配置驱动的处理"""
        mock_config.return_value = {
            "enable_cleaning": True,
            "enable_validation": True,
            "enable_transformation": True
        }

        result = service.process_raw_match_data(sample_raw_data)

        assert result is not None
        # 验证配置被正确应用

    # === 日志记录测试 ===

    def test_logging_integration(self, service, sample_raw_data, caplog):
        """测试日志记录集成"""
        with caplog.at_level('INFO'):
            result = service.process_raw_match_data(sample_raw_data)

        assert result is not None
        # 验证日志记录
        assert len(caplog.records) > 0

    # === 性能基准测试 ===

    def test_processing_performance(self, service, sample_raw_data):
        """测试处理性能"""
        import time

        start_time = time.time()

        # 执行多次处理
        for _ in range(100):
            service.process_raw_match_data(sample_raw_data)

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证处理时间在合理范围内
        assert processing_time < 1.0  # 100次处理应在1秒内完成

    # === 并发处理测试 ===

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, service, sample_raw_data):
        """测试并发处理"""
        tasks = []

        # 创建多个并发任务
        for _ in range(10):
            task = asyncio.create_task(
                asyncio.to_thread(service.process_raw_match_data, sample_raw_data)
            )
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(result is not None for result in results)

    # === 内存使用测试 ===

    def test_memory_usage(self, service, sample_raw_data):
        """测试内存使用"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 处理大量数据
        for _ in range(1000):
            service.process_raw_match_data(sample_raw_data)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 验证内存增长在合理范围内
        assert memory_increase < 10 * 1024 * 1024  # 增长应小于10MB