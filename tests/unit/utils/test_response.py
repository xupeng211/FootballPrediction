"""API响应工具类测试"""

import pytest
from datetime import datetime

from src.utils.response import APIResponse, APIResponseModel


class TestAPIResponseModel:
    """测试API响应Pydantic模型"""

    def test_model_creation(self):
        """测试模型创建"""
        model = APIResponseModel(
            success=True,
            message="操作成功",
            data={"id": 1},
            code="SUCCESS"
        )

        assert model.success is True
        assert model.message == "操作成功"
        assert model.data == {"id": 1}
        assert model.code == "SUCCESS"

    def test_model_minimal(self):
        """测试最小模型创建"""
        model = APIResponseModel(
            success=False,
            message="操作失败"
        )

        assert model.success is False
        assert model.message == "操作失败"
        assert model.data is None
        assert model.code is None

    def test_model_validation(self):
        """测试模型验证"""
        # success字段是必需的
        with pytest.raises(ValueError):
            APIResponseModel(message="test")  # 缺少success

        # message字段是必需的
        with pytest.raises(ValueError):
            APIResponseModel(success=True)  # 缺少message


class TestAPIResponse:
    """测试API响应工具类"""

    def test_success_without_data(self):
        """测试成功响应不带数据"""
        response = APIResponse.success()

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert "data" not in response
        assert "timestamp" in response
        assert "code" not in response

        # 验证时间戳格式
        datetime.fromisoformat(response["timestamp"])

    def test_success_with_data(self):
        """测试成功响应带数据"""
        data = {"id": 1, "name": "test"}
        response = APIResponse.success(data=data)

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert response["data"] == data
        assert "timestamp" in response

    def test_success_with_custom_message(self):
        """测试成功响应自定义消息"""
        response = APIResponse.success(message="自定义成功消息")

        assert response["success"] is True
        assert response["message"] == "自定义成功消息"

    def test_success_with_none_data(self):
        """测试成功响应数据为None"""
        response = APIResponse.success(data=None)

        assert response["success"] is True
        assert "data" not in response  # None值不应该包含

    def test_success_with_empty_data(self):
        """测试成功响应数据为空"""
        response = APIResponse.success(data={})

        assert response["success"] is True
        assert response["data"] == {}

    def test_success_response_alias(self):
        """测试成功响应别名方法"""
        data = {"test": "value"}
        response = APIResponse.success_response(data, "别名消息")

        assert response["success"] is True
        assert response["message"] == "别名消息"
        assert response["data"] == data

    def test_error_without_code_and_data(self):
        """测试错误响应不带代码和数据"""
        response = APIResponse.error()

        assert response["success"] is False
        assert response["message"] == "操作失败"
        assert response["code"] == 500  # 默认错误代码
        assert "data" not in response
        assert "timestamp" in response

    def test_error_with_code(self):
        """测试错误响应带代码"""
        response = APIResponse.error(message="资源未找到", code=404)

        assert response["success"] is False
        assert response["message"] == "资源未找到"
        assert response["code"] == 404
        assert "data" not in response

    def test_error_with_data(self):
        """测试错误响应带数据"""
        data = {"field": "email", "error": "邮箱格式错误"}
        response = APIResponse.error(
            message="验证失败",
            code=400,
            data=data
        )

        assert response["success"] is False
        assert response["message"] == "验证失败"
        assert response["code"] == 400
        assert response["data"] == data

    def test_error_with_none_data(self):
        """测试错误响应数据为None"""
        response = APIResponse.error(data=None)

        assert response["success"] is False
        assert "data" not in response  # None值不应该包含

    def test_error_with_zero_code(self):
        """测试错误响应代码为0"""
        response = APIResponse.error(code=0)

        assert response["code"] == 0

    def test_error_with_string_code(self):
        """测试错误响应代码为字符串"""
        response = APIResponse.error(code="INVALID_INPUT")

        assert response["code"] == "INVALID_INPUT"

    def test_error_response_alias(self):
        """测试错误响应别名方法"""
        response = APIResponse.error_response(
            message="别名错误",
            code=403,
            data={"permission": "denied"}
        )

        assert response["success"] is False
        assert response["message"] == "别名错误"
        assert response["code"] == 403
        assert response["data"] == {"permission": "denied"}

    def test_response_structure(self):
        """测试响应结构"""
        # 测试成功响应结构
        success_resp = APIResponse.success({"test": "data"})
        required_keys = {"success", "message", "timestamp"}
        optional_keys = {"data", "code"}

        assert all(key in success_resp for key in required_keys)
        assert all(key in optional_keys for key in success_resp.keys() if key not in required_keys)

        # 测试错误响应结构
        error_resp = APIResponse.error(code=500)
        assert all(key in error_resp for key in required_keys)
        assert "code" in error_resp

    def test_timestamp_format(self):
        """测试时间戳格式"""
        response = APIResponse.success()
        timestamp_str = response["timestamp"]

        # 验证可以解析为datetime
        parsed_time = datetime.fromisoformat(timestamp_str)
        assert isinstance(parsed_time, datetime)

        # 验证时间是最近的（1秒内）
        now = datetime.now()
        assert abs((parsed_time - now).total_seconds()) < 1

    def test_data_types(self):
        """测试不同类型的数据"""
        test_cases = [
            {"key": "value"},  # 字典
            [1, 2, 3],  # 列表
            "string",  # 字符串
            123,  # 数字
            True,  # 布尔值
            None,  # None值
            {"nested": {"deeply": {"structured": "data"}}},  # 嵌套结构
        ]

        for data in test_cases:
            response = APIResponse.success(data=data)
            if data is not None:
                assert response["data"] == data
            else:
                # 对于None，data不应该包含在响应中
                assert "data" not in response

    def test_message_formats(self):
        """测试不同的消息格式"""
        messages = [
            "简单消息",
            "Message with special chars: 中文, ñ, é, ü",
            "",  # 空消息
            "Very long message " * 100,  # 长消息
            "Message\nwith\nnewlines",  # 带换行符
            "Message\twith\ttabs",  # 带制表符
        ]

        for msg in messages:
            response = APIResponse.success(message=msg)
            assert response["message"] == msg

    def test_error_code_types(self):
        """测试不同类型的错误代码"""
        error_codes = [
            400,  # 整数
            "NOT_FOUND",  # 字符串
            "4.0.1",  # 版本号字符串
            0,  # 零
            -1,  # 负数
        ]

        for code in error_codes:
            response = APIResponse.error(code=code)
            assert response["code"] == code

    def test_chinese_messages(self):
        """测试中文消息"""
        response = APIResponse.success(message="操作成功")
        assert response["message"] == "操作成功"

        response = APIResponse.error(message="服务器内部错误")
        assert response["message"] == "服务器内部错误"

    def test_empty_response(self):
        """测试空响应"""
        # 最小成功响应
        success = APIResponse.success()
        assert len(success) == 3  # success, message, timestamp

        # 最小错误响应
        error = APIResponse.error()
        assert len(error) == 4  # success, message, timestamp, code