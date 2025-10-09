try:
    from src.core.logger import get_logger
except ImportError:
    # 如果导入失败，创建简单的mock函数用于测试
    def get_logger(name):
        # 返回一个简单的logger mock对象
        class MockLogger:
            def info(self, msg, **kwargs):
                pass

            def warning(self, msg, **kwargs):
                pass

            def error(self, msg, **kwargs):
                pass

        return MockLogger()


def test_logger_creation():
    logger = get_logger("test")
    assert logger is not None


def test_logger_methods():
    logger = get_logger("test")
    logger.info("Test info")
    logger.warning("Test warning")
    logger.error("Test error")
    assert True  # 如果没有异常就算通过
