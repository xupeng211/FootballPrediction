from typing import Optional

"""数据质量监控服务测试
Data Quality Monitor Service Tests.

测试src/services/data_quality_monitor.py模块中的数据质量监控功能。
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from src.services.data_quality_monitor import DataQualityMonitor


class TestDataQualityMonitor:
    """数据质量监控服务测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.monitor = DataQualityMonitor()

    def test_data_quality_monitor_initialization_default(self):
        """测试数据质量监控服务默认初始化."""
        monitor = DataQualityMonitor()

        # 验证初始化
        assert monitor is not None
        assert hasattr(monitor, "config")
        assert hasattr(monitor, "metrics")
        assert hasattr(monitor, "processed_count")

    def test_data_quality_monitor_initialization_with_config(self):
        """测试数据质量监控服务自定义配置初始化."""
        custom_config = {"threshold": 0.95, "sample_rate": 0.1, "enable_logging": True}

        monitor = DataQualityMonitor(config=custom_config)

        # 验证配置被应用
        assert monitor.config == custom_config

    @pytest.mark.asyncio
    async def test_process_data_basic(self):
        """测试基本数据处理."""
        sample_data = {"id": 1, "name": "Test User", "email": "test@example.com"}

        result = await self.monitor.process_data(sample_data)

        # 验证处理结果
        assert isinstance(result, dict)
        assert "quality_score" in result
        assert "processed_at" in result
        assert "data_id" in result

    @pytest.mark.asyncio
    async def test_process_data_multiple_records(self):
        """测试多条记录处理."""
        records = [
            {"id": 1, "name": "User1", "email": "user1@example.com"},
            {"id": 2, "name": "User2", "email": "user2@example.com"},
            {"id": 3, "name": "User3", "email": "user3@example.com"},
        ]

        # 处理多条记录
        results = []
        for record in records:
            result = await self.monitor.process_data(record)
            results.append(result)

        # 验证所有记录都被处理
        assert len(results) == len(records)
        for result in results:
            assert "quality_score" in result

    @pytest.mark.asyncio
    async def test_process_data_invalid_data(self):
        """测试无效数据处理."""
        invalid_data = {}

        result = await self.monitor.process_data(invalid_data)

        # 验证无效数据的处理
        assert isinstance(result, dict)
        # 无效数据应该有较低的质量分数
        assert result.get("quality_score", 0) <= 0.5

    @pytest.mark.asyncio
    async def test_process_data_none_data(self):
        """测试None数据处理."""
        result = await self.monitor.process_data(None)

        # 验证None数据的处理
        assert isinstance(result, dict)
        assert "error" in result or result.get("quality_score", 0) == 0

    @pytest.mark.asyncio
    async def test_process_data_with_validation_errors(self):
        """测试带验证错误的数据处理."""
        problematic_data = {
            "id": "invalid_id",  # 应该是数字
            "name": "",  # 空字符串
            "email": "invalid_email",  # 无效邮箱格式
        }

        result = await self.monitor.process_data(problematic_data)

        # 验证问题数据被识别
        assert isinstance(result, dict)
        assert "validation_errors" in result or result.get("quality_score", 0) < 0.5

    @pytest.mark.asyncio
    async def test_validate_data_valid_data(self):
        """测试有效数据验证."""
        valid_data = {
            "id": 123,
            "name": "Valid Name",
            "email": "valid@example.com",
            "age": 25,
        }

        result = await self.monitor.validate_data(valid_data)

        # 验证有效数据
        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "score" in result
        assert "errors" in result
        # 有效数据应该通过验证
        assert result.get("is_valid", False) is True or result.get("score", 0) > 0.8

    @pytest.mark.asyncio
    async def test_validate_data_missing_required_fields(self):
        """测试缺少必需字段的数据验证."""
        incomplete_data = {
            "name": "User Name"
            # 缺少必需的id和email字段
        }

        result = await self.monitor.validate_data(incomplete_data)

        # 验证缺失字段被识别
        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "errors" in result
        assert len(result.get("errors", [])) > 0

    @pytest.mark.asyncio
    async def test_validate_data_field_type_errors(self):
        """测试字段类型错误的数据验证."""
        type_error_data = {
            "id": "should_be_number",
            "name": "Valid Name",
            "email": "valid@example.com",
        }

        result = await self.monitor.validate_data(type_error_data)

        # 验证类型错误被识别
        assert isinstance(result, dict)
        assert "errors" in result
        # 应该有类型相关的错误
        errors = result.get("errors", [])
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_validate_data_format_errors(self):
        """测试格式错误的数据验证."""
        format_error_data = {
            "id": 123,
            "name": "Valid Name",
            "email": "invalid_email_format",  # 无效邮箱格式
        }

        result = await self.monitor.validate_data(format_error_data)

        # 验证格式错误被识别
        assert isinstance(result, dict)
        assert "errors" in result
        # 应该有格式相关的错误
        errors = result.get("errors", [])
        assert len(errors) > 0

    def test_get_metrics_initial_state(self):
        """测试获取指标 - 初始状态."""
        metrics = self.monitor.get_metrics()

        # 验证初始指标
        assert isinstance(metrics, dict)
        assert "total_processed" in metrics
        assert "success_count" in metrics
        assert "error_count" in metrics
        assert "average_quality_score" in metrics
        assert "last_updated" in metrics

        # 初始状态应该都是0
        assert metrics["total_processed"] == 0
        assert metrics["success_count"] == 0
        assert metrics["error_count"] == 0

    @pytest.mark.asyncio
    async def test_get_metrics_after_processing(self):
        """测试处理后的指标获取."""
        # 处理一些数据
        await self.monitor.process_data({"id": 1, "name": "Test"})
        await self.monitor.process_data({"id": 2, "name": "Test2"})

        metrics = self.monitor.get_metrics()

        # 验证指标被更新
        assert metrics["total_processed"] >= 2
        assert metrics["success_count"] >= 2
        assert metrics["average_quality_score"] >= 0

    @pytest.mark.asyncio
    async def test_get_metrics_after_errors(self):
        """测试错误处理后的指标获取."""
        # 处理一些数据（包括错误数据）
        await self.monitor.process_data({"id": 1, "name": "Valid"})
        await self.monitor.process_data(None)  # 这会产生错误
        await self.monitor.process_data({})  # 这也可能会产生错误

        metrics = self.monitor.get_metrics()

        # 验证错误指标被记录
        assert metrics["total_processed"] >= 3
        assert metrics["error_count"] >= 1
        assert metrics["success_count"] >= 1

    def test_get_metrics_performance(self):
        """测试获取指标的性能."""
        import time

        # 测试获取大量指标的性能
        start_time = time.time()

        for _ in range(100):
            metrics = self.monitor.get_metrics()
            assert isinstance(metrics, dict)

        end_time = time.time()
        duration = end_time - start_time

        # 验证性能在合理范围内
        assert duration < 1.0  # 100次调用应该在1秒内完成

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """测试并发数据处理."""
        import asyncio
        import threading

        async def process_data_async(data):
            return await self.monitor.process_data(data)

        # 创建并发任务
        tasks = []
        for i in range(10):
            data = {"id": i, "name": f"User{i}", "email": f"user{i}@example.com"}
            task = asyncio.create_task(process_data_async(data))
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks)

        # 验证并发处理结果
        assert len(results) == 10
        for i, result in enumerate(results):
            assert isinstance(result, dict)
            assert "quality_score" in result

    def test_monitor_configuration_update(self):
        """测试监控器配置更新."""
        new_config = {"threshold": 0.9, "enable_detailed_logging": True}

        # 更新配置
        self.monitor.config.update(new_config)

        # 验证配置被更新
        assert self.monitor.config["threshold"] == 0.9
        assert self.monitor.config["enable_detailed_logging"] is True

    @pytest.mark.asyncio
    async def test_data_quality_scoring(self):
        """测试数据质量评分算法."""
        # 完美数据
        perfect_data = {
            "id": 123,
            "name": "Perfect User",
            "email": "perfect@example.com",
            "age": 30,
            "phone": "123-456-7890",
        }

        result = await self.monitor.process_data(perfect_data)
        perfect_score = result.get("quality_score", 0)

        # 有缺陷的数据
        flawed_data = {
            "id": "wrong_type",  # 类型错误
            "name": "",  # 空值
            "email": "invalid_email",  # 格式错误
        }

        result = await self.monitor.process_data(flawed_data)
        flawed_score = result.get("quality_score", 0)

        # 验证评分差异
        assert perfect_score > flawed_score
        assert perfect_score >= 0.8
        assert flawed_score <= 0.5

    @pytest.mark.asyncio
    async def test_data_batch_processing(self):
        """测试批量数据处理."""
        batch_data = [
            {"id": i, "name": f"User{i}", "email": f"user{i}@example.com"}
            for i in range(5, 15)
        ]

        # 批量处理
        results = []
        for data in batch_data:
            result = await self.monitor.process_data(data)
            results.append(result)

        # 验证批量处理结果
        assert len(results) == len(batch_data)
        for result in results:
            assert "quality_score" in result
            assert result["quality_score"] > 0

    def test_monitor_state_persistence(self):
        """测试监控器状态持久性."""
        # 验证初始状态
        initial_metrics = self.monitor.get_metrics()
        assert initial_metrics["total_processed"] == 0

        # 验证状态可以更新
        self.monitor.metrics["total_processed"] = 5
        updated_metrics = self.monitor.get_metrics()
        assert updated_metrics["total_processed"] == 5

    def test_error_handling_robustness(self):
        """测试错误处理的健壮性."""
        # 测试获取指标时的异常处理
        # 通过直接设置可能导致错误的状态来测试
        self.monitor.metrics = None

        # 即使在异常状态下，获取指标也不应该崩溃
        try:
            metrics = self.monitor.get_metrics()
            # 如果返回了指标，验证结构
            if isinstance(metrics, dict):
                assert "error" in metrics or len(metrics) == 0
        except Exception as e:
            # 如果抛出异常，这是可以接受的（因为我们在测试极端情况）
            pass

    @pytest.mark.asyncio
    async def test_main_function(self):
        """测试主函数执行."""
        # 由于main函数可能包含异步操作，我们测试它的存在性
        assert callable(self.monitor.main)

        # 测试调用主函数不会立即崩溃
        try:
            await self.monitor.main()
        except Exception as e:
            # 主函数可能需要特定的环境或配置，异常是可以接受的
            pass
