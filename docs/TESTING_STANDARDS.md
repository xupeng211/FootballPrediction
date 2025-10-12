# 测试标准文档

本文档定义了项目的测试标准和最佳实践，确保代码质量和测试覆盖率符合大厂标准。

## 目录
1. [测试原则](#测试原则)
2. [测试分类](#测试分类)
3. [测试命名规范](#测试命名规范)
4. [测试结构规范](#测试结构规范)
5. [Mock使用规范](#mock使用规范)
6. [覆盖率要求](#覆盖率要求)
7. [测试质量门禁](#测试质量门禁)
8. [常见反模式](#常见反模式)

## 测试原则

### 1. FIRST原则
- **Fast（快速）**：测试应该快速运行
- **Independent（独立）**：测试之间不应相互依赖
- **Repeatable（可重复）**：测试结果应该一致
- **Self-Validating（自我验证）**：测试应该有明确的通过/失败结果
- **Timely（及时）**：测试应该及时编写

### 2. 测试金字塔
```
    E2E Tests (5%)
      ↓
Integration Tests (15%)
      ↓
Unit Tests (80%)
```

### 3. 测试隔离原则
- 每个测试都应该独立运行
- 不依赖测试的执行顺序
- 不依赖外部系统状态

## 测试分类

### 1. 单元测试（Unit Tests）
- **目标**：验证单个函数或类的行为
- **特点**：快速、独立、无副作用
- **覆盖率要求**：业务逻辑 >= 90%，工具类 >= 95%

### 2. 集成测试（Integration Tests）
- **目标**：验证多个组件的协作
- **特点**：测试组件间的交互
- **标记**：`@pytest.mark.integration`

### 3. 端到端测试（E2E Tests）
- **目标**：验证完整的业务流程
- **特点**：最接近真实用户场景
- **标记**：`@pytest.mark.e2e`

## 测试命名规范

### 1. 文件命名
- 测试文件：`test_<module_name>.py`
- 测试类：`Test<ClassName>`
- 测试方法：`test_<scenario>_<expected_result>`

### 2. 命名示例
```python
# ✅ 好的命名
def test_user_login_with_valid_credentials_returns_token()
def test_invalid_email_format_raises_validation_error()
def test_empty_cart_total_is_zero()

# ❌ 避免的命名
def test_user_1()
def test_function()
def test_case()
```

## 测试结构规范

### 1. 测试文件模板
```python
"""
模块测试描述
Module Test Description
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.module import ClassUnderTest


class TestClassUnderTest:
    """类测试描述"""

    @pytest.fixture
    def setup_data(self):
        """提供测试数据"""
        return {
            "valid_input": {"key": "value"},
            "invalid_input": None
        }

    @pytest.fixture
    def mock_dependency(self):
        """提供Mock依赖"""
        mock = Mock(spec=DependencyClass)
        mock.method.return_value = "mocked_value"
        return mock

    def test_method_success_scenario(self, setup_data, mock_dependency):
        """测试：成功场景描述"""
        # Given - 准备测试条件
        sut = ClassUnderTest(mock_dependency)

        # When - 执行操作
        result = sut.method(setup_data["valid_input"])

        # Then - 验证结果
        assert result["status"] == "success"
        mock_dependency.method.assert_called_once()

    def test_method_error_scenario(self, setup_data, mock_dependency):
        """测试：错误场景描述"""
        # Given
        sut = ClassUnderTest(mock_dependency)
        mock_dependency.method.side_effect = ValueError("Test error")

        # When / Then
        with pytest.raises(ValueError, match="Test error"):
            sut.method(setup_data["valid_input"])
```

### 2. 异步测试模板
```python
@pytest.mark.asyncio
async def test_async_method_success(self):
    """测试：异步方法成功场景"""
    # Given
    async_service = AsyncService()

    # When
    result = await async_service.process_data()

    # Then
    assert result is not None
```

## Mock使用规范

### 1. 何时使用Mock
- 测试外部依赖（数据库、API、文件系统）
- 模拟错误场景
- 加速测试执行
- 隔离被测试单元

### 2. 何时避免使用Mock
- 测试核心业务逻辑
- 测试数据转换逻辑
- 测试简单工具函数
- Mock比实际实现更复杂时

### 3. Mock最佳实践
```python
# ✅ 好的Mock使用
def test_service_with_external_api(self):
    """测试服务调用外部API"""
    with patch('src.module.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"data": "value"}

        service = MyService()
        result = service.fetch_data()

        assert result["data"] == "value"
        mock_get.assert_called_once_with("https://api.example.com/data")

# ✅ 使用工厂方法创建Mock
@pytest.fixture
def mock_database():
    """Mock数据库连接"""
    mock = Mock()
    mock.query.return_value = [{"id": 1, "name": "test"}]
    return mock

# ❌ 避免过度Mock
def test_simple_math():
    """简单数学运算不需要Mock"""
    result = add(2, 3)
    assert result == 5
```

## 覆盖率要求

### 1. 总体覆盖率
- **最低要求**：80%
- **目标**：90%
- **优秀**：95%+

### 2. 分类覆盖率
| 模块类型 | 最低要求 | 目标 |
|---------|---------|------|
| 业务逻辑 | 90% | 95% |
| 工具类 | 95% | 100% |
| 数据模型 | 85% | 90% |
| API层 | 85% | 90% |
| 数据访问层 | 80% | 85% |

### 3. 覆盖率检查
```bash
# 本地开发
make coverage-local    # 80% 门槛
make coverage-fast     # 仅单元测试

# CI/CD
make coverage          # 90% 门槛
make coverage-ci        # 完整测试集
```

## 测试质量门禁

### 1. 代码质量
- 所有测试必须通过
- 无警告信息
- 符合代码规范（ruff、mypy）

### 2. 测试质量
- 测试描述清晰
- 断言具体明确
- 无测试重复
- 边界条件测试

### 3. CI检查
```yaml
# .github/workflows/test.yml
- name: Run Tests
  run: |
    make prepush  # 包含：lint + typecheck + test
    make coverage  # 覆盖率检查
```

## 常见反模式

### 1. 测试反模式
```python
# ❌ 测试实现细节
def test_method_uses_list_comprehension():
    # 测试不应该关心内部实现
    sut = Processor()
    result = sut.process()
    assert result == [x for x in items if x > 0]

# ✅ 测试行为契约
def test_process_filters_invalid_items():
    # 测试应该验证行为
    sut = Processor()
    result = sut.process(items=[-1, 0, 1, 2])
    assert result == [1, 2]

# ❌ 测试私有方法
def test_private_method():
    # 私有方法不应该直接测试
    sut = MyClass()
    result = sut._private_method()

# ✅ 通过公共接口测试私有逻辑
def test_public_behavior_uses_private_logic():
    sut = MyClass()
    result = sut.public_method()
    assert result.is_valid

# ❌ 脆弱的断言
def test_something():
    result = process()
    assert result is not None

# ✅ 具体的断言
def test_something_returns_expected_structure():
    result = process()
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] in ["success", "error"]
```

### 2. 测试数据反模式
```python
# ❌ 硬编码测试数据
def test_with_hardcoded_data():
    user = User(name="John", age=30, email="john@example.com")
    assert user.is_adult()

# ✅ 使用工厂或Fixture
@pytest.fixture
def sample_user():
    return User(name="John", age=30, email="john@example.com")

def test_user_is_adult(sample_user):
    assert sample_user.is_adult()
```

### 3. 异步测试反模式
```python
# ❌ 在同步测试中使用asyncio.run
def test_async_wrong():
    result = asyncio.run(async_function())
    assert result

# ✅ 使用异步测试装饰器
@pytest.mark.asyncio
async def test_async_correct():
    result = await async_function()
    assert result
```

## 测试工具配置

### 1. pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --disable-warnings
    -ra
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
```

### 2. pyproject.toml
```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*",
    "*/conftest.py"
]
branch = true
fail_under = 80

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:"
]
```

## 测试数据管理

### 1. 测试数据分层
```
tests/
├── fixtures/          # 测试夹具
│   ├── user.json     # 用户数据
│   └── match.json    # 比赛数据
├── factories/         # 数据工厂
│   ├── user_factory.py
│   └── match_factory.py
└── conftest.py        # 共享配置
```

### 2. 工厂模式示例
```python
# tests/factories/user_factory.py
import factory
from src.domain.models import User

class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n)
    name = factory.Faker("name")
    email = factory.LazyAttribute(lambda o: f"{o.name.lower()}@example.com")
    age = factory.Faker("random_int", min=18, max=80)

class AdminUserFactory(UserFactory):
    role = "admin"
    permissions = ["read", "write", "delete"]
```

## 性能测试

### 1. 基准测试
```python
def test_performance_critical_path(benchmark):
    """性能基准测试"""
    data = list(range(1000))

    def process_data():
        return [x * 2 for x in data if x > 500]

    result = benchmark(process_data)
    assert result == [x * 2 for x in data if x > 500]
    # 性能断言
    assert benchmark.stats["mean"] < 0.01  # 10ms内完成
```

### 2. 内存测试
```python
def test_memory_usage():
    """内存使用测试"""
    import psutil
    import gc

    process = psutil.Process()
    initial_memory = process.memory_info().rss

    # 执行操作
    large_data = [0] * 1000000
    process_data(large_data)

    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory

    # 内存增长不超过100MB
    assert memory_increase < 100 * 1024 * 1024
```

## 总结

遵循这些标准可以确保：
1. **测试质量高**：每个测试都有明确的价值
2. **维护成本低**：测试易于理解和修改
3. **执行速度快**：快速反馈开发进度
4. **覆盖率高**：保证代码质量
5. **CI/CD稳定**：减少失败风险

记住：**测试不是越多越好，而是越精准越好！**