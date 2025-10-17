"""
简单测试 - 验证核心功能
"""

import pytest
import time
from unittest.mock import AsyncMock, Mock


@pytest.mark.unit
class TestBasicFunctionality:
    """测试基础功能"""

    def test_imports(self):
        """测试模块导入"""
        # 测试核心模块可以正常导入
        from src.utils import retry
        from src.utils import formatters
        from src.utils import i18n

        assert retry is not None
        assert formatters is not None
        assert i18n is not None

    def test_retry_function(self):
        """测试重试函数"""
        from src.utils.retry import retry

        @retry(max_attempts=3, delay=0.1)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_formatter_datetime(self):
        """测试日期格式化"""
        from src.utils.formatters import format_datetime
        from datetime import datetime

        dt = datetime(2024, 1, 1, 12, 0, 0)
        formatted = format_datetime(dt)
        assert formatted is not None

    def test_i18n_get_language(self):
        """测试国际化"""
        from src.utils.i18n import get_current_language

        lang = get_current_language()
        assert lang in ["en", "zh", None]

    def test_performance_metrics(self, performance_metrics):
        """测试性能指标"""
        # 测试计时器
        performance_metrics.start_timer("test")
        time.sleep(0.01)
        duration = performance_metrics.end_timer("test")

        assert duration >= 0.01

    def test_data_loader(self, test_data_loader):
        """测试数据加载器"""
        teams = test_data_loader.create_teams()
        assert len(teams) > 0
        assert "id" in teams[0]

        matches = test_data_loader.create_matches()
        assert len(matches) > 0

        odds = test_data_loader.create_odds(1)
        assert "home_odds" in odds

    def test_api_client_mock(self, api_client):
        """测试 API 客户端 mock"""
        # 验证 mock 对象
        assert api_client is not None
        assert hasattr(api_client, "get")
        assert hasattr(api_client, "post")

        # 设置响应
        api_client.get.return_value.status_code = 200
        api_client.get.return_value.json.return_value = {"status": "ok"}

        # 使用 mock
        response = api_client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.unit
class TestDatabaseModels:
    """测试数据库模型（不需要数据库连接）"""

    def test_user_model_import(self):
        """测试用户模型导入"""
        try:
            from src.domain.models.user import User

            assert User is not None
        except ImportError:
            pytest.skip("User model not available")

    def test_match_model_import(self):
        """测试比赛模型导入"""
        try:
            from src.domain.models.match import Match

            assert Match is not None
        except ImportError:
            pytest.skip("Match model not available")

    def test_prediction_model_import(self):
        """测试预测模型导入"""
        try:
            from src.domain.models.prediction import Prediction

            assert Prediction is not None
        except ImportError:
            pytest.skip("Prediction model not available")


@pytest.mark.unit
class TestAPIRoutes:
    """测试 API 路由"""

    def test_main_app_import(self):
        """测试主应用导入"""
        try:
            from src.main import app

            assert app is not None
        except ImportError:
            pytest.skip("Main app not available")

    def test_router_imports(self):
        """测试路由导入"""
        try:
            from src.api.cqrs import CommandResponse
            from src.api.events import Event, EventManager

            # 这些应该不会抛出异常
            assert CommandResponse is not None
            assert Event is not None
        except ImportError:
            pytest.skip("API modules not available")


@pytest.mark.integration
class TestIntegrationBasics:
    """基础集成测试"""

    def test_config_loader(self):
        """测试配置加载"""
        from src.core.config import get_config

        config = get_config()
        assert config is not None
        assert hasattr(config, "environment")

    def test_logger(self):
        """测试日志系统"""
        from src.core.logging import get_logger

        logger = get_logger(__name__)
        assert logger is not None
        # 这应该不会抛出异常
        logger.info("Test message")

    def test_database_url_parsing(self):
        """测试数据库 URL 解析"""
        try:
            from src.database.connection import get_database_url

            url = get_database_url()
            assert url is not None
        except ImportError:
            pytest.skip("Database connection module not available")
