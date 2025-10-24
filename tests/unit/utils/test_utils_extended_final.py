# from src.utils.crypto_utils import CryptoUtils
# from src.utils.dict_utils import DictUtils
# from src.utils.string_utils import StringUtils
# from src.utils.time_utils import TimeUtils
# from src.utils.file_utils import FileUtils


@pytest.mark.unit

def test_crypto_utils_extended():
    # 测试加密功能
    password = "test123"
    hashed = CryptoUtils.hash_password(password)
    assert hashed != password

    # 测试ID生成
    id1 = CryptoUtils.generate_uuid()
    id2 = CryptoUtils.generate_uuid()
    assert id1 != id2
    assert len(id1) == 36  # UUID长度

    # 测试短ID生成
    short_id = CryptoUtils.generate_short_id(8)
    assert len(short_id) == 8

    # 测试字符串哈希
    text = "test"
    hashed = CryptoUtils.hash_string(text)
    assert len(hashed) == 32  # MD5长度


def test_dict_utils_extended():
    # 测试字典扁平化
    _data = {"a": {"b": {"c": 1}}}
    flat = DictUtils.flatten_dict(data)
    assert "a.b.c" in flat
    assert flat["a.b.c"] == 1

    # 测试深度合并
    dict1 = {"a": {"x": 1}, "b": 2}
    dict2 = {"a": {"y": 2}, "c": 3}
    merged = DictUtils.deep_merge(dict1, dict2)
    assert merged == {"a": {"x": 1, "y": 2}, "b": 2, "c": 3}

    # 测试过滤None值
    data_with_none = {"a": 1, "b": None, "c": 3}
    filtered = DictUtils.filter_none_values(data_with_none)
    assert filtered == {"a": 1, "c": 3}


def test_string_utils_extended():
    # 测试字符串操作
    text = "This is a very long string"
    _result = StringUtils.truncate(text, 10)
    assert len(result) <= 13  # 10 + 3 for ...

    # 测试驼峰转下划线
    camel = "testString"
    snake = StringUtils.camel_to_snake(camel)
    assert snake == "test_string"


def test_time_utils_extended():
    # 测试时间格式化
    from datetime import datetime
import pytest

    now = datetime.now()
    formatted = TimeUtils.format_datetime(now)
    assert formatted is not None


def test_file_utils_extended():
    # 测试确保目录存在
    from pathlib import Path

    test_dir = Path("/tmp/test_football")
    _result = FileUtils.ensure_dir(test_dir)
    assert _result.exists()

    # 测试JSON读写
    test_data = {"key": "value"}
    test_file = test_dir / "test.json"
    FileUtils.write_json(test_data, test_file)
    read_data = FileUtils.read_json(test_file)
    assert read_data == test_data
