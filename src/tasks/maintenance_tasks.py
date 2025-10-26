"""
维护任务模块

包含系统维护相关的任务：
- 数据质量检查
- 错误日志清理
- 系统健康监控
- 数据库维护
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime
from typing import Any, Dict

from src.database.connection import DatabaseManager
from src.tasks.celery_app import app

logger = logging.getLogger(__name__)

@app.task
def quality_check_task() -> Dict[str, Any]:
    """
    数据质量检查任务

    执行定期的数据质量检查，包括：
    - 数据完整性检查
    - 数据一致性验证
    - 重复数据检查
    - 异常值检测

    Returns:
        检查结果字典
    """

    async def _run_quality_checks():
        """内部异步检查函数"""
        try:
            db_manager = DatabaseManager()
            check_results = {}
            issues_found = 0

            async with db_manager.get_async_session() as session:
                logger.info("开始执行数据质量检查")

                # 1. 检查比赛数据完整性
                match_integrity_query = text(
                    """
                    SELECT COUNT(*) as incomplete_matches
                    FROM matches
                    WHERE home_team_id IS NULL
                    OR away_team_id IS NULL
                    OR league_id IS NULL
                    OR match_time IS NULL
                """
                )

                result = await session.execute(match_integrity_query)
                incomplete_matches = (await result.scalar()) or 0
                check_results["incomplete_matches"] = incomplete_matches
                if incomplete_matches > 0:
                    issues_found += 1

                # 2. 检查重复比赛记录
                duplicate_matches_query = text(
                    """
                    SELECT COUNT(*) as duplicate_count
                    FROM (
                        SELECT home_team_id, away_team_id, match_time, COUNT(*) as cnt
                        FROM matches
                        GROUP BY home_team_id, away_team_id, match_time
                        HAVING COUNT(*) > 1
                    ) t
                """
                )

                result = await session.execute(duplicate_matches_query)
                duplicate_matches = (await result.scalar()) or 0
                check_results["duplicate_matches"] = duplicate_matches
                if duplicate_matches > 0:
                    issues_found += 1

                # 3. 检查赔率数据异常
                abnormal_odds_query = text(
                    """
                    SELECT COUNT(*) as abnormal_odds
                    FROM odds
                    WHERE home_odds < 1.01
                    OR draw_odds < 1.01
                    OR away_odds < 1.01
                    OR home_odds > 1000
                    OR draw_odds > 1000
                    OR away_odds > 1000
                """
                )

                result = await session.execute(abnormal_odds_query)
                abnormal_odds = (await result.scalar()) or 0
                check_results["abnormal_odds"] = abnormal_odds
                if abnormal_odds > 0:
                    issues_found += 1

                # 4. 检查孤立的比赛记录（没有对应球队信息）
                orphan_matches_query = text(
                    """
                    SELECT COUNT(*) as orphan_matches
                    FROM matches m
                    LEFT JOIN teams ht ON m.home_team_id = ht.id
                    LEFT JOIN teams at ON m.away_team_id = at.id
                    WHERE ht.id IS NULL OR at.id IS NULL
                """
                )

                result = await session.execute(orphan_matches_query)
                orphan_matches = (await result.scalar()) or 0
                check_results["orphan_matches"] = orphan_matches
                if orphan_matches > 0:
                    issues_found += 1

                # 5. 检查数据新鲜度
                stale_data_query = text(
                    """
                    SELECT COUNT(*) as stale_collection_logs
                    FROM data_collection_logs
                    WHERE created_at < NOW() - INTERVAL '24 hours'
                    AND status = 'running'
                """
                )

                result = await session.execute(stale_data_query)
                stale_logs = (await result.scalar()) or 0
                check_results["stale_collection_logs"] = stale_logs
                if stale_logs > 0:
                    issues_found += 1

                logger.info(f"数据质量检查完成，发现 {issues_found} 个问题类别")

                return check_results, issues_found

        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.error(f"数据质量检查失败: {str(e)}")
            raise e

    try:
        check_results, issues_found = asyncio.run(_run_quality_checks())

        return {
            "status": "success",
            "checks_performed": len(check_results),
            "issues_found": issues_found,
            "check_results": check_results,
            "execution_time": datetime.now().isoformat(),
        }

    except (RuntimeError, ValueError, ConnectionError) as exc:
        logger.error(f"数据质量检查任务失败: {str(exc)}")
        return {
            "status": "failed",
            "error": str(exc),
            "execution_time": datetime.now().isoformat(),
        }

@app.task
def cleanup_error_logs_task(days: int = 7) -> Dict[str, Any]:
    """
    错误日志清理任务

    清理超过指定天数的错误日志记录

    Args:
        days_to_keep: 保留天数，默认7天

    Returns:
        清理结果字典
    """

    async def _cleanup_error_logs():
        """内部异步清理函数"""
        error_logger = TaskErrorLogger()
        deleted_count = await error_logger.cleanup_old_errors(days)
        return deleted_count

    try:
        logger.info(f"开始清理超过 {days} 天的错误日志")

        deleted_count = asyncio.run(_cleanup_error_logs())

        logger.info(f"错误日志清理完成，删除了 {deleted_count} 条记录")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "days_to_keep": days,
            "execution_time": datetime.now().isoformat(),
        }

    except (RuntimeError, ValueError, ConnectionError) as exc:
        logger.error(f"错误日志清理任务失败: {str(exc)}")
        return {
            "status": "failed",
            "error": str(exc),
            "deleted_count": 0,
            "execution_time": datetime.now().isoformat(),
        }

@app.task
def system_health_check_task() -> Dict[str, Any]:
    """
    系统健康检查任务

    检查系统各组件的健康状态：
    - 数据库连接
    - Redis 连接
    - 任务队列状态
    - 磁盘空间

    Returns:
        健康检查结果
    """

    async def _check_system_health():
        """内部异步健康检查函数"""
        health_status = {}
        overall_healthy = True

        try:
            # 1. 检查数据库连接

            db_manager = DatabaseManager()

            async with db_manager.get_async_session() as session:
                await session.execute(text("SELECT 1"))
                health_status["database"] = {
                    "status": "healthy",
                    "message": "数据库连接正常",
                }

        except (RuntimeError, ValueError, ConnectionError) as e:
            health_status["database"] = {
                "status": "unhealthy",
                "message": f"数据库连接失败: {str(e)}",
            }
            overall_healthy = False

        try:
            # 2. 检查Redis连接

            redis_client = redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0")
            )
            redis_client.ping()
            health_status["redis"] = {"status": "healthy", "message": "Redis连接正常"}

        except (RuntimeError, ValueError, ConnectionError) as e:
            health_status["redis"] = {
                "status": "unhealthy",
                "message": f"Redis连接失败: {str(e)}",
            }
            overall_healthy = False

        try:
            # 3. 检查磁盘空间

            disk_usage = shutil.disk_usage("/")
            free_space_gb = disk_usage.free / (1024**3)

            if free_space_gb > 5:  # 至少5GB空闲空间
                health_status["disk_space"] = {
                    "status": "healthy",
                    "message": f"磁盘空间充足: {free_space_gb:.2f} GB可用",
                }
            else:
                health_status["disk_space"] = {
                    "status": "warning",
                    "message": f"磁盘空间不足: 仅剩 {free_space_gb:.2f} GB",
                }

        except (RuntimeError, ValueError, ConnectionError) as e:
            health_status["disk_space"] = {
                "status": "unknown",
                "message": f"无法检查磁盘空间: {str(e)}",
            }

        return health_status, overall_healthy

    try:
        logger.info("开始执行系统健康检查")

        health_status, overall_healthy = asyncio.run(_check_system_health())

        status = "healthy" if overall_healthy else "unhealthy"
        logger.info(f"系统健康检查完成，状态: {status}")

        return {
            "status": status,
            "overall_healthy": overall_healthy,
            "components": health_status,
            "execution_time": datetime.now().isoformat(),
        }

    except (RuntimeError, ValueError, ConnectionError) as exc:
        logger.error(f"系统健康检查任务失败: {str(exc)}")
        return {
            "status": "failed",
            "error": str(exc),
            "overall_healthy": False,
            "execution_time": datetime.now().isoformat(),
        }

@app.task
def database_maintenance_task() -> Dict[str, Any]:
    """
    数据库维护任务

    执行定期的数据库维护操作：
    - 更新表统计信息
    - 清理临时数据
    - 优化数据库性能

    Returns:
        维护结果字典
    """

    async def _run_database_maintenance():
        """内部异步维护函数"""
        try:
            db_manager = DatabaseManager()
            maintenance_results = {}

            async with db_manager.get_async_session() as session:
                logger.info("开始执行数据库维护")

                # 1. 更新表统计信息（PostgreSQL ANALYZE）
                analyze_queries = [
                    "ANALYZE matches",
                    "ANALYZE odds",
                    "ANALYZE teams",
                    "ANALYZE leagues",
                    "ANALYZE data_collection_logs",
                ]

                for query in analyze_queries:
                    try:
                        await session.execute(text(query))
                        logger.info(f"已执行: {query}")
                    except (RuntimeError, ValueError, ConnectionError) as e:
                        logger.warning(f"执行 {query} 失败: {str(e)}")

                # 2. 清理过期的会话数据
                cleanup_query = text(
                    """
                    DELETE FROM data_collection_logs
                    WHERE status = 'running'
                    AND created_at < NOW() - INTERVAL '24 hours'
                """
                )

                result = await session.execute(cleanup_query)
                cleaned_sessions = result.rowcount
                maintenance_results["cleaned_stale_sessions"] = cleaned_sessions

                # 3. 获取表大小信息
                table_size_query = text(
                    """
                    SELECT
                        table_name,
                        pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC
                    LIMIT 10
                """
                )

                result = await session.execute(table_size_query)
                rows = await result.fetchall()
                table_sizes = [
                    {"table": row.table_name, "size": row.size} for row in rows
                ]
                maintenance_results["table_sizes"] = table_sizes

                await session.commit()

                logger.info("数据库维护完成")

                return maintenance_results

        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.error(f"数据库维护失败: {str(e)}")
            raise e

    try:
        maintenance_results = asyncio.run(_run_database_maintenance())

        return {
            "status": "success",
            "maintenance_results": maintenance_results,
            "execution_time": datetime.now().isoformat(),
        }

    except (RuntimeError, ValueError, ConnectionError) as exc:
        logger.error(f"数据库维护任务失败: {str(exc)}")
        return {
            "status": "failed",
            "error": str(exc),
            "execution_time": datetime.now().isoformat(),
        }
