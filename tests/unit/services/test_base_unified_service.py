"""
统一基础服务测试
Base Unified Service Tests

测试BaseService基类的功能。
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

# 添加src到路径
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from src.services.base_unified import BaseService
from src.core.exceptions import FootballPredictionError as ServiceError, ValidationError


# 创建一个简单的测试服务实现
class TestService(BaseService):
    """用于测试的简单服务实现"""

    async def _get_service_info(self):
        """获取服务信息"""
        return {
            "name": self.name,
            "type": "TestService",
            "description": "Test service implementation",
        }


@pytest.mark.unit
@pytest.mark.fast
class TestBaseService:
    """测试BaseService基类"""

    def test_base_service_initialization(self):
        """测试基础服务初始化"""
        service = TestService("test_service")

        assert service.name == "test_service"
        assert service.logger is not None
        assert service._initialized is False

    def test_base_service_with_dependencies(self):
        """测试带依赖的基础服务初始化"""
        mock_db = Mock()
        mock_cache = Mock()

        service = TestService("test_service", database=mock_db, cache=mock_cache)

        assert service.database == mock_db
        assert service.cache == mock_cache

    @pytest.mark.asyncio
    async def test_initialize_service(self):
        """测试服务初始化"""
        service = TestService("test_service")

        result = await service.initialize()

        assert result is True
        assert service._health_status == "healthy"

    @pytest.mark.asyncio
    async def test_initialize_with_error(self):
        """测试初始化时出错"""
        service = TestService("test_service")

        # 模拟初始化错误
        with patch.object(
            service, "_validate_configuration", side_effect=Exception("Init error")
        ):
            with pytest.raises(ServiceError):
                await service.initialize()

    @pytest.mark.asyncio
    async def test_cleanup_service(self):
        """测试服务清理"""
        service = TestService("test_service")

        result = await service.cleanup()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        service = TestService("test_service")

        health = await service.health_check()

        assert "status" in health
        assert "name" in health
        assert "timestamp" in health
        assert health["name"] == "test_service"

    def test_get_status(self):
        """测试获取服务状态"""
        service = TestService("test_service")

        status = service.get_status()

        assert isinstance(status, str)
        assert status in ["initialized", "running", "stopped", "error"]

    def test_log_operation_start(self):
        """测试操作开始日志"""
        service = TestService("test_service")

        with patch.object(service.logger, "info") as mock_log:
            service._log_operation_start("test_operation", {"param": "value"})

            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert "test_operation" in call_args
            assert "param" in call_args

    def test_log_operation_success(self):
        """测试操作成功日志"""
        service = TestService("test_service")

        with patch.object(service.logger, "info") as mock_log:
            service._log_operation_success("test_operation", 0.5)

            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert "test_operation" in call_args
            assert "0.5" in call_args

    def test_log_operation_error(self):
        """测试操作错误日志"""
        service = TestService("test_service")

        error = ValueError("Test error")

        with patch.object(service.logger, "error") as mock_log:
            service._log_operation_error("test_operation", error, 0.3)

            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert "test_operation" in call_args
            assert "Test error" in call_args

    def test_validate_configuration(self):
        """测试配置验证"""
        service = TestService("test_service")

        # 基础服务应该总是通过配置验证
        result = service._validate_configuration()

        assert result is True

    def test_measure_performance(self):
        """测试性能测量装饰器"""
        service = TestService("test_service")

        @service.measure_performance
        def test_function():
            return "test_result"

        with patch.object(service.logger, "info") as mock_log:
            result = test_function()

            assert result == "test_result"
            mock_log.assert_called()
            call_args = mock_log.call_args[0][0]
            assert "test_function" in call_args
            assert "seconds" in call_args

    def test_circuit_breaker_pattern(self):
        """测试熔断器模式"""
        service = TestService("test_service")

        # 模拟一个会失败的操作
        failing_call_count = 0

        def failing_operation():
            nonlocal failing_call_count
            failing_call_count += 1
            if failing_call_count <= 3:
                raise Exception("Service unavailable")
            return "success"

        # 前三次调用应该失败
        for _ in range(3):
            with pytest.raises(ServiceError):
                service.execute(failing_operation, operation_name="failing_op")

        # 第四次调用应该成功（如果实现了熔断器恢复）
        result = service.execute(failing_operation, operation_name="failing_op")
        assert result == "success"

    def test_retry_mechanism(self):
        """测试重试机制"""
        service = TestService("test_service")

        call_count = 0

        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = service.execute_with_retry(
            flaky_operation, max_attempts=3, operation_name="flaky_op"
        )

        assert result == "success"
        assert call_count == 3

    def test_cache_operations(self):
        """测试缓存操作"""
        mock_cache = Mock()
        service = TestService("test_service", cache=mock_cache)

        # 测试设置缓存
        service.set_cache("test_key", {"data": "value"}, ttl=300)
        mock_cache.set.assert_called_once()

        # 测试获取缓存
        mock_cache.get.return_value = {"data": "value"}
        result = service.get_cache("test_key")
        assert result == {"data": "value"}
        mock_cache.get.assert_called_once()

        # 测试删除缓存
        service.delete_cache("test_key")
        mock_cache.delete.assert_called_once()

    def test_database_operations(self):
        """测试数据库操作"""
        mock_db = Mock()
        service = TestService("test_service", database=mock_db)

        # 测试执行查询
        mock_db.execute.return_value = [{"id": 1, "name": "test"}]
        result = service.execute_query("SELECT * FROM test")

        assert result == [{"id": 1, "name": "test"}]
        mock_db.execute.assert_called_once_with("SELECT * FROM test")

    def test_metrics_collection(self):
        """测试指标收集"""
        service = TestService("test_service")

        # 记录指标
        service.record_metric("test_counter", 1, tags={"type": "test"})
        service.record_metric("test_gauge", 0.5, metric_type="gauge")
        service.record_metric("test_histogram", 0.1, metric_type="histogram")

        # 验证指标被记录（这里需要实际的指标收集系统）
        metrics = service.get_metrics()
        assert isinstance(metrics, dict)

    def test_dependency_injection(self):
        """测试依赖注入"""
        mock_dep1 = Mock()
        mock_dep2 = Mock()

        service = TestService(
            "test_service", dependency1=mock_dep1, dependency2=mock_dep2
        )

        assert service.dependency1 == mock_dep1
        assert service.dependency2 == mock_dep2

    @pytest.mark.asyncio
    async def test_async_execute(self):
        """测试异步执行"""
        service = TestService("test_service")

        async def async_operation():
            await asyncio.sleep(0.01)
            return "async_result"

        result = await service.async_execute(async_operation, operation_name="async_op")

        assert result == "async_result"

    def test_context_manager(self):
        """测试上下文管理器"""
        service = TestService("test_service")

        with service as s:
            assert s == service
            assert s._health_status == "healthy"

        # 退出上下文后应该清理资源
        assert service._health_status == "cleaned"

    def test_service_discovery(self):
        """测试服务发现"""
        service = TestService("test_service")

        # 注册服务
        service.register_service("test_service", "http://localhost:8000")

        # 发现服务
        endpoint = service.discover_service("test_service")
        assert endpoint == "http://localhost:8000"

    def test_configuration_management(self):
        """测试配置管理"""
        config = {
            "database_url": "sqlite:///:memory:",
            "cache_ttl": 300,
            "max_connections": 10,
        }

        service = TestService("test_service", config=config)

        assert service.get_config("database_url") == "sqlite:///:memory:"
        assert service.get_config("cache_ttl") == 300
        assert service.get_config("max_connections") == 10
        assert service.get_config("nonexistent", "default") == "default"

    def test_error_handling(self):
        """测试错误处理"""
        service = TestService("test_service")

        # 测试处理不同类型的异常
        exceptions = [
            ValueError("Validation error"),
            KeyError("Missing key"),
            TypeError("Type error"),
            RuntimeError("Runtime error"),
        ]

        for exc in exceptions:
            with pytest.raises(ServiceError):
                service.execute(lambda: exc, operation_name="test_error")

    def test_service_metrics(self):
        """测试服务指标"""
        service = TestService("test_service")

        # 执行一些操作来生成指标
        service.execute(lambda: "test1", operation_name="op1")
        service.execute(lambda: "test2", operation_name="op2")

        # 获取指标
        metrics = service.get_service_metrics()

        assert "operations_total" in metrics
        assert "operations_success" in metrics
        assert "operations_failed" in metrics
        assert "average_response_time" in metrics


@pytest.mark.unit
@pytest.mark.fast
class TestBaseServiceIntegration:
    """测试BaseService集成场景"""

    def test_service_with_database_and_cache(self):
        """测试带数据库和缓存的服务"""
        mock_db = Mock()
        mock_cache = Mock()

        # 设置缓存未命中
        mock_cache.get.return_value = None
        # 设置数据库查询结果
        mock_db.execute.return_value = [{"id": 1, "name": "test"}]

        service = TestService("test_service", database=mock_db, cache=mock_cache)

        # 第一次调用应该查询数据库
        result = service.get_with_cache_or_db(
            "test_key", "SELECT * FROM test WHERE id = %s", 1
        )

        assert result == [{"id": 1, "name": "test"}]
        mock_cache.get.assert_called_once_with("test_key")
        mock_db.execute.assert_called_once()
        mock_cache.set.assert_called_once()

    def test_service_pipeline(self):
        """测试服务管道"""
        service = TestService("pipeline_service")

        def step1(data):
            return data * 2

        def step2(data):
            return data + 10

        def step3(data):
            return data**2

        # 创建管道
        pipeline = service.create_pipeline([step1, step2, step3])

        # 执行管道
        result = pipeline(5)

        # (5 * 2 + 10) ** 2 = 400
        assert result == 400

    def test_service_batch_operations(self):
        """测试批量操作"""
        service = TestService("batch_service")

        items = [1, 2, 3, 4, 5]

        def process_item(item):
            return item * 2

        # 批量处理
        results = service.execute_batch(process_item, items, batch_size=2)

        assert results == [2, 4, 6, 8, 10]

    def test_service_caching_with_ttl(self):
        """测试带TTL的缓存"""
        mock_cache = Mock()
        service = TestService("cache_service", cache=mock_cache)

        # 设置带TTL的缓存
        service.set_cache_with_ttl("test_key", "test_value", ttl=60)

        mock_cache.set.assert_called_once_with("test_key", "test_value", ex=60)
