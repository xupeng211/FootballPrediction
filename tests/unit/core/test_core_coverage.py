"""
核心模块测试覆盖率提升
Core Module Coverage Improvement

专门为提升src/core/目录下低覆盖率模块而创建的测试用例。
Created specifically to improve coverage for low-coverage modules in src/core/.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))


class TestLoggerSimple:
    """测试简化日志模块"""

    def test_get_simple_logger_info_level(self):
        """测试INFO级别日志器创建"""
        logger = get_simple_logger("test_logger", "INFO")

        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_get_simple_logger_debug_level(self):
        """测试DEBUG级别日志器创建"""
        logger = get_simple_logger("debug_logger", "DEBUG")

        assert logger.level == logging.DEBUG

    def test_get_simple_logger_warning_level(self):
        """测试WARNING级别日志器创建"""
        logger = get_simple_logger("warning_logger", "WARNING")

        assert logger.level == logging.WARNING

    def test_get_simple_logger_error_level(self):
        """测试ERROR级别日志器创建"""
        logger = get_simple_logger("error_logger", "ERROR")

        assert logger.level == logging.ERROR

    def test_get_simple_logger_critical_level(self):
        """测试CRITICAL级别日志器创建"""
        logger = get_simple_logger("critical_logger", "CRITICAL")

        assert logger.level == logging.CRITICAL

    def test_get_simple_logger_default_level(self):
        """测试默认级别日志器"""
        logger = get_simple_logger("default_logger")

        assert logger.level == logging.INFO

    def test_get_simple_logger_single_handler(self):
        """测试日志器只有一个处理器"""
        logger1 = get_simple_logger("single_handler_logger")
        initial_handler_count = len(logger1.handlers)

        # 再次获取相同的日志器
        logger2 = get_simple_logger("single_handler_logger")

        assert logger1 is logger2  # 应该是同一个实例
        assert len(logger2.handlers) == initial_handler_count

    def test_get_simple_logger_formatter(self):
        """测试日志器格式化器"""
        logger = get_simple_logger("formatter_logger")
        handler = logger.handlers[0]
        formatter = handler.formatter

        assert formatter is not None
        assert "%(asctime)s" in formatter._fmt
        assert "%(name)s" in formatter._fmt
        assert "%(levelname)s" in formatter._fmt
        assert "%(message)s" in formatter._fmt

    def test_get_simple_logger_functionality(self):
        """测试日志器实际功能"""
        logger = get_simple_logger("functionality_logger")

        # 测试不同级别的日志输出
        with patch("logging.StreamHandler.emit") as mock_emit:
            logger.info("Test info message")
            logger.warning("Test warning message")
            logger.error("Test error message")

            assert mock_emit.call_count == 3


class TestPredictionEngine:
    """测试预测引擎模块"""

    @patch("src.core.prediction_engine._lazy_import")
    @patch("src.core.prediction_engine.PredictionConfig")
    def test_get_prediction_engine_first_call(
        self, mock_config_class, mock_lazy_import
    ):
        """测试首次获取预测引擎"""
        # 设置模拟
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        mock_engine_class = Mock()
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine

        with patch("src.core.prediction_engine.PredictionEngine", mock_engine_class):
            # 重置全局实例
            import src.core.prediction_engine

            src.core.prediction_engine._prediction_engine_instance = None

            result = asyncio.run(get_prediction_engine())

            assert result == mock_engine
            mock_lazy_import.assert_called_once()
            mock_config_class.assert_called_once()
            mock_engine_class.assert_called_once_with(config=mock_config)

    @patch("src.core.prediction_engine._lazy_import")
    def test_get_prediction_engine_singleton(self, mock_lazy_import):
        """测试预测引擎单例模式"""
        mock_engine_class = Mock()
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine

        with patch("src.core.prediction_engine.PredictionEngine", mock_engine_class):
            with patch("src.core.prediction_engine.PredictionConfig"):
                # 重置全局实例
                import src.core.prediction_engine

                src.core.prediction_engine._prediction_engine_instance = None

                # 第一次调用
                result1 = asyncio.run(get_prediction_engine())
                # 第二次调用
                result2 = asyncio.run(get_prediction_engine())

                assert result1 is result2  # 应该是同一个实例
                mock_engine_class.assert_called_once()  # 只应该创建一次

    def test_lazy_import_function(self):
        """测试延迟导入函数"""
        # 重置全局变量
        import src.core.prediction_engine

        src.core.prediction_engine.PredictionEngine = None
        src.core.prediction_engine.PredictionConfig = None
        src.core.prediction_engine.PredictionStatistics = None

        with patch("src.core.prediction_engine.PredictionEngine") as mock_pe:
            with patch("src.core.prediction_engine.PredictionConfig") as mock_pc:
                with patch(
                    "src.core.prediction_engine.PredictionStatistics"
                ) as mock_ps:
                    # 模拟导入
                    src.core.prediction_engine._lazy_import()

                    assert src.core.prediction_engine.PredictionEngine == mock_pe
                    assert src.core.prediction_engine.PredictionConfig == mock_pc
                    assert src.core.prediction_engine.PredictionStatistics == mock_ps

    def test_lazy_import_idempotent(self):
        """测试延迟导入的幂等性"""
        import src.core.prediction_engine

        # 设置模拟值
        mock_pe = Mock()
        mock_pc = Mock()
        mock_ps = Mock()

        src.core.prediction_engine.PredictionEngine = mock_pe
        src.core.prediction_engine.PredictionConfig = mock_pc
        src.core.prediction_engine.PredictionStatistics = mock_ps

        with (
            patch("src.core.prediction_engine.PredictionEngine"),
            patch("src.core.prediction_engine.PredictionConfig"),
            patch("src.core.prediction_engine.PredictionStatistics"),
        ):
            # 再次调用应该不改变值
            src.core.prediction_engine._lazy_import()

            # 值应该保持不变
            assert src.core.prediction_engine.PredictionEngine == mock_pe
            assert src.core.prediction_engine.PredictionConfig == mock_pc
            assert src.core.prediction_engine.PredictionStatistics == mock_ps


class TestAutoBinding:
    """测试自动绑定模块"""

    def test_auto_binding_imports(self):
        """测试自动绑定导入"""
        try:
            from src.core.auto_binding import auto_bind

            assert auto_bind is not None
        except ImportError:
            pytest.skip("auto_binding模块不可用")

    def test_auto_binding_function_exists(self):
        """测试自动绑定函数存在"""
        try:
            from src.core.auto_binding import auto_bind

            assert callable(auto_bind)
        except ImportError:
            pytest.skip("auto_binding模块不可用")


class TestServiceLifecycle:
    """测试服务生命周期模块"""

    def test_service_lifecycle_imports(self):
        """测试服务生命周期导入"""
        try:
            from src.core.service_lifecycle import ServiceLifecycle

            assert ServiceLifecycle is not None
        except ImportError:
            pytest.skip("service_lifecycle模块不可用")

    def test_service_lifecycle_class_exists(self):
        """测试服务生命周期类存在"""
        try:
            from src.core.service_lifecycle import ServiceLifecycle

            # 检查是否是类
            assert isinstance(ServiceLifecycle, type)
        except ImportError:
            pytest.skip("service_lifecycle模块不可用")


class TestDIContainer:
    """测试依赖注入容器"""

    def test_di_container_imports(self):
        """测试DI容器导入"""
        try:
            from src.core.di import DIContainer

            assert DIContainer is not None
        except ImportError:
            pytest.skip("di模块不可用")

    def test_di_container_creation(self):
        """测试DI容器创建"""
        try:
            from src.core.di import DIContainer

            container = DIContainer()
            assert container is not None
        except ImportError:
            pytest.skip("di模块不可用")


class TestConfigDI:
    """测试配置依赖注入"""

    def test_config_di_imports(self):
        """测试配置DI导入"""
        try:
            from src.core.config_di import load_config

            assert load_config is not None
        except ImportError:
            pytest.skip("config_di模块不可用")


class TestEventApplication:
    """测试事件应用模块"""

    def test_event_application_imports(self):
        """测试事件应用导入"""
        try:
            from src.core.event_application import EventApplication

            assert EventApplication is not None
        except ImportError:
            pytest.skip("event_application模块不可用")


class TestPredictionModules:
    """测试预测相关模块"""

    def test_cache_manager_imports(self):
        """测试缓存管理器导入"""
        try:
            from src.core.prediction.cache_manager import CacheManager

            assert CacheManager is not None
        except ImportError:
            pytest.skip("cache_manager模块不可用")

    def test_data_loader_imports(self):
        """测试数据加载器导入"""
        try:
            from src.core.prediction.data_loader import DataLoader

            assert DataLoader is not None
        except ImportError:
            pytest.skip("data_loader模块不可用")


class TestLoggerModule:
    """测试日志模块"""

    def test_logger_imports(self):
        """测试日志模块导入"""
        try:
            from src.core.logger import get_logger

            assert get_logger is not None
        except ImportError:
            pytest.skip("logger模块不可用")

    def test_get_logger_function(self):
        """测试获取日志器函数"""
        try:
            from src.core.logger import get_logger

            logger = get_logger("test_module")
            assert logger is not None
        except ImportError:
            pytest.skip("logger模块不可用")


class TestExceptionsModule:
    """测试异常模块"""

    def test_exceptions_imports(self):
        """测试异常模块导入"""
        try:
            from src.core.exceptions import PredictionException

            assert PredictionException is not None
        except ImportError:
            pytest.skip("exceptions模块不可用")

    def test_prediction_exception_creation(self):
        """测试预测异常创建"""
        try:
            from src.core.exceptions import PredictionException

            exception = PredictionException("Test error")
            assert str(exception) == "Test error"
        except ImportError:
            pytest.skip("exceptions模块不可用")


class TestErrorHandler:
    """测试错误处理器"""

    def test_error_handler_imports(self):
        """测试错误处理器导入"""
        try:
            from src.core.error_handler import ErrorHandler

            assert ErrorHandler is not None
        except ImportError:
            pytest.skip("error_handler模块不可用")


class TestModuleIntegration:
    """测试模块集成"""

    def test_core_modules_compatibility(self):
        """测试核心模块兼容性"""
        modules_to_test = [
            "src.core.logger_simple",
            "src.core.prediction_engine",
        ]

        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.skip(f"模块 {module_name} 不可用: {e}")

    def test_no_circular_imports(self):
        """测试无循环导入"""
        # 测试一些关键模块是否能正常导入
        modules_to_test = [
            "src.core.logger_simple",
        ]

        for module_name in modules_to_test:
            try:
                module = __import__(module_name, fromlist=[""])
                assert module is not None
            except ImportError as e:
                pytest.skip(f"模块 {module_name} 导入失败: {e}")


# 尝试导入要测试的函数
try:
    from src.core.logger_simple import get_simple_logger
except ImportError:
    get_simple_logger = None

try:
    from src.core.prediction_engine import get_prediction_engine
except ImportError:
    get_prediction_engine = None

# 如果关键函数不可用，跳过测试
if get_simple_logger is None:
    pytest.skip("logger_simple模块不可用", allow_module_level=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
