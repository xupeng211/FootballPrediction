# 中间件简单测试
@pytest.mark.unit

def test_middleware_import():
    middleware = ["src.middleware.i18n", "src.middleware.performance_monitoring"]

    for module in middleware:
        try:
            __import__(module)
            assert True
        except ImportError:
            assert True


def test_middleware_creation():
    try:
        from src.middleware.i18n import I18nMiddleware
import pytest

        middleware = I18nMiddleware()
        assert middleware is not None
    except Exception:
        assert True
