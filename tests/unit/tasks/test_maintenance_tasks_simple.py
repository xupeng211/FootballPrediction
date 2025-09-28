"""
maintenance_tasks模块的简化测试
主要测试维护任务的基本功能以提升测试覆盖率
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

pytestmark = pytest.mark.unit


class TestMaintenanceTasksSimple:
    """测试维护任务 - 简化版本"""

    @pytest.mark.parametrize("issue_count,expected_status", [
        (0, "success"),
        (1, "success"),
        (5, "success"),
        (10, "success")
    ])
    @patch('src.tasks.maintenance_tasks.DatabaseManager')
    def test_quality_check_parametrized(self, mock_db_manager, issue_count, expected_status):
        """参数化测试质量检查功能"""
        # Mock database manager
        mock_session = AsyncMock()
        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalar.return_value = issue_count
        mock_session.execute.return_value = mock_result

        # Import and test
        from src.tasks.maintenance_tasks import quality_check_task

        result = quality_check_task.run()

        # Verify structure
        assert isinstance(result, dict)
        assert result["status"] == expected_status
        assert "issues_found" in result
        assert "check_results" in result
        assert isinstance(result["check_results"], dict)

    @patch('src.tasks.maintenance_tasks.DatabaseManager')
    def test_quality_check_database_error(self, mock_db_manager):
        """测试质量检查数据库错误处理"""
        # Mock database manager to raise exception
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database connection failed")
        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        # Import and test
        from src.tasks.maintenance_tasks import quality_check_task

        result = quality_check_task.run()

        # Verify error handling
        assert isinstance(result, dict)
        assert result["status"] == "failed"
        assert "error" in result
        assert "Database connection failed" in result["error"]

    @pytest.mark.parametrize("days,deleted_count,expected_status", [
        (1, 5, "success"),
        (7, 10, "success"),
        (30, 25, "success"),
        (365, 100, "success"),
        (0, 0, "success"),  # Edge case: 0 days
        (-1, 0, "failed")  # Edge case: negative days
    ])
    @patch('src.tasks.maintenance_tasks.TaskErrorLogger')
    def test_cleanup_error_logs_parametrized(self, mock_error_logger, days, deleted_count, expected_status):
        """参数化测试清理错误日志功能"""
        # Mock error logger
        mock_logger_instance = AsyncMock()
        if expected_status == "failed":
            mock_logger_instance.cleanup_old_errors.side_effect = ValueError("Invalid days parameter")
        else:
            mock_logger_instance.cleanup_old_errors.return_value = deleted_count
        mock_error_logger.return_value = mock_logger_instance

        # Import and test
        from src.tasks.maintenance_tasks import cleanup_error_logs_task

        result = cleanup_error_logs_task.run(days=days)

        # Verify structure
        assert isinstance(result, dict)
        assert result["status"] == expected_status
        assert "deleted_count" in result
        if expected_status == "success":
            assert result["deleted_count"] == deleted_count
        else:
            assert "error" in result

    @pytest.mark.parametrize("disk_free_gb,redis_healthy,db_healthy,expected_overall", [
        (10, True, True, True),
        (1, True, True, True),    # Low disk space but above 5GB threshold
        (4, True, True, True),   # Below 5GB threshold but only warning, not failure
        (10, False, True, False),  # Redis unhealthy
        (10, True, False, False),  # Database unhealthy
        (0.5, False, False, False), # All unhealthy
        (100, True, True, True)   # Plenty of space
    ])
    @patch('src.tasks.maintenance_tasks.DatabaseManager')
    @patch('shutil.disk_usage')
    @patch('redis.from_url')
    def test_system_health_check_parametrized(self, mock_redis, mock_disk, mock_db,
                                              disk_free_gb, redis_healthy, db_healthy, expected_overall):
        """参数化测试系统健康检查功能"""
        # Mock database
        mock_session = AsyncMock()
        if db_healthy:
            mock_session.execute.return_value = AsyncMock()
        else:
            mock_session.execute.side_effect = Exception("Database down")
        mock_db.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        # Mock Redis
        mock_redis_client = MagicMock()
        if redis_healthy:
            mock_redis_client.ping.return_value = True
        else:
            mock_redis_client.ping.side_effect = Exception("Redis connection failed")
        mock_redis.return_value = mock_redis_client

        # Mock disk usage
        mock_disk.return_value.free = disk_free_gb * (1024**3)

        # Import and test
        from src.tasks.maintenance_tasks import system_health_check_task

        result = system_health_check_task.run()

        # Verify structure
        assert isinstance(result, dict)
        assert "status" in result
        assert result["overall_healthy"] == expected_overall
        assert "components" in result
        assert len(result["components"]) >= 3  # database, redis, disk_space

    @patch('src.tasks.maintenance_tasks.DatabaseManager')
    def test_database_maintenance_basic_functionality(self, mock_db_manager):
        """测试数据库维护基本功能"""
        # Mock database manager
        mock_session = AsyncMock()
        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        # Mock result
        mock_result = AsyncMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        # Import and test
        from src.tasks.maintenance_tasks import database_maintenance_task

        result = database_maintenance_task.run()

        # Verify structure
        assert isinstance(result, dict)
        assert "status" in result
        assert "maintenance_results" in result

    def test_task_imports(self):
        """测试任务导入"""
        from src.tasks.maintenance_tasks import (
            cleanup_error_logs_task,
            database_maintenance_task,
            quality_check_task,
            system_health_check_task,
        )

        # Verify all tasks are callable
        assert callable(cleanup_error_logs_task.run)
        assert callable(database_maintenance_task.run)
        assert callable(quality_check_task.run)
        assert callable(system_health_check_task.run)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])