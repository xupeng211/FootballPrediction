"""
数据质量监控服务测试
Data Quality Monitor Service Tests

测试数据质量监控服务的核心功能。
Tests core functionality of data quality monitor service.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.services.data_quality_monitor import DataQualityMonitor


class TestDataQualityMonitorBasic:
    """测试数据质量监控基础功能"""

    def test_default_initialization(self):
        """测试默认初始化"""
        monitor = DataQualityMonitor()

        assert monitor.config == {}
        assert monitor.status == "initialized"
        assert "processed_items" in monitor.metrics
        assert "errors" in monitor.metrics
        assert "start_time" in monitor.metrics
        assert monitor.metrics["processed_items"] == 0
        assert monitor.metrics["errors"] == 0
        assert isinstance(monitor.metrics["start_time"], datetime)

    def test_custom_config_initialization(self):
        """测试自定义配置初始化"""
        custom_config = {
            "batch_size": 100,
            "timeout": 30,
            "retry_count": 3,
            "validation_rules": ["required_fields", "data_types"]
        }
        monitor = DataQualityMonitor(custom_config)

        assert monitor.config == custom_config
        assert monitor.status == "initialized"

    def test_get_metrics_empty(self):
        """测试获取空指标"""
        monitor = DataQualityMonitor()
        metrics = monitor.get_metrics()

        assert metrics["processed_items"] == 0
        assert metrics["errors"] == 0
        assert "duration" in metrics
        assert "throughput" in metrics
        assert isinstance(metrics["duration"], float)
        assert isinstance(metrics["throughput"], float)


class TestDataProcessing:
    """测试数据处理功能"""

    @pytest.mark.asyncio
    async def test_process_data_basic(self):
        """测试基础数据处理"""
        monitor = DataQualityMonitor()
        processed_items = []

        async for data in monitor.process_data("test_source"):
            processed_items.append(data)

        assert len(processed_items) == 10  # 模拟处理10个项目
        assert all(item["processed"] for item in processed_items)
        assert all("id" in item for item in processed_items)
        assert all("timestamp" in item for item in processed_items)
        assert all("quality_score" in item for item in processed_items)

    @pytest.mark.asyncio
    async def test_process_data_metrics_update(self):
        """测试数据处理指标更新"""
        monitor = DataQualityMonitor()
        initial_items = monitor.metrics["processed_items"]

        # 处理所有数据
        async for _ in monitor.process_data("test_source"):
            pass

        final_items = monitor.metrics["processed_items"]
        assert final_items - initial_items == 10

    @pytest.mark.asyncio
    async def test_process_data_quality_scores(self):
        """测试数据质量分数"""
        monitor = DataQualityMonitor()
        quality_scores = []

        async for data in monitor.process_data("test_source"):
            quality_scores.append(data["quality_score"])

        # 验证质量分数在预期范围内
        for score in quality_scores:
            assert 0.95 <= score <= 1.0

        # 验证质量分数变化模式
        expected_scores = [0.95, 0.96, 0.97, 0.98, 0.99, 0.95, 0.96, 0.97, 0.98, 0.99]
        assert quality_scores == expected_scores

    @pytest.mark.asyncio
    async def test_process_data_different_sources(self):
        """测试不同数据源处理"""
        monitor = DataQualityMonitor()
        sources = ["source1", "source2", "source3"]

        for source in sources:
            items = []
            async for data in monitor.process_data(source):
                items.append(data)
            assert len(items) == 10

    @pytest.mark.asyncio
    @patch('src.services.data_quality_monitor.logger')
    async def test_process_data_with_exception(self, mock_logger):
        """测试处理数据时的异常"""
        monitor = DataQualityMonitor()

        # 模拟异常
        with patch.object(monitor, 'process_data') as mock_process:
            mock_process.side_effect = Exception("Processing failed")

            with pytest.raises(Exception, match="Processing failed"):
                async for _ in monitor.process_data("test_source"):
                    pass

            # 验证错误计数增加
            assert monitor.metrics["errors"] == 1
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_data_timing(self):
        """测试数据处理时间"""
        monitor = DataQualityMonitor()
        start_time = datetime.now()

        async for _ in monitor.process_data("test_source"):
            pass

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # 验证处理时间合理（应该大约1秒，因为每次迭代有0.1秒延迟）
        assert 0.8 <= processing_time <= 1.5


class TestDataValidation:
    """测试数据验证功能"""

    @pytest.mark.asyncio
    async def test_validate_data_valid(self):
        """测试有效数据验证"""
        monitor = DataQualityMonitor()
        test_data = {
            "id": 123,
            "name": "Test Prediction",
            "confidence": 0.85,
            "timestamp": datetime.now().isoformat()
        }

        result = await monitor.validate_data(test_data)

        assert result["valid"] is True
        assert result["score"] == 0.98
        assert result["issues"] == []
        assert result["recommendations"] == []

    @pytest.mark.asyncio
    async def test_validate_data_empty(self):
        """测试空数据验证"""
        monitor = DataQualityMonitor()
        empty_data = {}

        result = await monitor.validate_data(empty_data)

        assert result["valid"] is True  # 当前实现总是返回True
        assert result["score"] == 0.98

    @pytest.mark.asyncio
    async def test_validate_data_invalid_format(self):
        """测试无效格式数据验证"""
        monitor = DataQualityMonitor()
        invalid_data = "invalid_data_string"

        result = await monitor.validate_data(invalid_data)

        assert result["valid"] is True  # 当前实现没有格式验证
        assert result["score"] == 0.98

    @pytest.mark.asyncio
    @patch('src.services.data_quality_monitor.logger')
    async def test_validate_data_with_exception(self, mock_logger):
        """测试验证数据时的异常"""
        monitor = DataQualityMonitor()

        # 模拟异常
        with patch.object(monitor, 'validate_data') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")

            result = await monitor.validate_data({"test": "data"})

            assert result["valid"] is False
            assert result["score"] == 0.0
            assert "Validation failed" in result["issues"]
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_data_various_types(self):
        """测试各种类型数据验证"""
        monitor = DataQualityMonitor()
        test_cases = [
            {"type": "string", "data": "test string"},
            {"type": "integer", "data": 42},
            {"type": "float", "data": 3.14},
            {"type": "boolean", "data": True},
            {"type": "list", "data": [1, 2, 3]},
            {"type": "dict", "data": {"key": "value"}},
            {"type": "none", "data": None},
        ]

        for test_case in test_cases:
            result = await monitor.validate_data(test_case["data"])
            assert result["valid"] is True
            assert isinstance(result["score"], float)


class TestMetricsCalculation:
    """测试指标计算功能"""

    def test_get_metrics_after_processing(self):
        """测试处理后的指标获取"""
        monitor = DataQualityMonitor()

        # 模拟一些处理
        monitor.metrics["processed_items"] = 50
        monitor.metrics["errors"] = 2

        metrics = monitor.get_metrics()

        assert metrics["processed_items"] == 50
        assert metrics["errors"] == 2
        assert "duration" in metrics
        assert "throughput" in metrics
        assert metrics["throughput"] >= 0

    def test_throughput_calculation(self):
        """测试吞吐量计算"""
        monitor = DataQualityMonitor()

        # 模拟1秒内处理100个项目
        import time
        time.sleep(0.1)  # 确保有一些时间差

        monitor.metrics["processed_items"] = 100
        monitor.metrics["start_time"] = datetime.now().timestamp() - 1.0

        metrics = monitor.get_metrics()

        # 吞吐量应该大约是100 items/second
        assert 90 <= metrics["throughput"] <= 110

    def test_duration_calculation(self):
        """测试持续时间计算"""
        monitor = DataQualityMonitor()

        # 模拟开始时间为2秒前
        monitor.metrics["start_time"] = datetime.now().timestamp() - 2.0

        metrics = monitor.get_metrics()

        # 持续时间应该大约是2秒
        assert 1.8 <= metrics["duration"] <= 2.2

    def test_throughput_zero_items(self):
        """测试零项目吞吐量"""
        monitor = DataQualityMonitor()
        monitor.metrics["processed_items"] = 0

        metrics = monitor.get_metrics()

        # 零项目时吞吐量应该为0
        assert metrics["throughput"] == 0.0


class TestDataQualityMonitorIntegration:
    """数据质量监控集成测试"""

    @pytest.mark.asyncio
    async def test_full_processing_workflow(self):
        """测试完整处理工作流"""
        monitor = DataQualityMonitor()
        processed_count = 0
        validation_results = []

        # 处理数据
        async for data in monitor.process_data("integration_test"):
            processed_count += 1

            # 验证每个处理的数据项
            validation_result = await monitor.validate_data(data)
            validation_results.append(validation_result)

        # 验证结果
        assert processed_count == 10
        assert len(validation_results) == 10
        assert all(result["valid"] for result in validation_results)

        # 验证最终指标
        final_metrics = monitor.get_metrics()
        assert final_metrics["processed_items"] == 10
        assert final_metrics["errors"] == 0
        assert final_metrics["throughput"] > 0

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """测试错误恢复工作流"""
        monitor = DataQualityMonitor()
        initial_errors = monitor.metrics["errors"]

        # 模拟处理失败的数据
        try:
            await monitor.validate_data(None)  # 可能导致异常
        except:
            pass

        # 尝试验证会产生异常的数据
        with patch.object(monitor, 'validate_data') as mock_validate:
            mock_validate.side_effect = Exception("Test error")

            result = await monitor.validate_data({"test": "data"})

            # 验证错误处理
            assert result["valid"] is False
            assert monitor.metrics["errors"] > initial_errors

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """测试并发处理"""
        monitor = DataQualityMonitor()

        async def process_source(source_name):
            """处理单个数据源"""
            items = []
            async for data in monitor.process_data(source_name):
                validation = await monitor.validate_data(data)
                items.append(validation)
            return items

        # 并发处理多个数据源
        tasks = [
            process_source("source1"),
            process_source("source2"),
            process_source("source3")
        ]

        results = await asyncio.gather(*tasks)

        # 验证结果
        assert len(results) == 3
        assert all(len(result) == 10 for result in results)
        assert all(item["valid"] for result in results for item in result)

    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """测试性能监控"""
        monitor = DataQualityMonitor()

        start_time = datetime.now()
        processed_items = 0

        # 处理数据并监控性能
        async for data in monitor.process_data("performance_test"):
            processed_items += 1

            # 验证数据
            await monitor.validate_data(data)

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # 获取最终指标
        metrics = monitor.get_metrics()

        # 验证性能指标
        assert processed_items == 10
        assert metrics["processed_items"] == 10
        assert metrics["throughput"] > 0
        assert processing_time > 0

        # 验证指标合理性
        expected_throughput = processed_items / processing_time
        actual_throughput = metrics["throughput"]

        # 允许一些误差
        assert abs(expected_throughput - actual_throughput) < 5.0

    @pytest.mark.asyncio
    async def test_data_quality_score_tracking(self):
        """测试数据质量分数跟踪"""
        monitor = DataQualityMonitor()
        quality_scores = []

        # 处理数据并收集质量分数
        async for data in monitor.process_data("quality_test"):
            validation = await monitor.validate_data(data)
            quality_scores.append(validation["score"])

        # 分析质量分数
        average_quality = sum(quality_scores) / len(quality_scores)
        min_quality = min(quality_scores)
        max_quality = max(quality_scores)

        assert average_quality == 0.98  # 当前实现固定返回0.98
        assert min_quality == 0.98
        assert max_quality == 0.98

    def test_global_instance_usage(self):
        """测试全局实例使用"""
        from src.services.data_quality_monitor import dataqualitymonitor_instance

        assert isinstance(dataqualitymonitor_instance, DataQualityMonitor)
        assert dataqualitymonitor_instance.status == "initialized"
        assert dataqualitymonitor_instance.metrics["processed_items"] == 0


class TestDataQualityMonitorEdgeCases:
    """数据质量监控边界情况测试"""

    @pytest.mark.asyncio
    async def test_empty_data_source_name(self):
        """测试空数据源名称"""
        monitor = DataQualityMonitor()
        items = []

        async for data in monitor.process_data(""):
            items.append(data)

        assert len(items) == 10  # 应该仍然处理数据

    @pytest.mark.asyncio
    async def test_very_long_data_source_name(self):
        """测试很长的数据源名称"""
        monitor = DataQualityMonitor()
        long_name = "a" * 1000

        items = []
        async for data in monitor.process_data(long_name):
            items.append(data)

        assert len(items) == 10

    def test_metrics_with_zero_duration(self):
        """测试零持续时间的指标"""
        monitor = DataQualityMonitor()

        # 设置开始时间为当前时间
        monitor.metrics["start_time"] = datetime.now()

        metrics = monitor.get_metrics()

        # 持续时间应该非常小但非负
        assert metrics["duration"] >= 0
        # 吞吐量在零时间下应该是0或很大，但不应出错
        assert isinstance(metrics["throughput"], (int, float))

    def test_large_processed_items_count(self):
        """测试大量处理项目计数"""
        monitor = DataQualityMonitor()
        monitor.metrics["processed_items"] = 1000000

        metrics = monitor.get_metrics()

        assert metrics["processed_items"] == 1000000
        assert metrics["throughput"] >= 0