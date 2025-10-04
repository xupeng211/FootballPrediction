# 测试指南

## 概述

本项目采用pytest作为测试框架，集成了覆盖率检查、性能测试和持续集成。

## 快速开始

### 运行所有测试
```bash
make test
```

### 运行特定类型的测试
```bash
# 单元测试
make test.unit

# 集成测试
make test.int

# 端到端测试
make test.e2e

# 快速测试（跳过慢速测试）
make test-quick
```

### 生成覆盖率报告
```bash
# 生成HTML覆盖率报告
make cov.html

# 强制80%覆盖率
make cov.enforce

# 查看详细覆盖率
pytest --cov=src --cov-report=term-missing
```

## 测试结构

```
tests/
├── unit/           # 单元测试 - 测试单个函数/类
│   ├── api/        # API端点测试
│   ├── services/   # 服务层测试
│   ├── database/   # 数据库测试
│   └── utils/      # 工具函数测试
├── integration/    # 集成测试 - 测试多个组件协作
└── e2e/           # 端到端测试 - 测试完整流程
```

## 测试标记（Markers）

使用pytest标记来分类和过滤测试：

```python
@pytest.mark.unit          # 单元测试
@pytest.mark.integration   # 集成测试
@pytest.mark.e2e          # 端到端测试
@pytest.mark.slow         # 慢速测试
@pytest.mark.smoke        # 冒烟测试
@pytest.mark.asyncio      # 异步测试
```

### 运行特定标记的测试
```bash
# 只运行单元测试
pytest -m unit

# 排除慢速测试
pytest -m "not slow"

# 运行冒烟测试
pytest -m smoke
```

## 编写测试

### 单元测试示例

```python
"""测试示例模块"""

import pytest
from src.utils.string_utils import StringUtils


class TestStringUtils:
    """字符串工具测试"""

    def test_capitalize_first_letter(self):
        """测试首字母大写"""
        result = StringUtils.capitalize_first_letter("hello")
        assert result == "Hello"

    @pytest.mark.parametrize("input,expected", [
        ("test", "Test"),
        ("HELLO", "HELLO"),
        ("", ""),
    ])
    def test_capitalize_multiple_cases(self, input, expected):
        """测试多种情况"""
        assert StringUtils.capitalize_first_letter(input) == expected
```

### 异步测试示例

```python
import pytest
from src.services.example_service import ExampleService


class TestExampleService:
    """异步服务测试"""

    @pytest.mark.asyncio
    async def test_async_method(self):
        """测试异步方法"""
        service = ExampleService()
        result = await service.async_method()
        assert result is not None
```

### 使用Fixtures

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """API测试客户端"""
    from src.main import app
    return TestClient(app)


def test_health_check(api_client):
    """测试健康检查"""
    response = api_client.get("/api/health")
    assert response.status_code == 200
```

## Mock和Stub

### Mock外部依赖

```python
from unittest.mock import patch, MagicMock


def test_with_mock():
    """使用mock测试"""
    with patch('src.api.predictions.PredictionService') as mock_service:
        mock_service.create_prediction.return_value = {"id": 1}

        # 执行测试
        result = create_prediction(data)

        # 验证
        assert result["id"] == 1
        mock_service.create_prediction.assert_called_once()
```

### 使用测试辅助工具

```python
from tests.helpers import (
    MockRedis,
    create_sqlite_memory_engine,
    create_sqlite_sessionmaker,
)


@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    redis_mock = MockRedis()
    redis_mock.set("key", "value")
    return redis_mock
```

## 覆盖率目标

- **总体覆盖率**: ≥80%
- **核心API模块**: ≥90%
- **工具类**: 100%
- **CI强制**: ≥80%

### 查看未覆盖的代码

```bash
# 查看缺失覆盖的行
pytest --cov=src --cov-report=term-missing

# 生成HTML报告
pytest --cov=src --cov-report=html
# 然后打开 htmlcov/index.html
```

## 性能测试

### 使用pytest-benchmark

```python
def test_performance(benchmark):
    """性能基准测试"""
    result = benchmark(expensive_function, arg1, arg2)
    assert result == expected_value
```

### 设置性能阈值

```python
@pytest.mark.benchmark(min_rounds=10)
def test_with_threshold(benchmark):
    """带阈值的性能测试"""
    result = benchmark(function)
    assert benchmark.stats.stats.mean < 0.1  # 平均<100ms
```

## 测试数据

### 使用Faker生成测试数据

```python
from faker import Faker


@pytest.fixture
def fake_user():
    """生成假用户数据"""
    fake = Faker()
    return {
        "name": fake.name(),
        "email": fake.email(),
        "address": fake.address()
    }
```

### 使用Factory模式

```python
from tests.factories import UserFactory, MatchFactory


def test_with_factory():
    """使用factory生成测试数据"""
    user = UserFactory.create()
    match = MatchFactory.create()
    assert user.id is not None
```

## CI/CD集成

### GitHub Actions

测试在每次push和PR时自动运行：

```yaml
- name: Run tests
  run: |
    pytest tests/ --cov=src --cov-report=xml --cov-fail-under=80
```

### 本地CI模拟

```bash
# 运行完整CI流程
make ci

# 或使用ci-verify脚本
./ci-verify.sh
```

## 最佳实践

1. **测试命名**: 使用描述性名称，清楚说明测试内容
   ```python
   def test_user_registration_with_valid_email_creates_user():
       ...
   ```

2. **一个测试一个断言**: 保持测试简单和专注
   ```python
   def test_addition():
       assert add(2, 3) == 5  # 只测试一件事
   ```

3. **使用fixture复用**: 避免重复的setup代码
   ```python
   @pytest.fixture
   def database():
       db = create_db()
       yield db
       db.cleanup()
   ```

4. **独立性**: 测试之间不应相互依赖
   ```python
   # ❌ 不好
   test_order = []
   def test_1(): test_order.append(1)
   def test_2(): assert test_order == [1]

   # ✅ 好
   def test_1(): assert function_a() == expected
   def test_2(): assert function_b() == expected
   ```

5. **清晰的失败消息**: 使用自定义消息
   ```python
   assert result == expected, f"Expected {expected}, got {result}"
   ```

## 故障排查

### 测试失败

```bash
# 查看详细错误
pytest -vv

# 显示完整traceback
pytest --tb=long

# 只运行失败的测试
pytest --lf

# 调试模式
pytest -s  # 显示print输出
pytest --pdb  # 失败时进入debugger
```

### 慢速测试

```bash
# 查看最慢的10个测试
pytest --durations=10

# 设置超时
pytest --timeout=60
```

### Coverage问题

```bash
# 查看哪些文件未覆盖
pytest --cov=src --cov-report=term-missing:skip-covered

# 只测试特定模块的覆盖率
pytest --cov=src/api --cov-report=term
```

## 资源

- [Pytest官方文档](https://docs.pytest.org/)
- [pytest-cov文档](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio文档](https://pytest-asyncio.readthedocs.io/)
- [Faker文档](https://faker.readthedocs.io/)

## 获取帮助

- 查看示例测试: `tests/unit/api/test_health.py`
- 查看测试辅助工具: `tests/helpers.py`
- 运行 `make help` 查看所有make命令
