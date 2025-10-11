# 测试指南

## 测试结构

### 单元测试 (tests/unit/)
- **core/**: 核心业务逻辑测试
- **api/**: API路由和端点测试
- **services/**: 服务层测试
- **database/**: 数据库模型和查询测试
- **repositories/**: 仓储模式测试
- **domain/**: 领域模型测试
- **utils/**: 工具函数测试

### 集成测试 (tests/integration/)
- **api/**: API集成测试
- **database/**: 数据库集成测试
- **services/**: 服务集成测试

### 端到端测试 (tests/e2e/)
- 完整的用户流程测试

### 性能测试 (tests/performance/)
- 基准测试和性能分析

## 测试命名规范

### 文件命名
- 使用 `test_` 前缀
- 格式：`test_<module>_<feature>.py`
- 示例：`test_user_service_authentication.py`

### 函数命名
- 使用 `test_` 前缀
- 格式：`test_<feature>_<scenario>`
- 使用描述性名称
- 示例：`test_user_login_with_valid_credentials`

### 类命名
- 使用 `Test` 前缀
- 示例：`class TestUserService`

## 测试标记

使用 pytest 标记来分类测试：

```python
import pytest

@pytest.mark.unit
class TestUserService:
    pass

@pytest.mark.api
@pytest.mark.database
def test_create_user_via_api():
    pass

@pytest.mark.slow
@pytest.mark.integration
def test_full_workflow():
    pass
```

## 测试编写最佳实践

### 1. 使用 AAA 模式
- **Arrange** - 准备测试数据
- **Act** - 执行被测试的代码
- **Assert** - 验证结果

### 2. 使用描述性的断言
```python
# 好的断言
assert user.is_active is True
assert len(user.predictions) == 5

# 避免的断言
assert True  # 没有意义的断言
```

### 3. 使用 Fixtures
- 在 conftest.py 中定义可复用的 fixtures
- 使用 fixtures 来准备测试数据和模拟依赖

### 4. Mock 外部依赖
- 使用 unittest.mock 进行 mock
- Mock 数据库、网络请求、文件系统等
- 避免测试依赖外部资源

### 5. 测试边界条件
- 测试正常情况
- 测试异常情况
- 测试边界值

## 运行测试

### 运行所有测试
```bash
pytest
```

### 运行特定标记的测试
```bash
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

### 运行特定文件
```bash
pytest tests/unit/services/test_user_service.py
```

### 生成覆盖率报告
```bash
pytest --cov=src --cov-report=html
```
