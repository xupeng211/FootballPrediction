"""
数据库连接核心枚举

定义数据库角色和类型相关的枚举
"""

from enum import Enum
from typing import Dict


class DatabaseRole(str, Enum):
    """
    数据库用户角色枚举 / Database User Role Enumeration

    定义数据库用户的三种角色，用于权限分离。
    Defines three roles for database users for permission separation.

    Roles:
        READER: 只读用户（分析、前端） / Read-only user (analytics, frontend)
        WRITER: 读写用户（数据采集） / Read-write user (data collection)
        ADMIN: 管理员用户（运维、迁移） / Administrator user (operations, migration)
    """

    READER = "reader"
    WRITER = "writer"
    ADMIN = "admin"

    @classmethod
    def get_permissions(cls, role: "DatabaseRole") -> Dict[str, bool]:
        """
        获取角色的权限 / Get role permissions

        Args:
            role: 数据库角色 / Database role

        Returns:
            Dict[str, bool]: 权限字典 / Permission dictionary
        """
        permissions = {
            cls.READER: {
                "select": True,
                "insert": False,
                "update": False,
                "delete": False,
                "create": False,
                "drop": False,
            },
            cls.WRITER: {
                "select": True,
                "insert": True,
                "update": True,
                "delete": False,
                "create": False,
                "drop": False,
            },
            cls.ADMIN: {
                "select": True,
                "insert": True,
                "update": True,
                "delete": True,
                "create": True,
                "drop": True,
            },
        }
        return permissions.get(role, {})

    def has_permission(self, permission: str) -> bool:
        """
        检查角色是否具有特定权限 / Check if role has specific permission

        Args:
            permission: 权限名称 / Permission name

        Returns:
            bool: 是否有权限 / Whether has permission
        """
        permissions = self.get_permissions(self)
        return permissions.get(permission, False)