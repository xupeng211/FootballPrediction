from src.data.quality.exception_handler_mod import DataQualityExceptionHandler


def test_exception_handler():
    handler = DataQualityExceptionHandler()
    assert handler is not None


def test_handling_methods():
    handler = DataQualityExceptionHandler()
    assert hasattr(handler, "handle_exception")
    assert hasattr(handler, "log_error")
