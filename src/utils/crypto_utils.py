import base64
import hashlib
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
    """加密工具类."""

    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希."""
        if len(password) > 72:
            password = password[:72]  # bcrypt限制
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """验证密码."""
        try:
            if not password or not hashed:
                return False

            # 检查是否是bcrypt格式
            if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
                return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

            # 检查是否是sha256格式: sha256$salt$hash
            elif hashed.startswith("sha256$") and hashed.count("$") == 2:
                parts = hashed.split("$")
                if len(parts) == 3:
                    _, salt, expected_hash = parts
                    salted_password = f"{password}{salt}"
                    actual_hash = hashlib.sha256(
                        salted_password.encode("utf-8")
                    ).hexdigest()
                    return actual_hash == expected_hash

            # 默认使用bcrypt验证
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """生成随机令牌."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_uuid() -> str:
        """生成UUID."""
        return str(uuid.uuid4())

    @staticmethod
    def url_encode(data: str) -> str:
        """URL编码."""
        return urllib.parse.quote(data)

    @staticmethod
    def url_decode(data: str) -> str:
        """URL解码."""
        return urllib.parse.unquote(data)

    @staticmethod
    def base64_encode(data: str) -> str:
        """Base64编码."""
        return base64.b64encode(data.encode("utf-8")).decode("utf-8")

    @staticmethod
    def base64_decode(data: str) -> str:
        """Base64解码."""
        return base64.b64decode(data.encode("utf-8")).decode("utf-8")

    # 添加测试期望的函数别名和方法
    @staticmethod
    def generate_short_id(length: int = 8) -> str:
        """生成短ID - 始终返回十六进制格式."""
        try:
            # 确保返回十六进制格式，长度需要是偶数
            if length % 2 == 1:
                length += 1  # 调整为偶数
            return secrets.token_hex(length // 2)[:length]
        except Exception:
            return ""

    @staticmethod
    def encode_base64(data: str) -> str:
        """Base64编码 - 别名方法."""
        try:
            if not data:
                return ""
            return base64.b64encode(data.encode("utf-8")).decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def decode_base64(data: str) -> str:
        """Base64解码 - 别名方法."""
        try:
            if not data:
                return ""
            return base64.b64decode(data.encode("utf-8")).decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def create_checksum(data) -> str:
        """创建校验和."""
        import hashlib

        try:
            # 只接受字符串类型，其他类型返回空字符串
            if not isinstance(data, str):
                return ""
            # 空字符串也要产生哈希值
            return hashlib.sha256(data.encode("utf-8")).hexdigest()
        except Exception:
            return ""

    @staticmethod
    def generate_random_string(length: int = 32) -> str:
        """生成随机字符串."""
        try:
            return secrets.token_urlsafe(length)[:length]
        except Exception:
            return ""

    @staticmethod
    def generate_api_key(prefix: str = "fp") -> str:
        """生成API密钥."""
        try:
            random_part = secrets.token_urlsafe(24)
            return f"{prefix}_{random_part}"
        except Exception:
            return f"{prefix}_default"

    @staticmethod
    def encode_url(data: str) -> str:
        """URL编码 - 别名方法."""
        try:
            if not data:
                return ""
            return urllib.parse.quote(data)
        except Exception:
            return ""

    @staticmethod
    def decode_url(data: str) -> str:
        """URL解码 - 别名方法."""
        try:
            if not data:
                return ""
            return urllib.parse.unquote(data)
        except Exception:
            return ""

    @staticmethod
    def hash_password_safe(password: str) -> str:
        """安全的密码哈希，处理长密码."""
        if len(password) > 72:
            password = password[:72]  # bcrypt限制
        return CryptoUtils.hash_password(password)

    @staticmethod
    def verify_password_safe(password: str, hashed: str) -> bool:
        """安全的密码验证，处理边界情况."""
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
