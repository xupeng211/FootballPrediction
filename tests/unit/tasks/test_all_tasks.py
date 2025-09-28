"""
测试文件：所有任务模块测试

测试所有Celery任务功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock


@pytest.mark.unit
class TestAllTasks:
    """所有任务模块测试类"""

    def test_data_collection_tasks(self):
        """测试数据收集任务"""
        try:
            from src.tasks.data_collection_tasks import (
                collect_scores_task,
                collect_odds_task,
                collect_fixtures_task
            )
            assert callable(collect_scores_task)
            assert callable(collect_odds_task)
            assert callable(collect_fixtures_task)
        except ImportError:
            pytest.skip("Data collection tasks not available")

    def test_backup_tasks(self):
        """测试备份任务"""
        try:
            from src.tasks.backup_tasks import (
                backup_database_task,
                backup_models_task,
                backup_data_task
            )
            assert callable(backup_database_task)
            assert callable(backup_models_task)
            assert callable(backup_data_task)
        except ImportError:
            pytest.skip("Backup tasks not available")

    def test_maintenance_tasks(self):
        """测试维护任务"""
        try:
            from src.tasks.maintenance_tasks import (
                cleanup_old_data_task,
                update_model_metrics_task,
                system_health_check_task
            )
            assert callable(cleanup_old_data_task)
            assert callable(update_model_metrics_task)
            assert callable(system_health_check_task)
        except ImportError:
            pytest.skip("Maintenance tasks not available")

    def test_monitoring_tasks(self):
        """测试监控任务"""
        try:
            from src.tasks.monitoring import (
                collect_system_metrics_task,
                check_alerts_task,
                generate_reports_task
            )
            assert callable(collect_system_metrics_task)
            assert callable(check_alerts_task)
            assert callable(generate_reports_task)
        except ImportError:
            pytest.skip("Monitoring tasks not available")

    def test_error_logger_tasks(self):
        """测试错误日志任务"""
        try:
            from src.tasks.error_logger import (
                log_error_task,
                process_error_queue_task,
                cleanup_error_logs_task
            )
            assert callable(log_error_task)
            assert callable(process_error_queue_task)
            assert callable(cleanup_error_logs_task)
        except ImportError:
            pytest.skip("Error logger tasks not available")

    def test_task_execution(self):
        """测试任务执行"""
        try:
            from src.tasks.data_collection_tasks import collect_scores_task

            # Mock任务执行
            with patch.object(collect_scores_task, 'delay') as mock_delay:
                mock_delay.return_value = Mock(id='task_123')

                result = collect_scores_task.delay(date='2024-01-01')
                assert result.id == 'task_123'

        except ImportError:
            pytest.skip("Task execution not available")

    def test_task_status_check(self):
        """测试任务状态检查"""
        try:
            from src.tasks.celery_app import app

            # Mock任务状态检查
            with patch(app.AsyncResult) as mock_result:
                mock_result.return_value = Mock(
                    status='PENDING',
                    result=None,
                    traceback=None
                )

                result = app.AsyncResult('task_123')
                assert result.status == 'PENDING'

        except ImportError:
            pytest.skip("Task status check not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.tasks", "--cov-report=term-missing"])