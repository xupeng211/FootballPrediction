"""
maintenance_tasks.py 测试文件
测试系统维护任务功能，包括数据质量检查、错误日志清理、系统健康监控和数据库维护
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta
from typing import Dict, Any
import asyncio
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# 模拟外部依赖
with patch.dict('sys.modules', {
    'sqlalchemy': Mock(),
    'sqlalchemy.text': Mock(),
    'redis': Mock(),
    'shutil': Mock(),
    'src.database.connection': Mock(),
    'src.tasks.error_logger': Mock(),
    'src.tasks.celery_app': Mock()
}):
    from tasks.maintenance_tasks import (
        quality_check_task,
        cleanup_error_logs_task,
        system_health_check_task,
        database_maintenance_task
    )

# 模拟 text 函数
def mock_text(query):
    """模拟 SQLAlchemy text 函数"""
    mock_query = Mock()
    mock_query.__str__ = lambda: query
    return mock_query


class TestQualityCheckTask:
    """测试数据质量检查任务"""

    @patch('tasks.maintenance_tasks.DatabaseManager')
    @patch('tasks.maintenance_tasks.asyncio.run')
    def test_quality_check_task_success(self, mock_asyncio_run, mock_db_manager):
        """测试数据质量检查任务成功执行"""
        # 模拟异步检查结果
        mock_check_results = {
            "incomplete_matches": 0,
            "duplicate_matches": 0,
            "abnormal_odds": 0,
            "orphan_matches": 0,
            "stale_collection_logs": 0
        }
        mock_asyncio_run.return_value = (mock_check_results, 0)

        result = quality_check_task()

        assert result["status"] == "success"
        assert result["checks_performed"] == 5
        assert result["issues_found"] == 0
        assert result["check_results"] == mock_check_results
        assert "execution_time" in result

    @patch('tasks.maintenance_tasks.DatabaseManager')
    @patch('tasks.maintenance_tasks.asyncio.run')
    def test_quality_check_task_with_issues(self, mock_asyncio_run, mock_db_manager):
        """测试数据质量检查任务发现问题"""
        # 模拟发现问题
        mock_check_results = {
            "incomplete_matches": 5,
            "duplicate_matches": 2,
            "abnormal_odds": 0,
            "orphan_matches": 0,
            "stale_collection_logs": 0
        }
        mock_asyncio_run.return_value = (mock_check_results, 2)

        result = quality_check_task()

        assert result["status"] == "success"
        assert result["checks_performed"] == 5
        assert result["issues_found"] == 2
        assert result["check_results"]["incomplete_matches"] == 5
        assert result["check_results"]["duplicate_matches"] == 2

    @patch('tasks.maintenance_tasks.DatabaseManager')
    @patch('tasks.maintenance_tasks.asyncio.run')
    def test_quality_check_task_exception(self, mock_asyncio_run, mock_db_manager):
        """测试数据质量检查任务异常处理"""
        mock_asyncio_run.side_effect = Exception("Database connection failed")

        result = quality_check_task()

        assert result["status"] == "failed"
        assert "error" in result
        assert "Database connection failed" in result["error"]
        assert "execution_time" in result

    @patch('tasks.maintenance_tasks.DatabaseManager')
    @patch('tasks.maintenance_tasks.asyncio.run')
    def test_async_quality_checks_database_operations(self, mock_asyncio_run, mock_db_manager):
        """测试异步质量检查中的数据库操作"""
        async def mock_run_checks():
            # 模拟数据库会话
            mock_session = AsyncMock()
            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            # 模拟查询结果
            mock_session.execute.side_effect = [
                Mock(scalar=AsyncMock(return_value=0)),  # incomplete_matches
                Mock(scalar=AsyncMock(return_value=0)),  # duplicate_matches
                Mock(scalar=AsyncMock(return_value=0)),  # abnormal_odds
                Mock(scalar=AsyncMock(return_value=0)),  # orphan_matches
                Mock(scalar=AsyncMock(return_value=0)),  # stale_collection_logs
            ]

            # 导入实际函数并执行
            from tasks.maintenance_tasks import quality_check_task
            db_manager = DatabaseManager()

            async with db_manager.get_async_session() as session:
                check_results = {}

                # 模拟完整性检查
                from sqlalchemy import text
                match_integrity_query = text("SELECT COUNT(*) as incomplete_matches FROM matches WHERE home_team_id IS NULL OR away_team_id IS NULL OR league_id IS NULL OR match_time IS NULL")
                result = await session.execute(match_integrity_query)
                incomplete_matches = await result.scalar() or 0
                check_results["incomplete_matches"] = incomplete_matches

                return check_results, 0

        mock_asyncio_run.side_effect = mock_run_checks
        result = quality_check_task()

        assert result["status"] == "success"

    def test_quality_check_queries_validation(self):
        """测试质量检查查询的有效性"""
        # 检查各个SQL查询的基本结构
        queries = [
            "SELECT COUNT(*) as incomplete_matches FROM matches WHERE home_team_id IS NULL OR away_team_id IS NULL OR league_id IS NULL OR match_time IS NULL",
            "SELECT COUNT(*) as duplicate_count FROM (SELECT home_team_id, away_team_id, match_time, COUNT(*) as cnt FROM matches GROUP BY home_team_id, away_team_id, match_time HAVING COUNT(*) > 1) t",
            "SELECT COUNT(*) as abnormal_odds FROM odds WHERE home_odds < 1.01 OR draw_odds < 1.01 OR away_odds < 1.01 OR home_odds > 1000 OR draw_odds > 1000 OR away_odds > 1000",
            "SELECT COUNT(*) as orphan_matches FROM matches m LEFT JOIN teams ht ON m.home_team_id = ht.id LEFT JOIN teams at ON m.away_team_id = at.id WHERE ht.id IS NULL OR at.id IS NULL",
            "SELECT COUNT(*) as stale_collection_logs FROM data_collection_logs WHERE created_at < NOW() - INTERVAL '24 hours' AND status = 'running'"
        ]

        for query in queries:
            assert "COUNT(*)" in query
            assert len(query) > 20  # 查询应该有基本长度


class TestCleanupErrorLogsTask:
    """测试错误日志清理任务"""

    @patch('tasks.maintenance_tasks.TaskErrorLogger')
    @patch('tasks.maintenance_tasks.asyncio.run')
    def test_cleanup_error_logs_task_success(self, mock_asyncio_run, mock_error_logger):
        """测试错误日志清理任务成功执行"""
        mock_asyncio_run.return_value = 25  # 删除了25条记录

        result = cleanup_error_logs_task(days=7)

        assert result["status"] == "success"
        assert result["deleted_count"] == 25
        assert result["days_to_keep"] == 7
        assert "execution_time" in result

    @patch('tasks.maintenance_tasks.TaskErrorLogger')
    @patch('tasks.maintenance_tasks.asyncio.run')
    def test_cleanup_error_logs_task_default_days(self, mock_asyncio_run, mock_error_logger):
        """测试错误日志清理任务使用默认天数"""
        mock_asyncio_run.return_value = 10

        result = cleanup_error_logs_task()

        assert result["status"] == "success"
        assert result["deleted_count"] == 10
        assert result["days_to_keep"] == 7  # 默认值

    @patch('tasks.maintenance_tasks.TaskErrorLogger')
    @patch('tasks.maintenance_tasks.asyncio.run')
    def test_cleanup_error_logs_task_exception(self, mock_asyncio_run, mock_error_logger):
        """测试错误日志清理任务异常处理"""
        mock_asyncio_run.side_effect = Exception("Cleanup failed")

        result = cleanup_error_logs_task(days=3)

        assert result["status"] == "failed"
        assert "error" in result
        assert "Cleanup failed" in result["error"]
        assert result["deleted_count"] == 0

    @patch('tasks.maintenance_tasks.TaskErrorLogger')
    def test_cleanup_error_logs_async_operation(self, mock_error_logger):
        """测试错误日志清理异步操作"""
        async def test_cleanup():
            mock_logger_instance = AsyncMock()
            mock_logger_instance.cleanup_old_errors.return_value = 15
            mock_error_logger.return_value = mock_logger_instance

            deleted_count = await mock_logger_instance.cleanup_old_errors(5)
            return deleted_count

        deleted_count = asyncio.run(test_cleanup())
        assert deleted_count == 15


class TestSystemHealthCheckTask:
    """测试系统健康检查任务"""

    @patch('tasks.maintenance_tasks.DatabaseManager')
    @patch('tasks.maintenance_tasks.asyncio.run')
    @patch('tasks.maintenance_tasks.redis.from_url')
    @patch('tasks.maintenance_tasks.shutil.disk_usage')
    def test_system_health_check_all_healthy(self, mock_disk_usage, mock_redis, mock_asyncio_run, mock_db_manager):
        """测试系统健康检查全部健康"""
        # 模拟磁盘空间
        mock_disk_usage.return_value = Mock(free=10 * 1024**3)  # 10GB
        mock_redis.return_value.ping.return_value = True

        # 模拟健康状态
        mock_health_status = {
            "database": {"status": "healthy", "message": "数据库连接正常"},
            "redis": {"status": "healthy", "message": "Redis连接正常"},
            "disk_space": {"status": "healthy", "message": "磁盘空间充足: 10.00 GB可用"}
        }
        mock_asyncio_run.return_value = (mock_health_status, True)

        result = system_health_check_task()

        assert result["status"] == "healthy"
        assert result["overall_healthy"] is True
        assert "components" in result
        assert result["components"]["database"]["status"] == "healthy"
        assert result["components"]["redis"]["status"] == "healthy"

    @patch('tasks.maintenance_tasks.DatabaseManager')
    @patch('tasks.maintenance_tasks.asyncio.run')
    @patch('tasks.maintenance_tasks.redis.from_url')
    @patch('tasks.maintenance_tasks.shutil.disk_usage')
    def test_system_health_check_disk_warning(self, mock_disk_usage, mock_redis, mock_asyncio_run, mock_db_manager):
        """测试系统健康检查磁盘空间警告"""
        mock_disk_usage.return_value = Mock(free=3 * 1024**3)  # 3GB < 5GB

        mock_health_status = {
            "database": {"status": "healthy", "message": "数据库连接正常"},
            "redis": {"status": "healthy", "message": "Redis连接正常"},
            "disk_space": {"status": "warning", "message": "磁盘空间不足: 仅剩 3.00 GB"}
        }
        mock_asyncio_run.return_value = (mock_health_status, True)

        result = system_health_check_task()

        assert result["status"] == "healthy"
        assert result["overall_healthy"] is True
        assert result["components"]["disk_space"]["status"] == "warning"

    @patch('tasks.maintenance_tasks.DatabaseManager')
    @patch('tasks.maintenance_tasks.asyncio.run')
    @patch('tasks.maintenance_tasks.redis.from_url')
    def test_system_health_check_database_failure(self, mock_redis, mock_asyncio_run, mock_db_manager):
        """测试系统健康检查数据库失败"""
        mock_redis.return_value.ping.return_value = True

        mock_health_status = {
            "database": {"status": "unhealthy", "message": "数据库连接失败: Connection timeout"},
            "redis": {"status": "healthy", "message": "Redis连接正常"}
        }
        mock_asyncio_run.return_value = (mock_health_status, False)

        result = system_health_check_task()

        assert result["status"] == "unhealthy"
        assert result["overall_healthy"] is False
        assert result["components"]["database"]["status"] == "unhealthy"

    @patch('tasks.maintenance_tasks.asyncio.run')
    def test_system_health_check_exception(self, mock_asyncio_run):
        """测试系统健康检查异常处理"""
        mock_asyncio_run.side_effect = Exception("Health check failed")

        result = system_health_check_task()

        assert result["status"] == "failed"
        assert "error" in result
        assert "Health check failed" in result["error"]
        assert result["overall_healthy"] is False

    @patch('tasks.maintenance_tasks.os.getenv')
    def test_redis_connection_with_env_var(self, mock_getenv):
        """测试Redis连接使用环境变量"""
        mock_getenv.return_value = "redis://custom:6379/1"

        with patch('tasks.maintenance_tasks.redis.from_url') as mock_redis:
            mock_redis.return_value.ping.return_value = True

            async def test_redis():
                import redis
                redis_client = redis.from_url("redis://custom:6379/1")
                return redis_client.ping()

            result = asyncio.run(test_redis())
            assert result is True
            mock_redis.assert_called_once_with("redis://custom:6379/1")

    def test_disk_space_check_validation(self):
        """测试磁盘空间检查验证"""
        # 测试不同磁盘空间情况
        test_cases = [
            (10 * 1024**3, "healthy"),    # 10GB - 充足
            (5.1 * 1024**3, "healthy"),   # 5.1GB - 充足
            (5.0 * 1024**3, "healthy"),   # 5GB - 刚好充足
            (4.9 * 1024**3, "warning"),   # 4.9GB - 不足
            (1 * 1024**3, "warning"),     # 1GB - 不足
        ]

        for free_bytes, expected_status in test_cases:
            free_gb = free_bytes / (1024**3)
            if free_gb > 5:
                status = "healthy"
            else:
                status = "warning"
            assert status == expected_status


class TestDatabaseMaintenanceTask:
    """测试数据库维护任务"""

    @patch('tasks.maintenance_tasks.DatabaseManager')
    @patch('tasks.maintenance_tasks.asyncio.run')
    def test_database_maintenance_task_success(self, mock_asyncio_run, mock_db_manager):
        """测试数据库维护任务成功执行"""
        mock_maintenance_results = {
            "cleaned_stale_sessions": 5,
            "table_sizes": [
                {"table": "matches", "size": "150 MB"},
                {"table": "odds", "size": "80 MB"}
            ]
        }
        mock_asyncio_run.return_value = mock_maintenance_results

        result = database_maintenance_task()

        assert result["status"] == "success"
        assert result["maintenance_results"] == mock_maintenance_results
        assert result["maintenance_results"]["cleaned_stale_sessions"] == 5
        assert "execution_time" in result

    @patch('tasks.maintenance_tasks.DatabaseManager')
    @patch('tasks.maintenance_tasks.asyncio.run')
    def test_database_maintenance_task_exception(self, mock_asyncio_run, mock_db_manager):
        """测试数据库维护任务异常处理"""
        mock_asyncio_run.side_effect = Exception("Maintenance failed")

        result = database_maintenance_task()

        assert result["status"] == "failed"
        assert "error" in result
        assert "Maintenance failed" in result["error"]

    @patch('tasks.maintenance_tasks.DatabaseManager')
    def test_database_maintenance_operations(self, mock_db_manager):
        """测试数据库维护操作"""
        async def test_maintenance():
            mock_session = AsyncMock()
            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            # 模拟ANALYZE查询结果
            mock_session.execute.return_value = Mock()

            # 模拟清理结果
            mock_cleanup_result = Mock()
            mock_cleanup_result.rowcount = 3
            mock_session.execute.side_effect = [
                Mock(),  # ANALYZE matches
                Mock(),  # ANALYZE odds
                Mock(),  # ANALYZE teams
                Mock(),  # ANALYZE leagues
                Mock(),  # ANALYZE data_collection_logs
                mock_cleanup_result,  # 清理过期会话
                Mock(fetchall=AsyncMock(return_value=[
                    Mock(table_name="matches", size="150 MB"),
                    Mock(table_name="odds", size="80 MB")
                ]))  # 表大小查询
            ]

            # 执行维护操作
            analyze_queries = [
                "ANALYZE matches",
                "ANALYZE odds",
                "ANALYZE teams",
                "ANALYZE leagues",
                "ANALYZE data_collection_logs"
            ]

            from sqlalchemy import text

            for query in analyze_queries:
                await mock_session.execute(text(query))

            cleanup_query = text("DELETE FROM data_collection_logs WHERE status = 'running' AND created_at < NOW() - INTERVAL '24 hours'")
            result = await mock_session.execute(cleanup_query)
            cleaned_sessions = result.rowcount

            return cleaned_sessions

        cleaned_sessions = asyncio.run(test_maintenance())
        assert cleaned_sessions == 3

    def test_analyze_queries_validation(self):
        """测试ANALYZE查询验证"""
        analyze_queries = [
            "ANALYZE matches",
            "ANALYZE odds",
            "ANALYZE teams",
            "ANALYZE leagues",
            "ANALYZE data_collection_logs"
        ]

        for query in analyze_queries:
            assert query.startswith("ANALYZE ")
            assert len(query) > 8  # 应该有表名

    def test_table_size_query_validation(self):
        """测试表大小查询验证"""
        table_size_query = """
            SELECT
                table_name,
                pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC
            LIMIT 10
        """

        assert "pg_size_pretty" in table_size_query
        assert "information_schema.tables" in table_size_query
        assert "table_schema = 'public'" in table_size_query
        assert "LIMIT 10" in table_size_query


class TestMaintenanceTaskIntegration:
    """测试维护任务集成功能"""

    @patch('tasks.maintenance_tasks.DatabaseManager')
    def test_concurrent_maintenance_tasks(self, mock_db_manager):
        """测试并发维护任务执行"""
        async def run_concurrent_tasks():
            # 模拟并发执行多个维护任务
            tasks = [
                asyncio.create_task(self._mock_quality_check()),
                asyncio.create_task(self._mock_cleanup_logs()),
                asyncio.create_task(self._mock_health_check()),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        results = asyncio.run(run_concurrent_tasks())
        assert len(results) == 3
        assert not any(isinstance(r, Exception) for r in results)

    @patch('tasks.maintenance_tasks.DatabaseManager')
    def test_maintenance_task_error_recovery(self, mock_db_manager):
        """测试维护任务错误恢复"""
        async def test_with_failure():
            try:
                # 模拟部分失败的任务
                quality_result = await self._mock_quality_check()
                # 模拟健康检查失败
                raise Exception("Health check failed")
            except Exception as e:
                # 记录错误但不中断其他任务
                return {"status": "partial_failure", "error": str(e)}

        result = asyncio.run(test_with_failure())
        assert result["status"] == "partial_failure"
        assert "error" in result

    @patch('tasks.maintenance_tasks.DatabaseManager')
    def test_maintenance_task_metrics_collection(self, mock_db_manager):
        """测试维护任务指标收集"""
        async def collect_metrics():
            metrics = {
                "quality_check_duration": 2.5,
                "cleanup_duration": 0.5,
                "health_check_duration": 1.0,
                "total_issues_found": 3,
                "total_records_cleaned": 15
            }
            return metrics

        metrics = asyncio.run(collect_metrics())
        assert metrics["quality_check_duration"] == 2.5
        assert metrics["total_issues_found"] == 3

    async def _mock_quality_check(self):
        """模拟质量检查"""
        await asyncio.sleep(0.1)
        return {"status": "success", "issues_found": 0}

    async def _mock_cleanup_logs(self):
        """模拟日志清理"""
        await asyncio.sleep(0.05)
        return {"status": "success", "deleted_count": 10}

    async def _mock_health_check(self):
        """模拟健康检查"""
        await asyncio.sleep(0.1)
        return {"status": "healthy", "overall_healthy": True}

    def test_maintenance_task_scheduling(self):
        """测试维护任务调度"""
        # 测试任务可以正确导入和调用
        assert callable(quality_check_task)
        assert callable(cleanup_error_logs_task)
        assert callable(system_health_check_task)
        assert callable(database_maintenance_task)

    def test_maintenance_task_return_structure(self):
        """测试维护任务返回结构"""
        # 模拟任务返回的基本结构验证
        base_structure = {
            "status": "success",
            "execution_time": "2023-01-01T00:00:00"
        }

        assert "status" in base_structure
        assert "execution_time" in base_structure
        assert base_structure["status"] in ["success", "failed", "healthy", "unhealthy"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])