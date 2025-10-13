"""
文件工具模块完整测试
"""

import pytest
import json
import os
import tempfile
import time
from pathlib import Path
# from src.utils.file_utils import FileUtils


class TestFileUtils:
    """文件工具类测试"""

    def test_ensure_dir_create_new(self):
        """测试创建新目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "new_directory" / "subdir"
            _result = FileUtils.ensure_dir(new_dir)

            assert result.exists()
            assert result.is_dir()
            assert _result == new_dir

    def test_ensure_dir_existing(self):
        """测试确保已存在的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            existing_dir = Path(tmpdir) / "existing"
            existing_dir.mkdir()

            _result = FileUtils.ensure_dir(existing_dir)
            assert result.exists()
            assert result.is_dir()

    def test_ensure_directory_alias(self):
        """测试目录确保别名方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "alias_test"
            _result = FileUtils.ensure_directory(new_dir)

            assert result.exists()
            assert result.is_dir()

    def test_read_json_success(self):
        """测试成功读取JSON文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_data = {"name": "test", "value": 123, "items": ["a", "b", "c"]}
            json_file = Path(tmpdir) / "test.json"

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            _result = FileUtils.read_json(json_file)
            assert _result == test_data

    def test_read_json_file_not_found(self):
        """测试读取不存在的JSON文件"""
        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json("/nonexistent/file.json")

    def test_read_json_invalid_json(self):
        """测试读取无效的JSON文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "invalid.json"
            with open(json_file, "w") as f:
                f.write("{ invalid json }")

            with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
                FileUtils.read_json(json_file)

    def test_read_json_file_alias_success(self):
        """测试读取JSON文件别名方法 - 成功"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_data = {"test": "data"}
            json_file = Path(tmpdir) / "test.json"

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            _result = FileUtils.read_json_file(json_file)
            assert _result == test_data

    def test_read_json_file_alias_not_found(self):
        """测试读取JSON文件别名方法 - 文件不存在"""
        _result = FileUtils.read_json_file("/nonexistent/file.json")
        assert result is None

    def test_write_json_success(self):
        """测试成功写入JSON文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_data = {"name": "test", "items": [1, 2, 3]}
            json_file = Path(tmpdir) / "write_test.json"

            FileUtils.write_json(test_data, json_file)

            assert json_file.exists()
            with open(json_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_write_json_with_subdirectory(self):
        """测试写入JSON文件到子目录（自动创建）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_data = {"test": "subdir"}
            json_file = Path(tmpdir) / "subdir" / "nested" / "test.json"

            FileUtils.write_json(test_data, json_file)

            assert json_file.exists()
            assert json_file.parent.exists()

    def test_write_json_file_alias_success(self):
        """测试写入JSON文件别名方法 - 成功"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_data = {"test": "alias"}
            json_file = Path(tmpdir) / "alias_write.json"

            _result = FileUtils.write_json_file(test_data, json_file)

            assert result is True
            assert json_file.exists()

    def test_write_json_file_alias_failure(self):
        """测试写入JSON文件别名方法 - 失败"""
        # 尝试写入到只读目录（模拟失败）
        _result = FileUtils.write_json_file({"test": "data"}, "/root/test.json")
        assert result is False

    def test_get_file_hash_existing(self):
        """测试获取存在文件的哈希值"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "hash_test.txt"
            test_content = "Hello, World!"

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_content)

            hash_value = FileUtils.get_file_hash(test_file)
            assert len(hash_value) == 32  # MD5 hash length
            assert isinstance(hash_value, str)

    def test_get_file_hash_not_existing(self):
        """测试获取不存在文件的哈希值"""
        with pytest.raises(FileNotFoundError):
            FileUtils.get_file_hash("/nonexistent/file.txt")

    def test_get_file_size_existing(self):
        """测试获取存在文件的大小"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "size_test.txt"
            test_content = "This is a test file for size measurement."

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_content)

            size = FileUtils.get_file_size(test_file)
            assert size == len(test_content.encode("utf-8"))
            assert size > 0

    def test_get_file_size_not_existing(self):
        """测试获取不存在文件的大小"""
        size = FileUtils.get_file_size("/nonexistent/file.txt")
        assert size == 0

    def test_cleanup_old_files_empty_directory(self):
        """测试清理空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            removed_count = FileUtils.cleanup_old_files(tmpdir, days=30)
            assert removed_count == 0

    def test_cleanup_old_files_no_files_to_remove(self):
        """测试清理没有需要删除的文件的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一个新文件
            test_file = Path(tmpdir) / "new_file.txt"
            test_file.write_text("recent file")

            # 设置清理365天前的文件
            removed_count = FileUtils.cleanup_old_files(tmpdir, days=365)
            assert removed_count == 0
            assert test_file.exists()

    def test_cleanup_old_files_with_old_files(self):
        """测试清理包含旧文件的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一个文件
            test_file = Path(tmpdir) / "old_file.txt"
            test_file.write_text("old file")

            # 设置文件的修改时间为50天前
            old_time = time.time() - (50 * 24 * 60 * 60)
            os.utime(test_file, (old_time, old_time))

            # 清理30天前的文件
            removed_count = FileUtils.cleanup_old_files(tmpdir, days=30)
            assert removed_count == 1
            assert not test_file.exists()

    def test_cleanup_old_files_nonexistent_directory(self):
        """测试清理不存在的目录"""
        removed_count = FileUtils.cleanup_old_files("/nonexistent/directory", days=30)
        assert removed_count == 0

    def test_cleanup_old_files_with_subdirectories(self):
        """测试清理包含子目录的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建文件
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")

            # 设置为旧文件
            old_time = time.time() - (40 * 24 * 60 * 60)
            os.utime(test_file, (old_time, old_time))

            # 清理
            removed_count = FileUtils.cleanup_old_files(tmpdir, days=30)
            assert removed_count == 1

    def test_write_json_without_ensure_dir(self):
        """测试写入JSON文件（不确保目录存在）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_data = {"test": "no_ensure"}
            json_file = Path(tmpdir) / "no_ensure.json"

            # 确保目录已存在
            json_file.parent.mkdir(exist_ok=True)

            FileUtils.write_json(test_data, json_file, ensure_dir=False)

            assert json_file.exists()

    def test_pathlib_and_string_interchangeability(self):
        """测试Path对象和字符串路径的互换性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 使用字符串路径
            str_path = f"{tmpdir}/string_test.json"
            test_data = {"path_type": "string"}

            FileUtils.write_json(test_data, str_path)
            _result = FileUtils.read_json(str_path)
            assert _result == test_data

            # 使用Path对象
            path_obj = Path(tmpdir) / "path_test.json"
            FileUtils.write_json(test_data, path_obj)
            _result = FileUtils.read_json(path_obj)
            assert _result == test_data

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_data = {"chinese": "中文测试", "emoji": "🏈⚽", "special": "àáâãäåæçè"}
            json_file = Path(tmpdir) / "unicode_test.json"

            FileUtils.write_json(test_data, json_file)
            _result = FileUtils.read_json(json_file)
            assert _result == test_data
