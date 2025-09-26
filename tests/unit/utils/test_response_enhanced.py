"""
Enhanced test file for response.py utility module
Provides comprehensive coverage for API response formatting functionality
"""

import pytest
from datetime import datetime
from typing import Any, Dict
from unittest.mock import patch, Mock

# Import directly to avoid NumPy reload issues
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from utils.response import APIResponse, APIResponseModel


class TestAPIResponseModel:
    """Test APIResponseModel Pydantic model"""

    def test_model_creation_success(self):
        """Test successful model creation with all fields"""
        model = APIResponseModel(
            success=True,
            message="操作成功",
            data={"key": "value"},
            code="200"
        )
        assert model.success is True
        assert model.message == "操作成功"
        assert model.data == {"key": "value"}
        assert model.code == "200"

    def test_model_creation_minimal(self):
        """Test model creation with minimal required fields"""
        model = APIResponseModel(
            success=False,
            message="操作失败"
        )
        assert model.success is False
        assert model.message == "操作失败"
        assert model.data is None
        assert model.code is None

    def test_model_validation(self):
        """Test Pydantic model validation"""
        # Valid model
        model_data = {
            "success": True,
            "message": "test",
            "data": {"test": "data"},
            "code": "200"
        }
        model = APIResponseModel(**model_data)
        assert model.success is True

        # Invalid model should raise ValidationError
        with pytest.raises(ValueError):
            APIResponseModel(
                success="not_boolean",  # Should be boolean
                message="test"
            )


class TestAPIResponse:
    """Test APIResponse utility class"""

    def test_success_response_basic(self):
        """Test basic success response"""
        result = APIResponse.success()

        assert result["success"] is True
        assert result["message"] == "操作成功"
        assert "timestamp" in result
        assert "data" not in result
        assert "code" not in result

    def test_success_response_with_data(self):
        """Test success response with data"""
        test_data = {"users": ["user1", "user2"], "count": 2}
        result = APIResponse.success(data=test_data)

        assert result["success"] is True
        assert result["message"] == "操作成功"
        assert result["data"] == test_data
        assert "timestamp" in result

    def test_success_response_with_custom_message(self):
        """Test success response with custom message"""
        result = APIResponse.success(data={"test": "data"}, message="自定义成功消息")

        assert result["success"] is True
        assert result["message"] == "自定义成功消息"
        assert result["data"] == {"test": "data"}

    def test_success_response_with_none_data(self):
        """Test success response with None data"""
        result = APIResponse.success(data=None)

        assert result["success"] is True
        assert "data" not in result

    def test_success_response_with_empty_data(self):
        """Test success response with empty data"""
        result = APIResponse.success(data={})

        assert result["success"] is True
        assert result["data"] == {}

    def test_success_response_alias_method(self):
        """Test success_response alias method"""
        test_data = {"test": "value"}
        result1 = APIResponse.success(data=test_data)
        result2 = APIResponse.success_response(data=test_data)

        assert result1 == result2

    def test_error_response_basic(self):
        """Test basic error response"""
        result = APIResponse.error()

        assert result["success"] is False
        assert result["message"] == "操作失败"
        assert result["code"] == 500
        assert "timestamp" in result
        assert "data" not in result

    def test_error_response_with_custom_message(self):
        """Test error response with custom message"""
        result = APIResponse.error(message="自定义错误消息")

        assert result["success"] is False
        assert result["message"] == "自定义错误消息"
        assert result["code"] == 500

    def test_error_response_with_custom_code(self):
        """Test error response with custom code"""
        result = APIResponse.error(message="Not Found", code=404)

        assert result["success"] is False
        assert result["message"] == "Not Found"
        assert result["code"] == 404

    def test_error_response_with_data(self):
        """Test error response with additional data"""
        error_data = {"field": "username", "error": "required"}
        result = APIResponse.error(
            message="验证失败",
            code=400,
            data=error_data
        )

        assert result["success"] is False
        assert result["message"] == "验证失败"
        assert result["code"] == 400
        assert result["data"] == error_data

    def test_error_response_with_none_data(self):
        """Test error response with None data"""
        result = APIResponse.error(data=None)

        assert result["success"] is False
        assert "data" not in result

    def test_error_response_with_empty_data(self):
        """Test error response with empty data"""
        result = APIResponse.error(data={})

        assert result["success"] is False
        assert result["data"] == {}

    def test_error_response_zero_code(self):
        """Test error response with zero code"""
        result = APIResponse.error(code=0)

        assert result["success"] is False
        assert result["code"] == 0

    def test_error_response_string_code(self):
        """Test error response with string code"""
        result = APIResponse.error(code="INVALID_INPUT")

        assert result["success"] is False
        assert result["code"] == "INVALID_INPUT"

    def test_error_response_alias_method(self):
        """Test error_response alias method"""
        result1 = APIResponse.error(message="test", code=400)
        result2 = APIResponse.error_response(message="test", code=400)

        assert result1 == result2

    @patch('utils.response.datetime')
    def test_timestamp_format(self, mock_datetime):
        """Test timestamp format in responses"""
        # Mock datetime to return consistent timestamp
        mock_now = Mock()
        mock_now.isoformat.return_value = "2023-01-01T12:00:00"
        mock_datetime.now.return_value = mock_now

        # Test success response
        success_result = APIResponse.success()
        assert success_result["timestamp"] == "2023-01-01T12:00:00"

        # Test error response
        error_result = APIResponse.error()
        assert error_result["timestamp"] == "2023-01-01T12:00:00"

    def test_response_structure_consistency(self):
        """Test that response structure is consistent"""
        success_data = {"items": [1, 2, 3]}
        error_data = {"details": "Something went wrong"}

        success_response = APIResponse.success(data=success_data, message="Success")
        error_response = APIResponse.error(message="Error", code=400, data=error_data)

        # Both should have the same basic structure
        assert "success" in success_response
        assert "success" in error_response
        assert "message" in success_response
        assert "message" in error_response
        assert "timestamp" in success_response
        assert "timestamp" in error_response

    def test_response_immutability(self):
        """Test that responses are proper dictionaries"""
        response = APIResponse.success(data={"test": "value"})

        # Should be a dict
        assert isinstance(response, dict)

        # Should have expected keys
        expected_keys = {"success", "message", "timestamp", "data"}
        assert set(response.keys()) == expected_keys

    def test_large_data_handling(self):
        """Test handling of large data objects"""
        large_data = {"items": list(range(1000))}
        response = APIResponse.success(data=large_data)

        assert response["success"] is True
        assert response["data"] == large_data
        assert len(response["data"]["items"]) == 1000

    def test_special_characters_in_message(self):
        """Test handling of special characters in messages"""
        special_messages = [
            "消息包含中文",
            "Message with émojis 🎉",
            "Message\nwith\nnewlines",
            "Message\twith\ttabs",
            "Message with 'quotes'",
            'Message with "double quotes"',
            "Message with <html>&entities</html>"
        ]

        for message in special_messages:
            response = APIResponse.success(message=message)
            assert response["message"] == message

    def test_numeric_data_types(self):
        """Test handling of various numeric data types"""
        test_cases = [
            ({"integer": 42}, "Integer"),
            ({"float": 3.14159}, "Float"),
            ({"negative": -123}, "Negative integer"),
            ({"zero": 0}, "Zero"),
            ({"scientific": 1.23e-4}, "Scientific notation")
        ]

        for data, description in test_cases:
            response = APIResponse.success(data=data)
            assert response["data"] == data, f"Failed for {description}"

    def test_boolean_data_types(self):
        """Test handling of boolean data types"""
        response = APIResponse.success(data={"flag": True, "disabled": False})
        assert response["data"]["flag"] is True
        assert response["data"]["disabled"] is False

    def test_none_values_in_data(self):
        """Test handling of None values in data"""
        data_with_nones = {
            "value": None,
            "nested": {"inner": None},
            "list": [1, None, 3]
        }
        response = APIResponse.success(data=data_with_nones)
        assert response["data"] == data_with_nones

    def test_empty_collections_in_data(self):
        """Test handling of empty collections in data"""
        empty_collections = {
            "empty_list": [],
            "empty_dict": {},
            "empty_string": "",
            "zero": 0,
            "false": False
        }
        response = APIResponse.success(data=empty_collections)
        assert response["data"] == empty_collections


class TestAPIResponseEdgeCases:
    """Test edge cases and error scenarios"""

    def test_unicode_data(self):
        """Test handling of Unicode data"""
        unicode_data = {
            "chinese": "中文测试",
            "emoji": "🎉✨🚀",
            "special": "特殊字符: ©®™"
        }
        response = APIResponse.success(data=unicode_data)
        assert response["data"] == unicode_data

    def test_nested_data_structures(self):
        """Test handling of deeply nested data structures"""
        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep",
                        "list": [1, 2, {"nested": "item"}]
                    }
                }
            }
        }
        response = APIResponse.success(data=nested_data)
        assert response["data"] == nested_data

    def test_code_types_variations(self):
        """Test different code type variations"""
        test_codes = [
            200,      # Integer
            "200",    # String
            "OK",     # String status
            None,     # None
            0,        # Zero
            "400_BAD_REQUEST"  # String with underscore
        ]

        for code in test_codes:
            if code is not None:
                response = APIResponse.error(code=code)
                assert response["code"] == code
            else:
                # None should default to 500
                response = APIResponse.error(code=None)
                assert response["code"] == 500

    def test_message_types_variations(self):
        """Test different message type variations"""
        test_messages = [
            "",           # Empty string
            " ",          # Space
            "A",          # Single character
            123,          # Number
            True,         # Boolean
            None,         # None
            "Long message " * 100  # Very long message
        ]

        for message in test_messages:
            if message is not None:
                response = APIResponse.success(message=str(message))
                assert response["message"] == str(message)
            else:
                # None should default to "操作成功"
                response = APIResponse.success(message=None)
                assert response["message"] == "操作成功"

    @patch('utils.response.datetime')
    def test_timestamp_consistency(self, mock_datetime):
        """Test timestamp consistency across multiple calls"""
        mock_now = Mock()
        mock_now.isoformat.return_value = "2023-01-01T12:00:00.000000"
        mock_datetime.now.return_value = mock_now

        # Create multiple responses
        response1 = APIResponse.success()
        response2 = APIResponse.error()
        response3 = APIResponse.success(data={"test": "data"})

        # All should have the same timestamp
        assert response1["timestamp"] == "2023-01-01T12:00:00.000000"
        assert response2["timestamp"] == "2023-01-01T12:00:00.000000"
        assert response3["timestamp"] == "2023-01-01T12:00:00.000000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])