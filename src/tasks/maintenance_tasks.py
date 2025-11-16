"""维护任务模块.

包含系统维护相关的任务:
- 数据质量检查
- 错误日志清理
- 系统健康监控
- 数据库维护
"""

import logging
import os
from datetime import datetime
from typing import Any

from sqlalchemy import text

import redis
from src.database.connection import DatabaseManager
from src.tasks.celery_app import app

logger = logging.getLogger(__name__)


@app.task
def quality_check_task() -> dict[str, Any]:
    """数据质量检查任务."""
    try:
        db_manager = DatabaseManager()

        # 检查数据库连接
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT 1"))
            db_status = "healthy" if result else "unhealthy"

        # 检查Redis连接
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        redis_status = "healthy" if r.ping() else "unhealthy"

        return {
            "timestamp": datetime.now().isoformat(),
            "database_status": db_status,
            "redis_status": redis_status,
            "overall_status": (
                "healthy"
                if db_status == "healthy" and redis_status == "healthy"
                else "degraded"
            ),
        }

    except Exception as e:
        logger.error(f"质量检查失败: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "overall_status": "error",
        }


@app.task
def cleanup_logs_task() -> dict[str, Any]:
    """日志清理任务."""
    try:
        log_dir = "logs"
        cleaned_files = []

        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                filepath = os.path.join(log_dir, filename)
                if os.path.isfile(filepath):
                    # 删除超过7天的日志文件
                    file_age = datetime.now().timestamp() - os.path.getctime(filepath)
                    if file_age > 7 * 24 * 3600:  # 7天
                        os.remove(filepath)
                        cleaned_files.append(filename)

        return {
            "timestamp": datetime.now().isoformat(),
            "cleaned_files": cleaned_files,
            "files_count": len(cleaned_files),
        }

    except Exception as e:
        logger.error(f"日志清理失败: {e}")
        return {"timestamp": datetime.now().isoformat(), "error": str(e)}


@app.task
def system_health_task() -> dict[str, Any]:
    """系统健康检查任务."""
    try:
        import psutil

        # 系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3),
            "status": (
                "healthy" if cpu_percent < 80 and memory.percent < 80 else "warning"
            ),
        }

    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "error",
        }


@app.task
def database_maintenance_task() -> dict[str, Any]:
    """数据库维护任务."""
    try:
        db_manager = DatabaseManager()

        with db_manager.get_session() as session:
            # 更新统计信息
            session.execute(text("ANALYZE"))

            # 清理过期数据（示例：删除30天前的日志）
            result = session.execute(
                text(
                    "DELETE FROM system_logs WHERE created_at < NOW() - INTERVAL '30 days'"
                )
            )
            deleted_count = result.rowcount

            session.commit()

        return {
            "timestamp": datetime.now().isoformat(),
            "analyzed": True,
            "deleted_records": deleted_count,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"数据库维护失败: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "error",
        }
