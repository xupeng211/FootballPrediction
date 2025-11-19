from typing import Optional

"""
Response模块增强测试 - 快速提升覆盖率
测试APIResponseModel和APIResponse类的所有方法
"""

import re

from src.utils.response import APIResponse, APIResponseModel, ResponseUtils


class TestAPIResponseModel:
    """API响应模型测试"""

    def test_model_creation_basic(self):
        """测试基本模型创建"""
        model = APIResponseModel(
            success=True, message="操作成功", data={"id": 1}, code="200"
        )

        assert model.success is True
        assert model.message == "操作成功"
        assert model.data == {"id": 1}
        assert model.code == "200"

    def test_model_creation_minimal(self):
        """测试最小参数模型创建"""
        model = APIResponseModel(success=False, message="错误")

        assert model.success is False
        assert model.message == "错误"
        assert model.data is None
        assert model.code is None

    def test_model_with_various_data_types(self):
        """测试各种数据类型的模型创建"""
        # 测试字典数据
        model_dict = APIResponseModel(
            success=True, message="字典数据", data={"key": "value", "number": 42}
        )
        assert model_dict.data["key"] == "value"

        # 测试列表数据
        model_list = APIResponseModel(
            success=True, message="列表数据", data=[1, 2, 3, "four"]
        )
        assert len(model_list.data) == 4

        # 测试字符串数据
        model_str = APIResponseModel(
            success=True, message="字符串数据", data="Hello World"
        )
        assert model_str.data == "Hello World"

        # 测试数字数据
        model_num = APIResponseModel(success=True, message="数字数据", data=123.45)
        assert model_num.data == 123.45


class TestAPIResponseEnhanced:
    """API响应工具增强测试"""

    def test_success_basic(self):
        """测试基本成功响应"""
        response = APIResponse.success()

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert "timestamp" in response
        assert "data" not in response

        # 验证时间戳格式
        timestamp = response["timestamp"]
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", timestamp)

    def test_success_with_data(self):
        """测试带数据的成功响应"""
        test_data = {"user_id": 123, "name": "张三"}
        response = APIResponse.success(data=test_data, message="用户信息获取成功")

        assert response["success"] is True
        assert response["message"] == "用户信息获取成功"
        assert response["data"] == test_data
        assert "timestamp" in response

    def test_success_with_none_data(self):
        """测试显式传入None数据的成功响应"""
        response = APIResponse.success(data=None, message="无数据响应")

        assert response["success"] is True
        assert response["message"] == "无数据响应"
        assert "data" not in response  # None值应该被忽略

    def test_success_response_alias(self):
        """测试成功响应别名方法"""
        test_data = {"result": "success"}
        response1 = APIResponse.success(data=test_data)
        response2 = APIResponse.success_response(data=test_data)

        # 两个方法应该产生相同的结果
        assert response1["success"] == response2["success"]
        assert response1["message"] == response2["message"]
        assert response1["data"] == response2["data"]

    def test_success_various_data_types(self):
        """测试各种数据类型的成功响应"""
        # 测试字符串数据
        response_str = APIResponse.success(data="Hello", message="字符串响应")
        assert response_str["data"] == "Hello"

        # 测试数字数据
        response_num = APIResponse.success(data=42, message="数字响应")
        assert response_num["data"] == 42

        # 测试列表数据
        response_list = APIResponse.success(data=[1, 2, 3], message="列表响应")
        assert response_list["data"] == [1, 2, 3]

        # 测试布尔数据
        response_bool = APIResponse.success(data=True, message="布尔响应")
        assert response_bool["data"] is True

    def test_error_basic(self):
        """测试基本错误响应"""
        response = APIResponse.error()

        assert response["success"] is False
        assert response["message"] == "操作失败"
        assert response["code"] == 500  # 默认错误代码
        assert "timestamp" in response
        assert "data" not in response

    def test_error_with_custom_message_and_code(self):
        """测试自定义消息和代码的错误响应"""
        response = APIResponse.error(message="用户不存在", code=404)

        assert response["success"] is False
        assert response["message"] == "用户不存在"
        assert response["code"] == 404
        assert "timestamp" in response

    def test_error_with_data(self):
        """测试带数据的错误响应"""
        error_data = {"field": "email", "reason": "格式不正确"}
        response = APIResponse.error(message="验证失败", code=400, data=error_data)

        assert response["success"] is False
        assert response["message"] == "验证失败"
        assert response["code"] == 400
        assert response["data"] == error_data

    def test_error_response_alias(self):
        """测试错误响应别名方法"""
        error_data = {"detail": "权限不足"}
        response1 = APIResponse.error(message="权限错误", code=403, data=error_data)
        response2 = APIResponse.error_response(
            message="权限错误", code=403, data=error_data
        )

        # 两个方法应该产生相同的结果
        assert response1["success"] == response2["success"]
        assert response1["message"] == response2["message"]
        assert response1["code"] == response2["code"]
        assert response1["data"] == response2["data"]

    def test_error_with_none_data(self):
        """测试显式传入None数据的错误响应"""
        response = APIResponse.error(data=None)

        assert response["success"] is False
        assert response["code"] == 500
        assert "data" not in response  # None值应该被忽略

    def test_error_various_codes(self):
        """测试各种错误代码"""
        codes_to_test = [400, 401, 403, 404, 500, 502, 503]

        for code in codes_to_test:
            response = APIResponse.error(message=f"错误 {code}", code=code)
            assert response["code"] == code
            assert response["success"] is False

    def test_response_consistency(self):
        """测试响应格式一致性"""
        success_resp = APIResponse.success(data={"test": True})
        error_resp = APIResponse.error(message="测试错误")

        # 两种响应都应该包含相同的基础字段
        for resp in [success_resp, error_resp]:
            assert "success" in resp
            assert "message" in resp
            assert "timestamp" in resp
            assert isinstance(resp["success"], bool)
            assert isinstance(resp["message"], str)

        # 时间戳格式应该一致
        success_timestamp = success_resp["timestamp"]
        error_timestamp = error_resp["timestamp"]
        assert isinstance(success_timestamp, str)
        assert isinstance(error_timestamp, str)
        assert len(success_timestamp) > 0
        assert len(error_timestamp) > 0

    def test_response_utils_alias(self):
        """测试ResponseUtils别名"""
        # ResponseUtils应该是APIResponse的别名
        assert ResponseUtils is APIResponse

        # 使用别名应该产生相同结果
        data = {"alias_test": True}
        resp1 = APIResponse.success(data=data)
        resp2 = ResponseUtils.success(data=data)

        assert resp1["success"] == resp2["success"]
        assert resp1["data"] == resp2["data"]
        assert resp1["message"] == resp2["message"]

    def test_real_world_scenarios(self):
        """测试真实世界场景"""
        # 场景1: 用户登录成功
        login_data = {"user_id": 123, "token": "abc123", "expires_in": 3600}
        login_response = APIResponse.success(data=login_data, message="登录成功")

        assert login_response["success"] is True
        assert login_response["data"]["user_id"] == 123

        # 场景2: 数据验证失败
        validation_errors = [
            {"field": "email", "message": "邮箱格式不正确"},
            {"field": "password", "message": "密码长度不能少于8位"},
        ]
        validation_response = APIResponse.error(
            message="数据验证失败", code=422, data=validation_errors
        )

        assert validation_response["success"] is False
        assert validation_response["code"] == 422
        assert len(validation_response["data"]) == 2

        # 场景3: 数据查询结果为空
        empty_response = APIResponse.success(data=[], message="查询成功，无数据")

        assert empty_response["success"] is True
        assert empty_response["data"] == []

        # 场景4: 系统内部错误
        system_error_response = APIResponse.error(
            message="系统内部错误，请联系管理员", code=500, data={"error_id": "ERR_001"}
        )

        assert system_error_response["success"] is False
        assert system_error_response["code"] == 500
        assert system_error_response["data"]["error_id"] == "ERR_001"

    def test_timestamp_generation(self):
        """测试时间戳生成"""
        # 连续创建多个响应，确保时间戳不同
        responses = []
        for i in range(5):
            response = APIResponse.success(data={"iteration": i})
            responses.append(response)

        # 所有响应都应该有时间戳
        for resp in responses:
            assert "timestamp" in resp
            assert isinstance(resp["timestamp"], str)
            assert len(resp["timestamp"]) > 0

        # 时间戳应该各不相同（至少大部分）
        timestamps = [resp["timestamp"] for resp in responses]
        unique_timestamps = set(timestamps)
        # 允许少数重复（理论上很少见）
        assert len(unique_timestamps) >= 3
