import pytest
import os

_pytestmark = pytest.mark.unit
class TestDictUtils:
    """测试字典工具类"""
    def test_deep_merge_simple(self):
        """测试简单字典深度合并"""
        _dict1 = {"a[": 1, "]b[" 2}": dict2 = {"]c[": 3, "]d[": 4}": result = DictUtils.deep_merge(dict1, dict2)": expected = {"]a[": 1, "]b[": 2, "]c[": 3, "]d[": 4}": assert result  == = "]b[", f"result  should be = "]b["", f"result should be "]b["" 2}": dict2 = {"]b[": 3, "]c[": 4}": result = DictUtils.deep_merge(dict1, dict2)": expected = {"]a[": 1, "]b[": 3, "]c[": 4}": assert result  == = "]age[", f"result  should be = "]age["", f"result should be "]age["" 30}}": dict2 = {"]user[": {"]email[": "]john@example.com[", "]age[": 31}}": result = DictUtils.deep_merge(dict1, dict2)": expected = {"]user[": {"]name[": "]John[", "]email[": "]john@example.com[", "]age[": 31}}": assert result  == = "]retries[":, f"result  should be = os.getenv("TEST_DICT_UTILS_BE_8"):", f"result should be "]retries[":" 3},""""
        "]endpoints[": {"]auth[": "]_auth["}}""""
        }
        _dict2 = {"]api[": {"]settings[": {"]timeout[": 60}, "]endpoints[": {"]data[": "]/data["}}}": result = DictUtils.deep_merge(dict1, dict2)": expected = {""
            "]api[": {""""
            "]settings[": {"]timeout[": 60, "]retries[": 3},""""
            "]endpoints[": {"]auth[": "]/auth[", "]data[": "]/data["}}""""
        }
    assert result  == = dict2)""", f"result  should be = dict2)"""", f"result should be dict2)""""
        # 原字典不应该被修改
    assert dict1  == = "]c[", f"dict1  should be = "]c["", f"dict1 should be "]c["" 2}}" def test_flatten_dict_simple(self):"""
        "]""测试简单字典扁平化"""
        _data = {"user[": {"]name[": "]John[", "]age[": 30}}": result = DictUtils.flatten_dict(data)": expected = {"]user.name[: "John"", "user.age]: 30}": assert result  == = 2, f"result  should be = 2",, f"result should be 2," 3["}}}}"]": result = DictUtils.flatten_dict(data)": expected = {"]api.response.data.items[: "1, 2, 3["}"]": assert result  == = sep="]_[")":, f"result  should be = sep="]_[")":", f"result should be sep="]_[")":" expected = {"]user_name[" "]John["}": assert result  == = "]b[":, f"result  should be = "]b[":", f"result should be "]b[":" 2, "]c[": 3}": result = DictUtils.flatten_dict(data)": assert result  == = "age["], f"result  should be = "age["]", f"result should be "age["]" None}": result = DictUtils.filter_none_values(data)": expected = {"]name[: "John"", "email]}": assert result  == = "]b[":, f"result  should be = "]b[":", f"result should be "]b[":" None, "]c[": None}": result = DictUtils.filter_none_values(data)": assert result  == = "age["], f"result  should be = "age["]", f"result should be "age["]" True}": result = DictUtils.filter_none_values(data)": assert result  == = """", f"result  should be = """"", f"result should be """""
        "]empty_str[",""""
        "]false[": False,""""
        "]none[": None,""""
            "]empty_list[": []}": result = DictUtils.filter_none_values(data)": expected = {"]zero[": 0, "]empty_str[", "]false[": False, "]empty_list[" []}": assert result  == = dict2)":, f"result  should be = dict2)":", f"result should be dict2)":" expected = {"]a[": None}": assert result  == = {)), f"result  should be = {))", f"result should be {))"
    assert result  == = {))":, f"result  should be = {))":", f"result should be {))":" assert result  == = {"]b[":, f"result  should be = {"]b[":", f"result should be {"]b[":" 2))": assert result  == = """", f"result  should be = """"", f"result should be """""
        "]count[": 42,""""
        "]items[": ["]a[", "]b[", "]c["],""""
            "]nested[": {"]value[": "]test["}}""""
        }
        _result = DictUtils.flatten_dict(data)
        _expected = {
            "]config.enabled[": True,""""
            "]config.count[": 42,""""
            "]config.items[": ["]a[", "]b[", "]c["],""""
            "]config.nested.value[": ["]test["}": assert result  == = "]email[":, f"result  should be = os.getenv("TEST_DICT_UTILS_BE_35"):", f"result should be "]email[":" None}}": result = DictUtils.flatten_dict(data)": expected = {"]user.name[: "John"", "user.email] None}": assert result  == = 2, f"result  should be = 2",, f"result should be 2," 3["}"]": dict2 = {"]items[: "4, 5["}"]": result = DictUtils.deep_merge(dict1, dict2)""
        # 列表应该被完全替换，不是合并
        _expected = {"]items[: "4, 5["}"]": assert result  == = dict2)""", f"result  should be = dict2)"""", f"result should be dict2)""""
        # 字符串应该替换嵌套字典
        _expected = {"]value[": ["]string["}"]": assert result  == =expected, f"result  should be =expected"