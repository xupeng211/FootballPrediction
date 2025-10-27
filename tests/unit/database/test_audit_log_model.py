import pytest

from src.database.models.audit_log import AuditLog


@pytest.mark.unit
@pytest.mark.database
def test_audit_log():
    log = AuditLog(action="CREATE", table_name="test_table")
    assert log.action == "CREATE"
    assert log.table_name == "test_table"
