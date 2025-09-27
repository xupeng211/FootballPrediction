"""
Auto-generated tests for src.utils.response module
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from src.utils.response import APIResponse, APIResponseModel


class TestAPIResponse:
    """测试API响应工具类"""

    # Success response tests
    def test_success_basic_response(self):
        """测试基本成功响应"""
        result = APIResponse.success()

        assert result["success"] is True
        assert result["message"] == "操作成功"
        assert "timestamp" in result
        assert "data" not in result

    def test_success_with_data(self):
        """测试带数据的成功响应"""
        test_data = {"key": "value", "items": [1, 2, 3]}
        result = APIResponse.success(test_data)

        assert result["success"] is True
        assert result["message"] == "操作成功"
        assert result["data"] == test_data
        assert "timestamp" in result

    def test_success_with_custom_message(self):
        """测试自定义消息的成功响应"""
        custom_message = "自定义成功消息"
        result = APIResponse.success(message=custom_message)

        assert result["success"] is True
        assert result["message"] == custom_message
        assert "timestamp" in result

    def test_success_with_data_and_custom_message(self):
        """测试带数据和自定义消息的成功响应"""
        test_data = {"id": 1, "name": "test"}
        custom_message = "数据获取成功"
        result = APIResponse.success(test_data, custom_message)

        assert result["success"] is True
        assert result["message"] == custom_message
        assert result["data"] == test_data
        assert "timestamp" in result

    @pytest.mark.parametrize("test_data", [
        None,
        {},
        [],
        {"key": "value"},
        [1, 2, 3],
        "string",
        123,
        True,
        False,
    ])
    def test_success_with_different_data_types(self, test_data):
        """测试不同数据类型的成功响应"""
        result = APIResponse.success(test_data)

        assert result["success"] is True
        if test_data is not None:
            assert result["data"] == test_data
        else:
            assert "data" not in result

    # Success response alias tests
    @patch('src.utils.response.datetime')
    def test_success_response_alias(self, mock_datetime):
        """测试成功响应别名方法"""
        fixed_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time

        test_data = {"test": "data"}
        result1 = APIResponse.success(test_data)
        result2 = APIResponse.success_response(test_data)

        assert result1 == result2
        assert result1["success"] is True
        assert result1["data"] == test_data

    # Error response tests
    def test_error_basic_response(self):
        """测试基本错误响应"""
        result = APIResponse.error()

        assert result["success"] is False
        assert result["message"] == "操作失败"
        assert result["code"] == 500  # 默认错误代码
        assert "timestamp" in result
        assert "data" not in result

    def test_error_with_custom_message(self):
        """测试自定义消息的错误响应"""
        custom_message = "自定义错误消息"
        result = APIResponse.error(custom_message)

        assert result["success"] is False
        assert result["message"] == custom_message
        assert result["code"] == 500
        assert "timestamp" in result

    def test_error_with_custom_code(self):
        """测试自定义错误代码的错误响应"""
        custom_code = 400
        result = APIResponse.error(code=custom_code)

        assert result["success"] is False
        assert result["code"] == custom_code
        assert "timestamp" in result

    def test_error_with_data(self):
        """测试带数据的错误响应"""
        error_data = {"field": "email", "error": "invalid_format"}
        result = APIResponse.error(data=error_data)

        assert result["success"] is False
        assert result["data"] == error_data
        assert "timestamp" in result

    def test_error_with_all_parameters(self):
        """测试带所有参数的错误响应"""
        message = "验证失败"
        code = 422
        data = {"errors": [{"field": "email", "message": "无效格式"}]}
        result = APIResponse.error(message, code, data)

        assert result["success"] is False
        assert result["message"] == message
        assert result["code"] == code
        assert result["data"] == data
        assert "timestamp" in result

    @pytest.mark.parametrize("code", [400, 401, 403, 404, 422, 500, None])
    def test_error_with_different_codes(self, code):
        """测试不同错误代码"""
        result = APIResponse.error(code=code)

        assert result["success"] is False
        if code is not None:
            assert result["code"] == code
        else:
            assert result["code"] == 500  # 默认值

    # Error response alias tests
    @patch('src.utils.response.datetime')
    def test_error_response_alias(self, mock_datetime):
        """测试错误响应别名方法"""
        fixed_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time

        message = "错误消息"
        code = 404
        data = {"details": "资源未找到"}
        result1 = APIResponse.error(message, code, data)
        result2 = APIResponse.error_response(message, code, data)

        assert result1 == result2
        assert result1["success"] is False
        assert result1["message"] == message
        assert result1["code"] == code
        assert result1["data"] == data

    # Timestamp tests
    @patch('src.utils.response.datetime')
    def test_success_response_timestamp(self, mock_datetime):
        """测试成功响应时间戳"""
        fixed_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time

        result = APIResponse.success()

        assert result["timestamp"] == "2023-01-01T12:00:00"

    @patch('src.utils.response.datetime')
    def test_error_response_timestamp(self, mock_datetime):
        """测试错误响应时间戳"""
        fixed_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time

        result = APIResponse.error()

        assert result["timestamp"] == "2023-01-01T12:00:00"

    def test_timestamp_format(self):
        """测试时间戳格式"""
        result1 = APIResponse.success()
        result2 = APIResponse.error()

        # 时间戳应该是有效的ISO格式
        for result in [result1, result2]:
            timestamp = result["timestamp"]
            assert isinstance(timestamp, str)
            assert "T" in timestamp
            assert datetime.fromisoformat(timestamp)

    # APIResponseModel tests
    def test_api_response_model_basic(self):
        """测试API响应模型基本功能"""
        model = APIResponseModel(
            success=True,
            message="测试消息"
        )

        assert model.success is True
        assert model.message == "测试消息"
        assert model.data is None
        assert model.code is None

    def test_api_response_model_with_data(self):
        """测试API响应模型带数据"""
        model = APIResponseModel(
            success=False,
            message="错误消息",
            data={"error": "validation"},
            code="VALIDATION_ERROR"
        )

        assert model.success is False
        assert model.message == "错误消息"
        assert model.data == {"error": "validation"}
        assert model.code == "VALIDATION_ERROR"

    def test_api_response_model_serialization(self):
        """测试API响应模型序列化"""
        model = APIResponseModel(
            success=True,
            message="成功",
            data={"id": 1},
            code="SUCCESS"
        )

        dict_result = model.model_dump()
        assert dict_result["success"] is True
        assert dict_result["message"] == "成功"
        assert dict_result["data"] == {"id": 1}
        assert dict_result["code"] == "SUCCESS"

    # Edge cases and integration tests
    def test_response_structure_consistency(self):
        """测试响应结构一致性"""
        success_response = APIResponse.success({"test": "data"})
        error_response = APIResponse.error("error message", 400)

        # 两个响应都应该有相同的基本结构
        for response in [success_response, error_response]:
            assert "success" in response
            assert "message" in response
            assert "timestamp" in response
            assert isinstance(response["success"], bool)
            assert isinstance(response["message"], str)
            assert isinstance(response["timestamp"], str)

    def test_response_immutability(self):
        """测试响应的不可变性"""
        response = APIResponse.success({"test": "data"})
        original_response = response.copy()

        # 修改响应不应该影响原始响应
        response["modified"] = True
        assert "modified" not in original_response

    def test_multiple_responses_different_timestamps(self):
        """测试多个响应有不同的时间戳"""
        response1 = APIResponse.success()
        response2 = APIResponse.error()

        # 两个响应应该有不同的时间戳（除非在极短时间内创建）
        timestamp1 = datetime.fromisoformat(response1["timestamp"])
        timestamp2 = datetime.fromisoformat(response2["timestamp"])

        # 允许微小的时间差异
        time_difference = abs((timestamp2 - timestamp1).total_seconds())
        assert time_difference < 1.0  # 1秒内的差异是可接受的

    def test_response_with_complex_data(self):
        """测试复杂数据结构的响应"""
        complex_data = {
            "users": [
                {"id": 1, "name": "Alice", "active": True},
                {"id": 2, "name": "Bob", "active": False}
            ],
            "pagination": {
                "page": 1,
                "per_page": 10,
                "total": 2
            }
        }

        result = APIResponse.success(complex_data)
        assert result["data"] == complex_data
        assert result["success"] is True

    def test_response_with_none_data_field(self):
        """测试显式传入None作为data"""
        result = APIResponse.success(None)
        assert "data" not in result

        result_with_none = APIResponse.error("error", data=None)
        assert "data" not in result_with_none