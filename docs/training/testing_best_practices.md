# 测试最佳实践培训材料

> 目标受众：开发团队
> 培训时长：2小时
> 最后更新：2025-10-17

## 📚 目录

1. [培训目标](#培训目标)
2. [测试基础概念](#测试基础概念)
3. [我们的测试策略](#我们的测试策略)
4. [实践演练](#实践演练)
5. [常见问题](#常见问题)
6. [参考资料](#参考资料)

## 🎯 培训目标

完成本次培训后，您将能够：

- ✅ 理解测试金字塔和各层测试的作用
- ✅ 编写符合最佳实践的单元测试
- ✅ 使用正确的Mock策略
- ✅ 编写清晰、可维护的测试代码
- ✅ 应用统一的命名约定
- ✅ 使用Faker生成测试数据

## 📖 测试基础概念

### 1. 什么是单元测试？

单元测试是针对软件中最小可测试单元进行的测试。在Python中，通常是一个函数或方法。

```python
# 示例：计算两个数的和
def add(a, b):
    return a + b

# 对应的单元测试
def test_add_with_positive_numbers():
    assert add(2, 3) == 5
```

### 2. 测试金字塔

```
        /\
       /  \     E2E Tests (10%)
      /____\     完整业务流程
     /      \
    /________\  Integration Tests (20%)
   /          \  模块间交互
  /____________\
 /              \ Unit Tests (70%)
/________________\ 单元逻辑
```

### 3. 测试的FIRST原则

- **Fast（快速）**：测试应该在几秒内完成
- **Independent（独立）**：测试之间不应相互依赖
- **Repeatable（可重复）**：每次运行结果应该相同
- **Self-validating（自验证）**：有明确的通过/失败结果
- **Timely（及时）**：在生产代码之前编写测试

## 🏗️ 我们的测试策略

### 1. 命名约定

格式：`test_[功能]_[场景]_[期望结果]`

```python
# ✅ 好的命名
def test_create_prediction_with_valid_data_returns_201(self):
def test_create_prediction_with_invalid_match_id_returns_422(self):
def test_batch_prediction_with_empty_list_returns_422(self):

# ❌ 不好的命名
def test_prediction_1(self):
def test_data(self):
def test_it_works(self):
```

### 2. 测试结构（AAA模式）

```python
def test_user_creation():
    # Arrange - 准备测试数据
    user_data = {
        "name": "John Doe",
        "email": "john@example.com"
    }

    # Act - 执行操作
    user = User.create(user_data)

    # Assert - 验证结果
    assert user.name == "John Doe"
    assert user.email == "john@example.com"
```

### 3. Mock使用原则

#### 什么时候使用Mock？
- 外部依赖（数据库、API、文件系统）
- 慢速操作（网络请求）
- 难以重现的条件（错误场景）

#### 什么时候不用Mock？
- 核心业务逻辑
- 简单的工具函数
- 数据转换逻辑

#### 正确的Mock使用

```python
# ✅ 推荐：精确patch
@patch('src.services.prediction.fetch_external_data')
def test_prediction_with_external_api(self, mock_fetch):
    mock_fetch.return_value = {"odds": [1.5, 3.2, 5.8]}

    prediction = PredictionService.create(123)

    assert prediction is not None
    mock_fetch.assert_called_once_with(123)

# ❌ 避免：全局mock
# 不要在conftest.py中全局替换requests
```

### 4. 断言最佳实践

```python
# ✅ 推荐：明确的断言
assert response.status_code == 201, f"Expected 201, got {response.status_code}"
assert user.is_active, f"User {user.id} should be active"

# ✅ 推荐：验证必要字段
required_fields = ["id", "name", "email"]
for field in required_fields:
    assert field in response.json(), f"Missing field: {field}"

# ❌ 避免：模糊断言
assert response.status_code in [200, 201, 202]
assert "success" in str(response.json())
```

## 💻 实践演练

### 练习1：编写第一个单元测试

任务：为以下函数编写测试

```python
# src/utils/calculator.py
def calculate_win_probability(home_goals, away_goals):
    """根据进球数计算获胜概率"""
    if home_goals > away_goals:
        return 0.8
    elif home_goals < away_goals:
        return 0.2
    else:
        return 0.5
```

解决方案：

```python
# tests/unit/utils/test_calculator.py
import pytest
from src.utils.calculator import calculate_win_probability

class TestCalculateWinProbability:
    def test_home_team_wins_returns_80_percent(self):
        """测试：主队进球数多时返回80%概率"""
        result = calculate_win_probability(3, 1)
        assert result == 0.8

    def test_away_team_wins_returns_20_percent(self):
        """测试：客队进球数多时返回20%概率"""
        result = calculate_win_probability(1, 3)
        assert result == 0.2

    def test_equal_goals_returns_50_percent(self):
        """测试：进球数相等时返回50%概率"""
        result = calculate_win_probability(2, 2)
        assert result == 0.5
```

### 练习2：使用Faker生成测试数据

任务：使用Faker创建测试数据

```python
# ✅ 解决方案
from tests.factories.fake_data_improved import create_valid_prediction

def test_prediction_creation_with_faker_data():
    """使用Faker数据测试预测创建"""
    # 使用Faker生成数据
    prediction_data = create_valid_prediction(
        match_id=123,
        confidence=0.85
    )

    # 测试逻辑
    service = PredictionService()
    result = service.create(prediction_data)

    assert result is not None
    assert result.match_id == 123
    assert result.confidence == 0.85
```

### 练习3：Mock外部依赖

任务：为依赖外部API的服务编写测试

```python
# src/services/odds_service.py
import requests

def get_match_odds(match_id):
    """获取比赛赔率"""
    response = requests.get(f"https://api.odds.com/matches/{match_id}")
    return response.json()
```

```python
# ✅ 解决方案
from unittest.mock import patch

class TestOddsService:
    @patch('src.services.odds_service.requests.get')
    def test_get_match_odds_with_valid_id_returns_odds(self, mock_get):
        """测试：有效ID获取赔率返回赔率数据"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "match_id": 123,
            "home_win": 2.0,
            "draw": 3.2,
            "away_win": 3.8
        }
        mock_get.return_value = mock_response

        # Act
        odds = get_match_odds(123)

        # Assert
        assert odds["match_id"] == 123
        assert odds["home_win"] == 2.0
        mock_get.assert_called_once_with("https://api.odds.com/matches/123")
```

### 练习4：API测试

任务：为FastAPI端点编写测试

```python
# ✅ 解决方案
class TestPredictionAPI:
    def test_create_prediction_with_valid_data_returns_201(self):
        """测试：使用有效数据创建预测返回201"""
        request_data = {
            "match_id": 123,
            "model_version": "v1.0"
        }

        response = client.post("/predictions", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["match_id"] == 123
        assert "predicted_outcome" in data

    def test_create_prediction_with_invalid_data_returns_422(self):
        """测试：使用无效数据创建预测返回422"""
        request_data = {
            "match_id": "invalid"  # 应该是整数
        }

        response = client.post("/predictions", json=request_data)

        assert response.status_code == 422
```

## ❓ 常见问题

### Q1: 测试太慢怎么办？

**A:**
- 使用pytest-xdist并行运行：`pytest -n auto`
- 减少数据库操作，使用内存数据库
- 避免不必要的sleep，使用Mock替代
- 只运行相关的测试：`pytest -m "unit and not slow"`

### Q2: 测试不稳定（flaky）怎么办？

**A:**
- 检查测试依赖，确保测试独立
- 使用固定种子：`Faker.seed(42)`
- 添加等待机制而不是硬编码时间
- 检查资源清理是否完整

### Q3: 如何测试私有方法？

**A:**
- 优先通过公共接口测试
- 如果必须测试，考虑：
  ```python
  # 通过继承访问
  class TestPublicInterface(TestPrivateClass):
      def test_private_method(self):
          return self._private_method()
  ```

### Q4: Mock太多正常吗？

**A:**
- 如果Mock超过50%，可能说明：
  - 代码耦合度太高
  - 需要重构
  - 应该写更多集成测试

### Q5: 测试覆盖率100%是必须的吗？

**A:**
- 不是，追求有意义的覆盖率
- 重点关注：
  - 核心业务逻辑
  - 错误处理路径
  - 边界条件
- 100%覆盖率可能只是幻觉

## 📋 检查清单

在提交代码前，确保：

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

## 🚀 快速参考

### 常用pytest命令

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/unit/test_service.py

# 运行特定测试
pytest tests/unit/test_service.py::test_method

# 显示详细输出
pytest -v

# 在第一个失败时停止
pytest -x

# 只运行失败的测试
pytest --lf

# 运行带标记的测试
pytest -m "unit"
pytest -m "not slow"

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 常用Mock模式

```python
# Mock属性
@patch('module.ClassName.attribute')
def test_something(self, mock_attr):
    mock_attr.return_value = "mocked_value"

# Mock整个类
@patch('module.ClassName')
def test_something(self, MockClass):
    instance = MockClass.return_value
    instance.method.return_value = "result"

# Mock上下文管理器
with patch('module.function') as mock_func:
    mock_func.return_value = "value"
    # 测试代码
```

### 常用断言

```python
# 基本断言
assert result == expected
assert result is not None
assert condition, "Error message"

# 集合断言
assert "key" in dict
assert value in list
assert len(list) == expected

# 异常断言
with pytest.raises(ValueError):
    function_that_raises()

# 警告断言
with pytest.warns(DeprecationWarning):
    deprecated_function()
```

## 📚 进一步学习

### 推荐阅读
1. [Effective Testing with RSpec, Java, and Python](https://effective-testing.com/)
2. [Python Testing with pytest](https://pythontestingbook.org/)
3. [Test-Driven Development with Python](https://www.obeythetestinggoat.com/)

### 内部资源
- 测试策略文档：`docs/testing_strategy.md`
- 测试模板：`tests/templates/`
- 最佳实践示例：`tests/unit/test_faker_integration.py`

## 🎉 总结

记住：
- 测试是代码质量的重要保障
- 编写测试需要练习和耐心
- 保持简单，专注于核心价值
- 团队合作，相互学习，共同提高

---

**培训反馈**：请提供您的反馈和建议，帮助我们改进培训材料。
