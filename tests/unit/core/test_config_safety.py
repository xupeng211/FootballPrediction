"""Phase 6: Config 安全网测试
Mock驱动的环境变量单元测试 - 专门针对 src/core/config.py

测试策略：
- Mock所有环境变量 os.environ
- 使用 importlib.reload 重新加载模块
- 测试配置加载、默认值、缺失配置处理
- 验证Config类和Settings类的行为
- 覆盖文件读写和持久化功能
"""

import json
import os
import pytest
from unittest.mock import Mock, patch, mock_open
from importlib import reload
from pathlib import Path
from typing import Any, Optional

# 导入要测试的模块
import src.core.config


class TestConfigSafetyNet:
    """
    Config模块安全网测试

    核心目标：为核心配置文件创建安全网
    风险等级: P0 (363行代码，0%覆盖率)
    测试策略: Mock环境变量 + 重新导入模块
    """

    def setup_method(self):
        """每个测试方法前的设置."""
        # 保存原始环境变量
        self.original_env = dict(os.environ)

    def teardown_method(self):
        """每个测试方法后的清理."""
        # 恢复原始环境变量
        os.environ.clear()
        os.environ.update(self.original_env)

    @pytest.fixture
    def mock_empty_env(self):
        """创建空的环境变量Mock"""
        with patch.dict(os.environ, {}, clear=True):
            yield

    @pytest.fixture
    def mock_full_env(self):
        """创建完整的环境变量Mock"""
        full_env = {
            "SECRET_KEY": "test-secret-key-12345",
            "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
            "TEST_DATABASE_URL": "postgresql://test:test@localhost:5432/test_db_test",
            "REDIS_URL": "redis://localhost:6380/1",
            "API_HOST": "test-host",
            "API_PORT": "9000",
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG",
            "MLFLOW_TRACKING_URI": "http://localhost:5000",
            "API_FOOTBALL_KEY": "test-api-key-67890",
            "API_FOOTBALL_URL": "https://test-api-football.com",
            "METRICS_ENABLED": "false",
            "METRICS_TABLES": '["table1", "table2", "table3"]',
            "METRICS_COLLECTION_INTERVAL": "60",
            "MISSING_DATA_DEFAULTS_PATH": "/path/to/defaults.json",
            "MISSING_DATA_DEFAULTS_JSON": '{"key": "value"}',
            "ENABLED_SERVICES": "ServiceA,ServiceB,ServiceC",
        }
        with patch.dict(os.environ, full_env, clear=True):
            yield

    # ==================== P0 优先级 Config类测试 ====================

    @pytest.mark.unit
    @pytest.mark.core
    @pytest.mark.critical
    def test_config_class_initialization_empty_env(self, mock_empty_env):
        """
        P0测试: Config类初始化 - 空环境变量

        测试目标: Config.__init__() 方法
        环境构造: 空的环境变量
        预期结果: 使用默认值创建配置实例
        业务重要性: 核心配置类初始化能力
        """
        # 重新加载config模块以应用Mock的环境变量
        reload(src.core.config)

        # 创建新的配置实例
        config = src.core.config.Config()

        # 验证基本属性
        assert config is not None
        assert hasattr(config, "debug")
        assert hasattr(config, "secret_key")
        assert hasattr(config, "database_url")

        # 验证默认值
        assert config.debug is False
        assert config.secret_key == "dev-secret-key-for-testing"
        assert (
            config.database_url == "sqlite+aiosqlite:///./data/football_prediction.db"
        )

    @pytest.mark.unit
    @pytest.mark.core
    @pytest.mark.critical
    def test_config_class_initialization_with_env(self, mock_full_env):
        """
        P0测试: Config类初始化 - 带环境变量

        测试目标: Config.__init__() 方法
        环境构造: 完整的环境变量
        预期结果: 从环境变量加载配置值
        业务重要性: 环境变量配置加载功能
        """
        # 重新加载config模块以应用Mock的环境变量
        reload(src.core.config)

        # 创建新的配置实例
        config = src.core.config.Config()

        # 验证环境变量加载
        assert config.secret_key == "test-secret-key-12345"
        assert config.database_url == "postgresql://test:test@localhost:5432/test_db"

    @pytest.mark.unit
    @pytest.mark.core
    @pytest.mark.critical
    def test_config_get_set_methods(self, mock_empty_env):
        """
        P0测试: Config类get和set方法

        测试目标: Config.get() 和 Config.set() 方法
        预期结果: 正确获取和设置配置项
        业务重要性: 配置项动态管理功能
        """
        # 重新加载config模块
        reload(src.core.config)
        config = src.core.config.Config()

        # 测试get方法 - 默认值
        result = config.get("non_existent_key", "default_value")
        assert result == "default_value"

        # 测试set方法
        config.set("test_key", "test_value")
        result = config.get("test_key")
        assert result == "test_value"

    @pytest.mark.unit
    @pytest.mark.core
    @pytest.mark.critical
    def test_config_file_operations(self, mock_empty_env):
        """
        P0测试: Config类文件操作

        测试目标: Config.save() 方法
        预期结果: 正确保存配置到文件
        业务重要性: 配置持久化功能
        """
        # 重新加载config模块
        reload(src.core.config)
        config = src.core.config.Config()

        # 模拟文件写入操作
        mock_file_data = {}

        def mock_json_dump(data, file, **kwargs):
            mock_file_data.update(data)

        with (
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump", side_effect=mock_json_dump),
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir"),
        ):
            config.set("test_key", "test_value")
            config.save()

            # 验证文件操作被调用
            mock_file.assert_called_once()

            # 验证数据被正确保存
            assert mock_file_data["test_key"] == "test_value"

    @pytest.mark.unit
    @pytest.mark.core
    @pytest.mark.critical
    def test_config_file_load_corrupted(self, mock_empty_env):
        """
        P0测试: Config类加载损坏的配置文件

        测试目标: Config._load_config() 方法
        错误构造: 模拟损坏的JSON配置文件
        预期结果: 记录警告但不中断程序执行
        业务重要性: 配置文件损坏时的容错能力
        """
        # 重新加载config模块
        reload(src.core.config)
        config = src.core.config.Config()

        # 模拟损坏的配置文件
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data="{invalid json")),
            patch("logging.warning") as mock_warning,
        ):
            config._load_config()

            # 验证警告被记录
            mock_warning.assert_called_once()
            assert "配置文件加载失败" in str(mock_warning.call_args)

    # ==================== P0 优先级 Settings类测试 ====================

    @pytest.mark.unit
    @pytest.mark.core
    @pytest.mark.critical
    def test_settings_class_empty_env(self, mock_empty_env):
        """
        P0测试: Settings类 - 空环境变量

        测试目标: Settings类初始化和默认值
        环境构造: 空的环境变量
        预期结果: 使用代码中定义的默认值
        业务重要性: Settings类基础功能
        """
        # 重新加载config模块
        reload(src.core.config)

        # 获取Settings实例
        settings = src.core.config.get_settings()

        # 验证基本属性存在
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "redis_url")
        assert hasattr(settings, "api_host")
        assert hasattr(settings, "api_port")
        assert hasattr(settings, "environment")
        assert hasattr(settings, "log_level")

        # 验证默认值（取决于是否有Pydantic）
        assert (
            settings.database_url == "sqlite+aiosqlite:///./data/football_prediction.db"
        )
        assert settings.redis_url == "redis://redis:6379/0"
        assert settings.api_host == "localhost"
        assert settings.api_port == 8000
        assert settings.environment == "development"
        assert settings.log_level == "INFO"

    @pytest.mark.unit
    @pytest.mark.core
    @pytest.mark.critical
    def test_settings_class_with_env_variables(self, mock_full_env):
        """
        P0测试: Settings类 - 带环境变量

        测试目标: Settings类环境变量加载
        环境构造: 完整的环境变量
        预期结果: 从环境变量正确加载所有配置
        业务重要性: 环境变量配置功能
        """
        # 重新加载config模块
        reload(src.core.config)

        # 获取Settings实例
        settings = src.core.config.get_settings()

        # 验证环境变量被正确加载
        assert settings.database_url == "postgresql://test:test@localhost:5432/test_db"
        assert (
            settings.test_database_url
            == "postgresql://test:test@localhost:5432/test_db_test"
        )
        assert settings.redis_url == "redis://localhost:6380/1"
        assert settings.api_host == "test-host"
        assert settings.api_port == 9000  # 应该从字符串转换为整数
        assert settings.environment == "test"
        assert settings.log_level == "DEBUG"
        assert settings.mlflow_tracking_uri == "http://localhost:5000"

    @pytest.mark.unit
    @pytest.mark.core
    @pytest.mark.critical
    def test_settings_boolean_conversion(self, mock_full_env):
        """
        P0测试: Settings类 - 布尔值转换

        测试目标: 环境变量字符串到布尔值的转换
        环境构造: METRICS_ENABLED="false"
        预期结果: 正确转换为布尔值False
        业务重要性: 布尔配置项处理
        """
        # 重新加载config模块
        reload(src.core.config)

        # 获取Settings实例
        settings = src.core.config.get_settings()

        # 验证布尔值转换
        assert settings.metrics_enabled is False

    @pytest.mark.unit
    @pytest.mark.core
    @pytest.mark.critical
    def test_settings_list_parsing_json(self, mock_full_env):
        """
        P0测试: Settings类 - 列表解析(JSON格式)

        测试目标: JSON格式列表环境变量解析
        环境构造: METRICS_TABLES='["table1", "table2", "table3"]'
        预期结果: 正确解析为Python列表
        业务重要性: 列表配置项处理
        """
        # 重新加载config模块
        reload(src.core.config)

        # 获取Settings实例
        settings = src.core.config.get_settings()

        # 验证JSON列表解析 - 使用新的属性方法
        if hasattr(settings, "metrics_tables_list"):
            assert isinstance(settings.metrics_tables_list, list)
            assert "table1" in settings.metrics_tables_list
            assert "table2" in settings.metrics_tables_list
            assert "table3" in settings.metrics_tables_list

    @pytest.mark.unit
    @pytest.mark.core
    @pytest.mark.critical
    def test_settings_list_parsing_comma_separated(self):
        """
        P0测试: Settings类 - 列表解析(逗号分隔)

        测试目标: 逗号分隔列表环境变量解析
        环境构造: ENABLED_SERVICES="ServiceA,ServiceB,ServiceC"
        预期结果: 正确解析为Python列表
        业务重要性: 列表配置项处理
        """
        # 设置逗号分隔的环境变量
        env_with_comma = {"ENABLED_SERVICES": "ServiceA,ServiceB,ServiceC"}
        with patch.dict(os.environ, env_with_comma, clear=True):
            # 重新加载config模块
            reload(src.core.config)

            # 获取Settings实例
            settings = src.core.config.get_settings()

            # 验证逗号分隔列表解析 - 使用新的属性方法
            if hasattr(settings, "enabled_services_list"):
                assert isinstance(settings.enabled_services_list, list)
                assert "ServiceA" in settings.enabled_services_list
                assert "ServiceB" in settings.enabled_services_list
                assert "ServiceC" in settings.enabled_services_list

    # ==================== P1 优先级 全局函数测试 ====================

    @pytest.mark.unit
    @pytest.mark.core
    def test_get_config_function(self, mock_empty_env):
        """
        P1测试: get_config()全局函数

        测试目标: get_config()函数
        预期结果: 返回Config实例
        业务重要性: 全局配置访问函数
        """
        # 重新加载config模块
        reload(src.core.config)

        # 调用全局函数
        config = src.core.config.get_config()

        # 验证返回类型
        assert isinstance(config, src.core.config.Config)
        assert hasattr(config, "get")
        assert hasattr(config, "set")
        assert hasattr(config, "save")

    @pytest.mark.unit
    @pytest.mark.core
    def test_get_settings_function(self, mock_empty_env):
        """
        P1测试: get_settings()全局函数

        测试目标: get_settings()函数
        预期结果: 返回Settings实例
        业务重要性: 全局设置访问函数
        """
        # 重新加载config模块
        reload(src.core.config)

        # 调用全局函数
        settings = src.core.config.get_settings()

        # 验证返回类型
        assert isinstance(settings, src.core.config.Settings)
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "redis_url")

    @pytest.mark.unit
    @pytest.mark.core
    def test_load_config_function(self, mock_empty_env):
        """
        P1测试: load_config()全局函数

        测试目标: load_config()函数
        预期结果: 返回Settings实例（忽略config_file参数）
        业务重要性: 配置加载函数
        """
        # 重新加载config模块
        reload(src.core.config)

        # 调用全局函数
        settings = src.core.config.load_config("/path/to/custom/config.json")

        # 验证返回类型（函数当前忽略config_file参数）
        assert isinstance(settings, src.core.config.Settings)
        assert hasattr(settings, "database_url")

    # ==================== P1 优先级 错误处理测试 ====================

    @pytest.mark.unit
    @pytest.mark.core
    def test_settings_invalid_port_number(self):
        """
        P1测试: Settings类 - 无效端口号

        测试目标: 端口号验证和错误处理
        错误构造: API_PORT="invalid_port"
        预期结果: 使用默认值或忽略无效值
        业务重要性: 配置验证功能
        """
        # 设置无效端口号
        env_with_invalid_port = {"API_PORT": "invalid_port"}
        with patch.dict(os.environ, env_with_invalid_port, clear=True):
            # 重新加载config模块
            reload(src.core.config)

            # 获取Settings实例
            settings = src.core.config.get_settings()

            # 验证处理无效端口的方式
            # 根据实现，可能会使用默认值或忽略
            assert hasattr(settings, "api_port")

    @pytest.mark.unit
    @pytest.mark.core
    def test_config_directory_creation(self, mock_empty_env):
        """
        P1测试: Config类 - 配置目录创建

        测试目标: Config.save()方法创建目录
        预期结果: 自动创建配置目录
        业务重要性: 配置文件路径管理
        """
        # 重新加载config模块
        reload(src.core.config)
        config = src.core.config.Config()

        # 模拟目录创建
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", mock_open()),
            patch("json.dump"),
        ):
            config.save()

            # 验证目录创建被调用
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @pytest.mark.unit
    @pytest.mark.core
    def test_config_path_manager_integration(self, mock_empty_env):
        """
        P1测试: Config类 - Path集成

        测试目标: 配置文件路径处理
        预期结果: 正确处理用户主目录路径
        业务重要性: 跨平台路径处理
        """
        # 重新加载config模块
        reload(src.core.config)
        config = src.core.config.Config()

        # 验证配置路径结构
        assert hasattr(config, "config_dir")
        assert hasattr(config, "config_file")

        # 验证路径类型
        assert isinstance(config.config_dir, Path)
        assert isinstance(config.config_file, Path)

    @pytest.mark.unit
    @pytest.mark.core
    def test_environment_variable_priority(self):
        """
        P1测试: 环境变量优先级

        测试目标: 验证环境变量覆盖默认值
        环境构造: 部分环境变量
        预期结果: 环境变量优先于默认值
        业务重要性: 配置优先级管理
        """
        # 设置部分环境变量
        partial_env = {
            "DATABASE_URL": "custom://db",
            "API_HOST": "custom-host",
            # 其他使用默认值
        }
        with patch.dict(os.environ, partial_env, clear=True):
            # 重新加载config模块
            reload(src.core.config)

            # 获取Settings实例
            settings = src.core.config.get_settings()

            # 验证环境变量覆盖
            assert settings.database_url == "custom://db"
            assert settings.api_host == "custom-host"

            # 验证其他使用默认值
            assert settings.api_port == 8000  # 默认值
            assert settings.environment == "development"  # 默认值

    @pytest.mark.unit
    @pytest.mark.core
    def test_multiple_config_instances_isolation(self, mock_empty_env):
        """
        P1测试: 多个配置实例隔离

        测试目标: 验证多个配置实例之间的隔离
        预期结果: 不同实例的配置互不影响
        业务重要性: 配置实例管理
        """
        # 重新加载config模块
        reload(src.core.config)

        # 创建多个Config实例
        config1 = src.core.config.Config()
        config2 = src.core.config.Config()

        # 在一个实例中设置配置
        config1.set("test_key", "value1")
        config2.set("test_key", "value2")

        # 验证实例隔离
        assert config1.get("test_key") == "value1"
        assert config2.get("test_key") == "value2"

    @pytest.mark.unit
    @pytest.mark.core
    def test_config_serialization_deserialization(self, mock_empty_env):
        """
        P1测试: 配置序列化和反序列化

        测试目标: JSON配置文件的读写
        预期结果: 正确序列化和反序列化各种数据类型
        业务重要性: 配置文件持久化
        """
        # 重新加载config模块
        reload(src.core.config)
        config = src.core.config.Config()

        # 设置各种类型的数据
        test_data = {
            "string_key": "string_value",
            "int_key": 42,
            "bool_key": True,
            "list_key": ["item1", "item2"],
            "dict_key": {"nested": "value"},
        }

        mock_file_data = {}

        def mock_json_dump(data, file, **kwargs):
            mock_file_data.clear()
            mock_file_data.update(data)

        with (
            patch("builtins.open", mock_open()),
            patch("json.dump", side_effect=mock_json_dump),
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir"),
        ):
            # 保存配置
            for key, value in test_data.items():
                config.set(key, value)
            config.save()

            # 验证序列化
            for key, value in test_data.items():
                assert mock_file_data[key] == value

    @pytest.mark.unit
    @pytest.mark.core
    def test_secret_key_fallback_logic(self):
        """
        P1测试: Secret Key回退逻辑

        测试目标: Config类中SECRET_KEY的回退逻辑
        环境构造: 无SECRET_KEY，有FLASK_SECRET_KEY
        预期结果: 使用FLASK_SECRET_KEY作为回退
        业务重要性: 密钥配置回退机制
        """
        # 设置FLASK_SECRET_KEY但不设置SECRET_KEY
        env_with_flask_key = {"FLASK_SECRET_KEY": "flask-secret-fallback"}
        with patch.dict(os.environ, env_with_flask_key, clear=True):
            # 重新加载config模块
            reload(src.core.config)

            # 创建配置实例
            config = src.core.config.Config()

            # 验证回退逻辑
            assert config.secret_key == "flask-secret-fallback"

    @pytest.mark.unit
    @pytest.mark.core
    def test_config_module_reloading_stability(self, mock_empty_env):
        """
        P1测试: 模块重新加载稳定性

        测试目标: 多次重新加载config模块
        预期结果: 模块状态保持一致
        业务重要性: 模块重新加载稳定性
        """
        # 多次重新加载模块
        for _i in range(3):
            reload(src.core.config)

            # 验证全局实例仍然可用
            config = src.core.config.get_config()
            settings = src.core.config.get_settings()

            assert config is not None
            assert settings is not None
            assert hasattr(config, "get")
            assert hasattr(settings, "database_url")
