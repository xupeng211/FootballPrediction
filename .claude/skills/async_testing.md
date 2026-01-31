# pytest-asyncio 最佳实践指南

## 概述
本文档记录了 Football Prediction System 中 pytest-asyncio 的标准化使用方法。

## 核心原则

### 1. Event Loop 管理
```python
# ✅ 正确方式：使用 pytest fixture 提供的 event_loop
@pytest.fixture(scope="function")
def event_loop():
    """创建事件循环用于异步测试"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# ❌ 错误方式：手动创建和管理事件循环
def test_manual_loop():
    loop = asyncio.new_event_loop()  # 不要这样做
```

### 2. 异步 Fixture 生命周期
```python
# ✅ 正确方式：异步 fixture 使用 @pytest.mark.asyncio
@pytest.fixture
async def async_service():
    """异步服务fixture"""
    service = InferenceService()
    await service.initialize()
    yield service
    await service.cleanup()

# ✅ 测试中使用
async def test_service_operation(async_service):
    result = await async_service.predict("Team A", "Team B")
    assert result.success
```

### 3. Mock 异步对象
```python
# ✅ 正确方式：使用 AsyncMock
from unittest.mock import AsyncMock

@pytest.fixture
def mock_async_service():
    """Mock异步服务"""
    service = AsyncMock()
    service.predict = AsyncMock(return_value=Mock(success=True))
    return service

# ✅ 测试中验证异步调用
async def test_with_mock_async(mock_async_service):
    result = await mock_async_service.predict("Team A", "Team B")
    assert result.success
    mock_async_service.predict.assert_called_once_with("Team A", "Team B")
```

### 4. 依赖注入中的异步处理
```python
# ✅ 正确方式：Mock异步依赖注入
@pytest.fixture
def mock_di_container():
    """Mock依赖注入容器"""
    container = AsyncMock()

    # Mock异步resolve方法
    async def mock_resolve(service_name):
        if service_name == "model_service":
            return AsyncMock()
        return Mock()

    container.resolve = AsyncMock(side_effect=mock_resolve)
    return container

@patch("src.services.dependency_injection.ServiceContainer")
def test_inference_service_async(mock_container_class, mock_di_container):
    """测试推理服务的异步初始化"""
    mock_container_class.return_value = mock_di_container

    service = InferenceService()
    # 注意：初始化已经是同步的，依赖注入异步化在初始化内部
    assert service.name == "InferenceService"
```

### 5. 缓存和清理处理
```python
# ✅ 正确方式：处理异步清理
@pytest.fixture
async def prediction_cache():
    """预测缓存fixture"""
    cache = PredictionCache(max_size=100)
    # 设置测试数据
    await cache.set("test_key", {"result": "test"})
    yield cache
    # 自动清理（不需要手动清理，fixture会自动处理）

# ❌ 错误方式：遗留的未等待协程
def test_leaving_coroutine():
    cache = PredictionCache()
    cache._cleanup_loop()  # 这会创建未等待的协程

# ✅ 正确方式：确保协程被正确处理
@pytest.fixture
async def clean_cache():
    """干净的缓存fixture"""
    cache = PredictionCache()
    # 如果需要调用清理，确保等待
    await cache.clear_all()
    yield cache
```

### 6. 测试隔离和并发
```python
# ✅ 正确方式：使用 fixture 确保测试隔离
@pytest.fixture
async def isolated_service():
    """隔离的异步服务"""
    # 每个测试都获得全新的服务实例
    service = InferenceService()
    await service.initialize()
    try:
        yield service
    finally:
        await service.shutdown()

# ❌ 错误方式：共享状态导致测试污染
service = None  # 全局变量，会导致测试间污染
```

## 常见问题和解决方案

### 1. RuntimeWarning: coroutine was never awaited
```python
# 问题：创建但未等待协程
def test_problematic():
    cache = PredictionCache()
    # cache.cleanup_loop() 创建了协程但不等待

# 解决方案1：使用同步版本的方法
def test_fixed():
    cache = PredictionCache()
    cache.clear_all()  # 使用同步方法

# 解决方案2：正确处理异步方法
async def test_fixed_async():
    cache = PredictionCache()
    await cache.async_clear()  # 等待异步方法
```

### 2. 事件循环不一致
```python
# 问题：在测试中混用不同的事件循环
def test_loop_mismatch():
    loop1 = asyncio.new_event_loop()
    loop2 = asyncio.new_event_loop()
    # 不要这样做

# 解决方案：使用 pytest 提供的 event_loop fixture
async def test_consistent_loop(event_loop):
    # 所有异步操作都在同一个事件循环中
    service = InferenceService()
    await service.initialize()
```

### 3. Mock 异步方法返回同步对象
```python
# 问题：Mock异步方法但返回同步对象
@pytest.fixture
def problematic_mock():
    service = Mock()
    service.predict = Mock(return_value=Mock(success=True))  # 错误

# 解决方案：使用 AsyncMock
@pytest.fixture
def correct_mock():
    service = AsyncMock()
    service.predict = AsyncMock(return_value=Mock(success=True))  # 正确
```

## 测试模板

### 基础异步测试模板
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_async_service_workflow():
    """异步服务工作流测试模板"""
    # 1. 准备Mock
    mock_dependency = AsyncMock()
    mock_dependency.async_operation.return_value = {"result": "success"}

    # 2. 创建服务
    service = SomeAsyncService(dependency=mock_dependency)

    # 3. 执行异步操作
    result = await service.perform_async_operation()

    # 4. 验证结果
    assert result["result"] == "success"
    mock_dependency.async_operation.assert_called_once()
```

### 依赖注入测试模板
```python
@pytest.fixture
def mock_di_container():
    """标准化Mock依赖注入容器"""
    container = AsyncMock()

    # 标准化Mock服务
    mock_services = {
        "model_service": AsyncMock(),
        "database_service": AsyncMock(),
        "cache_service": AsyncMock(),
    }

    async def resolve_service(name):
        return mock_services.get(name, AsyncMock())

    container.resolve = AsyncMock(side_effect=resolve_service)
    return container, mock_services

@patch("src.services.dependency_injection.ServiceContainer")
def test_service_with_di(mock_container_class, mock_di_container):
    """依赖注入测试模板"""
    container, services = mock_di_container
    mock_container_class.return_value = container

    service = SomeService()
    # 验证服务正确初始化
    assert service.is_initialized
```

## 性能考虑

### 1. 异步测试性能
```python
# ✅ 批量异步操作
async def test_bulk_operations():
    service = AsyncService()

    # 并行执行而不是串行
    tasks = [service.process_item(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 10

# ❌ 避免串行异步操作
async def test_sequential_operations():
    service = AsyncService()
    results = []
    for i in range(10):
        result = await service.process_item(i)  # 串行执行，较慢
        results.append(result)
```

### 2. 资源清理
```python
# ✅ 使用异步上下文管理器
class AsyncServiceManager:
    async def __aenter__(self):
        self.service = await create_service()
        return self.service

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.service.cleanup()

@pytest.mark.asyncio
async def test_context_manager():
    async with AsyncServiceManager() as service:
        result = await service.do_work()
        assert result.success
    # 自动清理
```

## 总结

1. **始终使用 AsyncMock** 来Mock异步方法
2. **依赖pytest的event_loop fixture** 而不是手动管理
3. **确保所有协程都被正确等待**
4. **使用异步fixture进行资源管理**
5. **避免测试间的状态共享**

遵循这些最佳实践将确保异步测试的稳定性和可维护性。