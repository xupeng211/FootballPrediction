"""
数据库备份任务 / Database Backup Tasks

实现定时数据库备份任务，包括：
- 全量备份任务
- 增量备份任务
- 备份文件清理任务
- 备份验证任务

集成 Prometheus 监控指标，支持备份成功率和时间戳监控。

Implements scheduled database backup tasks, including:
- Full backup tasks
- Incremental backup tasks
- Backup file cleanup tasks
- Backup verification tasks

Integrates Prometheus monitoring metrics, supporting backup success rate and timestamp monitoring.

⚠️ 注意：此文件已重构为模块化结构。
为了向后兼容性，这里保留了原始的导入接口。
建议使用：from src.tasks.backup import <function_name>

主要类 / Main Classes:
    DatabaseBackupTask: 数据库备份任务基类 / Database backup task base class

主要方法 / Main Methods:
    daily_full_backup_task: 每日全量备份任务 / Daily full backup task
    hourly_incremental_backup_task: 每小时增量备份任务 / Hourly incremental backup task
    weekly_wal_archive_task: 每周WAL归档任务 / Weekly WAL archive task
    cleanup_old_backups_task: 清理旧备份文件任务 / Clean up old backup files task

使用示例 / Usage Example:
    ```python
    from src.tasks.backup_tasks import daily_full_backup_task

    # 手动触发每日全量备份
    _result = daily_full_backup_task.delay()

    # 获取任务执行结果
    backup_result = result.get()
    logger.info(f"备份状态: {'成功' if backup_result['success'] else '失败'}")
    ```

环境变量 / Environment Variables:
    BACKUP_DIR: 备份文件存储目录 / Backup file storage directory
    DB_HOST: 数据库主机地址 / Database host address
    DB_PORT: 数据库端口 / Database port
    DB_NAME: 数据库名称 / Database name
    DB_USER: 数据库用户名 / Database username
    DB_PASSWORD: 数据库密码 / Database password

依赖 / Dependencies:
    - celery: 任务队列框架 / Task queue framework

重构历史 / Refactoring History:
    - 原始文件：1380行，包含所有备份相关功能
    - 重构为模块化结构：
      - base.py: 基础类和指标定义
      - database.py: 数据库备份任务
      - maintenance.py: 维护任务（清理、验证）
      - services.py: 服务备份任务（Redis、日志）
      - manual.py: 手动备份和状态查询
"""

# 为了向后兼容性，从新的模块化结构中导入所有内容
from .backup import (  # type: ignore
    # 基础类和指标
    DatabaseBackupTask,
    get_backup_metrics,
    backup_tasks_total,
    backup_task_duration,
    backup_last_success,
    backup_size_bytes,
    backup_failures_total,
    # 数据库备份任务
    daily_full_backup_task,
    hourly_incremental_backup_task,
    weekly_wal_archive_task,
    backup_database_task,
    verify_backup_task,
    # 维护任务
    cleanup_old_backups_task,
    verify_backup_integrity_task,
    check_backup_storage_task,
    # 服务备份任务
    backup_redis_task,
    backup_logs_task,
    backup_config_task,
    # 手动任务
    manual_backup_task,
    get_backup_status,
    list_backup_files,
    restore_backup,
)

# 重新导出以保持原始接口
__all__ = [
    # 基础类和指标
    "DatabaseBackupTask",
    "get_backup_metrics",
    "backup_tasks_total",
    "backup_task_duration",
    "backup_last_success",
    "backup_size_bytes",
    "backup_failures_total",
    # 数据库备份任务
    "daily_full_backup_task",
    "hourly_incremental_backup_task",
    "weekly_wal_archive_task",
    "backup_database_task",
    "verify_backup_task",
    # 维护任务
    "cleanup_old_backups_task",
    "verify_backup_integrity_task",
    "check_backup_storage_task",
    # 服务备份任务
    "backup_redis_task",
    "backup_logs_task",
    "backup_config_task",
    # 手动任务
    "manual_backup_task",
    "get_backup_status",
    "list_backup_files",
    "restore_backup",
]

# 原始实现已移至 src/tasks/backup/ 模块
# 此处保留仅用于向后兼容性
# 请使用新的模块化结构以获得更好的维护性

# 包含的所有功能：
# - DatabaseBackupTask: 数据库备份任务基类
# - get_backup_metrics: 获取备份相关指标
# - daily_full_backup_task: 每日完整数据库备份任务
# - hourly_incremental_backup_task: 每小时增量备份任务（基于WAL归档）
# - weekly_wal_archive_task: 每周WAL归档任务
# - backup_database_task: 通用数据库备份任务
# - verify_backup_task: 验证备份文件完整性
# - cleanup_old_backups_task: 清理旧备份文件任务
# - verify_backup_integrity_task: 验证备份完整性任务
# - check_backup_storage_task: 检查备份存储空间任务
# - backup_redis_task: Redis备份任务
# - backup_logs_task: 日志备份任务
# - backup_config_task: 配置文件备份任务
# - manual_backup_task: 手动备份任务
# - get_backup_status: 获取备份状态
# - list_backup_files: 列出备份文件
# - restore_backup: 恢复备份（紧急情况）
