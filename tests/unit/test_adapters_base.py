"""
适配器基类测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from src.core.exceptions import AdapterError
from src.adapters.base import BaseAdapter


class TestBaseAdapter:
    """基础适配器测试"""

    def test_adapter_is_abstract(self):
        """测试适配器是抽象基类"""
        # 验证不能直接实例化抽象类
        with pytest.raises(TypeError):
            BaseAdapter()

    def test_adapter_has_abstract_methods(self):
        """测试适配器有抽象方法"""
        # 检查抽象方法
        abstract_methods = BaseAdapter.__abstractmethods__
        assert "initialize" in abstract_methods
        assert "get_data" in abstract_methods
        assert "close" in abstract_methods

    def test_concrete_adapter_implementation(self):
        """测试具体适配器实现"""

        class ConcreteAdapter(BaseAdapter):
            """具体适配器实现"""

            async def initialize(self):
                """初始化适配器"""
                self.initialized = True

            async def get_data(self, query: str, params: Optional[Dict] = None) -> Dict:
                """获取数据"""
                if not getattr(self, "initialized", False):
                    raise AdapterError("Adapter not initialized")
                return {"data": f"result for {query}", "params": params or {}}

            async def close(self):
                """关闭适配器"""
                self.initialized = False

        # 测试实例化
        adapter = ConcreteAdapter()
        assert isinstance(adapter, BaseAdapter)

        # 测试方法调用
        import asyncio

        # 初始化
        asyncio.run(adapter.initialize())
        assert adapter.initialized is True

        # 获取数据
        result = asyncio.run(adapter.get_data("test_query", {"param": "value"}))
        assert result["data"] == "result for test_query"
        assert result["params"] == {"param": "value"}

        # 未初始化错误
        adapter.initialized = False
        with pytest.raises(AdapterError, match="Adapter not initialized"):
            asyncio.run(adapter.get_data("test"))

        # 关闭
        asyncio.run(adapter.close())
        assert adapter.initialized is False

    def test_adapter_error_handling(self):
        """测试适配器错误处理"""

        class FailingAdapter(BaseAdapter):
            """总是失败的适配器"""

            async def initialize(self):
                raise AdapterError("Initialization failed")

            async def get_data(self, query: str, params: Optional[Dict] = None) -> Dict:
                raise AdapterError(f"Query failed: {query}")

            async def close(self):
                raise AdapterError("Close failed")

        adapter = FailingAdapter()
        import asyncio

        # 测试各种错误
        with pytest.raises(AdapterError, match="Initialization failed"):
            asyncio.run(adapter.initialize())

        with pytest.raises(AdapterError, match="Query failed: test"):
            asyncio.run(adapter.get_data("test"))

        with pytest.raises(AdapterError, match="Close failed"):
            asyncio.run(adapter.close())

    def test_adapter_with_configuration(self):
        """测试带配置的适配器"""

        class ConfigurableAdapter(BaseAdapter):
            """可配置的适配器"""

            def __init__(self, config: Dict[str, Any]):
                super().__init__()
                self.config = config
                self.connected = False

            async def initialize(self):
                """使用配置初始化"""
                self.connected = True

            async def get_data(self, query: str, params: Optional[Dict] = None) -> Dict:
                """获取数据"""
                return {
                    "query": query,
                    "source": self.config.get("source", "default"),
                    "timeout": self.config.get("timeout", 30),
                }

            async def close(self):
                """关闭连接"""
                self.connected = False

        # 测试配置
        config = {"source": "test_db", "timeout": 60}
        adapter = ConfigurableAdapter(config)
        assert adapter.config == config

        import asyncio

        asyncio.run(adapter.initialize())
        assert adapter.connected is True

        result = asyncio.run(adapter.get_data("SELECT * FROM test"))
        assert result["source"] == "test_db"
        assert result["timeout"] == 60

    def test_adapter_lifecycle(self):
        """测试适配器生命周期"""
        lifecycle_events = []

        class LifecycleAdapter(BaseAdapter):
            """记录生命周期事件的适配器"""

            async def initialize(self):
                lifecycle_events.append("initialized")

            async def get_data(self, query: str, params: Optional[Dict] = None) -> Dict:
                lifecycle_events.append(f"query_executed: {query}")
                return {"lifecycle": lifecycle_events.copy()}

            async def close(self):
                lifecycle_events.append("closed")

        adapter = LifecycleAdapter()
        import asyncio

        # 测试生命周期
        assert lifecycle_events == []

        asyncio.run(adapter.initialize())
        assert lifecycle_events == ["initialized"]

        asyncio.run(adapter.get_data("test"))
        assert lifecycle_events == ["initialized", "query_executed: test"]

        asyncio.run(adapter.close())
        assert lifecycle_events == ["initialized", "query_executed: test", "closed"]

    def test_adapter_context_manager(self):
        """测试适配器上下文管理器"""

        class ContextAdapter(BaseAdapter):
            """支持上下文管理器的适配器"""

            async def initialize(self):
                self.initialized = True

            async def get_data(self, query: str, params: Optional[Dict] = None) -> Dict:
                return {"context": "managed"}

            async def close(self):
                self.initialized = False

            async def __aenter__(self):
                await self.initialize()
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await self.close()

        adapter = ContextAdapter()
        import asyncio

        # 测试上下文管理器
        async def test_context():
            async with adapter as ctx:
                assert ctx.initialized is True
                result = await ctx.get_data("test")
                assert result["context"] == "managed"
            assert adapter.initialized is False

        asyncio.run(test_context())

    def test_adapter_retry_logic(self):
        """测试适配器重试逻辑"""
        retry_count = 0

        class RetryAdapter(BaseAdapter):
            """带重试逻辑的适配器"""

            async def initialize(self):
                pass

            async def get_data(self, query: str, params: Optional[Dict] = None) -> Dict:
                nonlocal retry_count
                retry_count += 1
                if retry_count < 3:
                    raise AdapterError(f"Temporary error {retry_count}")
                return {"success": True, "attempts": retry_count}

            async def close(self):
                pass

        adapter = RetryAdapter()
        import asyncio

        # 模拟重试逻辑
        result = None
        for attempt in range(3):
            try:
                result = asyncio.run(adapter.get_data("test"))
                break
            except AdapterError:
                if attempt == 2:  # 最后一次尝试
                    raise

        assert result is not None
        assert result["success"] is True
        assert result["attempts"] == 3

    def test_adapter_caching(self):
        """测试适配器缓存功能"""

        class CachingAdapter(BaseAdapter):
            """带缓存的适配器"""

            def __init__(self):
                super().__init__()
                self.cache = {}

            async def initialize(self):
                pass

            async def get_data(self, query: str, params: Optional[Dict] = None) -> Dict:
                cache_key = f"{query}:{str(params or {})}"
                if cache_key in self.cache:
                    return {"cached": True, "data": self.cache[cache_key]}

                # 模拟获取数据
                data = {"query": query, "timestamp": "2024-01-01"}
                self.cache[cache_key] = data
                return {"cached": False, "data": data}

            async def close(self):
                self.cache.clear()

        adapter = CachingAdapter()
        import asyncio

        # 第一次调用
        result1 = asyncio.run(adapter.get_data("test", {"id": 1}))
        assert result1["cached"] is False

        # 第二次调用（从缓存）
        result2 = asyncio.run(adapter.get_data("test", {"id": 1}))
        assert result2["cached"] is True
        assert result2["data"] == result1["data"]

    def test_adapter_validation(self):
        """测试适配器验证功能"""

        class ValidatingAdapter(BaseAdapter):
            """带验证的适配器"""

            async def initialize(self):
                pass

            async def get_data(self, query: str, params: Optional[Dict] = None) -> Dict:
                # 验证查询
                if not query or not isinstance(query, str):
                    raise AdapterError("Invalid query")

                # 验证参数
                if params:
                    if "id" in params and not isinstance(params["id"], int):
                        raise AdapterError("ID must be integer")

                return {"valid": True, "query": query}

            async def close(self):
                pass

        adapter = ValidatingAdapter()
        import asyncio

        # 有效查询
        result = asyncio.run(adapter.get_data("SELECT * FROM test", {"id": 123}))
        assert result["valid"] is True

        # 无效查询
        with pytest.raises(AdapterError, match="Invalid query"):
            asyncio.run(adapter.get_data(""))

        # 无效参数
        with pytest.raises(AdapterError, match="ID must be integer"):
            asyncio.run(adapter.get_data("test", {"id": "abc"}))

    def test_adapter_metrics(self):
        """测试适配器指标收集"""

        class MetricsAdapter(BaseAdapter):
            """收集指标的适配器"""

            def __init__(self):
                super().__init__()
                self.metrics = {"queries": 0, "errors": 0, "total_time": 0}

            async def initialize(self):
                pass

            async def get_data(self, query: str, params: Optional[Dict] = None) -> Dict:
                import time

                start_time = time.time()

                try:
                    # 模拟处理
                    await asyncio.sleep(0.01)
                    result = {"metrics": "collected"}

                    # 记录成功
                    self.metrics["queries"] += 1
                    self.metrics["total_time"] += time.time() - start_time

                    return result
                except Exception:
                    self.metrics["errors"] += 1
                    raise

            async def close(self):
                pass

        adapter = MetricsAdapter()
        import asyncio

        # 执行查询
        asyncio.run(adapter.get_data("test1"))
        asyncio.run(adapter.get_data("test2"))

        # 检查指标
        assert adapter.metrics["queries"] == 2
        assert adapter.metrics["errors"] == 0
        assert adapter.metrics["total_time"] > 0
