#!/usr/bin/env python3
"""
测试辅助工具函数
"""

import pytest
import uuid
import json
import os
from pathlib import Path


def test_generate_uuid():
    """测试 UUID 生成"""
    # 使用标准库
    u = uuid.uuid4()
    assert isinstance(u, uuid.UUID)
    assert len(str(u)) == 36

    # 测试唯一性
    u2 = uuid.uuid4()
    assert u != u2


def test_is_json():
    """测试 JSON 验证"""

    def is_json(s):
        try:
            json.loads(s)
            return True
        except:
            return False

    assert is_json('{"key": "value"}') is True
    assert is_json("[1, 2, 3]") is True
    assert is_json("not json") is False
    assert is_json("") is False


def test_deep_get():
    """测试深度获取字典值"""

    def deep_get(d, keys, default=None):
        """深度获取嵌套字典的值"""
        if not keys:
            return d

        current = d
        for key in keys.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    data = {"a": {"b": {"c": 123}}}
    assert deep_get(data, "a.b.c") == 123
    assert deep_get(data, "a.b.x", "default") == "default"
    assert deep_get(data, "x.y.z", None) is None


def test_merge_dicts():
    """测试字典合并"""

    def merge_dicts(*dicts):
        """合并多个字典"""
        result = {}
        for d in dicts:
            result.update(d)
        return result

    dict1 = {"a": 1, "b": 2}
    dict2 = {"b": 3, "c": 4}
    merged = merge_dicts(dict1, dict2)
    assert merged == {"a": 1, "b": 3, "c": 4}


def test_remove_duplicates():
    """测试列表去重"""

    def remove_duplicates(lst):
        """移除列表中的重复项"""
        return list(dict.fromkeys(lst))

    dup_list = [1, 2, 2, 3, 1, 4, 3]
    unique = remove_duplicates(dup_list)
    assert unique == [1, 2, 3, 4]


def test_chunk_list():
    """测试列表分块"""

    def chunk_list(lst, size):
        """将列表分成指定大小的块"""
        return [lst[i : i + size] for i in range(0, len(lst), size)]

    lst = list(range(10))
    chunks = chunk_list(lst, 3)
    assert chunks == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]


def test_safe_filename():
    """测试安全文件名"""

    def safe_filename(filename):
        """生成安全的文件名"""
        # 替换不安全的字符
        unsafe_chars = '<>:"/\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, "_")
        return filename

    unsafe = "file<>:|?.txt"
    safe = safe_filename(unsafe)
    assert safe == "file_____.txt"
    assert "/" not in safe
    assert "\\" not in safe


def test_temp_file_operations():
    """测试临时文件操作"""
    import tempfile

    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write("test content")

    # 读取文件
    with open(tmp_path, "r") as f:
        content = f.read()
        assert content == "test content"

    # 清理
    os.unlink(tmp_path)


def test_path_operations():
    """测试路径操作"""
    # 测试路径拼接
    base = Path("/tmp")
    filename = "test.txt"
    full_path = base / filename
    assert str(full_path) == "/tmp/test.txt"

    # 测试路径属性
    path = Path("/home/user/file.txt")
    assert path.name == "file.txt"
    assert path.suffix == ".txt"
    assert path.stem == "file"
    assert path.parent.name == "user"


def test_environment_variables():
    """测试环境变量操作"""
    # 设置测试环境变量
    os.environ["TEST_VAR"] = "test_value"

    # 读取环境变量
    assert os.getenv("TEST_VAR") == "test_value"
    assert os.getenv("MISSING_VAR", "default") == "default"

    # 清理
    del os.environ["TEST_VAR"]
