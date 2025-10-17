"""
优化后的file_utils测试
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from src.utils.file_utils import FileUtils


class TestFileOperations:
    """文件操作测试"""

    def test_read_json_file(self):
        """测试读取JSON文件"""
        test_data = {"name": "test", "value": 123, "items": ["a", "b", "c"]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = FileUtils.read_json(temp_path)
            assert result == test_data
        finally:
            os.unlink(temp_path)

    def test_write_json_file(self):
        """测试写入JSON文件"""
        test_data = {"name": "write_test", "value": 456}

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            FileUtils.write_json(temp_path, test_data)
            # 验证文件是否正确写入
            with open(temp_path, "r") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data
        finally:
            os.unlink(temp_path)

    def test_get_file_hash(self):
        """测试计算文件哈希"""
        test_content = b"test content for hashing"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            file_hash = FileUtils.get_file_hash(temp_path)
            assert isinstance(file_hash, str)
            assert len(file_hash) == 32  # MD5 hash length
        finally:
            os.unlink(temp_path)

    def test_get_file_size(self):
        """测试获取文件大小"""
        test_content = b"test file size content"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            size = FileUtils.get_file_size(temp_path)
            assert size == len(test_content)
            assert size > 0
        finally:
            os.unlink(temp_path)

    def test_file_exists(self):
        """测试检查文件是否存在"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            assert FileUtils.file_exists(temp_path) is True
            assert FileUtils.file_exists("/nonexistent/path/file.txt") is False
        finally:
            os.unlink(temp_path)

    def test_create_directory(self):
        """测试创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "test_subdir" / "nested"
            FileUtils.create_directory(new_dir)
            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_copy_file(self):
        """测试复制文件"""
        test_content = b"content to copy"

        with tempfile.NamedTemporaryFile(delete=False) as src:
            src.write(test_content)
            src_path = src.name

        with tempfile.NamedTemporaryFile(delete=False) as dst:
            dst_path = dst.name

        try:
            FileUtils.copy_file(src_path, dst_path)
            with open(dst_path, "rb") as f:
                copied_content = f.read()
            assert copied_content == test_content
        finally:
            os.unlink(src_path)
            os.unlink(dst_path)

    def test_move_file(self):
        """测试移动文件"""
        test_content = b"content to move"

        with tempfile.NamedTemporaryFile(delete=False) as src:
            src.write(test_content)
            src_path = src.name

        with tempfile.NamedTemporaryFile(delete=False) as dst:
            dst_path = dst.name

        try:
            # 删除目标文件（因为tempfile会创建）
            os.unlink(dst_path)

            FileUtils.move_file(src_path, dst_path)
            assert not os.path.exists(src_path)
            assert os.path.exists(dst_path)
            with open(dst_path, "rb") as f:
                moved_content = f.read()
            assert moved_content == test_content
        finally:
            if os.path.exists(src_path):
                os.unlink(src_path)
            if os.path.exists(dst_path):
                os.unlink(dst_path)

    def test_delete_file(self):
        """测试删除文件"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        assert os.path.exists(temp_path)
        FileUtils.delete_file(temp_path)
        assert not os.path.exists(temp_path)

    def test_list_files(self):
        """测试列出目录中的文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_files = ["test1.txt", "test2.py", "test3.json"]
            for filename in test_files:
                Path(temp_dir) / filename.touch()

            # 列出所有文件
            all_files = FileUtils.list_files(temp_dir)
            assert len(all_files) >= len(test_files)

            # 列出特定扩展名的文件
            py_files = FileUtils.list_files(temp_dir, pattern="*.py")
            assert any("test2.py" in f for f in py_files)

    def test_clean_directory(self):
        """测试清理目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件和子目录
            test_file = Path(temp_dir) / "test.txt"
            test_file.touch()

            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            (subdir / "nested.txt").touch()

            # 清理目录
            FileUtils.clean_directory(temp_dir)
            assert test_file.exists() is False
            assert subdir.exists() is False

    def test_get_extension(self):
        """测试获取文件扩展名"""
        assert FileUtils.get_extension("test.txt") == "txt"
        assert FileUtils.get_extension("test.file.py") == "py"
        assert FileUtils.get_extension("/path/to/file.json") == "json"
        assert FileUtils.get_extension("no_extension") == ""

    def test_is_text_file(self):
        """测试判断是否为文本文件"""
        text_extensions = [".txt", ".py", ".json", ".md", ".csv"]
        for ext in text_extensions:
            assert FileUtils.is_text_file(f"test{ext}") is True

        assert FileUtils.is_text_file("test.jpg") is False
        assert FileUtils.is_text_file("test.pdf") is False

    def test_backup_file(self):
        """测试备份文件"""
        test_content = b"backup test content"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            # 备份文件
            backup_path = FileUtils.backup_file(temp_path)
            assert os.path.exists(backup_path)

            # 验证备份内容
            with open(backup_path, "rb") as f:
                backup_content = f.read()
            assert backup_content == test_content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists(backup_path):
                os.unlink(backup_path)


if __name__ == "__main__":
    pytest.main([__file__])
