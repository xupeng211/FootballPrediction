"""
数据清理器
Data Sanitizer

处理敏感数据的清理和掩码功能。
"""

import hashlib
import re
from typing import Any, Dict, List, Optional, Union

from src.core.logging import get_logger

logger = get_logger(__name__)


class DataSanitizer:
    """
    数据清理器 / Data Sanitizer

    负责敏感数据的检测、掩码和哈希处理。
    Responsible for detecting, masking, and hashing sensitive data.
    """

    def __init__(self):
        """初始化数据清理器 / Initialize Data Sanitizer"""
        self.logger = get_logger(f"audit.{self.__class__.__name__}")

        # 敏感表配置
        self.sensitive_tables = {
            "users",
            "permissions",
            "tokens",
            "passwords",
            "api_keys",
            "user_profiles",
            "payment_info",
            "personal_data",
            "financial_data",
            "health_records",
            "contact_information",
        }

        # 敏感列配置
        self.sensitive_columns = {
            "password",
            "token",
            "secret",
            "key",
            "credential",
            "ssn",
            "social_security_number",
            "credit_card",
            "credit_card_number",
            "bank_account",
            "account_number",
            "pin",
            "cvv",
            "security_code",
            "passport",
            "passport_number",
            "license",
            "driver_license",
            "medical_record",
            "health_info",
        }

        # 敏感数据模式
        self.sensitive_patterns = [
            # 信用卡号
            r"\b(?:\d[ -]*?){13,16}\b",
            # 社会安全号码
            r"\b\d{3}-?\d{2}-?\d{4}\b",
            # 邮箱地址
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            # 电话号码
            r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
            # IP地址
            r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
            # API密钥
            r"\b[A-Za-z0-9]{32,}\b",
        ]

        # 合规类别映射
        self.compliance_mapping = {
            "users": "user_management",
            "permissions": "access_control",
            "tokens": "authentication",
            "payment": "financial",
            "financial_data": "financial",
            "personal_data": "privacy",
            "health_records": "healthcare",
            "contact_information": "privacy",
        }

        # PII指示器
        self.pii_indicators = [
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
            "private",
            "confidential",
            "secret",
            "sensitive",
        ]

    def is_sensitive_table(self, table_name: str) -> bool:
        """
        检查是否为敏感表 / Check if Sensitive Table

        Args:
            table_name: 表名 / Table name

        Returns:
            bool: 是否敏感 / Whether sensitive
        """
        if not table_name:
            return False
        return table_name.lower() in self.sensitive_tables

    def is_sensitive_column(self, column_name: str) -> bool:
        """
        检查是否为敏感列 / Check if Sensitive Column

        Args:
            column_name: 列名 / Column name

        Returns:
            bool: 是否敏感 / Whether sensitive
        """
        if not column_name:
            return False

        column_lower = column_name.lower()
        return column_lower in self.sensitive_columns

    def contains_pii(self, data: Dict[str, Any]) -> bool:
        """
        检查是否包含个人身份信息 / Check if Contains PII

        Args:
            data: 数据字典 / Data dictionary

        Returns:
            bool: 是否包含PII / Whether contains PII
        """
        if not isinstance(data, dict):
            return False

        # 检查键名
        for key in data.keys():
            key_lower = key.lower()
            if any(indicator in key_lower for indicator in self.pii_indicators):
                return True

        # 检查值的模式
        for value in data.values():
            if isinstance(value, str) and self._contains_sensitive_pattern(value):
                return True

        return False

    def _contains_sensitive_pattern(self, text: str) -> bool:
        """
        检查文本是否包含敏感模式 / Check if Text Contains Sensitive Pattern

        Args:
            text: 文本 / Text

        Returns:
            bool: 是否包含敏感模式 / Whether contains sensitive pattern
        """
        for pattern in self.sensitive_patterns:
            if re.search(pattern, text):
                return True
        return False

    def is_sensitive_data(
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
            bool: 是否敏感 / Whether sensitive
        """
        # 检查表名
        if table_name and self.is_sensitive_table(table_name):
            return True

        # 检查动作
        sensitive_actions = [
            "delete",
            "update_password",
            "reset_password",
            "change_role",
            "export",
        ]
        if action and action.lower() in sensitive_actions:
            return True

        # 检查数据内容
        if isinstance(data, dict) and self.contains_pii(data):
            return True

        return False

    def hash_sensitive_value(self, value: str) -> str:
        """
        哈希敏感值 / Hash Sensitive Value

        Args:
            value: 敏感值 / Sensitive value

        Returns:
            str: 哈希值 / Hashed value
        """
        if not value:
            return value

        try:
            return hashlib.sha256(value.encode()).hexdigest()[:16]
        except Exception as e:
            self.logger.error(f"哈希敏感值失败: {e}")
            return "***HASHED***"

    def mask_sensitive_value(
        self, value: str, mask_char: str = "*", show_chars: int = 4
    ) -> str:
        """
        掩码敏感值 / Mask Sensitive Value

        Args:
            value: 敏感值 / Sensitive value
            mask_char: 掩码字符 / Mask character
            show_chars: 显示字符数 / Number of characters to show

        Returns:
            str: 掩码值 / Masked value
        """
        if not value or len(value) <= show_chars:
            return mask_char * len(value) if value else value

        try:
            return value[:show_chars] + mask_char * (len(value) - show_chars)
        except Exception as e:
            self.logger.error(f"掩码敏感值失败: {e}")
            return mask_char * 8

    def sanitize_value(self, value: Any, method: str = "hash") -> Any:
        """
        清理单个值 / Sanitize Single Value

        Args:
            value: 值 / Value
            method: 清理方法 / Sanitization method

        Returns:
            Any: 清理后的值 / Sanitized value
        """
        if not isinstance(value, str):
            return value

        if method == "hash":
            return self.hash_sensitive_value(value)
        elif method == "mask":
            return self.mask_sensitive_value(value)
        elif method == "remove":
            return "***REMOVED***"
        else:
            return "***SANITIZED***"

    def hash_sensitive_data(self, data: str) -> str:
        """
        哈希敏感数据 / Hash Sensitive Data

        Args:
            data: 敏感数据 / Sensitive data

        Returns:
            str: 哈希后的数据 / Hashed data
        """
        try:
            # 尝试解析为JSON
            import json

            parsed_data = json.loads(data)
            # 递归处理嵌套结构
            return self.sanitize_data(parsed_data)
        except Exception:
            # 如果不是JSON，直接哈希
            return self.hash_sensitive_value(data)

    def sanitize_data(self, data: Any, method: str = "hash") -> Any:
        """
        清理敏感数据 / Sanitize Sensitive Data

        Args:
            data: 数据 / Data
            method: 清理方法 / Sanitization method

        Returns:
            Any: 清理后的数据 / Sanitized data
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if self.is_sensitive_column(key):
                    sanitized[key] = self.sanitize_value(value, method)
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self.sanitize_data(value, method)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_data(item, method) for item in data]
        elif isinstance(data, str) and self._contains_sensitive_pattern(data):
            return self.sanitize_value(data, method)
        else:
            return data

    def detect_sensitive_fields(self, data: Dict[str, Any]) -> List[str]:
        """
        检测敏感字段 / Detect Sensitive Fields

        Args:
            data: 数据字典 / Data dictionary

        Returns:
            List[str]: 敏感字段列表 / List of sensitive fields
        """
        sensitive_fields = []

        if not isinstance(data, dict):
            return sensitive_fields

        for key, value in data.items():
            if self.is_sensitive_column(key):
                sensitive_fields.append(key)
            elif isinstance(value, str) and self._contains_sensitive_pattern(value):
                sensitive_fields.append(key)

        return sensitive_fields

    def redact_data(
        self, data: Dict[str, Any], fields_to_redact: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        删除数据 / Redact Data

        Args:
            data: 数据字典 / Data dictionary
            fields_to_redact: 要删除的字段列表 / List of fields to redact

        Returns:
            Dict[str, Any]: 删除后的数据 / Redacted data
        """
        if not isinstance(data, dict):
            return data

        # 如果没有指定字段，自动检测
        if not fields_to_redact:
            fields_to_redact = self.detect_sensitive_fields(data)

        redacted = data.copy()
        for field in fields_to_redact:
            if field in redacted:
                redacted[field] = "***REDACTED***"

        return redacted

    def anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        匿名化数据 / Anonymize Data

        Args:
            data: 数据字典 / Data dictionary

        Returns:
            Dict[str, Any]: 匿名化后的数据 / Anonymized data
        """
        if not isinstance(data, dict):
            return data

        anonymized = {}
        for key, value in data.items():
            if self.is_sensitive_column(key):
                anonymized[key] = self.hash_sensitive_value(str(value))
            elif isinstance(value, dict):
                anonymized[key] = self.anonymize_data(value)
            elif isinstance(value, list):
                anonymized[key] = [
                    self.anonymize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                anonymized[key] = value

        return anonymized

    def validate_sanitization(self, original: Any, sanitized: Any) -> bool:
        """
        验证清理结果 / Validate Sanitization Result

        Args:
            original: 原始数据 / Original data
            sanitized: 清理后数据 / Sanitized data

        Returns:
            bool: 验证是否通过 / Whether validation passed
        """
        # 简单验证：确保敏感数据已被清理
        if isinstance(original, dict) and isinstance(sanitized, dict):
            for key in original.keys():
                if self.is_sensitive_column(key):
                    if key in sanitized and original[key] == sanitized[key]:
                        return False
        return True

    def get_sanitization_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取清理报告 / Get Sanitization Report

        Args:
            data: 数据字典 / Data dictionary

        Returns:
            Dict[str, Any]: 清理报告 / Sanitization report
        """
        sensitive_fields = self.detect_sensitive_fields(data)
        total_fields = len(data) if isinstance(data, dict) else 0

        return {
            "total_fields": total_fields,
            "sensitive_fields_count": len(sensitive_fields),
            "sensitive_fields": sensitive_fields,
            "sanitization_ratio": len(sensitive_fields) / total_fields
            if total_fields > 0
            else 0,
            "compliance_categories": [
                self.compliance_mapping.get(field, "unknown")
                for field in sensitive_fields
                if field in self.compliance_mapping
            ],
        }

    def update_sensitive_patterns(self, new_patterns: List[str]) -> None:
        """
        更新敏感模式 / Update Sensitive Patterns

        Args:
            new_patterns: 新模式列表 / New patterns list
        """
        try:
            self.sensitive_patterns.extend(new_patterns)
            self.logger.info(f"已添加 {len(new_patterns)} 个新的敏感模式")
        except Exception as e:
            self.logger.error(f"更新敏感模式失败: {e}")

    def update_sensitive_columns(self, new_columns: List[str]) -> None:
        """
        更新敏感列 / Update Sensitive Columns

        Args:
            new_columns: 新列列表 / New columns list
        """
        try:
            self.sensitive_columns.update([col.lower() for col in new_columns])
            self.logger.info(f"已添加 {len(new_columns)} 个新的敏感列")
        except Exception as e:
            self.logger.error(f"更新敏感列失败: {e}")

    def get_compliance_category(
        self, table_name: Optional[str] = None
    ) -> Optional[str]:
        """
        获取合规类别 / Get Compliance Category

        Args:
            table_name: 表名 / Table name

        Returns:
            Optional[str]: 合规类别 / Compliance category
        """
        if table_name and table_name in self.compliance_mapping:
            return self.compliance_mapping[table_name]
        return None
