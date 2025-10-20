# 测试最佳实践快速参考

## 📝 命名约定

### 格式
```
test_[功能]_[场景]_[期望结果]
```

### 示例
```python
✅ 好的命名
test_create_prediction_with_valid_data_returns_201
test_create_prediction_with_invalid_match_id_returns_422
test_batch_prediction_with_empty_list_returns_422

❌ 不好的命名
test_prediction_1
test_data
test_it_works
```

## 🏗️ 测试结构（AAA模式）

```python
def test_function_name():
    # Arrange - 准备测试数据和环境
    data = create_test_data()

    # Act - 执行被测试的操作
    result = function_to_test(data)

    # Assert - 验证结果
    assert result == expected_value, f"Expected {expected_value}, got {result}"
```

## 🎭 Mock使用指南

### 什么时候使用Mock？
- 外部依赖（数据库、API、文件系统）
- 慢速操作（网络请求）
- 难以重现的条件

### 正确的用法
```python
# ✅ 推荐：精确patch
@patch('src.services.prediction.fetch_external_data')
def test_prediction_with_external_api(self, mock_fetch):
    mock_fetch.return_value = {"odds": [1.5, 3.2, 5.8]}

    prediction = PredictionService.create(123)

    assert prediction is not None
    mock_fetch.assert_called_once_with(123)
```

### 错误的用法
```python
# ❌ 避免：全局mock
sys.modules["requests"] = mock_requests
```

## ✅ 断言最佳实践

### 明确的断言
```python
# ✅ 推荐
assert response.status_code == 201, f"Expected 201, got {response.status_code}"
assert user.is_active, f"User {user.id} should be active"

# ❌ 避免
assert response.status_code in [200, 201, 202]
assert "success" in str(response.json())
```

### 验证响应结构
```python
# ✅ 推荐
required_fields = ["id", "name", "email"]
for field in required_fields:
    assert field in response.json(), f"Missing field: {field}"
```

## 🏭 测试数据管理

### 使用Faker
```python
# ✅ 推荐：使用Faker工厂
from tests.factories.fake_data_improved import create_valid_prediction

def test_prediction_creation():
    prediction_data = create_valid_prediction(match_id=123)
    # 测试逻辑
```

### 测试数据验证
```python
# ✅ 推荐：使用Pydantic验证
class PredictionData(BaseModel):
    match_id: int
    home_win_prob: float
    # 字段验证规则
```

## 🚀 常用命令

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/unit/test_service.py

# 运行特定测试
pytest tests/unit/test_service.py::test_method

# 详细输出
pytest -v

# 在第一个失败时停止
pytest -x

# 只运行失败的测试
pytest --lf
```

### 覆盖率
```bash
# 生成覆盖率报告
pytest --cov=src --cov-report=html

# 检查特定模块
pytest --cov=src.services --cov-report=term-missing
```

### 并行执行
```bash
# 使用所有CPU核心
pytest -n auto

# 使用指定数量
pytest -n 4
```

### 按标记运行
```bash
# 运行单元测试
pytest -m "unit"

# 运行快速测试
pytest -m "fast"

# 排除慢测试
pytest -m "not slow"
```

## 📊 质量检查

### 运行质量检查
```bash
# 检查所有测试
python scripts/check_test_quality.py

# 检查特定文件
python scripts/check_test_quality.py tests/unit/test_api.py

# 只检查特定规则
python scripts/check_test_quality.py --rules naming assertions
```

### 质量评分
- 90-100分：优秀
- 80-89分：良好
- 70-79分：一般
- <70分：需要改进

## 🔧 常见模式

### 测试API端点
```python
def test_endpoint_with_valid_data_returns_201(self):
    request_data = {"name": "Test"}
    response = client.post("/endpoint", json=request_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test"
```

### 测试异常
```python
def test_function_with_invalid_input_raises_error(self):
    with pytest.raises(ValueError, match="Invalid input"):
        function_with_validation(invalid_input)
```

### 测试异步代码
```python
@pytest.mark.asyncio
async def test_async_function_returns_expected(self):
    result = await async_function()
    assert result is not None
```

### 参数化测试
```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    assert input * 2 == expected
```

## 📋 检查清单

提交代码前检查：

### 测试编写
- [ ] 测试命名符合约定
- [ ] 使用AAA结构
- [ ] 测试独立，无依赖
- [ ] 断言明确，包含错误信息

### Mock使用
- [ ] Mock范围最小化
- [ ] 使用精确patch
- [ ] 验证Mock调用（如需要）

### 测试数据
- [ ] 使用Faker生成数据
- [ ] 避免硬编码测试值
- [ ] 测试边界条件

### 文档
- [ ] 复杂测试有注释
- [ ] 测试目的清晰
- [ ] 已知限制有说明

## 💡 技巧和窍门

### 快速调试
```python
# 使用-pdb调试
pytest --pdb

# 打印输出
pytest -s

# 只运行一个测试
pytest tests/test_file.py::test_function -v
```

### 提高测试速度
```python
# 使用fixture共享资源
@pytest.fixture(scope="session")
def expensive_resource():
    # 只初始化一次
    return create_expensive_resource()

# 使用mock避免真实操作
@patch('module.expensive_function')
def test_with_mock(mock_function):
    mock_function.return_value = "mocked"
    # 测试逻辑
```

### 组织测试
```python
# 使用类组织相关测试
class TestUserService:
    def test_create_user(self):
        pass

    def test_update_user(self):
        pass

# 使用标记分类
@pytest.mark.slow
def test_slow_operation(self):
    pass
```

## 🔗 有用链接

- [pytest文档](https://docs.pytest.org/)
- [Faker文档](https://faker.readthedocs.io/)
- [测试覆盖率](https://coverage.readthedocs.io/)
- [测试策略文档](testing_strategy.md)

---

*保持简单，专注于价值！*
