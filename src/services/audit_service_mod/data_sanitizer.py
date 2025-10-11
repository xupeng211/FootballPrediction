"""
Data Sanitization and Sensitive Data Handling

提供敏感数据清理、哈希和隐私保护功能。
Provides sensitive data sanitization, hashing and privacy protection.
"""

import hashlib
import json
from typing import Any, Dict, Optional

from src.core.logging import get_logger


class DataSanitizer:
    """
    数据清理器

    负责识别和清理敏感数据，确保隐私保护。
    """

    def __init__(self):
        """初始化数据清理器"""
        self.logger = get_logger(__name__)

        # 敏感数据配置
        self.sensitive_tables = {
            "users",
            "permissions",
            "tokens",
            "passwords",
            "api_keys",
            "user_profiles",
            "payment_info",
            "personal_data",
        }

        self.sensitive_columns = {
            "password",
            "token",
            "secret",
            "key",
            "credential",
            "ssn",
            "credit_card",
            "bank_account",
        }


def _hash_sensitive_value(self, value: str) -> str:
    """
    哈希敏感值 / Hash Sensitive Value

    Args:
        value: 敏感值 / Sensitive value

    Returns:
        哈希值 / Hashed value
    """
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _hash_sensitive_data(self, data: str) -> str:
    """
    哈希敏感数据 / Hash Sensitive Data

    Args:
        data: 敏感数据 / Sensitive data

    Returns:
        哈希后的数据 / Hashed data
    """
    try:
        # 尝试解析为JSON
        import json

        parsed_data = json.loads(data)
        # 递归处理嵌套结构
        return self._sanitize_data(parsed_data)  # type: ignore
    except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
        # 如果不是JSON，直接哈希
        return self._hash_sensitive_value(data)


def _sanitize_data(self, data: Any) -> Any:
    """
    清理敏感数据 / Sanitize Sensitive Data

    Args:
        data: 数据 / Data

    Returns:
        清理后的数据 / Sanitized data
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key in self.sensitive_columns:
                sanitized[key] = self._hash_sensitive_value(str(value))
            elif isinstance(value, (dict, list)):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, list):
        return [self._sanitize_data(item) for item in data]
    else:
        return data


def _is_sensitive_table(self, table_name: Any) -> bool:
    """
    检查是否为敏感表 / Check if Sensitive Table

    Args:
        table_name: 表名 / Table name

    Returns:
        是否敏感 / Whether sensitive
    """
    return table_name in self.sensitive_tables


def _contains_pii(self, data: Dict[str, Any]) -> bool:
    """
    检查是否包含个人身份信息 / Check if Contains PII

    Args:
        data: 数据字典 / Data dictionary

    Returns:
        是否包含PII / Whether contains PII
    """
    pii_indicators = [
        "ssn",
        "social_security",
        "credit_card",
        "bank_account",
        "email",
        "phone",
        "address",
        "id_number",
        "passport",
        "license",
        "personal",
    ]

    for key in data.keys():
        key_lower = key.lower()
        if any(indicator in key_lower for indicator in pii_indicators):
            return True

    return False


def _is_sensitive_data(
    self,
    data: Any,
    table_name: Optional[str] = None,
    action: Optional[str] = None,
) -> bool:
    """
    检查是否为敏感数据 / Check if Sensitive Data

    Args:
        data: 数据 / Data
        table_name: 表名 / Table name
        action: 动作 / Action

    Returns:
        是否敏感 / Whether sensitive
    """
    # 检查表名
    if table_name and self._is_sensitive_table(table_name):
        return True

    # 检查动作
    sensitive_actions = [
        "delete",
        "update_password",
        "reset_password",
        "change_role",
    ]
    if action and action in sensitive_actions:
        return True

    # 检查数据内容
    if isinstance(data, dict) and self._contains_pii(data):
        return True

    return False
