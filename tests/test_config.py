"""测试环境配置管理"""

import os
from typing import Any, Dict


class TestConfig:
    """测试配置类"""

    @staticmethod
    def setup_full_api_mode():
        """设置完整API模式（启用所有路由）"""
        os.environ["MINIMAL_API_MODE"] = "false"
        os.environ["FAST_FAIL"] = "false"
        os.environ["ENABLE_METRICS"] = "false"
        os.environ["METRICS_ENABLED"] = "false"
        os.environ["ENABLE_FEAST"] = "false"
        os.environ["ENVIRONMENT"] = "test"
        os.environ["ENABLED_SERVICES"] = "[]"
        os.environ["TESTING"] = "true"
        os.environ["MINIMAL_HEALTH_MODE"] = "false"
        os.environ["FAST_FAIL"] = "false"

    @staticmethod
    def setup_minimal_api_mode():
        """设置最小API模式（只启用健康检查）"""
        os.environ["MINIMAL_API_MODE"] = "true"
        os.environ["FAST_FAIL"] = "false"
        os.environ["ENABLE_METRICS"] = "false"
        os.environ["METRICS_ENABLED"] = "false"
        os.environ["ENABLE_FEAST"] = "false"
        os.environ["ENVIRONMENT"] = "test"
        os.environ["ENABLED_SERVICES"] = "[]"
        os.environ["TESTING"] = "true"
        os.environ["MINIMAL_HEALTH_MODE"] = "true"
        os.environ["FAST_FAIL"] = "false"

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """获取当前配置"""
        return {
            "MINIMAL_API_MODE": os.environ.get("MINIMAL_API_MODE", "true"),
            "MINIMAL_HEALTH_MODE": os.environ.get("MINIMAL_HEALTH_MODE", "true"),
            "FAST_FAIL": os.environ.get("FAST_FAIL", "false"),
            "ENABLE_METRICS": os.environ.get("ENABLE_METRICS", "false"),
            "TESTING": os.environ.get("TESTING", "true"),
            "ENVIRONMENT": os.environ.get("ENVIRONMENT", "test"),
        }
