"""
Tests for src/utils/file_utils.py (Phase 5)

针对文件处理工具类的全面测试，旨在提升覆盖率至 ≥60%
覆盖JSON文件操作、目录创建、文件哈希、大小获取等核心功能
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

# Import the module to ensure coverage tracking
import src.utils.file_utils
from src.utils.file_utils import FileUtils


class TestFileUtilsDirectoryOperations:
    """目录操作测试"""

    def test_ensure_dir_new_directory(self):
        """测试创建新目录"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = Path(tmp_dir) / "test_new_dir"

            result = FileUtils.ensure_dir(test_path)

            assert result == test_path
            assert test_path.exists()
            assert test_path.is_dir()

    def test_ensure_dir_existing_directory(self):
        """测试已存在的目录"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = Path(tmp_dir)

            result = FileUtils.ensure_dir(test_path)

            assert result == test_path
            assert test_path.exists()
            assert test_path.is_dir()

    def test_ensure_dir_nested_path(self):
        """测试嵌套路径创建"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = Path(tmp_dir) / "level1" / "level2" / "level3"

            result = FileUtils.ensure_dir(test_path)

            assert result == test_path
            assert test_path.exists()
            assert test_path.is_dir()

    def test_ensure_dir_string_input(self):
        """测试字符串输入"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path_str = os.path.join(tmp_dir, "string_dir")

            result = FileUtils.ensure_dir(test_path_str)

            assert result == Path(test_path_str)
            assert Path(test_path_str).exists()

    def test_ensure_directory_alias(self):
        """测试别名方法"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = Path(tmp_dir) / "alias_test"

            result = FileUtils.ensure_directory(test_path)

            assert result == test_path
            assert test_path.exists()


class TestFileUtilsJSONOperations:
    """JSON文件操作测试"""

    def test_read_json_success(self):
        """测试成功读取JSON文件"""
        test_data = {"key": "value", "number": 42}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(test_data, tmp_file)
            tmp_file.flush()

            try:
                result = FileUtils.read_json(tmp_file.name)
                assert result == test_data
            finally:
                os.unlink(tmp_file.name)

    def test_read_json_file_not_found(self):
        """测试读取不存在的文件"""
        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json("/nonexistent/file.json")

    def test_read_json_invalid_json(self):
        """测试读取无效JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_file.write("invalid json content")
            tmp_file.flush()

            try:
                with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
                    FileUtils.read_json(tmp_file.name)
            finally:
                os.unlink(tmp_file.name)

    def test_write_json_success(self):
        """测试成功写入JSON文件"""
        test_data = {"test": "data", "number": 123}

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test.json"

            FileUtils.write_json(test_data, file_path)

            assert file_path.exists()
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_write_json_with_nested_directory(self):
        """测试写入JSON到嵌套目录"""
        test_data = {"nested": True}

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "nested" / "dir" / "test.json"

            FileUtils.write_json(test_data, file_path, ensure_dir=True)

            assert file_path.exists()
            assert file_path.parent.exists()

    def test_write_json_without_ensure_dir(self):
        """测试不创建目录写入JSON"""
        test_data = {"test": "data"}

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test.json"

            FileUtils.write_json(test_data, file_path, ensure_dir=False)

            assert file_path.exists()

    def test_read_json_file_alias_success(self):
        """测试别名方法成功读取"""
        test_data = {"alias": "test"}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(test_data, tmp_file)
            tmp_file.flush()

            try:
                result = FileUtils.read_json_file(tmp_file.name)
                assert result == test_data
            finally:
                os.unlink(tmp_file.name)

    def test_read_json_file_alias_not_found(self):
        """测试别名方法读取不存在文件"""
        result = FileUtils.read_json_file("/nonexistent/file.json")
        assert result is None

    def test_write_json_file_alias_success(self):
        """测试别名方法成功写入"""
        test_data = {"alias": "write"}

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "alias_test.json"

            result = FileUtils.write_json_file(test_data, file_path)

            assert result is True
            assert file_path.exists()

    def test_write_json_file_alias_failure(self):
        """测试别名方法写入失败"""
        test_data = {"test": "data"}

        # 尝试写入到只读目录
        with patch('src.utils.file_utils.FileUtils.write_json', side_effect=PermissionError("Permission denied")):
            result = FileUtils.write_json_file(test_data, "/readonly/path.json")
            assert result is False


class TestFileUtilsFileOperations:
    """文件操作测试"""

    def test_get_file_hash_success(self):
        """测试成功获取文件哈希"""
        test_content = b"test file content for hashing"

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(test_content)
            tmp_file.flush()

            try:
                file_hash = FileUtils.get_file_hash(tmp_file.name)

                # 验证是32字符的十六进制字符串
                assert len(file_hash) == 32
                assert all(c in "0123456789abcdef" for c in file_hash)

                # 验证哈希一致性
                file_hash2 = FileUtils.get_file_hash(tmp_file.name)
                assert file_hash == file_hash2

            finally:
                os.unlink(tmp_file.name)

    def test_get_file_hash_empty_file(self):
        """测试空文件哈希"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            pass  # 创建空文件

            try:
                file_hash = FileUtils.get_file_hash(tmp_file.name)

                # 空文件的MD5哈希值
                expected_hash = "d41d8cd98f00b204e9800998ecf8427e"
                assert file_hash == expected_hash

            finally:
                os.unlink(tmp_file.name)

    def test_get_file_size_existing_file(self):
        """测试获取存在文件的大小"""
        test_content = b"test content with known size"

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(test_content)
            tmp_file.flush()

            try:
                file_size = FileUtils.get_file_size(tmp_file.name)
                assert file_size == len(test_content)

            finally:
                os.unlink(tmp_file.name)

    def test_get_file_size_nonexistent_file(self):
        """测试获取不存在文件的大小"""
        file_size = FileUtils.get_file_size("/nonexistent/file.txt")
        assert file_size == 0

    def test_get_file_size_empty_file(self):
        """测试获取空文件的大小"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            pass  # 创建空文件

            try:
                file_size = FileUtils.get_file_size(tmp_file.name)
                assert file_size == 0

            finally:
                os.unlink(tmp_file.name)

    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_get_file_size_os_error(self, mock_getsize, mock_exists):
        """测试OS错误处理"""
        mock_exists.return_value = True
        mock_getsize.side_effect = OSError("Permission denied")

        file_size = FileUtils.get_file_size("test_file.txt")
        assert file_size == 0


class TestFileUtilsCleanupOperations:
    """文件清理操作测试"""

    def test_cleanup_old_files_nonexistent_directory(self):
        """测试清理不存在的目录"""
        result = FileUtils.cleanup_old_files("/nonexistent/directory")
        assert result == 0

    def test_cleanup_old_files_empty_directory(self):
        """测试清理空目录"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = FileUtils.cleanup_old_files(tmp_dir)
            assert result == 0

    def test_cleanup_old_files_success(self):
        """测试成功清理旧文件"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 创建一些测试文件
            old_file = Path(tmp_dir) / "old_file.txt"
            recent_file = Path(tmp_dir) / "recent_file.txt"

            old_file.write_text("old content")
            recent_file.write_text("recent content")

            # 修改旧文件的修改时间
            old_time = time.time() - (35 * 24 * 60 * 60)  # 35天前
            os.utime(old_file, (old_time, old_time))

            result = FileUtils.cleanup_old_files(tmp_dir, days=30)

            assert result == 1
            assert not old_file.exists()
            assert recent_file.exists()

    def test_cleanup_old_files_with_subdirectories(self):
        """测试清理包含子目录的目录"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 创建文件和子目录
            test_file = Path(tmp_dir) / "test_file.txt"
            sub_dir = Path(tmp_dir) / "subdir"

            test_file.write_text("content")
            sub_dir.mkdir()

            # 修改文件时间为很久以前
            old_time = time.time() - (40 * 24 * 60 * 60)
            os.utime(test_file, (old_time, old_time))

            result = FileUtils.cleanup_old_files(tmp_dir, days=30)

            assert result == 1
            assert not test_file.exists()
            assert sub_dir.exists()  # 子目录应该保留

    @patch('pathlib.Path.iterdir')
    def test_cleanup_old_files_exception_handling(self, mock_iterdir):
        """测试清理过程中的异常处理"""
        mock_iterdir.side_effect = PermissionError("Permission denied")

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = FileUtils.cleanup_old_files(tmp_dir)
            assert result == 0

    def test_cleanup_old_files_custom_days(self):
        """测试自定义天数清理"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test_file.txt"
            test_file.write_text("content")

            # 修改文件时间为5天前
            old_time = time.time() - (5 * 24 * 60 * 60)
            os.utime(test_file, (old_time, old_time))

            # 用7天清理，文件应该被删除
            result = FileUtils.cleanup_old_files(tmp_dir, days=3)
            assert result == 1
            assert not test_file.exists()


class TestFileUtilsPathHandling:
    """路径处理测试"""

    def test_path_types_consistency(self):
        """测试不同路径类型的一致性"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 字符串路径
            str_path = os.path.join(tmp_dir, "string_path")
            str_result = FileUtils.ensure_dir(str_path)

            # Path对象路径
            path_obj = Path(tmp_dir) / "path_object"
            path_result = FileUtils.ensure_dir(path_obj)

            assert isinstance(str_result, Path)
            assert isinstance(path_result, Path)
            assert str_result.exists()
            assert path_result.exists()

    def test_unicode_path_handling(self):
        """测试Unicode路径处理"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            unicode_path = Path(tmp_dir) / "测试目录"

            result = FileUtils.ensure_dir(unicode_path)

            assert result == unicode_path
            assert unicode_path.exists()

    def test_json_unicode_handling(self):
        """测试JSON Unicode处理"""
        unicode_data = {
            "中文": "测试",
            "emoji": "😀🚀",
            "русский": "тест"
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "unicode.json"

            FileUtils.write_json(unicode_data, file_path)
            result = FileUtils.read_json(file_path)

            assert result == unicode_data


class TestFileUtilsIntegration:
    """集成测试"""

    def test_full_json_workflow(self):
        """测试完整的JSON工作流程"""
        test_data = {
            "config": {
                "version": "1.0",
                "settings": [1, 2, 3]
            },
            "metadata": {
                "created": "2024-01-01",
                "author": "test"
            }
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / "config" / "nested"
            file_path = config_dir / "config.json"

            # 写入JSON文件（包括目录创建）
            FileUtils.write_json(test_data, file_path, ensure_dir=True)

            # 验证目录和文件存在
            assert config_dir.exists()
            assert file_path.exists()

            # 读取并验证数据
            loaded_data = FileUtils.read_json(file_path)
            assert loaded_data == test_data

            # 获取文件信息
            file_size = FileUtils.get_file_size(file_path)
            file_hash = FileUtils.get_file_hash(file_path)

            assert file_size > 0
            assert len(file_hash) == 32

    def test_alias_methods_consistency(self):
        """测试别名方法的一致性"""
        test_data = {"alias_test": True}

        with tempfile.TemporaryDirectory() as tmp_dir:
            # 使用主方法
            main_dir = FileUtils.ensure_dir(Path(tmp_dir) / "main")
            main_file = main_dir / "main.json"
            FileUtils.write_json(test_data, main_file)
            main_result = FileUtils.read_json(main_file)

            # 使用别名方法
            alias_dir = FileUtils.ensure_directory(Path(tmp_dir) / "alias")
            alias_file = alias_dir / "alias.json"
            FileUtils.write_json_file(test_data, alias_file)
            alias_result = FileUtils.read_json_file(alias_file)

            # 验证结果一致性
            assert main_result == alias_result == test_data


class TestFileUtilsErrorHandling:
    """错误处理测试"""

    @patch('builtins.open')
    def test_write_json_io_error(self, mock_open):
        """测试写入JSON时的IO错误"""
        mock_open.side_effect = IOError("IO Error")

        with pytest.raises(IOError):
            FileUtils.write_json({"test": "data"}, "test.json")

    @patch('builtins.open')
    def test_get_file_hash_io_error(self, mock_open):
        """测试获取文件哈希时的IO错误"""
        mock_open.side_effect = IOError("Cannot open file")

        with pytest.raises(IOError):
            FileUtils.get_file_hash("test.txt")

    def test_path_edge_cases(self):
        """测试路径边界情况"""
        # 测试根路径
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 测试相对路径
            relative_path = "relative/path"
            abs_result = FileUtils.ensure_dir(Path(tmp_dir) / relative_path)
            assert abs_result.exists()

    @patch('pathlib.Path.mkdir')
    def test_ensure_dir_permission_error(self, mock_mkdir):
        """测试目录创建权限错误"""
        mock_mkdir.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            FileUtils.ensure_dir("/permission/denied/path")


class TestFileUtilsPerformance:
    """性能相关测试"""

    def test_large_file_hash(self):
        """测试大文件哈希性能"""
        # 创建一个相对较大的文件用于测试
        large_content = b"x" * (1024 * 10)  # 10KB

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(large_content)
            tmp_file.flush()

            try:
                import time
                start_time = time.time()
                file_hash = FileUtils.get_file_hash(tmp_file.name)
                end_time = time.time()

                # 验证哈希正确性
                assert len(file_hash) == 32
                # 验证性能（应该很快）
                assert (end_time - start_time) < 1.0

            finally:
                os.unlink(tmp_file.name)

    def test_many_small_files_cleanup(self):
        """测试清理多个小文件的性能"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 创建多个小文件
            old_time = time.time() - (40 * 24 * 60 * 60)  # 40天前

            for i in range(50):
                file_path = Path(tmp_dir) / f"file_{i}.txt"
                file_path.write_text(f"content {i}")
                os.utime(file_path, (old_time, old_time))

            import time as time_module
            start_time = time_module.time()
            result = FileUtils.cleanup_old_files(tmp_dir, days=30)
            end_time = time_module.time()

            assert result == 50
            assert (end_time - start_time) < 2.0  # 应该在2秒内完成