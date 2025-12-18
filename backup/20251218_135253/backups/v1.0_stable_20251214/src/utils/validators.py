"""Data validators."""

import re
from typing import Any


def is_valid_email(email: str) -> bool:
    """Validate email address."""
    if not isinstance(email, str) or not email:
        return False

    # 基本长度检查
    if len(email) > 254:  # RFC 5321限制
        return False

    # 改进的邮箱验证正则表达式
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False

    # 额外检查：不允许连续的点号
    if ".." in email:
        return False

    # 额外检查：域名不能以点号开始或结束
    domain = email.split("@")[1]
    if domain.startswith(".") or domain.endswith("."):
        return False

    # 额外检查：域名不能以连字符开始或结束
    if domain.startswith("-") or domain.endswith("-"):
        return False

    return True


def is_valid_phone(phone: str) -> bool:
    """Validate phone number."""
    # 检查输入类型
    if not isinstance(phone, str) or not phone:
        return False

    # 支持多种电话号码格式，但要求至少10位数字
    pattern = r"^\+?[\d\s\-\(\).]+$"
    if not re.match(pattern, phone):
        return False

    # 提取数字并检查长度
    digits_only = re.sub(r"[^\d]", "", phone)
    return len(digits_only) >= 10


def is_valid_url(url: str) -> bool:
    """Validate URL."""
    # 检查输入类型
    if not isinstance(url, str) or not url:
        return False

    # 基本URL格式验证
    pattern = r"^https?://(?:[-\w.][-\w.]*)+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$"
    if not re.match(pattern, url):
        return False

    # 额外检查：确保域名不是以点号开始或只包含点号
    # 提取域名部分进行检查
    try:
        # 移除协议部分
        domain_part = url.replace("http://", "").replace("https://", "")
        # 移除路径部分
        domain_part = domain_part.split("/", 1)[0]
        # 移除端口部分
        domain_part = domain_part.split(":", 1)[0]

        # 域名不能以点号开始或结束
        if domain_part.startswith(".") or domain_part.endswith("."):
            return False

        # 域名不能连续出现点号
        if ".." in domain_part:
            return False

        # 域名必须包含至少一个字母或数字
        if not re.search(r"[a-zA-Z0-9]", domain_part):
            return False

    except Exception as e:
        return False

    return True


def validate_required_fields(
    data: dict[str, Any], required_fields: list[str]
) -> list[str]:
    """Check if all required fields are present."""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    return missing_fields


def validate_data_types(data: dict, schema: dict) -> list[str]:
    """验证数据类型."""
    errors = []
    for field, expected_type in schema.items():
        if field in data:
            value = data[field]
            if expected_type == "str" and not isinstance(value, str):
                errors.append(f"Field '{field}' should be string")
            elif expected_type == "int" and not isinstance(value, int):
                errors.append(f"Field '{field}' should be integer")
            elif expected_type == "float" and not isinstance(value, int | float):
                errors.append(f"Field '{field}' should be number")
            elif expected_type == "bool" and not isinstance(value, bool):
                errors.append(f"Field '{field}' should be boolean")
            elif expected_type == "list" and not isinstance(value, list):
                errors.append(f"Field '{field}' should be list")
    return errors
