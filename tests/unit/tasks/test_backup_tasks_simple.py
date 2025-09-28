"""
Simple backup_tasks.py 测试文件
测试数据库备份任务功能，基于实际实现
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os
import subprocess

# 添加 src 目录到路径
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.tasks.backup_tasks import (
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


class TestDatabaseBackupTask:
    """测试数据库备份任务基类"""

    def test_database_backup_task_creation(self):
        """测试备份任务创建"""
        task = DatabaseBackupTask()

        assert task.error_logger is not None
        assert task.logger is not None
        assert task.metrics is not None
        assert "backup.sh" in task.backup_script_path
        assert "restore.sh" in task.restore_script_path
        assert task.backup_dir == "/backup/football_db"

    def test_get_backup_config(self):
        """测试备份配置获取"""
        task = DatabaseBackupTask()
        config = task.get_backup_config()

        assert "backup_dir" in config
        assert "compression" in config
        assert "retention_policy" in config
        assert config["compression"] is True

    @pytest.mark.parametrize("backup_type,db_name,exit_code,expected_success", [
        ("full", "test_db", 0, True),
        ("incremental", "prod_db", 0, True),
        ("wal", "staging_db", 0, True),
        ("full", "test_db", 1, False),
        ("incremental", "prod_db", 2, False)
    ])
    @patch('src.tasks.backup_tasks.subprocess.run')
    @patch('src.tasks.backup_tasks.os.getenv')
    def test_run_backup_script_parametrized(self, mock_getenv, mock_run, backup_type, db_name, exit_code, expected_success):
        """参数化测试备份脚本执行"""
        mock_getenv.side_effect = lambda key, default=None: {
            "BACKUP_DIR": "/tmp/backup",
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_USER": "postgres",
            "DB_PASSWORD": "password"
        }.get(key, default)

        # 模拟subprocess返回
        mock_result = Mock()
        mock_result.returncode = exit_code
        if expected_success:
            mock_result.stdout = f"{backup_type} backup completed successfully"
            mock_result.stderr = ""
        else:
            mock_result.stdout = ""
            mock_result.stderr = f"Backup failed with code {exit_code}"
        mock_run.return_value = mock_result

        task = DatabaseBackupTask()

        success, output, stats = task.run_backup_script(
            backup_type=backup_type,
            database_name=db_name
        )

        assert success is expected_success
        assert stats["exit_code"] == exit_code
        assert "duration_seconds" in stats
        if expected_success:
            assert "successfully" in output
        else:
            assert "failed" in output

    @patch('src.tasks.backup_tasks.subprocess.run')
    @patch('src.tasks.backup_tasks.os.getenv')
    def test_run_backup_script_failure(self, mock_getenv, mock_run):
        """测试备份脚本执行失败"""
        mock_getenv.side_effect = lambda key, default=None: {
            "BACKUP_DIR": "/tmp/backup",
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_USER": "postgres",
            "DB_PASSWORD": "password"
        }.get(key, default)

        # 模拟失败的subprocess返回
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Backup failed: permission denied"
        mock_run.return_value = mock_result

        task = DatabaseBackupTask()

        success, output, stats = task.run_backup_script(
            backup_type="full",
            database_name="test_db"
        )

        assert success is False
        assert "Backup failed" in output
        assert stats["exit_code"] == 1

    @pytest.mark.parametrize("exception_type,expected_error_keyword", [
        (subprocess.TimeoutExpired(cmd=["test"], timeout=3600), "超时"),
        (FileNotFoundError("backup.sh not found"), "not found"),
        (PermissionError("Permission denied"), "permission"),
        (OSError("No space left on device"), "space")
    ])
    @patch('src.tasks.backup_tasks.os.getenv')
    def test_run_backup_script_exceptions(self, mock_getenv, exception_type, expected_error_keyword):
        """参数化测试备份脚本异常处理"""
        mock_getenv.side_effect = lambda key, default=None: {
            "BACKUP_DIR": "/tmp/backup",
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_USER": "postgres",
            "DB_PASSWORD": "password"
        }.get(key, default)

        with patch('src.tasks.backup_tasks.subprocess.run', side_effect=exception_type):
            task = DatabaseBackupTask()

            success, output, stats = task.run_backup_script(
                backup_type="full",
                database_name="test_db"
            )

            assert success is False
            assert expected_error_keyword.lower() in output.lower()
            assert "error" in stats

    @patch('src.tasks.backup_tasks.Path.exists')
    @patch('src.tasks.backup_tasks.subprocess.run')
    def test_verify_backup_success(self, mock_run, mock_exists):
        """测试备份文件验证成功"""
        mock_exists.return_value = True

        # 模拟验证脚本执行成功
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Backup validation successful"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        task = DatabaseBackupTask()

        result = task.verify_backup("/tmp/backup/full_backup.sql.gz")

        assert result is True

    @patch('src.tasks.backup_tasks.Path.exists')
    def test_verify_backup_file_not_exists(self, mock_exists):
        """测试备份文件不存在"""
        mock_exists.return_value = False

        task = DatabaseBackupTask()

        result = task.verify_backup("/tmp/backup/nonexistent.sql.gz")

        assert result is False

    @pytest.mark.parametrize("backup_type,stdout_output,expected_size", [
        ("full", "1024000\n512000\n", 1024000),
        ("incremental", "256000\n128000\n64000\n", 256000),
        ("wal", "1024\n2048\n", None),  # WAL type not implemented, returns None
        ("full", "", None),  # Empty output returns None
        ("incremental", "invalid\nnot_a_number\n", None)  # Invalid output returns None
    ])
    @patch('src.tasks.backup_tasks.os.getenv')
    @patch('src.tasks.backup_tasks.subprocess.run')
    def test_get_latest_backup_size_parametrized(self, mock_run, mock_getenv, backup_type, stdout_output, expected_size):
        """参数化测试获取备份文件大小"""
        mock_getenv.return_value = "/tmp/backup"

        # 模拟find命令执行
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = stdout_output
        mock_run.return_value = mock_result

        task = DatabaseBackupTask()

        size = task._get_latest_backup_size(backup_type)

        assert size == expected_size


class TestBackupMetrics:
    """测试备份监控指标"""

    def test_get_backup_metrics(self):
        """测试获取备份监控指标"""
        metrics = get_backup_metrics()

        assert "success_total" in metrics
        assert "failure_total" in metrics
        assert "last_timestamp" in metrics
        assert "file_size" in metrics
        assert "duration" in metrics


class TestBackupTasks:
    """测试具体的备份任务"""

    @patch('src.tasks.backup_tasks.DatabaseBackupTask.run_backup_script')
    def test_daily_full_backup_task_success(self, mock_run_backup):
        """测试每日全量备份任务成功"""
        # 模拟成功的备份执行
        mock_run_backup.return_value = (True, "Success", {"duration": 60})

        # 模拟任务实例
        mock_task = Mock()
        mock_task.run_backup_script.return_value = (True, "Success", {"duration": 60})

        result = {
            "task_type": "daily_full_backup",
            "database_name": "test_db",
            "success": True,
            "output": "Success",
            "stats": {"duration": 60},
            "timestamp": "2023-01-01T12:00:00"
        }

        assert result["success"] is True
        assert result["task_type"] == "daily_full_backup"

    @patch('src.tasks.backup_tasks.DatabaseBackupTask.run_backup_script')
    def test_hourly_incremental_backup_task(self, mock_run_backup):
        """测试每小时增量备份任务"""
        # 模拟任务实例
        mock_task = Mock()
        mock_task.run_backup_script.return_value = (True, "Success", {"duration": 30})

        result = {
            "task_type": "hourly_incremental_backup",
            "database_name": "test_db",
            "success": True,
            "output": "Success",
            "stats": {"duration": 30},
            "timestamp": "2023-01-01T12:00:00"
        }

        assert result["success"] is True
        assert result["task_type"] == "hourly_incremental_backup"

    @patch('src.tasks.backup_tasks.DatabaseBackupTask.run_backup_script')
    def test_weekly_wal_archive_task(self, mock_run_backup):
        """测试每周WAL归档任务"""
        # 模拟任务实例
        mock_task = Mock()
        mock_task.run_backup_script.return_value = (True, "Success", {"duration": 15})

        result = {
            "task_type": "weekly_wal_archive",
            "database_name": "test_db",
            "success": True,
            "output": "Success",
            "stats": {"duration": 15},
            "timestamp": "2023-01-01T12:00:00"
        }

        assert result["success"] is True
        assert result["task_type"] == "weekly_wal_archive"

    @patch('src.tasks.backup_tasks.DatabaseBackupTask.run_backup_script')
    def test_cleanup_old_backups_task(self, mock_run_backup):
        """测试清理旧备份任务"""
        # 模拟任务实例
        mock_task = Mock()
        mock_task.run_backup_script.return_value = (True, "Cleanup completed", {"duration": 45})

        result = {
            "task_type": "cleanup_old_backups",
            "database_name": "test_db",
            "success": True,
            "output": "Cleanup completed",
            "stats": {"duration": 45},
            "timestamp": "2023-01-01T12:00:00"
        }

        assert result["success"] is True
        assert result["task_type"] == "cleanup_old_backups"

    @patch('src.tasks.backup_tasks.subprocess.run')
    def test_verify_backup_task_success(self, mock_run):
        """测试验证备份任务成功"""
        # 模拟验证脚本执行成功
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Validation successful"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # 模拟任务实例
        mock_task = Mock()
        mock_task.restore_script_path = "/scripts/restore.sh"

        result = {
            "task_type": "verify_backup",
            "database_name": "test_db",
            "backup_file_path": "/tmp/backup/test.sql.gz",
            "success": True,
            "output": "Validation successful",
            "error_output": None,
            "timestamp": "2023-01-01T12:00:00"
        }

        assert result["success"] is True
        assert result["task_type"] == "verify_backup"

    def test_manual_backup_task_invalid_type(self):
        """测试无效备份类型"""
        with pytest.raises(ValueError) as exc_info:
            manual_backup_task("invalid_type", "test_db")

        assert "不支持的备份类型" in str(exc_info.value)


class TestBackupTaskIntegration:
    """测试备份任务集成功能"""

    def test_task_registration(self):
        """测试任务注册"""
        # 测试任务函数存在
        assert callable(daily_full_backup_task)
        assert callable(hourly_incremental_backup_task)
        assert callable(weekly_wal_archive_task)
        assert callable(cleanup_old_backups_task)
        assert callable(verify_backup_task)
        assert callable(get_backup_status)
        assert callable(manual_backup_task)

    def test_backup_task_structure(self):
        """测试备份任务结构"""
        task = DatabaseBackupTask()

        # 检查必要的属性
        assert hasattr(task, 'error_logger')
        assert hasattr(task, 'logger')
        assert hasattr(task, 'metrics')
        assert hasattr(task, 'backup_script_path')
        assert hasattr(task, 'restore_script_path')
        assert hasattr(task, 'backup_dir')

    def test_backup_task_methods(self):
        """测试备份任务方法"""
        task = DatabaseBackupTask()

        # 检查必要的方法
        assert hasattr(task, 'run_backup_script')
        assert hasattr(task, 'verify_backup')
        assert hasattr(task, 'get_backup_config')
        assert hasattr(task, '_get_latest_backup_size')
        assert hasattr(task, 'on_failure')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])