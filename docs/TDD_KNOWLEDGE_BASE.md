# TDD知识库

## 📚 核心概念

### 什么是TDD？
测试驱动开发（Test-Driven Development）是一种软件开发方法，遵循"测试先行"的原则，通过Red-Green-Refactor循环来驱动代码设计。

### TDD的核心循环

#### 1. Red（红灯）
- 写一个失败的测试
- 测试应该清晰地描述需求
- 确保测试失败是因为功能不存在，而不是其他原因

```python
def test_should_return_5_when_add_2_and_3():
    calculator = Calculator()
    result = calculator.add(2, 3)
    assert result == 5  # 预期会失败，因为add方法还不存在
```

#### 2. Green（绿灯）
- 写最少的代码让测试通过
- 不要过度设计
- 可以暂时忽略代码质量

```python
def add(self, a, b):
    return 5  # 最简单的实现，让测试通过
```

#### 3. Refactor（重构）
- 在测试保护下优化代码
- 消除重复
- 提高可读性

```python
def add(self, a, b):
    return a + b  # 重构为正确的实现
```

## 🎯 最佳实践

### 1. 测试命名

#### 原则
- 测试名称应该描述它要验证什么
- 使用"should/when"模式
- 避免模糊的名称

#### 好的示例
```python
def test_should_return_empty_list_when_no_items_added():
    pass

def test_should_raise_validation_error_when_email_is_invalid():
    pass

def test_should_calculate_total_price_including_tax():
    pass
```

#### 不好的示例
```python
def test_add():
    pass

def test_user():
    pass

def test_works():
    pass
```

### 2. 测试结构（AAA模式）

#### Arrange（准备）
- 准备测试数据
- 设置测试环境
- 创建必要的对象

#### Act（行动）
- 执行被测试的方法
- 触发要测试的行为

#### Assert（断言）
- 验证结果
- 检查是否符合预期

```python
def test_user_registration_with_valid_data():
    # Arrange
    user_data = {
        'email': 'test@example.com',
        'password': 'SecurePass123!',
        'name': 'Test User'
    }

    # Act
    user = UserService().register(user_data)

    # Assert
    assert user.email == 'test@example.com'
    assert user.is_active is True
    assert user.id is not None
```

### 3. 测试隔离

#### 原则
- 每个测试应该独立运行
- 不依赖其他测试的状态
- 不影响其他测试

#### 实现
```python
@pytest.fixture
def fresh_database():
    # 每个测试前都创建新的数据库
    with create_test_database() as db:
        yield db
        # 自动清理

def test_create_user(fresh_database):
    # 使用全新的数据库
    pass

def test_update_user(fresh_database):
    # 使用全新的数据库，不受其他测试影响
    pass
```

### 4. Mock和Stub

#### 何时使用Mock
- 测试涉及外部依赖
- 需要控制依赖的行为
- 依赖太慢或不稳定

```python
from unittest.mock import Mock

def test_send_email_notification():
    # 准备Mock对象
    email_service = Mock()
    user = User(email='test@example.com')

    # 执行操作
    send_notification(user, email_service)

    # 验证交互
    email_service.send.assert_called_once_with(
        to='test@example.com',
        subject='Notification',
        body='Hello!'
    )
```

#### 何时使用Stub
- 需要提供测试数据
- 不需要验证交互

```python
def test_calculate_total_with_stub():
    # 创建Stub提供数据
    stub_repository = StubRepository()
    stub_repository.get_prices.return_value = [10, 20, 30]

    calculator = PriceCalculator(stub_repository)
    total = calculator.calculate_total()

    assert total == 60
```

### 5. 测试数据管理

#### 使用工厂模式
```python
class UserFactory:
    @staticmethod
    def create_user(**overrides):
        defaults = {
            'email': 'test@example.com',
            'name': 'Test User',
            'is_active': True
        }
        return User(**{**defaults, **overrides})

# 使用
def test_inactive_user():
    user = UserFactory.create_user(is_active=False)
    assert not user.is_active
```

#### 使用Builder模式
```python
class UserBuilder:
    def __init__(self):
        self.user = User()
        self.user.email = 'test@example.com'
        self.user.name = 'Test User'

    def with_email(self, email):
        self.user.email = email
        return self

    def inactive(self):
        self.user.is_active = False
        return self

    def build(self):
        return self.user

# 使用
def test_inactive_user():
    user = (UserBuilder()
            .with_email('inactive@example.com')
            .inactive()
            .build())
    assert not user.is_active
```

## 🚨 常见陷阱与解决方案

### 1. 测试太复杂

#### 问题
```python
# ❌ 测试逻辑太复杂
def test_complex_calculation():
    # 50行准备代码
    # 复杂的计算逻辑
    # 多个断言
    pass
```

#### 解决方案
```python
# ✅ 简化测试
def test_should_add_two_numbers():
    # 简单明了
    calculator = Calculator()
    result = calculator.add(2, 3)
    assert result == 5

# 将复杂逻辑拆分到多个测试
def test_should_add_negative_numbers():
    calculator = Calculator()
    result = calculator.add(-2, -3)
    assert result == -5
```

### 2. 测试脆弱

#### 问题
```python
# ❌ 依赖具体实现细节
def test_user_email_format():
    user = User()
    assert user._email == 'test@example.com'  # 依赖私有属性
```

#### 解决方案
```python
# ✅ 测试行为而非实现
def test_user_can_be_created_with_email():
    user = User(email='test@example.com')
    assert user.get_email() == 'test@example.com'
```

### 3. 测试覆盖率陷阱

#### 问题
- 追求100%覆盖率
- 编写无意义的测试

#### 解决方案
```python
# ❌ 无意义的测试
def test_getter():
    obj = MyClass()
    assert obj.value == obj.value  # 毫无意义

# ✅ 有价值的测试
def test_value_should_persist():
    obj = MyClass()
    obj.set_value(42)
    assert obj.get_value() == 42
```

### 4. 测试太慢

#### 问题
- 测试涉及数据库、网络等慢操作
- 运行一次需要几分钟

#### 解决方案
```python
# ❌ 真实数据库测试
def test_save_user():
    db = connect_to_production_database()  # 慢！
    # ...测试代码

# ✅ 使用内存数据库或Mock
def test_save_user():
    db = create_in_memory_database()  # 快！
    # ...测试代码

# 或使用Mock
def test_save_user():
    db = Mock()
    # ...测试代码
```

## 🔧 高级技巧

### 1. 参数化测试

```python
import pytest

@pytest.mark.parametrize("a,b,expected", [
    (2, 3, 5),
    (-2, -3, -5),
    (0, 0, 0),
    (100, 200, 300)
])
def test_add_multiple_cases(a, b, expected):
    calculator = Calculator()
    assert calculator.add(a, b) == expected
```

### 2. 测试金字塔

```
    /\
   /E2E\     少量端到端测试
  /______\
 /        \
/Integration\ 适量集成测试
/____________\
/            \
/  Unit Tests  \ 大量单元测试
/______________\
```

### 3. 测试分类

```python
# 快速测试
@pytest.mark.unit
def test_calculator_add():
    pass

# 慢速测试
@pytest.mark.slow
@pytest.mark.integration
def test_user_flow():
    pass

# 需要特殊环境
@pytest.mark.requires_db
def test_database_operations():
    pass
```

### 4. 测试工具链

#### 推荐工具
- **pytest**: 测试框架
- **pytest-cov**: 覆盖率报告
- **pytest-mock**: Mock支持
- **factory-boy**: 测试数据工厂
- **hypothesis**: 属性测试

#### 配置示例
```ini
# pytest.ini
[tool:pytest]
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    requires_db: Tests requiring database
addopts =
    --strict-markers
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
```

## 📖 学习资源

### 必读书籍
1. 《测试驱动开发》- Kent Beck
2. 《Growing Object-Oriented Software》- Steve Freeman
3. 《Working Effectively with Legacy Code》- Michael Feathers

### 在线资源
- [Test-Driven Development: By Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)
- [Pytest文档](https://docs.pytest.org/)
- [TDD Kata练习](https://katas.tdd.org/)

### 练习项目
1. FizzBuzz
2. 罗马数字转换
3. 购物车
4. 银行账户
5. 生命游戏

## 🎯 TDD检查清单

### 编写测试前
- [ ] 我理解要实现的功能吗？
- [ ] 我能描述清楚成功和失败的情况吗？
- [ ] 测试名称是否描述了期望的行为？

### 编写测试时
- [ ] 测试是否独立？
- [ ] 是否使用了AAA模式？
- [ ] 断言是否清晰明确？
- [ ] 是否只测试一个行为？

### 实现功能时
- [ ] 是否写了最少的代码？
- [ ] 代码是否刚好通过测试？
- [ ] 是否避免过度设计？

### 重构时
- [ ] 是否在测试保护下进行？
- [ ] 是否消除了重复？
- [ ] 是否提高了可读性？
- [ ] 所有测试是否仍然通过？

## 💡 TDD语录

> "If you're not writing tests first, you're not doing TDD." - Kent Beck

> "TDD is not about testing. TDD is about design." - Robert C. Martin

> "The act of writing a test first forces you to think about the design."

> "Fear is the mind-killer. Tests are the fear-killer."

---

记住：TDD是一种技能，需要持续练习才能掌握。保持耐心，持续改进！
