import base64
import secrets
import urllib.parse
import uuid

import bcrypt

"""
加密工具模块
Crypto Utilities Module

提供密码哈希、令牌生成等加密相关功能。
Provides encryption-related functions such as password hashing and token generation.
"""


class CryptoUtils:
    """加密工具类"""

    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        if len(password) > 72:
            password = password[:72]  # bcrypt限制
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """验证密码"""
        try:
            if not password or not hashed:
                return False
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """生成随机令牌"""
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_uuid() -> str:
        """生成UUID"""
        return str(uuid.uuid4())

    @staticmethod
    def url_encode(data: str) -> str:
        """URL编码"""
        return urllib.parse.quote(data)

    @staticmethod
    def url_decode(data: str) -> str:
        """URL解码"""
        return urllib.parse.unquote(data)

    @staticmethod
    def base64_encode(data: str) -> str:
        """Base64编码"""
        return base64.b64encode(data.encode("utf-8")).decode("utf-8")

    @staticmethod
    def base64_decode(data: str) -> str:
        """Base64解码"""
        return base64.b64decode(data.encode("utf-8")).decode("utf-8")

    # 添加测试期望的函数别名和方法
    @staticmethod
    def generate_short_id(length: int = 8) -> str:
        """生成短ID"""
        # 如果是奇数，使用token_hex并减半长度
        if length % 2 == 1:
            return secrets.token_hex(length // 2)
        # 否则使用token_urlsafe
        return secrets.token_urlsafe(length)[:length]

    @staticmethod
    def encode_base64(data: str) -> str:
        """Base64编码 - 别名方法"""
        try:
            if not data:
                return ""
            return base64.b64encode(data.encode("utf-8")).decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def decode_base64(data: str) -> str:
        """Base64解码 - 别名方法"""
        try:
            if not data:
                return ""
            return base64.b64decode(data.encode("utf-8")).decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def encode_url(data: str) -> str:
        """URL编码 - 别名方法"""
        try:
            if not data:
                return ""
            return urllib.parse.quote(data)
        except Exception:
            return ""

    @staticmethod
    def decode_url(data: str) -> str:
        """URL解码 - 别名方法"""
        try:
            if not data:
                return ""
            return urllib.parse.unquote(data)
        except Exception:
            return ""

    @staticmethod
    def hash_password_safe(password: str) -> str:
        """安全的密码哈希，处理长密码"""
        if len(password) > 72:
            password = password[:72]  # bcrypt限制
        return CryptoUtils.hash_password(password)

    @staticmethod
    def verify_password_safe(password: str, hashed: str) -> bool:
        """安全的密码验证，处理边界情况"""
        try:
            if not password or not hashed:
                return False
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False


# 全局实例
crypto_utils = CryptoUtils()

__all__ = [
    "CryptoUtils",
    "crypto_utils",
]
