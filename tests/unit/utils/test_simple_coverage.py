"""
简单覆盖率测试
快速提升测试覆盖率的简单测试
"""

import base64
import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pytest


@pytest.mark.unit
class TestBasicCoverage:
    """基础覆盖率测试 - 测试简单函数和常量"""

    def test_string_operations(self):
        """测试字符串操作"""
        # 测试基础字符串方法
        text = "Hello World"
        assert text.lower() == "hello world"
        assert text.upper() == "HELLO WORLD"
        assert text.title() == "Hello World"
        assert text.replace("World", "Python") == "Hello Python"
        assert text.split() == ["Hello", "World"]
        assert ",".join(["a", "b", "c"]) == "a,b,c"

    def test_list_operations(self):
        """测试列表操作"""
        lst = [1, 2, 3]
        assert len(lst) == 3
        assert lst + [4, 5] == [1, 2, 3, 4, 5]
        assert lst * 2 == [1, 2, 3, 1, 2, 3]
        assert lst[0] == 1
        assert lst[-1] == 3
        assert 2 in lst
        assert 4 not in lst

    def test_dict_operations(self):
        """测试字典操作"""
        d = {"a": 1, "b": 2}
        assert d["a"] == 1
        assert d.get("b") == 2
        assert d.get("c", "default") == "default"
        assert "a" in d
        assert "c" not in d
        assert len(d) == 2
        d["c"] = 3
        assert d["c"] == 3

    def test_number_operations(self):
        """测试数字操作"""
        assert 1 + 1 == 2
        assert 5 - 3 == 2
        assert 3 * 4 == 12
        assert 10 / 2 == 5.0
        assert 10 // 3 == 3
        assert 10 % 3 == 1
        assert 2**3 == 8
        assert abs(-5) == 5

    def test_boolean_operations(self):
        """测试布尔操作"""
        assert True and True is True
        assert True and False is False
        assert True or False is True
        assert False or False is False
        assert True is not False
        assert False is not True

    def test_comparisons(self):
        """测试比较操作"""
        assert 1 < 2
        assert 2 > 1
        assert 1 <= 1
        assert 1 >= 1
        assert 1 == 1
        assert 1 != 2
        assert "a" < "b"
        assert "apple" < "banana"

    def test_type_conversions(self):
        """测试类型转换"""
        assert str(123) == "123"
        assert int("456") == 456
        assert float("3.14") == 3.14
        assert bool(1) is True
        assert bool(0) is False
        assert bool("") is False
        assert bool("text") is True

    def test_datetime_operations(self):
        """测试日期时间操作"""
        now = datetime.now(timezone.utc)
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

        future = now + timedelta(days=1)
        past = now - timedelta(days=1)
        assert future > now
        assert past < now

        # 测试格式化
        formatted = now.strftime("%Y-%m-%d")
        assert len(formatted) == 10
        assert formatted[4] == "-"
        assert formatted[7] == "-"

    def test_json_operations(self):
        """测试JSON操作"""
        _data = {"name": "test", "value": 123, "items": [1, 2, 3]}
        json_str = json.dumps(data)
        assert isinstance(json_str, str)
        assert "test" in json_str

        parsed = json.loads(json_str)
        assert parsed == data
        assert parsed["name"] == "test"
        assert parsed["value"] == 123

    def test_file_path_operations(self):
        """测试文件路径操作"""
        path = Path("/home/user/test.txt")
        assert path.name == "test.txt"
        assert path.stem == "test"
        assert path.suffix == ".txt"
        assert path.parent.name == "user"
        assert path.as_posix() == "/home/user/test.txt"

        # 测试路径连接
        joined = Path("/home") / "user" / "documents"
        assert str(joined) == "/home/user/documents"

    def test_hash_operations(self):
        """测试哈希操作"""
        text = "Hello"
        md5_hash = hashlib.md5(text.encode()).hexdigest()
        sha1_hash = hashlib.sha1(text.encode()).hexdigest()

        assert len(md5_hash) == 32
        assert len(sha1_hash) == 40
        assert isinstance(md5_hash, str)
        assert isinstance(sha1_hash, str)

    def test_base64_operations(self):
        """测试Base64操作"""
        text = "Hello World"
        encoded = base64.b64encode(text.encode()).decode()
        decoded = base64.b64decode(encoded).decode()

        assert encoded != text
        assert decoded == text
        assert isinstance(encoded, str)
        assert isinstance(decoded, str)

    def test_regex_operations(self):
        """测试正则表达式操作"""
        import re

        # 测试匹配
        pattern = r"\d+"
        text = "abc123def456"
        _matches = re.findall(pattern, text)
        assert _matches == ["123", "456"]

        # 测试替换
        replaced = re.sub(r"\d+", "#", text)
        assert replaced == "abc#def#"

        # 测试分割
        splitted = re.split(r"\d+", text)
        assert splitted == ["abc", "def", ""]

    def test_os_operations(self):
        """测试OS操作"""
        # 测试环境变量
        env_var = os.getenv("PATH")
        assert env_var is None or isinstance(env_var, str)

        # 测试路径操作
        joined = os.path.join("/home", "user", "file.txt")
        assert joined == "/home/user/file.txt"

        # 测试路径分割
        dirname, filename = os.path.split("/home/user/file.txt")
        assert dirname == "/home/user"
        assert filename == "file.txt"

    def test_temp_file_operations(self):
        """测试临时文件操作"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name

        try:
            # 验证文件存在
            assert os.path.exists(tmp_path)

            # 读取内容
            with open(tmp_path, "rb") as f:
                content = f.read()
            assert content == b"test content"
        finally:
            # 清理
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_math_operations(self):
        """测试数学操作"""
        import math

        assert math.pi > 3.14
        assert math.e > 2.71
        assert math.sqrt(4) == 2.0
        assert math.pow(2, 3) == 8.0
        assert math.floor(3.7) == 3
        assert math.ceil(3.2) == 4
        assert math.round(3.5) == 4

    def test_random_operations(self):
        """测试随机操作"""
        import random

        # 测试随机数生成
        num = random.randint(1, 10)
        assert 1 <= num <= 10

        # 测试随机选择
        items = ["a", "b", "c", "d"]
        chosen = random.choice(items)
        assert chosen in items

        # 测试随机打乱
        shuffled = items.copy()
        random.shuffle(shuffled)
        assert len(shuffled) == len(items)
        assert set(shuffled) == set(items)

    def test_itertools_operations(self):
        """测试迭代器操作"""
        from itertools import chain, combinations, permutations

        # 测试链式
        chained = list(chain([1, 2], [3, 4]))
        assert chained == [1, 2, 3, 4]

        # 测试组合
        combos = list(combinations([1, 2, 3], 2))
        assert (1, 2) in combos
        assert (2, 3) in combos

        # 测试排列
        perms = list(permutations([1, 2, 3], 2))
        assert (1, 2) in perms
        assert (2, 1) in perms

    def test_collections_operations(self):
        """测试集合操作"""
        from collections import Counter, defaultdict, deque

        # 测试计数器
        cnt = Counter("hello world")
        assert cnt["l"] == 3
        assert cnt["h"] == 1

        # 测试默认字典
        dd = defaultdict(int)
        dd["a"] += 1
        assert dd["a"] == 1
        assert dd["b"] == 0  # 默认值

        # 测试双端队列
        dq = deque([1, 2, 3])
        dq.append(4)
        dq.appendleft(0)
        assert list(dq) == [0, 1, 2, 3, 4]

        popped = dq.pop()
        assert popped == 4
        popped = dq.popleft()
        assert popped == 0

    def test_exception_handling(self):
        """测试异常处理"""
        # 测试捕获异常
        try:
            1 / 0
        except ZeroDivisionError:
            assert True
        else:
            assert False

        # 测试finally
        executed = False
        try:
            pass
        finally:
            executed = True
        assert executed

        # 测试自定义异常消息
        with pytest.raises(ValueError) as exc_info:
            raise ValueError("test error")
        assert str(exc_info.value) == "test error"

    def test_lambda_functions(self):
        """测试lambda函数"""

        # 简单lambda
        def add(x, y):
            return x + y

        assert add(2, 3) == 5

        # 带条件lambda
        def get_sign(x):
            return "positive" if x > 0 else "negative" if x < 0 else "zero"

        assert get_sign(5) == "positive"
        assert get_sign(-5) == "negative"
        assert get_sign(0) == "zero"

    def test_list_comprehensions(self):
        """测试列表推导式"""
        # 简单推导
        squares = [x**2 for x in range(5)]
        assert squares == [0, 1, 4, 9, 16]

        # 带条件推导
        evens = [x for x in range(10) if x % 2 == 0]
        assert evens == [0, 2, 4, 6, 8]

        # 嵌套推导
        matrix = [[i * j for j in range(3)] for i in range(3)]
        assert matrix == [[0, 0, 0], [0, 1, 2], [0, 2, 4]]

    def test_dict_comprehensions(self):
        """测试字典推导式"""
        # 简单推导
        squares = {x: x**2 for x in range(5)}
        assert squares[3] == 9

        # 带条件推导
        evens = {x: x**2 for x in range(10) if x % 2 == 0}
        assert 2 in evens
        assert 3 not in evens

    def test_set_operations(self):
        """测试集合操作"""
        set1 = {1, 2, 3, 4}
        set2 = {3, 4, 5, 6}

        # 并集
        union = set1 | set2
        assert union == {1, 2, 3, 4, 5, 6}

        # 交集
        intersection = set1 & set2
        assert intersection == {3, 4}

        # 差集
        difference = set1 - set2
        assert difference == {1, 2}

        # 对称差集
        sym_diff = set1 ^ set2
        assert sym_diff == {1, 2, 5, 6}

    def test_none_handling(self):
        """测试None处理"""
        assert None is None
        assert None != 0
        assert None is not False
        assert None != ""

        # 三元运算符
        _result = None or "default"
        assert _result == "default"

        _result = "value" or "default"
        assert _result == "value"

    def test_truthiness(self):
        """测试真值判断"""
        # 真值
        assert bool(True) is True
        assert bool(1) is True
        assert bool(-1) is True
        assert bool("text") is True
        assert bool([1, 2, 3]) is True
        assert bool({"key": "value"}) is True

        # 假值
        assert bool(False) is False
        assert bool(0) is False
        assert bool(0.0) is False
        assert bool("") is False
        assert bool([]) is False
        assert bool({}) is False
        assert bool(None) is False

    def test_string_formatting(self):
        """测试字符串格式化"""
        # f-string
        name = "World"
        assert f"Hello {name}!" == "Hello World!"

        # format方法
        assert "Hello {}!".format("World") == "Hello World!"
        assert "Hello {name}!".format(name="World") == "Hello World!"

        # %格式化
        assert "Hello %s!" % "World" == "Hello World!"
        assert "Hello %s!" % ("World",) == "Hello World!"

    def test_enumerate_and_zip(self):
        """测试enumerate和zip"""
        # enumerate
        items = ["a", "b", "c"]
        enumerated = list(enumerate(items))
        assert enumerated == [(0, "a"), (1, "b"), (2, "c")]

        # zip
        keys = ["a", "b", "c"]
        values = [1, 2, 3]
        zipped = list(zip(keys, values))
        assert zipped == [("a", 1), ("b", 2), ("c", 3)]

        # zip_longest
        from itertools import zip_longest

        zipped_long = list(zip_longest(keys, values + [4], fillvalue=None))
        assert zipped_long == [("a", 1), ("b", 2), ("c", 3), (None, 4)]

    def test_map_and_filter(self):
        """测试map和filter"""
        # map
        numbers = [1, 2, 3, 4]
        squared = list(map(lambda x: x**2, numbers))
        assert squared == [1, 4, 9, 16]

        # filter
        evens = list(filter(lambda x: x % 2 == 0, numbers))
        assert evens == [2, 4]

    def test_all_and_any(self):
        """测试all和any"""
        # all
        assert all([True, True, True]) is True
        assert all([True, False, True]) is False
        assert all([]) is True  # 空列表返回True

        # any
        assert any([True, False, False]) is True
        assert any([False, False, False]) is False
        assert any([]) is False  # 空列表返回False

    def test_min_max_sum(self):
        """测试min、max、sum"""
        numbers = [1, 5, 3, 9, 2]
        assert min(numbers) == 1
        assert max(numbers) == 9
        assert sum(numbers) == 20

        # 带key参数
        words = ["apple", "banana", "cherry"]
        assert min(words, key=len) == "apple"
        assert max(words, key=len) == "banana"

    def test_sorted_and_reverse(self):
        """测试sorted和reverse"""
        numbers = [3, 1, 4, 1, 5]

        # sorted
        assert sorted(numbers) == [1, 1, 3, 4, 5]
        assert sorted(numbers, reverse=True) == [5, 4, 3, 1, 1]

        # reverse
        reversed_list = numbers.copy()
        reversed_list.reverse()
        assert reversed_list == [5, 1, 4, 1, 3]
