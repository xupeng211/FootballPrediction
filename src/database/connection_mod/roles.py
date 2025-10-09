"""
数据库角色定义
Database Role Definitions

定义数据库用户角色和权限。
"""

from enum import Enum


class DatabaseRole(str, Enum):
    """
    数据库用户角色枚举 / Database User Role Enumeration

    定义数据库用户的三种角色，用于权限分离。
    Defines three roles for database users for permission separation.

    Roles:
        READER: 只读用户（分析、前端） / Read-only user (analytics, frontend)
        WRITER: 读写用户（数据采集） / Read-write user (data collection)
        ADMIN: 管理员用户（运维、迁移） / Administrator user (operations, migration)

    Attributes:
        READER: 只读角色 / Read-only role
        WRITER: 读写角色 / Read-write role
        ADMIN: 管理员角色 / Administrator role
    """

    READER = "reader"
    WRITER = "writer"
    ADMIN = "admin"

    @classmethod
    def get_role_permissions(cls, role: str) -> Dict[str, bool]:
        """
        获取角色权限 / Get role permissions

        Args:
            role (str): 角色名称 / Role name

        Returns:
            Dict[str, bool]: 权限字典 / Permission dictionary
        """
        permissions = {
            cls.READER: {
                "read": True,
                "write": False,
                "delete": False,
                "create_table": False,
                "alter_table": False,
                "drop_table": False,
                "create_index": False,
                "drop_index": False,
                "execute": True,
            },
            cls.WRITER: {
                "read": True,
                "write": True,
                "delete": False,
                "create_table": False,
                "alter_table": False,
                "drop_table": False,
                "create_index": True,
                "drop_index": False,
                "execute": True,
            },
            cls.ADMIN: {
                "read": True,
                "write": True,
                "delete": True,
                "create_table": True,
                "alter_table": True,
                "drop_table": True,
                "create_index": True,
                "drop_index": True,
                "execute": True,
            },
        }

        return permissions.get(role, {})

    @classmethod
    def can_perform(cls, role: str, action: str) -> bool:
        """
        检查角色是否可以执行特定操作 / Check if role can perform specific action

        Args:
            role (str): 角色名称 / Role name
            action (str): 操作名称 / Action name

        Returns:
            bool: 是否可以执行 / Whether can perform
        """
        permissions = cls.get_role_permissions(role)
        return permissions.get(action, False)