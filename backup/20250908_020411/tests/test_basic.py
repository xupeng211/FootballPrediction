"""基本功能测试"""

from footballprediction.core import ProjectCore
from footballprediction.utils import setup_logger


class TestCore:
    """核心功能测试类"""

    def test_project_core_initialization(self):
        """测试项目核心初始化"""
        core = ProjectCore()
        assert core.name == "FootballPrediction"
        assert core.version == "0.1.0"

    def test_get_info(self):
        """测试获取项目信息"""
        core = ProjectCore()
        info = core.get_info()

        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "description" in info


class TestUtils:
    """工具函数测试类"""

    def test_setup_logger(self):
        """测试日志记录器设置"""
        logger = setup_logger("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == 20  # INFO level
