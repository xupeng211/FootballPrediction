"""
足球预测系统字符串处理工具模块

提供字符串操作和文本处理相关的工具函数。
"""

import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


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
        # 简单实现，生产环境可能需要更复杂的处理
        text = re.sub(r"[^\w\s-]", "", text.lower())
        return re.sub(r"[-\s]+", "-", text).strip("-")

    @staticmethod
    def camel_to_snake(name: str) -> str:
        """驼峰命名转下划线命名"""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def snake_to_camel(name: str) -> str:
        """下划线命名转驼峰命名"""
        components = name.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本（移除多余空白等）"""
        # 移除多余的空白字符
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """从文本中提取数字"""
        pattern = r"-?\d+\.?\d*"
        numbers = re.findall(pattern, text)

        return [float(num) for num in numbers if num]
