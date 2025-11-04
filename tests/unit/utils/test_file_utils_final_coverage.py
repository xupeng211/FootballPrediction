"""
FileUtils补充测试 - 冲刺7.5%覆盖率目标
专门针对未覆盖的函数进行精准测试
"""

import pytest
import tempfile
import time
import os
from pathlib import Path
from src.utils.file_utils import FileUtils


class TestFileUtilsFinalCoverage:
    """FileUtils补充测试类 - 针对性提升覆盖率"""

    def test_cleanup_old_files_basic(self):
        """测试基本清理旧文件功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建一个旧文件
            old_file = Path(temp_dir) / "old_file.txt"
            old_file.write_text("old content")

            # 修改文件时间为30天前
            old_time = time.time() - (31 * 24 * 60 * 60)
            os.utime(old_file, (old_time, old_time))

            # 清理30天前的文件
            removed_count = FileUtils.cleanup_old_files(temp_dir, days=30)
            assert removed_count == 1
            assert not old_file.exists()

    def test_cleanup_old_files_no_directory(self):
        """测试清理不存在的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "nonexistent"
            removed_count = FileUtils.cleanup_old_files(nonexistent_dir)
            assert removed_count == 0

    def test_cleanup_old_files_no_old_files(self):
        """测试清理没有旧文件的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建新文件
            new_file = Path(temp_dir) / "new_file.txt"
            new_file.write_text("new content")

            # 清理30天前的文件（应该没有文件被删除）
            removed_count = FileUtils.cleanup_old_files(temp_dir, days=30)
            assert removed_count == 0
            assert new_file.exists()

    def test_copy_file_basic(self):
        """测试基本文件复制功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            src_file = Path(temp_dir) / "source.txt"
            dst_file = Path(temp_dir) / "destination.txt"

            # 创建源文件
            src_file.write_text("test content")

            # 复制文件
            result = FileUtils.copy_file(src_file, dst_file)
            assert result is True
            assert dst_file.exists()
            assert dst_file.read_text() == "test content"

    def test_copy_file_nonexistent(self):
        """测试复制不存在的文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            src_file = Path(temp_dir) / "nonexistent.txt"
            dst_file = Path(temp_dir) / "destination.txt"

            result = FileUtils.copy_file(src_file, dst_file)
            assert result is False
            assert not dst_file.exists()

    def test_move_file_basic(self):
        """测试基本文件移动功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            src_file = Path(temp_dir) / "source.txt"
            dst_dir = Path(temp_dir) / "subdir"
            dst_file = dst_dir / "moved.txt"

            # 创建源文件
            src_file.write_text("test content")

            # 移动文件
            result = FileUtils.move_file(src_file, dst_file)
            assert result is True
            assert not src_file.exists()
            assert dst_file.exists()
            assert dst_file.read_text() == "test content"

    def test_move_file_nonexistent(self):
        """测试移动不存在的文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            src_file = Path(temp_dir) / "nonexistent.txt"
            dst_file = Path(temp_dir) / "destination.txt"

            result = FileUtils.move_file(src_file, dst_file)
            assert result is False

    def test_delete_file_basic(self):
        """测试基本文件删除功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "to_delete.txt"
            test_file.write_text("content to delete")

            result = FileUtils.delete_file(test_file)
            assert result is True
            assert not test_file.exists()

    def test_delete_file_nonexistent(self):
        """测试删除不存在的文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = Path(temp_dir) / "nonexistent.txt"

            result = FileUtils.delete_file(nonexistent_file)
            assert result is False

    def test_file_exists_function(self):
        """测试文件存在检查功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_file = Path(temp_dir) / "exists.txt"
            existing_file.write_text("content")
            nonexistent_file = Path(temp_dir) / "nonexistent.txt"

            assert FileUtils.file_exists(existing_file) is True
            assert FileUtils.file_exists(nonexistent_file) is False

    def test_is_file_function(self):
        """测试文件类型检查功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")
            test_dir = Path(temp_dir) / "subdir"
            test_dir.mkdir()

            assert FileUtils.is_file(test_file) is True
            assert FileUtils.is_file(test_dir) is False
            assert FileUtils.is_file(Path(temp_dir) / "nonexistent") is False

    def test_is_directory_function(self):
        """测试目录类型检查功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")
            test_dir = Path(temp_dir) / "subdir"
            test_dir.mkdir()

            assert FileUtils.is_directory(test_dir) is True
            assert FileUtils.is_directory(test_file) is False
            assert FileUtils.is_directory(Path(temp_dir) / "nonexistent") is False

    def test_list_files_basic(self):
        """测试基本文件列表功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            (Path(temp_dir) / "file1.txt").write_text("content1")
            (Path(temp_dir) / "file2.py").write_text("content2")
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()

            # 列出所有文件
            all_files = FileUtils.list_files(temp_dir)
            file_names = [f.name for f in all_files]
            assert "file1.txt" in file_names
            assert "file2.py" in file_names

            # 按模式列出文件
            txt_files = FileUtils.list_files(temp_dir, "*.txt")
            txt_names = [f.name for f in txt_files]
            assert "file1.txt" in txt_names
            assert "file2.py" not in txt_names

    def test_list_files_nonexistent_directory(self):
        """测试列出不存在目录的文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "nonexistent"
            files = FileUtils.list_files(nonexistent_dir)
            assert files == []

    def test_list_files_recursive(self):
        """测试递归文件列表功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建嵌套文件结构
            (Path(temp_dir) / "root.txt").write_text("root content")
            subdir1 = Path(temp_dir) / "subdir1"
            subdir1.mkdir()
            (subdir1 / "nested1.txt").write_text("nested content 1")
            subdir2 = Path(temp_dir) / "subdir2"
            subdir2.mkdir()
            (subdir2 / "nested2.py").write_text("nested content 2")

            # 递归列出所有文件
            all_files = FileUtils.list_files_recursive(temp_dir)
            file_names = [f.name for f in all_files]
            assert "root.txt" in file_names
            assert "nested1.txt" in file_names
            assert "nested2.py" in file_names

            # 递归列出txt文件
            txt_files = FileUtils.list_files_recursive(temp_dir, "*.txt")
            txt_names = [f.name for f in txt_files]
            assert "root.txt" in txt_names
            assert "nested1.txt" in txt_names
            assert "nested2.py" not in txt_names

    def test_list_files_recursive_nonexistent_directory(self):
        """测试递归列出不存在目录的文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "nonexistent"
            files = FileUtils.list_files_recursive(nonexistent_dir)
            assert files == []

    def test_get_file_extension_function(self):
        """测试获取文件扩展名功能"""
        # 测试各种文件扩展名
        assert FileUtils.get_file_extension("test.txt") == ".txt"
        assert FileUtils.get_file_extension("document.pdf") == ".pdf"
        assert FileUtils.get_file_extension("archive.tar.gz") == ".gz"
        assert FileUtils.get_file_extension("no_extension") == ""
        assert FileUtils.get_file_extension(".hidden") == ""
        assert FileUtils.get_file_extension("") == ""

    def test_get_file_extension_path_object(self):
        """测试对Path对象获取文件扩展名"""
        file_path = Path("test/example.txt")
        assert FileUtils.get_file_extension(file_path) == ".txt"

    def test_edge_cases_file_operations(self):
        """测试文件操作边界情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试空文件操作
            empty_file = Path(temp_dir) / "empty.txt"
            empty_file.write_text("")

            assert FileUtils.file_exists(empty_file) is True
            assert FileUtils.is_file(empty_file) is True
            assert FileUtils.get_file_size(empty_file) == 0
            assert FileUtils.get_file_extension(empty_file) == ".txt"

            # 测试复制空文件
            empty_copy = Path(temp_dir) / "empty_copy.txt"
            result = FileUtils.copy_file(empty_file, empty_copy)
            assert result is True
            assert empty_copy.exists()
            assert empty_copy.read_text() == ""

    def test_error_handling_file_operations(self):
        """测试文件操作错误处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")

            # 测试复制到不存在的目录（应该失败）
            invalid_dst = Path("/invalid/path/destination.txt")
            result = FileUtils.copy_file(test_file, invalid_dst)
            assert result is False

            # 测试移动到不存在的目录（应该失败）
            result = FileUtils.move_file(test_file, invalid_dst)
            assert result is False
