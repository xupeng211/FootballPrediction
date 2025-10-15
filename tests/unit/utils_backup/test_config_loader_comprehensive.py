"""ConfigLoader模块综合测试 - 目标：从18%提升到60%"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml


class TestConfigLoaderFromFile:
    """测试从文件加载配置的功能"""

    def test_load_json_config_success(self):
        """测试成功加载JSON配置文件"""
        from src.utils.config_loader import load_config_from_file

        # 创建临时JSON配置文件
        config_data = {
            "database": {"url": "sqlite:///test.db", "pool_size": 10},
            "redis": {"host": "localhost", "port": 6379},
            "api": {"host": "0.0.0.0", "port": 8000, "debug": True},
            "features": {"feature1": True, "feature2": False},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            # 测试加载配置
            loaded = load_config_from_file(temp_file)
            assert loaded == config_data
            assert loaded["database"]["url"] == "sqlite:///test.db"
            assert loaded["api"]["debug"] is True
            assert loaded["features"]["feature1"] is True
        finally:
            os.unlink(temp_file)

    def test_load_yaml_config_success(self):
        """测试成功加载YAML配置文件"""
        from src.utils.config_loader import load_config_from_file

        # 创建临时YAML配置文件
        config_data = {
            "database": {"url": "postgresql://localhost/test"},
            "cache": {"type": "redis", "ttl": 3600},
            "logging": {"level": "INFO", "format": "json"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            # 测试加载配置
            loaded = load_config_from_file(temp_file)
            assert loaded == config_data
            assert loaded["database"]["url"] == "postgresql://localhost/test"
            assert loaded["cache"]["ttl"] == 3600
        finally:
            os.unlink(temp_file)

    def test_load_yml_config_success(self):
        """测试成功加载.yml扩展名的YAML文件"""
        from src.utils.config_loader import load_config_from_file

        config_data = {"app": {"name": "test", "version": "1.0.0"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert loaded == config_data
            assert loaded["app"]["name"] == "test"
        finally:
            os.unlink(temp_file)

    def test_load_config_nonexistent_file(self):
        """测试加载不存在的配置文件"""
        from src.utils.config_loader import load_config_from_file

        # 测试不存在的文件
        loaded = load_config_from_file("/path/that/does/not/exist/config.json")
        assert loaded == {}

    def test_load_config_unsupported_format(self):
        """测试加载不支持的配置文件格式"""
        from src.utils.config_loader import load_config_from_file

        # 创建临时文本文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is not a valid config format")
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert loaded == {}
        finally:
            os.unlink(temp_file)

    def test_load_config_json_invalid_json(self):
        """测试加载无效的JSON文件"""
        from src.utils.config_loader import load_config_from_file

        # 创建包含无效JSON的文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json content}')  # 无效JSON
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert loaded == {}
        finally:
            os.unlink(temp_file)

    def test_load_config_yaml_invalid_yaml(self):
        """测试加载无效的YAML文件"""
        from src.utils.config_loader import load_config_from_file

        # 创建包含无效YAML的文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:\n  - missing\n    proper\n    indentation")
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert loaded == {}
        finally:
            os.unlink(temp_file)

    def test_load_config_yaml_empty_file(self):
        """测试加载空的YAML文件"""
        from src.utils.config_loader import load_config_from_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # 空文件
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert loaded == {}
        finally:
            os.unlink(temp_file)

    def test_load_config_permission_error(self):
        """测试文件权限错误"""
        from src.utils.config_loader import load_config_from_file

        # 使用mock模拟权限错误
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            loaded = load_config_from_file("config.json")
            assert loaded == {}

    def test_load_config_runtime_error(self):
        """测试运行时错误"""
        from src.utils.config_loader import load_config_from_file

        # 使用mock模拟运行时错误
        with patch("builtins.open", side_effect=RuntimeError("Runtime error")):
            loaded = load_config_from_file("config.json")
            assert loaded == {}

    def test_load_config_key_error(self):
        """测试键错误"""
        from src.utils.config_loader import load_config_from_file

        # 使用mock模拟键错误
        with patch("builtins.open", side_effect=KeyError("Key error")):
            loaded = load_config_from_file("config.json")
            assert loaded == {}

    def test_load_config_value_error(self):
        """测试值错误"""
        from src.utils.config_loader import load_config_from_file

        # 使用mock模拟值错误
        with patch("builtins.open", side_effect=ValueError("Value error")):
            loaded = load_config_from_file("config.json")
            assert loaded == {}

    def test_load_config_with_pathlib_path(self):
        """测试使用Path对象加载配置"""
        from src.utils.config_loader import load_config_from_file

        config_data = {"test": "value"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = Path(f.name)

        try:
            # 使用Path对象
            loaded = load_config_from_file(str(temp_file))
            assert loaded == config_data

            # 也可以直接传入Path对象（会转换为字符串）
            loaded = load_config_from_file(temp_file)
            assert loaded == config_data
        finally:
            temp_file.unlink()

    def test_load_config_nested_json(self):
        """测试加载嵌套JSON配置"""
        from src.utils.config_loader import load_config_from_file

        # 创建深度嵌套的配置
        config_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "deep_value": "found it",
                            "list": [1, 2, 3, {"nested": True}],
                        }
                    }
                }
            },
            "arrays": [{"item": 1}, {"item": 2}, {"sub": {"deep": "value"}}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert (
                loaded["level1"]["level2"]["level3"]["level4"]["deep_value"]
                == "found it"
            )
            assert (
                loaded["level1"]["level2"]["level3"]["level4"]["list"][3]["nested"]
                is True
            )
            assert loaded["arrays"][2]["sub"]["deep"] == "value"
        finally:
            os.unlink(temp_file)

    def test_load_config_special_characters(self):
        """测试加载包含特殊字符的配置"""
        from src.utils.config_loader import load_config_from_file

        # 包含特殊字符和Unicode的配置
        config_data = {
            "unicode": "测试中文 🚀",
            "special_chars": "Special: !@#$%^&*()",
            "escape": "Line 1\nLine 2\tTabbed",
            "quotes": 'Single "and" double quotes',
            "emoji": "🎉✨🐍",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(config_data, f, ensure_ascii=False)
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert loaded["unicode"] == "测试中文 🚀"
            assert loaded["emoji"] == "🎉✨🐍"
        finally:
            os.unlink(temp_file)

    def test_load_config_large_file(self):
        """测试加载大型配置文件"""
        from src.utils.config_loader import load_config_from_file

        # 创建大型配置
        config_data = {
            "large_array": list(range(1000)),
            "large_object": {f"key_{i}": f"value_{i}" for i in range(100)},
            "nested": {
                "data": {str(i): {"value": i * 2, "square": i**2} for i in range(100)}
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert len(loaded["large_array"]) == 1000
            assert len(loaded["large_object"]) == 100
            assert loaded["nested"]["data"]["99"]["square"] == 9801
        finally:
            os.unlink(temp_file)

    def test_load_config_yaml_not_available(self):
        """测试YAML库不可用时的回退"""
        from src.utils.config_loader import load_config_from_file

        # 模拟yaml库不可用
        with patch.dict("sys.modules", {"yaml": None}):
            with pytest.raises(ImportError):
                import yaml

        # 或者模拟yaml导入失败
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'yaml'")
        ):
            loaded = load_config_from_file("config.yaml")
            assert loaded == {}


class TestConfigLoaderEdgeCases:
    """测试配置加载器的边界情况"""

    def test_load_config_empty_json_file(self):
        """测试加载空JSON文件"""
        from src.utils.config_loader import load_config_from_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")  # 空文件
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert loaded == {}
        finally:
            os.unlink(temp_file)

    def test_load_config_json_null_value(self):
        """测试JSON中包含null值"""
        from src.utils.config_loader import load_config_from_file

        config_data = {
            "existing": "value",
            "null_value": None,
            "nested": {"also_null": None, "not_null": "ok"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert loaded["null_value"] is None
            assert loaded["nested"]["also_null"] is None
            assert loaded["existing"] == "value"
        finally:
            os.unlink(temp_file)

    def test_load_config_yaml_returns_none(self):
        """测试YAML safe_load返回None"""
        from src.utils.config_loader import load_config_from_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("null")  # YAML null值
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert loaded == {}  # 应该返回空字典而不是None
        finally:
            os.unlink(temp_file)

    def test_load_config_case_insensitive_extension(self):
        """测试文件扩展名大小写"""
        from src.utils.config_loader import load_config_from_file

        config_data = {"test": "value"}

        # 测试大写扩展名
        with tempfile.NamedTemporaryFile(mode="w", suffix=".JSON", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            # 应该能正确识别大写的JSON扩展名
            loaded = load_config_from_file(temp_file)
            assert loaded == config_data
        finally:
            os.unlink(temp_file)

    def test_load_config_no_extension(self):
        """测试没有扩展名的文件"""
        from src.utils.config_loader import load_config_from_file

        with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
            json.dump({"test": "value"}, f)
            temp_file = f.name

        try:
            # 没有扩展名应该返回空字典
            loaded = load_config_from_file(temp_file)
            assert loaded == {}
        finally:
            os.unlink(temp_file)

    def test_load_config_double_extension(self):
        """测试双扩展名文件"""
        from src.utils.config_loader import load_config_from_file

        config_data = {"test": "value"}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json.bak", delete=False
        ) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            # 双扩展名应该不被识别为JSON
            loaded = load_config_from_file(temp_file)
            assert loaded == {}
        finally:
            os.unlink(temp_file)

    def test_load_config_with_bom(self):
        """测试带有BOM的UTF-8文件"""
        from src.utils.config_loader import load_config_from_file

        config_data = {"message": "Hello with BOM"}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8-sig"
        ) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)
            assert loaded == config_data
        finally:
            os.unlink(temp_file)

    def test_load_config_file_like_object(self):
        """测试传入类文件对象路径"""
        import io

        from src.utils.config_loader import load_config_from_file

        # 注意：load_config_from_file期望文件路径，不是文件对象
        # 这个测试确保它能优雅地处理错误输入
        assert load_config_from_file(None) == {}
        assert load_config_from_file("") == {}


# 集成测试 - 与其他模块的交互
class TestConfigLoaderIntegration:
    """测试配置加载器与其他模块的集成"""

    def test_config_loader_with_environment_variables(self):
        """测试配置加载器与环境变量的交互"""
        from src.utils.config_loader import load_config_from_file

        # 创建包含环境变量占位符的配置
        config_data = {
            "database": {
                "url": "postgresql://${DB_HOST}:${DB_PORT}/testdb",
                "user": "${DB_USER}",
                "password": "${DB_PASSWORD}",
            },
            "debug": "${DEBUG_MODE:false}",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            # 加载配置
            loaded = load_config_from_file(temp_file)

            # 验证配置已加载（实际的环境变量替换需要在其他模块中实现）
            assert "${DB_HOST}" in loaded["database"]["url"]
            assert loaded["debug"] == "${DEBUG_MODE:false}"
        finally:
            os.unlink(temp_file)

    def test_config_loader_with_default_values(self):
        """测试配置加载器处理默认值"""
        from src.utils.config_loader import load_config_from_file

        # 创建最小配置
        config_data = {
            "api": {"port": 8000}
            # 其他配置应该有默认值
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)

            # 验证加载的配置
            assert loaded["api"]["port"] == 8000
            # 默认值处理应该在应用程序逻辑中实现
        finally:
            os.unlink(temp_file)

    def test_config_loader_multiple_environments(self):
        """测试多环境配置加载"""
        from src.utils.config_loader import load_config_from_file

        # 创建不同环境的配置
        configs = {
            "development.json": {
                "debug": True,
                "database": {"url": "sqlite:///dev.db"},
                "log_level": "DEBUG",
            },
            "production.json": {
                "debug": False,
                "database": {"url": "postgresql://prod/db"},
                "log_level": "INFO",
            },
        }

        temp_files = []
        try:
            # 创建临时配置文件
            for env, config in configs.items():
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_{env}", delete=False
                ) as f:
                    json.dump(config, f)
                    temp_files.append(f.name)

            # 测试加载不同配置
            for i, (env, expected_config) in enumerate(configs.items()):
                loaded = load_config_from_file(temp_files[i])
                assert loaded["debug"] == expected_config["debug"]
                assert loaded["log_level"] == expected_config["log_level"]
        finally:
            for temp_file in temp_files:
                os.unlink(temp_file)

    def test_config_loader_with_validation(self):
        """测试配置加载后的验证"""
        from src.utils.config_loader import load_config_from_file

        # 创建需要验证的配置
        config_data = {
            "api": {"port": 8000, "host": "0.0.0.0"},
            "database": {"url": "sqlite:///test.db", "required": True},
            "features": {"feature1": True, "feature2": False},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)

            # 验证必需字段
            assert "database" in loaded
            assert "url" in loaded["database"]
            assert loaded["database"]["required"] is True

            # 验证端口号范围
            assert isinstance(loaded["api"]["port"], int)
            assert 0 < loaded["api"]["port"] < 65536
        finally:
            os.unlink(temp_file)

    def test_config_loader_caching(self):
        """测试配置加载的缓存机制（如果有的话）"""
        from src.utils.config_loader import load_config_from_file

        config_data = {"test": "value", "timestamp": "2025-01-13"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            # 多次加载同一个文件
            loaded1 = load_config_from_file(temp_file)
            loaded2 = load_config_from_file(temp_file)
            loaded3 = load_config_from_file(temp_file)

            # 验证结果一致
            assert loaded1 == loaded2 == loaded3 == config_data

            # 注意：实际的缓存需要在应用程序层面实现
        finally:
            os.unlink(temp_file)

    def test_config_loader_with_schema_validation(self):
        """测试配置模式验证"""
        from src.utils.config_loader import load_config_from_file

        # 创建符合模式的配置
        config_data = {
            "$schema": "https://example.com/config-schema.json",
            "version": "1.0",
            "services": {
                "api": {"port": 8000, "endpoints": ["/users", "/matches"]},
                "worker": {"concurrency": 4, "queues": ["high", "default"]},
                "scheduler": {"enabled": True},
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            loaded = load_config_from_file(temp_file)

            # 验证模式信息存在（实际验证需要jsonschema库）
            assert "$schema" in loaded
            assert loaded["version"] == "1.0"
            assert len(loaded["services"]["api"]["endpoints"]) == 2
        finally:
            os.unlink(temp_file)


# 性能测试
class TestConfigLoaderPerformance:
    """测试配置加载器的性能"""

    def test_load_config_performance_small(self):
        """测试加载小配置文件的性能"""
        import time

        from src.utils.config_loader import load_config_from_file

        config_data = {"small": "config", "number": 42}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            start_time = time.time()
            for _ in range(100):
                load_config_from_file(temp_file)
            elapsed = time.time() - start_time

            # 100次加载应该在1秒内完成
            assert elapsed < 1.0
        finally:
            os.unlink(temp_file)

    def test_load_config_performance_large(self):
        """测试加载大配置文件的性能"""
        import time

        from src.utils.config_loader import load_config_from_file

        # 创建大型配置
        config_data = {
            "users": [
                {"id": i, "name": f"user_{i}", "data": "x" * 100} for i in range(1000)
            ],
            "metadata": {f"key_{i}": f"value_{i}" * 10 for i in range(100)},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            start_time = time.time()
            loaded = load_config_from_file(temp_file)
            elapsed = time.time() - start_time

            # 加载应该在合理时间内完成
            assert elapsed < 0.5
            assert len(loaded["users"]) == 1000
        finally:
            os.unlink(temp_file)
