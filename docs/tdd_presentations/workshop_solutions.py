"""
TDD分享会实战演练答案
Mock与Stub在测试中的艺术
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# ===================== 练习1：天气预报服务 =====================

class WeatherApp:
    def __init__(self, api_client):
        self.api_client = api_client

    def get_today_forecast(self, city):
        data = self.api_client.get_weather(city)
        if data["temperature"] > 25:
            return f"今天{city}很热，{data['temperature']}°C"
        else:
            return f"今天{city}很凉爽，{data['temperature']}°C"


# 使用Stub的实现
class WeatherApiClientStub:
    def __init__(self, temperature):
        self.temperature = temperature

    def get_weather(self, city):
        return {
            "city": city,
            "temperature": self.temperature,
            "condition": "sunny"
        }


# 解决方案1：使用Stub
def test_weather_app_hot_day_with_stub():
    # Arrange - 使用Stub提供测试数据
    api_client = WeatherApiClientStub(temperature=30)
    app = WeatherApp(api_client)

    # Act
    forecast = app.get_today_forecast("北京")

    # Assert - 验证结果
    assert forecast == "今天北京很热，30°C"


def test_weather_app_cold_day_with_stub():
    # Arrange
    api_client = WeatherApiClientStub(temperature=20)
    app = WeatherApp(api_client)

    # Act
    forecast = app.get_today_forecast("上海")

    # Assert
    assert forecast == "今天上海很凉爽，20°C"


# 解决方案2：使用Mock
def test_weather_app_hot_day_with_mock():
    # Arrange - 使用Mock
    api_client = Mock()
    api_client.get_weather.return_value = {
        "city": "广州",
        "temperature": 28,
        "condition": "sunny"
    }
    app = WeatherApp(api_client)

    # Act
    forecast = app.get_today_forecast("广州")

    # Assert
    assert forecast == "今天广州很热，28°C"
    api_client.get_weather.assert_called_once_with("广州")


def test_weather_app_cold_day_with_mock():
    # Arrange
    api_client = Mock()
    api_client.get_weather.return_value = {
        "city": "深圳",
        "temperature": 22,
        "condition": "cloudy"
    }
    app = WeatherApp(api_client)

    # Act
    forecast = app.get_today_forecast("深圳")

    # Assert
    assert forecast == "今天深圳很凉爽，22°C"
    api_client.get_weather.assert_called_once_with("深圳")


# ===================== 练习2：文件上传功能 =====================

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


# 解决方案：测试文件上传
def test_upload_file_success():
    # Arrange - Mock存储服务和通知服务
    storage_service = Mock()
    storage_service.save.return_value = "https://example.com/files/document.pdf"

    notifier = Mock()

    uploader = FileUploader(storage_service, notifier)

    # Act
    result = uploader.upload_file("document.pdf", b"file content")

    # Assert
    assert result["success"] is True
    assert result["url"] == "https://example.com/files/document.pdf"

    # 验证存储服务被正确调用
    storage_service.save.assert_called_once_with("document.pdf", b"file content")

    # 验证通知被发送
    notifier.notify.assert_called_once_with("文件已上传: https://example.com/files/document.pdf")


def test_upload_file_failure():
    # Arrange - 模拟存储失败
    storage_service = Mock()
    storage_service.save.side_effect = Exception("存储空间不足")

    notifier = Mock()

    uploader = FileUploader(storage_service, notifier)

    # Act
    result = uploader.upload_file("large_file.zip", b"large content")

    # Assert
    assert result["success"] is False
    assert result["error"] == "存储空间不足"

    # 验证存储服务被调用
    storage_service.save.assert_called_once_with("large_file.zip", b"large content")

    # 验证失败通知被发送
    notifier.notify.assert_called_once_with("上传失败: 存储空间不足")


# ===================== 进阶示例：测试邮件发送 =====================

class UserService:
    def __init__(self, email_service):
        self.email_service = email_service
        self.users = {}

    def register_user(self, email, password):
        if email in self.users:
            raise ValueError("用户已存在")

        user_id = len(self.users) + 1
        user = {"id": user_id, "email": email, "active": True}
        self.users[email] = user

        # 发送欢迎邮件
        self.email_service.send_welcome_email(user)

        return user


def test_register_user_sends_welcome_email():
    # Arrange
    email_service = Mock()
    service = UserService(email_service)

    # Act
    user = service.register_user("test@example.com", "password123")

    # Assert
    assert user["email"] == "test@example.com"
    assert user["active"] is True

    # 验证邮件发送
    email_service.send_welcome_email.assert_called_once()

    # 验证传递的用户数据
    call_args = email_service.send_welcome_email.call_args[0][0]
    assert call_args["email"] == "test@example.com"
    assert call_args["active"] is True


# ===================== 最佳实践示例 =====================

# 不要这样做 - 过度指定Mock行为
def test_bad_example_over_specified():
    db = Mock()
    db.query.return_value.filter.return_value.all.return_value = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]
    # 这种测试太脆弱，实现细节稍变就失败


# 更好的方式 - 关注行为而非实现
def test_good_example_behavior_focused():
    # 使用真实的内存数据库或测试替身
    test_db = InMemoryDatabase()
    test_db.add({"id": 1, "name": "Alice"})
    test_db.add({"id": 2, "name": "Bob"})

    # 直接从内存数据库获取，关注数据本身
    users = test_db.query().all()

    assert len(users) == 2
    assert users[0]["name"] == "Alice"


# 辅助类 - 内存数据库
class InMemoryDatabase:
    def __init__(self):
        self.data = []

    def add(self, item):
        self.data.append(item)

    def query(self):
        return QueryBuilder(self.data)


class QueryBuilder:
    def __init__(self, data):
        self.data = data

    def filter(self, criteria):
        # 简化实现
        return self

    def all(self):
        return self.data


# ===================== 运行测试 =====================

if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v"])

    print("\n✅ 所有示例测试通过！")
    print("\n💡 记住：")
    print("- Stub用于提供数据")
    print("- Mock用于验证行为")
    print("- 保持测试简单和可维护")
    print("- 不要过度Mock")
