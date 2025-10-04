import pytest

_pytestmark = pytest.mark.unit
class TestStringUtils:
    """测试StringUtils类的所有方法"""
    def test_truncate_short_text(self):
        """测试截断短文本"""
        _result = StringUtils.truncate("短文本[", 10)": assert result  == = 10)":, f"result  should be = 10)":", f"result should be 10)":" assert result  == = 6, f"result  should be = 6",, f"result should be 6," "]!!!")": assert result  == = 5)":, f"result  should be = 5)":", f"result should be 5)":" assert result  == = 456.0]", f"result  should be = 456.0]"", f"result should be 456.0]"" def test_extract_numbers_floats(self):""
        "]""测试提取小数"""
        _result = StringUtils.extract_numbers("温度是23.5度，湿度是60.2%")": assert result  == = 60.2]", f"result  should be = 60.2]"", f"result should be 60.2]"" def test_extract_numbers_negative(self):""
        """测试提取负数"""
        _result = StringUtils.extract_numbers("温度-10.5度，下降了-2.3度[")": assert result  == = -2.3]", f"result  should be = -2.3]"", f"result should be -2.3]"" def test_extract_numbers_no_numbers(self):""
        "]""测试无数字的文本"""
        _result = StringUtils.extract_numbers("没有任何数字的文本[")": assert result  == = 10.0, f"result  should be = 10.0",, f"result should be 10.0," 100.0]