#!/usr/bin/env python3
"""
测试功能模块
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from datetime import datetime, timedelta


def test_config_loader():
    """测试配置加载"""
    # 测试 JSON 配置加载
    config_data = {
        "debug": True,
        "port": 8000,
        "database": {
            "host": "localhost",
            "port": 5432
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name

    try:
        # 读取配置
        with open(config_path, 'r') as f:
            loaded_config = json.load(f)

        assert loaded_config["debug"] is True
        assert loaded_config["port"] == 8000
        assert loaded_config["database"]["host"] == "localhost"
    finally:
        os.unlink(config_path)


def test_cache_operations():
    """测试缓存操作"""
    # 简单的内存缓存实现
    class SimpleCache:
        def __init__(self):
            self.cache = {}

        def get(self, key, default=None):
            return self.cache.get(key, default)

        def set(self, key, value, ttl=None):
            self.cache[key] = value

        def delete(self, key):
            return self.cache.pop(key, None)

        def clear(self):
            self.cache.clear()

    cache = SimpleCache()

    # 测试基本操作
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.get("missing", "default") == "default"

    # 测试删除
    cache.delete("key1")
    assert cache.get("key1") is None

    # 测试清空
    cache.set("key2", "value2")
    cache.clear()
    assert cache.get("key2") is None


def test_retry_mechanism():
    """测试重试机制"""
    def retry(operation, max_attempts=3, delay=0.1):
        """简单的重试机制"""
        for attempt in range(max_attempts):
            try:
                return operation()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                time.sleep(delay)

    import time

    # 测试成功的操作
    def successful_op():
        return "success"

    assert retry(successful_op) == "success"

    # 测试失败的操作（前两次失败，第三次成功）
    attempt_count = 0
    def flaky_op():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError("Temporary failure")
        return "success"

    assert retry(flaky_op) == "success"


def test_warning_filters():
    """测试警告过滤器"""
    import warnings

    # 测试过滤特定警告
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        warnings.warn("This is a warning", UserWarning)
        warnings.warn("Deprecation warning", DeprecationWarning)

    # 检查警告数量
    assert len(w) == 2

    # 测试过滤掉特定类型的警告
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")  # 首先设置总是显示警告
        warnings.simplefilter("ignore", DeprecationWarning)  # 然后忽略弃用警告
        warnings.warn("This is a warning", UserWarning)
        warnings.warn("Deprecation warning", DeprecationWarning)

    assert len(w) == 1
    assert issubclass(w[0].category, UserWarning)


def test_time_operations():
    """测试时间操作"""
    # 测试时间差计算
    now = datetime.now()
    later = now + timedelta(hours=2, minutes=30)
    diff = later - now
    assert diff.total_seconds() == 2.5 * 3600

    # 测试时间格式化
    formatted = now.strftime("%Y-%m-%d %H:%M:%S")
    assert len(formatted) == 19

    # 测试时间解析
    parsed = datetime.strptime("2024-01-15 10:30:00", "%Y-%m-%d %H:%M:%S")
    assert parsed.year == 2024
    assert parsed.month == 1
    assert parsed.day == 15


def test_file_monitoring():
    """测试文件监控"""
    import time
    # 创建测试目录
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"

        # 测试文件创建
        test_file.write_text("test content")
        assert test_file.exists()
        assert test_file.read_text() == "test content"

        # 测试文件修改时间
        mtime = test_file.stat().st_mtime
        time.sleep(0.1)  # 添加延迟确保时间戳不同
        test_file.write_text("updated content")
        new_mtime = test_file.stat().st_mtime
        assert new_mtime >= mtime  # 使用 >= 而不是 >，处理精度问题

        # 测试文件大小
        size = test_file.stat().st_size
        assert size > 0


def test_data_validation():
    """测试数据验证"""
    def validate_email(email):
        """简单的邮箱验证"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def validate_phone(phone):
        """简单的电话号码验证"""
        import re
        pattern = r'^[\d\s\-\(\)]+$'
        return re.match(pattern, phone) is not None

    def validate_url(url):
        """简单的URL验证"""
        return url.startswith(('http://', 'https://'))

    # 测试邮箱验证
    assert validate_email("test@example.com") is True
    assert validate_email("invalid-email") is False
    assert validate_email("@example.com") is False

    # 测试电话验证
    assert validate_phone("123-456-7890") is True
    assert validate_phone("(123) 456-7890") is True
    assert validate_phone("abc") is False

    # 测试URL验证
    assert validate_url("https://example.com") is True
    assert validate_url("http://localhost:8000") is True
    assert validate_url("not-a-url") is False
