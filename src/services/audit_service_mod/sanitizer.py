"""
审计数据清理器
Audit Data Sanitizer

负责清理和屏蔽敏感数据。
"""

import hashlib
from typing import Any, Dict, List


class AuditDataSanitizer:
    """审计数据清理器，用于处理敏感信息"""

    def __init__(self):
        """初始化清理器"""
        self.sensitive_tables = {
            "users",
            "permissions",
            "tokens",
            "user_sessions",
            "audit_logs",
            "api_keys",
            "credentials",
            "secrets",
        }

        self.sensitive_fields = {
            "password",
            "token",
            "secret",
            "key",
            "hash",
            "salt",
            "ssn",
            "social_security_number",
            "credit_card",
            "bank_account",
            "email",
            "phone",
            "address",
            "id_number",
            "passport",
        }

        self.pii_patterns = [
            "email",
            "phone",
            "address",
            "name",
            "username",
            "userid",
            "user_id",
            "identification",
        ]

        self.high_risk_operations = {
            "DELETE",
            "DROP",
            "TRUNCATE",
            "UPDATE password",
            "UPDATE token",
            "UPDATE secret",
            "UPDATE key",
            "CREATE user",
            "GRANT",
            "REVOKE",
        }

    def _hash_sensitive_value(self, value: str) -> str:
        """对敏感值进行哈希处理"""
        if not value:
            return ""
        # 使用SHA-256哈希算法
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    def _hash_sensitive_data(self, data: str) -> str:
        """哈希敏感数据"""
        try:
            # 检测JSON格式
            if data.strip().startswith("{") or data.strip().startswith("["):
                import json

                parsed = json.loads(data)
                sanitized = self._sanitize_data(parsed)
                return json.dumps(sanitized)
            else:
                # 检测是否是键值对格式
                if "=" in data and "&" in data:
                    # URL参数格式
                    params = dict(param.split("=") for param in data.split("&"))
                    sanitized = self._sanitize_data(params)
                    return "&".join(f"{k}={v}" for k, v in sanitized.items())
                else:
                    # 纯文本
                    if len(data) > 50:  # 只哈希长文本
                        return self._hash_sensitive_value(data)
                    return data
        except Exception:
            # 如果解析失败，直接哈希
            return self._hash_sensitive_value(data) if len(data) > 20 else data

    def _sanitize_data(self, data: Any) -> Any:
        """清理敏感数据"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if self._is_sensitive_field(key):
                    sanitized[key] = "***MASKED***"
                elif isinstance(value, (str, dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, str):
            # 检查是否包含敏感信息
            if any(pattern in data.lower() for pattern in self.pii_patterns):
                # 如果是键值对格式
                if ":" in data or "=" in data:
                    parts = data.split(":") if ":" in data else data.split("=")
                    if len(parts) == 2:
                        key, value = parts
                        if self._is_sensitive_field(key):
                            return f"{key}:***MASKED***"
                return data[:20] + "***" if len(data) > 20 else data
            return data
        else:
            return data

    def _is_sensitive_field(self, field_name: str) -> bool:
        """检查字段是否敏感"""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in self.sensitive_fields)

    def _is_sensitive_table(self, table_name: str) -> bool:
        """检查表是否敏感"""
        return table_name.lower() in self.sensitive_tables

    def _contains_pii(self, data: Dict[str, Any]) -> bool:
        """检查是否包含个人身份信息"""
        if not isinstance(data, dict):
            return False

        data_str = str(data).lower()
        return any(pattern in data_str for pattern in self.pii_patterns)

    def _is_sensitive_data(
        self,
        table_name: Any,
        operation: str,
        data: Any,
        field_name: Optional[str] = None,
    ) -> bool:
        """判断数据是否敏感"""
        # 检查表名
        if isinstance(table_name, str) and self._is_sensitive_table(table_name):
            return True

        # 检查字段名
        if field_name and self._is_sensitive_field(field_name):
            return True

        # 检查操作类型
        if operation.upper() in self.high_risk_operations:
            return True

        # 检查数据内容
        if isinstance(data, dict) and self._contains_pii(data):
            return True

        # 检查数据中的敏感字段
        if isinstance(data, dict):
            for key in data.keys():
                if self._is_sensitive_field(key):
                    return True

        return False
