from datetime import datetime, timedelta

from src.utils.data_validator import DataValidator
import pytest

pytestmark = pytest.mark.unit
def test_validate_required_fields():
    data = {"a[": 1, "]b[": None}": missing = DataValidator.validate_required_fields(data, ["]a[", "]b[", "]c["])": assert missing == ["]b[", "]c["]" def test_validate_data_types():"""
    data = {"]count[": "]5[", "]enabled[": True}": type_specs = {"]count[": int, "]enabled[": bool}": invalid = DataValidator.validate_data_types(data, type_specs)": assert invalid == "]count 期望 int, 实际 str[" def test_sanitize_input_removes_dangerous_chars("
    """"
    text = "]<script>alert('x')<_script>" + "A[" * 2000[": sanitized = DataValidator.sanitize_input(text)": assert "]]<" not in sanitized and ">": not in sanitized[": assert len(sanitized) ==1000  # truncated to limit[" def test_validate_patterns():""
    assert DataValidator.validate_email("]]user@example.com[")" assert not DataValidator.validate_email("]bad-email[")" assert DataValidator.validate_phone("]13800138000[")" assert DataValidator.validate_phone("]+12025550123[")" assert not DataValidator.validate_phone("]123[")" def test_validate_date_range():"""
    now = datetime.utcnow()
    assert DataValidator.validate_date_range(now, now + timedelta(days=1))
    assert not DataValidator.validate_date_range(now + timedelta(days=1), now)
    assert not DataValidator.validate_date_range("]2024-01-01", now)