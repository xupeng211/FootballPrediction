"""
敏感数据处理

清理和哈希敏感信息，保护用户隐私。
"""




class DataSanitizer:
    """敏感数据清理器"""

    def __init__(self):
        """初始化清理器"""
        # 敏感数据表
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
        # 敏感字段
        self.sensitive_columns = {
            "password",
            "token",
            "secret",
            "key",
            "email",
            "phone",
            "ssn",
            "credit_card",
            "bank_account",
            "api_key",
        }
        # 高风险操作
        self.high_risk_actions = {
            AuditAction.DELETE,
            AuditAction.GRANT,
            AuditAction.REVOKE,
            AuditAction.BACKUP,
            AuditAction.RESTORE,
            AuditAction.SCHEMA_CHANGE,
        }
        # 高敏感字段（需要哈希处理）
        self.high_sensitive_fields = {"password", "token", "secret", "key", "api_key"}

    def hash_sensitive_value(self, value: str) -> str:
        """对敏感数据进行哈希处理"""
        if not value:
            return ""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def is_sensitive_table(self, table_name: str) -> bool:
        """检查是否为敏感表"""
        return table_name.lower() in self.sensitive_tables

    def is_sensitive_column(self, column_name: str) -> bool:
        """检查是否为敏感字段"""
        return column_name.lower() in self.sensitive_columns

    def is_high_risk_action(self, action: AuditAction) -> bool:
        """检查是否为高风险操作"""
        return action in self.high_risk_actions

    def sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理数据中的敏感信息"""
        if not isinstance(data, dict):
            return data

        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            if key.lower() in self.high_sensitive_fields:
                # 对高敏感字段进行哈希处理
                if isinstance(value, str):
                    sanitized[key] = self.hash_sensitive_value(value)
                else:
                    sanitized[key] = "[SENSITIVE]"
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                sanitized[key] = self.sanitize_data(value)
            elif isinstance(value, list):
                # 处理列表中的字典
                sanitized[key] = [
                    self.sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def filter_sensitive_fields(self, data: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """过滤特定表的敏感字段"""
        if not self.is_sensitive_table(table_name):
            return data



        filtered = {}
        for key, value in data.items():
            if key.lower() not in self.sensitive_columns:
                filtered[key] = value
            else:
                # 对敏感字段进行标记
                filtered[key] = f"[REDACTED:{key.upper()}]"

        return filtered