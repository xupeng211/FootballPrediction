# 测试规范文档

## 概述

本文档定义了FootballPrediction项目的测试标准、规范和最佳实践。

## 测试原则

1. **FIRST原则**
   - **Fast** - 测试应该快速执行
   - **Independent** - 测试之间应该相互独立
   - **Repeatable** - 测试应该在任何环境下可重复执行
   - **Self-Validating** - 测试应该有明确的通过/失败结果
   - **Timely** - 测试应该及时编写

2. **测试金字塔**
   - 70% 单元测试 (Unit Tests)
   - 20% 集成测试 (Integration Tests)
   - 10% 端到端测试 (E2E Tests)

## 测试命名规范

### 测试文件命名
- 单元测试：`test_<module_name>.py`
- 集成测试：`test_<feature>_integration.py`
- E2E测试：`test_<workflow>_e2e.py`

### 测试类命名
- 使用描述性名称：`TestClassName` 或 `TestFeatureName`
- 避免缩写：使用 `TestAuthentication` 而不是 `TestAuth`

### 测试方法命名
- 格式：`test_<functionality>_<scenario>_<expected_result>`
- 示例：
  ```python
  def test_login_with_valid_credentials_should_succeed(self):
  def test_create_user_with_duplicate_email_should_fail(self):
  def test_get_match_by_id_with_nonexistent_id_should_return_404(self):
  ```

## 测试结构

### AAA模式（Arrange-Act-Assert）
```python
def test_user_creation():
    # Arrange - 准备测试数据
    user_data = {"name": "John", "email": "john@example.com"}

    # Act - 执行被测试的操作
    user = User.create(user_data)

    # Assert - 验证结果
    assert user.name == "John"
    assert user.email == "john@example.com"
```

### 测试组织
- 使用pytest fixtures处理通用设置
- 使用参数化测试处理多种输入情况
- 将相关的测试组织在同一个测试类中

## 测试覆盖率要求

### 覆盖率目标
- **最低要求**：80%行覆盖率
- **推荐目标**：90%行覆盖率，85%分支覆盖率
- **关键模块**：95%以上覆盖率

### 覆盖率例外
- 配置文件
- 异常处理中的日志语句
- 类型注解相关代码
- 废弃代码（需要标记）

## 测试数据管理

### 测试数据原则
- 每个测试应该是自包含的
- 不依赖外部数据
- 使用工厂模式生成测试数据

### 测试数据示例
```python
# 使用工厂模式
@pytest.fixture
def sample_user():
    return {
        "id": 1,
        "name": "Test User",
        "email": "test@example.com",
        "active": True
    }

# 使用参数化
@pytest.mark.parametrize("input,expected", [
    (1, 1),
    (2, 4),
    (3, 9),
])
def test_square(input, expected):
    assert square(input) == expected
```

## Mock和Stub

### 使用原则
- Mock外部依赖（数据库、API、文件系统）
- 不Mock被测试的类本身
- 保持Mock简单和专注

### 示例
```python
# 使用Mock
from unittest.mock import Mock, patch

def test_api_call():
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok"}

        response = api_call()

        assert response["status"] == "ok"
        mock_get.assert_called_once_with("https://api.example.com")
```

## 异步测试

### 测试异步代码
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### 异步Fixture
```python
@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

## 测试环境

### 测试数据库
- 使用内存数据库或测试数据库
- 每个测试运行前清理数据
- 使用事务回滚确保隔离

### 测试配置
- 使用单独的测试配置文件
- 环境变量使用测试值
- 禁用外部服务调用

## CI/CD集成

### GitHub Actions工作流
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          make install
      - name: Run tests
        run: |
          make test
          make coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

### 质量门禁
- 所有测试必须通过
- 覆盖率不能低于80%
- 代码质量检查必须通过

## 测试报告

### 覆盖率报告
- 生成HTML覆盖率报告
- 上传到Codecov或类似服务
- 持续跟踪覆盖率变化

### 测试结果
- 使用JUnit XML格式输出
- 集成到CI/CD平台
- 发送测试结果通知

## 最佳实践

### DO
- ✅ 保持测试简单和专注
- ✅ 使用描述性的测试名称
- ✅ 测试边界条件和错误情况
- ✅ 定期重构测试代码
- ✅ 使用有意义的断言消息

### DON'T
- ❌ 测试多个功能在一个测试中
- ❌ 依赖测试执行顺序
- ❌ 在测试中使用随机数据
- ❌ 忽略测试失败
- ❌ 编写过于复杂的测试

## 测试命令

```bash
# 运行所有测试
make test

# 运行特定模块测试
pytest tests/unit/utils/

# 运行带覆盖率的测试
make coverage

# 查看覆盖率报告
open htmlcov/index.html

# 运行快速测试
make test-quick
```

## 工具和框架

### 核心工具
- **pytest**: 测试框架
- **pytest-cov**: 覆盖率测试
- **pytest-asyncio**: 异步测试支持
- **pytest-mock**: Mock支持

### 推荐工具
- **factory-boy**: 测试数据工厂
- **faker**: 生成假数据
- **hypothesis**: 属性基测试
- **pytest-xdist**: 并行测试执行

## 故障排除

### 常见问题
1. **导入错误**：检查Python路径和模块结构
2. **数据库错误**：确保使用测试数据库
3. **异步测试错误**：使用正确的pytest标记
4. **覆盖率不正确**：检查配置和包含的文件

### 调试技巧
- 使用 `-v` 标志查看详细输出
- 使用 `--pdb` 进入调试器
- 使用 `--lf` 只运行失败的测试
- 使用 `-k` 按名称选择测试

## 持续改进

定期审查和改进测试：
- 每月检查覆盖率报告
- 每季度评估测试策略
- 根据缺陷更新测试用例
- 培训团队测试最佳实践

## 参考资料

- [pytest官方文档](https://docs.pytest.org/)
- [测试驱动开发](https://en.wikipedia.org/wiki/Test-driven_development)
- [代码覆盖率最佳实践](https://about.codecov.io/blog/)