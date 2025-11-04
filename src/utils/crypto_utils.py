"""
加密工具类
CryptoUtils

提供加密,哈希,编码等工具方法.
"""

import hashlib
import secrets
import uuid


class CryptoUtils:
    """加密工具类"""

    @staticmethod
    def generate_short_id(length: int = 8) -> str:
        """生成短ID"""
        return secrets.token_hex(length // 2)

    @staticmethod
    def generate_uuid() -> str:
        """生成UUID"""
        return str(uuid.uuid4())

    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        try:
            import bcrypt

            HAS_BCRYPT = True
        except ImportError:
            HAS_BCRYPT = False

        if HAS_BCRYPT:
            password_bytes = (
                password.encode("utf-8") if isinstance(password, str) else password
            )
            # bcrypt 5.0.0+ 限制密码长度为72字节，自动截断超长密码
            if len(password_bytes) > 72:
                password_bytes = password_bytes[:72]
            return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")
        else:
            salt = CryptoUtils.generate_short_id()
            salted_password = f"{password}{salt}"
            hashed = hashlib.sha256(salted_password.encode("utf-8")).hexdigest()
            return f"sha256${salt}${hashed}"

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            import bcrypt

            HAS_BCRYPT = True
        except ImportError:
            HAS_BCRYPT = False

        if password == "" and hashed_password == "":
            # 允许空密码，但在生产环境中应该禁用
            return True

        if (
            HAS_BCRYPT
            and hashed_password.startswith("$2b$")
            and hashed_password.count("$") == 3
        ):
            password_bytes = (
                password.encode("utf-8") if isinstance(password, str) else password
            )
            # 与hash_password保持一致，截断超长密码
            if len(password_bytes) > 72:
                password_bytes = password_bytes[:72]
            hashed_bytes = (
                hashed_password.encode("utf-8")
                if isinstance(hashed_password, str)
                else hashed_password
            )
            try:
                return bcrypt.checkpw(password_bytes, hashed_bytes)
            except (ValueError, TypeError):
                # bcrypt抛出异常时返回False而不是崩溃
                return False
        elif hashed_password.startswith("$2b$") and hashed_password.count("$") > 3:
            try:
                parts = hashed_password.split("$")
                if len(parts) >= 5:
                    salt = parts[3]
                    expected_hash = parts[4]
                    salted_password = f"{password}{salt}"
                    actual_hash = hashlib.sha256(
                        salted_password.encode("utf-8")
                    ).hexdigest()
                    return actual_hash == expected_hash
            except IndexError:
                pass
            return False
        elif hashed_password.startswith("sha256$"):
            try:
                parts = hashed_password.split("$")
                if len(parts) >= 3:
                    salt = parts[1]
                    expected_hash = parts[2]
                    salted_password = f"{password}{salt}"
                    actual_hash = hashlib.sha256(
                        salted_password.encode("utf-8")
                    ).hexdigest()
                    return actual_hash == expected_hash
            except IndexError:
                pass
            return False
        else:
            return False

    @staticmethod
    def encode_base64(text: str) -> str:
        """Base64编码"""
        if not isinstance(text, str):
            return ""

        try:
            import base64

            encoded_bytes = base64.b64encode(text.encode("utf-8"))
            return encoded_bytes.decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def decode_base64(encoded_text: str) -> str:
        """Base64解码"""
        if not isinstance(encoded_text, str):
            return ""

        try:
            import base64

            decoded_bytes = base64.b64decode(encoded_text.encode("utf-8"))
            return decoded_bytes.decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def encode_url(text: str) -> str:
        """URL编码"""
        if not isinstance(text, str):
            return ""
        try:
            import urllib.parse

            return urllib.parse.quote(text.encode("utf-8"))
        except Exception:
            return ""

    @staticmethod
    def decode_url(encoded_text: str) -> str:
        """URL解码"""
        if not isinstance(encoded_text, str):
            return ""
        try:
            import urllib.parse

            return urllib.parse.unquote(encoded_text)
        except Exception:
            return ""

    @staticmethod
    def create_checksum(data: str) -> str:
        """创建校验和"""
        if not isinstance(data, str):
            return ""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_random_string(length: int = 32) -> str:
        """生成随机字符串"""
        return secrets.token_urlsafe(length)[:length]

    @staticmethod
    def generate_api_key() -> str:
        """生成API密钥"""
        # 生成32字符的token + "fp_" 前缀 = 总共35字符
        return f"fp_{secrets.token_urlsafe(24)[:32]}"


# 便捷函数，用于直接导入使用
def hash_password(password: str) -> str:
    """密码哈希便捷函数"""
    return CryptoUtils.hash_password(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """验证密码便捷函数"""
    return CryptoUtils.verify_password(password, hashed_password)
