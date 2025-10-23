# 中间件扩展测试
from src.middleware.i18n import I18nMiddleware
from src.middleware.performance_monitoring import PerformanceMiddleware

def test_i18n_middleware():
    middleware = I18nMiddleware()
    assert middleware is not None

def test_performance_middleware():
    middleware = PerformanceMiddleware()
    assert middleware is not None

def test_middleware_methods():
    # 测试中间件方法
    i18n = I18nMiddleware()
    perf = PerformanceMiddleware()

    assert hasattr(i18n, 'detect_language')
    assert hasattr(perf, 'record_request')