"""测试审计日志模型."""

import pytest
from datetime import datetime
from src.database.models.audit_log import AuditLog


class TestAuditLog:
    """测试审计日志模型."""

    def test_table_name(self):
        """测试表名."""
        assert AuditLog.__tablename__ == "audit_logs"

    def test_model_fields(self):
        """测试模型字段."""
        required_fields = [
            "id",
            "user_id",
            "action",
            "resource_type",
            "resource_id",
            "old_values",
            "new_values",
            "ip_address",
            "user_agent",
            "timestamp",
        ]

        for field in required_fields:
            assert hasattr(AuditLog, field), f"Missing field: {field}"

    def test_repr_method(self):
        """测试__repr__方法."""
        log = AuditLog(
            user_id=1, action="CREATE", resource_type="match", resource_id=123
        )

        repr_str = repr(log)
        assert "AuditLog" in repr_str
        assert "CREATE" in repr_str or "match" in repr_str

    def test_model_import(self):
        """测试模型导入."""
        from src.database.models.audit_log import AuditLog

        assert AuditLog is not None
