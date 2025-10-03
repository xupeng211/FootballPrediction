from datetime import datetime

from pydantic import ValidationError
from src.utils.response import APIResponseModel, APIResponse
from unittest.mock import patch
import pytest
import os

"""
API响应工具类测试套件

覆盖src/utils/response.py的所有功能：
- APIResponseModel
- APIResponse

目标：实现100%覆盖率
"""

class TestAPIResponseModel:
    """APIResponseModel测试类"""
    def test_api_response_model_creation_success(self):
        """测试成功创建APIResponseModel"""
        model = APIResponseModel(success = True, message="操作成功[", data={"]result[": "]test["), code = os.getenv("TEST_RESPONSE_CODE_22")""""
        )
        assert model.success is True
        assert model.message =="]操作成功[" assert model.data =={"]result[" ["]test["}" assert model.code =="]SUCCESS[" def test_api_response_model_minimal("
    """"
        "]""测试最小APIResponseModel创建"""
        model = APIResponseModel(success=True, message="操作成功[")": assert model.success is True[" assert model.message =="]]操作成功[" assert model.data is None[""""
        assert model.code is None
    def test_api_response_model_validation_required_fields(self):
        "]]""测试必填字段验证"""
        # 缺少success字段
        with pytest.raises(ValidationError) as exc_info:
            APIResponseModel(message="操作成功[")": assert "]success[" in str(exc_info.value)""""
        # 缺少message字段
        with pytest.raises(ValidationError) as exc_info:
            APIResponseModel(success=True)
        assert "]message[" in str(exc_info.value)""""
    def test_api_response_model_field_types(self):
        "]""测试字段类型验证"""
        # 错误的success类型
        with pytest.raises(ValidationError):
            APIResponseModel(success="true[", message = os.getenv("TEST_RESPONSE_MESSAGE_43"))""""
        # 错误的message类型
        with pytest.raises(ValidationError):
            APIResponseModel(success=True, message=123)
        # 正确的data类型（可以是任何类型）
        model = APIResponseModel(success = True, message = os.getenv("TEST_RESPONSE_MESSAGE_43"), data={"]key[": "]value[")""""
        )
        assert model.data =={"]key[" "]value["}" def test_api_response_model_various_data_types(self):"""
        "]""测试不同的数据类型"""
        test_cases = [
            ({"key[: "value""}, "dict]),""""
            ([1, 2, 3], "list["),""""
            ("]string[", "]str["),""""
            (123, "]int["),""""
            (123.45, "]float["),""""
            (True, "]bool["),""""
            (None, "]None[")]": for data, data_type in test_cases = model APIResponseModel(success=True, message=f["]测试{data_type)"], data=data[""""
            )
            assert model.data ==data
    def test_api_response_model_serialization(self):
        "]""测试模型序列化"""
        model = APIResponseModel(success = True, message="操作成功[", data={"]result[": "]test["), code = os.getenv("TEST_RESPONSE_CODE_22")""""
        )
        # 转换为字典
        model_dict = model.model_dump()
        assert model_dict["]success["] is True[" assert model_dict["]]message["] =="]操作成功[" assert model_dict["]data["] =={"]result[" "]test["}" assert model_dict["]code["] =="]SUCCESS["""""
        # 转换为JSON
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        assert "]success[" in json_str[""""
        assert "]]操作成功[" in json_str[""""
class TestAPIResponse:
    "]]""APIResponse测试类"""
    @pytest.fixture
    def freeze_datetime(self):
        """冻结时间用于测试"""
        frozen_datetime = datetime(2025, 9, 29, 15, 0, 0)
        with patch("src.utils.response.datetime[") as mock_datetime:": mock_datetime.now.return_value = frozen_datetime[": yield frozen_datetime[": def test_success_response_minimal(self, freeze_datetime):"
        "]]]""测试最小成功响应"""
        response = APIResponse.success()
        expected = {
            "success[": True,""""
            "]message[: "操作成功[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_success_response_with_data(self, freeze_datetime):""
        "]]""测试带数据的成功响应"""
        data = {"result[: "test"", "count]: 10}": response = APIResponse.success(data=data)": expected = {""
            "success[": True,""""
            "]message[: "操作成功[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_success_response_with_custom_message(self, freeze_datetime):""
        "]]""测试自定义消息的成功响应"""
        response = APIResponse.success(message = os.getenv("TEST_RESPONSE_MESSAGE_91"))": expected = {"""
            "]success[": True,""""
            "]message[: "自定义成功消息[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_success_response_with_data_and_message(self, freeze_datetime):""
        "]]""测试带数据和自定义消息的成功响应"""
        data = {"users[": 100}": message = os.getenv("TEST_RESPONSE_MESSAGE_96"): response = APIResponse.success(data=data, message=message)": expected = {"""
            "]success[": True,""""
            "]message[": message,""""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_success_response_with_none_data(self, freeze_datetime):""
        "]]""测试显式传入None数据"""
        response = APIResponse.success(data=None)
        expected = {
            "success[": True,""""
            "]message[: "操作成功[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected["""
        # 确保没有data字段
        assert "]]data[" not in response[""""
    def test_success_response_alias_method(self, freeze_datetime):
        "]]""测试成功响应别名方法"""
        data = {"result[: "alias test["}"]": response = APIResponse.success_response(data=data, message = os.getenv("TEST_RESPONSE_MESSAGE_110"))": expected = {"""
            "]success[": True,""""
            "]message[: "别名方法测试[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_error_response_minimal(self, freeze_datetime):""
        "]]""测试最小错误响应"""
        response = APIResponse.error()
        expected = {
            "success[": False,""""
            "]message[: "操作失败[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_error_response_with_custom_code(self, freeze_datetime):""
        "]]""测试自定义错误代码"""
        response = APIResponse.error(message="未找到[", code=404)": expected = {"""
            "]success[": False,""""
            "]message[: "未找到[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_error_response_with_data(self, freeze_datetime):""
        "]]""测试带数据的错误响应"""
        data = {"field[: "email"", "error]}": response = APIResponse.error(message="验证失败[", code=400, data=data)": expected = {"""
            "]success[": False,""""
            "]message[: "验证失败[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_error_response_with_zero_code(self, freeze_datetime):""
        "]]""测试0错误代码"""
        response = APIResponse.error(message="错误[", code=0)": expected = {"""
            "]success[": False,""""
            "]message[: "错误[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_error_response_with_negative_code(self, freeze_datetime):""
        "]]""测试负错误代码"""
        response = APIResponse.error(message="错误[", code=-1)": expected = {"""
            "]success[": False,""""
            "]message[: "错误[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_error_response_with_none_code(self, freeze_datetime):""
        "]]""测试None错误代码"""
        response = APIResponse.error(message="错误[", code=None)": expected = {"""
            "]success[": False,""""
            "]message[: "错误[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_error_response_with_none_data(self, freeze_datetime):""
        "]]""测试显式传入None数据"""
        response = APIResponse.error(message="错误[", code=400, data=None)": expected = {"""
            "]success[": False,""""
            "]message[: "错误[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected["""
        # 确保没有data字段
        assert "]]data[" not in response[""""
    def test_error_response_alias_method(self, freeze_datetime):
        "]]""测试错误响应别名方法"""
        data = {"details[: "参数错误["}"]": response = APIResponse.error_response(": message = os.getenv("TEST_RESPONSE_MESSAGE_153"), code=422, data=data[""""
        )
        expected = {
            "]]success[": False,""""
            "]message[: "别名方法错误[","]"""
            "]timestamp[": freeze_datetime.isoformat()": assert response ==expected[" def test_response_structure_consistency(self, freeze_datetime):""
        "]]""测试响应结构一致性"""
        # 测试成功响应结构
        success_response = APIResponse.success(data={"test[": ["]data["))": assert "]success[" in success_response[""""
        assert "]]message[" in success_response[""""
        assert "]]timestamp[" in success_response[""""
        assert success_response["]]success["] is True[""""
        # 测试错误响应结构
        error_response = APIResponse.error(message="]]错误[", code=400)": assert "]success[" in error_response[""""
        assert "]]message[" in error_response[""""
        assert "]]timestamp[" in error_response[""""
        assert "]]code[" in error_response[""""
        assert error_response["]]success["] is False[""""
class TestAPIResponseEdgeCases:
    "]]""APIResponse边界情况测试"""
    def test_response_with_empty_data(self, freeze_datetime):
        """测试空数据响应"""
        # 空字典
        response1 = APIResponse.success(data={))
        assert response1["data["] =={}"]"""
        # 空列表
        response2 = APIResponse.success(data=[])
        assert response2["data["] ==[]"]"""
        # 空字符串
        response3 = APIResponse.success(data=: )
        assert response3["data["] =="]"""""
    def test_response_with_complex_data(self, freeze_datetime):
        """测试复杂数据结构"""
        complex_data = {
            "users[": [""""
                {"]id[": 1, "]name[": "]User1[", "]active[": True},""""
                {"]id[": 2, "]name[": "]User2[", "]active[": False}],""""
            "]metadata[": {""""
                "]total[": 2,""""
                "]page[": 1,""""
                "]per_page[": 10,""""
                "]filters[": {"]status[": "]active["}},""""
            "]stats[": {"]count[": 2, "]average[": 85.5, "]percentiles[: "25, 50, 75, 95["}}"]": response = APIResponse.success(data=complex_data)": assert response["]data["] ==complex_data[" def test_response_with_special_characters(self, freeze_datetime):"""
        "]]""测试特殊字符"""
        response = APIResponse.success(
            data = {"message: 特殊字符: !@#$%^&*()_+-=[]{}|;'\",./<>? 🚀"},": message = os.getenv("TEST_RESPONSE_MESSAGE_198"))": assert ("""
            "]特殊字符: !@#$%^&*()_+-=[]{}|;':\",./<>? 🚀": in response["data["]"]message["""""
        )
        assert "]测试特殊字符[" in response["]message["]: def test_response_with_unicode("
    """"
        "]""测试Unicode字符"""
        response = APIResponse.success(data = {"text[": [中文 español 日本語 한국語["]), message = os.getenv("TEST_RESPONSE_MESSAGE_202")"""
        )
        assert response["data["]"]text[" =="]中文 español 日本語 한국語[" assert response["]message["] =="]Unicode测试[" def test_response_with_very_long_message("
    """"
        "]""测试超长消息"""
        long_message = "x[" * 10000  # 10000个字符[": response = APIResponse.success(message=long_message)": assert response["]]message["] ==long_message[" def test_response_with_nested_data(self, freeze_datetime):"""
        "]]""测试嵌套数据结构"""
        nested_data = {"level1[": {"]level2[": {"]level3[": {"]deep_value[": "]found["}}}}": response = APIResponse.success(data=nested_data)": assert response["]data["]"]level1""level2""level3""deep_value[" =="]found[" def test_response_error_codes_range("
    """"
        "]""测试错误代码范围"""
        # 测试各种HTTP状态码
        error_codes = [400, 401, 403, 404, 405, 500, 502, 503, 504]
        for code in error_codes = response APIResponse.error(code=code, message=f["Error {code)"])": assert response["code["] ==code["]"]" assert response["success["] is False["]"]" def test_response_timestamp_format(self, freeze_datetime):"
        """测试时间戳格式"""
        response = APIResponse.success()
        # 验证时间戳格式是ISO格式
        timestamp = response["timestamp["]"]": assert "T[" in timestamp[""""
        assert isinstance(timestamp, str)
        # 可以解析回datetime
        parsed_dt = datetime.fromisoformat(timestamp)
        assert parsed_dt ==freeze_datetime
class TestAPIResponseIntegration:
    "]]""APIResponse集成测试"""
    def test_model_and_response_compatibility(self):
        """测试模型与响应工具的兼容性"""
        # 使用APIResponse工具创建响应
        response_dict = APIResponse.success(data={"result[": [test["]), message="]成功])""""
        # 使用APIResponseModel验证响应
        model = APIResponseModel(
            success=response_dict["success["],"]": message=response_dict["message["],"]": data=response_dict.get("data["))": assert model.success is True[" assert model.message =="]]成功[" assert model.data =={"]result[" "]test["}" def test_multiple_responses_consistency(self):"""
        "]""测试多个响应的一致性"""
        responses = []
        # 创建多个响应
        for i in range(5):
            response = APIResponse.success(data={"id[": i))": responses.append(response)"""
        # 验证结构一致性
        keys = ["]success[", "]message[", "]timestamp["]": for response in responses:": for key in keys:": assert key in response"
            assert response["]success["] is True[" def test_response_immutability(self):"""
        "]]""测试响应不可变性"""
        response = APIResponse.success(data={"original[": ["]value["))""""
        # 修改原始数据不应该影响响应
        original_data = {"]original[": ["]value["}": response = APIResponse.success(data=original_data)": original_data["]modified["] = "]changed[": assert "]modified[" not in response["]data["]: def test_response_return_type("
    """"
        "]""测试响应返回类型"""
        response = APIResponse.success()
        # 应该返回字典
        assert isinstance(response, dict)
        assert isinstance(response["success["], bool)"]" assert isinstance(response["message["], str)"]" assert isinstance(response["timestamp["], str)"]" def test_response_methods_existence(self):""
        """测试响应方法存在性"""
        # 验证所有静态方法都存在
        assert hasattr(APIResponse, "success[")" assert hasattr(APIResponse, "]success_response[")" assert hasattr(APIResponse, "]error[")" assert hasattr(APIResponse, "]error_response[")""""
        # 验证方法可调用
        assert callable(getattr(APIResponse, "]success["))" assert callable(getattr(APIResponse, "]success_response["))" assert callable(getattr(APIResponse, "]error["))" assert callable(getattr(APIResponse, "]error_response["))" if __name__ =="]__main__[": pytest.main(""""
        ["]__file__[", "]-v[", "]--cov=src.utils.response[", "]--cov-report=term-missing["]"]"""
    )