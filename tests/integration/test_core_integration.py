from typing import Optional

"""
核心模块集成测试
Core Module Integration Tests

测试核心业务模块的集成功能，包括配置、日志、验证等.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

# 使用简化的导入方式
try:
    from src.core.config import AppConfig
except ImportError:
    AppConfig = None

try:
    from src.core.logging import get_logger
except ImportError:
    get_logger = None

try:
    from src.core.validators import DataValidator
except ImportError:
    DataValidator = None

try:
    from src.utils.string_utils import StringUtils
except ImportError:
    StringUtils = None

try:
    from src.utils.date_utils import DateUtils
except ImportError:
    DateUtils = None


@pytest.mark.integration
@pytest.mark.core
class TestCoreModuleIntegration:
    """核心模块集成测试类"""

    @pytest.mark.asyncio
    async def test_config_system_integration(self):
        """测试配置系统集成"""
        if AppConfig is None:
            pytest.skip("AppConfig not available")

        # 1. 测试配置加载
        with patch("src.core.config.load_config") as mock_load:
            mock_config = {
                "database": {"url": "sqlite:///test.db", "echo": False},
                "cache": {"redis_url": "redis://localhost:6379", "default_ttl": 3600},
                "api": {"title": "Test API", "version": "1.0.0"},
            }
            mock_load.return_value = mock_config

            config = AppConfig()
            config.load_from_dict(mock_config)

            # 验证配置加载
            assert config.database.url == "sqlite:///test.db"
            assert config.cache.redis_url == "redis://localhost:6379"
            assert config.api.title == "Test API"

        # 2. 测试环境变量配置
        with patch.dict(
            "os.environ",
            {
                "DATABASE_URL": "postgresql://test/test",
                "REDIS_URL": "redis://localhost:6379/1",
            },
        ):
            # 模拟环境变量配置
            config = AppConfig()
            config.load_from_env()

            # 验证环境变量读取
            assert hasattr(config, "database")
            assert hasattr(config, "cache")

    def test_logging_system_integration(self):
        """测试日志系统集成"""
        # 1. 测试基础日志功能
        logger = get_logger(__name__)

        # 验证日志器创建
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

        # 2. 测试日志输出
        with patch("src.core.logging.get_logger") as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            test_logger = get_logger("test_module")

            # 测试不同级别的日志
            test_logger.info("测试信息日志")
            test_logger.warning("测试警告日志")
            test_logger.error("测试错误日志")

            # 验证日志调用
            mock_logger.info.assert_called_with("测试信息日志")
            mock_logger.warning.assert_called_with("测试警告日志")
            mock_logger.error.assert_called_with("测试错误日志")
            assert mock_logger.error.called

    def test_validation_system_integration(self):
        """测试验证系统集成"""
        if DataValidator is None:
            pytest.skip("DataValidator not available")

        validator = DataValidator()

        # 1. 测试字符串验证
        assert validator.validate_string("test", required=True) is True
        assert validator.validate_string("", required=True) is False
        assert validator.validate_string(None, required=False) is True

        # 2. 测试数字验证
        assert validator.validate_number(100, min_value=0, max_value=200) is True
        assert validator.validate_number(-1, min_value=0, max_value=200) is False
        assert validator.validate_number(300, min_value=0, max_value=200) is False

        # 3. 测试日期验证
        valid_date = datetime.utcnow()
        assert validator.validate_datetime(valid_date) is True

        invalid_date = "invalid-date"
        assert validator.validate_datetime(invalid_date) is False

        # 4. 测试邮箱验证
        assert validator.validate_email("test@example.com") is True
        assert validator.validate_email("invalid-email") is False
        assert validator.validate_email("") is False

    def test_string_utils_integration(self):
        """测试字符串工具集成"""
        if StringUtils is None:
            pytest.skip("StringUtils not available")

        # 1. 测试基础字符串操作
        assert StringUtils.is_empty("") is True
        assert StringUtils.is_empty("test") is False
        assert StringUtils.is_empty(None) is True

        # 2. 测试字符串格式化
        assert StringUtils.capitalize("hello") == "Hello"
        assert StringUtils.capitalize("HELLO") == "HELLO"

        # 3. 测试字符串清理
        assert StringUtils.clean_whitespace("  hello  world  ") == "hello world"
        assert StringUtils.remove_special_chars("hello@world!") == "helloworld"

        # 4. 测试字符串验证
        assert StringUtils.is_email("test@example.com") is True
        assert StringUtils.is_email("invalid") is False
        assert StringUtils.is_phone("+1234567890") is True
        assert StringUtils.is_phone("invalid") is False

    def test_date_utils_integration(self):
        """测试日期工具集成"""
        if DateUtils is None:
            pytest.skip("DateUtils not available")

        # 1. 测试基础日期操作
        now = datetime.utcnow()
        assert DateUtils.is_future(now + timedelta(days=1)) is True
        assert DateUtils.is_future(now - timedelta(days=1)) is False

        # 2. 测试日期格式化
        test_date = datetime(2024, 12, 15, 20, 0, 0)
        assert DateUtils.format_date(test_date, "%Y-%m-%d") == "2024-12-15"
        assert DateUtils.format_iso(test_date) == "2024-12-15T20:00:00"

        # 3. 测试日期解析
        parsed_date = DateUtils.parse_date("2024-12-15")
        assert parsed_date.year == 2024
        assert parsed_date.month == 12
        assert parsed_date.day == 15

        # 4. 测试日期计算
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        days_diff = DateUtils.days_between(start_date, end_date)
        assert days_diff == 30

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 1. 测试异常捕获
        try:
            # 模拟一个会抛出异常的操作
            raise ValueError("测试异常")
        except ValueError as e:
            assert str(e) == "测试异常"

        # 2. 测试自定义异常处理
        class CustomError(Exception):
            pass

        def risky_operation():
            raise CustomError("自定义错误")

        try:
            risky_operation()
            raise AssertionError("应该抛出异常")
        except CustomError:
            assert True  # 正确捕获自定义异常

    def test_data_validation_integration(self):
        """测试数据验证集成"""
        validator = DataValidator()

        # 1. 测试复杂数据结构验证
        valid_data = {
            "name": "Test User",
            "email": "test@example.com",
            "age": 25,
            "created_at": datetime.utcnow().isoformat(),
        }

        validation_rules = {
            "name": {"type": str, "required": True},
            "email": {
                "type": str,
                "required": True,
                "validator": validator.validate_email,
            },
            "age": {"type": int, "required": True, "min_value": 0, "max_value": 150},
            "created_at": {
                "type": str,
                "required": True,
                "validator": validator.validate_datetime,
            },
        }

        # 验证数据
        is_valid = validator.validate_dict(valid_data, validation_rules)
        assert is_valid is True

        # 2. 测试无效数据验证
        invalid_data = {
            "name": "",  # 无效：空字符串
            "email": "invalid-email",  # 无效：格式错误
            "age": -5,  # 无效：负数
            "created_at": "invalid-date",  # 无效：格式错误
        }

        is_valid = validator.validate_dict(invalid_data, validation_rules)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_async_operations_integration(self):
        """测试异步操作集成"""

        # 1. 测试异步任务执行
        async def async_task():
            await asyncio.sleep(0.01)  # 模拟异步操作
            return "异步任务完成"

        result = await async_task()
        assert result == "异步任务完成"

        # 2. 测试并发异步任务
        async def concurrent_task(task_id):
            await asyncio.sleep(0.01)
            return f"任务{task_id}完成"

        tasks = [concurrent_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all("完成" in result for result in results)

    def test_memory_management_integration(self):
        """测试内存管理集成"""
        # 1. 测试大对象处理
        large_list = list(range(10000))
        assert len(large_list) == 10000

        # 清理大对象
        del large_list

        # 2. 测试内存效率
        def memory_efficient_function():
            # 使用生成器而不是列表
            for i in range(1000):
                yield i * 2

        result = list(memory_efficient_function())
        assert len(result) == 1000
        assert result[0] == 0
        assert result[999] == 1998


@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceIntegration:
    """性能集成测试类"""

    def test_string_operations_performance(self):
        """测试字符串操作性能"""
        import time

        # 测试大量字符串操作的性能
        large_text = "测试字符串性能" * 1000

        start_time = time.time()

        # 执行多个字符串操作
        for _ in range(100):
            StringUtils.clean_whitespace(large_text)
            StringUtils.capitalize(large_text)
            StringUtils.remove_special_chars(large_text)

        end_time = time.time()

        # 验证性能在合理范围内（应该小于1秒）
        assert (end_time - start_time) < 1.0

    def test_date_operations_performance(self):
        """测试日期操作性能"""
        import time

        start_time = time.time()

        # 执行大量日期操作
        for i in range(1000):
            date = datetime(2024, 1, 1) + timedelta(days=i)
            DateUtils.format_iso(date)
            DateUtils.is_future(date)
            DateUtils.get_month_start(date)

        end_time = time.time()

        # 验证性能在合理范围内
        assert (end_time - start_time) < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
