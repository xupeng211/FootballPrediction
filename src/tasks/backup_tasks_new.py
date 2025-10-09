"""
备份任务模块（重构后）

这是一个重构后的备份任务模块，将原来的1380行大文件拆分为：
- BackupConfig: 备份配置管理
- BackupExecutor: 备份执行器
- BackupValidator: 备份验证器
- BackupCleaner: 备份清理器
- 各种专门的备份任务类

使用示例:
    from src.tasks.backup import (
        DatabaseBackupTask,
        RedisBackupTask,
        daily_full_backup_task,
        redis_backup_task
    )

    # 执行数据库备份
    result = DatabaseBackupTask().delay(backup_type="full")

    # 使用预定义任务
    result = daily_full_backup_task.apply_async()
"""

from .backup.cleanup.backup_cleaner import BackupCleaner
from .backup.core.backup_config import BackupConfig
from .backup.executor.backup_executor import BackupExecutor
from .backup.tasks import (
from .backup.validation.backup_validator import BackupValidator

    DatabaseBackupTask,
    RedisBackupTask,
    LogsBackupTask,
    BackupValidationTask,
    BackupCleanupTask,
    # 预定义任务实例
    daily_full_backup_task,
    weekly_full_backup_task,
    monthly_full_backup_task,
    hourly_incremental_backup_task,
    wal_backup_task,
    redis_backup_task,
    logs_backup_task,
    backup_validation_task,
    backup_cleanup_task,
    redis_cleanup_task,
    logs_cleanup_task
)

# 导出核心组件

# 为了向后兼容，保留一些常用的导入

__all__ = [
    # 主要任务类
    "DatabaseBackupTask",
    "RedisBackupTask",
    "LogsBackupTask",
    "BackupValidationTask",
    "BackupCleanupTask",

    # 预定义任务
    "daily_full_backup_task",
    "weekly_full_backup_task",
    "monthly_full_backup_task",
    "hourly_incremental_backup_task",
    "wal_backup_task",
    "redis_backup_task",
    "logs_backup_task",
    "backup_validation_task",
    "backup_cleanup_task",
    "redis_cleanup_task",
    "logs_cleanup_task",

    # 核心组件
    "BackupConfig",
    "BackupExecutor",
    "BackupValidator",
    "BackupCleaner",
    "get_backup_metrics",

    # 向后兼容
    "BackupTask",
]

# 版本信息
__version__ = "2.0.0"
__author__ = "Claude Code"
__description__ = "重构后的备份任务模块，提供模块化、可测试的备份功能"