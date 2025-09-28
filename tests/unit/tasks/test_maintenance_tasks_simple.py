"""
maintenance_tasks模块的简化测试
主要测试维护任务的基本功能以提升测试覆盖率
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

pytestmark = pytest.mark.unit


class TestMaintenanceTasksSimple:
    """测试维护任务 - 简化版本"""

    @patch('src.tasks.maintenance_tasks.DatabaseManager')
    def test_quality_check_basic_functionality(self, mock_db_manager):
        """测试质量检查基本功能"""
        # Mock database manager
        mock_session = AsyncMock()
        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        # Import and test
        from src.tasks.maintenance_tasks import quality_check_task

        result = quality_check_task.run()

        # Verify structure
        assert isinstance(result, dict)
        assert "status" in result
        assert "issues_found" in result
        assert "check_results" in result

    @patch('src.tasks.maintenance_tasks.TaskErrorLogger')
    def test_cleanup_error_logs_basic_functionality(self, mock_error_logger):
        """测试清理错误日志基本功能"""
        # Mock error logger
        mock_logger_instance = AsyncMock()
        mock_logger_instance.cleanup_old_errors.return_value = 10
        mock_error_logger.return_value = mock_logger_instance

        # Import and test
        from src.tasks.maintenance_tasks import cleanup_error_logs_task

        result = cleanup_error_logs_task.run(days=7)

        # Verify structure
        assert isinstance(result, dict)
        assert "status" in result
        assert "deleted_count" in result

    @patch('src.tasks.maintenance_tasks.DatabaseManager')
    @patch('shutil.disk_usage')
    @patch('redis.from_url')
    def test_system_health_check_basic_functionality(self, mock_redis, mock_disk, mock_db):
        """测试系统健康检查基本功能"""
        # Mock database
        mock_session = AsyncMock()
        mock_db.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        # Mock Redis
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis.return_value = mock_redis_client

        # Mock disk usage
        mock_disk.return_value.free = 10 * (1024**3)  # 10 GB

        # Import and test
        from src.tasks.maintenance_tasks import system_health_check_task

        result = system_health_check_task.run()

        # Verify structure
        assert isinstance(result, dict)
        assert "status" in result
        assert "overall_healthy" in result
        assert "components" in result

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