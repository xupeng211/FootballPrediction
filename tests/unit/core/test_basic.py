"""基本功能测试"""

import pytest

from src.core import Logger

pytestmark = pytest.mark.unit


class TestProjectBasics:
    """项目基本功能测试类"""

    def test_project_structure(self):
        """测试项目结构"""
        # 这里可以测试项目的基本结构
        import os

        assert os.path.exists("src/api")
        assert os.path.exists("src/core")
        assert os.path.exists("src/database")
        assert os.path.exists("src/services")


class TestUtils:
    """工具函数测试类"""

    def test_setup_logger(self):
        """测试日志记录器设置"""
        logger = Logger.setup_logger("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == 20  # INFO level
