"""
Helper functions
"""

import hashlib
import uuid
from datetime import datetime
from typing import Any, Dict, Optional


def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())


def generate_hash(data: str, algorithm: str = "sha256") -> str:
    """Generate hash with specified algorithm"""
    if algorithm == "md5":
        return hashlib.md5(data.encode()).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(data.encode()).hexdigest()
    else:
        return hashlib.sha256(data.encode()).hexdigest()


def safe_get(data: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    """Safely get value from dict using dot notation"""
    if data is None:
        return default

    # 支持点号分隔的嵌套键
    keys = key.split(".")
    current = data

    try:
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            elif isinstance(current, list) and k.isdigit():
                index = int(k)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return default
            else:
                return default
        return current
    except (KeyError, TypeError, IndexError):
        return default


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format timestamp to ISO format"""
    if dt is None:
        dt = datetime.utcnow()
    return dt.isoformat()


def sanitize_string(s: str) -> str:
    """Sanitize string input - basic XSS protection"""
    if not s:
        return ""

    # 移除常见的XSS攻击向量
    dangerous_patterns = [
        "<script>",
        "</script>",
        "javascript:",
        "onload=",
        "onerror="
    ]

    sanitized = s
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern, "")

    return sanitized.strip()
