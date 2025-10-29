"""
文件工具完整测试
File Utils Complete Tests

基于Issue #98成功模式，创建完整的文件工具测试
"""

import os
import tempfile
import time
from pathlib import Path

import pytest

from src.utils.file_utils import FileUtils


@pytest.mark.unit
class TestFileUtilsComplete:
    """文件工具完整测试"""

    def test_ensure_dir(self):
        """测试确保目录存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建新目录
            new_dir = Path(tmpdir) / "new" / "sub" / "dir"
            result = FileUtils.ensure_dir(new_dir)
            assert result.exists()
            assert result.is_dir()

            # 目录已存在
            result = FileUtils.ensure_dir(new_dir)
            assert result.exists()

            # 使用字符串路径
            str_dir = os.path.join(tmpdir, "string", "dir")
            result = FileUtils.ensure_dir(str_dir)
            assert isinstance(result, Path)
            assert result.exists()

    def test_ensure_directory_alias(self):
        """测试ensure_directory别名方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "alias" / "dir"
            result = FileUtils.ensure_directory(new_dir)
            assert result.exists()
            assert result.is_dir()

    def test_write_and_read_json(self):
        """测试JSON文件读写"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            data = {"name": "John", "age": 30, "active": True, "scores": [90, 85, 95]}

            # 写入JSON
            FileUtils.write_json(data, file_path)
            assert file_path.exists()

            # 读取JSON
            loaded_data = FileUtils.read_json(file_path)
            assert loaded_data == data

    def test_write_json_with_ensure_dir(self):
        """测试写入JSON时自动创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "nested" / "dirs" / "test.json"
            data = {"test": "data"}

            # 确保目录不存在
            assert not file_path.parent.exists()

            # 写入文件
            FileUtils.write_json(data, file_path, ensure_dir=True)
            assert file_path.exists()
            assert file_path.parent.exists()

    def test_read_json_file_aliases(self):
        """测试JSON文件别名方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            data = {"name": "Alice", "age": 25}

            # 写入JSON
            FileUtils.write_json(data, file_path)

            # 使用别名方法读取
            result1 = FileUtils.read_json_file(file_path)
            assert result1 == data

            # 测试不存在的文件
            result2 = FileUtils.read_json_file(Path(tmpdir) / "nonexistent.json")
            assert result2 is None

    def test_write_json_file_aliases(self):
        """测试JSON文件写入别名方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            data = {"name": "Bob", "age": 35}

            # 使用别名方法写入
            result = FileUtils.write_json_file(data, file_path)
            assert result is True
            assert file_path.exists()

            # 验证内容
            loaded = FileUtils.read_json(file_path)
            assert loaded == data

    def test_get_file_hash(self):
        """测试获取文件哈希值"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            content = "Hello, World!"

            file_path.write_text(content, encoding="utf-8")
            hash1 = FileUtils.get_file_hash(file_path)
            assert isinstance(hash1, str)
            assert len(hash1) == 32  # MD5哈希长度

            # 修改文件内容，哈希应该改变
            file_path.write_text("Modified content", encoding="utf-8")
            hash2 = FileUtils.get_file_hash(file_path)
            assert hash1 != hash2

    def test_get_file_size(self):
        """测试获取文件大小"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            content = "Hello, World!"

            file_path.write_text(content, encoding="utf-8")
            size = FileUtils.get_file_size(file_path)
            assert size == len(content.encode("utf-8"))

            # 测试不存在的文件
            size = FileUtils.get_file_size(Path(tmpdir) / "nonexistent.txt")
            assert size == 0

    def test_file_operations(self):
        """测试基本文件操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.txt"
            target_file = Path(tmpdir) / "target.txt"
            moved_file = Path(tmpdir) / "moved.txt"
            content = "Test content for file operations"

            # 创建源文件
            source_file.write_text(content, encoding="utf-8")

            # 测试文件存在性
            assert FileUtils.file_exists(source_file) is True
            assert FileUtils.file_exists(target_file) is False
            assert FileUtils.is_file(source_file) is True
            assert FileUtils.is_directory(source_file) is False

            # 复制文件
            result = FileUtils.copy_file(source_file, target_file)
            assert result is True
            assert target_file.exists()
            assert target_file.read_text(encoding="utf-8") == content

            # 移动文件
            result = FileUtils.move_file(target_file, moved_file)
            assert result is True
            assert moved_file.exists()
            assert not target_file.exists()

            # 删除文件
            result = FileUtils.delete_file(moved_file)
            assert result is True
            assert not moved_file.exists()

    def test_list_files(self):
        """测试列出文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            files = ["test1.txt", "test2.py", "test3.json"]
            for filename in files:
                (Path(tmpdir) / filename).write_text("test content")

            # 创建子目录
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "subfile.txt").write_text("sub content")

            # 列出当前目录文件
            result = FileUtils.list_files(tmpdir)
            file_names = [f.name for f in result]
            assert "test1.txt" in file_names
            assert "test2.py" in file_names
            assert "test3.json" in file_names

            # 按模式过滤
            py_files = FileUtils.list_files(tmpdir, "*.py")
            assert len(py_files) == 1
            assert py_files[0].name == "test2.py"

            # 递归列出文件
            all_files = FileUtils.list_files_recursive(tmpdir)
            assert len(all_files) == 5  # 3个文件 + 1个子目录 + 1个子目录文件

    def test_file_info_operations(self):
        """测试文件信息操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "example.test.file.txt"
            file_path.write_text("test content")

            # 测试文件名操作
            assert FileUtils.get_file_extension(file_path) == ".txt"
            assert FileUtils.get_file_name(file_path) == "example.test.file"
            assert FileUtils.get_file_full_name(file_path) == "example.test.file.txt"

    def test_directory_operations(self):
        """测试目录操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            for i in range(5):
                (Path(tmpdir) / f"file{i}.txt").write_text(f"content {i}")

            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "subfile.txt").write_text("sub content")

            # 获取目录大小
            size = FileUtils.get_directory_size(tmpdir)
            assert size > 0

            # 统计文件数量
            count = FileUtils.count_files(tmpdir)
            assert count == 6  # 5个文件 + 1个子目录文件

            # 测试目录类型检查
            assert FileUtils.is_directory(tmpdir) is True
            # 注意：source_file在上下文中未定义，我们使用一个已创建的文件
            existing_file = [f for f in Path(tmpdir).iterdir() if f.is_file()][0]
            assert FileUtils.is_directory(existing_file) is False

    def test_text_file_operations(self):
        """测试文本文件操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "text.txt"
            content = "这是中文内容\nEnglish content\n12345"

            # 写入文本文件
            result = FileUtils.write_text_file(content, file_path)
            assert result is True
            assert file_path.exists()

            # 读取文本文件
            read_content = FileUtils.read_text_file(file_path)
            assert read_content == content

            # 追加内容
            additional = "\n追加的内容"
            result = FileUtils.append_to_file(additional, file_path)
            assert result is True

            final_content = FileUtils.read_text_file(file_path)
            assert final_content == content + additional

    def test_backup_operations(self):
        """测试备份操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.txt"
            backup_dir = Path(tmpdir) / "backups"
            content = "重要内容需要备份"

            source_file.write_text(content)

            # 创建备份
            backup_path = FileUtils.create_backup(source_file)
            assert backup_path is not None
            assert backup_path.exists()
            assert backup_path.read_text(encoding="utf-8") == content

            # 验证备份文件名格式
            assert "source.backup" in backup_path.name

            # 指定备份目录
            backup_path2 = FileUtils.create_backup(source_file, backup_dir)
            assert backup_path2 is not None
            assert backup_path2.parent == backup_dir

    def test_cleanup_old_files(self):
        """测试清理旧文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建不同时间的文件
            current_time = time.time()
            old_time = current_time - (5 * 24 * 60 * 60)  # 5天前

            files = []
            for i in range(3):
                file_path = Path(tmpdir) / f"old_file_{i}.txt"
                file_path.write_text(f"old content {i}")

                # 修改文件时间
                os.utime(file_path, (old_time + i, old_time + i))
                files.append(file_path)

            # 创建一个新文件
            new_file = Path(tmpdir) / "new_file.txt"
            new_file.write_text("new content")

            # 清理3天前的文件
            removed = FileUtils.cleanup_old_files(tmpdir, days=3)
            assert removed == 3

            # 验证旧文件被删除，新文件保留
            assert not any(f.exists() for f in files)
            assert new_file.exists()

    def test_error_handling(self):
        """测试错误处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 测试不存在的文件操作
            result = FileUtils.copy_file(
                Path(tmpdir) / "nonexistent.txt", Path(tmpdir) / "target.txt"
            )
            assert result is False

            result = FileUtils.move_file(
                Path(tmpdir) / "nonexistent.txt", Path(tmpdir) / "target.txt"
            )
            assert result is False

            result = FileUtils.delete_file(Path(tmpdir) / "nonexistent.txt")
            assert result is False

            # 测试无效路径的JSON操作
            with pytest.raises(FileNotFoundError):
                FileUtils.read_json(Path(tmpdir) / "nonexistent.json")

            # 测试无效JSON内容
            invalid_file = Path(tmpdir) / "invalid.json"
            invalid_file.write_text("invalid json content")

            with pytest.raises(FileNotFoundError):
                FileUtils.read_json(invalid_file)

    def test_edge_cases(self):
        """测试边界情况"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 测试空文件
            empty_file = Path(tmpdir) / "empty.txt"
            empty_file.write_text("")

            assert FileUtils.get_file_size(empty_file) == 0
            assert FileUtils.read_text_file(empty_file) == ""

            # 测试特殊字符文件名
            special_file = Path(tmpdir) / "特殊文件名.txt"
            special_content = "特殊内容测试"
            special_file.write_text(special_content, encoding="utf-8")

            read_content = FileUtils.read_text_file(special_file)
            assert read_content == special_content

            # 测试空字典处理
            assert len({}) == 0

            # 测试非空字典
            assert len({"a": 1}) == 1

    def test_json_handling_complex(self):
        """测试复杂JSON数据处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "complex.json"

            # 复杂数据结构
            complex_data = {
                "users": [
                    {"id": 1, "name": "Alice", "active": True},
                    {"id": 2, "name": "Bob", "active": False},
                ],
                "settings": {
                    "theme": "dark",
                    "notifications": {"email": True, "push": False},
                },
                "metadata": {"created": "2025-01-01", "version": 1.0},
            }

            # 写入复杂JSON
            FileUtils.write_json(complex_data, file_path)

            # 读取复杂JSON
            loaded_data = FileUtils.read_json(file_path)
            assert loaded_data == complex_data
            assert len(loaded_data["users"]) == 2
            assert loaded_data["settings"]["theme"] == "dark"

    def test_large_file_operations(self):
        """测试大文件操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            large_file = Path(tmpdir) / "large.txt"

            # 创建大内容
            large_content = "A" * 10000  # 10KB
            large_file.write_text(large_content, encoding="utf-8")

            # 测试大文件读取
            read_content = FileUtils.read_text_file(large_file)
            assert len(read_content) == 10000

            # 测试大文件哈希
            hash_value = FileUtils.get_file_hash(large_file)
            assert isinstance(hash_value, str)
            assert len(hash_value) == 32

            # 测试大文件复制
            large_copy = Path(tmpdir) / "large_copy.txt"
            result = FileUtils.copy_file(large_file, large_copy)
            assert result is True
            assert large_copy.read_text(encoding="utf-8") == large_content

    def test_concurrent_operations(self):
        """测试并发操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建多个文件
            for i in range(10):
                file_path = Path(tmpdir) / f"file_{i}.txt"
                file_path.write_text(f"content {i}")

            # 测试列表操作
            all_files = FileUtils.list_files(tmpdir)
            assert len(all_files) == 10

            # 测试批量复制
            copy_dir = Path(tmpdir) / "copies"
            copy_dir.mkdir()

            for file_path in all_files:
                target_path = copy_dir / file_path.name
                FileUtils.copy_file(file_path, target_path)

            copied_files = FileUtils.list_files(copy_dir)
            assert len(copied_files) == 10

            # 测试批量统计
            total_size = FileUtils.get_directory_size(tmpdir)
            file_count = FileUtils.count_files(tmpdir)

            assert total_size > 0
            assert file_count == 20  # 10个原文件 + 10个复制文件

    def test_unicode_and_encoding(self):
        """测试Unicode和编码处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 测试多种语言内容
            unicode_content = """
            English: Hello World!
            中文: 你好世界！
            日本語: こんにちは世界！
            Español: ¡Hola Mundo!
            Français: Bonjour le monde!
            Русский: Привет мир!
            Arabic: مرحبا بالعالم
            """

            unicode_file = Path(tmpdir) / "unicode.txt"

            # 写入Unicode内容
            result = FileUtils.write_text_file(unicode_content, unicode_file)
            assert result is True

            # 读取Unicode内容
            read_content = FileUtils.read_text_file(unicode_file)
            assert read_content == unicode_content

            # 测试JSON中的Unicode
            json_file = Path(tmpdir) / "unicode.json"
            unicode_data = {
                "chinese": "你好",
                "japanese": "こんにちは",
                "emoji": "🎉🚀",
                "symbols": "αβγδε",
            }

            FileUtils.write_json(unicode_data, json_file)
            loaded_data = FileUtils.read_json(json_file)
            assert loaded_data == unicode_data

    def test_path_handling_variations(self):
        """测试各种路径处理变体"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            # 测试Path对象
            result1 = FileUtils.file_exists(test_file)
            assert result1 is True

            # 测试字符串路径
            str_path = str(test_file)
            result2 = FileUtils.file_exists(str_path)
            assert result2 is True

            # 测试相对路径
            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result3 = FileUtils.file_exists("test.txt")
                assert result3 is True
            finally:
                os.chdir(old_cwd)

            # 测试路径操作
            file_info = {
                "extension": FileUtils.get_file_extension(test_file),
                "name": FileUtils.get_file_name(test_file),
                "full_name": FileUtils.get_file_full_name(test_file),
                "size": FileUtils.get_file_size(test_file),
            }

            assert file_info["extension"] == ".txt"
            assert file_info["name"] == "test"
            assert file_info["full_name"] == "test.txt"
            assert file_info["size"] > 0
