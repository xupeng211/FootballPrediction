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
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

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


# 全局实例
crypto_utils = CryptoUtils()

__all__ = [
    "CryptoUtils",
    "crypto_utils",
]
