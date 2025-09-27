"""
Auto-generated tests for src.utils.file_utils module
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.utils.file_utils import FileUtils


class TestFileUtils:
    """测试文件处理工具类"""

    def test_ensure_dir_new_directory(self):
        """测试创建新目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new" / "nested" / "directory"
            result = FileUtils.ensure_dir(new_dir)
            assert result == new_dir
            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_ensure_dir_existing_directory(self):
        """测试已存在目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_dir = Path(temp_dir) / "existing"
            existing_dir.mkdir()
            result = FileUtils.ensure_dir(existing_dir)
            assert result == existing_dir
            assert existing_dir.exists()

    def test_ensure_dir_string_path(self):
        """测试字符串路径"""
        with tempfile.TemporaryDirectory() as temp_dir:
            string_path = str(Path(temp_dir) / "string_path")
            result = FileUtils.ensure_dir(string_path)
            assert isinstance(result, Path)
            assert result.exists()

    def test_read_json_existing_file(self):
        """测试读取存在的JSON文件"""
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file_path = f.name

        try:
            result = FileUtils.read_json(temp_file_path)
            assert result == test_data
        finally:
            os.unlink(temp_file_path)

    def test_read_json_nonexistent_file(self):
        """测试读取不存在的JSON文件"""
        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json("/nonexistent/file.json")

    def test_read_json_invalid_json(self):
        """测试读取无效JSON文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file_path = f.name

        try:
            with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
                FileUtils.read_json(temp_file_path)
        finally:
            os.unlink(temp_file_path)

    def test_write_json_new_file(self):
        """测试写入新JSON文件"""
        test_data = {"key": "value", "number": 42}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"
            FileUtils.write_json(test_data, file_path)

            assert file_path.exists()
            with open(file_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            assert result_data == test_data

    def test_write_json_with_ensure_dir(self):
        """测试写入JSON文件并自动创建目录"""
        test_data = {"key": "value"}

        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nested" / "directory" / "test.json"
            FileUtils.write_json(test_data, nested_path, ensure_dir=True)

            assert nested_path.exists()
            assert nested_path.parent.exists()

    def test_write_json_without_ensure_dir(self):
        """测试写入JSON文件但不创建目录"""
        test_data = {"key": "value"}

        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nonexistent" / "test.json"

            with pytest.raises(FileNotFoundError):
                FileUtils.write_json(test_data, nested_path, ensure_dir=False)

    def test_get_file_hash_existing_file(self):
        """测试获取存在文件的哈希值"""
        test_content = "test content for hashing"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(test_content)
            temp_file_path = f.name

        try:
            hash1 = FileUtils.get_file_hash(temp_file_path)
            hash2 = FileUtils.get_file_hash(temp_file_path)

            assert isinstance(hash1, str)
            assert len(hash1) == 32  # MD5 hash length
            assert hash1 == hash2  # Same file should have same hash
        finally:
            os.unlink(temp_file_path)

    def test_get_file_hash_different_files(self):
        """测试不同文件有不同的哈希值"""
        content1 = "content one"
        content2 = "content two"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f1:
            f1.write(content1)
            file1_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f2:
            f2.write(content2)
            file2_path = f2.name

        try:
            hash1 = FileUtils.get_file_hash(file1_path)
            hash2 = FileUtils.get_file_hash(file2_path)

            assert hash1 != hash2
        finally:
            os.unlink(file1_path)
            os.unlink(file2_path)

    def test_get_file_size_existing_file(self):
        """测试获取存在文件的大小"""
        test_content = "test content" * 100  # 13 * 100 = 1300 bytes

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(test_content)
            temp_file_path = f.name

        try:
            size = FileUtils.get_file_size(temp_file_path)
            assert size == len(test_content.encode('utf-8'))
        finally:
            os.unlink(temp_file_path)

    def test_get_file_size_nonexistent_file(self):
        """测试获取不存在文件的大小"""
        size = FileUtils.get_file_size("/nonexistent/file.txt")
        assert size == 0

    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_get_file_size_os_error(self, mock_exists, mock_getsize):
        """测试获取文件大小时的OS错误"""
        mock_exists.return_value = True
        mock_getsize.side_effect = OSError("Permission denied")

        size = FileUtils.get_file_size("/some/file.txt")
        assert size == 0

    def test_ensure_directory_alias_method(self):
        """测试ensure_directory别名方法"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "alias_test"
            result = FileUtils.ensure_directory(new_dir)
            assert result == new_dir
            assert new_dir.exists()

    def test_read_json_file_existing(self):
        """测试read_json_file读取存在文件"""
        test_data = {"key": "value"}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file_path = f.name

        try:
            result = FileUtils.read_json_file(temp_file_path)
            assert result == test_data
        finally:
            os.unlink(temp_file_path)

    def test_read_json_file_nonexistent(self):
        """测试read_json_file读取不存在文件"""
        result = FileUtils.read_json_file("/nonexistent/file.json")
        assert result is None

    def test_write_json_file_success(self):
        """测试write_json_file成功写入"""
        test_data = {"key": "value"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"
            result = FileUtils.write_json_file(test_data, file_path)

            assert result is True
            assert file_path.exists()

            with open(file_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            assert saved_data == test_data

    @patch('src.utils.file_utils.FileUtils.write_json')
    def test_write_json_file_failure(self, mock_write_json):
        """测试write_json_file失败情况"""
        mock_write_json.side_effect = Exception("Write error")

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"
            result = FileUtils.write_json_file({"key": "value"}, file_path)

            assert result is False

    @patch('time.time')
    def test_cleanup_old_files_success(self, mock_time):
        """测试成功清理旧文件"""
        mock_time.return_value = 1000000  # Current time

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Create old file (modified 31 days ago)
            old_file = temp_dir_path / "old_file.txt"
            old_file.write_text("old content")

            # Create new file (modified recently)
            new_file = temp_dir_path / "new_file.txt"
            new_file.write_text("new content")

            # Mock file modification times
            old_time = 1000000 - (31 * 24 * 60 * 60)  # 31 days ago
            new_time = 1000000 - (1 * 24 * 60 * 60)   # 1 day ago

            with patch.object(Path, 'stat') as mock_stat:
                # Configure old file stat
                old_stat = MagicMock()
                old_stat.st_mtime = old_time
                # Configure new file stat
                new_stat = MagicMock()
                new_stat.st_mtime = new_time

                def stat_side_effect(self):
                    if self.name.endswith('old_file.txt'):
                        return old_stat
                    else:
                        return new_stat

                mock_stat.side_effect = stat_side_effect

                removed_count = FileUtils.cleanup_old_files(temp_dir, 30)

                assert removed_count == 1
                assert not old_file.exists()
                assert new_file.exists()

    def test_cleanup_old_files_nonexistent_directory(self):
        """测试清理不存在的目录"""
        result = FileUtils.cleanup_old_files("/nonexistent/directory", 30)
        assert result == 0

    @patch('time.time')
    @patch('Path.iterdir')
    def test_cleanup_old_files_with_exception(self, mock_iterdir, mock_time):
        """测试清理文件时遇到异常"""
        mock_time.return_value = 1000000
        mock_iterdir.side_effect = Exception("Directory access error")

        with tempfile.TemporaryDirectory() as temp_dir:
            result = FileUtils.cleanup_old_files(temp_dir, 30)
            assert result == 0  # Should handle exception gracefully

    def test_cleanup_old_files_no_files_to_remove(self):
        """测试没有需要删除的文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Create recent file
            recent_file = temp_dir_path / "recent_file.txt"
            recent_file.write_text("recent content")

            with patch('time.time', return_value=1000000):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value = MagicMock()
                    mock_stat.return_value.st_mtime = 1000000 - (1 * 24 * 60 * 60)  # 1 day ago

                    removed_count = FileUtils.cleanup_old_files(temp_dir, 30)

                    assert removed_count == 0
                    assert recent_file.exists()

    # Integration tests
    def test_file_operations_workflow(self):
        """测试文件操作工作流程"""
        test_data = {"name": "test", "value": 42, "items": [1, 2, 3]}

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure
            data_dir = Path(temp_dir) / "data" / "subdir"
            FileUtils.ensure_dir(data_dir)

            # Write JSON file
            json_file = data_dir / "test.json"
            FileUtils.write_json(test_data, json_file)

            # Read back
            read_data = FileUtils.read_json(json_file)
            assert read_data == test_data

            # Get file info
            file_size = FileUtils.get_file_size(json_file)
            assert file_size > 0

            file_hash = FileUtils.get_file_hash(json_file)
            assert isinstance(file_hash, str)
            assert len(file_hash) == 32

    def test_path_handling_string_vs_path(self):
        """测试字符串路径和Path对象的兼容性"""
        with tempfile.TemporaryDirectory() as temp_dir:
            string_path = str(temp_dir) + "/string_test"
            path_object = Path(temp_dir) / "path_test"

            # Test with string path
            result1 = FileUtils.ensure_dir(string_path)
            assert isinstance(result1, Path)
            assert result1.exists()

            # Test with Path object
            result2 = FileUtils.ensure_dir(path_object)
            assert isinstance(result2, Path)
            assert result2.exists()

    @pytest.mark.parametrize("test_data", [
        {"simple": "value"},
        {"nested": {"dict": {"with": "values"}}},
        {"list": [1, 2, 3, "four", {"five": 5}]},
        {"mixed": {"string": "text", "number": 42, "bool": True, "null": None}}
    ])
    def test_json_serialization_deserialization(self, test_data):
        """测试JSON序列化和反序列化的往返一致性"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"

            # Write data
            FileUtils.write_json(test_data, file_path)

            # Read back
            read_data = FileUtils.read_json(file_path)

            assert read_data == test_data