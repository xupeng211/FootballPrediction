"""文件工具测试"""
import os
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.utils.file_utils import FileUtils

class TestFileUtils:
    """文件工具测试"""

    def test_ensure_dir(self):
        """测试确保目录存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test" / "subdir"
            result = FileUtils.ensure_dir(test_dir)
            assert result.exists()
            assert result.is_dir()

    def test_read_json(self):
        """测试读取JSON文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"key": "value", "number": 42}, f)
            f.flush()

            result = FileUtils.read_json(f.name)
            assert result == {"key": "value", "number": 42}
            Path(f.name).unlink()

    def test_read_json_not_found(self):
        """测试读取不存在的JSON文件"""
        with pytest.raises(FileNotFoundError):
            FileUtils.read_json("nonexistent.json")

    def test_write_json(self):
        """测试写入JSON文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"
            data = {"name": "test", "items": [1, 2, 3]}

            FileUtils.write_json(data, test_file)

            assert test_file.exists()
            result = FileUtils.read_json(test_file)
            assert result == data

    def test_get_file_hash(self):
        """测试获取文件哈希值"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()

            hash1 = FileUtils.get_file_hash(f.name)
            hash2 = FileUtils.get_file_hash(f.name)
            assert hash1 == hash2
            assert len(hash1) == 32  # MD5 hash length
            Path(f.name).unlink()

    def test_get_file_size(self):
        """测试获取文件大小"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()

            size = FileUtils.get_file_size(f.name)
            assert size > 0
            assert size == len("test content")
            Path(f.name).unlink()

    def test_get_file_size_not_exists(self):
        """测试获取不存在文件的大小"""
        size = FileUtils.get_file_size("nonexistent.txt")
        assert size == 0

    def test_ensure_directory_alias(self):
        """测试ensure_directory别名方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "alias_test"
            result = FileUtils.ensure_directory(test_dir)
            assert result.exists()
            assert result.is_dir()

    def test_read_json_file_success(self):
        """测试read_json_file成功读取"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "data"}, f)
            f.flush()

            result = FileUtils.read_json_file(f.name)
            assert result == {"test": "data"}
            Path(f.name).unlink()

    def test_read_json_file_not_found(self):
        """测试read_json_file读取不存在文件"""
        result = FileUtils.read_json_file("nonexistent.json")
        assert result is None

    def test_write_json_file_success(self):
        """测试write_json_file成功写入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "success.json"
            data = {"success": True}

            result = FileUtils.write_json_file(data, test_file)
            assert result is True
            assert test_file.exists()

    def test_write_json_file_failure(self):
        """测试write_json_file写入失败"""
        # 尝试写入到无效路径
        result = FileUtils.write_json_file({}, "/invalid/path/test.json")
        assert result is False

    def test_cleanup_old_files(self):
        """测试清理旧文件"""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一些文件
            old_file = Path(tmpdir) / "old.txt"
            new_file = Path(tmpdir) / "new.txt"

            old_file.write_text("old")
            new_file.write_text("new")

            # 修改旧文件的时间戳使其看起来更旧
            old_time = time.time() - (31 * 24 * 60 * 60)  # 31 days ago
            os.utime(old_file, (old_time, old_time))

            # 清理30天前的文件
            removed = FileUtils.cleanup_old_files(tmpdir, days=30)

            assert removed == 1
            assert not old_file.exists()
            assert new_file.exists()
