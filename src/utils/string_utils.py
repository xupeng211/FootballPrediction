"""
足球预测系统字符串处理工具模块 - Phase 4B增强版

提供字符串操作和文本处理相关的工具函数：
- 字符串清理和格式化
- 邮箱和URL验证
- 文本截断和省略
- Slug生成和URL友好化
- 命名风格转换
- 数字提取和处理
"""

import re
import unicodedata
from functools import lru_cache
from typing import List


class StringUtils:
    """字符串处理工具类"""

    # 编译正则表达式以提高性能
    _EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    _PHONE_REGEX = re.compile(r"^1[3-9]\d{9}$")

    @staticmethod
    def clean_string(text: str, remove_special_chars: bool = False) -> str:
        """清理字符串"""
        if not isinstance(text, str):
            return ""

        # 基本清理
        cleaned = text.strip()

        # 移除Unicode控制字符
        cleaned = "".join(char for char in cleaned if unicodedata.category(char)[0] != "C")

        if remove_special_chars:
            # 移除特殊字符，保留字母数字和基本标点
            cleaned = re.sub(r'[^\w\s\-.,!?()[\]{}"\'`~@#$%^&*+=<>|\\]', "", cleaned)

        # 规范化空白字符
        cleaned = " ".join(cleaned.split())
        return cleaned

    @staticmethod
    def truncate(text: str, length: int, suffix: str = "...") -> str:
        """截断字符串"""
        if not isinstance(text, str):
            return ""

        # 处理负长度情况
        if length < 0:
            # 负长度：从开头截取到 len(suffix) + length - 1
            effective_length = len(suffix) + length - 1
            if effective_length <= 0:
                return suffix
            return text[:effective_length] + suffix

        # 处理零长度
        if length == 0:
            return suffix

        if len(text) <= length:
            return text

        # 确保长度至少能容纳后缀
        if length <= len(suffix):
            return suffix

        return text[: length - len(suffix)] + suffix

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        if not isinstance(email, str):
            return False

        email = email.strip().lower()

        # 基本长度检查
        if len(email) > 254:  # RFC 5321限制
            return False

        # 使用正则表达式验证
        return bool(StringUtils._EMAIL_REGEX.match(email))

    @staticmethod
    def slugify(text: str) -> str:
        """转换为URL友好的字符串"""
        if not isinstance(text, str):
            return ""

        # 规范化Unicode
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")

        # 转换为小写，替换空格为连字符
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text).strip("-")
        return text

    @staticmethod
    def camel_to_snake(name: str) -> str:
        """驼峰命名转下划线命名"""
        if not isinstance(name, str):
            return ""

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def snake_to_camel(name: str) -> str:
        """下划线命名转驼峰命名"""
        if not isinstance(name, str):
            return ""

        components = name.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本（移除多余空白等）"""
        if not isinstance(text, str):
            return ""

        # 移除多余的空白字符
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    @lru_cache(maxsize=1000)
    def validate_phone_number(phone: str) -> bool:
        """验证中国手机号格式"""
        if not isinstance(phone, str):
            return False

        # 移除非数字字符
        digits_only = re.sub(r"[^\d]", "", phone)

        # 验证11位手机号
        return bool(StringUtils._PHONE_REGEX.match(digits_only))

    @staticmethod
    def sanitize_phone_number(phone: str) -> str:
        """清理电话号码"""
        if not isinstance(phone, str):
            return ""

        # 移除非数字字符
        digits_only = re.sub(r"[^\d]", "", phone)

        # 中国手机号格式验证
        if len(digits_only) == 11 and digits_only.startswith("1"):
            return digits_only

        return ""

    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """从文本中提取数字"""
        if not isinstance(text, str):
            return []

        pattern = r"-?\d+\.?\d*"
        numbers = re.findall(pattern, text)
        return [float(num) for num in numbers if num]

    @staticmethod
    def mask_sensitive_data(text: str, mask_char: str = "*", visible_chars: int = 4) -> str:
        """遮蔽敏感数据"""
        if not isinstance(text, str) or len(text) <= visible_chars:
            return text

        visible = text[:visible_chars] if len(text) > visible_chars else text
        masked_length = len(text) - visible_chars
        return visible + mask_char * masked_length

    @staticmethod
    def generate_slug(text: str) -> str:
        """生成URL友好的slug（与slugify功能相同）"""
        return StringUtils.slugify(text)

    @staticmethod
    def format_bytes(bytes_count: float, precision: int = 2) -> str:
        """格式化字节数为人类可读格式"""
        if bytes_count == 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        unit_index = 0

        while bytes_count >= 1024 and unit_index < len(units) - 1:
            bytes_count /= 1024.0
            unit_index += 1

        return f"{bytes_count:.{precision}f} {units[unit_index]}"

    @staticmethod
    def count_words(text: str) -> int:
        """计算文本中的单词数"""
        if not isinstance(text, str):
            return 0

        # 简单的单词计数（基于空白字符分割）
        words = text.strip().split()
        return len(words)

    @staticmethod
    def escape_html(text: str) -> str:
        """HTML转义"""
        if not isinstance(text, str):
            return ""

        html_escape_map = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
            "/": "&#x2F;",
        }

        return "".join(html_escape_map.get(char, char) for char in text)

    @staticmethod
    def unescape_html(text: str) -> str:
        """HTML反转义"""
        if not isinstance(text, str):
            return ""

        html_unescape_map = {
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&#x27;": "'",
            "&#x2F;": "/",
        }

        for html_char, char in html_unescape_map.items():
            text = text.replace(html_char, char)

        return text

    @staticmethod
    def is_url(text: str) -> bool:
        """检查字符串是否为URL"""
        if not isinstance(text, str):
            return False

        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        return url_pattern.match(text.strip()) is not None

    @staticmethod
    def reverse_string(text: str) -> str:
        """反转字符串"""
        if not isinstance(text, str):
            return ""
        return text[::-1]

    @staticmethod
    def is_palindrome(text: str) -> bool:
        """检查是否为回文"""
        if not isinstance(text, str):
            return False
        # 移除非字母数字字符并转为小写
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", text).lower()
        return cleaned == cleaned[::-1]

    @staticmethod
    def capitalize_words(text: str) -> str:
        """首字母大写每个单词"""
        if not isinstance(text, str):
            return ""
        return " ".join(word.capitalize() for word in text.split())

    @staticmethod
    def random_string(
        length: int = 10,
        chars: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    ) -> str:
        """生成随机字符串"""
        import random

        if length <= 0:
            return ""
        return "".join(random.choice(chars) for _ in range(length))

    @staticmethod
    def remove_duplicates(text: str) -> str:
        """移除重复的字符"""
        if not isinstance(text, str):
            return ""
        seen = set()
        return "".join(char for char in text if not (char in seen or seen.add(char)))

    @staticmethod
    def word_count(text: str) -> int:
        """计算单词数"""
        if not isinstance(text, str):
            return 0
        return len(text.split())

    @staticmethod
    def char_frequency(text: str) -> dict:
        """计算字符频率"""
        if not isinstance(text, str):
            return {}
        frequency = {}
        for char in text:
            frequency[char] = frequency.get(char, 0) + 1
        return frequency


# 性能优化的字符串处理函数
@lru_cache(maxsize=256)
def cached_slug(text: str) -> str:
    """缓存的slug生成函数"""
    return StringUtils.slugify(text)


def batch_clean_strings(strings: List[str], **kwargs) -> List[str]:
    """批量清理字符串"""
    return [StringUtils.clean_string(s, **kwargs) for s in strings]


def validate_batch_emails(emails: List[str]) -> dict:
    """批量验证邮箱"""
    return {email: StringUtils.validate_email(email) for email in emails}
