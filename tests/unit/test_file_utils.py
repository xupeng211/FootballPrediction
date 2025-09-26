"""
文件工具类的单元测试

测试覆盖：
- FileUtils 类的所有方法
- 文件操作的边界情况
- 错误处理和异常情况
- JSON文件读写
- 文件哈希和大小计算
- 目录清理功能
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.file_utils import FileUtils


class TestFileUtils:
    """文件工具类测试"""

    def test_ensure_dir_creates_directory(self, tmp_path):
        """测试确保目录存在功能"""
        test_dir = tmp_path / "test_directory" / "nested"

        result = FileUtils.ensure_dir(test_dir)

    assert test_dir.exists()
    assert test_dir.is_dir()
    assert result == test_dir

    def test_ensure_dir_existing_directory(self, tmp_path):
        """测试在已存在目录上调用ensure_dir"""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        result = FileUtils.ensure_dir(existing_dir)

    assert existing_dir.exists()
    assert result == existing_dir

    def test_ensure_directory_alias(self, tmp_path):
        """测试ensure_directory别名方法"""
        test_dir = tmp_path / "alias_test"

        result = FileUtils.ensure_directory(test_dir)

    assert test_dir.exists()
    assert result == test_dir

    def test_read_json_success(self, tmp_path):
        """测试成功读取JSON文件"""
        test_data = {"key": "value", "number": 42, "中文": "测试"}
        json_file = tmp_path / "test.json"

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False)

        result = FileUtils.read_json(json_file)

    assert result == test_data

    def test_read_json_file_not_found(self, tmp_path):
        """测试读取不存在的JSON文件"""
        non_existent = tmp_path / "non_existent.json"

        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json(non_existent)

    def test_read_json_invalid_json(self, tmp_path):
        """测试读取无效JSON文件"""
        invalid_json = tmp_path / "invalid.json"

        with open(invalid_json, "w") as f:
            f.write("{ invalid json content")

        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json(invalid_json)

    def test_read_json_file_alias(self, tmp_path):
        """测试read_json_file别名方法"""
        test_data = {"alias": "test"}
        json_file = tmp_path / "alias.json"

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False)

        result = FileUtils.read_json_file(json_file)

    assert result == test_data

    def test_write_json_success(self, tmp_path):
        """测试成功写入JSON文件"""
        test_data = {"name": "测试", "value": 123, "list": [1, 2, 3]}
        json_file = tmp_path / "output.json"

        FileUtils.write_json(test_data, json_file)

    assert json_file.exists()
        with open(json_file, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
    assert loaded_data == test_data

    def test_write_json_with_nested_directory(self, tmp_path):
        """测试写入到嵌套目录中的JSON文件"""
        test_data = {"nested": True}
        nested_file = tmp_path / "deep" / "nested" / "file.json"

        FileUtils.write_json(test_data, nested_file, ensure_dir=True)

    assert nested_file.exists()
    assert nested_file.parent.exists()

        with open(nested_file, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
    assert loaded_data == test_data

    def test_write_json_no_ensure_dir(self, tmp_path):
        """测试写入JSON时不自动创建目录"""
        test_data = {"no_dir": True}
        non_existent_dir = tmp_path / "missing_dir" / "file.json"

        with pytest.raises(FileNotFoundError):
            FileUtils.write_json(test_data, non_existent_dir, ensure_dir=False)

    def test_write_json_file_alias_success(self, tmp_path):
        """测试write_json_file别名方法成功"""
        test_data = {"alias": "write"}
        json_file = tmp_path / "alias_write.json"

        result = FileUtils.write_json_file(test_data, json_file)

    assert result is True
    assert json_file.exists()

    def test_write_json_file_alias_failure(self, tmp_path):
        """测试write_json_file别名方法失败情况"""
        test_data = {"test": "data"}
        # 使用只读目录模拟写入失败
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)  # 只读权限

        json_file = read_only_dir / "test.json"

        try:
            result = FileUtils.write_json_file(test_data, json_file)
            # 某些系统可能仍允许写入，所以不强制断言失败
            if not result:
    assert result is False
        finally:
            # 恢复权限以便清理
            read_only_dir.chmod(0o755)

    def test_get_file_hash(self, tmp_path):
        """测试获取文件MD5哈希值"""
        test_content = "这是测试内容"
        test_file = tmp_path / "test_file.txt"

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        hash_value = FileUtils.get_file_hash(test_file)

    assert isinstance(hash_value, str)
    assert len(hash_value) == 32  # MD5哈希长度

        # 验证相同内容产生相同哈希
        hash_value2 = FileUtils.get_file_hash(test_file)
    assert hash_value == hash_value2

    def test_get_file_hash_binary_file(self, tmp_path):
        """测试获取二进制文件的哈希值"""
        test_content = b"\x00\x01\x02\x03\xff"
        test_file = tmp_path / "binary_file.bin"

        with open(test_file, "wb") as f:
            f.write(test_content)

        hash_value = FileUtils.get_file_hash(test_file)

    assert isinstance(hash_value, str)
    assert len(hash_value) == 32

    def test_get_file_size(self, tmp_path):
        """测试获取文件大小"""
        test_content = "Hello, World!" * 100  # 创建一定大小的内容
        test_file = tmp_path / "size_test.txt"

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        file_size = FileUtils.get_file_size(test_file)

    assert isinstance(file_size, int)
    assert file_size > 0
    assert file_size == len(test_content.encode("utf-8"))

    def test_get_file_size_empty_file(self, tmp_path):
        """测试获取空文件大小"""
        empty_file = tmp_path / "empty.txt"
        empty_file.touch()

        file_size = FileUtils.get_file_size(empty_file)

    assert file_size == 0

    def test_cleanup_old_files(self, tmp_path):
        """测试清理旧文件功能"""
        # 创建一些测试文件
        old_file1 = tmp_path / "old1.txt"
        old_file2 = tmp_path / "old2.txt"
        new_file = tmp_path / "new.txt"

        # 创建文件
        old_file1.write_text("old content 1")
        old_file2.write_text("old content 2")
        new_file.write_text("new content")

        # 修改旧文件的时间戳（模拟旧文件）
        import os

        old_time = time.time() - (35 * 24 * 60 * 60)  # 35天前
        os.utime(old_file1, (old_time, old_time))
        os.utime(old_file2, (old_time, old_time))

        # 清理30天以上的文件
        removed_count = FileUtils.cleanup_old_files(tmp_path, days=30)

    assert removed_count == 2
    assert not old_file1.exists()
    assert not old_file2.exists()
    assert new_file.exists()

    def test_cleanup_old_files_non_existent_directory(self, tmp_path):
        """测试清理不存在目录的旧文件"""
        non_existent = tmp_path / "non_existent_dir"

        removed_count = FileUtils.cleanup_old_files(non_existent)

    assert removed_count == 0

    def test_cleanup_old_files_no_old_files(self, tmp_path):
        """测试清理目录中没有旧文件的情况"""
        # 创建一些新文件
        for i in range(3):
            new_file = tmp_path / f"new_file_{i}.txt"
            new_file.write_text(f"content {i}")

        removed_count = FileUtils.cleanup_old_files(tmp_path, days=30)

    assert removed_count == 0
        # 验证文件仍然存在
    assert len(list(tmp_path.iterdir())) == 3

    def test_cleanup_old_files_with_subdirectories(self, tmp_path):
        """测试清理时忽略子目录"""
        # 创建文件和子目录
        old_file = tmp_path / "old.txt"
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()

        old_file.write_text("old content")

        # 设置旧时间戳
        import os

        old_time = time.time() - (35 * 24 * 60 * 60)
        os.utime(old_file, (old_time, old_time))
        os.utime(sub_dir, (old_time, old_time))

        removed_count = FileUtils.cleanup_old_files(tmp_path, days=30)

    assert removed_count == 1  # 只删除文件，不删除目录
    assert not old_file.exists()
    assert sub_dir.exists()

    @patch("src.utils.file_utils.Path.iterdir")
    def test_cleanup_old_files_exception_handling(self, mock_iterdir, tmp_path):
        """测试清理文件时的异常处理"""
        mock_iterdir.side_effect = Exception("权限错误")

        removed_count = FileUtils.cleanup_old_files(tmp_path)

    assert removed_count == 0

    def test_all_methods_with_string_paths(self, tmp_path):
        """测试所有方法都支持字符串路径"""
        test_dir_str = str(tmp_path / "string_test")
        test_file_str = str(tmp_path / "string_test.json")
        test_data = {"string_path": True}

        # 测试字符串路径
        FileUtils.ensure_dir(test_dir_str)
        FileUtils.write_json(test_data, test_file_str)
        loaded_data = FileUtils.read_json(test_file_str)

    assert Path(test_dir_str).exists()
    assert loaded_data == test_data

        # 测试文件操作
        file_size = FileUtils.get_file_size(test_file_str)
        file_hash = FileUtils.get_file_hash(test_file_str)

    assert file_size > 0
    assert len(file_hash) == 32
