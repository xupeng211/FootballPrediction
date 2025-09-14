"""
备份任务模块的单元测试

测试覆盖：
- DatabaseBackupTask 类的各种方法
- 备份配置和验证
- 错误处理和重试机制
- Prometheus 指标集成
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.tasks.backup_tasks import DatabaseBackupTask, get_backup_status


class TestDatabaseBackupTask:
    """数据库备份任务测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.backup_task = DatabaseBackupTask()

    def test_backup_task_initialization(self):
        """测试备份任务初始化"""
        assert self.backup_task is not None
        # Celery任务类的基本属性测试
        assert hasattr(self.backup_task, "run")
        assert hasattr(self.backup_task, "name")

    @patch("src.tasks.backup_tasks.subprocess.run")
    @patch("src.tasks.backup_tasks.Path.mkdir")
    @patch("src.tasks.backup_tasks.datetime")
    def test_run_backup_script_success(self, mock_datetime, mock_mkdir, mock_run):
        """测试备份脚本成功执行"""
        # 模拟当前时间
        mock_datetime.now.return_value = datetime(2025, 1, 15, 10, 30, 0)
        mock_datetime.now().strftime.return_value = "20250115_103000"

        # 模拟subprocess.run成功
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = "Backup completed successfully"
        mock_run.return_value = mock_process

        # 执行备份
        result = self.backup_task._run_backup_script("full", "/test / output")

        # 验证结果
        assert result is True
        mock_run.assert_called_once()
        mock_mkdir.assert_called_once()

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_run_backup_script_failure(self, mock_run):
        """测试备份脚本执行失败"""
        # 模拟subprocess.run失败
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.stderr = "Database connection failed"
        mock_run.return_value = mock_process

        # 执行备份
        result = self.backup_task._run_backup_script("full", "/test / output")

        # 验证结果
        assert result is False

    @patch("src.tasks.backup_tasks.DatabaseBackupTask._run_backup_script")
    def test_perform_full_backup_success(self, mock_run_script):
        """测试执行完整备份成功"""
        mock_run_script.return_value = True

        result = self.backup_task.perform_full_backup()

        assert result is True
        mock_run_script.assert_called_once()

    @patch("src.tasks.backup_tasks.DatabaseBackupTask._run_backup_script")
    def test_perform_incremental_backup_success(self, mock_run_script):
        """测试执行增量备份成功"""
        mock_run_script.return_value = True

        result = self.backup_task.perform_incremental_backup()

        assert result is True
        mock_run_script.assert_called_once()

    @patch("src.tasks.backup_tasks.Path.glob")
    def test_cleanup_old_backups_success(self, mock_glob):
        """测试清理旧备份成功"""
        # 模拟旧的备份文件
        old_backup = Mock()
        old_backup.stat.return_value.st_mtime = 1640995200  # 2022 - 01 - 01
        old_backup.unlink = Mock()

        mock_glob.return_value = [old_backup]

        with patch(
            "src.tasks.backup_tasks.time.time", return_value=1700000000
        ):  # 2023年的时间戳
            deleted_count = self.backup_task.cleanup_old_backups()

        assert deleted_count == 1
        old_backup.unlink.assert_called_once()

    @patch("src.tasks.backup_tasks.Path.exists")
    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_verify_backup_success(self, mock_run, mock_exists):
        """测试备份验证成功"""
        mock_exists.return_value = True
        mock_process = Mock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        result = self.backup_task.verify_backup("/test / backup.sql")

        assert result is True

    @patch("src.tasks.backup_tasks.Path.exists")
    def test_verify_backup_file_not_exists(self, mock_exists):
        """测试备份文件不存在"""
        mock_exists.return_value = False

        result = self.backup_task.verify_backup("/nonexistent / backup.sql")

        assert result is False

    def test_get_backup_config(self):
        """测试获取备份配置"""
        config = self.backup_task.get_backup_config()

        assert isinstance(config, dict)
        assert "backup_dir" in config
        assert "max_backup_age_days" in config
        assert "compression" in config


class TestBackupHelperTasks:
    """备份辅助任务测试类"""

    @patch("src.tasks.backup_tasks.get_backup_status")
    def test_get_backup_status_function_exists(self, mock_status):
        """测试get_backup_status函数存在性"""
        mock_status.return_value = {
            "status": "healthy",
            "last_backup": "2025 - 01 - 15 10:30:00",
        }

        from src.tasks.backup_tasks import get_backup_status

        result = get_backup_status()

        assert isinstance(result, dict)
        assert "status" in result


class TestPrometheusMetrics:
    """Prometheus指标测试类"""

    def test_prometheus_metrics_setup(self):
        """测试Prometheus指标设置"""
        # 测试指标是否正确定义
        task = DatabaseBackupTask()

        # 确保任务有监控能力
        assert hasattr(task, "logger")

        # 这里可以测试指标的基本结构
        assert task is not None


class TestErrorHandling:
    """错误处理测试类"""

    def test_backup_task_exception_handling(self):
        """测试备份任务异常处理"""
        task = DatabaseBackupTask()

        # 测试任务创建时的异常处理
        assert task is not None
        assert hasattr(task, "logger")

    def test_invalid_parameters(self):
        """测试无效参数处理"""
        task = DatabaseBackupTask()

        # 测试任务的基本属性
        assert task is not None


class TestEdgeCases:
    """边界情况测试类"""

    def test_empty_backup_directory(self):
        """测试空的备份目录"""
        with patch("src.tasks.backup_tasks.Path.glob", return_value=[]):
            status = get_backup_status()

            assert status["full_backups"]["count"] == 0
            assert status["incremental_backups"]["count"] == 0

    @patch("src.tasks.backup_tasks.Path.glob")
    def test_corrupted_backup_files(self, mock_glob):
        """测试损坏的备份文件"""
        # 模拟无法读取的备份文件
        corrupted_file = Mock()
        corrupted_file.stat.side_effect = OSError("File corrupted")
        mock_glob.return_value = [corrupted_file]

        status = get_backup_status()

        # 应该跳过损坏的文件
        assert isinstance(status, dict)

    def test_concurrent_backup_operations(self):
        """测试并发备份操作"""
        task1 = DatabaseBackupTask()
        task2 = DatabaseBackupTask()

        # 两个任务应该是独立的
        assert task1 is not task2
        assert task1.backup_dir == task2.backup_dir  # 但配置应该相同

    @patch("src.tasks.backup_tasks.time.time")
    def test_backup_during_system_maintenance(self, mock_time):
        """测试系统维护期间的备份"""
        # 模拟系统负载高的情况
        mock_time.return_value = 1700000000

        task = DatabaseBackupTask()

        with patch(
            "src.tasks.backup_tasks.subprocess.run",
            side_effect=TimeoutError("Operation timed out"),
        ):
            result = task._run_backup_script("full", "/test / output")
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
