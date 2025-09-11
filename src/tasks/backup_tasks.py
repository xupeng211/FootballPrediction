"""
数据库备份任务

实现定时数据库备份任务，包括：
- 全量备份任务
- 增量备份任务
- 备份文件清理任务
- 备份验证任务

集成 Prometheus 监控指标，支持备份成功率和时间戳监控。
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from celery import Task
from prometheus_client import Counter, Gauge, Histogram

from .celery_app import app
from .error_logger import TaskErrorLogger

logger = logging.getLogger(__name__)


# =============================================================================
# Prometheus 监控指标
# =============================================================================

# 备份成功指标
backup_success_total = Counter(
    "football_database_backup_success_total",
    "Total number of successful database backups",
    ["backup_type", "database_name"],
)

# 备份失败指标
backup_failure_total = Counter(
    "football_database_backup_failure_total",
    "Total number of failed database backups",
    ["backup_type", "database_name", "error_type"],
)

# 最后备份时间戳
last_backup_timestamp = Gauge(
    "football_database_last_backup_timestamp",
    "Timestamp of last successful backup",
    ["backup_type", "database_name"],
)

# 备份执行时间
backup_duration_seconds = Histogram(
    "football_database_backup_duration_seconds",
    "Time taken to complete database backup",
    ["backup_type", "database_name"],
)

# 备份文件大小
backup_file_size_bytes = Gauge(
    "football_database_backup_file_size_bytes",
    "Size of backup file in bytes",
    ["backup_type", "database_name"],
)


class DatabaseBackupTask(Task):
    """数据库备份任务基类"""

    def __init__(self):
        super().__init__()
        self.error_logger = TaskErrorLogger()

        # 备份脚本路径
        self.backup_script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "scripts",
            "backup.sh",
        )

        # 恢复脚本路径
        self.restore_script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "scripts",
            "restore.sh",
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的处理"""
        task_name = self.name.split(".")[-1] if self.name else "unknown_backup_task"
        backup_type = kwargs.get("backup_type", "unknown")
        database_name = kwargs.get("database_name", "football_prediction")

        # 记录 Prometheus 失败指标
        backup_failure_total.labels(
            backup_type=backup_type,
            database_name=database_name,
            error_type=type(exc).__name__,
        ).inc()

        # 异步记录错误日志
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                self.error_logger.log_task_error(
                    task_name=task_name,
                    task_id=task_id,
                    error=exc,
                    context={
                        "args": args,
                        "kwargs": kwargs,
                        "einfo": str(einfo),
                        "backup_type": backup_type,
                        "database_name": database_name,
                    },
                    retry_count=self.request.retries if hasattr(self, "request") else 0,
                )
            )
        except Exception as log_error:
            logger.error(f"记录备份任务错误日志失败: {log_error}")

    def run_backup_script(
        self,
        backup_type: str,
        database_name: str = "football_prediction",
        additional_args: Optional[list] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        运行备份脚本

        Args:
            backup_type: 备份类型 (full|incremental|wal|all)
            database_name: 数据库名称
            additional_args: 额外的脚本参数

        Returns:
            (成功状态, 输出信息, 执行统计)
        """
        start_time = datetime.now()

        # 构建命令
        cmd = [self.backup_script_path, "--type", backup_type]
        if additional_args:
            cmd.extend(additional_args)

        # 设置环境变量
        env = os.environ.copy()
        env.update(
            {
                "DB_NAME": database_name,
                "DB_HOST": os.getenv("DB_HOST", "localhost"),
                "DB_PORT": os.getenv("DB_PORT", "5432"),
                "DB_USER": os.getenv("DB_USER", "postgres"),
                "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
                "BACKUP_DIR": os.getenv("BACKUP_DIR", "/backup/football_db"),
            }
        )

        try:
            logger.info(f"开始执行 {backup_type} 备份: {' '.join(cmd)}")

            # 执行备份脚本
            result = subprocess.run(
                cmd, capture_output=True, text=True, env=env, timeout=3600  # 1小时超时
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 备份统计信息
            stats = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "exit_code": result.returncode,
                "command": " ".join(cmd),
            }

            if result.returncode == 0:
                # 备份成功
                logger.info(f"{backup_type} 备份执行成功，耗时 {duration:.2f} 秒")

                # 记录成功指标
                backup_success_total.labels(
                    backup_type=backup_type, database_name=database_name
                ).inc()

                last_backup_timestamp.labels(
                    backup_type=backup_type, database_name=database_name
                ).set(end_time.timestamp())

                backup_duration_seconds.labels(
                    backup_type=backup_type, database_name=database_name
                ).observe(duration)

                # 尝试获取备份文件大小
                backup_file_size = self._get_latest_backup_size(backup_type)
                if backup_file_size:
                    backup_file_size_bytes.labels(
                        backup_type=backup_type, database_name=database_name
                    ).set(backup_file_size)
                    stats["backup_file_size_bytes"] = backup_file_size

                return True, result.stdout, stats

            else:
                # 备份失败
                error_msg = f"{backup_type} 备份执行失败，退出码: {result.returncode}"
                logger.error(
                    f"{error_msg}\n标准输出: {result.stdout}\n错误输出: {result.stderr}"
                )

                # 记录失败指标
                backup_failure_total.labels(
                    backup_type=backup_type,
                    database_name=database_name,
                    error_type="script_execution_failed",
                ).inc()

                return False, f"{error_msg}\n{result.stderr}", stats

        except subprocess.TimeoutExpired:
            error_msg = f"{backup_type} 备份执行超时"
            logger.error(error_msg)

            backup_failure_total.labels(
                backup_type=backup_type,
                database_name=database_name,
                error_type="timeout",
            ).inc()

            return False, error_msg, {"error": "timeout"}

        except Exception as e:
            error_msg = f"{backup_type} 备份执行异常: {str(e)}"
            logger.error(error_msg)

            backup_failure_total.labels(
                backup_type=backup_type,
                database_name=database_name,
                error_type=type(e).__name__,
            ).inc()

            return False, error_msg, {"error": str(e)}

    def _get_latest_backup_size(self, backup_type: str) -> Optional[int]:
        """获取最新备份文件大小"""
        try:
            backup_base_dir = os.getenv("BACKUP_DIR", "/backup/football_db")

            if backup_type == "full":
                backup_dir = os.path.join(backup_base_dir, "full")
                # 查找最新的压缩备份文件
                cmd = f"find {backup_dir} -name 'full_backup_*.sql.gz' -printf '%s\n' | sort -n | tail -1"
            elif backup_type == "incremental":
                backup_dir = os.path.join(backup_base_dir, "incremental")
                # 查找最新增量备份目录大小
                cmd = f"find {backup_dir} -maxdepth 1 -type d -name '2*' -exec du -sb {{}} \\; | sort -k2 | tail -1 | cut -f1"
            else:
                return None

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())

        except Exception as e:
            logger.warning(f"获取备份文件大小失败: {e}")

        return None


# =============================================================================
# 备份任务定义
# =============================================================================


@app.task(base=DatabaseBackupTask, bind=True)
def daily_full_backup_task(self, database_name: str = "football_prediction"):
    """
    每日全量备份任务

    Args:
        database_name: 数据库名称

    Returns:
        dict: 备份执行结果
    """
    logger.info("开始执行每日全量备份任务")

    success, output, stats = self.run_backup_script(
        backup_type="full", database_name=database_name
    )

    result = {
        "task_type": "daily_full_backup",
        "database_name": database_name,
        "success": success,
        "output": output,
        "stats": stats,
        "timestamp": datetime.now().isoformat(),
    }

    if success:
        logger.info("每日全量备份任务执行成功")
    else:
        logger.error("每日全量备份任务执行失败")
        # 自动重试机制在 TaskRetryConfig 中配置

    return result


@app.task(base=DatabaseBackupTask, bind=True)
def hourly_incremental_backup_task(self, database_name: str = "football_prediction"):
    """
    每小时增量备份任务

    Args:
        database_name: 数据库名称

    Returns:
        dict: 备份执行结果
    """
    logger.info("开始执行每小时增量备份任务")

    success, output, stats = self.run_backup_script(
        backup_type="incremental", database_name=database_name
    )

    result = {
        "task_type": "hourly_incremental_backup",
        "database_name": database_name,
        "success": success,
        "output": output,
        "stats": stats,
        "timestamp": datetime.now().isoformat(),
    }

    if success:
        logger.info("每小时增量备份任务执行成功")
    else:
        logger.error("每小时增量备份任务执行失败")

    return result


@app.task(base=DatabaseBackupTask, bind=True)
def weekly_wal_archive_task(self, database_name: str = "football_prediction"):
    """
    每周WAL归档任务

    Args:
        database_name: 数据库名称

    Returns:
        dict: 备份执行结果
    """
    logger.info("开始执行每周WAL归档任务")

    success, output, stats = self.run_backup_script(
        backup_type="wal", database_name=database_name
    )

    result = {
        "task_type": "weekly_wal_archive",
        "database_name": database_name,
        "success": success,
        "output": output,
        "stats": stats,
        "timestamp": datetime.now().isoformat(),
    }

    if success:
        logger.info("每周WAL归档任务执行成功")
    else:
        logger.error("每周WAL归档任务执行失败")

    return result


@app.task(base=DatabaseBackupTask, bind=True)
def cleanup_old_backups_task(self, database_name: str = "football_prediction"):
    """
    清理旧备份文件任务

    Args:
        database_name: 数据库名称

    Returns:
        dict: 清理执行结果
    """
    logger.info("开始执行备份文件清理任务")

    success, output, stats = self.run_backup_script(
        backup_type="full",  # 使用 full 类型，但传递 --cleanup 参数
        database_name=database_name,
        additional_args=["--cleanup"],
    )

    result = {
        "task_type": "cleanup_old_backups",
        "database_name": database_name,
        "success": success,
        "output": output,
        "stats": stats,
        "timestamp": datetime.now().isoformat(),
    }

    if success:
        logger.info("备份文件清理任务执行成功")
    else:
        logger.error("备份文件清理任务执行失败")

    return result


@app.task(base=DatabaseBackupTask, bind=True)
def verify_backup_task(
    self, backup_file_path: str, database_name: str = "football_prediction"
):
    """
    验证备份文件任务

    Args:
        backup_file_path: 备份文件路径
        database_name: 数据库名称

    Returns:
        dict: 验证执行结果
    """
    logger.info(f"开始验证备份文件: {backup_file_path}")

    # 使用恢复脚本的验证功能
    cmd = [self.restore_script_path, "--validate", backup_file_path]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300  # 5分钟超时
        )

        success = result.returncode == 0

        verification_result = {
            "task_type": "verify_backup",
            "database_name": database_name,
            "backup_file_path": backup_file_path,
            "success": success,
            "output": result.stdout,
            "error_output": result.stderr if result.stderr else None,
            "timestamp": datetime.now().isoformat(),
        }

        if success:
            logger.info(f"备份文件验证成功: {backup_file_path}")
        else:
            logger.error(f"备份文件验证失败: {backup_file_path}")

        return verification_result

    except subprocess.TimeoutExpired:
        error_msg = f"备份文件验证超时: {backup_file_path}"
        logger.error(error_msg)

        return {
            "task_type": "verify_backup",
            "database_name": database_name,
            "backup_file_path": backup_file_path,
            "success": False,
            "error": "timeout",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        error_msg = f"备份文件验证异常: {str(e)}"
        logger.error(error_msg)

        return {
            "task_type": "verify_backup",
            "database_name": database_name,
            "backup_file_path": backup_file_path,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 辅助任务
# =============================================================================


@app.task
def get_backup_status():
    """
    获取备份状态信息

    Returns:
        dict: 备份状态统计
    """
    try:
        backup_base_dir = os.getenv("BACKUP_DIR", "/backup/football_db")

        # 统计备份文件数量和大小
        stats = {
            "full_backups": {"count": 0, "total_size_bytes": 0, "latest_backup": None},
            "incremental_backups": {
                "count": 0,
                "total_size_bytes": 0,
                "latest_backup": None,
            },
            "timestamp": datetime.now().isoformat(),
        }

        # 统计全量备份
        full_backup_dir = os.path.join(backup_base_dir, "full")
        if os.path.exists(full_backup_dir):
            cmd = f"find {full_backup_dir} -name 'full_backup_*.sql.gz' -printf '%s %T@ %p\n' | sort -k2"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split("\n")
                total_size = 0
                count = 0
                latest_backup = None

                for line in lines:
                    if line:
                        parts = line.split(" ", 2)
                        if len(parts) == 3:
                            size, timestamp, path = parts
                            total_size += int(size)
                            count += 1
                            latest_backup = {
                                "path": path,
                                "size_bytes": int(size),
                                "timestamp": float(timestamp),
                            }

                stats["full_backups"] = {
                    "count": count,
                    "total_size_bytes": total_size,
                    "latest_backup": latest_backup,
                }

        # 统计增量备份
        incremental_backup_dir = os.path.join(backup_base_dir, "incremental")
        if os.path.exists(incremental_backup_dir):
            cmd = (
                f"find {incremental_backup_dir} -maxdepth 1 -type d -name '2*' | wc -l"
            )
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0 and result.stdout:
                stats["incremental_backups"]["count"] = int(result.stdout.strip())

        return stats

    except Exception as e:
        logger.error(f"获取备份状态失败: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@app.task
def manual_backup_task(
    backup_type: str = "full", database_name: str = "football_prediction"
):
    """
    手动触发备份任务

    Args:
        backup_type: 备份类型 (full|incremental|wal|all)
        database_name: 数据库名称

    Returns:
        dict: 备份执行结果
    """
    logger.info(f"手动触发 {backup_type} 备份任务")

    # 根据备份类型调用相应的任务
    if backup_type == "full":
        return daily_full_backup_task.apply_async(args=[database_name]).get()
    elif backup_type == "incremental":
        return hourly_incremental_backup_task.apply_async(args=[database_name]).get()
    elif backup_type == "wal":
        return weekly_wal_archive_task.apply_async(args=[database_name]).get()
    elif backup_type == "all":
        # 并行执行所有类型的备份
        from celery import group

        job = group(
            daily_full_backup_task.s(database_name),
            hourly_incremental_backup_task.s(database_name),
            weekly_wal_archive_task.s(database_name),
        )

        results = job.apply_async().get()

        return {
            "task_type": "manual_backup_all",
            "database_name": database_name,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    else:
        raise ValueError(f"不支持的备份类型: {backup_type}")
