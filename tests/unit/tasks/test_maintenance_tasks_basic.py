"""
maintenance_tasks模块的基本测试
主要测试维护任务的基本功能以提升测试覆盖率
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tasks.maintenance_tasks import (cleanup_error_logs_task,
                                         database_maintenance_task,
                                         quality_check_task,
                                         system_health_check_task)


@pytest.fixture
def mock_db_manager():
    with patch("src.tasks.maintenance_tasks.DatabaseManager") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        yield mock_db, mock_session


class TestQualityCheckTask:
    def test_quality_check_success(self, mock_db_manager):
        mock_db, mock_session = mock_db_manager
        # 修复异步mock返回值
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        result = quality_check_task.run()

        assert result["status"] == "success"
        assert result["issues_found"] == 0
        assert len(result["check_results"]) == 5

    def test_quality_check_with_issues(self, mock_db_manager):
        mock_db, mock_session = mock_db_manager
        # 修复异步mock返回值
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        result = quality_check_task.run()

        assert result["status"] == "success"
        assert result["issues_found"] == 5

    def test_quality_check_db_error(self, mock_db_manager):
        mock_db, mock_session = mock_db_manager
        mock_session.execute.side_effect = Exception("DB Error")

        result = quality_check_task.run()

        assert result["status"] == "failed"
        assert "DB Error" in result["error"]


class TestCleanupErrorLogsTask:
    @patch("src.tasks.maintenance_tasks.TaskErrorLogger")
    def test_cleanup_success(self, mock_error_logger):
        mock_logger_instance = AsyncMock()
        mock_logger_instance.cleanup_old_errors.return_value = 10
        mock_error_logger.return_value = mock_logger_instance

        result = cleanup_error_logs_task.run(days=7)

        assert result["status"] == "success"
        assert result["deleted_count"] == 10
        mock_logger_instance.cleanup_old_errors.assert_called_once_with(7)

    @patch("src.tasks.maintenance_tasks.TaskErrorLogger")
    def test_cleanup_failure(self, mock_error_logger):
        mock_error_logger.return_value.cleanup_old_errors.side_effect = Exception(
            "Cleanup Failed"
        )

        result = cleanup_error_logs_task.run(days=7)

        assert result["status"] == "failed"
        assert "Cleanup Failed" in result["error"]


class TestSystemHealthCheckTask:
    @patch("shutil.disk_usage")
    @patch("redis.from_url")
    def test_health_check_all_healthy(
        self, mock_redis_from_url, mock_disk_usage, mock_db_manager
    ):
        mock_db, mock_session = mock_db_manager
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client
        mock_disk_usage.return_value.free = 10 * (1024**3)  # 10 GB

        result = system_health_check_task.run()

        assert result["status"] == "healthy"
        assert result["overall_healthy"] is True
        assert result["components"]["database"]["status"] == "healthy"
        assert result["components"]["redis"]["status"] == "healthy"
        assert result["components"]["disk_space"]["status"] == "healthy"

    @patch("shutil.disk_usage")
    @patch("redis.from_url")
    def test_health_check_db_unhealthy(
        self, mock_redis_from_url, mock_disk_usage, mock_db_manager
    ):
        mock_db, mock_session = mock_db_manager
        mock_session.execute.side_effect = Exception("DB Down")
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client
        mock_disk_usage.return_value.free = 10 * (1024**3)

        result = system_health_check_task.run()

        assert result["status"] == "unhealthy"
        assert result["overall_healthy"] is False
        assert result["components"]["database"]["status"] == "unhealthy"


class TestDatabaseMaintenanceTask:
    def test_maintenance_success(self, mock_db_manager):
        mock_db, mock_session = mock_db_manager

        # 创建mock结果对象，支持rowcount和fetchall
        mock_result = AsyncMock()
        mock_result.rowcount = 5

        mock_row = MagicMock()
        mock_row.table_name = "matches"
        mock_row.size = "10 MB"
        mock_result.fetchall.return_value = [mock_row]

        mock_session.execute.return_value = mock_result

        result = database_maintenance_task.run()

        assert result["status"] == "success"
        assert "table_sizes" in result["maintenance_results"]
        mock_session.commit.assert_called_once()

    def test_maintenance_db_error(self, mock_db_manager):
        mock_db, mock_session = mock_db_manager
        mock_session.execute.side_effect = Exception("Analyze Failed")

        result = database_maintenance_task.run()

        assert result["status"] == "failed"
        assert "Analyze Failed" in result["error"]
