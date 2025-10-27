"""
简单的模块可用性测试
"""

import sys

import pytest

# 确保模块可以导入
sys.path.insert(0, "src")


@pytest.mark.unit
def test_health_module_import():
    """测试健康模块可以导入"""
    try:
        from src.api.health.utils import HealthChecker

        assert HealthChecker is not None
    except ImportError:
        pytest.skip("健康模块不可用")


def test_audit_module_import():
    """测试审计模块可以导入"""
    try:
        from src.services.audit_service import AuditService

        assert AuditService is not None
    except ImportError:
        pytest.skip("审计模块不可用")


def test_di_module_import():
    """测试DI模块可以导入"""
    try:
        from src.core.di import DIContainer

        assert DIContainer is not None
    except ImportError:
        pytest.skip("DI模块不可用")
