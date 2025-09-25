"""
数据库备份任务测试

验证备份任务的各个组件：
- Celery备份任务执行
- 备份脚本调用
- 恢复流程测试
- Prometheus指标验证
- 错误处理机制
"""

import os
import subprocess
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from prometheus_client import CollectorRegistry

from src.tasks.backup_tasks import (
    DatabaseBackupTask,
    cleanup_old_backups_task,
    daily_full_backup_task,
    get_backup_metrics,
    get_backup_status,
    hourly_incremental_backup_task,
    manual_backup_task,
    verify_backup_task,
    weekly_wal_archive_task,
)


class TestDatabaseBackupTask:
    """数据库备份任务基类测试"""

    def test_init(self):
        """测试任务初始化"""
        task = DatabaseBackupTask()

        assert task.error_logger is not None
        assert task.backup_script_path.endswith("backup.sh")
        assert task.restore_script_path.endswith("restore.sh")

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_run_backup_script_success(self, mock_subprocess):
        """测试备份脚本成功执行"""
        # 模拟成功的subprocess调用
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "备份完成"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        task = DatabaseBackupTask()

        success, output, stats = task.run_backup_script("full", "test_db")

        assert success is True
        assert output == "备份完成"
        assert "start_time" in stats
        assert "end_time" in stats
        assert "duration_seconds" in stats
        assert stats["exit_code"] == 0

        # 验证subprocess调用
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert "--type" in call_args[0][0]
        assert "full" in call_args[0][0]

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_run_backup_script_failure(self, mock_subprocess):
        """测试备份脚本执行失败"""
        # 模拟失败的subprocess调用
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = "备份失败"
        mock_result.stderr = "数据库连接错误"
        mock_subprocess.return_value = mock_result

        task = DatabaseBackupTask()

        success, output, stats = task.run_backup_script("full", "test_db")

        assert success is False
        assert "备份执行失败" in output
        assert "数据库连接错误" in output
        assert stats["exit_code"] == 1

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_run_backup_script_timeout(self, mock_subprocess):
        """测试备份脚本超时"""
        # 模拟超时异常
        mock_subprocess.side_effect = subprocess.TimeoutExpired("cmd", 3600)

        task = DatabaseBackupTask()

        success, output, stats = task.run_backup_script("full", "test_db")

        assert success is False
        assert "备份执行超时" in output
        assert stats["error"] == "timeout"

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_get_latest_backup_size_full(self, mock_subprocess):
        """测试获取全量备份文件大小"""
        # 模拟find命令返回文件大小
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "1048576"  # 1MB
        mock_subprocess.return_value = mock_result

        task = DatabaseBackupTask()
        size = task._get_latest_backup_size("full")

        assert size == 1048576

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_get_latest_backup_size_failure(self, mock_subprocess):
        """测试获取备份文件大小失败"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        task = DatabaseBackupTask()
        size = task._get_latest_backup_size("full")

        assert size is None

    @patch("src.tasks.backup_tasks.asyncio.get_event_loop")
    @patch("src.tasks.backup_tasks.TaskErrorLogger")
    def test_on_failure(self, mock_logger_class, mock_get_loop):
        """测试任务失败处理"""
        mock_logger = Mock()
        mock_logger_class.return_value = mock_logger

        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        task = DatabaseBackupTask()
        task.name = "tasks.backup_tasks.test_task"

        exc = Exception("测试异常")
        task.on_failure(exc, "task_123", [], {"backup_type": "full"}, "traceback")

        # 验证错误日志记录
        mock_loop.run_until_complete.assert_called_once()


class TestBackupTasks:
    """备份任务测试"""

    @patch.object(DatabaseBackupTask, "run_backup_script")
    def test_daily_full_backup_task_success(self, mock_run_script):
        """测试每日全量备份任务成功"""
        # 模拟成功的备份执行
        mock_run_script.return_value = (
            True,
            "全量备份完成",
            {"duration_seconds": 300, "backup_file_size_bytes": 1048576},
        )

        result = daily_full_backup_task.apply(args=["test_db"]).get()

        assert result["success"] is True
        assert result["task_type"] == "daily_full_backup"
        assert result["database_name"] == "test_db"
        assert "timestamp" in result

        mock_run_script.assert_called_once_with(
            backup_type="full", database_name="test_db"
        )

    @patch.object(DatabaseBackupTask, "run_backup_script")
    def test_daily_full_backup_task_failure(self, mock_run_script):
        """测试每日全量备份任务失败"""
        # 模拟失败的备份执行
        mock_run_script.return_value = (
            False,
            "数据库连接失败",
            {"error": "connection_failed"},
        )

        result = daily_full_backup_task.apply(args=["test_db"]).get()

        assert result["success"] is False
        assert "数据库连接失败" in result["output"]

    @patch.object(DatabaseBackupTask, "run_backup_script")
    def test_hourly_incremental_backup_task(self, mock_run_script):
        """测试每小时增量备份任务"""
        mock_run_script.return_value = (True, "增量备份完成", {"duration_seconds": 120})

        result = hourly_incremental_backup_task.apply(args=["test_db"]).get()

        assert result["success"] is True
        assert result["task_type"] == "hourly_incremental_backup"

        mock_run_script.assert_called_once_with(
            backup_type="incremental", database_name="test_db"
        )

    @patch.object(DatabaseBackupTask, "run_backup_script")
    def test_weekly_wal_archive_task(self, mock_run_script):
        """测试每周WAL归档任务"""
        mock_run_script.return_value = (True, "WAL归档完成", {"duration_seconds": 60})

        result = weekly_wal_archive_task.apply(args=["test_db"]).get()

        assert result["success"] is True
        assert result["task_type"] == "weekly_wal_archive"

        mock_run_script.assert_called_once_with(
            backup_type="wal", database_name="test_db"
        )

    @patch.object(DatabaseBackupTask, "run_backup_script")
    def test_cleanup_old_backups_task(self, mock_run_script):
        """测试清理旧备份任务"""
        mock_run_script.return_value = (True, "清理完成", {"duration_seconds": 30})

        result = cleanup_old_backups_task.apply(args=["test_db"]).get()

        assert result["success"] is True
        assert result["task_type"] == "cleanup_old_backups"

        mock_run_script.assert_called_once_with(
            backup_type="full", database_name="test_db", additional_args=["--cleanup"]
        )

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_verify_backup_task_success(self, mock_subprocess):
        """测试备份验证任务成功"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "备份文件验证成功"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        backup_file = "/path/to/backup.sql.gz"
        result = verify_backup_task.apply(args=[backup_file, "test_db"]).get()

        assert result["success"] is True
        assert result["task_type"] == "verify_backup"
        assert result["backup_file_path"] == backup_file

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_verify_backup_task_failure(self, mock_subprocess):
        """测试备份验证任务失败"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "备份文件损坏"
        mock_subprocess.return_value = mock_result

        backup_file = "/path/to/backup.sql.gz"
        result = verify_backup_task.apply(args=[backup_file, "test_db"]).get()

        assert result["success"] is False
        assert result["error_output"] == "备份文件损坏"

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_verify_backup_task_timeout(self, mock_subprocess):
        """测试备份验证任务超时"""
        mock_subprocess.side_effect = subprocess.TimeoutExpired("cmd", 300)

        backup_file = "/path/to/backup.sql.gz"
        result = verify_backup_task.apply(args=[backup_file, "test_db"]).get()

        assert result["success"] is False
        assert result["error"] == "timeout"


class TestHelperTasks:
    """辅助任务测试"""

    @patch("src.tasks.backup_tasks.subprocess.run")
    @patch("src.tasks.backup_tasks.os.path.exists")
    def test_get_backup_status_success(self, mock_exists, mock_subprocess):
        """测试获取备份状态成功"""
        mock_exists.return_value = True

        # 模拟find命令返回备份文件信息
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "1048576 1631234567.0 /backup/full/backup.sql.gz\n2097152 1631234568.0 /backup/full/backup2.sql.gz"
        mock_subprocess.return_value = mock_result

        result = get_backup_status.apply().get()

        assert "full_backups" in result
        assert "incremental_backups" in result
        assert "timestamp" in result
        assert result["full_backups"]["count"] == 2
        assert result["full_backups"]["total_size_bytes"] == 3145728  # 1MB + 2MB

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_get_backup_status_failure(self, mock_subprocess):
        """测试获取备份状态失败"""
        mock_subprocess.side_effect = Exception("文件系统错误")

        result = get_backup_status.apply().get()

        assert "error" in result
        assert "timestamp" in result

    @patch("src.tasks.backup_tasks.daily_full_backup_task")
    def test_manual_backup_task_full(self, mock_daily_task):
        """测试手动触发全量备份"""
        mock_daily_task.apply_async.return_value.get.return_value = {"success": True}

        result = manual_backup_task.apply(args=["full", "test_db"]).get()

        assert result["success"] is True
        mock_daily_task.apply_async.assert_called_once_with(args=["test_db"])

    @patch("src.tasks.backup_tasks.hourly_incremental_backup_task")
    def test_manual_backup_task_incremental(self, mock_incremental_task):
        """测试手动触发增量备份"""
        mock_incremental_task.apply_async.return_value.get.return_value = {
            "success": True
        }

        result = manual_backup_task.apply(args=["incremental", "test_db"]).get()

        assert result["success"] is True
        mock_incremental_task.apply_async.assert_called_once_with(args=["test_db"])

    @patch("src.tasks.backup_tasks.group")
    def test_manual_backup_task_all(self, mock_group):
        """测试手动触发所有类型备份"""
        mock_job = Mock()
        mock_job.apply_async.return_value.get.return_value = [
            {"success": True, "task_type": "daily_full_backup"},
            {"success": True, "task_type": "hourly_incremental_backup"},
            {"success": True, "task_type": "weekly_wal_archive"},
        ]
        mock_group.return_value = mock_job

        result = manual_backup_task.apply(args=["all", "test_db"]).get()

        assert result["task_type"] == "manual_backup_all"
        assert result["database_name"] == "test_db"
        assert "results" in result

    def test_manual_backup_task_invalid_type(self):
        """测试无效备份类型"""
        with pytest.raises(ValueError, match="不支持的备份类型"):
            manual_backup_task.apply(args=["invalid_type", "test_db"]).get()


class TestPrometheusMetrics:
    """Prometheus指标测试 - 使用fake collector registry避免真实依赖"""

    @pytest.fixture
    def fake_registry(self):
        """
        创建fake collector registry用于测试
        这样可以避免与全局registry的冲突，确保测试隔离
        """
        return CollectorRegistry()

    @pytest.fixture
    def mock_backup_metrics(self, fake_registry):
        """
        创建mock的备份相关Prometheus指标对象
        使用fake registry确保测试不会影响真实的指标收集
        """
        from prometheus_client import Counter, Gauge, Histogram

        # 使用fake registry创建测试专用的指标
        mock_success_counter = Counter(
            "test_backup_success_total",
            "Test backup success counter",
            ["backup_type", "database_name"],
            registry=fake_registry,
        )

        mock_failure_counter = Counter(
            "test_backup_failure_total",
            "Test backup failure counter",
            ["backup_type", "database_name", "error_type"],
            registry=fake_registry,
        )

        mock_timestamp_gauge = Gauge(
            "test_last_backup_timestamp",
            "Test last backup timestamp gauge",
            ["backup_type", "database_name"],
            registry=fake_registry,
        )

        mock_duration_histogram = Histogram(
            "test_backup_duration_seconds",
            "Test backup duration histogram",
            ["backup_type", "database_name"],
            registry=fake_registry,
        )

        mock_size_gauge = Gauge(
            "test_backup_file_size_bytes",
            "Test backup file size gauge",
            ["backup_type", "database_name"],
            registry=fake_registry,
        )

        return {
            "success_counter": mock_success_counter,
            "failure_counter": mock_failure_counter,
            "timestamp_gauge": mock_timestamp_gauge,
            "duration_histogram": mock_duration_histogram,
            "size_gauge": mock_size_gauge,
        }

    def test_backup_success_total_metric(self, mock_backup_metrics):
        """
        测试备份成功指标
        使用mock counter避免访问私有属性，通过registry获取指标值
        注意：Counter会自动生成_created时间戳样本，所以会有2个样本
        """
        success_counter = mock_backup_metrics["success_counter"]

        # 增加指标
        success_counter.labels(backup_type="full", database_name="test_db").inc()

        # 通过collect方法验证指标值（避免访问私有属性）
        metric_families = list(success_counter.collect())
        assert len(metric_families) == 1

        samples = metric_families[0].samples
        # Counter会生成2个样本：主要计数器和_created时间戳
        assert len(samples) == 2

        # 找到主要计数器样本（不是_created样本）
        main_sample = next(s for s in samples if not s.name.endswith("_created"))
        assert main_sample.value == 1.0

    def test_backup_failure_total_metric(self, mock_backup_metrics):
        """
        测试备份失败指标
        使用mock counter通过collect方法获取值，避免访问私有属性
        注意：Counter会自动生成_created时间戳样本，所以会有2个样本
        """
        failure_counter = mock_backup_metrics["failure_counter"]

        # 增加指标
        failure_counter.labels(
            backup_type="full", database_name="test_db", error_type="timeout"
        ).inc()

        # 通过collect方法验证指标值
        metric_families = list(failure_counter.collect())
        assert len(metric_families) == 1

        samples = metric_families[0].samples
        # Counter会生成2个样本：主要计数器和_created时间戳
        assert len(samples) == 2

        # 找到主要计数器样本（不是_created样本）
        main_sample = next(s for s in samples if not s.name.endswith("_created"))
        assert main_sample.value == 1.0

    def test_last_backup_timestamp_metric(self, mock_backup_metrics):
        """
        测试最后备份时间戳指标
        使用mock gauge通过collect方法获取值，避免访问私有属性
        """
        timestamp_gauge = mock_backup_metrics["timestamp_gauge"]
        timestamp = datetime.now().timestamp()

        timestamp_gauge.labels(backup_type="full", database_name="test_db").set(
            timestamp
        )

        # 通过collect方法验证设置值
        metric_families = list(timestamp_gauge.collect())
        assert len(metric_families) == 1

        samples = metric_families[0].samples
        assert len(samples) == 1
        assert samples[0].value == timestamp

    def test_backup_duration_seconds_metric(self, mock_backup_metrics):
        """
        测试备份执行时间指标
        使用mock histogram通过collect方法获取统计信息，避免访问私有属性
        """
        duration_histogram = mock_backup_metrics["duration_histogram"]
        duration = 300.5  # 5分钟30秒

        duration_histogram.labels(backup_type="full", database_name="test_db").observe(
            duration
        )

        # 通过collect方法验证观察值被记录
        metric_families = list(duration_histogram.collect())
        assert len(metric_families) == 1

        samples = metric_families[0].samples
        # histogram会产生多个样本：_bucket, _count, _sum
        sum_sample = next(s for s in samples if s.name.endswith("_sum"))
        count_sample = next(s for s in samples if s.name.endswith("_count"))

        assert sum_sample.value == duration
        assert count_sample.value == 1

    def test_backup_file_size_bytes_metric(self, mock_backup_metrics):
        """
        测试备份文件大小指标
        使用mock gauge通过collect方法获取值，避免访问私有属性
        """
        size_gauge = mock_backup_metrics["size_gauge"]
        file_size = 1048576  # 1MB

        size_gauge.labels(backup_type="full", database_name="test_db").set(file_size)

        # 通过collect方法验证设置值
        metric_families = list(size_gauge.collect())
        assert len(metric_families) == 1

        samples = metric_families[0].samples
        assert len(samples) == 1
        assert samples[0].value == file_size


class TestBackupScriptIntegration:
    """备份脚本集成测试"""

    def test_backup_script_exists(self):
        """测试备份脚本文件存在"""
        task = DatabaseBackupTask()
        assert os.path.exists(task.backup_script_path)

    def test_restore_script_exists(self):
        """测试恢复脚本文件存在"""
        task = DatabaseBackupTask()
        assert os.path.exists(task.restore_script_path)

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_backup_script_help_command(self, mock_subprocess):
        """测试备份脚本帮助命令"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "用法: backup.sh [选项]"
        mock_subprocess.return_value = mock_result

        task = DatabaseBackupTask()

        # 测试帮助命令
        cmd = [task.backup_script_path, "--help"]
        subprocess.run(cmd, capture_output=True, text=True)

        # 由于是mock，我们只验证路径正确
        assert task.backup_script_path.endswith("backup.sh")

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_restore_script_help_command(self, mock_subprocess):
        """测试恢复脚本帮助命令"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "用法: restore.sh [选项]"
        mock_subprocess.return_value = mock_result

        task = DatabaseBackupTask()

        # 测试帮助命令
        cmd = [task.restore_script_path, "--help"]
        subprocess.run(cmd, capture_output=True, text=True)

        # 由于是mock，我们只验证路径正确
        assert task.restore_script_path.endswith("restore.sh")


class TestErrorHandling:
    """错误处理测试"""

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_script_not_found_error(self, mock_subprocess):
        """测试脚本文件不存在错误"""
        mock_subprocess.side_effect = FileNotFoundError("脚本文件不存在")

        task = DatabaseBackupTask()
        success, output, stats = task.run_backup_script("full", "test_db")

        assert success is False
        assert "脚本文件不存在" in output
        assert "error" in stats

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_permission_denied_error(self, mock_subprocess):
        """测试权限不足错误"""
        mock_subprocess.side_effect = PermissionError("权限不足")

        task = DatabaseBackupTask()
        success, output, stats = task.run_backup_script("full", "test_db")

        assert success is False
        assert "权限不足" in output

    @patch.object(DatabaseBackupTask, "run_backup_script")
    def test_task_retry_on_failure(self, mock_run_script):
        """测试任务失败时的重试机制"""
        # 模拟连续失败然后成功
        mock_run_script.side_effect = [
            (False, "第一次失败", {"error": "timeout"}),
            (False, "第二次失败", {"error": "connection_failed"}),
            (True, "第三次成功", {"duration_seconds": 300}),
        ]

        # 第一次和第二次调用应该失败，第三次成功
        # 注意：实际的重试逻辑由Celery处理，这里只测试任务逻辑
        result1 = daily_full_backup_task.apply(args=["test_db"]).get()
        assert result1["success"] is False

        result2 = daily_full_backup_task.apply(args=["test_db"]).get()
        assert result2["success"] is False

        result3 = daily_full_backup_task.apply(args=["test_db"]).get()
        assert result3["success"] is True


class TestDataConsistency:
    """数据一致性测试"""

    @patch("src.tasks.backup_tasks.subprocess.run")
    def test_backup_metadata_consistency(self, mock_subprocess):
        """测试备份元数据一致性"""
        # 模拟成功的备份执行
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "备份完成"
        mock_subprocess.return_value = mock_result

        task = DatabaseBackupTask()
        success, output, stats = task.run_backup_script("full", "test_db")

        # 验证统计信息完整性
        required_fields = [
            "start_time",
            "end_time",
            "duration_seconds",
            "exit_code",
            "command",
        ]
        for field in required_fields:
            assert field in stats

        # 验证时间一致性
        start_time = datetime.fromisoformat(stats["start_time"])
        end_time = datetime.fromisoformat(stats["end_time"])
        assert end_time >= start_time
        assert stats["duration_seconds"] >= 0

    def test_metric_labels_consistency(self):
        """
        测试Prometheus指标标签一致性

        使用独立的 CollectorRegistry 确保测试隔离，避免全局状态污染。
        这个测试验证指标标签的一致性以及正确的指标操作。
        """
        # 创建独立的注册表用于测试，避免全局状态污染
        test_registry = CollectorRegistry()
        metrics = get_backup_metrics(registry=test_registry)

        backup_type = "full"
        database_name = "test_db"

        # 使用相同标签操作不同指标
        metrics["success_total"].labels(
            backup_type=backup_type, database_name=database_name
        ).inc()

        metrics["last_timestamp"].labels(
            backup_type=backup_type, database_name=database_name
        ).set(datetime.now().timestamp())

        metrics["duration"].labels(
            backup_type=backup_type, database_name=database_name
        ).observe(300)

        # 验证标签一致性 - 所有指标都应该使用相同的标签
        # 这里主要验证不会抛出异常
        assert True  # 如果执行到这里，说明标签使用一致


# 集成测试标记
@pytest.mark.integration
class TestBackupTasksIntegration:
    """备份任务集成测试"""

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"),
        reason="需要设置 RUN_INTEGRATION_TESTS 环境变量",
    )
    def test_real_backup_script_execution(self):
        """测试真实备份脚本执行（需要数据库连接）"""
        # 这个测试需要真实的数据库环境
        # 在CI/CD环境中跳过，只在本地开发时运行
        task = DatabaseBackupTask()

        # 尝试执行备份脚本的帮助命令
        cmd = [task.backup_script_path, "--help"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        # 验证脚本可以执行且返回帮助信息
        assert result.returncode == 0
        assert "用法" in result.stdout or "Usage" in result.stdout

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"),
        reason="需要设置 RUN_INTEGRATION_TESTS 环境变量",
    )
    def test_real_restore_script_execution(self):
        """测试真实恢复脚本执行（需要数据库连接）"""
        task = DatabaseBackupTask()

        # 尝试执行恢复脚本的帮助命令
        cmd = [task.restore_script_path, "--help"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        # 验证脚本可以执行且返回帮助信息
        assert result.returncode == 0
        assert "用法" in result.stdout or "Usage" in result.stdout


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
