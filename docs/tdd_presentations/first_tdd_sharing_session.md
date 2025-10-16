# TDD分享会：Mock与Stub在测试中的艺术

**分享人**：TDD推动小组
**日期**：2025-10-22（计划）
**时长**：45分钟

---

## 📋 会议议程

| 时间 | 内容 | 负责人 |
|------|------|--------|
| 16:00-16:05 | 开场 & TDD进展汇报 | 主持人 |
| 16:05-16:10 | TDD小贴士：测试命名艺术 | 志愿者 |
| 16:10-16:20 | 主题分享：Mock与Stub | 主讲人 |
| 16:20-16:35 | 实战演练 | 全体参与 |
| 16:35-16:45 | 自由讨论 & 总结 | 全体 |

---

## 🎯 本次分享会目标

1. **理解Mock和Stub的区别**
2. **掌握在Python中使用Mock的技巧**
3. **学会如何测试外部依赖**
4. **提升测试的可维护性**

---

## ⚡ TDD小贴士（5分钟）

### 测试命名指南

#### ❌ 不好的命名
```python
def test_1():
    pass

def test_user():
    pass

def test_works():
    pass
```

#### ✅ 好的命名
```python
def test_user_registration_with_valid_email_should_succeed():
    """测试用户使用有效邮箱注册应该成功"""
    pass

def test_should_raise_error_when_password_is_too_short():
    """测试密码过短时应该抛出错误"""
    pass

def test_calculate_total_should_include_tax_and_shipping():
    """测试计算总额应该包含税费和运费"""
    pass
```

### 命名模式
- **Should模式**：`test_should_[期望]_when_[条件]`
- **场景模式**：`test_[功能]_with_[条件]_[期望结果]`
- **行为驱动**：`test_[主语]_[动词]_[宾语]_[期望]`

---

## 🎪 主题分享：Mock vs Stub（15分钟）

### 核心概念

#### 什么是Stub？
- **定义**：预设响应的测试替代品
- **用途**：提供测试数据
- **特点**：不会验证交互

```python
# Stub示例
class UserRepositoryStub:
    def __init__(self):
        self.users = [
            User(id=1, name="Alice", email="alice@example.com"),
            User(id=2, name="Bob", email="bob@example.com")
        ]

    def find_by_id(self, user_id):
        for user in self.users:
            if user.id == user_id:
                return user
        return None
```

#### 什么是Mock？
- **定义**：可验证交互的测试替代品
- **用途**：验证行为和交互
- **特点**：可以验证调用次数、参数等

```python
# Mock示例（使用unittest.mock）
from unittest.mock import Mock, MagicMock

email_service = Mock()
user = User(name="Alice", email="alice@example.com")

# 执行操作
send_welcome_email(user, email_service)

# 验证交互
email_service.send.assert_called_once_with(
    to="alice@example.com",
    subject="Welcome!",
    template="welcome"
)
```

### 主要区别

| 特性 | Stub | Mock |
|------|------|------|
| 目的 | 提供数据 | 验证行为 |
| 状态 | 只返回预设值 | 记录调用历史 |
| 断言 | 验证最终状态 | 验证交互过程 |
| 复杂度 | 简单 | 相对复杂 |

### 实践案例

#### 场景1：测试支付功能

```python
# 使用Stub
def test_payment_successful_with_valid_card():
    # Arrange
    payment_gateway = PaymentGatewayStub(success=True)
    cart = ShoppingCart()
    cart.add_item("Book", 29.99)

    # Act
    result = cart.checkout(payment_gateway)

    # Assert
    assert result.success is True
    assert result.transaction_id is not None

# 使用Mock
def test_payment_should_call_gateway_with_correct_amount():
    # Arrange
    payment_gateway = Mock()
    payment_gateway.charge.return_value = {"success": True, "id": "12345"}
    cart = ShoppingCart()
    cart.add_item("Book", 29.99)

    # Act
    cart.checkout(payment_gateway)

    # Assert
    payment_gateway.charge.assert_called_once_with(
        amount=29.99,
        currency="USD"
    )
```

#### 场景2：测试邮件发送

```python
# 不要这样做（测试了实现细节）
def test_user_registration_sends_email():
    with patch('smtplib.SMTP') as mock_smtp:
        register_user("test@example.com", "password")
        mock_smtp.return_value.sendmail.assert_called()
        # 太多细节，容易破碎

# 更好的方式（使用Mock）
def test_user_registration_triggers_welcome_email():
    email_service = Mock()
    user = register_user("test@example.com", "password", email_service)
    email_service.send_welcome_email.assert_called_once_with(user)
```

---

## 🛠️ 实战演练（15分钟）

### 练习1：为天气预报服务写测试

```python
# 待测试的代码
class WeatherApp:
    def __init__(self, api_client):
        self.api_client = api_client

    def get_today_forecast(self, city):
        data = self.api_client.get_weather(city)
        if data["temperature"] > 25:
            return f"今天{city}很热，{data['temperature']}°C"
        else:
            return f"今天{city}很凉爽，{data['temperature']}°C"
```

#### 任务：完成测试

```python
def test_weather_app_hot_day():
    # TODO: 使用Stub或Mock完成测试
    pass

def test_weather_app_cold_day():
    # TODO: 使用Stub或Mock完成测试
    pass
```

### 练习2：测试文件上传功能

```python
# 待测试的代码
class FileUploader:
    def __init__(self, storage_service, notifier):
        self.storage = storage_service
        self.notifier = notifier

    def upload_file(self, filename, content):
        try:
            url = self.storage.save(filename, content)
            self.notifier.notify(f"文件已上传: {url}")
            return {"success": True, "url": url}
        except Exception as e:
            self.notifier.notify(f"上传失败: {str(e)}")
            return {"success": False, "error": str(e)}
```

#### 任务：编写测试覆盖成功和失败场景

```python
def test_upload_file_success():
    # TODO: 使用Mock测试成功场景
    pass

def test_upload_file_failure():
    # TODO: 使用Mock测试失败场景
    pass
```

---

## 💡 最佳实践

### 1. 选择合适的测试替身

- **使用Stub当**：
  - 只需要提供测试数据
  - 不关心交互细节
  - 测试对象的行为而非实现

- **使用Mock当**：
  - 需要验证交互
  - 测试协议或接口
  - 确保副作用正确发生

### 2. 避免过度Mock

```python
# ❌ 过度Mock
def test_user_flow():
    db = Mock()
    cache = Mock()
    email = Mock()
    logger = Mock()
    metrics = Mock()
    # 太多Mock，测试变得脆弱

# ✅ 适度使用
def test_user_flow():
    # 集成测试或使用真实的数据库
    db = TestDatabase()
    email = Mock()  # 只Mock外部依赖
```

### 3. 保持测试简洁

```python
# ✅ 好的示例
def test_should_charge_correct_amount():
    payment_gateway = Mock()
    payment_gateway.charge.return_value = {"success": True}

    cart = ShoppingCart()
    cart.add_item("Book", 29.99)

    cart.checkout(payment_gateway)

    payment_gateway.charge.assert_called_once_with(amount=29.99)
```

---

## 🔧 常见问题与解决方案

### Q1：什么时候应该使用Mock？
**A**：当测试代码依赖外部系统时：
- 数据库
- API调用
- 文件系统
- 时间/日期
- 网络请求

### Q2：Mock让测试变得脆弱怎么办？
**A**：
- Mock接口而非实现
- 使用集成测试补充
- 保持Mock简单
- 定期更新Mock

### Q3：如何测试异步代码？
```python
# 使用AsyncMock
import asyncio
from unittest.mock import AsyncMock

async def test_async_operation():
    async_service = AsyncMock()
    async_service.fetch_data.return_value = {"result": "success"}

    result = await my_async_function(async_service)

    assert result == {"result": "success"}
    async_service.fetch_data.assert_called_once()
```

---

## 📊 团队TDD进展

### 当前状态
- **总体覆盖率**：24.2%
- **string_utils**：100% ✅
- **helpers**：100% ✅
- **predictions**：93% ✅

### 本周改进
- ✅ 修复了string_utils所有测试
- ✅ 达成70个测试用例全部通过
- ✅ 建立了完整的TDD工具链

### 下周目标
- 🎯 提升dict_utils模块覆盖率
- 🎯 组织第二次TDD工作坊
- 🎯 完善CI/CD中的TDD检查

---

## 🎯 互动讨论

### 思考题

1. **在你的项目中，哪些场景适合使用Mock？哪些适合使用Stub？**
2. **过度使用Mock会带来什么问题？如何避免？**
3. **如何平衡测试的隔离性和真实性？**

### 分享你的经验

- 你在使用Mock时遇到过什么困难？
- 有什么好的测试实践愿意分享？
- 对团队的TDD实践有什么建议？

---

## 📚 推荐资源

### 📖 必读书籍
- 《测试驱动开发》- Kent Beck
- 《xUnit测试模式》- Gerard Meszaros
- 《Growing Object-Oriented Software》- Steve Freeman

### 🔗 在线资源
- [Python Mock文档](https://docs.python.org/3/library/unittest.mock.html)
- [TestDouble](https://martinfowler.com/bliki/TestDouble.html)
- [Mock最佳实践](https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html)

---

## ✨ 下次会议预告

**主题**：TDD在遗留代码中的应用
**日期**：2025-10-29
**分享人**：待定

---

## Thank You! 💫

**欢迎提问和讨论！**

记住：*Mock是工具，不是目的。关键是写出清晰、可维护的测试。*
