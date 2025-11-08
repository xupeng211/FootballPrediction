#!/usr/bin/env python3
"""
Phase 3.1 - Utils模块文件工具类全面测试
文件处理工具comprehensive测试，快速提升覆盖率
"""

import json
import logging
import os
import tempfile
from pathlib import Path

import pytest

from src.utils.file_utils import FileUtils

logger = logging.getLogger(__name__)


class TestFileUtilsComprehensive:
    """FileUtils全面测试类"""

    def test_ensure_dir_create_new(self):
        """测试创建新目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new" / "subdir"
            result = FileUtils.ensure_dir(new_dir)

            assert result.exists()
            assert result.is_dir()
            assert result == new_dir

    def test_ensure_dir_existing(self):
        """测试确保已存在目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_dir = Path(temp_dir) / "existing"
            existing_dir.mkdir()
            result = FileUtils.ensure_dir(existing_dir)

            assert result.exists()
            assert result.is_dir()
            assert result == existing_dir

    def test_ensure_dir_with_string(self):
        """测试使用字符串路径创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, "test", "path")
            result = FileUtils.ensure_dir(new_dir)

            assert result.exists()
            assert result.is_dir()

    def test_read_json_success(self):
        """测试成功读取JSON文件"""
        test_data = {"name": "张三", "age": 25, "city": "北京"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f, ensure_ascii=False)
            temp_file = f.name

        try:
            result = FileUtils.read_json(temp_file)
            assert result == test_data
        finally:
            os.unlink(temp_file)

    def test_read_json_file_not_found(self):
        """测试读取不存在的JSON文件"""
        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json("/nonexistent/file.json")

    def test_read_json_invalid_json(self):
        """测试读取无效JSON文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json content}')
            temp_file = f.name

        try:
            with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
                FileUtils.read_json(temp_file)
        finally:
            os.unlink(temp_file)

    def test_write_json_success(self):
        """测试成功写入JSON文件"""
        test_data = {"name": "李四", "age": 30, "hobbies": ["读书", "游泳"]}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "test_output.json"

            FileUtils.write_json(test_data, temp_file)

            assert temp_file.exists()

            # 验证写入的内容
            with open(temp_file, encoding="utf-8") as f:
                loaded_data = json.load(f)

            assert loaded_data == test_data

    def test_write_json_create_directory(self):
        """测试写入JSON文件时自动创建目录"""
        test_data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "subdir" / "deep" / "test.json"

            FileUtils.write_json(test_data, temp_file)

            assert temp_file.exists()
            assert temp_file.parent.exists()

    def test_write_json_no_create_dir(self):
        """测试写入JSON文件时不自动创建目录"""
        test_data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "nonexistent" / "test.json"

            with pytest.raises(FileNotFoundError):
                FileUtils.write_json(test_data, temp_file, ensure_dir=False)

    def test_get_file_hash_success(self):
        """测试成功获取文件哈希值"""
        test_content = "Hello, World! 这是一个测试文件。"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write(test_content)
            temp_file = f.name

        try:
            hash_value = FileUtils.get_file_hash(temp_file)

            assert isinstance(hash_value, str)
            assert len(hash_value) == 32  # MD5 hash length

            # 验证哈希值的一致性
            hash_value2 = FileUtils.get_file_hash(temp_file)
            assert hash_value == hash_value2

        finally:
            os.unlink(temp_file)

    def test_get_file_hash_not_found(self):
        """测试获取不存在文件的哈希值"""
        with pytest.raises(FileNotFoundError):
            FileUtils.get_file_hash("/nonexistent/file.txt")

    def test_file_operations_with_path_object(self):
        """测试使用Path对象的文件操作"""
        test_data = {"operation": "path_object_test"}

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test_dir"
            test_file = test_dir / "test.json"

            # 测试ensure_dir
            result_dir = FileUtils.ensure_dir(test_dir)
            assert result_dir == test_dir
            assert result_dir.exists()

            # 测试write_json
            FileUtils.write_json(test_data, test_file)
            assert test_file.exists()

            # 测试read_json
            result_data = FileUtils.read_json(test_file)
            assert result_data == test_data

    def test_all_methods_exist(self):
        """测试所有方法都存在"""
        methods = ["ensure_dir", "read_json", "write_json", "get_file_hash"]

        for method in methods:
            assert hasattr(FileUtils, method), f"方法 {method} 不存在"

    def test_json_file_with_unicode_content(self):
        """测试处理包含Unicode内容的JSON文件"""
        test_data = {
            "中文名": "张三",
            "emoji": "🎉✨🚀",
            "special_chars": "áéíóú ñ",
            "mixed": "Hello 世界! 🌍",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "unicode_test.json"

            FileUtils.write_json(test_data, temp_file)
            result_data = FileUtils.read_json(temp_file)

            assert result_data == test_data

    def test_empty_json_file(self):
        """测试空JSON文件处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "empty.json"

            # 写入空字典
            FileUtils.write_json({}, temp_file)
            result = FileUtils.read_json(temp_file)
            assert result == {}

            # 写入空列表
            test_data = {"empty_list": [], "empty_dict": {}}
            FileUtils.write_json(test_data, temp_file)
            result = FileUtils.read_json(temp_file)
            assert result == test_data

    def test_large_json_file(self):
        """测试大型JSON文件处理"""
        # 创建包含大量数据的测试数据
        large_data = {
            "users": [
                {"id": i, "name": f"用户{i}", "data": list(range(100))}
                for i in range(1000)
            ],
            "metadata": {"total": 1000, "version": "1.0"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "large.json"

            FileUtils.write_json(large_data, temp_file)
            result = FileUtils.read_json(temp_file)

            assert len(result["users"]) == 1000
            assert result["metadata"]["total"] == 1000


def test_file_utils_comprehensive_suite():
    """FileUtils综合测试套件"""
    # 快速验证核心功能
    with tempfile.TemporaryDirectory() as temp_dir:
        # 测试目录创建
        test_dir = Path(temp_dir) / "test"
        result = FileUtils.ensure_dir(test_dir)
        assert result.exists()

        # 测试JSON读写
        test_data = {"test": "success"}
        test_file = test_dir / "test.json"

        FileUtils.write_json(test_data, test_file)
        result_data = FileUtils.read_json(test_file)
        assert result_data == test_data

    logger.debug("✅ FileUtils综合测试套件通过")  # TODO: Add logger import if needed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
