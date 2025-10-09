"""
数据库备份任务模块

提供数据库备份功能。
"""

from .backup_task import backup_database

__all__ = ["backup_database"]