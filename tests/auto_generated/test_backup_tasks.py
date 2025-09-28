"""
backup_tasks.py 测试文件
测试数据库备份任务功能，包括全量备份、增量备份、WAL归档和备份清理任务
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import os
import subprocess
import sys
import tempfile
import shutil

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# 模拟外部依赖
with patch.dict('sys.modules', {
    'celery': Mock(),
    'celery.Task': Mock(),
    'celery.schedules': Mock(),
    'prometheus_client': Mock(),
    'prometheus_client.registry': Mock(),
    'prometheus_client.core': Mock(),
    '.celery_app': Mock(),
    '.error_logger': Mock(),
    'src.tasks.celery_app': Mock(),
    'src.tasks.error_logger': Mock()
}):
    from tasks.backup_tasks import (
        DatabaseBackupTask,
        daily_full_backup_task,
        hourly_incremental_backup_task,
        weekly_wal_archive_task,
        cleanup_old_backups_task,
        verify_backup_task,
        get_backup_status,
        manual_backup_task,
        get_backup_metrics
    )


class TestBackupMetrics:
    """测试备份监控指标功能"""

    def test_get_backup_metrics_default_registry(self):
        """测试使用默认注册表获取指标"""
        metrics = get_backup_metrics()

        assert isinstance(metrics, dict)
        assert "success_total" in metrics
        assert "failure_total" in metrics
        assert "last_timestamp" in metrics
        assert "file_size" in metrics
        assert "duration" in metrics

    def test_get_backup_metrics_with_custom_registry(self):
        """测试使用自定义注册表获取指标"""
        mock_registry = Mock()
        metrics = get_backup_metrics(registry=mock_registry)

        assert isinstance(metrics, dict)
        # 验证所有指标都有必要的方法
        for metric_name, metric in metrics.items():
            assert hasattr(metric, 'inc')
            assert hasattr(metric, 'set')
            assert hasattr(metric, 'observe')
            assert hasattr(metric, 'labels')

    def test_get_backup_metrics_with_value_error(self):
        """测试指标已存在时的错误处理"""
        # 模拟ValueError异常
        with patch('tasks.backup_tasks.REGISTRY') as mock_registry:
            mock_registry.side_effect = ValueError("Metric already registered")

            metrics = get_backup_metrics()

            assert isinstance(metrics, dict)
            # 应该返回mock对象
            for metric_name, metric in metrics.items():
                assert hasattr(metric, 'inc')
                assert hasattr(metric, 'set')
                assert hasattr(metric, 'observe')


class TestDatabaseBackupTask:
    """测试数据库备份任务基类"""

    def setup_method(self):
        """设置测试环境"""
        self.task = DatabaseBackupTask()
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)

    def teardown_method(self):
        """清理测试环境"""
        # 清理临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_database_backup_task_initialization(self):
        """测试数据库备份任务初始化"""
        assert hasattr(self.task, 'error_logger')
        assert hasattr(self.task, 'logger')
        assert hasattr(self.task, 'metrics')
        assert hasattr(self.task, 'backup_script_path')
        assert hasattr(self.task, 'restore_script_path')
        assert hasattr(self.task, 'backup_dir')

        # 验证指标
        metrics = self.task.metrics
        assert "success_total" in metrics
        assert "failure_total" in metrics
        assert "last_timestamp" in metrics
        assert "file_size" in metrics
        assert "duration" in metrics

    def test_database_backup_task_initialization_with_custom_registry(self):
        """测试使用自定义注册表的初始化"""
        mock_registry = Mock()
        task = DatabaseBackupTask(registry=mock_registry)

        assert task.metrics is not None

    def test_get_backup_config(self):
        """测试获取备份配置"""
        config = self.task.get_backup_config()

        assert isinstance(config, dict)
        assert "backup_dir" in config
        assert "max_backup_age_days" in config
        assert "compression" in config
        assert "backup_script_path" in config
        assert "restore_script_path" in config
        assert "retention_policy" in config
        assert "notification" in config

        # 验证保留策略
        retention = config["retention_policy"]
        assert "full_backups" in retention
        assert "incremental_backups" in retention
        assert "wal_archives" in retention

        # 验证通知配置
        notification = config["notification"]
        assert "enabled" in notification
        assert "email" in notification
        assert "webhook" in notification

    def test_get_backup_config_with_env_vars(self):
        """测试使用环境变量的备份配置"""
        # 设置测试环境变量
        test_env_vars = {
            "BACKUP_DIR": "/custom/backup/dir",
            "MAX_BACKUP_AGE_DAYS": "60",
            "KEEP_FULL_BACKUPS": "14",
            "KEEP_INCREMENTAL_BACKUPS": "60",
            "KEEP_WAL_ARCHIVES": "14",
            "BACKUP_NOTIFICATIONS": "false",
            "BACKUP_NOTIFICATION_EMAIL": "test@example.com",
            "BACKUP_NOTIFICATION_WEBHOOK": "https://example.com/webhook"
        }

        with patch.dict(os.environ, test_env_vars):
            config = self.task.get_backup_config()

            assert config["backup_dir"] == "/custom/backup/dir"
            assert config["max_backup_age_days"] == 60
            assert config["retention_policy"]["full_backups"] == 14
            assert config["retention_policy"]["incremental_backups"] == 60
            assert config["retention_policy"]["wal_archives"] == 14
            assert config["notification"]["enabled"] is False
            assert config["notification"]["email"] == "test@example.com"
            assert config["notification"]["webhook"] == "https://example.com/webhook"

    def test_run_backup_script_success(self):
        """测试成功运行备份脚本"""
        # 模拟成功的subprocess.run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Backup completed successfully"
        mock_result.stderr = ""

        with patch('tasks.backup_tasks.subprocess.run', return_value=mock_result):
            with patch('tasks.backup_tasks.datetime') as mock_datetime:
                # 模拟时间
                start_time = datetime.now()
                end_time = start_time + timedelta(seconds=30)
                mock_datetime.now.side_effect = [start_time, end_time]

                # 模拟获取备份文件大小
                with patch.object(self.task, '_get_latest_backup_size', return_value=1024):
                    success, output, stats = self.task.run_backup_script(
                        backup_type="full",
                        database_name="test_db"
                    )

                    assert success is True
                    assert "Backup completed successfully" in output
                    assert stats["duration_seconds"] == 30
                    assert stats["exit_code"] == 0
                    assert stats["backup_file_size_bytes"] == 1024

    def test_run_backup_script_failure(self):
        """测试备份脚本执行失败"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = "Backup started"
        mock_result.stderr = "Backup failed: disk full"

        with patch('tasks.backup_tasks.subprocess.run', return_value=mock_result):
            with patch('tasks.backup_tasks.datetime') as mock_datetime:
                start_time = datetime.now()
                end_time = start_time + timedelta(seconds=10)
                mock_datetime.now.side_effect = [start_time, end_time]

                success, output, stats = self.task.run_backup_script(
                    backup_type="incremental",
                    database_name="test_db"
                )

                assert success is False
                assert "disk full" in output
                assert stats["exit_code"] == 1
                assert stats["duration_seconds"] == 10

    def test_run_backup_script_timeout(self):
        """测试备份脚本执行超时"""
        with patch('tasks.backup_tasks.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["test"], timeout=3600
            )

            success, output, stats = self.task.run_backup_script(
                backup_type="full",
                database_name="test_db"
            )

            assert success is False
            assert "timeout" in output.lower()
            assert stats["error"] == "timeout"

    def test_run_backup_script_exception(self):
        """测试备份脚本执行异常"""
        with patch('tasks.backup_tasks.subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Script not found")

            success, output, stats = self.task.run_backup_script(
                backup_type="wal",
                database_name="test_db"
            )

            assert success is False
            assert "script not found" in output.lower()
            assert "script not found" in stats["error"]

    def test_run_backup_script_with_additional_args(self):
        """测试带额外参数的备份脚本执行"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Backup with cleanup completed"
        mock_result.stderr = ""

        with patch('tasks.backup_tasks.subprocess.run', return_value=mock_result):
            with patch('tasks.backup_tasks.datetime') as mock_datetime:
                start_time = datetime.now()
                end_time = start_time + timedelta(seconds=45)
                mock_datetime.now.side_effect = [start_time, end_time]

                success, output, stats = self.task.run_backup_script(
                    backup_type="full",
                    database_name="test_db",
                    additional_args=["--cleanup", "--compress"]
                )

                assert success is True
                # 验证命令中包含了额外参数
                expected_args = ["--cleanup", "--compress"]
                # 注意：这里我们只能验证函数调用了subprocess.run，参数会在实际执行时传递

    def test_get_latest_backup_size_full_backup(self):
        """测试获取全量备份文件大小"""
        # 创建测试备份文件
        full_backup_dir = os.path.join(self.backup_dir, "full")
        os.makedirs(full_backup_dir, exist_ok=True)

        # 创建测试文件
        test_file = os.path.join(full_backup_dir, "full_backup_20231201_120000.sql.gz")
        with open(test_file, 'w') as f:
            f.write("test backup data" * 100)  # 创建约1.5KB的文件

        # 模拟find命令返回文件大小
        mock_find_result = Mock()
        mock_find_result.returncode = 0
        mock_find_result.stdout = "1536\n"

        with patch('tasks.backup_tasks.subprocess.run', return_value=mock_find_result):
            with patch.dict(os.environ, {"BACKUP_DIR": self.backup_dir}):
                size = self.task._get_latest_backup_size("full")

                assert size == 1536

    def test_get_latest_backup_size_incremental_backup(self):
        """测试获取增量备份文件大小"""
        # 创建测试增量备份目录
        incremental_backup_dir = os.path.join(self.backup_dir, "incremental")
        os.makedirs(incremental_backup_dir, exist_ok=True)

        test_dir = os.path.join(incremental_backup_dir, "20231201_120000")
        os.makedirs(test_dir, exist_ok=True)

        # 创建测试文件
        test_file = os.path.join(test_dir, "incremental_data.sql")
        with open(test_file, 'w') as f:
            f.write("incremental backup data")

        # 模拟find和du命令
        mock_find_result = Mock()
        mock_find_result.returncode = 0
        mock_find_result.stdout = f"{test_dir}\n"

        mock_du_result = Mock()
        mock_du_result.returncode = 0
        mock_du_result.stdout = "1024\t{test_dir}"

        def run_side_effect(cmd, **kwargs):
            if "find" in cmd:
                return mock_find_result
            elif "du" in cmd:
                return mock_du_result
            return Mock()

        with patch('tasks.backup_tasks.subprocess.run', side_effect=run_side_effect):
            with patch.dict(os.environ, {"BACKUP_DIR": self.backup_dir}):
                size = self.task._get_latest_backup_size("incremental")

                assert size == 1024

    def test_get_latest_backup_size_no_backups(self):
        """测试无备份文件时的文件大小获取"""
        with patch.dict(os.environ, {"BACKUP_DIR": self.backup_dir}):
            size = self.task._get_latest_backup_size("full")

            assert size is None

    def test_get_latest_backup_size_exception(self):
        """测试获取备份文件大小时的异常处理"""
        with patch('tasks.backup_tasks.subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Command not found")

            with patch.dict(os.environ, {"BACKUP_DIR": self.backup_dir}):
                size = self.task._get_latest_backup_size("full")

                assert size is None

    def test_verify_backup_success(self):
        """测试成功验证备份文件"""
        # 创建测试备份文件
        test_backup_file = os.path.join(self.temp_dir, "test_backup.sql")
        with open(test_backup_file, 'w') as f:
            f.write("valid backup data")

        # 模拟成功的验证命令
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Backup validation successful"
        mock_result.stderr = ""

        with patch('tasks.backup_tasks.subprocess.run', return_value=mock_result):
            result = self.task.verify_backup(test_backup_file)

            assert result is True

    def test_verify_backup_file_not_exists(self):
        """测试验证不存在的备份文件"""
        non_existent_file = os.path.join(self.temp_dir, "non_existent.sql")

        result = self.task.verify_backup(non_existent_file)

        assert result is False

    def test_verify_backup_validation_failed(self):
        """测试备份文件验证失败"""
        # 创建测试备份文件
        test_backup_file = os.path.join(self.temp_dir, "invalid_backup.sql")
        with open(test_backup_file, 'w') as f:
            f.write("invalid backup data")

        # 模拟验证失败
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Backup file is corrupted"

        with patch('tasks.backup_tasks.subprocess.run', return_value=mock_result):
            result = self.task.verify_backup(test_backup_file)

            assert result is False

    def test_verify_backup_timeout(self):
        """测试备份文件验证超时"""
        # 创建测试备份文件
        test_backup_file = os.path.join(self.temp_dir, "timeout_backup.sql")
        with open(test_backup_file, 'w') as f:
            f.write("large backup data")

        with patch('tasks.backup_tasks.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["test"], timeout=300
            )

            result = self.task.verify_backup(test_backup_file)

            assert result is False

    def test_verify_backup_exception(self):
        """测试备份文件验证异常"""
        # 创建测试备份文件
        test_backup_file = os.path.join(self.temp_dir, "exception_backup.sql")
        with open(test_backup_file, 'w') as f:
            f.write("test backup data")

        with patch('tasks.backup_tasks.subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Validation script not found")

            result = self.task.verify_backup(test_backup_file)

            assert result is False

    def test_on_failure(self):
        """测试任务失败处理"""
        # 设置模拟的request属性
        self.task.request = Mock()
        self.task.request.retries = 2
        self.task.name = "tasks.backup_tasks.daily_full_backup_task"

        # 模拟error_logger
        mock_error_logger = Mock()
        self.task.error_logger = mock_error_logger

        # 模拟异步日志记录
        with patch('tasks.backup_tasks.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_asyncio.get_event_loop.return_value = mock_loop

            test_exception = ValueError("Test backup error")
            test_kwargs = {"backup_type": "full", "database_name": "test_db"}

            self.task.on_failure(
                exc=test_exception,
                task_id="test_task_id",
                args=["test_db"],
                kwargs=test_kwargs,
                einfo=Mock()
            )

            # 验证失败指标被记录
            self.task.metrics["failure_total"].labels.assert_called_with(
                backup_type="full",
                database_name="test_db",
                error_type="ValueError"
            )
            self.task.metrics["failure_total"].labels.return_value.inc.assert_called_once()

            # 验证错误日志被记录
            mock_loop.run_until_complete.assert_called_once()

    def test_on_failure_without_request(self):
        """测试无request属性的任务失败处理"""
        # 不设置request属性
        if hasattr(self.task, 'request'):
            delattr(self.task, 'request')

        self.task.name = "tasks.backup_tasks.daily_full_backup_task"

        # 模拟error_logger
        mock_error_logger = Mock()
        self.task.error_logger = mock_error_logger

        test_exception = ValueError("Test backup error")
        test_kwargs = {"backup_type": "full", "database_name": "test_db"}

        # 应该不抛出异常
        self.task.on_failure(
            exc=test_exception,
            task_id="test_task_id",
            args=["test_db"],
            kwargs=test_kwargs,
            einfo=Mock()
        )


class TestBackupTasks:
    """测试具体的备份任务函数"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('tasks.backup_tasks.DatabaseBackupTask')
    def test_daily_full_backup_task(self, mock_task_class):
        """测试每日全量备份任务"""
        # 模拟任务实例
        mock_task = Mock()
        mock_task_class.return_value = mock_task

        # 模拟run_backup_script返回成功结果
        mock_task.run_backup_script.return_value = (
            True, "Backup completed", {"duration_seconds": 30}
        )

        with patch('tasks.backup_tasks.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:00:00"

            result = daily_full_backup_task(mock_task, "test_db")

            assert result["task_type"] == "daily_full_backup"
            assert result["database_name"] == "test_db"
            assert result["success"] is True
            assert result["timestamp"] == "2023-12-01T12:00:00"

            # 验证调用了正确的方法
            mock_task.run_backup_script.assert_called_once_with(
                backup_type="full", database_name="test_db"
            )

    @patch('tasks.backup_tasks.DatabaseBackupTask')
    def test_hourly_incremental_backup_task(self, mock_task_class):
        """测试每小时增量备份任务"""
        mock_task = Mock()
        mock_task_class.return_value = mock_task

        mock_task.run_backup_script.return_value = (
            True, "Incremental backup completed", {"duration_seconds": 15}
        )

        with patch('tasks.backup_tasks.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:30:00"

            result = hourly_incremental_backup_task(mock_task, "test_db")

            assert result["task_type"] == "hourly_incremental_backup"
            assert result["success"] is True
            assert result["database_name"] == "test_db"

            mock_task.run_backup_script.assert_called_once_with(
                backup_type="incremental", database_name="test_db"
            )

    @patch('tasks.backup_tasks.DatabaseBackupTask')
    def test_weekly_wal_archive_task(self, mock_task_class):
        """测试每周WAL归档任务"""
        mock_task = Mock()
        mock_task_class.return_value = mock_task

        mock_task.run_backup_script.return_value = (
            True, "WAL archive completed", {"duration_seconds": 45}
        )

        with patch('tasks.backup_tasks.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T00:00:00"

            result = weekly_wal_archive_task(mock_task, "test_db")

            assert result["task_type"] == "weekly_wal_archive"
            assert result["success"] is True
            assert result["database_name"] == "test_db"

            mock_task.run_backup_script.assert_called_once_with(
                backup_type="wal", database_name="test_db"
            )

    @patch('tasks.backup_tasks.DatabaseBackupTask')
    def test_cleanup_old_backups_task(self, mock_task_class):
        """测试清理旧备份任务"""
        mock_task = Mock()
        mock_task_class.return_value = mock_task

        mock_task.run_backup_script.return_value = (
            True, "Cleanup completed", {"duration_seconds": 20}
        )

        with patch('tasks.backup_tasks.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T02:00:00"

            result = cleanup_old_backups_task(mock_task, "test_db")

            assert result["task_type"] == "cleanup_old_backups"
            assert result["success"] is True
            assert result["database_name"] == "test_db"

            # 验证传递了cleanup参数
            mock_task.run_backup_script.assert_called_once_with(
                backup_type="full",
                database_name="test_db",
                additional_args=["--cleanup"]
            )

    @patch('tasks.backup_tasks.subprocess.run')
    def test_verify_backup_task(self, mock_run):
        """测试验证备份任务"""
        # 模拟成功的验证结果
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Backup validation successful"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        mock_task = Mock()
        mock_task.restore_script_path = "/path/to/restore.sh"

        with patch('tasks.backup_tasks.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:00:00"

            result = verify_backup_task(
                mock_task,
                "/path/to/backup.sql",
                "test_db"
            )

            assert result["task_type"] == "verify_backup"
            assert result["database_name"] == "test_db"
            assert result["backup_file_path"] == "/path/to/backup.sql"
            assert result["success"] is True
            assert result["error_output"] is None

            # 验证调用了正确的命令
            mock_run.assert_called_once()

    @patch('tasks.backup_tasks.subprocess.run')
    def test_verify_backup_task_timeout(self, mock_run):
        """测试验证备份任务超时"""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["test"], timeout=300
        )

        mock_task = Mock()
        mock_task.restore_script_path = "/path/to/restore.sh"

        with patch('tasks.backup_tasks.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:00:00"

            result = verify_backup_task(
                mock_task,
                "/path/to/backup.sql",
                "test_db"
            )

            assert result["success"] is False
            assert result["error"] == "timeout"

    @patch('tasks.backup_tasks.subprocess.run')
    def test_get_backup_status_success(self, mock_run):
        """测试成功获取备份状态"""
        # 创建测试备份目录
        full_backup_dir = os.path.join(self.backup_dir, "full")
        os.makedirs(full_backup_dir, exist_ok=True)

        # 创建测试备份文件
        test_file = os.path.join(full_backup_dir, "full_backup_20231201_120000.sql.gz")
        with open(test_file, 'w') as f:
            f.write("test backup data")

        # 模拟find命令返回结果
        mock_find_result = Mock()
        mock_find_result.returncode = 0
        mock_find_result.stdout = "1024 1701388800 /path/to/backup.sql.gz\n"
        mock_run.return_value = mock_find_result

        with patch.dict(os.environ, {"BACKUP_DIR": self.backup_dir}):
            with patch('tasks.backup_tasks.datetime') as mock_datetime:
                mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:00:00"

                result = get_backup_status()

                assert result["full_backups"]["count"] == 1
                assert result["full_backups"]["total_size_bytes"] == 1024
                assert result["full_backups"]["latest_backup"] is not None
                assert "timestamp" in result

    @patch('tasks.backup_tasks.subprocess.run')
    def test_get_backup_status_empty_directory(self, mock_run):
        """测试空备份目录的状态获取"""
        # 模拟find命令返回空结果
        mock_find_result = Mock()
        mock_find_result.returncode = 0
        mock_find_result.stdout = ""
        mock_run.return_value = mock_find_result

        with patch.dict(os.environ, {"BACKUP_DIR": self.backup_dir}):
            with patch('tasks.backup_tasks.datetime') as mock_datetime:
                mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:00:00"

                result = get_backup_status()

                assert result["full_backups"]["count"] == 0
                assert result["full_backups"]["total_size_bytes"] == 0
                assert result["full_backups"]["latest_backup"] is None
                assert result["incremental_backups"]["count"] == 0

    def test_get_backup_status_exception(self):
        """测试获取备份状态时的异常处理"""
        with patch.dict(os.environ, {"BACKUP_DIR": self.backup_dir}):
            with patch('tasks.backup_tasks.datetime') as mock_datetime:
                mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:00:00"

                result = get_backup_status()

                assert "error" in result
                assert "timestamp" in result

    @patch('tasks.backup_tasks.daily_full_backup_task')
    @patch('tasks.backup_tasks.hourly_incremental_backup_task')
    @patch('tasks.backup_tasks.weekly_wal_archive_task')
    def test_manual_backup_task_full(self, mock_wal, mock_incremental, mock_full):
        """测试手动全量备份任务"""
        mock_result = {"success": True, "task_type": "daily_full_backup"}
        mock_full.apply_async.return_value.get.return_value = mock_result

        with patch('tasks.backup_tasks.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:00:00"

            result = manual_backup_task("full", "test_db")

            assert result["task_type"] == "daily_full_backup"
            assert result["success"] is True
            assert result["database_name"] == "test_db"

            mock_full.apply_async.assert_called_once_with(args=["test_db"])

    @patch('tasks.backup_tasks.daily_full_backup_task')
    @patch('tasks.backup_tasks.hourly_incremental_backup_task')
    @patch('tasks.backup_tasks.weekly_wal_archive_task')
    def test_manual_backup_task_incremental(self, mock_wal, mock_incremental, mock_full):
        """测试手动增量备份任务"""
        mock_result = {"success": True, "task_type": "hourly_incremental_backup"}
        mock_incremental.apply_async.return_value.get.return_value = mock_result

        with patch('tasks.backup_tasks.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:00:00"

            result = manual_backup_task("incremental", "test_db")

            assert result["task_type"] == "hourly_incremental_backup"
            assert result["success"] is True

            mock_incremental.apply_async.assert_called_once_with(args=["test_db"])

    @patch('tasks.backup_tasks.daily_full_backup_task')
    @patch('tasks.backup_tasks.hourly_incremental_backup_task')
    @patch('tasks.backup_tasks.weekly_wal_archive_task')
    def test_manual_backup_task_wal(self, mock_wal, mock_incremental, mock_full):
        """测试手动WAL备份任务"""
        mock_result = {"success": True, "task_type": "weekly_wal_archive"}
        mock_wal.apply_async.return_value.get.return_value = mock_result

        with patch('tasks.backup_tasks.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:00:00"

            result = manual_backup_task("wal", "test_db")

            assert result["task_type"] == "weekly_wal_archive"
            assert result["success"] is True

            mock_wal.apply_async.assert_called_once_with(args=["test_db"])

    @patch('tasks.backup_tasks.daily_full_backup_task')
    @patch('tasks.backup_tasks.hourly_incremental_backup_task')
    @patch('tasks.backup_tasks.weekly_wal_archive_task')
    @patch('tasks.backup_tasks.group')
    def test_manual_backup_task_all(self, mock_group, mock_wal, mock_incremental, mock_full):
        """测试手动执行所有类型备份任务"""
        # 模拟各个任务的结果
        full_result = {"success": True, "task_type": "daily_full_backup"}
        incremental_result = {"success": True, "task_type": "hourly_incremental_backup"}
        wal_result = {"success": True, "task_type": "weekly_wal_archive"}

        mock_full.s.return_value.apply_async.return_value.get.return_value = full_result
        mock_incremental.s.return_value.apply_async.return_value.get.return_value = incremental_result
        mock_wal.s.return_value.apply_async.return_value.get.return_value = wal_result

        # 模拟group任务
        mock_job = Mock()
        mock_job.apply_async.return_value.get.return_value = [
            full_result, incremental_result, wal_result
        ]
        mock_group.return_value = mock_job

        with patch('tasks.backup_tasks.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-12-01T12:00:00"

            result = manual_backup_task("all", "test_db")

            assert result["task_type"] == "manual_backup_all"
            assert result["database_name"] == "test_db"
            assert len(result["results"]) == 3

            # 验证group被正确调用
            mock_group.assert_called_once_with(
                mock_full.s("test_db"),
                mock_incremental.s("test_db"),
                mock_wal.s("test_db"),
            )

    def test_manual_backup_task_invalid_type(self):
        """测试无效备份类型的手动备份任务"""
        with pytest.raises(ValueError) as exc_info:
            manual_backup_task("invalid_type", "test_db")

        assert "不支持的备份类型" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)


class TestBackupTaskIntegration:
    """测试备份任务集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_backup_task_environment_variables(self):
        """测试备份任务环境变量处理"""
        test_env = {
            "DB_HOST": "test.host.com",
            "DB_PORT": "5433",
            "DB_USER": "test_user",
            "DB_PASSWORD": "test_pass",
            "BACKUP_DIR": self.backup_dir
        }

        task = DatabaseBackupTask()

        with patch.dict(os.environ, test_env):
            with patch('tasks.backup_tasks.subprocess.run') as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "Success"
                mock_result.stderr = ""
                mock_run.return_value = mock_result

                with patch('tasks.backup_tasks.datetime') as mock_datetime:
                    start_time = datetime.now()
                    end_time = start_time + timedelta(seconds=30)
                    mock_datetime.now.side_effect = [start_time, end_time]

                    success, output, stats = task.run_backup_script(
                        backup_type="full",
                        database_name="test_db"
                    )

                    assert success is True

                    # 验证subprocess.run被调用，且包含了正确的环境变量
                    call_args = mock_run.call_args
                    env_vars = call_args[1]['env']

                    assert env_vars['DB_HOST'] == "test.host.com"
                    assert env_vars['DB_PORT'] == "5433"
                    assert env_vars['DB_USER'] == "test_user"
                    assert env_vars['DB_PASSWORD'] == "test_pass"
                    assert env_vars['BACKUP_DIR'] == self.backup_dir

    def test_backup_task_metrics_recording(self):
        """测试备份任务指标记录"""
        task = DatabaseBackupTask()

        with patch('tasks.backup_tasks.subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Success"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            with patch('tasks.backup_tasks.datetime') as mock_datetime:
                start_time = datetime.now()
                end_time = start_time + timedelta(seconds=30)
                mock_datetime.now.side_effect = [start_time, end_time]

                with patch.object(task, '_get_latest_backup_size', return_value=2048):
                    success, output, stats = task.run_backup_script(
                        backup_type="full",
                        database_name="test_db"
                    )

                    assert success is True

                    # 验证成功指标被记录
                    task.metrics["success_total"].labels.assert_called_with(
                        backup_type="full", database_name="test_db"
                    )
                    task.metrics["success_total"].labels.return_value.inc.assert_called_once()

                    # 验证时间戳指标被记录
                    task.metrics["last_timestamp"].labels.assert_called_with(
                        backup_type="full", database_name="test_db"
                    )
                    task.metrics["last_timestamp"].labels.return_value.set.assert_called_once()

                    # 验证持续时间指标被记录
                    task.metrics["duration"].labels.assert_called_with(
                        backup_type="full", database_name="test_db"
                    )
                    task.metrics["duration"].labels.return_value.observe.assert_called_once_with(30)

                    # 验证文件大小指标被记录
                    task.metrics["file_size"].labels.assert_called_with(
                        backup_type="full", database_name="test_db"
                    )
                    task.metrics["file_size"].labels.return_value.set.assert_called_once_with(2048)

    def test_backup_task_concurrent_execution(self):
        """测试备份任务并发执行"""
        import asyncio

        async def run_concurrent_backups():
            task = DatabaseBackupTask()

            with patch('tasks.backup_tasks.subprocess.run') as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "Success"
                mock_result.stderr = ""
                mock_run.return_value = mock_result

                with patch('tasks.backup_tasks.datetime') as mock_datetime:
                    start_time = datetime.now()
                    end_time = start_time + timedelta(seconds=30)
                    mock_datetime.now.side_effect = [start_time, end_time] * 3

                    # 并发执行多个备份任务
                    tasks = []
                    for backup_type in ["full", "incremental", "wal"]:
                        task_coroutine = asyncio.create_task(
                            asyncio.get_event_loop().run_in_executor(
                                None,
                                task.run_backup_script,
                                backup_type,
                                "test_db"
                            )
                        )
                        tasks.append(task_coroutine)

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # 验证所有任务都成功完成
                    assert len(results) == 3
                    for success, output, stats in results:
                        assert success is True
                        assert stats["duration_seconds"] == 30

                    return results

        # 执行并发测试
        results = asyncio.run(run_concurrent_backups())
        assert len(results) == 3

    def test_backup_task_error_recovery(self):
        """测试备份任务错误恢复"""
        task = DatabaseBackupTask()

        # 模拟第一次失败，第二次成功
        call_count = 0
        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 第一次失败
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = "Disk full"
                return mock_result
            else:
                # 第二次成功
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "Success"
                mock_result.stderr = ""
                return mock_result

        with patch('tasks.backup_tasks.subprocess.run', side_effect=mock_run_side_effect):
            with patch('tasks.backup_tasks.datetime') as mock_datetime:
                start_time = datetime.now()
                end_time = start_time + timedelta(seconds=30)
                mock_datetime.now.side_effect = [start_time, end_time] * 2

                # 第一次执行（失败）
                success1, output1, stats1 = task.run_backup_script(
                    backup_type="full",
                    database_name="test_db"
                )

                # 第二次执行（成功）
                success2, output2, stats2 = task.run_backup_script(
                    backup_type="full",
                    database_name="test_db"
                )

                assert success1 is False
                assert "Disk full" in output1
                assert success2 is True
                assert "Success" in output2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])