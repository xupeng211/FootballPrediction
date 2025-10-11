"""API响应工具简单测试"""

# from src.utils.response import APIResponse


class TestResponseSimple:
    """API响应工具简单测试"""

    def test_success_without_data(self):
        """测试成功响应（无数据）"""
        response = APIResponse.success()
        assert response["success"] is True
        assert "timestamp" in response
        assert response["message"] == "操作成功"

    def test_success_with_data(self):
        """测试成功响应（带数据）"""
        data = {"test": "value"}
        response = APIResponse.success(data=data)
        assert response["success"] is True
        assert response["data"] == data
        assert "timestamp" in response

    def test_success_with_message(self):
        """测试成功响应（自定义消息）"""
        message = "自定义成功消息"
        response = APIResponse.success(message=message)
        assert response["success"] is True
        assert response["message"] == message
        assert "timestamp" in response

    def test_success_response_alias(self):
        """测试成功响应别名方法"""
        data = {"test": "data"}
        response = APIResponse.success_response(data=data)
        assert response["success"] is True
        assert response["data"] == data
        assert "timestamp" in response

    def test_error_response(self):
        """测试错误响应"""
        response = APIResponse.error("测试错误")
        assert response["success"] is False
        assert response["error"] == "测试错误"
        assert "timestamp" in response

    def test_error_with_details(self):
        """测试错误响应（带详细信息）"""
        details = {"field": "email", "issue": "格式错误"}
        response = APIResponse.error("验证失败", details=details)
        assert response["success"] is False
        assert response["error"] == "验证失败"
        assert response["details"] == details
        assert "timestamp" in response

    def test_error_with_code(self):
        """测试错误响应（带错误码）"""
        response = APIResponse.error("业务错误", error_code="BUSINESS_ERROR")
        assert response["success"] is False
        assert response["error"] == "业务错误"
        assert response["error_code"] == "BUSINESS_ERROR"
        assert "timestamp" in response

    def test_timestamp_format(self):
        """测试时间戳格式"""
        response = APIResponse.success()
        timestamp = response["timestamp"]
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO格式

    def test_complex_data_structure(self):
        """测试复杂数据结构"""
        data = {
            "user": {
                "id": 1,
                "profile": {"name": "测试用户", "settings": {"theme": "dark"}},
            },
            "items": [1, 2, 3],
        }
        response = APIResponse.success(data=data)
        assert response["success"] is True
        assert response["data"]["user"]["profile"]["name"] == "测试用户"
        assert len(response["data"]["items"]) == 3
