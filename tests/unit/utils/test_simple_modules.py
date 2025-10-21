"""
简单模块测试
"""

import pytest
from unittest.mock import MagicMock, patch
from src.utils import crypto_utils
from src.utils import response
from src.utils import i18n


class TestCryptoUtils:
    """加密工具测试"""

    def test_generate_uuid(self):
        """测试生成UUID"""
        uuid_val = crypto_utils.CryptoUtils.generate_uuid()
        assert isinstance(uuid_val, str)
        assert len(uuid_val) == 36
        assert uuid_val.count("-") == 4

    def test_generate_short_id(self):
        """测试生成短ID"""
        # 测试不同长度
        for length in [8, 16, 32]:
            short_id = crypto_utils.CryptoUtils.generate_short_id(length)
            assert len(short_id) == length
            assert short_id.isalnum()

        # 测试默认长度
        default_id = crypto_utils.CryptoUtils.generate_short_id()
        assert len(default_id) == 8

        # 测试长度为0
        assert crypto_utils.CryptoUtils.generate_short_id(0) == ""

        # 测试大长度
        long_id = crypto_utils.CryptoUtils.generate_short_id(64)
        assert len(long_id) == 64

    def test_hash_string_md5(self):
        """测试MD5哈希"""
        text = "hello world"
        hash_value = crypto_utils.CryptoUtils.hash_string(text, algorithm="md5")
        assert hash_value == "5eb63bbbe01eeed093cb22bb8f5acdc3"
        assert len(hash_value) == 32

    def test_hash_string_sha256(self):
        """测试SHA256哈希"""
        text = "hello world"
        hash_value = crypto_utils.CryptoUtils.hash_string(text, algorithm="sha256")
        assert (
            hash_value
            == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        )
        assert len(hash_value) == 64

    def test_hash_string_default(self):
        """测试默认哈希算法"""
        text = "test"
        hash_value = crypto_utils.CryptoUtils.hash_string(text)
        assert isinstance(hash_value, str)
        assert len(hash_value) > 0

    def test_hash_string_invalid_algorithm(self):
        """测试无效的哈希算法"""
        with pytest.raises(ValueError, match="不支持的哈希算法"):
            crypto_utils.CryptoUtils.hash_string("test", algorithm="invalid")

    def test_hash_password(self):
        """测试密码哈希"""
        password = "mypassword123"
        hashed = crypto_utils.CryptoUtils.hash_password(password)
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hash length

        # 测试带盐值的哈希
        salt = "testsalt"
        hashed_with_salt = crypto_utils.CryptoUtils.hash_password(password, salt)
        assert isinstance(hashed_with_salt, str)
        # 在bcrypt实现中，盐值是编码在哈希结果里的
        assert hashed_with_salt != hashed
        assert hashed != password

    def test_verify_password(self):
        """测试验证密码"""
        password = "mypassword123"
        hashed = crypto_utils.CryptoUtils.hash_password(password)

        # 正确密码
        assert crypto_utils.CryptoUtils.verify_password(password, hashed) is True

        # 错误密码
        assert (
            crypto_utils.CryptoUtils.verify_password("wrongpassword", hashed) is False
        )

        # 空密码和空哈希
        assert crypto_utils.CryptoUtils.verify_password("", "") is True

        # 空密码和非空哈希
        assert crypto_utils.CryptoUtils.verify_password("", hashed) is False

    def test_generate_salt(self):
        """测试生成盐值"""
        salt = crypto_utils.CryptoUtils.generate_salt()
        assert isinstance(salt, str)
        assert len(salt) == 32  # 16 bytes = 32 hex chars

        # 自定义长度
        salt_8 = crypto_utils.CryptoUtils.generate_salt(8)
        assert len(salt_8) == 16

    def test_generate_token(self):
        """测试生成令牌"""
        token = crypto_utils.CryptoUtils.generate_token()
        assert isinstance(token, str)
        assert len(token) == 64  # 32 bytes = 64 hex chars

        # 自定义长度
        token_16 = crypto_utils.CryptoUtils.generate_token(16)
        assert len(token_16) == 32


class TestResponseUtils:
    """响应工具测试"""

    def test_create_success_response(self):
        """测试创建成功响应"""
        _data = {"message": "success"}
        response_obj = response.APIResponse.success(data)

        assert response_obj["success"] is True
        assert response_obj["data"] == data
        assert "message" in response_obj
        assert response_obj["message"] == "操作成功"
        assert "timestamp" in response_obj

    def test_create_success_response_with_custom_message(self):
        """测试带自定义消息的成功响应"""
        _data = {"id": 1}
        custom_message = "创建成功"
        response_obj = response.APIResponse.success(data, message=custom_message)

        assert response_obj["success"] is True
        assert response_obj["data"] == data
        assert response_obj["message"] == custom_message
        assert "timestamp" in response_obj

    def test_create_success_response_without_data(self):
        """测试不带数据的成功响应"""
        response_obj = response.APIResponse.success()
        assert response_obj["success"] is True
        assert "data" not in response_obj
        assert "timestamp" in response_obj

    def test_create_success_response_alias(self):
        """测试成功响应别名方法"""
        _data = {"test": "data"}
        response_obj = response.APIResponse.success_response(data)
        assert response_obj["success"] is True
        assert response_obj["data"] == data

    def test_create_error_response(self):
        """测试创建错误响应"""
        error_msg = "Something went wrong"
        response_obj = response.APIResponse.error(error_msg)

        assert response_obj["success"] is False
        assert response_obj["message"] == error_msg
        assert response_obj["code"] == 500  # 默认错误代码
        assert "timestamp" in response_obj

    def test_create_error_response_with_code(self):
        """测试带错误代码的错误响应"""
        error_msg = "Validation failed"
        error_code = 400
        response_obj = response.APIResponse.error(error_msg, code=error_code)

        assert response_obj["success"] is False
        assert response_obj["message"] == error_msg
        assert response_obj["code"] == error_code
        assert "timestamp" in response_obj

    def test_create_error_response_with_data(self):
        """测试带数据的错误响应"""
        error_msg = "Validation failed"
        details = {"field": "email", "error": "invalid format"}
        response_obj = response.APIResponse.error(error_msg, _data=details)

        assert response_obj["success"] is False
        assert response_obj["message"] == error_msg
        assert response_obj["data"] == details
        assert "timestamp" in response_obj

    def test_create_error_response_alias(self):
        """测试错误响应别名方法"""
        error_msg = "Error occurred"
        response_obj = response.APIResponse.error_response(error_msg)
        assert response_obj["success"] is False
        assert response_obj["message"] == error_msg

    def test_api_response_model(self):
        """测试API响应模型"""
        # 测试成功响应模型
        model = response.APIResponseModel(
            success=True, message="Success", _data={"id": 1}
        )
        assert model.success is True
        assert model.message == "Success"
        assert model._data == {"id": 1}
        assert model.code is None

        # 测试错误响应模型
        error_model = response.APIResponseModel(
            success=False, message="Error", code="400"
        )
        assert error_model.success is False
        assert error_model.code == "400"


class TestI18nUtils:
    """国际化工具测试"""

    def test_supported_languages(self):
        """测试支持的语言列表"""
        from src.utils.i18n import supported_languages

        assert isinstance(supported_languages, dict)
        assert "zh" in supported_languages
        assert "en" in supported_languages
        assert supported_languages["zh"] == "zh_CN"
        assert supported_languages["en"] == "en_US"
        assert supported_languages["zh-CN"] == "zh_CN"
        assert supported_languages["en-US"] == "en_US"

    def test_locale_dir(self):
        """测试本地化目录"""
        from src.utils.i18n import LOCALE_DIR

        assert LOCALE_DIR.name == "locales"
        assert LOCALE_DIR.parent.name == "utils"

    @patch("src.utils.i18n.gettext")
    def test_init_i18n(self, mock_gettext):
        """测试初始化国际化"""
        # 模拟gettext方法
        mock_gettext.bindtextdomain = MagicMock()
        mock_gettext.textdomain = MagicMock()
        mock_gettext.install = MagicMock()

        # 重新初始化
        with patch("os.getenv", return_value="zh_CN"):
            from src.utils.i18n import init_i18n

            init_i18n()

            # 验证调用
            mock_gettext.bindtextdomain.assert_called()
            mock_gettext.textdomain.assert_called()
            mock_gettext.install.assert_called()

    @patch("src.utils.i18n.gettext")
    def test_init_i18n_exception(self, mock_gettext):
        """测试初始化国际化时的异常处理"""
        # 模拟异常
        mock_gettext.bindtextdomain.side_effect = Exception("Test error")

        # 应该不会抛出异常
        try:
            from src.utils.i18n import init_i18n

            init_i18n()
        except Exception:
            pytest.fail("init_i18n应该处理异常并继续执行")

    def test_i18n_module_import(self):
        """测试i18n模块可以正常导入"""
        from src.utils import i18n

        # 验证模块属性
        assert hasattr(i18n, "supported_languages")
        assert hasattr(i18n, "LOCALE_DIR")
        assert hasattr(i18n, "init_i18n")

    def test_i18n_initialization_on_import(self):
        """测试导入时自动初始化"""
        # 由于模块在导入时会自动调用init_i18n
        # 这里主要验证不会抛出异常
        import importlib

        # 重新导入模块
        import sys

        if "src.utils.i18n" in sys.modules:
            del sys.modules["src.utils.i18n"]

        # 应该能成功导入
        import src.utils.i18n

        assert True  # 如果没有异常就算成功
