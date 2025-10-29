from typing import Optional
from typing import Callable
from typing import Any
from typing import Tuple
from typing import List
from typing import Dict
"""
集合工具测试
"""

import pytest

T = TypeVar("T")


class CollectionUtils:
    """集合工具类"""

    @staticmethod
    def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
        """将列表分块"""
        if chunk_size <= 0:
            return []
        return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]

    @staticmethod
    def flatten(nested_list: List[Any]) -> List[Any]:
        """展平嵌套列表"""
        _result = []
        for item in nested_list:
            if isinstance(item, list):
                result.extend(CollectionUtils.flatten(item))
            else:
                result.append(item)
        return result

    @staticmethod
    def unique(lst: List[T]) -> List[T]:
        """去重并保持顺序"""
        seen = set()
        _result = []
        for item in lst:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def group_by(lst: List[T], key_func: Callable[[T], Any]) -> Dict[Any, List[T]]:
        """根据键函数分组"""
        groups = {}
        for item in lst:
            key = key_func(item)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        return groups

    @staticmethod
    def partition(lst: List[T], predicate: Callable[[T], bool]) -> Tuple[List[T], List[T]]:
        """将列表分为满足和不满足条件的两部分"""
        true_items = []
        false_items = []
        for item in lst:
            if predicate(item):
                true_items.append(item)
            else:
                false_items.append(item)
        return true_items, false_items

    @staticmethod
    def find_all(lst: List[T], predicate: Callable[[T], bool]) -> List[T]:
        """查找所有满足条件的元素"""
        return [item for item in lst if predicate(item)]

    @staticmethod
    def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        _result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(_result[key], dict) and isinstance(value, dict):
                _result[key] = CollectionUtils.deep_merge(_result[key], value)
            else:
                _result[key] = value
        return result

    @staticmethod
    def pick_dict(dictionary: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """从字典中选择指定的键"""
        return {key: dictionary[key] for key in keys if key in dictionary}

    @staticmethod
    def omit_dict(dictionary: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """从字典中排除指定的键"""
        return {key: value for key, value in dictionary.items() if key not in keys}

    @staticmethod
    def map_keys(dictionary: Dict[str, Any], key_map: Dict[str, str]) -> Dict[str, Any]:
        """映射字典的键"""
        _result = {}
        for old_key, value in dictionary.items():
            new_key = key_map.get(old_key, old_key)
            _result[new_key] = value
        return result

    @staticmethod
    def invert_dict(dictionary: Dict[Any, Any]) -> Dict[Any, Any]:
        """反转字典（值变键，键变值）"""
        return {value: key for key, value in dictionary.items()}

    @staticmethod
    def is_empty(collection: Any) -> bool:
        """检查集合是否为空"""
        if collection is None:
            return True
        return len(collection) == 0

    @staticmethod
    def not_empty(collection: Any) -> bool:
        """检查集合是否非空"""
        return not CollectionUtils.is_empty(collection)

    @staticmethod
    def compact(lst: List[Optional[T]]) -> List[T]:
        """移除列表中的None值"""
        return [item for item in lst if item is not None]

    @staticmethod
    def without(lst: List[T], *items: T) -> List[T]:
        """移除列表中的指定元素"""
        return [item for item in lst if item not in items]

    @staticmethod
    def intersection(*lists: List[T]) -> List[T]:
        """多个列表的交集"""
        if not lists:
            return []
        _result = set(lists[0])
        for lst in lists[1:]:
            _result = result.intersection(lst)
        return list(result)

    @staticmethod
    def union(*lists: List[T]) -> List[T]:
        """多个列表的并集"""
        _result = set()
        for lst in lists:
            _result = result.union(lst)
        return list(result)

    @staticmethod
    def difference(list1: List[T], list2: List[T]) -> List[T]:
        """列表差集（在list1但不在list2）"""
        return [item for item in list1 if item not in set(list2)]

    @staticmethod
    def symmetric_difference(list1: List[T], list2: List[T]) -> List[T]:
        """对称差集（只在其中一个列表中的元素）"""
        set1, set2 = set(list1), set(list2)
        return list(set1.symmetric_difference(set2))

    @staticmethod
    def zip_dicts(*dicts: Dict[str, Any]) -> Dict[str, List[Any]]:
        """将多个字典的值按键组合成列表"""
        _result = {}
        all_keys = set()
        for d in dicts:
            all_keys.update(d.keys())

        for key in all_keys:
            values = []
            for d in dicts:
                values.append(d.get(key))
            _result[key] = values
        return result

    @staticmethod
    def flatten_dict(dictionary: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
        """展平嵌套字典"""
        _result = {}

        def _flatten(obj: Any, parent_key: str = ""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{parent_key}{separator}{key}" if parent_key else key
                    _flatten(value, new_key)
            else:
                _result[parent_key] = obj

        _flatten(dictionary)
        return result

    @staticmethod
    def unflatten_dict(dictionary: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
        """恢复展平的字典"""
        _result = {}

        for key, value in dictionary.items():
            parts = key.split(separator)
            current = result

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = value

        return result

    @staticmethod
    def sample(lst: List[T], n: int) -> List[T]:
        """随机采样"""
        import random

        if n >= len(lst):
            return lst.copy()
        return random.sample(lst, n)

    @staticmethod
    def shuffle(lst: List[T]) -> List[T]:
        """打乱列表"""
        import random

        _result = lst.copy()
        random.shuffle(result)
        return result

    @staticmethod
    def sort_by(lst: List[T], key_func: Callable[[T], Any], reverse: bool = False) -> List[T]:
        """根据键函数排序"""
        return sorted(lst, key=key_func, reverse=reverse)

    @staticmethod
    def group_consecutive(lst: List[T], predicate: Callable[[T, T], bool]) -> List[List[T]]:
        """将连续满足条件的元素分组"""
        if not lst:
            return []

        groups = [[lst[0]]]
        for i in range(1, len(lst)):
            if predicate(lst[i - 1], lst[i]):
                groups[-1].append(lst[i])
            else:
                groups.append([lst[i]])
        return groups


@pytest.mark.unit
class TestCollectionUtils:
    """测试集合工具类"""

    def test_chunk_list(self):
        """测试列表分块"""
        lst = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        chunks = CollectionUtils.chunk_list(lst, 3)
        assert chunks == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

        # 不均匀分块
        chunks = CollectionUtils.chunk_list(lst, 4)
        assert chunks == [[1, 2, 3, 4], [5, 6, 7, 8], [9]]

        # 空列表
        assert CollectionUtils.chunk_list([], 3) == []

        # 零分块大小
        assert CollectionUtils.chunk_list([1, 2, 3], 0) == []

    def test_flatten(self):
        """测试展平嵌套列表"""
        nested = [1, [2, [3, 4], 5], 6, [7, 8]]
        flattened = CollectionUtils.flatten(nested)
        assert flattened == [1, 2, 3, 4, 5, 6, 7, 8]

        # 空列表
        assert CollectionUtils.flatten([]) == []

        # 已展平的列表
        assert CollectionUtils.flatten([1, 2, 3]) == [1, 2, 3]

    def test_unique(self):
        """测试去重"""
        lst = [1, 2, 2, 3, 1, 4, 3, 5]
        unique_lst = CollectionUtils.unique(lst)
        assert unique_lst == [1, 2, 3, 4, 5]

        # 已去重的列表
        assert CollectionUtils.unique([1, 2, 3]) == [1, 2, 3]

        # 字符串列表
        str_lst = ["a", "b", "a", "c", "b"]
        assert CollectionUtils.unique(str_lst) == ["a", "b", "c"]

    def test_group_by(self):
        """测试分组"""
        people = [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 30},
            {"name": "Charlie", "age": 25},
            {"name": "David", "age": 30},
        ]

        grouped = CollectionUtils.group_by(people, lambda x: x["age"])
        assert len(grouped) == 2
        assert len(grouped[25]) == 2
        assert len(grouped[30]) == 2
        assert grouped[25][0]["name"] == "Alice"

    def test_partition(self):
        """测试分区"""
        lst = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        evens, odds = CollectionUtils.partition(lst, lambda x: x % 2 == 0)
        assert evens == [2, 4, 6, 8]
        assert odds == [1, 3, 5, 7, 9]

    def test_find_all(self):
        """测试查找所有满足条件的元素"""
        lst = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        evens = CollectionUtils.find_all(lst, lambda x: x % 2 == 0)
        assert evens == [2, 4, 6, 8]

        # 字符串列表
        words = ["apple", "banana", "apricot", "cherry"]
        a_words = CollectionUtils.find_all(words, lambda x: x.startswith("a"))
        assert a_words == ["apple", "apricot"]

    def test_deep_merge(self):
        """测试深度合并字典"""
        dict1 = {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}
        dict2 = {"b": {"y": 30, "z": 40}, "d": 4}

        merged = CollectionUtils.deep_merge(dict1, dict2)
        assert merged["a"] == 1
        assert merged["b"]["x"] == 10
        assert merged["b"]["y"] == 30
        assert merged["b"]["z"] == 40
        assert merged["c"] == 3
        assert merged["d"] == 4

    def test_pick_dict(self):
        """测试选择字典键"""
        d = {"a": 1, "b": 2, "c": 3, "d": 4}
        picked = CollectionUtils.pick_dict(d, ["a", "c"])
        assert picked == {"a": 1, "c": 3}

        # 不存在的键
        picked = CollectionUtils.pick_dict(d, ["a", "x"])
        assert picked == {"a": 1}

    def test_omit_dict(self):
        """测试排除字典键"""
        d = {"a": 1, "b": 2, "c": 3, "d": 4}
        omitted = CollectionUtils.omit_dict(d, ["b", "d"])
        assert omitted == {"a": 1, "c": 3}

    def test_map_keys(self):
        """测试映射字典键"""
        d = {"name": "John", "age": 30, "city": "NYC"}
        key_map = {"name": "full_name", "age": "years"}
        mapped = CollectionUtils.map_keys(d, key_map)
        assert mapped == {"full_name": "John", "years": 30, "city": "NYC"}

    def test_invert_dict(self):
        """测试反转字典"""
        d = {"a": 1, "b": 2, "c": 3}
        inverted = CollectionUtils.invert_dict(d)
        assert inverted == {1: "a", 2: "b", 3: "c"}

    def test_is_empty(self):
        """测试检查集合是否为空"""
        assert CollectionUtils.is_empty([]) is True
        assert CollectionUtils.is_empty({}) is True
        assert CollectionUtils.is_empty(set()) is True
        assert CollectionUtils.is_empty(None) is True
        assert CollectionUtils.is_empty([1]) is False
        assert CollectionUtils.is_empty({"a": 1}) is False

    def test_not_empty(self):
        """测试检查集合是否非空"""
        assert CollectionUtils.not_empty([1]) is True
        assert CollectionUtils.not_empty({"a": 1}) is True
        assert CollectionUtils.not_empty([]) is False
        assert CollectionUtils.not_empty({}) is False

    def test_compact(self):
        """测试移除None值"""
        lst = [1, None, 2, None, 3, None]
        compacted = CollectionUtils.compact(lst)
        assert compacted == [1, 2, 3]

        # 没有None值
        assert CollectionUtils.compact([1, 2, 3]) == [1, 2, 3]

    def test_without(self):
        """测试移除指定元素"""
        lst = [1, 2, 3, 2, 4, 2, 5]
        _result = CollectionUtils.without(lst, 2, 4)
        assert _result == [1, 3, 5]

    def test_intersection(self):
        """测试多个列表的交集"""
        list1 = [1, 2, 3, 4]
        list2 = [3, 4, 5, 6]
        list3 = [4, 5, 6, 7]

        _result = CollectionUtils.intersection(list1, list2, list3)
        assert set(result) == {4}

        # 空列表
        assert CollectionUtils.intersection() == []

    def test_union(self):
        """测试多个列表的并集"""
        list1 = [1, 2, 3]
        list2 = [3, 4, 5]
        list3 = [5, 6, 7]

        _result = CollectionUtils.union(list1, list2, list3)
        assert set(result) == {1, 2, 3, 4, 5, 6, 7}

    def test_difference(self):
        """测试列表差集"""
        list1 = [1, 2, 3, 4, 5]
        list2 = [4, 5, 6, 7]

        _result = CollectionUtils.difference(list1, list2)
        assert set(result) == {1, 2, 3}

    def test_symmetric_difference(self):
        """测试对称差集"""
        list1 = [1, 2, 3, 4]
        list2 = [3, 4, 5, 6]

        _result = CollectionUtils.symmetric_difference(list1, list2)
        assert set(result) == {1, 2, 5, 6}

    def test_zip_dicts(self):
        """测试组合字典值"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"a": 10, "b": 20, "c": 30}
        dict3 = {"b": 200, "c": 300}

        _result = CollectionUtils.zip_dicts(dict1, dict2, dict3)
        assert _result["a"] == [1, 10, None]
        assert _result["b"] == [2, 20, 200]
        assert _result["c"] == [None, 30, 300]

    def test_flatten_dict(self):
        """测试展平字典"""
        nested = {"a": 1, "b": {"x": 10, "y": {"z": 100}}, "c": 3}

        flattened = CollectionUtils.flatten_dict(nested)
        assert flattened == {"a": 1, "b.x": 10, "b.y.z": 100, "c": 3}

    def test_unflatten_dict(self):
        """测试恢复展平的字典"""
        flattened = {"a": 1, "b.x": 10, "b.y.z": 100, "c": 3}

        nested = CollectionUtils.unflatten_dict(flattened)
        assert nested == {"a": 1, "b": {"x": 10, "y": {"z": 100}}, "c": 3}

    def test_sample(self):
        """测试随机采样"""
        import random

        random.seed(42)  # 固定随机种子

        lst = list(range(10))
        sample = CollectionUtils.sample(lst, 5)
        assert len(sample) == 5
        assert set(sample).issubset(set(lst))

        # 采样数量大于列表长度
        sample = CollectionUtils.sample(lst, 20)
        assert sample == lst

    def test_shuffle(self):
        """测试打乱列表"""
        import random

        random.seed(42)  # 固定随机种子

        lst = [1, 2, 3, 4, 5]
        shuffled = CollectionUtils.shuffle(lst)
        assert len(shuffled) == 5
        assert set(shuffled) == set(lst)
        # 由于固定了随机种子，结果应该是确定的
        assert shuffled != lst

    def test_sort_by(self):
        """测试根据键函数排序"""
        people = [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 30},
            {"name": "Charlie", "age": 20},
        ]

        # 按年龄排序
        sorted_by_age = CollectionUtils.sort_by(people, lambda x: x["age"])
        ages = [p["age"] for p in sorted_by_age]
        assert ages == [20, 25, 30]

        # 按姓名排序
        sorted_by_name = CollectionUtils.sort_by(people, lambda x: x["name"])
        names = [p["name"] for p in sorted_by_name]
        assert names == ["Alice", "Bob", "Charlie"]

        # 逆序
        sorted_desc = CollectionUtils.sort_by(people, lambda x: x["age"], reverse=True)
        ages = [p["age"] for p in sorted_desc]
        assert ages == [30, 25, 20]

    def test_group_consecutive(self):
        """测试连续分组"""
        lst = [1, 2, 3, 5, 6, 8, 9, 10]

        # 按连续数字分组
        groups = CollectionUtils.group_consecutive(lst, lambda a, b: b == a + 1)
        assert groups == [[1, 2, 3], [5, 6], [8, 9, 10]]

        # 空列表
        assert CollectionUtils.group_consecutive([], lambda a, b: True) == []

        # 单元素列表
        assert CollectionUtils.group_consecutive([1], lambda a, b: True) == [[1]]
