import json
import os
import time
from pathlib import Path
import pytest
from src.utils.file_utils import FileUtils

"""
测试文件处理工具模块
"""


class TestFileUtils:
    """测试FileUtils类"""

    def test_ensure_dir_creates_directory(self, tmp_path):
        """测试创建目录"""
        new_dir = tmp_path / "new" / "directory"
        result = FileUtils.ensure_dir(new_dir)
        assert result.exists()
        assert result.is_dir()
        assert isinstance(result, Path)

    def test_ensure_dir_existing_directory(self, tmp_path):
        """测试确保已存在的目录"""
        result = FileUtils.ensure_dir(tmp_path)
        assert result.exists()
        assert result == tmp_path

    def test_read_json_success(self, tmp_path):
        """测试成功读取JSON文件"""
        data = {"name": "测试", "value": 123}
        file_path = tmp_path / "test.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result = FileUtils.read_json(file_path)
        assert result == data

    def test_read_json_file_not_found(self):
        """测试读取不存在的JSON文件"""
        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json("nonexistent.json")

    def test_read_json_invalid_json(self, tmp_path):
        """测试读取无效的JSON文件"""
        file_path = tmp_path / "invalid.json"
        with open(file_path, "w") as f:
            f.write("{ invalid json }")

        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json(file_path)

    def test_write_json_success(self, tmp_path):
        """测试成功写入JSON文件"""
        data = {"name": "测试", "value": 123, "nested": {"key": "值"}}
        file_path = tmp_path / "subdir" / "test.json"

        FileUtils.write_json(data, file_path)

        assert file_path.exists()
        with open(file_path, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
        assert loaded_data == data

    def test_write_json_without_ensure_dir(self, tmp_path):
        """测试写入JSON文件但不确保目录存在"""
        data = {"test": "value"}
        file_path = tmp_path / "test.json"

        # 先创建文件
        file_path.touch()

        FileUtils.write_json(data, file_path, ensure_dir=False)

        with open(file_path, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
        assert loaded_data == data

    def test_get_file_hash(self, tmp_path):
        """测试获取文件哈希值"""
        file_path = tmp_path / "test.txt"
        content = "Hello, World!"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        hash_value = FileUtils.get_file_hash(file_path)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 hash length
        assert hash_value == "65a8e2798839704b846ef3d7a6c7207c"

    def test_get_file_hash_large_file(self, tmp_path):
        """测试获取大文件的哈希值"""
        file_path = tmp_path / "large.txt"

        # 创建大于4096字节的文件
        content = "A" * 5000
        with open(file_path, "w") as f:
            f.write(content)

        hash_value = FileUtils.get_file_hash(file_path)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32

    def test_get_file_size_existing_file(self, tmp_path):
        """测试获取已存在文件的大小"""
        file_path = tmp_path / "test.txt"
        content = "Hello, World!"

        with open(file_path, "w") as f:
            f.write(content)

        size = FileUtils.get_file_size(file_path)
        assert size == len(content.encode())

    def test_get_file_size_nonexistent_file(self):
        """测试获取不存在文件的大小"""
        size = FileUtils.get_file_size("nonexistent.txt")
        assert size == 0

    def test_ensure_directory_alias(self, tmp_path):
        """测试ensure_directory别名方法"""
        new_dir = tmp_path / "alias_test"
        result = FileUtils.ensure_directory(new_dir)
        assert result.exists()
        assert result.is_dir()

    def test_read_json_file_success(self, tmp_path):
        """测试read_json_file成功读取"""
        data = {"test": "value"}
        file_path = tmp_path / "test.json"

        with open(file_path, "w") as f:
            json.dump(data, f)

        result = FileUtils.read_json_file(file_path)
        assert result == data

    def test_write_json_file_success(self, tmp_path):
        """测试write_json_file成功写入"""
        data = {"test": "value"}
        file_path = tmp_path / "success.json"

        result = FileUtils.write_json_file(data, file_path)
        assert result is True
        assert file_path.exists()

        with open(file_path, "r") as f:
            loaded_data = json.load(f)
        assert loaded_data == data

    def test_write_json_file_failure(self, tmp_path):
        """测试write_json_file写入失败"""
        # 尝试写入到只读目录
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)

        try:
            file_path = read_only_dir / "test.json"
            result = FileUtils.write_json_file({"test": "value"}, file_path)
            assert result is False
        finally:
            # 恢复权限以便清理
            read_only_dir.chmod(0o755)

    def test_cleanup_old_files_no_directory(self):
        """测试清理不存在的目录"""
        count = FileUtils.cleanup_old_files("nonexistent_dir")
        assert count == 0

    def test_cleanup_old_files_empty_directory(self, tmp_path):
        """测试清理空目录"""
        count = FileUtils.cleanup_old_files(tmp_path)
        assert count == 0

    def test_cleanup_old_files_with_old_files(self, tmp_path):
        """测试清理旧文件"""

        # 创建一个旧文件
        old_file = tmp_path / "old.txt"
        old_file.write_text("old content")

        # 修改文件时间为很久以前
        old_time = time.time() - (40 * 24 * 60 * 60)  # 40天前
        os.utime(old_file, (old_time, old_time))

        # 创建一个新文件
        new_file = tmp_path / "new.txt"
        new_file.write_text("new content")

        # 清理30天前的文件
        count = FileUtils.cleanup_old_files(tmp_path, days=30)

        assert count == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_cleanup_old_files_permission_error(self, tmp_path):
        """测试清理文件时的权限错误"""
        import time

        # 创建文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # 修改文件时间为旧文件
        old_time = time.time() - (40 * 24 * 60 * 60)
        os.utime(test_file, (old_time, old_time))

        # 使目录只读
        tmp_path.chmod(0o444)

        try:
            count = FileUtils.cleanup_old_files(tmp_path, days=30)
            # 应该返回0，因为无法删除文件
            assert count == 0
        finally:
            # 恢复权限
            tmp_path.chmod(0o755)
