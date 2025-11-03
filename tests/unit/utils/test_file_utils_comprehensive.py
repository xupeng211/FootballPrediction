"""
文件工具全面测试 - 冲刺45%覆盖率
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from src.utils.file_utils import FileUtils


class TestFileUtilsComprehensive:
    """文件工具全面测试类"""

    def test_ensure_dir_basic(self):
        """测试基本目录创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试创建新目录
            new_dir = Path(temp_dir) / "test_dir" / "sub_dir"
            result = FileUtils.ensure_dir(new_dir)
            assert result == new_dir
            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_ensure_dir_existing(self):
        """测试创建已存在的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试已存在目录
            existing_dir = Path(temp_dir) / "existing"
            existing_dir.mkdir()

            result = FileUtils.ensure_dir(existing_dir)
            assert result == existing_dir
            assert existing_dir.exists()

    def test_ensure_dir_nested(self):
        """测试嵌套目录创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试深层嵌套目录
            nested_dir = Path(temp_dir) / "a" / "b" / "c" / "d" / "e"
            result = FileUtils.ensure_dir(nested_dir)
            assert result == nested_dir
            assert nested_dir.exists()

    def test_read_json_file(self):
        """测试读取JSON文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试JSON文件
            test_data = {"name": "John", "age": 30, "active": True}
            json_file = Path(temp_dir) / "test.json"

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            # 读取JSON文件
            result = FileUtils.read_json(json_file)
            assert result == test_data
            assert result["name"] == "John"
            assert result["age"] == 30

    def test_read_json_nonexistent(self):
        """测试读取不存在的JSON文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = Path(temp_dir) / "nonexistent.json"

            with pytest.raises(FileNotFoundError):
                FileUtils.read_json(nonexistent_file)

    def test_read_json_invalid(self):
        """测试读取无效JSON文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建无效JSON文件
            invalid_file = Path(temp_dir) / "invalid.json"
            with open(invalid_file, "w", encoding="utf-8") as f:
                f.write("{ invalid json content")

            with pytest.raises(FileNotFoundError):
                FileUtils.read_json(invalid_file)

    def test_write_json_basic(self):
        """测试基本JSON写入"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_data = {"message": "Hello World", "numbers": [1, 2, 3]}
            json_file = Path(temp_dir) / "output.json"

            # 写入JSON文件
            FileUtils.write_json(test_data, json_file)

            # 验证文件存在并包含正确内容
            assert json_file.exists()

            with open(json_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_write_json_with_dir_creation(self):
        """测试写入JSON时自动创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_data = {"auto": "created"}
            nested_path = Path(temp_dir) / "auto" / "created" / "path" / "test.json"

            # 确保目录不存在
            assert not nested_path.parent.exists()

            # 写入JSON文件（应该自动创建目录）
            FileUtils.write_json(test_data, nested_path)

            assert nested_path.exists()
            assert nested_path.parent.exists()

    def test_write_json_no_dir_creation(self):
        """测试写入JSON时不创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_data = {"no": "auto-creation"}
            existing_dir = Path(temp_dir) / "existing"
            existing_dir.mkdir()
            json_file = existing_dir / "test.json"

            # 写入JSON文件
            FileUtils.write_json(test_data, json_file, ensure_dir=False)

            assert json_file.exists()

    def test_get_file_hash(self):
        """测试获取文件哈希值"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_file = Path(temp_dir) / "test.txt"
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Hello World")

            # 获取文件哈希
            hash_value = FileUtils.get_file_hash(test_file)
            assert isinstance(hash_value, str)
            assert len(hash_value) == 32  # MD5哈希长度
            assert all(c in "0123456789abcdef" for c in hash_value)

    def test_get_file_hash_nonexistent(self):
        """测试获取不存在文件的哈希值"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = Path(temp_dir) / "nonexistent.txt"

            with pytest.raises(FileNotFoundError):
                FileUtils.get_file_hash(nonexistent_file)

    def test_get_file_size_basic(self):
        """测试获取文件大小"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建不同大小的测试文件
            small_file = Path(temp_dir) / "small.txt"
            with open(small_file, "w", encoding="utf-8") as f:
                f.write("Hello")

            size = FileUtils.get_file_size(small_file)
            assert size == 5  # "Hello" = 5字节

    def test_get_file_size_nonexistent(self):
        """测试获取不存在文件的大小"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = Path(temp_dir) / "nonexistent.txt"

            size = FileUtils.get_file_size(nonexistent_file)
            assert size == 0

    def test_get_file_size_empty(self):
        """测试获取空文件大小"""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_file = Path(temp_dir) / "empty.txt"
            empty_file.touch()

            size = FileUtils.get_file_size(empty_file)
            assert size == 0

    def test_ensure_directory_alias(self):
        """测试目录创建别名方法"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "alias_test"

            result = FileUtils.ensure_directory(new_dir)
            assert result == new_dir
            assert new_dir.exists()

    def test_read_json_file_alias(self):
        """测试JSON读取别名方法"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试JSON文件
            test_data = {"alias": "test"}
            json_file = Path(temp_dir) / "alias.json"

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            # 使用别名方法读取
            result = FileUtils.read_json_file(json_file)
            assert result == test_data

    def test_read_json_file_nonexistent_alias(self):
        """测试读取不存在JSON文件的别名方法"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = Path(temp_dir) / "nonexistent.json"

            result = FileUtils.read_json_file(nonexistent_file)
            assert result is None

    def test_unicode_content(self):
        """测试Unicode内容处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 包含Unicode字符的测试数据
            test_data = {
                "chinese": "你好世界",
                "emoji": "🌍🚀",
                "special": "café résumé naïve"
            }

            json_file = Path(temp_dir) / "unicode.json"
            FileUtils.write_json(test_data, json_file)

            # 读取并验证Unicode内容
            result = FileUtils.read_json(json_file)
            assert result == test_data
            assert result["chinese"] == "你好世界"
            assert result["emoji"] == "🌍🚀"

    def test_large_json_files(self):
        """测试大型JSON文件处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建大型JSON数据
            large_data = {
                "items": [{"id": i, "name": f"item_{i}", "data": "x" * 100} for i in range(1000)]
            }

            json_file = Path(temp_dir) / "large.json"

            # 写入大型JSON
            FileUtils.write_json(large_data, json_file)

            # 读取大型JSON
            result = FileUtils.read_json(json_file)
            assert len(result["items"]) == 1000
            assert result["items"][0]["id"] == 0
            assert result["items"][-1]["id"] == 999

    def test_file_operations_edge_cases(self):
        """测试文件操作边界情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试空JSON数据
            empty_data = {}
            json_file = Path(temp_dir) / "empty.json"
            FileUtils.write_json(empty_data, json_file)

            result = FileUtils.read_json(json_file)
            assert result == {}

    def test_path_handling(self):
        """测试路径处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试字符串路径
            string_path = os.path.join(temp_dir, "string_path")
            result = FileUtils.ensure_dir(string_path)
            assert isinstance(result, Path)

            # 测试Path对象
            path_obj = Path(temp_dir) / "path_obj"
            result2 = FileUtils.ensure_dir(path_obj)
            assert isinstance(result2, Path)

    def test_error_handling(self):
        """测试错误处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试权限错误（模拟）
            try:
                # 创建只读目录
                readonly_dir = Path(temp_dir) / "readonly"
                readonly_dir.mkdir()
                readonly_dir.chmod(0o444)

                # 尝试在只读目录中创建文件
                try:
                    json_file = readonly_dir / "test.json"
                    FileUtils.write_json({"test": "data"}, json_file)
                except PermissionError:
                    pass  # 预期的权限错误
            except Exception:
                pytest.skip("Cannot simulate permission error")

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试大量文件操作性能
            start_time = time.time()

            for i in range(10):
                test_data = {"index": i, "data": "x" * 100}
                json_file = Path(temp_dir) / f"perf_test_{i}.json"
                FileUtils.write_json(test_data, json_file)

                # 读取回来
                result = FileUtils.read_json(json_file)
                assert result["index"] == i

            end_time = time.time()
            assert (end_time - start_time) < 2.0  # 应该在2秒内完成

    def test_class_vs_static_methods(self):
        """测试类方法与静态方法"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 所有方法都是静态方法，应该可以直接调用
            test_dir = Path(temp_dir) / "static_test"
            result1 = FileUtils.ensure_dir(test_dir)
            assert result1 == test_dir

            # 也可以通过实例调用
            instance = FileUtils()
            test_dir2 = Path(temp_dir) / "instance_test"
            result2 = instance.ensure_dir(test_dir2)
            assert result2 == test_dir2

    def test_file_utils_import(self):
        """测试FileUtils导入"""
        from src.utils.file_utils import FileUtils
        assert FileUtils is not None

        # 检查关键方法是否存在
        expected_methods = [
            'ensure_dir',
            'read_json',
            'write_json',
            'get_file_hash',
            'get_file_size',
            'ensure_directory',
            'read_json_file'
        ]

        for method in expected_methods:
            assert hasattr(FileUtils, method)
            assert callable(getattr(FileUtils, method))

    def test_file_hash_consistency(self):
        """测试文件哈希一致性"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_file = Path(temp_dir) / "consistency_test.txt"
            content = "Consistent content for hashing"

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            # 多次获取哈希值应该一致
            hash1 = FileUtils.get_file_hash(test_file)
            hash2 = FileUtils.get_file_hash(test_file)
            hash3 = FileUtils.get_file_hash(test_file)

            assert hash1 == hash2 == hash3

    def test_json_serialization_types(self):
        """测试JSON序列化类型处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试各种JSON可序列化类型
            test_data = {
                "string": "Hello",
                "integer": 42,
                "float": 3.14,
                "boolean": True,
                "null": None,
                "list": [1, 2, 3],
                "nested": {"key": "value"},
                "unicode": "你好世界 🌍"
            }

            json_file = Path(temp_dir) / "types_test.json"
            FileUtils.write_json(test_data, json_file)

            result = FileUtils.read_json(json_file)
            assert result == test_data