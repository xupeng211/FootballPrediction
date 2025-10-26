"""
Data validators
"""

import re
from typing import Any, Dict, List

def is_valid_email(email: str) -> bool:
    """Validate email address"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def is_valid_phone(phone: str) -> bool:
    """Validate phone number"""
    pattern = r"^\+?[\d\s-()]+$"
    return bool(re.match(pattern, phone))

def is_valid_url(url: str) -> bool:
    """Validate URL"""
    pattern = r"^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$"
    return bool(re.match(pattern, url))

def validate_required_fields(
    data: Dict[str, Any], required_fields: List[str]
) -> List[str]:
    """Check if all required fields are present"""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    return missing_fields

def validate_data_types(data: Dict[str, Any], schema: Dict[str, type]) -> List[str]:
    """Validate data types against schema"""
    errors = []
    for field, expected_type in schema.items():
        if field in data and not isinstance(data[field], expected_type):
            errors.append(
                f"Field '{field}' should be {expected_type.__name__}, got {type(data[field]).__name__}"
            )
    return errors
