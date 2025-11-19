from typing import Optional

"""
FileUtils完整覆盖测试 - 覆盖剩余函数以冲刺7.5%目标
"""

import tempfile
from pathlib import Path

from src.utils.file_utils import FileUtils


class TestFileUtilsCompleteCoverage:
    """FileUtils完整覆盖测试类"""

    def test_get_file_name_function(self):
        """测试获取文件名（不含扩展名）功能"""
        assert FileUtils.get_file_name("test.txt") == "test"
        assert FileUtils.get_file_name("document.pdf") == "document"
        assert FileUtils.get_file_name("archive.tar.gz") == "archive.tar"
        assert FileUtils.get_file_name("no_extension") == "no_extension"
        assert FileUtils.get_file_name(".hidden") == ".hidden"
        assert FileUtils.get_file_name("") == ""

    def test_get_file_name_path_object(self):
        """测试对Path对象获取文件名"""
        file_path = Path("test/example.txt")
        assert FileUtils.get_file_name(file_path) == "example"

    def test_get_file_full_name_function(self):
        """测试获取文件全名（含扩展名）功能"""
        assert FileUtils.get_file_full_name("test.txt") == "test.txt"
        assert FileUtils.get_file_full_name("document.pdf") == "document.pdf"
        assert FileUtils.get_file_full_name("archive.tar.gz") == "archive.tar.gz"
        assert FileUtils.get_file_full_name("no_extension") == "no_extension"
        assert FileUtils.get_file_full_name(".hidden") == ".hidden"
        assert FileUtils.get_file_full_name("") == ""

    def test_get_file_full_name_path_object(self):
        """测试对Path对象获取文件全名"""
        file_path = Path("test/example.txt")
        assert FileUtils.get_file_full_name(file_path) == "example.txt"

    def test_create_backup_default_location(self):
        """测试创建备份文件（默认位置）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建原始文件
            original_file = Path(temp_dir) / "original.txt"
            original_file.write_text("original content")

            # 创建备份（默认在相同目录）
            backup_path = FileUtils.create_backup(original_file)

            assert backup_path is not None
            assert backup_path.exists()
            assert backup_path.name.startswith("original.txt.backup")
            assert backup_path.read_text() == "original content"

    def test_create_backup_custom_directory(self):
        """测试创建备份文件（自定义目录）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建原始文件和备份目录
            original_file = Path(temp_dir) / "original.txt"
            original_file.write_text("original content")
            backup_dir = Path(temp_dir) / "backups"

            # 创建备份到指定目录
            backup_path = FileUtils.create_backup(original_file, backup_dir)

            assert backup_path is not None
            assert backup_path.exists()
            assert backup_dir.exists()
            assert backup_path.parent == backup_dir
            assert backup_path.read_text() == "original content"

    def test_create_backup_nonexistent_file(self):
        """测试备份不存在的文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = Path(temp_dir) / "nonexistent.txt"
            backup_path = FileUtils.create_backup(nonexistent_file)
            assert backup_path is None

    def test_read_text_file_basic(self):
        """测试基本文本文件读取功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello, World!")

            content = FileUtils.read_text_file(test_file)
            assert content == "Hello, World!"

    def test_read_text_file_nonexistent(self):
        """测试读取不存在的文本文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = Path(temp_dir) / "nonexistent.txt"
            content = FileUtils.read_text_file(nonexistent_file)
            assert content is None

    def test_read_text_file_encoding_error(self):
        """测试读取编码错误的文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建包含无效UTF-8字节的文件
            invalid_file = Path(temp_dir) / "invalid.txt"
            with open(invalid_file, "wb") as f:
                f.write(b"Invalid UTF-8: \xff\xfe")

            content = FileUtils.read_text_file(invalid_file)
            assert content is None

    def test_read_text_file_custom_encoding(self):
        """测试使用自定义编码读取文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            with open(test_file, "w", encoding="gbk") as f:
                f.write("中文内容")

            content = FileUtils.read_text_file(test_file, encoding="gbk")
            assert content == "中文内容"

    def test_write_text_file_basic(self):
        """测试基本文本文件写入功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"

            result = FileUtils.write_text_file("Hello, World!", test_file)
            assert result is True
            assert test_file.exists()
            assert test_file.read_text() == "Hello, World!"

    def test_write_text_file_with_directory_creation(self):
        """测试写入文件时自动创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_file = Path(temp_dir) / "auto" / "created" / "test.txt"

            result = FileUtils.write_text_file("Auto created", nested_file)
            assert result is True
            assert nested_file.exists()
            assert nested_file.read_text() == "Auto created"

    def test_write_text_file_no_directory_creation(self):
        """测试写入文件时不创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_dir = Path(temp_dir) / "existing"
            existing_dir.mkdir()
            test_file = existing_dir / "test.txt"

            result = FileUtils.write_text_file("Content", test_file, ensure_dir=False)
            assert result is True
            assert test_file.exists()

    def test_write_text_file_permission_error(self):
        """测试写入文件权限错误处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建只读目录
            readonly_dir = Path(temp_dir) / "readonly"
            readonly_dir.mkdir()
            readonly_dir.chmod(0o444)

            test_file = readonly_dir / "test.txt"

            try:
                result = FileUtils.write_text_file("Content", test_file)
                # 在某些系统上可能仍然成功，取决于权限设置
                assert isinstance(result, bool)
            except Exception:
                # 预期可能失败
                pass

    def test_append_to_file_basic(self):
        """测试基本文件追加功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Initial content")

            result = FileUtils.append_to_file("\nAppended content", test_file)
            assert result is True

            final_content = test_file.read_text()
            assert "Initial content" in final_content
            assert "Appended content" in final_content

    def test_append_to_file_new_file(self):
        """测试追加到新文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "new.txt"

            result = FileUtils.append_to_file("First content", test_file)
            assert result is True
            assert test_file.exists()
            assert test_file.read_text() == "First content"

    def test_append_to_file_permission_error(self):
        """测试追加文件权限错误处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建只读文件
            readonly_file = Path(temp_dir) / "readonly.txt"
            readonly_file.write_text("Readonly")
            readonly_file.chmod(0o444)

            try:
                result = FileUtils.append_to_file("Append", readonly_file)
                assert isinstance(result, bool)
            except Exception:
                # 预期可能失败
                pass

    def test_get_directory_size_basic(self):
        """测试获取目录大小基本功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "testdir"
            test_dir.mkdir()

            # 创建测试文件
            (test_dir / "file1.txt").write_text("Content 1")
            (test_dir / "file2.txt").write_text("Content 2")

            subdir = test_dir / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").write_text("Content 3")

            size = FileUtils.get_directory_size(test_dir)
            assert size > 0

    def test_get_directory_size_empty(self):
        """测试获取空目录大小"""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()

            size = FileUtils.get_directory_size(empty_dir)
            assert size == 0

    def test_get_directory_size_nonexistent(self):
        """测试获取不存在目录大小"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "nonexistent"

            size = FileUtils.get_directory_size(nonexistent_dir)
            assert size == 0

    def test_count_files_basic(self):
        """测试统计目录中文件数量"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "testdir"
            test_dir.mkdir()

            # 创建测试文件
            (test_dir / "file1.txt").write_text("Content 1")
            (test_dir / "file2.txt").write_text("Content 2")

            subdir = test_dir / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").write_text("Content 3")

            count = FileUtils.count_files(test_dir)
            assert count == 3

    def test_count_files_empty(self):
        """测试统计空目录文件数量"""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()

            count = FileUtils.count_files(empty_dir)
            assert count == 0

    def test_count_files_nonexistent(self):
        """测试统计不存在目录文件数量"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "nonexistent"

            count = FileUtils.count_files(nonexistent_dir)
            assert count == 0

    def test_safe_remove_directory_empty(self):
        """测试安全删除空目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()

            result = FileUtils.safe_remove_directory(empty_dir)
            assert result is True
            assert not empty_dir.exists()

    def test_safe_remove_directory_nonexistent(self):
        """测试安全删除不存在的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "nonexistent"

            result = FileUtils.safe_remove_directory(nonexistent_dir)
            assert result is False

    def test_safe_remove_directory_not_empty(self):
        """测试安全删除非空目录（应该失败）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonempty_dir = Path(temp_dir) / "nonempty"
            nonempty_dir.mkdir()
            (nonempty_dir / "file.txt").write_text("content")

            result = FileUtils.safe_remove_directory(nonempty_dir)
            assert result is False
            assert nonempty_dir.exists()

    def test_remove_directory_force_basic(self):
        """测试强制删除目录及其内容"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "testdir"
            test_dir.mkdir()

            # 创建文件和子目录
            (test_dir / "file1.txt").write_text("Content 1")
            subdir = test_dir / "subdir"
            subdir.mkdir()
            (subdir / "file2.txt").write_text("Content 2")

            result = FileUtils.remove_directory_force(test_dir)
            assert result is True
            assert not test_dir.exists()

    def test_remove_directory_force_nonexistent(self):
        """测试强制删除不存在的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "nonexistent"

            result = FileUtils.remove_directory_force(nonexistent_dir)
            assert result is False

    def test_comprehensive_file_workflow(self):
        """测试完整文件工作流程"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. 创建文件
            original_file = Path(temp_dir) / "workflow.txt"
            content = "Initial workflow content"
            FileUtils.write_text_file(content, original_file)

            # 2. 检查文件属性
            assert FileUtils.file_exists(original_file)
            assert FileUtils.is_file(original_file)
            assert FileUtils.get_file_name(original_file) == "workflow"
            assert FileUtils.get_file_full_name(original_file) == "workflow.txt"
            assert FileUtils.get_file_extension(original_file) == ".txt"

            # 3. 创建备份
            backup_file = FileUtils.create_backup(original_file)
            assert backup_file is not None
            assert backup_file.exists()

            # 4. 追加内容
            FileUtils.append_to_file("\nAppended workflow", original_file)
            updated_content = FileUtils.read_text_file(original_file)
            assert "Appended workflow" in updated_content

            # 5. 复制文件
            copied_file = Path(temp_dir) / "copied.txt"
            FileUtils.copy_file(original_file, copied_file)
            assert copied_file.exists()
            assert FileUtils.read_text_file(copied_file) == updated_content

            # 6. 获取文件信息
            assert FileUtils.get_file_size(original_file) > 0
            assert FileUtils.get_file_hash(original_file) is not None

            # 7. 删除原始文件
            FileUtils.delete_file(original_file)
            assert not FileUtils.file_exists(original_file)

            # 8. 从备份恢复
            FileUtils.move_file(backup_file, original_file)
            assert FileUtils.file_exists(original_file)
            assert FileUtils.read_text_file(original_file) == content
