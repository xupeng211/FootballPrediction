from unittest.mock import MagicMock, patch

"""
文件工具测试
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

# from src.utils.file_utils import FileUtils


@pytest.mark.unit
class TestFileUtils:
    """文件工具测试"""

    def test_ensure_dir(self):
        """测试确保目录存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建新目录
            new_dir = Path(tmpdir) / "new" / "sub" / "dir"
            _result = FileUtils.ensure_dir(new_dir)
            assert _result.exists()
            assert _result.is_dir()

            # 目录已存在
            _result = FileUtils.ensure_dir(new_dir)
            assert _result.exists()

            # 使用字符串路径
            str_dir = os.path.join(tmpdir, "string", "dir")
            _result = FileUtils.ensure_dir(str_dir)
            assert isinstance(result, Path)
            assert _result.exists()

    def test_ensure_directory_alias(self):
        """测试ensure_directory别名方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "alias" / "dir"
            _result = FileUtils.ensure_directory(new_dir)
            assert _result.exists()
            assert _result.is_dir()

    def test_write_and_read_json(self):
        """测试JSON文件读写"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            _data = {"name": "John", "age": 30, "active": True, "scores": [90, 85, 95]}

            # 写入JSON
            FileUtils.write_json(data, file_path)
            assert file_path.exists()

            # 读取JSON
            loaded_data = FileUtils.read_json(file_path)
            assert loaded_data == data

            # 验证文件内容格式
            content = file_path.read_text(encoding="utf-8")
            assert '"name": "John"' in content
            assert "  " in content  # 确认有缩进

    def test_write_json_with_ensure_dir(self):
        """测试写入JSON时自动创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "nested" / "dirs" / "test.json"
            _data = {"test": "data"}

            # 确保目录不存在
            assert not file_path.parent.exists()

            # 写入文件
            FileUtils.write_json(data, file_path, ensure_dir=True)
            assert file_path.exists()
            assert file_path.parent.exists()

            # 读取验证
            loaded = FileUtils.read_json(file_path)
            assert loaded == data

    def test_write_json_without_ensure_dir(self):
        """测试不自动创建目录时写入JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "nonexistent" / "test.json"
            _data = {"test": "data"}

            # 确保目录不存在
            assert not file_path.parent.exists()

            # 尝试写入应该失败
            with pytest.raises(FileNotFoundError):
                FileUtils.write_json(data, file_path, ensure_dir=False)

    def test_read_json_not_found(self):
        """测试读取不存在的JSON文件"""
        with pytest.raises(FileNotFoundError) as exc_info:
            FileUtils.read_json("/nonexistent/file.json")
            assert "无法读取JSON文件" in str(exc_info.value)

    def test_read_json_invalid_format(self):
        """测试读取无效格式的JSON文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "invalid.json"
            file_path.write_text("invalid json content")

            with pytest.raises(FileNotFoundError) as exc_info:
                FileUtils.read_json(file_path)
                assert "无法读取JSON文件" in str(exc_info.value)

    def test_get_file_hash(self):
        """测试获取文件哈希值"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            content = "Hello, World!"
            file_path.write_text(content, encoding="utf-8")

            # 计算哈希值
            hash_value = FileUtils.get_file_hash(file_path)
            assert isinstance(hash_value, str)
            assert len(hash_value) == 32  # MD5哈希长度

            # 相同内容应该有相同哈希
            file_path2 = Path(tmpdir) / "test2.txt"
            file_path2.write_text(content, encoding="utf-8")
            hash_value2 = FileUtils.get_file_hash(file_path2)
            assert hash_value == hash_value2

            # 不同内容应该有不同哈希
            file_path.write_text("Different content")
            hash_value3 = FileUtils.get_file_hash(file_path)
            assert hash_value3 != hash_value

    def test_get_file_size(self):
        """测试获取文件大小"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"

            # 不存在的文件
            size = FileUtils.get_file_size(file_path)
            assert size == 0

            # 创建文件
            content = "Hello, World!" * 100
            file_path.write_text(content, encoding="utf-8")
            size = FileUtils.get_file_size(file_path)
            assert size == len(content.encode("utf-8"))

            # 空文件
            empty_path = Path(tmpdir) / "empty.txt"
            empty_path.write_text("")
            size = FileUtils.get_file_size(empty_path)
            assert size == 0

    def test_read_json_file_alias(self):
        """测试read_json_file别名方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            _data = {"test": "data"}

            # 文件不存在
            _result = FileUtils.read_json_file(file_path)
            assert _result is None

            # 文件存在
            FileUtils.write_json(data, file_path)
            _result = FileUtils.read_json_file(file_path)
            assert _result == data

    def test_write_json_file_alias(self):
        """测试write_json_file别名方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            _data = {"test": "data"}

            # 成功写入
            _result = FileUtils.write_json_file(data, file_path)
            assert _result is True
            assert file_path.exists()

            # 验证内容
            loaded = FileUtils.read_json(file_path)
            assert loaded == data

    def test_write_json_file_alias_failure(self):
        """测试write_json_file失败情况"""
        # 尝试写入到无效路径
        _result = FileUtils.write_json_file({"test": "data"}, "/invalid/path/file.json")
        assert _result is False

    def test_cleanup_old_files(self):
        """测试清理旧文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)

            # 创建一些文件
            old_file1 = directory / "old1.txt"
            old_file2 = directory / "old2.txt"
            new_file = directory / "new.txt"

            old_file1.write_text("old content 1")
            old_file2.write_text("old content 2")
            new_file.write_text("new content")

            # 模拟文件时间（使用patch）
            with patch("time.time") as mock_time:
                mock_time.return_value = 1000000  # 当前时间
                old_time = 900000  # 100天前

                # 设置旧文件的修改时间
                os.utime(old_file1, (old_time, old_time))
                os.utime(old_file2, (old_time, old_time))

                # 清理超过10天的文件
                removed = FileUtils.cleanup_old_files(directory, days=10)
                assert removed == 2

                # 验证文件被删除
                assert not old_file1.exists()
                assert not old_file2.exists()
                assert new_file.exists()

    def test_cleanup_old_files_nonexistent_dir(self):
        """测试清理不存在的目录"""
        removed = FileUtils.cleanup_old_files("/nonexistent/directory")
        assert removed == 0

    def test_cleanup_old_files_with_exception(self):
        """测试清理时发生异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            file_path = directory / "test.txt"
            file_path.write_text("test")

            # 模拟iterdir抛出异常
            with patch.object(
                Path, "iterdir", side_effect=PermissionError("Permission denied")
            ):
                removed = FileUtils.cleanup_old_files(directory)
                assert removed == 0

    def test_path_handling(self):
        """测试路径处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 使用Path对象
            path_obj = Path(tmpdir) / "path_obj" / "test.json"
            _data = {"test": "path object"}
            FileUtils.write_json(data, path_obj)
            loaded = FileUtils.read_json(path_obj)
            assert loaded == data

            # 使用字符串路径
            path_str = os.path.join(tmpdir, "path_str", "test.json")
            FileUtils.write_json(data, path_str)
            loaded = FileUtils.read_json(path_str)
            assert loaded == data

    def test_unicode_handling(self):
        """测试Unicode处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "unicode.json"
            _data = {"chinese": "你好，世界！", "emoji": "🌍🚀", "special": "αβγδε"}

            # 写入和读取Unicode数据
            FileUtils.write_json(data, file_path)
            loaded = FileUtils.read_json(file_path)
            assert loaded == data

            # 验证文件编码
            content = file_path.read_bytes()
            assert b"\xe4\xbd\xa0" in content  # UTF-8编码的"你"

    def test_large_file_handling(self):
        """测试大文件处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "large.txt"

            # 创建大文件（1MB）
            large_content = "A" * (1024 * 1024)
            file_path.write_bytes(large_content.encode("utf-8"))

            # 计算哈希值
            hash_value = FileUtils.get_file_hash(file_path)
            assert isinstance(hash_value, str)
            assert len(hash_value) == 32

            # 获取文件大小
            size = FileUtils.get_file_size(file_path)
            assert size == len(large_content.encode("utf-8"))
