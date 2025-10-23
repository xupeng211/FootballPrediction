# 错误处理器简单测试
from src.core.error_handler import ErrorHandler
from src.core.exceptions import ServiceError

def test_error_handler():
    handler = ErrorHandler()
    assert handler is not None

def test_service_error():
    error = ServiceError("Test error")
    assert str(error) == "Test error"