# 📦 测试 Fixtures 与数据工厂

本文档说明如何使用新的测试辅助工具和 Mock 架构。

## 🎯 新的测试工具体系

### 1. 统一 Mock 工具 (`tests/helpers/`)

新的测试体系使用 `tests/helpers/` 目录下的统一 Mock 工具：

```python
# 导入所有 Mock 工具
from tests.helpers import (
    # 数据库工具
    create_sqlite_memory_engine,
    create_sqlite_sessionmaker,

    # Redis Mock
    MockRedis,
    MockAsyncRedis,
    apply_redis_mocks,

    # MLflow Mock
    MockMlflow,
    MockMlflowClient,
    MockMlflowRun,
    apply_mlflow_mocks,

    # Kafka Mock
    MockKafkaProducer,
    MockKafkaConsumer,
    MockKafkaMessage,
    apply_kafka_mocks,

    # HTTP Mock
    MockHTTPResponse,
    apply_http_mocks,
)
```

### 2. 全局 Mock fixture

所有 Mock 自动应用，无需手动配置：

```python
# 在 conftest.py 中已自动配置
@pytest.fixture(scope="session", autouse=True)
def mock_external_services():
    """自动 Mock 所有外部服务"""
    # 自动应用所有 Mock
```

## 📝 使用示例

### 单元测试示例

```python
import pytest
from tests.helpers import MockRedis, create_sqlite_sessionmaker

class TestPredictionService:
    @pytest.fixture
    async def db_session(self):
        """内存数据库会话"""
        engine = create_sqlite_memory_engine()
        sessionmaker = create_sqlite_sessionmaker(engine)
        async with sessionmaker() as session:
            yield session
        engine.dispose()

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis 客户端"""
        return MockRedis()

    @pytest.fixture
    def service(self, db_session, mock_redis):
        """创建服务实例"""
        from src.services.prediction_service import PredictionService
        return PredictionService(db=db_session, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_create_prediction(self, service, sample_prediction_data):
        """测试创建预测"""
        # Mock 返回值
        service.redis.get.return_value = None
        service.redis.set.return_value = True

        # 执行测试
        result = await service.create_prediction(sample_prediction_data)

        # 验证
        assert result is not None
        service.redis.set.assert_called_once()
```

### 测试数据工厂

虽然没有使用 factory-boy，但可以创建简单的数据工厂：

```python
# 在 tests/factories/ 目录
@pytest.fixture
def sample_match_data():
    """示例比赛数据"""
    return {
        "home_team": "Team A",
        "away_team": "Team B",
        "match_date": datetime.now(),
        "league_id": 1
    }

@pytest.fixture
def sample_prediction_data():
    """示例预测数据"""
    return {
        "match_id": 12345,
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75
    }
```

## 🔧 高级用法

### 1. 自定义 Mock 行为

```python
@pytest.fixture
def custom_mock_redis():
    """自定义 Mock Redis"""
    redis_mock = MockRedis()

    # 设置预设数据
    redis_mock.set("cached_value", "test_value")

    # 自定义方法行为
    def custom_get(key):
        if key == "special_key":
            return b"special_value"
        return redis_mock.data.get(key)

    redis_mock.get = custom_get
    return redis_mock
```

### 2. 条件 Mock

```python
@pytest.fixture
def conditional_service(mock_db_session):
    """条件 Mock 服务"""
    from src.services.prediction_service import PredictionService

    service = PredictionService(db=mock_db_session, redis=MockRedis())

    # 根据条件返回不同结果
    def mock_predict(match_id):
        if match_id % 2 == 0:
            return {"home_score": 2, "away_score": 1}
        else
            return {"home_score": 1, "away_score": 1}

    service.predict = mock_predict
    return service
```

### 3. 异步测试

```python
@pytest.mark.asyncio
async def test_async_operation(async_client):
    """异步测试示例"""
    # 发送异步请求
    response = await async_client.post("/api/predictions", json={
        "match_id": 123,
        "home_score": 2,
        "away_score": 1
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
```

## 📊 测试数据管理

### 数据隔离

每个测试自动隔离：
- 使用独立的内存数据库
- Mock 服务状态在测试间自动重置
- 不会相互影响

### 数据清理

```python
@pytest.fixture(autouse=True)
def cleanup_after_test(db_session):
    """测试后自动清理"""
    yield

    # 清理所有测试数据
    db_session.execute(text("DELETE FROM test_table"))
    db_session.commit()
```

## 🚀 性能优化

### 1. 使用 Session scope

```python
@pytest.fixture(scope="session")
def shared_service():
    """ session 级别的 fixture，所有测试共享"""
    # 初始化一次，所有测试使用
    service = HeavyInitService()
    yield service
    service.cleanup()
```

### 2. 并行测试

```bash
# 使用 pytest-xdist 并行运行
pytest tests/unit -n auto
```

### 3. 跳过慢速测试

```python
@pytest.mark.slow
def test_heavy_operation(self):
    """慢速测试，默认跳过"""
    # 耗时操作
    pass

# 运行时包含慢速测试
pytest -m "not slow"  # 跳过慢速
pytest -m slow         # 只运行慢速
```

## 🎨 最佳实践

### 1. 命名规范
- fixture: `sample_*_data`
- 测试方法: `test_*`
- 测试类: `Test*`

### 2. 测试结构
```python
def test_feature_behavior(self):
    """测试功能行为

    Given - 准备数据
    When - 执行操作
    Then - 验证结果
    """
    # Given
    data = prepare_test_data()

    # When
    result = perform_operation(data)

    # Then
    assert result.success
    assert result.value == expected
```

### 3. 使用描述性的断言
```python
# 好的断言
assert prediction.confidence > 0.5, "置信度应该大于 0.5"
assert user.email.endswith("@example.com"), "邮箱格式不正确"

# 使用 pytest.raises 测试异常
with pytest.raises(ValueError, match="无效的比赛ID"):
    service.get_prediction(-1)
```

## 🔍 调试技巧

### 1. 查看生成的内容
```python
def test_something(test_data):
    # 打印数据用于调试
    print(f"Test data: {test_data}")
    # 或者使用 -s 参数运行 pytest
```

### 2. 使用断点
```python
def test_complex_logic():
    # 添加断点
    import pdb; pdb.set_trace()
    # 或使用 ipdb（更好用）
    import ipdb; ipdb.set_trace()
```

### 3. 查看错误详情
```bash
# 显示完整错误堆栈
pytest --tb=long

# 只显示失败的测试
pytest --tb=short -x
```

## 📚 相关文档

- [完整测试指南](./TEST_GUIDE.md)
- [测试示例](./examples.md)
- [CI 配置](./ci_config.md)
- [性能测试](./performance_tests.md)

---

*更新日期：2025-01-04*