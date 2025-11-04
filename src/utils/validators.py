"""
Data validators
"""

import re
from typing import Any


def is_valid_email(email: str) -> bool:
    """Validate email address"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_valid_phone(phone: str) -> bool:
    """Validate phone number"""
    # 支持多种电话号码格式，但要求至少10位数字
    pattern = r"^\+?[\d\s\-\(\).]+$"
    if not re.match(pattern, phone):
        return False

    # 提取数字并检查长度
    digits_only = re.sub(r"[^\d]", "", phone)
    return len(digits_only) >= 10


def is_valid_url(url: str) -> bool:
    """Validate URL"""
    pattern = r"^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$"
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
