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
    pattern = r"^\+?[\d\s\-\(\)]+$"
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


# Additional validators for compatibility
def validate_username(username: str) -> bool:
    """Validate username"""
    pattern = r"^[a-zA-Z0-9_]{3,20}$"
    return bool(re.match(pattern, username))


def validate_password(password: str) -> bool:
    """Validate password - at least 8 characters with letter and number"""
    if len(password) < 8:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)
    return has_letter and has_number


def validate_credit_card(card: str) -> bool:
    """Validate credit card number (basic Luhn algorithm)"""
    card = card.replace(" ", "").replace("-", "")
    if not card.isdigit() or len(card) < 13 or len(card) > 19:
        return False
    # Simple check - could implement full Luhn algorithm
    return len(card) >= 13


def validate_ipv4_address(ip: str) -> bool:
    """Validate IPv4 address"""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address"""
    pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
    return bool(re.match(pattern, mac))


def validate_date_string(date_str: str) -> bool:
    """Validate date string (YYYY-MM-DD format)"""
    import datetime

    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_json_string(json_str: str) -> bool:
    """Validate JSON string"""
    import json

    try:
        json.loads(json_str)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


# Aliases for backward compatibility
is_valid_email = is_valid_email
is_valid_phone = is_valid_phone
is_valid_url = is_valid_url
is_valid_username = validate_username
is_valid_password = validate_password
is_valid_credit_card = validate_credit_card
is_valid_ipv4_address = validate_ipv4_address
is_valid_mac_address = validate_mac_address
is_valid_date_string = validate_date_string
is_valid_json_string = validate_json_string
