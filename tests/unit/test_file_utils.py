#!/usr/bin/env python3
"""
文件工具测试
测试 src.utils.file_utils 模块的功能
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.utils.file_utils import FileUtils


@pytest.mark.unit
class TestFileUtils:
    """文件工具测试"""

    def test_ensure_directory_exists_new(self):
        """测试确保新目录存在"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"

            # 确保目录不存在
            assert not new_dir.exists()

            # 创建目录
            FileUtils.ensure_directory_exists(new_dir)

            # 验证目录存在
            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_ensure_directory_exists_existing(self):
        """测试确保已存在目录存在"""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_dir = Path(temp_dir) / "existing_directory"
            existing_dir.mkdir()

            # 确保目录存在
            assert existing_dir.exists()

            # 再次调用应该不会出错
            FileUtils.ensure_directory_exists(existing_dir)

            # 目录仍然存在
            assert existing_dir.exists()

    def test_ensure_directory_exists_nested(self):
        """测试创建嵌套目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = Path(temp_dir) / "level1" / "level2" / "level3"

            # 确保嵌套目录不存在
            assert not nested_dir.exists()

            # 创建嵌套目录
            FileUtils.ensure_directory_exists(nested_dir)

            # 验证嵌套目录存在
            assert nested_dir.exists()
            assert nested_dir.is_dir()

    def test_ensure_directory_exists_string_path(self):
        """测试字符串路径的目录创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = os.path.join(temp_dir, "string_dir")

            # 创建目录
            FileUtils.ensure_directory_exists(dir_path)

            # 验证目录存在
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)

    def test_safe_filename_basic(self):
        """测试基础安全文件名生成"""
        unsafe_name = "file:name?with*invalid|chars"
        safe_name = FileUtils.safe_filename(unsafe_name)

        # 验证不包含不安全字符
        assert ":" not in safe_name
        assert "?" not in safe_name
        assert "*" not in safe_name
        assert "|" not in safe_name

        # 验证仍然是可识别的名称
        assert "file" in safe_name
        assert "name" in safe_name
        assert "with" in safe_name
        assert "invalid" in safe_name
        assert "chars" in safe_name

    def test_safe_filename_empty(self):
        """测试空字符串的安全文件名"""
        result = FileUtils.safe_filename("")
        assert result == ""

    def test_safe_filename_unicode(self):
        """测试Unicode文件名"""
        unicode_name = "测试文件名.txt"
        safe_name = FileUtils.safe_filename(unicode_name)

        # Unicode字符应该被保留
        assert "测试" in safe_name
        assert "文件名" in safe_name
        assert ".txt" in safe_name

    def test_safe_filename_with_spaces(self):
        """测试包含空格的文件名"""
        name_with_spaces = "file name with spaces.txt"
        safe_name = FileUtils.safe_filename(name_with_spaces)

        # 空格可能被保留或替换为下划线
        assert "file" in safe_name
        assert "name" in safe_name
        assert "with" in safe_name
        assert "spaces" in safe_name

    def test_get_file_size_existing(self):
        """测试获取已存在文件的大小"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name

        try:
            size = FileUtils.get_file_size(temp_file_path)

            # 验证返回正确的文件大小
            assert size == len("test content")
            assert isinstance(size, int)
            assert size > 0
        finally:
            os.unlink(temp_file_path)

    def test_get_file_size_nonexistent(self):
        """测试获取不存在文件的大小"""
        nonexistent_file = "/path/to/nonexistent/file.txt"

        size = FileUtils.get_file_size(nonexistent_file)
        assert size == 0

    def test_get_file_size_directory(self):
        """测试获取目录的大小"""
        with tempfile.TemporaryDirectory() as temp_dir:
            size = FileUtils.get_file_size(temp_dir)
            # 目录的大小通常为0或很小
            assert isinstance(size, int)
            assert size >= 0

    def test_is_text_file_text(self):
        """测试文本文件识别"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp_file:
            temp_file.write("This is a text file")
            temp_file_path = temp_file.name

        try:
            is_text = FileUtils.is_text_file(temp_file_path)
            assert is_text is True
        finally:
            os.unlink(temp_file_path)

    def test_is_text_file_binary(self):
        """测试二进制文件识别"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as temp_file:
            temp_file.write(b"\x00\x01\x02\x03\x04\x05")
            temp_file_path = temp_file.name

        try:
            is_text = FileUtils.is_text_file(temp_file_path)
            # 二进制文件应该返回False
            assert is_text is False
        finally:
            os.unlink(temp_file_path)
