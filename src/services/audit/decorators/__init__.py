"""
审计装饰器模块

提供自动审计装饰器。
"""


from .audit_decorators import audit_operation, audit_database_operation

__all__ = ["audit_operation", "audit_database_operation"]
