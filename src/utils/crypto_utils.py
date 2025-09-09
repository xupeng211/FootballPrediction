"""
足球预测系统加密工具模块

提供加密、哈希和ID生成相关的工具函数。
"""

import hashlib
import uuid
from typing import Optional


class CryptoUtils:
    """加密工具类"""

    @staticmethod
    def generate_uuid() -> str:
        """生成UUID"""
        return str(uuid.uuid4())

    @staticmethod
    def generate_short_id(length: int = 8) -> str:
        """生成短ID"""
        return str(uuid.uuid4()).replace("-", "")[:length]

    @staticmethod
    def hash_string(text: str, algorithm: str = "md5") -> str:
        """字符串哈希"""
        if algorithm == "md5":
            return hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
        elif algorithm == "sha256":
            return hashlib.sha256(text.encode("utf-8")).hexdigest()
        else:
            raise ValueError(f"不支持的哈希算法: {algorithm}")

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> str:
        """密码哈希（简单实现，生产环境建议使用bcrypt）"""
        if salt is None:
            salt = CryptoUtils.generate_short_id()

        salted_password = f"{password}{salt}"
        return hashlib.sha256(salted_password.encode("utf-8")).hexdigest()
