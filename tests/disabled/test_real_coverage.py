#!/usr/bin/env python3
"""
实际覆盖率测试
直接测试src模块中的实际功能
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestRealCoverage:
    """实际覆盖率测试"""

    def test_utils_validators_real(self):
        """测试验证器实际功能"""
        from src.utils.validators import (
            is_valid_email,
            is_valid_phone,
            is_valid_url,
            is_valid_username,
            is_valid_password,
            is_valid_credit_card,
            is_valid_ipv4_address,
            is_valid_mac_address,
            validate_date_string,
            validate_json_string,
        )

        # 测试邮箱验证
        assert is_valid_email("user@example.com") is True
        assert is_valid_email("invalid-email") is False

        # 测试电话验证
        assert is_valid_phone("+1-555-123-4567") is True

        # 测试URL验证
        assert is_valid_url("https://www.example.com") is True
        assert is_valid_url("not-a-url") is False

        # 测试用户名验证
        assert is_valid_username("validuser123") is True
        assert is_valid_username("") is False

        # 测试密码验证
        assert is_valid_password("SecurePass123!") is True
        assert is_valid_password("weak") is False

        # 测试信用卡验证
        assert is_valid_credit_card("4532015112830366") is True  # Visa测试卡号
        assert is_valid_credit_card("123") is False

        # 测试IPv4验证
        assert is_valid_ipv4_address("192.168.1.1") is True
        assert is_valid_ipv4_address("invalid") is False

        # 测试MAC地址验证
        assert is_valid_mac_address("00:1B:44:11:3A:B7") is True
        assert is_valid_mac_address("invalid") is False

        # 测试日期字符串验证
        assert validate_date_string("2023-01-01") is True
        assert validate_date_string("not-a-date") is False

        # 测试JSON字符串验证
        assert validate_json_string('{"key": "value"}') is True
        assert validate_json_string("not-json") is False

    def test_utils_crypto_real(self):
        """测试加密工具实际功能"""
        from src.utils.crypto_utils import (
            generate_token,
            hash_string,
            verify_hash,
            encrypt_data,
            decrypt_data,
        )

        # 测试token生成
        token = generate_token()
        assert token is not None
        assert len(token) > 0

        # 测试哈希
        data = "test data"
        hashed = hash_string(data)
        assert hashed is not None
        assert hashed != data

        # 测试哈希验证
        assert verify_hash(data, hashed) is True
        assert verify_hash("wrong", hashed) is False

        # 测试加密解密
        secret = "my secret key"
        plain_text = "secret message"
        encrypted = encrypt_data(plain_text, secret)
        decrypted = decrypt_data(encrypted, secret)
        assert decrypted == plain_text

    def test_utils_dict_real(self):
        """测试字典工具实际功能"""
        from src.utils.dict_utils import (
            merge_dicts,
            get_value,
            set_value,
            has_key,
            remove_key,
        )

        # 测试字典合并
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        merged = merge_dicts(dict1, dict2)
        assert merged == {"a": 1, "b": 3, "c": 4}

        # 测试获取值
        data = {"a": {"b": {"c": 1}}}
        value = get_value(data, "a.b.c")
        assert value == 1

        # 测试设置值
        set_value(data, "a.b.d", 2)
        assert data["a"]["b"]["d"] == 2

        # 测试键存在
        assert has_key(data, "a.b.c") is True
        assert has_key(data, "a.x.y") is False

        # 测试删除键
        remove_key(data, "a.b.c")
        assert has_key(data, "a.b.c") is False

    def test_utils_string_real(self):
        """测试字符串工具实际功能"""
        from src.utils.string_utils import (
            normalize_string,
            extract_numbers,
            camel_to_snake,
            snake_to_camel,
            is_palindrome,
        )

        # 测试字符串标准化
        assert normalize_string("  Hello World  ") == "hello world"

        # 测试提取数字
        assert extract_numbers("abc123def456") == "123456"

        # 测试驼峰转蛇形
        assert camel_to_snake("CamelCase") == "camel_case"

        # 测试蛇形转驼峰
        assert snake_to_camel("snake_case") == "snakeCase"

        # 测试回文
        assert is_palindrome("racecar") is True
        assert is_palindrome("hello") is False

    def test_utils_time_real(self):
        """测试时间工具实际功能"""
        from src.utils.time_utils import (
            get_current_timestamp,
            format_duration,
            parse_duration,
            is_future,
            is_past,
        )

        # 测试当前时间戳
        ts = get_current_timestamp()
        assert ts is not None
        assert isinstance(ts, (int, float))

        # 测试格式化持续时间
        assert format_duration(3600) == "1h 0m"
        assert format_duration(90) == "1m 30s"

        # 测试解析持续时间
        assert parse_duration("1h") == 3600
        assert parse_duration("30m") == 1800

        # 测试未来时间
        future_ts = get_current_timestamp() + 3600
        assert is_future(future_ts) is True

        # 测试过去时间
        past_ts = get_current_timestamp() - 3600
        assert is_past(past_ts) is True

    def test_utils_response_real(self):
        """测试响应工具实际功能"""
        from src.utils.response import (
            create_response,
            create_success_response,
            create_error_response,
            create_paginated_response,
        )

        # 测试创建响应
        response = create_response("custom", {"data": "test"})
        assert response["status"] == "custom"
        assert response["data"] == {"data": "test"}

        # 测试成功响应
        success = create_success_response({"result": "ok"})
        assert success["status"] == "success"
        assert success["data"]["result"] == "ok"

        # 测试错误响应
        error = create_error_response("Something went wrong", 400)
        assert error["status"] == "error"
        assert error["message"] == "Something went wrong"
        assert error["code"] == 400

        # 测试分页响应
        paginated = create_paginated_response(
            items=[1, 2, 3], total=100, page=1, per_page=10
        )
        assert paginated["status"] == "success"
        assert paginated["data"]["items"] == [1, 2, 3]
        assert paginated["data"]["pagination"]["total"] == 100

    def test_utils_file_real(self):
        """测试文件工具实际功能"""
        from src.utils.file_utils import (
            ensure_directory,
            get_file_size,
            read_text_file,
            write_text_file,
        )
        import tempfile
        import os

        # 测试目录创建
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = os.path.join(tmpdir, "test_subdir")
            ensure_directory(test_dir)
            assert os.path.exists(test_dir)

            # 测试文件读写
            test_file = os.path.join(test_dir, "test.txt")
            write_text_file(test_file, "Hello, World!")
            content = read_text_file(test_file)
            assert content == "Hello, World!"

            # 测试文件大小
            size = get_file_size(test_file)
            assert size > 0

    def test_utils_config_loader_real(self):
        """测试配置加载器实际功能"""
        from src.utils.config_loader import (
            load_config_from_file,
            load_config_from_dict,
            get_config_value,
        )
        import tempfile
        import json

        # 测试从文件加载配置
        config_data = {"database": {"url": "sqlite:///test.db"}, "debug": True}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name

        try:
            config = load_config_from_file(config_file)
            assert config["database"]["url"] == "sqlite:///test.db"
            assert config["debug"] is True

            # 测试获取配置值
            db_url = get_config_value(config, "database.url")
            assert db_url == "sqlite:///test.db"

            debug = get_config_value(config, "debug", False)
            assert debug is True
        finally:
            import os

            os.unlink(config_file)
