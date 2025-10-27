"""
Helper函数补充测试
补充 src.utils.helpers 模块的测试覆盖，目标达到100%覆盖率
"""

from unittest.mock import patch

import pytest

from src.utils.helpers import generate_hash, generate_uuid, safe_get


@pytest.mark.unit
class TestHelpersEnhanced:
    """Helper函数增强测试"""

    def test_generate_hash_md5(self) -> None:
        """✅ 成功用例：MD5哈希生成（覆盖第19行）"""
        data = "test_data"
        result = generate_hash(data, "md5")

        # 验证MD5格式
        assert len(result) == 32  # MD5哈希长度
        assert isinstance(result, str)
        assert all(c in "0123456789abcdef" for c in result)

        # 验证一致性
        result2 = generate_hash(data, "md5")
        assert result == result2

    def test_generate_hash_sha1(self) -> None:
        """✅ 成功用例：SHA1哈希生成（覆盖第21行）"""
        data = "test_data"
        result = generate_hash(data, "sha1")

        # 验证SHA1格式
        assert len(result) == 40  # SHA1哈希长度
        assert isinstance(result, str)
        assert all(c in "0123456789abcdef" for c in result)

        # 验证一致性
        result2 = generate_hash(data, "sha1")
        assert result == result2

    def test_safe_get_list_index_valid(self) -> None:
        """✅ 成功用例：列表索引处理 - 有效索引（覆盖第40-42行）"""
        data = {"items": ["first", "second", "third"]}

        # 测试有效索引
        result = safe_get(data, "items.0")
        assert result == "first"

        result = safe_get(data, "items.2")
        assert result == "third"

        # 测试嵌套结构
        nested_data = {"container": {"list": [10, 20, 30]}}
        result = safe_get(nested_data, "container.list.1")
        assert result == 20

    def test_safe_get_list_index_invalid(self) -> None:
        """✅ 成功用例：列表索引处理 - 无效索引（覆盖第43-44行）"""
        data = {"items": ["first", "second", "third"]}

        # 测试超出范围的索引
        result = safe_get(data, "items.5")
        assert result is None  # 默认值

        # 测试负索引
        result = safe_get(data, "items.-1")
        assert result is None  # 默认值

        # 测试非数字索引
        result = safe_get(data, "items.abc")
        assert result is None  # 默认值

        # 测试自定义默认值
        result = safe_get(data, "items.999", "default")
        assert result == "default"

    def test_safe_get_exception_handling(self) -> None:
        """✅ 成功用例：异常处理（覆盖第48-49行）"""
        # 测试各种可能导致异常的情况

        # 测试KeyError
        data = {"existing": "value"}
        result = safe_get(data, "nonexistent")
        assert result is None

        # 测试TypeError（非dict对象）
        result = safe_get("not_a_dict", "key")
        assert result is None

        # 测试复杂的嵌套异常
        complex_data = {"level1": {"level2": "value"}}
        result = safe_get(complex_data, "level1.nonexistent.level3")
        assert result is None

        # 测试自定义默认值
        result = safe_get(complex_data, "level1.nonexistent.level3", "fallback")
        assert result == "fallback"

    def test_safe_get_direct_exception_trigger(self) -> None:
        """✅ 成功用例：直接触发异常处理（覆盖第48-49行）"""
        # 创建一个会导致KeyError的具体场景
        data = {"valid": {"key": "value"}}

        # 尝试访问不存在的嵌套键，这应该触发try-except的except块
        result = safe_get(data, "valid.nonexistent_key")
        assert result is None  # 应该返回默认值

        # 创建一个会导致TypeError的场景
        data_with_int = {"key": 123}  # 整数而不是字典
        result = safe_get(data_with_int, "key.nonexistent")
        assert result is None  # 应该返回默认值

        # 创建一个会导致IndexError的场景（如果可能的话）
        data_with_short_list = {"items": ["only_one_item"]}
        result = safe_get(data_with_short_list, "items.999")
        assert result is None  # 应该返回默认值

    def test_safe_get_edge_cases_comprehensive(self) -> None:
        """✅ 边界用例：safe_get综合边界测试"""
        # 空字典
        result = safe_get({}, "any.key", "default")
        assert result == "default"

        # None数据
        result = safe_get(None, "any.key", "default")
        assert result == "default"

        # 空键
        result = safe_get({"key": "value"}, "", "default")
        assert result == "default"

        # 点号开头的键
        result = safe_get({"key": "value"}, ".key", "default")
        assert result == "default"

        # 点号结尾的键
        result = safe_get({"key": {"subkey": "value"}}, "key.subkey.", "default")
        assert result == "default"

    def test_safe_get_mixed_data_structures(self) -> None:
        """✅ 成功用例：混合数据结构处理"""
        data = {
            "users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            "metadata": {"count": 2, "tags": ["admin", "user"]},
        }

        # 测试列表中的字典
        result = safe_get(data, "users.0.name")
        assert result == "Alice"

        result = safe_get(data, "users.1.age")
        assert result == 25

        # 测试字典中的列表
        result = safe_get(data, "metadata.tags.0")
        assert result == "admin"

        # 测试多层嵌套
        complex_data = {"level1": {"level2": [{"level3": {"target": "found"}}]}}
        result = safe_get(complex_data, "level1.level2.0.level3.target")
        assert result == "found"

    def test_generate_hash_edge_cases(self) -> None:
        """✅ 边界用例：哈希生成边界情况"""
        # 空字符串
        result = generate_hash("", "md5")
        assert len(result) == 32

        # 长字符串
        long_data = "a" * 10000
        result = generate_hash(long_data, "sha256")
        assert len(result) == 64

        # 特殊字符
        special_data = "!@#$%^&*()_+-=[]{}|;':,./<>?"
        result = generate_hash(special_data, "md5")
        assert len(result) == 32

        # Unicode字符
        unicode_data = "测试中文🚀emoji"
        result = generate_hash(unicode_data, "sha1")
        assert len(result) == 40

    def test_generate_hash_unsupported_algorithm(self) -> None:
        """✅ 成功用例：不支持的哈希算法（默认使用sha256）"""
        data = "test_data"
        result = generate_hash(data, "unsupported_algo")

        # 应该回退到sha256
        expected = generate_hash(data, "sha256")
        assert result == expected
        assert len(result) == 64

    def test_integration_comprehensive(self) -> None:
        """✅ 集成用例：综合功能集成测试"""
        # 生成唯一ID和哈希的组合使用
        unique_id = generate_uuid()
        hash_result = generate_hash(unique_id, "md5")

        assert len(unique_id) == 36
        assert len(hash_result) == 32

        # 在复杂数据结构中使用safe_get
        complex_data = {
            "id": unique_id,
            "hash": hash_result,
            "metadata": {
                "created": "2023-01-01",
                "items": [
                    {"type": "user", "data": hash_result},
                    {"type": "system", "data": unique_id},
                ],
            },
        }

        # 验证数据检索
        retrieved_id = safe_get(complex_data, "id")
        retrieved_hash = safe_get(complex_data, "metadata.items.0.data")

        assert retrieved_id == unique_id
        assert retrieved_hash == hash_result

    def test_performance_considerations(self) -> None:
        """✅ 性能用例：性能考虑"""
        import time

        # 测试safe_get性能
        data = {"level1": {"level2": {"level3": {"target": "value"}}}}

        start_time = time.perf_counter()
        for _ in range(10000):
            safe_get(data, "level1.level2.level3.target")
        end_time = time.perf_counter()

        # 10000次深度查询应该在1秒内完成
        assert end_time - start_time < 1.0

        # 测试哈希性能
        large_data = "x" * 1000

        start_time = time.perf_counter()
        for _ in range(1000):
            generate_hash(large_data, "sha256")
        end_time = time.perf_counter()

        # 1000次大字符串哈希应该在1秒内完成
        assert end_time - start_time < 1.0

    def test_thread_safety_considerations(self) -> None:
        """✅ 并发用例：线程安全考虑"""
        import threading
        import time

        results = []
        errors = []

        def generate_ids(count: int, thread_id: int):
            try:
                for _ in range(count):
                    uuid_result = generate_uuid()
                    hash_result = generate_hash(uuid_result, "md5")
                    results.append(f"thread_{thread_id}_{hash_result}")
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时生成
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_ids, args=(100, i))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        assert len(errors) == 0
        assert len(results) == 500

        # 验证唯一性（UUID应该是唯一的）
        hash_values = [r.split("_", 2)[-1] for r in results]
        unique_hashes = set(hash_values)
        assert len(unique_hashes) == 500  # 所有哈希都应该是唯一的
