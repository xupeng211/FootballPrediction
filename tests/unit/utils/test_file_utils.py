"""
文件工具模块测试
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.utils.file_utils import FileUtils


class TestFileUtils:
    """测试文件工具类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 清理临时目录
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ensure_dir_new_directory(self):
        """测试创建新目录"""
        new_dir = self.temp_path / "new" / "nested" / "directory"

        result = FileUtils.ensure_dir(new_dir)

        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_dir_existing_directory(self):
        """测试已存在的目录"""
        existing_dir = self.temp_path / "existing"
        existing_dir.mkdir()

        result = FileUtils.ensure_dir(existing_dir)

        assert result == existing_dir
        assert existing_dir.exists()

    def test_ensure_dir_with_string_path(self):
        """测试字符串路径"""
        path_str = str(self.temp_path / "string_path")

        result = FileUtils.ensure_dir(path_str)

        assert isinstance(result, Path)
        assert result.exists()

    def test_read_json_success(self):
        """测试成功读取JSON文件"""
        test_data = {"key": "value", "number": 42, "bool": True}
        json_file = self.temp_path / "test.json"

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = FileUtils.read_json(json_file)

        assert result == test_data

    def test_read_json_file_not_found(self):
        """测试读取不存在的JSON文件"""
        non_existent = self.temp_path / "non_existent.json"

        with pytest.raises(FileNotFoundError):
            FileUtils.read_json(non_existent)

    def test_read_json_invalid_json(self):
        """测试读取无效的JSON文件"""
        invalid_json_file = self.temp_path / "invalid.json"

        with open(invalid_json_file, "w", encoding="utf-8") as f:
            f.write("{invalid json")

        with pytest.raises(FileNotFoundError):
            FileUtils.read_json(invalid_json_file)

    def test_read_json_with_string_path(self):
        """测试使用字符串路径读取JSON"""
        test_data = {"test": "data"}
        json_file = self.temp_path / "string_test.json"

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = FileUtils.read_json(str(json_file))

        assert result == test_data

    def test_write_json_success(self):
        """测试成功写入JSON文件"""
        test_data = {"name": "test", "items": [1, 2, 3]}
        json_file = self.temp_path / "write_test.json"

        FileUtils.write_json(test_data, json_file)

        assert json_file.exists()

        with open(json_file, "r", encoding="utf-8") as f:
            result = json.load(f)

        assert result == test_data

    def test_write_json_with_nested_directories(self):
        """测试写入到嵌套目录"""
        test_data = {"nested": True}
        nested_file = self.temp_path / "deep" / "nested" / "path.json"

        FileUtils.write_json(test_data, nested_file)

        assert nested_file.exists()
        assert nested_file.parent.exists()

    def test_write_json_without_ensure_dir(self):
        """测试不自动创建目录"""
        test_data = {"test": "data"}
        parent_dir = self.temp_path / "no_auto_create"
        json_file = parent_dir / "test.json"

        with pytest.raises(FileNotFoundError):
            FileUtils.write_json(test_data, json_file, ensure_dir=False)

    def test_write_json_preserves_existing_content(self):
        """测试写入时保留现有内容"""
        original_data = {"original": "content"}
        new_data = {"new": "content"}
        json_file = self.temp_path / "existing.json"

        # 写入原始数据
        FileUtils.write_json(original_data, json_file)

        # 写入新数据到不同文件
        new_file = self.temp_path / "new.json"
        FileUtils.write_json(new_data, new_file)

        # 验证原始文件未被修改
        with open(json_file, "r", encoding="utf-8") as f:
            result = json.load(f)

        assert result == original_data

    def test_get_file_hash_success(self):
        """测试成功获取文件哈希"""
        test_content = b"test content for hash"
        test_file = self.temp_path / "hash_test.txt"

        with open(test_file, "wb") as f:
            f.write(test_content)

        result = FileUtils.get_file_hash(test_file)

        # 验证哈希值一致性
        result2 = FileUtils.get_file_hash(test_file)
        assert result == result2

        # 验证哈希值长度（MD5应该是32位十六进制）
        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)

    def test_get_file_hash_large_file(self):
        """测试大文件的哈希计算"""
        test_file = self.temp_path / "large_file.txt"

        # 创建一个大于4096字节的文件
        with open(test_file, "wb") as f:
            f.write(b"x" * 5000)

        result = FileUtils.get_file_hash(test_file)

        assert len(result) == 32

    def test_get_file_hash_empty_file(self):
        """测试空文件的哈希"""
        empty_file = self.temp_path / "empty.txt"
        empty_file.touch()

        result = FileUtils.get_file_hash(empty_file)

        # 空文件的MD5应该是d41d8cd98f00b204e9800998ecf8427e
        assert result == "d41d8cd98f00b204e9800998ecf8427e"

    def test_get_file_hash_with_string_path(self):
        """测试使用字符串路径获取哈希"""
        test_content = b"string path test"
        test_file = self.temp_path / "string_hash.txt"

        with open(test_file, "wb") as f:
            f.write(test_content)

        result = FileUtils.get_file_hash(str(test_file))

        assert len(result) == 32

    def test_get_file_size_existing_file(self):
        """测试获取已存在文件的大小"""
        test_content = b"x" * 1000
        test_file = self.temp_path / "size_test.txt"

        with open(test_file, "wb") as f:
            f.write(test_content)

        result = FileUtils.get_file_size(test_file)

        assert result == 1000

    def test_get_file_size_nonexistent_file(self):
        """测试获取不存在文件的大小"""
        nonexistent = self.temp_path / "does_not_exist.txt"

        result = FileUtils.get_file_size(nonexistent)

        assert result == 0

    def test_get_file_size_empty_file(self):
        """测试获取空文件的大小"""
        empty_file = self.temp_path / "empty_size.txt"
        empty_file.touch()

        result = FileUtils.get_file_size(empty_file)

        assert result == 0

    @patch('os.path.getsize')
    def test_get_file_size_os_error(self, mock_getsize):
        """测试处理OSError的情况"""
        mock_getsize.side_effect = OSError("Permission denied")
        test_file = self.temp_path / "error_test.txt"
        test_file.touch()

        result = FileUtils.get_file_size(test_file)

        assert result == 0

    def test_ensure_directory_alias(self):
        """测试ensure_directory别名方法"""
        new_dir = self.temp_path / "alias_test"

        result = FileUtils.ensure_directory(new_dir)

        assert result == new_dir
        assert new_dir.exists()

    def test_read_json_file_success(self):
        """测试read_json_file成功读取"""
        test_data = {"alias": "test"}
        json_file = self.temp_path / "alias_read.json"

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = FileUtils.read_json_file(json_file)

        assert result == test_data

    def test_read_json_file_not_found_returns_none(self):
        """测试read_json_file读取不存在文件返回None"""
        nonexistent = self.temp_path / "alias_not_found.json"

        result = FileUtils.read_json_file(nonexistent)

        assert result is None

    def test_write_json_file_success(self):
        """测试write_json_file成功写入"""
        test_data = {"write": "alias test"}
        json_file = self.temp_path / "alias_write.json"

        result = FileUtils.write_json_file(test_data, json_file)

        assert result is True
        assert json_file.exists()

        with open(json_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data == test_data

    def test_write_json_file_failure_returns_false(self):
        """测试write_json_file失败返回False"""
        # 使用一个无法写入的路径
        invalid_path = "/invalid/path/that/should/not/exist/test.json"

        result = FileUtils.write_json_file({"test": "data"}, invalid_path)

        assert result is False

    def test_cleanup_old_files_no_files(self):
        """测试清理没有文件的目录"""
        empty_dir = self.temp_path / "empty"
        empty_dir.mkdir()

        result = FileUtils.cleanup_old_files(empty_dir, days=30)

        assert result == 0

    def test_cleanup_old_files_no_old_files(self):
        """测试清理没有旧文件的目录"""
        recent_dir = self.temp_path / "recent"
        recent_dir.mkdir()

        # 创建一个新文件
        recent_file = recent_dir / "new.txt"
        recent_file.write_text("recent content")

        result = FileUtils.cleanup_old_files(recent_dir, days=30)

        assert result == 0
        assert recent_file.exists()

    def test_cleanup_old_files_with_old_files(self):
        """测试清理包含旧文件的目录"""
        old_dir = self.temp_path / "old"
        old_dir.mkdir()

        # 创建旧文件
        old_file1 = old_dir / "old1.txt"
        old_file2 = old_dir / "old2.txt"
        old_file1.write_text("old content 1")
        old_file2.write_text("old content 2")

        # 修改文件时间为很久以前
        old_time = time.time() - (40 * 24 * 60 * 60)  # 40天前
        os.utime(old_file1, (old_time, old_time))
        os.utime(old_file2, (old_time, old_time))

        # 创建一个新文件
        new_file = old_dir / "new.txt"
        new_file.write_text("new content")

        result = FileUtils.cleanup_old_files(old_dir, days=30)

        assert result == 2
        assert not old_file1.exists()
        assert not old_file2.exists()
        assert new_file.exists()

    def test_cleanup_old_files_nonexistent_directory(self):
        """测试清理不存在的目录"""
        nonexistent = self.temp_path / "does_not_exist"

        result = FileUtils.cleanup_old_files(nonexistent, days=30)

        assert result == 0

    def test_cleanup_old_files_with_exception(self):
        """测试清理时处理异常"""
        # 创建一个目录
        test_dir = self.temp_path / "exception_test"
        test_dir.mkdir()

        # 创建一个文件
        test_file = test_dir / "test.txt"
        test_file.write_text("test")

        # 使文件无法删除（通过模拟权限错误）
        with patch.object(Path, 'unlink', side_effect=OSError("Permission denied")):
            result = FileUtils.cleanup_old_files(test_dir, days=0)

            assert result == 0

    def test_comprehensive_workflow(self):
        """测试综合工作流程"""
        # 创建目录
        work_dir = self.temp_path / "workflow"
        FileUtils.ensure_dir(work_dir)

        # 写入配置
        config = {"app": "test", "version": "1.0", "settings": {"debug": True}}
        config_file = work_dir / "config.json"
        FileUtils.write_json(config, config_file)

        # 读取配置
        loaded_config = FileUtils.read_json(config_file)
        assert loaded_config == config

        # 获取文件信息
        file_size = FileUtils.get_file_size(config_file)
        assert file_size > 0

        file_hash = FileUtils.get_file_hash(config_file)
        assert len(file_hash) == 32

        # 使用别名方法
        alias_result = FileUtils.read_json_file(config_file)
        assert alias_result == config

        write_success = FileUtils.write_json_file({"updated": True}, work_dir / "update.json")
        assert write_success is True

    def test_path_object_consistency(self):
        """测试Path对象的一致性"""
        # 确保所有方法都正确处理Path对象和字符串
        test_path = self.temp_path / "consistency"

        # 使用Path对象
        result1 = FileUtils.ensure_dir(test_path)
        assert isinstance(result1, Path)

        # 使用字符串
        str_path = str(test_path / "string")
        result2 = FileUtils.ensure_dir(str_path)
        assert isinstance(result2, Path)