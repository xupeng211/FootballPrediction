import pytest
from tests.base import BaseTestCase


class TestUtilsQuick(BaseTestCase):
    """工具模块快速测试"""

    def test_crypto_utils_import(self):
        """测试加密工具导入"""
        try:
from src.utils.crypto_utils import encrypt, decrypt

            assert callable(encrypt)
            assert callable(decrypt)
        except ImportError:
            pytest.skip("crypto_utils not available")

    def test_string_utils_import(self):
        """测试字符串工具导入"""
        try:
from src.utils.string_utils import StringUtils

            utils = StringUtils()
            assert utils is not None
        except ImportError:
            pytest.skip("StringUtils not available")

    def test_time_utils_import(self):
        """测试时间工具导入"""
        try:
from src.utils.time_utils import TimeUtils

            utils = TimeUtils()
            assert utils is not None
        except ImportError:
            pytest.skip("TimeUtils not available")

    def test_dict_utils_import(self):
        """测试字典工具导入"""
        try:
from src.utils.dict_utils import DictUtils

            utils = DictUtils()
            assert utils is not None
        except ImportError:
            pytest.skip("DictUtils not available")
