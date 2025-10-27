# 字典工具高级测试
import pytest

from src.utils.dict_utils import DictUtils


@pytest.mark.unit
def test_flatten_dict():
    nested = {"a": {"b": {"c": 1}}}
    flat = DictUtils.flatten(nested)
    assert "a.b.c" in flat
    assert flat["a.b.c"] == 1


def test_merge_dicts():
    dict1 = {"a": 1}
    dict2 = {"b": 2}
    merged = DictUtils.merge(dict1, dict2)
    assert merged == {"a": 1, "b": 2}


def test_pick_keys():
    data = {"a": 1, "b": 2, "c": 3}
    picked = DictUtils.pick(data, ["a", "c"])
    assert picked == {"a": 1, "c": 3}


def test_omit_keys():
    data = {"a": 1, "b": 2, "c": 3}
    omitted = DictUtils.omit(data, ["b"])
    assert omitted == {"a": 1, "c": 3}
