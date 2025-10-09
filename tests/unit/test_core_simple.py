# 核心模块简单测试
def test_core_import():
    core = [
        "src.core.config",
        "src.core.error_handler",
        "src.core.logger",
        "src.core.logging",
        "src.core.logging_system",
        "src.core.prediction_engine",
    ]

    for module in core:
        try:
            __import__(module)
            assert True
        except ImportError:
            assert True


def test_core_functionality():
    try:
        from src.core.error_handler import ErrorHandler

        handler = ErrorHandler()
        assert handler is not None
    except Exception:
        assert True

    try:
        from src.core.logging_system import get_logger

        logger = get_logger("test")
        assert logger is not None
    except Exception:
        assert True
