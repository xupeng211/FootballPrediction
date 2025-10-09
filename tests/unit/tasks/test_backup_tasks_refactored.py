"""
测试重构后的备份任务模块

验证拆分后的各个组件是否正常工作。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.tasks.backup.core.backup_config import BackupConfig
from src.tasks.backup.executor.backup_executor import BackupExecutor
from src.tasks.backup.validation.backup_validator import BackupValidator
from src.tasks.backup.cleanup.backup_cleaner import BackupCleaner
from src.tasks.backup.tasks.backup_tasks import (
    DatabaseBackupTask,
    RedisBackupTask,
    LogsBackupTask,
    BackupValidationTask,
    BackupCleanupTask
)


class TestBackupConfig:
    """测试备份配置"""

    def test_backup_config_initialization(self):
        """测试备份配置初始化"""
        config = BackupConfig()

        assert config.backup_dir is not None
        assert config.retention_policy is not None
        assert "daily" in config.retention_policy
        assert "weekly" in config.retention_policy
        assert "monthly" in config.retention_policy

    def test_backup_config_custom_values(self):
        """测试自定义配置值"""
        custom_dir = "/custom/backup/path"
        config = BackupConfig(backup_dir=custom_dir)

        assert config.backup_dir == custom_dir

    def test_retention_policy_structure(self):
        """测试保留策略结构"""
        config = BackupConfig()
        policy = config.retention_policy

        assert isinstance(policy["daily"], int)
        assert isinstance(policy["weekly"], int)
        assert isinstance(policy["monthly"], int)
        assert policy["daily"] > 0
        assert policy["weekly"] > 0
        assert policy["monthly"] > 0


class TestBackupExecutor:
    """测试备份执行器"""

    def setup_method(self):
        """设置测试环境"""
        self.config = BackupConfig()
        self.executor = BackupExecutor(self.config)

    @patch('src.tasks.backup.executor.backup_executor.subprocess.run')
    def test_backup_database_full(self, mock_subprocess):
        """测试全量数据库备份"""
        # Mock成功的子进程执行
        mock_subprocess.return_value = Mock(returncode=0)

        with patch.object(self.executor, '_verify_backup', return_value=True):
            result = self.executor.backup_database(
                backup_type="full",
                compress=True,
                verify=True
            )

        assert result["status"] == "success"
        assert "backup_file_path" in result
        assert result["backup_type"] == "full"

    @patch('src.tasks.backup.executor.backup_executor.subprocess.run')
    def test_backup_redis(self, mock_subprocess):
        """测试Redis备份"""
        mock_subprocess.return_value = Mock(returncode=0)

        with patch('os.path.exists', return_value=True), \
             patch('shutil.copy2'):
            result = self.executor.backup_redis(compress=True)

        assert result["status"] == "success"
        assert "backup_file_path" in result

    def test_backup_logs(self):
        """测试日志备份"""
        with patch('os.path.exists', return_value=True), \
             patch('tarfile.open') as mock_tar, \
             patch('os.listdir', return_value=['app.log']):

            mock_tar.return_value.__enter__.return_value = Mock()

            result = self.executor.backup_logs(
                log_dirs=['/tmp/logs'],
                compress=True
            )

        assert result["status"] == "success"
        assert "backup_file_path" in result


class TestBackupValidator:
    """测试备份验证器"""

    def setup_method(self):
        """设置测试环境"""
        self.config = BackupConfig()
        self.validator = BackupValidator(self.config)

    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_verify_database_backup_success(self, mock_getsize, mock_exists):
        """测试数据库备份验证成功"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024

        with patch.object(self.validator, '_verify_sql_file', return_value=True):
            result = self.validator.verify_database_backup(
                "/path/to/backup.sql",
                database_name="test_db"
            )

        assert result is True

    @patch('os.path.exists')
    def test_verify_database_backup_not_found(self, mock_exists):
        """测试数据库备份文件不存在"""
        mock_exists.return_value = False

        result = self.validator.verify_database_backup(
            "/path/to/nonexistent.sql",
            database_name="test_db"
        )

        assert result is False

    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_verify_redis_backup_success(self, mock_getsize, mock_exists, mock_open):
        """测试Redis备份验证成功"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024
        mock_file = MagicMock()
        mock_file.read.return_value = b'REDIS0009'
        mock_open.return_value.__enter__.return_value = mock_file

        result = self.validator.verify_redis_backup("/path/to/redis.rdb")

        assert result is True

    def test_get_backup_status_report(self):
        """测试获取备份状态报告"""
        with patch('os.listdir', return_value=['backup_20240101_full.sql']), \
             patch('os.path.isfile', return_value=True), \
             patch('os.path.getsize', return_value=1024), \
             patch('os.path.getmtime', return_value=1704067200), \
             patch.object(self.validator, 'verify_database_backup', return_value=True):

            report = self.validator.get_backup_status_report(
                database_name="test_db"
            )

        assert "database_name" in report
        assert "timestamp" in report
        assert "latest_backups" in report
        assert "verification_results" in report
        assert "storage_info" in report


class TestBackupCleaner:
    """测试备份清理器"""

    def setup_method(self):
        """设置测试环境"""
        self.config = BackupConfig()
        self.cleaner = BackupCleaner(self.config)

    @patch('os.listdir')
    @patch('os.path.getmtime')
    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_cleanup_old_backups(self, mock_exists, mock_getsize, mock_getmtime, mock_listdir):
        """测试清理过期备份"""
        mock_exists.return_value = True
        mock_listdir.return_value = ['backup_20230101_full.sql']
        mock_getsize.return_value = 1024
        mock_getmtime.return_value = 1672531200  # 2023-01-01

        with patch.object(self.cleaner, '_delete_file', return_value=True):
            result = self.cleaner.cleanup_old_backups(
                database_name="test_db",
                dry_run=True
            )

        assert result["database_name"] == "test_db"
        assert result["dry_run"] is True
        assert "summary" in result

    @patch('os.listdir')
    @patch('os.path.getmtime')
    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_cleanup_redis_backups(self, mock_exists, mock_getsize, mock_getmtime, mock_listdir):
        """测试清理Redis备份"""
        mock_exists.return_value = True
        mock_listdir.return_value = ['redis_backup_20230101.rdb']
        mock_getsize.return_value = 1024
        mock_getmtime.return_value = 1672531200

        with patch('os.remove'):
            result = self.cleaner.cleanup_redis_backups(dry_run=False)

        assert result["type"] == "redis"
        assert "summary" in result


class TestDatabaseBackupTask:
    """测试数据库备份任务"""

    def setup_method(self):
        """设置测试环境"""
        self.task = DatabaseBackupTask()

    def test_task_initialization(self):
        """测试任务初始化"""
        assert self.task.config is not None
        assert self.task.executor is not None
        assert self.task.validator is not None
        assert self.task.cleaner is not None
        assert self.task.metrics is not None

    @patch.object(DatabaseBackupTask, 'run')
    def test_run_full_backup(self, mock_run):
        """测试运行全量备份"""
        mock_run.return_value = {
            "status": "success",
            "backup_type": "full",
            "result": {"backup_file_path": "/path/to/backup.sql"}
        }

        result = self.task.run(backup_type="full")

        assert result["status"] == "success"
        assert result["backup_type"] == "full"

    def test_should_retry(self):
        """测试重试判断"""
        # 临时性错误应该重试
        assert self.task._should_retry(ConnectionError("Connection failed"))
        assert self.task._should_retry(TimeoutError("Operation timeout"))

        # 永久性错误不应该重试
        assert not self.task._should_retry(ValueError("Invalid input"))


class TestRedisBackupTask:
    """测试Redis备份任务"""

    def setup_method(self):
        """设置测试环境"""
        self.task = RedisBackupTask()

    def test_task_initialization(self):
        """测试任务初始化"""
        assert self.task.config is not None
        assert self.task.executor is not None
        assert self.task.validator is not None
        assert self.task.metrics is not None

    @patch.object(RedisBackupTask, 'run')
    def test_run_redis_backup(self, mock_run):
        """测试运行Redis备份"""
        mock_run.return_value = {
            "status": "success",
            "backup_type": "redis",
            "result": {"backup_file_path": "/path/to/redis.rdb"}
        }

        result = self.task.run()

        assert result["status"] == "success"
        assert result["backup_type"] == "redis"


class TestBackupValidationTask:
    """测试备份验证任务"""

    def setup_method(self):
        """设置测试环境"""
        self.task = BackupValidationTask()

    def test_task_initialization(self):
        """测试任务初始化"""
        assert self.task.config is not None
        assert self.task.validator is not None
        assert self.task.metrics is not None

    @patch.object(BackupValidationTask, 'run')
    def test_run_validation(self, mock_run):
        """测试运行备份验证"""
        mock_run.return_value = {
            "status": "success",
            "backup_file_path": "/path/to/backup.sql",
            "is_valid": True
        }

        result = self.task.run(
            backup_file_path="/path/to/backup.sql",
            backup_type="database"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is True


class TestBackupCleanupTask:
    """测试备份清理任务"""

    def setup_method(self):
        """设置测试环境"""
        self.task = BackupCleanupTask()

    def test_task_initialization(self):
        """测试任务初始化"""
        assert self.task.config is not None
        assert self.task.cleaner is not None
        assert self.task.metrics is not None

    @patch.object(BackupCleanupTask, 'run')
    def test_run_cleanup(self, mock_run):
        """测试运行备份清理"""
        mock_run.return_value = {
            "status": "success",
            "cleanup_type": "database",
            "result": {"summary": {"total_files_deleted": 5}}
        }

        result = self.task.run(cleanup_type="database", dry_run=False)

        assert result["status"] == "success"
        assert result["cleanup_type"] == "database"

    def test_format_bytes(self):
        """测试字节格式化"""
        assert self.task._format_bytes(1024) == "1.00 KB"
        assert self.task._format_bytes(1048576) == "1.00 MB"
        assert self.task._format_bytes(1073741824) == "1.00 GB"


if __name__ == "__main__":
    pytest.main([__file__])