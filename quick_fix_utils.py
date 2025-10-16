#!/usr/bin/env python3
"""
快速修复utils模块的语法错误
"""

import os
from pathlib import Path

def main():
    """修复关键文件"""
    files_to_fix = [
        "src/utils/string_utils.py",
        "src/utils/file_utils.py",
        "src/utils/time_utils.py",
        "src/utils/crypto_utils.py",
        "src/utils/dict_utils.py",
        "src/utils/data_validator.py",
        "src/utils/validators.py",
        "src/utils/redis_cache.py",
        "src/utils/warning_filters.py",
        "src/utils/__init__.py",
    ]

    # 创建正确的内容
    correct_content = {
        "src/utils/__init__.py": '''"""
足球预测系统工具模块

提供系统中使用的工具函数和辅助类, 包括:
- 文件处理工具
- 数据验证工具
- 时间处理工具
- 加密工具
- 字符串处理工具
- 字典处理工具
"""
from .crypto_utils import CryptoUtils
from .data_validator import DataValidator
from .dict_utils import DictUtils
from .file_utils import FileUtils
from .string_utils import StringUtils
from .time_utils import TimeUtils


__all__ = [
    "FileUtils",
    "DataValidator",
    "TimeUtils",
    "CryptoUtils",
    "StringUtils",
    "DictUtils",
]
''',
        "src/utils/string_utils.py": '''"""
足球预测系统字符串处理工具模块

提供字符串操作和文本处理相关的工具函数。
"""
import re


class StringUtils:
    """字符串处理工具类"""

    @staticmethod
    def truncate(text: str, length: int, suffix: str = "...") -> str:
        """截断字符串"""
        if len(text) <= length:
            return text
        return text[: length - len(suffix)] + suffix

    @staticmethod
    def slugify(text: str) -> str:
        """转换为URL友好的字符串"""
        # 简单实现, 生产环境可能需要更复杂的处理
        text = re.sub(r"[^\\w\\s-]", "", text.lower())
        return re.sub(r"[-\\s]+", "-", text).strip("-")

    @staticmethod
    def camel_to_snake(name: str) -> str:
        """驼峰命名转下划线命名"""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\\1_\\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\\1_\\2", s1).lower()

    @staticmethod
    def snake_to_camel(name: str) -> str:
        """下划线命名转驼峰命名"""
        components = name.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本（移除多余空白等）"""
        # 移除多余的空白字符
        text = re.sub(r"\\s+", " ", text)
        return text.strip()

    @staticmethod
    def extract_numbers(text: str) -> list[float]:
        """从文本中提取数字"""
        pattern = r"-?\\d+\\.?\\d*"
        numbers = re.findall(pattern, text)
        return [float(num) for num in numbers if num]

    @staticmethod
    def is_empty(text: str) -> bool:
        """检查字符串是否为空或只包含空白"""
        return not text.strip()

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """标准化空白字符"""
        return " ".join(text.split())

    @staticmethod
    def remove_special_chars(text: str, keep_chars: str = "") -> str:
        """移除特殊字符"""
        pattern = f"[^\\w\\s{re.escape(keep_chars)}]"
        return re.sub(pattern, "", text)
''',
        "src/utils/validators.py": '''from typing import Any
import re


def is_valid_email(email: str) -> bool:
    """Validate email address"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_valid_phone(phone: str) -> bool:
    """Validate phone number"""
    pattern = r"^\\+?[\\d\\s-()]+$"
    return bool(re.match(pattern, phone))


def is_valid_url(url: str) -> bool:
    """Validate URL"""
    pattern = r"^https?://(?:[-\\w.])+(?:\\:[0-9]+)?(?:/(?:[\\w/_.])*(?:\\?(?:[\\w&=%.])*)?(?:\\#(?:[\\w.])*)?)?$"
    return bool(re.match(pattern, url))


def validate_required_fields(
    data: dict[str, Any], required_fields: list[str]
) -> list[str]:
    """Check if all required fields are present"""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    return missing_fields


def validate_data_types(data: dict[str, Any], schema: dict[str, type]) -> list[str]:
    """Validate data types against schema"""
    errors = []
    for field, expected_type in schema.items():
        if field in data and not isinstance(data[field], expected_type):
            errors.append(
                f"Field '{field}' should be {expected_type.__name__}, got {type(data[field]).__name__}"
            )
    return errors
'''
    }

    # 写入修复后的文件
    for file_path, content in correct_content.items():
        print(f"修复 {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    print("\n修复完成！")

if __name__ == "__main__":
    main()