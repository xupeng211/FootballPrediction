# DIContainer 标准化 Mock 方法

## 概述
本文档定义了 Football Prediction System 中依赖注入容器（DIContainer）的标准化 Mock 方法。

## 核心架构

### 1. DIContainer 结构
```python
class ServiceContainer:
    """服务容器"""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}

    async def resolve(self, service_name: str) -> Any:
        """解析服务"""
        # 1. 检查单例
        # 2. 检查已注册服务
        # 3. 检查工厂方法
        # 4. 抛出异常

    def register_singleton(self, name: str, instance: Any) -> None:
        """注册单例"""

    def register_factory(self, name: str, factory: Callable) -> None:
        """注册工厂方法"""
```

## 标准化 Mock 模式

### 1. 基础 Mock 容器
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

@pytest.fixture
def mock_di_container():
    """标准化Mock依赖注入容器"""
    container = AsyncMock()

    # 创建标准化的Mock服务
    mock_services = {
        # 核心服务
        "model_service": create_mock_model_service(),
        "cache_service": create_mock_cache_service(),
        "database_service": create_mock_database_service(),

        # 业务服务
        "inference_service": create_mock_inference_service(),
        "collection_service": create_mock_collection_service(),
        "feature_extractor": create_mock_feature_extractor(),

        # 外部服务
        "fotmob_client": create_mock_fotmob_client(),
        "notification_service": create_mock_notification_service(),
    }

    # 设置resolve方法
    async def mock_resolve(service_name: str) -> Any:
        if service_name in mock_services:
            return mock_services[service_name]

        # 对于未Mock的服务，返回通用AsyncMock
        default_mock = AsyncMock()
        default_mock.configure_mock(**{
            'name': service_name,
            'initialize.return_value': None,
            'cleanup.return_value': None,
        })
        mock_services[service_name] = default_mock
        return default_mock

    container.resolve = AsyncMock(side_effect=mock_resolve)
    container.register_singleton = MagicMock()
    container.register_factory = MagicMock()

    return container, mock_services
```

### 2. 标准化服务 Mock 工厂
```python
def create_mock_model_service() -> AsyncMock:
    """创建Mock模型服务"""
    model_service = AsyncMock()

    # 配置返回值
    model_service.configure_mock(**{
        'name': 'model_service',
        'is_loaded.return_value': True,
        'model_info.return_value': {
            'name': 'xgboost_v2',
            'version': '2.0.0',
            'features': 12,
            'accuracy': 0.67
        }
    })

    # 配置异步方法
    model_service.load_model = AsyncMock(return_value=True)
    model_service.predict = AsyncMock(return_value={
        'prediction': 'HOME_WIN',
        'probabilities': [0.65, 0.25, 0.10],
        'confidence': 0.75
    })

    return model_service

def create_mock_cache_service() -> AsyncMock:
    """创建Mock缓存服务"""
    cache_service = AsyncMock()

    cache_service.configure_mock(**{
        'name': 'cache_service',
        'stats.return_value': {
            'hit_rate': 0.85,
            'total_requests': 1000,
            'cache_size': 150
        }
    })

    cache_service.get = AsyncMock(return_value=None)  # 默认缓存未命中
    cache_service.set = AsyncMock(return_value=True)
    cache_service.delete = AsyncMock(return_value=True)
    cache_service.clear_all = AsyncMock(return_value=True)

    return cache_service

def create_mock_database_service() -> AsyncMock:
    """创建Mock数据库服务"""
    db_service = AsyncMock()

    db_service.configure_mock(**{
        'name': 'database_service',
        'is_connected.return_value': True,
        'connection_pool_size.return_value': 10
    })

    # Mock查询方法
    db_service.fetch_one = AsyncMock(return_value={
        'id': 1,
        'home_team': 'Man Utd',
        'away_team': 'Arsenal'
    })

    db_service.fetch_many = AsyncMock(return_value=[
        {'id': 1, 'home_team': 'Man Utd', 'away_team': 'Arsenal'},
        {'id': 2, 'home_team': 'Chelsea', 'away_team': 'Liverpool'}
    ])

    db_service.execute_query = AsyncMock(return_value={'affected_rows': 1})

    return db_service

def create_mock_inference_service() -> AsyncMock:
    """创建Mock推理服务"""
    inference_service = AsyncMock()

    inference_service.configure_mock(**{
        'name': 'inference_service',
        'is_initialized.return_value': True,
        'stats.return_value': {
            'total_predictions': 500,
            'accuracy': 0.67,
            'avg_response_time': 0.05
        }
    })

    inference_service.predict_match = AsyncMock(return_value={
        'success': True,
        'prediction': 'HOME_WIN',
        'probabilities': {
            'HOME': 0.65,
            'DRAW': 0.25,
            'AWAY': 0.10
        },
        'confidence': 0.75,
        'model_version': 'xgboost_v2',
        'timestamp': '2024-01-15T10:00:00Z'
    })

    inference_service.batch_predict = AsyncMock(return_value={
        'success': True,
        'results': [
            {'match_id': '1', 'prediction': 'HOME_WIN'},
            {'match_id': '2', 'prediction': 'DRAW'}
        ]
    })

    return inference_service

def create_mock_feature_extractor() -> AsyncMock:
    """创建Mock特征提取器"""
    feature_extractor = AsyncMock()

    feature_extractor.configure_mock(**{
        'name': 'feature_extractor',
        'feature_count.return_value': 12,
        'feature_names.return_value': [
            'home_form', 'away_form', 'h2h_home_wins',
            'h2h_draws', 'h2h_away_wins', 'home_goals_scored',
            'away_goals_scored', 'venue_advantage', 'league_strength',
            'team_strength_diff', 'recent_performance', 'head_to_head'
        ]
    })

    feature_extractor.extract_features = AsyncMock(return_value={
        'features': [0.65, 0.45, 0.8, 0.3, 0.2, 1.2, 0.8, 1.0, 0.75, 0.15, 0.7, 0.6],
        'feature_metadata': {
            'match_id': 'test_match_001',
            'extraction_time': '2024-01-15T10:00:00Z',
            'source': 'enhanced_fotmob'
        }
    })

    return feature_extractor
```

## 测试应用模式

### 1. 单个服务测试
```python
@patch("src.services.dependency_injection.ServiceContainer")
def test_inference_service_initialization(mock_container_class, mock_di_container):
    """测试推理服务初始化"""
    container, services = mock_di_container
    mock_container_class.return_value = container

    # 创建服务
    service = InferenceService()

    # 验证初始化调用
    container.resolve.assert_any_call("model_service")
    container.resolve.assert_any_call("cache_service")

    # 验证服务属性
    assert hasattr(service, 'model_service')
    assert hasattr(service, 'cache_service')
```

### 2. 复杂业务逻辑测试
```python
@patch("src.services.dependency_injection.ServiceContainer")
@pytest.mark.asyncio
async def test_prediction_workflow(mock_container_class, mock_di_container):
    """测试预测工作流"""
    container, services = mock_di_container
    mock_container_class.return_value = container

    # 配置Mock行为
    services["feature_extractor"].extract_features.return_value = {
        'features': [0.65, 0.45, 0.8, 0.3, 0.2, 1.2, 0.8],
        'feature_metadata': {'match_id': 'test_001'}
    }

    services["model_service"].predict.return_value = {
        'prediction': 'HOME_WIN',
        'probabilities': [0.65, 0.25, 0.10]
    }

    # 执行测试
    inference_service = InferenceService()
    result = await inference_service.predict_match("Man Utd", "Arsenal")

    # 验证工作流
    services["feature_extractor"].extract_features.assert_called_once()
    services["model_service"].predict.assert_called_once()
    services["cache_service"].set.assert_called_once()

    # 验证结果
    assert result['success'] is True
    assert result['prediction'] == 'HOME_WIN'
```

### 3. 错误处理测试
```python
@patch("src.services.dependency_injection.ServiceContainer")
@pytest.mark.asyncio
async def test_service_error_handling(mock_container_class, mock_di_container):
    """测试服务错误处理"""
    container, services = mock_di_container
    mock_container_class.return_value = container

    # 配置Mock抛出异常
    services["model_service"].predict.side_effect = PredictionError("Model not loaded")

    # 创建服务并测试错误处理
    service = InferenceService()

    with pytest.raises(PredictionError):
        await service.predict_match("Team A", "Team B")

    # 验证错误处理逻辑
    assert service.error_count == 1
```

## 高级 Mock 模式

### 1. 动态 Mock 行为
```python
@pytest.fixture
def dynamic_mock_container():
    """动态Mock容器，根据调用参数返回不同结果"""
    container = AsyncMock()

    async def dynamic_resolve(service_name: str, **kwargs):
        if service_name == "model_service":
            mock_service = AsyncMock()
            # 根据模型类型返回不同Mock
            if 'model_type' in kwargs and kwargs['model_type'] == 'xgboost':
                mock_service.predict.return_value = {'prediction': 'HOME_WIN'}
            else:
                mock_service.predict.return_value = {'prediction': 'DRAW'}
            return mock_service

        return AsyncMock()

    container.resolve = AsyncMock(side_effect=dynamic_resolve)
    return container

# 测试中使用
async def test_model_selection(dynamic_mock_container):
    """测试不同模型选择"""
    service = ModelSelectionService()

    # 测试XGBoost模型
    model_service = await dynamic_mock_container.resolve("model_service", model_type="xgboost")
    result = await model_service.predict()
    assert result['prediction'] == 'HOME_WIN'
```

### 2. 状态跟踪 Mock
```python
@pytest.fixture
def tracked_mock_container():
    """带有状态跟踪的Mock容器"""
    container = AsyncMock()
    call_history = []

    async def tracked_resolve(service_name: str):
        call_history.append({
            'service': service_name,
            'timestamp': datetime.now(),
            'call_id': len(call_history)
        })

        return AsyncMock(name=service_name)

    container.resolve = AsyncMock(side_effect=tracked_resolve)
    container.get_call_history = lambda: call_history.copy()

    return container

# 测试中使用
def test_service_dependency_order(tracked_mock_container):
    """测试服务依赖顺序"""
    service1 = SomeService()
    service2 = AnotherService()

    history = tracked_mock_container.get_call_history()

    # 验证服务解析顺序
    assert len(history) >= 2
    assert history[0]['service'] == 'model_service'  # 第一个解析的应该是模型服务
```

### 3. 性能测试 Mock
```python
@pytest.fixture
def performance_mock_container():
    """性能测试专用Mock容器"""
    import time

    container = AsyncMock()

    async def performance_resolve(service_name: str):
        # 模拟不同服务的解析时间
        delays = {
            'model_service': 0.1,  # 模型加载较慢
            'cache_service': 0.01,  # 缓存服务很快
            'database_service': 0.05,  # 数据库中等
        }

        delay = delays.get(service_name, 0.02)
        await asyncio.sleep(delay)

        return AsyncMock(name=service_name)

    container.resolve = AsyncMock(side_effect=performance_resolve)
    return container

# 测试中使用
@pytest.mark.asyncio
async def test_service_initialization_performance(performance_mock_container):
    """测试服务初始化性能"""
    start_time = time.time()

    service = ComplexService()
    await service.initialize()

    end_time = time.time()
    initialization_time = end_time - start_time

    # 验证初始化时间在预期范围内
    assert initialization_time < 0.5  # 应该在500ms内完成
```

## 最佳实践

### 1. 命名约定
```python
# ✅ 良好的命名
mock_di_container          # Mock依赖注入容器
mock_model_service          # Mock模型服务
mock_cache_service         # Mock缓存服务

# ❌ 不良的命名
container_mock             # 顺序错误
service_model_mock          # 描述不清晰
```

### 2. Mock 配置原则
```python
# ✅ 原则1：所有Mock都应该是可预测的
mock_service.predict.return_value = {"prediction": "HOME_WIN"}

# ✅ 原则2：Mock应该包含真实的业务逻辑
mock_service.is_healthy.return_value = True
mock_service.get_stats.return_value = {
    'total_requests': 100,
    'error_rate': 0.02,
    'avg_response_time': 0.05
}

# ✅ 原则3：Mock应该支持错误场景测试
mock_service.predict.side_effect = ServiceUnavailableError("Service down")
```

### 3. 测试隔离
```python
# ✅ 每个测试都获得独立的Mock
@pytest.fixture
def fresh_mock_container():
    return create_fresh_mock_container()

# ❌ 避免全局Mock状态
_global_mock_container = None  # 不要这样做
```

## 故障排查

### 1. Mock 未被调用
```python
# 问题：Mock没有被调用
assert mock_service.method.called  # 失败

# 解决：检查Mock设置是否正确
print(mock_service.method.call_args_list)
print(mock_service.method.mock_calls)

# 常见原因：
# 1. 服务使用了不同的依赖注入方式
# 2. Mock服务名称不正确
# 3. 服务初始化时机问题
```

### 2. 异步 Mock 问题
```python
# 问题：异步方法返回非协程
async def test_async_issue():
    result = await mock_service.method()  # TypeError: object is not callable

# 解决：确保使用AsyncMock
mock_service = AsyncMock()  # 而不是Mock()
mock_service.method = AsyncMock(return_value=result)
```

### 3. Mock 返回值不匹配
```python
# 问题：Mock返回值类型不匹配
expected = {"result": "success"}
actual = mock_service.method.return_value  # 实际返回的是Mock对象

# 解决：配置正确的返回值
mock_service.method.return_value = {"result": "success"}

# 或者使用side_effect
def mock_method_implementation(*args, **kwargs):
    return {"result": "success"}

mock_service.method.side_effect = mock_method_implementation
```

## 总结

标准化 Mock 依赖注入的关键原则：

1. **使用AsyncMock**处理异步方法
2. **提供真实的业务数据**作为Mock返回值
3. **保持测试隔离**，避免状态污染
4. **支持错误场景**测试
5. **使用描述性命名**提高可读性

遵循这些原则将确保Mock的可靠性和测试的可维护性。