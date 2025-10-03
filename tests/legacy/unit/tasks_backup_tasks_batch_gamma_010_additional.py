import os
import sys

from src.tasks.backup_tasks import DatabaseBackupTask, get_backup_metrics
from unittest.mock import Mock, patch
import pytest
import subprocess

"""
BackupTasks Batch-Γ-010 补充测试套件

专门为 tasks/backup_tasks.py 设计的补充测试，目标是将其覆盖率从 43% 提升至 ≥51%
覆盖未测试的错误处理、指标记录、文件大小检测和边界情况
"""

# Add the project root to sys.path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
from src.tasks.backup_tasks import DatabaseBackupTask, get_backup_metrics
class TestBackupTasksBatchGamma010Additional:
    """BackupTasks Batch-Γ-010 补充测试类"""
    @pytest.fixture
    def backup_task(self):
        """创建数据库备份任务实例"""
        # 使用独立的 registry 避免测试冲突
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        return DatabaseBackupTask(registry=registry)
    def test_run_backup_script_success_with_file_size(self, backup_task):
        """测试成功执行备份脚本并记录文件大小"""
        # Mock subprocess.run 返回成功
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Backup successful[": mock_result.stderr = : ": with patch("]subprocess.run[", return_value = mock_result)""""
            # Mock _get_latest_backup_size 返回文件大小
            backup_task._get_latest_backup_size = Mock(return_value=1024000)
            success, output, stats = backup_task.run_backup_script(
                backup_type="]full[", database_name="]test_db["""""
            )
            # 验证成功结果
            assert success is True
            assert "]Backup successful[" in output[""""
            assert stats["]]backup_file_size_bytes["] ==1024000[" def test_run_backup_script_timeout_exception(self, backup_task):"""
        "]]""测试备份脚本执行超时异常"""
        with patch(:
            "subprocess.run[", side_effect=subprocess.TimeoutExpired("]cmd[", 3600)""""
        ):
            success, output, stats = backup_task.run_backup_script(
                backup_type="]incremental[", database_name="]timeout_db["""""
            )
            # 验证超时处理
            assert success is False
            assert "]超时[" in output[""""
            assert stats["]]error["] =="]timeout["""""
            # 验证超时指标被记录（不验证具体的 metrics 调用）
    def test_run_backup_script_general_exception(self, backup_task):
        "]""测试备份脚本执行一般异常"""
        with patch("subprocess.run[", side_effect = OSError("]Permission denied["))": success, output, stats = backup_task.run_backup_script(": backup_type="]wal[", database_name="]error_db["""""
            )
            # 验证异常处理
            assert success is False
            assert "]Permission denied[" in output[""""
            assert stats["]]error["] =="]Permission denied["""""
            # 验证异常指标被记录（不验证具体的 metrics 调用）
    def test_get_latest_backup_size_full_backup_with_files(self, backup_task):
        "]""测试获取全量备份文件大小 - 有备份文件的情况"""
        with patch("subprocess.run[") as mock_run:""""
            # Mock find 命令返回文件大小
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "]1024000\n2048000\n512000[": mock_run.return_value = mock_result[": size = backup_task._get_latest_backup_size("]]full[")""""
            # 验证返回最大文件大小
            assert size ==2048000
            # 验证 find 命令被正确调用
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "]find[" in call_args[""""
            assert "]]full_backup_*.sql.gz[" in call_args[""""
    def test_get_latest_backup_size_full_backup_no_files(self, backup_task):
        "]]""测试获取全量备份文件大小 - 无备份文件的情况"""
        with patch("subprocess.run[") as mock_run:""""
            # Mock find 命令返回空结果
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "]": mock_run.return_value = mock_result[": size = backup_task._get_latest_backup_size("]full[")""""
            # 验证返回 None
            assert size is None
    def test_get_latest_backup_size_full_backup_find_error(self, backup_task):
        "]""测试获取全量备份文件大小 - find 命令错误"""
        with patch("subprocess.run[") as mock_run:""""
            # Mock find 命令返回错误
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = "]": mock_run.return_value = mock_result[": size = backup_task._get_latest_backup_size("]full[")""""
            # 验证返回 None
            assert size is None
    def test_get_latest_backup_size_incremental_backup(self, backup_task):
        "]""测试获取增量备份文件大小"""
        with patch("subprocess.run[") as mock_run:""""
            # Mock find 命令返回目录列表
            mock_find_result = Mock()
            mock_find_result.returncode = 0
            mock_find_result.stdout = (
                "]/backup/incremental/20240101\n/backup/incremental/20240102["""""
            )
            # Mock du 命令返回目录大小
            mock_du_result = Mock()
            mock_du_result.returncode = 0
            mock_du_result.stdout = "]1024000\t/backup/incremental/20240102["""""
            # 设置 side_effect 来处理两个不同的调用
            mock_run.side_effect = ["]mock_find_result[", mock_du_result]": size = backup_task._get_latest_backup_size("]incremental[")""""
            # 验证返回目录大小
            assert size ==1024000
            # 验证命令被正确调用
            assert mock_run.call_count ==2
    def test_get_latest_backup_size_incremental_backup_empty_dirs(self, backup_task):
        "]""测试获取增量备份文件大小 - 空目录列表"""
        with patch("subprocess.run[") as mock_run:""""
            # Mock find 命令返回空结果
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "]": mock_run.return_value = mock_result[": size = backup_task._get_latest_backup_size("]incremental[")""""
            # 验证返回 None
            assert size is None
    def test_get_latest_backup_size_unsupported_type(self, backup_task):
        "]""测试获取不支持的备份类型文件大小"""
        size = backup_task._get_latest_backup_size("unsupported_type[")""""
        # 验证返回 None
        assert size is None
    def test_get_latest_backup_size_exception_handling(self, backup_task):
        "]""测试获取备份文件大小异常处理"""
        with patch("subprocess.run[", side_effect = OSError("]Command not found["))": with patch("]src.tasks.backup_tasks.logger[") as mock_logger:": size = backup_task._get_latest_backup_size("]full[")""""
                # 验证返回 None
                assert size is None
                # 验证错误被记录
                mock_logger.warning.assert_called_once()
    def test_verify_backup_timeout_exception(self, backup_task):
        "]""测试备份文件验证超时异常"""
        # Mock subprocess.run 抛出超时异常
        with patch(:
            "subprocess.run[", side_effect=subprocess.TimeoutExpired("]restore.sh[", 300)""""
        ):
            with patch("]src.tasks.backup_tasks.logger[") as mock_logger:": result = backup_task.verify_backup("]/backup/test_backup.sql.gz[")""""
                # 验证返回 False
                assert result is False
                # 验证错误被记录
                mock_logger.error.assert_called_once()
    def test_verify_backup_general_exception(self, backup_task):
        "]""测试备份文件验证一般异常"""
        # Mock subprocess.run 抛出一般异常
        with patch("subprocess.run[", side_effect = OSError("]File not found["))": with patch("]src.tasks.backup_tasks.logger[") as mock_logger:": result = backup_task.verify_backup("]/backup/nonexistent.sql.gz[")""""
                # 验证返回 False
                assert result is False
                # 验证错误被记录
                mock_logger.error.assert_called_once()
    def test_verify_backup_file_not_exists(self, backup_task):
        "]""测试验证不存在的备份文件"""
        with patch("src.tasks.backup_tasks.logger[") as mock_logger:": result = backup_task.verify_backup("]/backup/nonexistent.sql.gz[")""""
            # 验证返回 False
            assert result is False
            # 验证错误被记录
            mock_logger.error.assert_called_once()
    def test_get_backup_metrics_error_handling(self):
        "]""测试获取备份指标错误处理"""
        # Mock prometheus_client 抛出 ValueError（指标已存在）
        with patch("prometheus_client.REGISTRY[") as mock_registry:": mock_registry.register.side_effect = ValueError("]Metric already registered[")": metrics = get_backup_metrics()"""
            # 验证返回 mock 对象
            assert "]success_total[" in metrics[""""
            assert "]]failure_total[" in metrics[""""
            assert metrics["]]success_total["].inc is not None[" def test_backup_task_initialization_with_custom_registry(self):"""
        "]]""测试使用自定义 registry 的备份任务初始化"""
        from prometheus_client import CollectorRegistry
        custom_registry = CollectorRegistry()
        backup_task = DatabaseBackupTask(registry=custom_registry)
        # 验证使用自定义 registry
        assert backup_task.metrics is not None
    def test_backup_task_path_initialization(self, backup_task):
        """测试备份任务路径初始化"""
        # 验证脚本路径正确设置
        assert "backup.sh[" in backup_task.backup_script_path[""""
        assert "]]restore.sh[" in backup_task.restore_script_path[""""
        # 验证备份目录从环境变量获取
        expected_backup_dir = os.getenv("]]BACKUP_DIR[", "]/backup/football_db[")": assert backup_task.backup_dir ==expected_backup_dir[" def test_backup_config_environment_variables(self, backup_task):""
        "]]""测试备份配置环境变量"""
        config = backup_task.get_backup_config()
        # 验证环境变量被正确读取
        assert config["backup_dir["] ==os.getenv("]BACKUP_DIR[", "]/backup/football_db[")" assert config["]max_backup_age_days["] ==int(" os.getenv("]MAX_BACKUP_AGE_DAYS[", "]30[")""""
        )
        assert config["]compression["] is True[" def test_backup_config_retention_policy(self, backup_task):"""
        "]]""测试备份配置保留策略"""
        config = backup_task.get_backup_config()
        # 验证保留策略配置
        retention = config["retention_policy["]"]": assert "full_backups[" in retention[""""
        assert "]]incremental_backups[" in retention[""""
        assert "]]wal_archives[" in retention[""""
        # 验证默认值
        assert retention["]]full_backups["] ==int(os.getenv("]KEEP_FULL_BACKUPS[", "]7["))" assert retention["]incremental_backups["] ==int(" os.getenv("]KEEP_INCREMENTAL_BACKUPS[", "]30[")""""
        )
        assert retention["]wal_archives["] ==int(os.getenv("]KEEP_WAL_ARCHIVES[", "]7["))" def test_backup_config_notification_settings(self, backup_task):"""
        "]""测试备份配置通知设置"""
        config = backup_task.get_backup_config()
        # 验证通知配置
        notification = config["notification["]"]": assert "enabled[" in notification[""""
        assert "]]email[" in notification[""""
        assert "]]webhook[" in notification[""""
        # 验证环境变量处理
        expected_enabled = os.getenv("]]BACKUP_NOTIFICATIONS[", "]true[").lower() =="]true[": assert notification["]enabled["] ==expected_enabled["] from prometheus_client import CollectorRegistry"] from prometheus_client import CollectorRegistry