#!/usr/bin/env python3
"""
配置模块测试 - 基础业务逻辑测试
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from core.config import Settings, get_settings
except ImportError:
    pytest.skip("配置模块不可用", allow_module_level=True)


class TestConfiguration:
    """配置测试"""

    def test_default_settings_initialization(self):
        """测试默认设置初始化"""
        settings = Settings()

        # 验证基本配置项
        assert hasattr(settings, 'project_name')
        assert hasattr(settings, 'environment')
        assert hasattr(settings, 'debug')
        assert hasattr(settings, 'database_url')

    def test_get_settings_singleton(self):
        """测试设置单例模式"""
        settings1 = get_settings()
        settings2 = get_settings()

        # 验证单例行为
        assert settings1 is settings2

    @pytest.mark.unit
    def test_environment_variable_override(self):
        """测试环境变量覆盖"""
        import os
        with patch.dict(os.environ, {'PROJECT_NAME': 'test_project'}):
            settings = Settings()
            assert settings.project_name == 'test_project'

    @pytest.mark.unit
    def test_database_url_validation(self):
        """测试数据库URL验证"""
        settings = Settings()

        # 验证数据库URL格式
        if hasattr(settings, 'database_url') and settings.database_url:
            assert 'postgresql' in settings.database_url.lower()
            assert '://' in settings.database_url

    @pytest.mark.unit
    def test_debug_mode_configuration(self):
        """测试调试模式配置"""
        settings = Settings()

        # 验证调试模式设置
        debug_value = getattr(settings, 'debug', False)
        assert isinstance(debug_value, bool)

    @pytest.mark.unit
    def test_logging_configuration(self):
        """测试日志配置"""
        settings = Settings()

        # 验证日志相关配置
        if hasattr(settings, 'log_level'):
            assert settings.log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

    @pytest.mark.critical
    def test_required_configurations(self):
        """测试必需配置项"""
        required_configs = ['project_name', 'environment', 'database_url']
        settings = get_settings()

        for config in required_configs:
            assert hasattr(settings, config), f"缺少必需配置项: {config}"

    @pytest.mark.validation
    def test_configuration_validation(self):
        """测试配置验证"""
        settings = Settings()

        # 验证配置值的有效性
        if hasattr(settings, 'environment'):
            assert settings.environment in ['development', 'testing', 'production']

        if hasattr(settings, 'port'):
            assert isinstance(settings.port, int)
            assert 1024 <= settings.port <= 65535


if __name__ == "__main__":
    pytest.main([__file__, "-v"])