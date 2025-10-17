"""
文件处理工具的全面单元测试
Comprehensive unit tests for file utilities
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.utils.file_utils import FileUtils


class TestEnsureDir:
    """测试目录创建功能"""

    def test_ensure_dir_new_directory(self):
        """测试创建新目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory" / "sub_dir"

            # 确保目录不存在
            assert not new_dir.exists()

            # 创建目录
            result = FileUtils.ensure_dir(new_dir)

            # 验证目录已创建
            assert result == new_dir
            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_ensure_dir_existing_directory(self):
        """测试已存在的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_dir = Path(temp_dir) / "existing"
            existing_dir.mkdir()

            # 确保目录已存在
            assert existing_dir.exists()

            # 再次调用应该不会报错
            result = FileUtils.ensure_dir(existing_dir)

            assert result == existing_dir
            assert existing_dir.exists()

    def test_ensure_dir_nested_path(self):
        """测试嵌套路径创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "a" / "b" / "c" / "d"

            # 创建多层嵌套目录
            result = FileUtils.ensure_dir(nested_path)

            assert result == nested_path
            assert nested_path.exists()
            assert nested_path.is_dir()

    def test_ensure_dir_with_string(self):
        """测试使用字符串路径"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = os.path.join(temp_dir, "string_dir")

            result = FileUtils.ensure_dir(dir_path)

            assert isinstance(result, Path)
            assert result.exists()
            assert result.is_dir()

    def test_ensure_directory_alias(self):
        """测试别名方法"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir) / "alias_test"

            result1 = FileUtils.ensure_dir(dir_path)
            result2 = FileUtils.ensure_directory(dir_path)

            assert result1 == result2
            assert dir_path.exists()


class TestReadJson:
    """测试JSON文件读取功能"""

    def test_read_json_valid_file(self):
        """测试读取有效的JSON文件"""
        test_data = {"name": "test", "value": 123, "list": [1, 2, 3]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = FileUtils.read_json(temp_path)
            assert result == test_data
        finally:
            os.unlink(temp_path)

    def test_read_json_empty_file(self):
        """测试读取空JSON文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
                FileUtils.read_json(temp_path)
        finally:
            os.unlink(temp_path)

    def test_read_json_invalid_json(self):
        """测试读取无效的JSON文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json content}')
            temp_path = f.name

        try:
            with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
                FileUtils.read_json(temp_path)
        finally:
            os.unlink(temp_path)

    def test_read_json_nonexistent_file(self):
        """测试读取不存在的文件"""
        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json("/nonexistent/path/file.json")

    def test_read_json_with_path_object(self):
        """测试使用Path对象读取JSON"""
        test_data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"
            file_path.write_text(json.dumps(test_data))

            result = FileUtils.read_json(file_path)
            assert result == test_data

    def test_read_json_unicode_content(self):
        """测试读取包含Unicode的JSON"""
        test_data = {"message": "测试中文", "emoji": "🚀", "accent": "Café"}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(test_data, f, ensure_ascii=False)
            temp_path = f.name

        try:
            result = FileUtils.read_json(temp_path)
            assert result == test_data
        finally:
            os.unlink(temp_path)

    def test_read_json_file_alias_valid(self):
        """测试别名方法读取有效文件"""
        test_data = {"alias": "test"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = FileUtils.read_json_file(temp_path)
            assert result == test_data
        finally:
            os.unlink(temp_path)

    def test_read_json_file_alias_invalid(self):
        """测试别名方法读取无效文件返回None"""
        result = FileUtils.read_json_file("/nonexistent/file.json")
        assert result is None


class TestWriteJson:
    """测试JSON文件写入功能"""

    def test_write_json_new_file(self):
        """测试写入新JSON文件"""
        test_data = {"name": "test", "value": 456}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "new_file.json"

            FileUtils.write_json(test_data, file_path)

            # 验证文件已创建并包含正确数据
            assert file_path.exists()
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_write_json_with_path_string(self):
        """测试使用字符串路径写入JSON"""
        test_data = {"string": "path"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "string_path.json")

            FileUtils.write_json(test_data, file_path)

            # 验证文件存在
            assert os.path.exists(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_write_json_create_directory(self):
        """测试自动创建目录"""
        test_data = {"auto": "create"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "subdir" / "nested" / "file.json"

            # 确保目录不存在
            assert not file_path.parent.exists()

            FileUtils.write_json(test_data, file_path)

            # 验证目录和文件都已创建
            assert file_path.exists()
            assert file_path.parent.exists()

    def test_write_json_no_ensure_dir(self):
        """测试不自动创建目录"""
        test_data = {"no": "ensure"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "nonexistent" / "file.json"

            # 不自动创建目录，应该报错
            with pytest.raises(FileNotFoundError):
                FileUtils.write_json(test_data, file_path, ensure_dir=False)

    def test_write_json_existing_file(self):
        """测试覆盖已存在的文件"""
        initial_data = {"initial": "data"}
        new_data = {"new": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "existing.json"

            # 先写入初始数据
            FileUtils.write_json(initial_data, file_path)

            # 再写入新数据
            FileUtils.write_json(new_data, file_path)

            # 验证文件被覆盖
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == new_data

    def test_write_json_unicode_data(self):
        """测试写入Unicode数据"""
        test_data = {"chinese": "测试数据", "emoji": "🎉", "special": "áéíóú"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "unicode.json"

            FileUtils.write_json(test_data, file_path)

            # 验证Unicode正确保存
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_write_json_file_alias_success(self):
        """测试别名方法成功写入"""
        test_data = {"alias": "success"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "alias_success.json"

            result = FileUtils.write_json_file(test_data, file_path)

            assert result is True
            assert file_path.exists()
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_write_json_file_alias_failure(self):
        """测试别名方法失败情况"""
        test_data = {"test": "data"}

        # 模拟写入失败
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = FileUtils.write_json_file(test_data, "/invalid/path/file.json")
            assert result is False


class TestGetFileHash:
    """测试文件哈希功能"""

    def test_get_file_hash_existing_file(self):
        """测试获取存在文件的哈希"""
        test_content = b"This is test content for hashing"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            # 计算预期的MD5
            import hashlib

            expected_hash = hashlib.md5(test_content, usedforsecurity=False).hexdigest()

            result = FileUtils.get_file_hash(temp_path)
            assert result == expected_hash
            assert len(result) == 32  # MD5哈希长度
        finally:
            os.unlink(temp_path)

    def test_get_file_hash_empty_file(self):
        """测试空文件的哈希"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # 不写入任何内容
            temp_path = f.name

        try:
            result = FileUtils.get_file_hash(temp_path)
            # 空文件的MD5应该是固定值
            assert result == "d41d8cd98f00b204e9800998ecf8427e"
        finally:
            os.unlink(temp_path)

    def test_get_file_hash_large_file(self):
        """测试大文件的哈希（分块读取）"""
        # 创建一个大文件（超过4096字节以测试分块）
        large_content = b"A" * 10000

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(large_content)
            temp_path = f.name

        try:
            # 计算预期的MD5
            import hashlib

            expected_hash = hashlib.md5(
                large_content, usedforsecurity=False
            ).hexdigest()

            result = FileUtils.get_file_hash(temp_path)
            assert result == expected_hash
        finally:
            os.unlink(temp_path)

    def test_get_file_hash_nonexistent_file(self):
        """测试获取不存在文件的哈希"""
        with pytest.raises(FileNotFoundError):
            FileUtils.get_file_hash("/nonexistent/file.txt")

    def test_get_file_hash_with_path_object(self):
        """测试使用Path对象获取哈希"""
        test_content = b"Path object test"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "hash_test.txt"
            file_path.write_bytes(test_content)

            import hashlib

            expected_hash = hashlib.md5(test_content, usedforsecurity=False).hexdigest()

            result = FileUtils.get_file_hash(file_path)
            assert result == expected_hash


class TestGetFileSize:
    """测试文件大小获取功能"""

    def test_get_file_size_existing_file(self):
        """测试获取存在文件的大小"""
        test_content = b"This file has some content"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            result = FileUtils.get_file_size(temp_path)
            assert result == len(test_content)
        finally:
            os.unlink(temp_path)

    def test_get_file_size_nonexistent_file(self):
        """测试获取不存在文件的大小"""
        result = FileUtils.get_file_size("/nonexistent/file.txt")
        assert result == 0

    def test_get_file_size_empty_file(self):
        """测试空文件的大小"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # 创建空文件
            temp_path = f.name

        try:
            result = FileUtils.get_file_size(temp_path)
            assert result == 0
        finally:
            os.unlink(temp_path)

    def test_get_file_size_with_path_object(self):
        """测试使用Path对象获取文件大小"""
        test_content = b"Size test with Path"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "size_test.txt"
            file_path.write_bytes(test_content)

            result = FileUtils.get_file_size(file_path)
            assert result == len(test_content)

    def test_get_file_size_permission_error(self):
        """测试权限错误的情况"""
        # 模拟OSError
        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", side_effect=OSError("Permission denied")),
        ):
            result = FileUtils.get_file_size("/restricted/file.txt")
            assert result == 0


class TestCleanupOldFiles:
    """测试清理旧文件功能"""

    def test_cleanup_old_files_empty_directory(self):
        """测试清理空目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = FileUtils.cleanup_old_files(temp_dir, days=30)
            assert result == 0

    def test_cleanup_old_files_no_old_files(self):
        """测试没有旧文件的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建新文件
            for i in range(3):
                (Path(temp_dir) / f"new_file_{i}.txt").write_text(f"content {i}")

            result = FileUtils.cleanup_old_files(temp_dir, days=30)
            assert result == 0

            # 文件应该仍然存在
            for i in range(3):
                assert (Path(temp_dir) / f"new_file_{i}.txt").exists()

    def test_cleanup_old_files_with_old_files(self):
        """测试清理旧文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建一些文件
            old_files = []
            for i in range(3):
                file_path = Path(temp_dir) / f"old_file_{i}.txt"
                file_path.write_text(f"old content {i}")
                old_files.append(file_path)

            # 修改文件时间戳，使其看起来很旧
            old_time = time.time() - (31 * 24 * 60 * 60)  # 31天前
            for file_path in old_files:
                os.utime(file_path, (old_time, old_time))

            # 创建新文件
            for i in range(2):
                (Path(temp_dir) / f"new_file_{i}.txt").write_text(f"new content {i}")

            # 清理30天前的文件
            result = FileUtils.cleanup_old_files(temp_dir, days=30)
            assert result == 3

            # 旧文件应该被删除
            for file_path in old_files:
                assert not file_path.exists()

            # 新文件应该仍然存在
            for i in range(2):
                assert (Path(temp_dir) / f"new_file_{i}.txt").exists()

    def test_cleanup_old_files_nonexistent_directory(self):
        """测试清理不存在的目录"""
        result = FileUtils.cleanup_old_files("/nonexistent/directory", days=30)
        assert result == 0

    def test_cleanup_old_files_with_subdirectories(self):
        """测试包含子目录的情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建文件和子目录
            (Path(temp_dir) / "file1.txt").write_text("content 1")
            (Path(temp_dir) / "file2.txt").write_text("content 2")

            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").write_text("content 3")

            # 修改文件时间戳
            old_time = time.time() - (31 * 24 * 60 * 60)
            for item in Path(temp_dir).iterdir():
                if item.is_file():
                    os.utime(item, (old_time, old_time))

            # 清理文件（不应该删除子目录）
            result = FileUtils.cleanup_old_files(temp_dir, days=30)

            # 应该只删除文件，不删除子目录
            assert result == 2  # 只删除顶级目录下的文件
            assert subdir.exists()

    def test_cleanup_old_files_custom_days(self):
        """测试自定义天数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建文件
            file_path = Path(temp_dir) / "test_file.txt"
            file_path.write_text("test content")

            # 设置文件时间为5天前
            old_time = time.time() - (5 * 24 * 60 * 60)
            os.utime(file_path, (old_time, old_time))

            # 清理3天前的文件（应该删除该文件）
            result = FileUtils.cleanup_old_files(temp_dir, days=3)
            assert result == 1
            assert not file_path.exists()

    def test_cleanup_old_files_error_handling(self):
        """测试错误处理"""
        # 模拟错误
        with patch.object(Path, "iterdir", side_effect=OSError("Permission denied")):
            result = FileUtils.cleanup_old_files("/some/path", days=30)
            assert result == 0  # 应该优雅地处理错误

    def test_cleanup_old_files_zero_days(self):
        """测试清理0天前的文件（所有文件）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建文件
            for i in range(3):
                (Path(temp_dir) / f"file_{i}.txt").write_text(f"content {i}")

            # 清理0天前的文件
            result = FileUtils.cleanup_old_files(temp_dir, days=0)
            assert result == 3

            # 所有文件都应该被删除
            assert len(list(Path(temp_dir).iterdir())) == 0


class TestEdgeCases:
    """测试边界情况"""

    def test_all_methods_with_none_input(self):
        """测试None输入"""
        # 这些方法应该能处理None输入或抛出适当的异常

        # ensure_dir 应该能处理None（通过类型转换）
        with pytest.raises(TypeError):
            FileUtils.ensure_dir(None)

        # read_json 应该抛出TypeError
        with pytest.raises(TypeError):
            FileUtils.read_json(None)

        # write_json 应该能处理None（通过类型转换）
        with pytest.raises(TypeError):
            FileUtils.write_json({}, None)

    def test_all_methods_with_empty_strings(self):
        """测试空字符串输入"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 空路径应该被处理
            result = FileUtils.ensure_dir("")
            assert isinstance(result, Path)

    def test_path_type_consistency(self):
        """测试路径类型一致性"""
        with tempfile.TemporaryDirectory() as temp_dir:
            str_path = os.path.join(temp_dir, "test")
            path_obj = Path(temp_dir) / "test"

            result1 = FileUtils.ensure_dir(str_path)
            result2 = FileUtils.ensure_dir(path_obj)

            # 两种方式都应该返回Path对象
            assert isinstance(result1, Path)
            assert isinstance(result2, Path)

    def test_json_round_trip(self):
        """测试JSON读写往返"""
        test_data = {
            "string": "测试",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, "三"],
            "dict": {"nested": "value"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "roundtrip.json"

            # 写入然后读取
            FileUtils.write_json(test_data, file_path)
            loaded_data = FileUtils.read_json(file_path)

            assert loaded_data == test_data

    def test_file_operations_consistency(self):
        """测试文件操作的一致性"""
        test_content = b"Consistency test content"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "consistency.txt"
            file_path.write_bytes(test_content)

            # 多次获取大小应该一致
            size1 = FileUtils.get_file_size(file_path)
            size2 = FileUtils.get_file_size(file_path)
            assert size1 == size2 == len(test_content)

            # 多次获取哈希应该一致
            hash1 = FileUtils.get_file_hash(file_path)
            hash2 = FileUtils.get_file_hash(file_path)
            assert hash1 == hash2


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__])
