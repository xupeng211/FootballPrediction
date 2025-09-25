import pytest

from src.utils.response import APIResponse

pytestmark = pytest.mark.unit


def test_success_response_contains_timestamp():
    payload = {"items": [1, 2, 3]}
    result = APIResponse.success(data=payload, message="ok")

    assert result["success"] is True
    assert result["data"] == payload
    assert result["message"] == "ok"
    assert "timestamp" in result


def test_error_response_with_code_and_data():
    result = APIResponse.error(message="bad", code=400, data={"detail": "oops"})

    assert result["success"] is False
    assert result["message"] == "bad"
    assert result["code"] == 400
    assert result["data"] == {"detail": "oops"}
    assert "timestamp" in result


def test_error_response_defaults():
    result = APIResponse.error()

    assert result["code"] == 500
    assert result["success"] is False
    assert result["message"] == "操作失败"
