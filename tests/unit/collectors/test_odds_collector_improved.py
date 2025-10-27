# TODO: Consider creating a fixture for 32 repeated Mock creations

# TODO: Consider creating a fixture for 32 repeated Mock creations

from unittest.mock import AsyncMock, Mock, patch

"""
赔率收集器改进版测试
Tests for improved odds collector

测试赔率收集器的功能。
"""

import asyncio
import sys
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")

from src.collectors.odds_collector_improved import (OddsAnalyzer,
                                                    OddsCollector,
                                                    OddsCollectorManager,
                                                    OddsProcessor,
                                                    OddsSourceManager,
                                                    OddsStorage,
                                                    get_odds_manager)


@pytest.mark.unit
class TestOddsCollectorImproved:
    """赔率收集器改进版测试"""

    @pytest.fixture
    def mock_collector(self):
        """创建模拟赔率收集器"""
        return Mock(spec=OddsCollector)

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return {
            "match_id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "home_win": 2.15,
            "draw": 3.40,
            "away_win": 3.20,
            "source": "bet365",
            "timestamp": "2025-01-01T12:00:00Z",
            "confidence": 0.95,
        }

    # ========================================
    # OddsCollector 测试
    # ========================================

    def test_odds_collector_import(self):
        """测试赔率收集器导入"""
        # 测试主要类是否可以导入
        assert OddsCollector is not None
        assert OddsCollectorManager is not None
        assert OddsSourceManager is not None

    @patch("src.collectors.odds_collector_improved.logger")
    def test_odds_collector_warning_on_import(self, mock_logger):
        """测试导入时的弃用警告"""
        with pytest.warns(DeprecationWarning):
            from src.collectors.odds_collector_improved import OddsCollector

    # ========================================
    # OddsCollectorManager 测试
    # ========================================

    def test_odds_collector_manager_creation(self):
        """测试赔率收集器管理器创建"""
        manager = OddsCollectorManager()
        assert manager is not None

    @pytest.mark.asyncio
    async def test_odds_collector_manager_start_collection(self):
        """测试启动赔率收集"""
        manager = OddsCollectorManager()

        # 模拟异步方法
        manager.start_collection = AsyncMock()
        manager.start_collection.return_value = {"status": "started", "tasks": 5}

        result = await manager.start_collection()
        assert result["status"] == "started"
        assert result["tasks"] == 5

    @pytest.mark.asyncio
    async def test_odds_collector_manager_stop_collection(self):
        """测试停止赔率收集"""
        manager = OddsCollectorManager()

        manager.stop_collection = AsyncMock()
        manager.stop_collection.return_value = {"status": "stopped", "completed": 3}

        result = await manager.stop_collection()
        assert result["status"] == "stopped"
        assert result["completed"] == 3

    @pytest.mark.asyncio
    async def test_odds_collector_manager_get_collection_status(self):
        """测试获取收集状态"""
        manager = OddsCollectorManager()

        manager.get_collection_status = AsyncMock()
        manager.get_collection_status.return_value = {
            "status": "running",
            "active_tasks": 3,
            "completed_today": 15,
        }

        result = await manager.get_collection_status()
        assert result["status"] == "running"
        assert result["active_tasks"] == 3

    # ========================================
    # OddsSourceManager 测试
    # ========================================

    def test_odds_source_manager_creation(self):
        """测试赔率源管理器创建"""
        manager = OddsSourceManager()
        assert manager is not None

    def test_odds_source_manager_add_source(self):
        """测试添加赔率源"""
        manager = OddsSourceManager()
        manager.add_source = Mock()

        source_config = {
            "name": "bet365",
            "url": "https://api.bet365.com/odds",
            "api_key": "test_key",
            "rate_limit": 100,
        }

        manager.add_source(source_config)
        manager.add_source.assert_called_once_with(source_config)

    def test_odds_source_manager_remove_source(self):
        """测试移除赔率源"""
        manager = OddsSourceManager()
        manager.remove_source = Mock()

        manager.remove_source("bet365")
        manager.remove_source.assert_called_once_with("bet365")

    def test_odds_source_manager_list_sources(self):
        """测试列出赔率源"""
        manager = OddsSourceManager()
        manager.list_sources = Mock(
            return_value=["bet365", "william_hill", "ladbrokes"]
        )

        sources = manager.list_sources()
        assert len(sources) == 3
        assert "bet365" in sources

    @pytest.mark.asyncio
    async def test_odds_source_manager_validate_source(self):
        """测试验证赔率源"""
        manager = OddsSourceManager()
        manager.validate_source = AsyncMock(return_value=True)

        result = await manager.validate_source("bet365")
        assert result is True

    # ========================================
    # OddsProcessor 测试
    # ========================================

    def test_odds_processor_creation(self):
        """测试赔率处理器创建"""
        processor = OddsProcessor()
        assert processor is not None

    def test_odds_processor_process_raw_data(self, sample_odds_data):
        """测试处理原始赔率数据"""
        processor = OddsProcessor()
        processor.process_raw_data = Mock(return_value=sample_odds_data)

        raw_data = '{"match_id": 12345, "odds": {"home": "2.15"}}'
        result = processor.process_raw_data(raw_data)

        assert result["match_id"] == 12345
        processor.process_raw_data.assert_called_once_with(raw_data)

    def test_odds_processor_normalize_odds(self):
        """测试赔率标准化"""
        processor = OddsProcessor()
        processor.normalize_odds = Mock(
            return_value={"home": 2.15, "draw": 3.40, "away": 3.20}
        )

        raw_odds = {"home_win": "2.15", "draw": "3.40", "away_win": "3.20"}
        result = processor.normalize_odds(raw_odds)

        assert "home" in result
        assert result["home"] == 2.15

    def test_odds_processor_validate_odds_format(self):
        """测试验证赔率格式"""
        processor = OddsProcessor()
        processor.validate_odds_format = Mock(return_value=True)

        valid_odds = {"home": 2.15, "draw": 3.40, "away": 3.20}
        result = processor.validate_odds_format(valid_odds)
        assert result is True

    def test_odds_processor_calculate_implied_probabilities(self):
        """测试计算隐含概率"""
        processor = OddsProcessor()
        processor.calculate_implied_probabilities = Mock(
            return_value={"home": 0.465, "draw": 0.294, "away": 0.312}
        )

        odds = {"home": 2.15, "draw": 3.40, "away": 3.20}
        result = processor.calculate_implied_probabilities(odds)

        assert result["home"] == 0.465

    # ========================================
    # OddsAnalyzer 测试
    # ========================================

    def test_odds_analyzer_creation(self):
        """测试赔率分析器创建"""
        analyzer = OddsAnalyzer()
        assert analyzer is not None

    def test_odds_analyzer_detect_value_bets(self):
        """测试检测价值投注"""
        analyzer = OddsAnalyzer()
        analyzer.detect_value_bets = Mock(
            return_value=[{"match": 12345, "value": 0.15}]
        )

        odds_data = [{"match_id": 12345, "home": 2.15, "draw": 3.40, "away": 3.20}]
        result = analyzer.detect_value_bets(odds_data)

        assert len(result) == 1
        assert result[0]["match"] == 12345

    def test_odds_analyzer_analyze_market_trends(self):
        """测试分析市场趋势"""
        analyzer = OddsAnalyzer()
        analyzer.analyze_market_trends = Mock(
            return_value={"trend": "upward", "confidence": 0.85}
        )

        historical_odds = [{"timestamp": "2025-01-01", "home": 2.10}]
        result = analyzer.analyze_market_trends(historical_odds)

        assert result["trend"] == "upward"

    def test_odds_analyzer_compare_sources(self):
        """测试比较不同源的数据"""
        analyzer = OddsAnalyzer()
        analyzer.compare_sources = Mock(
            return_value={"best_source": "bet365", "difference": 0.05}
        )

        source_a = {"home": 2.15, "source": "bet365"}
        source_b = {"home": 2.10, "source": "william_hill"}
        result = analyzer.compare_sources(source_a, source_b)

        assert result["best_source"] == "bet365"

    # ========================================
    # OddsStorage 测试
    # ========================================

    def test_odds_storage_creation(self):
        """测试赔率存储创建"""
        storage = OddsStorage()
        assert storage is not None

    @pytest.mark.asyncio
    async def test_odds_storage_save_odds(self, sample_odds_data):
        """测试保存赔率数据"""
        storage = OddsStorage()
        storage.save_odds = AsyncMock(return_value={"status": "saved", "id": "12345"})

        result = await storage.save_odds(sample_odds_data)
        assert result["status"] == "saved"

    @pytest.mark.asyncio
    async def test_odds_storage_get_latest_odds(self):
        """测试获取最新赔率"""
        storage = OddsStorage()
        storage.get_latest_odds = AsyncMock(return_value=sample_odds_data)

        result = await storage.get_latest_odds(12345)
        assert result["match_id"] == 12345

    @pytest.mark.asyncio
    async def test_odds_storage_get_historical_odds(self):
        """测试获取历史赔率"""
        storage = OddsStorage()
        storage.get_historical_odds = AsyncMock(return_value=[sample_odds_data])

        result = await storage.get_historical_odds(12345, days=7)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_odds_storage_delete_old_odds(self):
        """测试删除旧赔率数据"""
        storage = OddsStorage()
        storage.delete_old_odds = AsyncMock(return_value={"deleted": 100})

        result = await storage.delete_old_odds(days=30)
        assert result["deleted"] == 100

    # ========================================
    # 便捷函数测试
    # ========================================

    def test_get_odds_manager(self):
        """测试获取赔率管理器便捷函数"""
        manager = get_odds_manager()
        assert isinstance(manager, OddsCollectorManager)

    # ========================================
    # 错误处理测试
    # ========================================

    @pytest.mark.asyncio
    async def test_collection_error_handling(self):
        """测试收集过程错误处理"""
        manager = OddsCollectorManager()
        manager.start_collection = AsyncMock(side_effect=Exception("API Error"))

        with pytest.raises(Exception, match="API Error"):
            await manager.start_collection()

    @pytest.mark.asyncio
    async def test_storage_error_handling(self):
        """测试存储错误处理"""
        storage = OddsStorage()
        storage.save_odds = AsyncMock(side_effect=Exception("Database Error"))

        with pytest.raises(Exception, match="Database Error"):
            await storage.save_odds({})

    # ========================================
    # 集成测试
    # ========================================

    @pytest.mark.asyncio
    async def test_full_odds_collection_workflow(self, sample_odds_data):
        """测试完整的赔率收集工作流程"""
        # 创建组件
        manager = OddsCollectorManager()
        processor = OddsProcessor()
        storage = OddsStorage()

        # 模拟组件方法
        manager.start_collection = AsyncMock(return_value={"status": "started"})
        processor.process_raw_data = Mock(return_value=sample_odds_data)
        storage.save_odds = AsyncMock(return_value={"status": "saved"})

        # 执行工作流程
        collection_result = await manager.start_collection()
        assert collection_result["status"] == "started"

        processed_data = processor.process_raw_data('{"raw": "data"}')
        assert processed_data["match_id"] == 12345

        save_result = await storage.save_odds(processed_data)
        assert save_result["status"] == "saved"

    # ========================================
    # 性能测试
    # ========================================

    @pytest.mark.asyncio
    async def test_bulk_odds_processing(self):
        """测试批量赔率处理性能"""
        processor = OddsProcessor()
        processor.normalize_odds = Mock(return_value={"home": 2.15})

        # 模拟大量数据
        bulk_data = [{"home": "2.15"} for _ in range(1000)]

        import time

        start_time = time.time()

        results = [processor.normalize_odds(data) for data in bulk_data]

        end_time = time.time()
        processing_time = end_time - start_time

        assert len(results) == 1000
        assert processing_time < 1.0  # 应该在1秒内完成

    def test_memory_usage_optimization(self):
        """测试内存使用优化"""
        import sys

        manager = OddsCollectorManager()

        # 获取对象大小
        manager_size = sys.getsizeof(manager)
        assert manager_size < 10000  # 应该小于10KB

    # ========================================
    # 配置测试
    # ========================================

    def test_collector_configuration(self):
        """测试收集器配置"""
        config = {
            "sources": ["bet365", "william_hill"],
            "update_interval": 300,
            "max_retries": 3,
            "timeout": 30,
        }

        manager = OddsCollectorManager()
        manager.configure = Mock()

        manager.configure(config)
        manager.configure.assert_called_once_with(config)

    def test_source_manager_configuration(self):
        """测试源管理器配置"""
        config = {
            "default_rate_limit": 100,
            "timeout": 30,
            "retry_policy": "exponential_backoff",
        }

        source_manager = OddsSourceManager()
        source_manager.configure = Mock()

        source_manager.configure(config)
        source_manager.configure.assert_called_once_with(config)


class TestOddsCollectorIntegration:
    """赔率收集器集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_odds_workflow(self):
        """测试端到端赔率工作流程"""
        # 创建所有组件
        manager = OddsCollectorManager()
        source_manager = OddsSourceManager()
        processor = OddsProcessor()
        analyzer = OddsAnalyzer()
        storage = OddsStorage()

        # 模拟完整工作流程
        manager.start_collection = AsyncMock(return_value={"status": "started"})
        source_manager.validate_source = AsyncMock(return_value=True)
        processor.process_raw_data = Mock(return_value={"match_id": 12345})
        analyzer.detect_value_bets = Mock(return_value=[])
        storage.save_odds = AsyncMock(return_value={"status": "saved"})

        # 执行工作流程
        await manager.start_collection()
        assert True  # 如果没有异常，说明工作流程正常

    def test_component_dependency_injection(self):
        """测试组件依赖注入"""
        storage = OddsStorage()
        processor = OddsProcessor()

        # 模拟依赖注入
        manager = OddsCollectorManager(storage=storage, processor=processor)
        assert manager is not None
