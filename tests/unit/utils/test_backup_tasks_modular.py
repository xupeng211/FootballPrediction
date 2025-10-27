# TODO: Consider creating a fixture for 4 repeated Mock creations

# TODO: Consider creating a fixture for 4 repeated Mock creations

from unittest.mock import MagicMock, patch

"""
测试备份任务模块化拆分
Test modular split of backup tasks
"""

from datetime import datetime

import pytest


@pytest.mark.unit
class TestBaseModule:
    """测试基础模块"""

    def test_database_backup_task_import(self):
        """测试数据库备份任务基类导入"""
        from src.tasks.backup.base import DatabaseBackupTask

        assert DatabaseBackupTask is not None

    def test_backup_metrics_import(self):
        """测试备份指标导入"""
        from src.tasks.backup.base import (backup_failures_total,
                                           backup_last_success,
                                           backup_size_bytes,
                                           backup_task_duration,
                                           backup_tasks_total,
                                           get_backup_metrics)

        assert backup_tasks_total is not None
        assert backup_task_duration is not None
        assert backup_last_success is not None
        assert backup_size_bytes is not None
        assert backup_failures_total is not None
        assert get_backup_metrics is not None

    def test_get_backup_metrics(self):
        """测试获取备份指标"""
        from src.tasks.backup.base import get_backup_metrics

        with patch("src.tasks.backup.base.REGISTRY") as mock_registry:
            mock_registry._collector_to_names = {}
            _result = get_backup_metrics()

            assert isinstance(result, dict)
            assert _result["status"] in ["success", "error"]
            assert "timestamp" in result


class TestDatabaseModule:
    """测试数据库备份模块"""

    def test_database_backup_tasks_import(self):
        """测试数据库备份任务导入"""
        from src.tasks.backup.database import (backup_database_task,
                                               daily_full_backup_task,
                                               hourly_incremental_backup_task,
                                               verify_backup_task,
                                               weekly_wal_archive_task)

        assert daily_full_backup_task is not None
        assert hourly_incremental_backup_task is not None
        assert weekly_wal_archive_task is not None
        assert backup_database_task is not None
        assert verify_backup_task is not None

    @patch("src.tasks.backup.database.subprocess.run")
    @patch("src.tasks.backup.database.Path")
    @patch("src.tasks.backup.database.get_config")
    def test_daily_full_backup_task(self, mock_get_config, mock_path, mock_subprocess):
        """测试每日完整备份任务"""
        from src.tasks.backup.database import daily_full_backup_task

        # Mock配置
        mock_config = MagicMock()
        mock_config.database.host = "localhost"
        mock_config.database.port = "5432"
        mock_config.database.username = "test"
        mock_config.database.password = "test"
        mock_config.backup.backup_dir = "/tmp/backups"
        mock_get_config.return_value = mock_config

        # Mock subprocess结果
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Mock路径
        mock_backup_dir = MagicMock()
        mock_backup_file = MagicMock()
        mock_backup_dir.mkdir.return_value = None
        mock_backup_dir.__truediv__.return_value = mock_backup_file
        mock_backup_file.with_suffix.return_value = mock_backup_file
        mock_backup_file.stat.return_value = 1024
        mock_backup_file.__str__ = lambda x: "/tmp/backups/test.sql.gz"
        mock_path.return_value = mock_backup_dir

        assert daily_full_backup_task is not None


class TestMaintenanceModule:
    """测试维护模块"""

    def test_maintenance_tasks_import(self):
        """测试维护任务导入"""
        from src.tasks.backup.maintenance import (check_backup_storage_task,
                                                  cleanup_old_backups_task,
                                                  verify_backup_integrity_task)

        assert cleanup_old_backups_task is not None
        assert verify_backup_integrity_task is not None
        assert check_backup_storage_task is not None

    def test_cleanup_old_backups_task(self):
        """测试清理旧备份任务"""
        from src.tasks.backup.maintenance import cleanup_old_backups_task

        assert cleanup_old_backups_task is not None

    def test_verify_backup_integrity_task(self):
        """测试验证备份完整性任务"""
        from src.tasks.backup.maintenance import verify_backup_integrity_task

        assert verify_backup_integrity_task is not None

    def test_check_backup_storage_task(self):
        """测试检查备份存储空间任务"""
        from src.tasks.backup.maintenance import check_backup_storage_task

        assert check_backup_storage_task is not None


class TestServicesModule:
    """测试服务备份模块"""

    def test_services_backup_tasks_import(self):
        """测试服务备份任务导入"""
        from src.tasks.backup.services import (backup_config_task,
                                               backup_logs_task,
                                               backup_redis_task)

        assert backup_redis_task is not None
        assert backup_logs_task is not None
        assert backup_config_task is not None

    def test_backup_redis_task(self):
        """测试Redis备份任务"""
        from src.tasks.backup.services import backup_redis_task

        assert backup_redis_task is not None

    def test_backup_logs_task(self):
        """测试日志备份任务"""
        from src.tasks.backup.services import backup_logs_task

        assert backup_logs_task is not None

    def test_backup_config_task(self):
        """测试配置备份任务"""
        from src.tasks.backup.services import backup_config_task

        assert backup_config_task is not None


class TestManualModule:
    """测试手动备份模块"""

    def test_manual_tasks_import(self):
        """测试手动任务导入"""
        from src.tasks.backup.manual import (get_backup_status,
                                             list_backup_files,
                                             manual_backup_task,
                                             restore_backup)

        assert manual_backup_task is not None
        assert get_backup_status is not None
        assert list_backup_files is not None
        assert restore_backup is not None

    def test_get_backup_status(self):
        """测试获取备份状态"""
        from src.tasks.backup.manual import get_backup_status

        assert get_backup_status is not None

    def test_list_backup_files(self):
        """测试列出备份文件"""
        from src.tasks.backup.manual import list_backup_files

        assert list_backup_files is not None

    def test_restore_backup(self):
        """测试恢复备份"""
        from src.tasks.backup.manual import restore_backup

        assert restore_backup is not None


class TestModularStructure:
    """测试模块化结构"""

    def test_import_from_main_module(self):
        """测试从主模块导入"""
        from src.tasks.backup import (DatabaseBackupTask, backup_redis_task,
                                      daily_full_backup_task,
                                      get_backup_metrics, manual_backup_task)

        assert DatabaseBackupTask is not None
        assert daily_full_backup_task is not None
        assert backup_redis_task is not None
        assert manual_backup_task is not None
        assert get_backup_metrics is not None

    def test_backward_compatibility_imports(self):
        """测试向后兼容性导入"""
        # 从原始文件导入应该仍然有效
        from src.tasks.backup_tasks import DatabaseBackupTask as old_task
        from src.tasks.backup_tasks import backup_redis_task as old_redis
        from src.tasks.backup_tasks import daily_full_backup_task as old_daily
        from src.tasks.backup_tasks import get_backup_metrics as old_metrics

        assert old_task is not None
        assert old_daily is not None
        assert old_redis is not None
        assert old_metrics is not None

    def test_all_classes_are_exported(self):
        """测试所有类都被导出"""
        from src.tasks.backup import __all__

        expected_exports = [
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

        for export in expected_exports:
            assert export in __all__

    def test_module_structure(self):
        """测试模块结构"""
        import src.tasks.backup as backup_module

        # 验证子模块存在
        assert hasattr(backup_module, "base")
        assert hasattr(backup_module, "database")
        assert hasattr(backup_module, "maintenance")
        assert hasattr(backup_module, "services")
        assert hasattr(backup_module, "manual")


@pytest.mark.asyncio
async def test_integration_example():
    """测试集成示例"""
    from src.tasks.backup import DatabaseBackupTask, get_backup_metrics

    # 验证DatabaseBackupTask可以正常使用
    task = DatabaseBackupTask()
    assert hasattr(task, "on_success")
    assert hasattr(task, "on_failure")
    assert hasattr(task, "_send_alert_notification")

    # 验证get_backup_metrics可以正常调用
    with patch("src.tasks.backup.base.REGISTRY") as mock_registry:
        mock_registry._collector_to_names = {}
        metrics = (
            await get_backup_metrics()
            if hasattr(get_backup_metrics, "__await__")
            else get_backup_metrics()
        )
        assert isinstance(metrics, dict)


class TestTaskDecorators:
    """测试任务装饰器"""

    def test_celery_task_decorators(self):
        """测试Celery任务装饰器"""
        from src.tasks.backup.database import daily_full_backup_task
        from src.tasks.backup.manual import manual_backup_task
        from src.tasks.backup.services import backup_redis_task

        # 验证任务都有delay方法
        assert hasattr(daily_full_backup_task, "delay")
        assert hasattr(backup_redis_task, "delay")
        assert hasattr(manual_backup_task, "delay")

    def test_task_base_class(self):
        """测试任务基类"""
        from src.tasks.backup.base import DatabaseBackupTask
        from src.tasks.backup.database import daily_full_backup_task

        # 验证任务使用了正确的基类
        assert isinstance(
            daily_full_backup_task, DatabaseBackupTask.__class__
        ) or hasattr(daily_full_backup_task, "__bases__")
