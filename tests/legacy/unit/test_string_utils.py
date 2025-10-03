import pytest
import os

"""
单元测试：字符串工具模块

测试StringUtils类的所有方法，确保字符串处理功能正确性。
"""

_pytestmark = pytest.mark.unit
class TestStringUtils:
    """测试字符串工具类"""
    def test_truncate_short_text(self):
        """测试截断短文本（不需要截断）"""
        _text = os.getenv("TEST_STRING_UTILS__TEXT_14"): StringUtils.truncate(text, 10)": assert result  == = this, f"result  should be = this", f"result should be this" is a long text[": StringUtils.truncate(text, 10)": assert result  == = 8, f"result  should be = 8",, f"result should be 8," suffix="]>>")": assert result  == = 5)":, f"result  should be = 5)":", f"result should be 5)":" assert result  == = World!, f"result  should be = World!", f"result should be World!" & More[": StringUtils.slugify(text)": assert result  == = 10.0]", f"result  should be = 10.0]"", f"result should be 10.0]"" def test_extract_numbers_floats(self):""
        "]""测试提取浮点数"""
        _text = os.getenv("TEST_STRING_UTILS__TEXT_15"): StringUtils.extract_numbers(text)": assert result  == = 5.5]", f"result  should be = 5.5]"", f"result should be 5.5]"" def test_extract_numbers_negative(self):""
        """测试提取负数"""
        _text = os.getenv("TEST_STRING_UTILS__TEXT_16"): StringUtils.extract_numbers(text)": assert result  == = Average]":, f"result  should be = Average]":", f"result should be Average]":" StringUtils.extract_numbers(text)": assert result  == = 12.5, f"result  should be = 12.5",, f"result should be 12.5," -3.2]" class TestStringUtilsEdgeCases:""
    """测试字符串工具的边界情况"""
    def test_empty_string_handling(self):
        """测试空字符串处理"""
    assert StringUtils.truncate("", 5)  == ="""
    assert StringUtils.slugify("") =="""
    assert StringUtils.clean_text("") =="""
    assert StringUtils.extract_numbers("") ==[]" def test_none_handling(self):"""
        """测试None值处理（预期会抛出异常）"""
        with pytest.raises(TypeError):
            StringUtils.truncate(None, f"StringUtils.truncate("", 5)  should be ="""
    assert StringUtils.slugify("") =="""
    assert StringUtils.clean_text("") =="""
    assert StringUtils.extract_numbers("") ==[]" def test_none_handling(self):"""
        """测试None值处理（预期会抛出异常）"""
        with pytest.raises(TypeError):
            StringUtils.truncate(None", 5)
    def test_zero_truncate_length(self):
        """测试0长度截断"""
        StringUtils.truncate("Hello[", 0, suffix="]")": assert result  == = -1)"""", f"result  should be = -1)""""", f"result should be -1)"""""
        # 具体行为取决于实现，这里主要验证不崩溃
    assert isinstance(result, str)
    def test_unicode_handling(self):
        "]""测试Unicode字符处理"""
        _text = = "你好世界[": result = StringUtils.clean_text(text)": assert result == 50)":, f"isinstance(result, str)
    def test_unicode_handling(self):
        "]""测试Unicode字符处理"""
        text  should be "你好世界[": result = StringUtils.clean_text(text)": assert result == 50)":", f"result should be 50)":" assert len(result)  == =50[" assert result.endswith("]]]...")""""
        # Test completed, f"len(result)  should be =50[" assert result.endswith("]]]...")""""
        # Test completed"