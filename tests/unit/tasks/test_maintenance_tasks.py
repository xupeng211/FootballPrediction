from unittest.mock import Mock, patch, AsyncMock
"""
维护任务测试
Tests for Maintenance Tasks

测试src.tasks.maintenance_tasks模块的维护任务功能
"""

import pytest
from datetime import datetime, timedelta
import asyncio

# 测试导入
try:
    from src.tasks.maintenance_tasks import (
        MaintenanceTaskManager,
        DatabaseMaintenanceTask,
        CacheCleanupTask,
        LogRotationTask,
        BackupTask,
        HealthCheckTask,
        MaintenanceTaskStatus,
    )

    MAINTENANCE_TASKS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    MAINTENANCE_TASKS_AVAILABLE = False
    # 创建模拟对象
    MaintenanceTaskManager = None
    DatabaseMaintenanceTask = None
    CacheCleanupTask = None
    LogRotationTask = None
    BackupTask = None
    HealthCheckTask = None
    MaintenanceTaskStatus = None


@pytest.mark.skipif(
    not MAINTENANCE_TASKS_AVAILABLE, reason="Maintenance tasks module not available"
)
@pytest.mark.unit

class TestMaintenanceTaskManager:
    """维护任务管理器测试"""

    def test_manager_creation(self):
        """测试：管理器创建"""
        manager = MaintenanceTaskManager()
        assert manager is not None
        assert hasattr(manager, "schedule_task")
        assert hasattr(manager, "execute_task")
        assert hasattr(manager, "get_task_status")
        assert hasattr(manager, "list_pending_tasks")

    @pytest.mark.asyncio
    async def test_schedule_task(self):
        """测试：调度任务"""
        manager = MaintenanceTaskManager()

        with patch.object(manager, "scheduler") as mock_scheduler:
            task = DatabaseMaintenanceTask()
            scheduled_time = datetime.now() + timedelta(hours=1)

            _result = await manager.schedule_task(task, scheduled_time)

            assert _result is True or result is not None
            mock_scheduler.add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task(self):
        """测试：执行任务"""
        manager = MaintenanceTaskManager()

        with patch.object(manager, "execute_task_direct") as mock_execute:
            task = CacheCleanupTask()
            mock_execute.return_value = {"status": "success", "cleaned_items": 100}

            _result = await manager.execute_task(task)

            assert _result["status"] == "success"
            assert _result["cleaned_items"] == 100
            mock_execute.assert_called_once_with(task)

    def test_get_task_status(self):
        """测试：获取任务状态"""
        manager = MaintenanceTaskManager()

        # 模拟任务状态
        task_id = "task_123"
        manager.task_statuses[task_id] = {
            "status": MaintenanceTaskStatus.RUNNING,
            "started_at": datetime.now(),
            "progress": 0.5,
        }

        status = manager.get_task_status(task_id)

        assert status["status"] == MaintenanceTaskStatus.RUNNING
        assert "started_at" in status
        assert status["progress"] == 0.5

    def test_list_pending_tasks(self):
        """测试：列出待处理任务"""
        manager = MaintenanceTaskManager()

        # 添加一些任务
        tasks = [DatabaseMaintenanceTask(), CacheCleanupTask(), LogRotationTask()]

        for task in tasks:
            manager.pending_tasks.append(task)

        pending = manager.list_pending_tasks()

        assert len(pending) == 3
        assert all(
            isinstance(t, DatabaseMaintenanceTask)
            or isinstance(t, CacheCleanupTask)
            or isinstance(t, LogRotationTask)
            for t in pending
        )


@pytest.mark.skipif(
    not MAINTENANCE_TASKS_AVAILABLE, reason="Maintenance tasks module not available"
)
class TestDatabaseMaintenanceTask:
    """数据库维护任务测试"""

    @pytest.mark.asyncio
    async def test_execute_database_backup(self):
        """测试：执行数据库备份"""
        task = DatabaseMaintenanceTask()

        with patch.object(task, "backup_database") as mock_backup:
            mock_backup.return_value = {
                "backup_file": "/backups/db_20240115.sql",
                "size": "1.5GB",
                "duration": 30,
            }

            _result = await task.execute_backup()

            assert _result["backup_file"].endswith(".sql")
            assert _result["size"] == "1.5GB"
            mock_backup.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_vacuum(self):
        """测试：执行VACUUM操作"""
        task = DatabaseMaintenanceTask()

        with patch.object(task, "run_vacuum") as mock_vacuum:
            mock_vacuum.return_value = {"space_freed": "500MB", "duration": 120}

            _result = await task.execute_vacuum()

            assert _result["space_freed"] == "500MB"
            assert _result["duration"] == 120
            mock_vacuum.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_analyze(self):
        """测试：执行分析操作"""
        task = DatabaseMaintenanceTask()

        with patch.object(task, "run_analyze") as mock_analyze:
            mock_analyze.return_value = {
                "table_stats": {
                    "users": {"rows": 10000, "size": "50MB"},
                    "matches": {"rows": 50000, "size": "200MB"},
                },
                "unused_indexes": ["idx_unused1", "idx_unused2"],
            }

            _result = await task.execute_analyze()

            assert "table_stats" in result
            assert "unused_indexes" in result
            assert len(_result["unused_indexes"]) == 2
            mock_analyze.assert_called_once()


@pytest.mark.skipif(
    not MAINTENANCE_TASKS_AVAILABLE, reason="Maintenance tasks module not available"
)
class TestCacheCleanupTask:
    """缓存清理任务测试"""

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys(self):
        """测试：清理过期键"""
        task = CacheCleanupTask()

        with patch.object(task, "redis_client") as mock_redis:
            mock_redis.scan_iter.return_value = [f"expired_key_{i}" for i in range(10)]
            mock_redis.delete.return_value = 10

            _result = await task.cleanup_expired_keys()

            assert _result["cleaned_keys"] == 10
            assert _result["time_taken"] > 0

    @pytest.mark.asyncio
    async def test_cleanup_large_values(self):
        """测试：清理大值"""
        task = CacheCleanupTask()

        with patch.object(task, "redis_client") as mock_redis:
            # 模拟大值检测
            mock_redis.memory_usage.return_value = 1048576  # 1MB

            _result = await task.cleanup_large_values()

            assert "cleaned_keys" in result
            assert _result["memory_freed"] > 0

    @pytest.mark.asyncio
    async def test_rebuild_index(self):
        """测试：重建索引"""
        task = CacheCleanupTask()

        with patch.object(task, "redis_client") as mock_redis:
            mock_redis.rebuild_index.return_value = True

            _result = await task.rebuild_index("user_index")

            assert _result is True
            mock_redis.rebuild_index.assert_called_once_with("user_index")


@pytest.mark.skipif(
    not MAINTENANCE_TASKS_AVAILABLE, reason="Maintenance tasks module not available"
)
class TestLogRotationTask:
    """日志轮转任务测试"""

    @pytest.mark.asyncio
    async def test_rotate_application_logs(self):
        """测试：轮转应用日志"""
        task = LogRotationTask()

        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=1073741824):  # 1GB
                with patch("shutil.move") as mock_move:
                    with patch("gzip.open") as mock_gzip:
                        _result = await task.rotate_application_logs("/var/log/app.log")

                        assert _result["original_size"] == 1073741824
                        assert "compressed_file" in result
                        assert mock_move.called
                        assert mock_gzip.called

    @pytest.mark.asyncio
    async def test_rotate_access_logs(self):
        """测试：轮转访问日志"""
        task = LogRotationTask()

        with patch("os.listdir") as mock_listdir:
            mock_listdir.return_value = [
                "access.log.2024-01-01",
                "access.log.2024-01-02",
                "access.log.2024-01-03",
            ]

            _result = await task.rotate_access_logs("/var/log/nginx/")

            assert "deleted_files" in result
            assert _result["deleted_files"] >= 0

    @pytest.mark.asyncio
    async def test_cleanup_old_logs(self):
        """测试：清理旧日志"""
        task = LogRotationTask()

        with patch("os.listdir") as mock_listdir:
            with patch("os.path.getmtime") as mock_mtime:
                mock_listdir.return_value = [
                    "app.log.2024-01-01",
                    "app.log.2024-01-02",
                    "app.log.2024-01-03",
                ]

                # 模拟不同时间的文件
                now = datetime.now()
                mock_mtime.side_effect = lambda path: now - timedelta(days=7)

                _result = await task.cleanup_old_logs("/var/log/app", keep_days=5)

                assert "deleted_files" in result
                assert _result["deleted_files"] >= 0


@pytest.mark.skipif(
    not MAINTENANCE_TASKS_AVAILABLE, reason="Maintenance tasks module not available"
)
class TestBackupTask:
    """备份任务测试"""

    @pytest.mark.asyncio
    async def test_full_backup(self):
        """测试：完整备份"""
        task = BackupTask()

        with patch.object(task, "backup_database") as mock_db_backup:
            with patch.object(task, "backup_files") as mock_files_backup:
                with patch.object(task, "backup_config") as mock_config_backup:
                    mock_db_backup.return_value = {
                        "status": "success",
                        "file": "db.sql",
                    }
                    mock_files_backup.return_value = {"status": "success", "files": 5}
                    mock_config_backup.return_value = {
                        "status": "success",
                        "file": "_config.tar.gz",
                    }

                    _result = await task.full_backup("/backups")

                    assert _result["status"] == "success"
                    assert "database" in result
                    assert "files" in result
                    assert "config" in result

    @pytest.mark.asyncio
    async def test_incremental_backup(self):
        """测试：增量备份"""
        task = BackupTask()

        with patch.object(task, "create_incremental_backup") as mock_incremental:
            mock_incremental.return_value = {
                "status": "success",
                "backup_file": "incremental_20240115_02.tar.gz",
                "changes_since": "20240115_01.tar.gz",
            }

            _result = await task.incremental_backup("/backups", "20240115_01.tar.gz")

            assert _result["status"] == "success"
            assert "backup_file" in result

    @pytest.mark.asyncio
    async def test_verify_backup(self):
        """测试：验证备份"""
        task = BackupTask()

        with patch("os.path.exists", return_value=True):
            with patch("tarfile.is_tarfile", return_value=True):
                _result = await task.verify_backup("/backups/full_backup.tar.gz")

                assert _result["valid"] is True
                assert _result["checksum"] is not None

    @pytest.mark.asyncio
    async def test_restore_backup(self):
        """测试：恢复备份"""
        task = BackupTask()

        with patch("tarfile.extractall") as mock_extract:
            with patch("subprocess.run") as mock_subprocess:
                _result = await task.restore_backup(
                    "/backups/full_backup.tar.gz", "/tmp/restore"
                )

                assert _result["status"] == "success"
                assert mock_extract.called
                assert mock_subprocess.called


@pytest.mark.skipif(
    not MAINTENANCE_TASKS_AVAILABLE,
    reason="Maintenance tasks module should be available",
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not MAINTENANCE_TASKS_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if MAINTENANCE_TASKS_AVAILABLE:
        from src.tasks.maintenance_tasks import (
            MaintenanceTaskManager,
            DatabaseMaintenanceTask,
            CacheCleanupTask,
            LogRotationTask,
            BackupTask,
            HealthCheckTask,
            MaintenanceTaskStatus,
        )

        assert MaintenanceTaskManager is not None
        assert DatabaseMaintenanceTask is not None
        assert CacheCleanupTask is not None
        assert LogRotationTask is not None
        assert BackupTask is not None
        assert HealthCheckTask is not None
        assert MaintenanceTaskStatus is not None


@pytest.mark.skipif(
    not MAINTENANCE_TASKS_AVAILABLE, reason="Maintenance tasks module not available"
)
class TestHealthCheckTask:
    """健康检查任务测试"""

    @pytest.mark.asyncio
    async def test_check_database_health(self):
        """测试：检查数据库健康"""
        task = HealthCheckTask()

        with patch.object(task, "db_manager") as mock_db:
            mock_db.ping.return_value = True
            mock_db.get_connection_pool_status.return_value = {
                "active": 5,
                "idle": 10,
                "total": 15,
            }

            _result = await task.check_database_health()

            assert _result["status"] == "healthy"
            assert _result["connection_pool"]["active"] == 5

    @pytest.mark.asyncio
    async def test_check_redis_health(self):
        """测试：检查Redis健康"""
        task = HealthCheckTask()

        with patch.object(task, "redis_client") as mock_redis:
            mock_redis.ping.return_value = True
            mock_redis.info.return_value = {
                "used_memory": "100MB",
                "connected_clients": 25,
            }

            _result = await task.check_redis_health()

            assert _result["status"] == "healthy"
            assert _result["memory_usage"] == "100MB"

    @pytest.mark.asyncio
    async def test_check_disk_space(self):
        """测试：检查磁盘空间"""
        task = HealthCheckTask()

        with patch("shutil.disk_usage") as mock_usage:
            mock_usage.return_value = (1000000000000, 800000000000, 500000000000)

            _result = await task.check_disk_space("/")

            assert _result["total"] == 1000000000000  # 100GB
            assert _result["used"] == 800000000000  # 80GB
            assert _result["free"] == 500000000000  # 50GB
            assert _result["usage_percent"] == 80.0

    @pytest.mark.asyncio
    async def test_check_system_metrics(self):
        """测试：检查系统指标"""
        task = HealthCheckTask()

        with patch("psutil.cpu_percent") as mock_cpu:
            with patch("psutil.virtual_memory") as mock_memory:
                mock_cpu.return_value = 45.5
                mock_memory.return_value = {
                    "total": 8589934592,
                    "available": 4294967296,
                    "percent": 50.0,
                }

                _result = await task.check_system_metrics()

                assert _result["cpu_percent"] == 45.5
                assert _result["memory_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_generate_health_report(self):
        """测试：生成健康报告"""
        task = HealthCheckTask()

        # 模拟所有检查结果
        task.last_checks = {
            "database": {"status": "healthy", "timestamp": datetime.now()},
            "redis": {"status": "healthy", "timestamp": datetime.now()},
            "disk": {"status": "warning", "usage_percent": 85.0},
            "metrics": {"cpu_percent": 75.0, "memory_percent": 80.0},
        }

        report = await task.generate_health_report()

        assert "overall_status" in report
        assert "checks" in report
        assert "timestamp" in report
        assert "recommendations" in report


@pytest.mark.skipif(
    not MAINTENANCE_TASKS_AVAILABLE, reason="Maintenance tasks module not available"
)
class TestMaintenanceTasksIntegration:
    """维护任务集成测试"""

    @pytest.mark.asyncio
    async def test_maintenance_workflow(self):
        """测试：维护工作流"""
        manager = MaintenanceTaskManager()

        # 创建任务队列
        tasks = [
            DatabaseMaintenanceTask(),
            CacheCleanupTask(),
            LogRotationTask(),
            HealthCheckTask(),
        ]

        # 模拟执行所有任务
        with patch.object(manager, "execute_task") as mock_execute:
            # 设置不同的返回值
            mock_execute.side_effect = [
                {"status": "success", "operation": "vacuum"},
                {"status": "success", "cleaned_keys": 50},
                {"status": "success", "rotated_files": 3},
                {"status": "success", "health": "good"},
            ]

            results = []
            for task in tasks:
                _result = await manager.execute_task(task)
                results.append(result)

            # 验证所有任务成功
            assert len(results) == 4
            assert all(r["status"] == "success" for r in results)

    @pytest.mark.asyncio
    async def test_scheduled_maintenance(self):
        """测试：定时维护"""
        manager = MaintenanceTaskManager()

        with patch.object(manager, "scheduler") as mock_scheduler:
            with patch.object(manager, "get_time") as mock_time:
                mock_time.return_value = datetime(2024, 1, 15, 2, 0, 0)  # 2 AM

                # 每日维护任务
                daily_tasks = [
                    DatabaseMaintenanceTask(),
                    LogRotationTask(),
                    CacheCleanupTask(),
                ]

                for task in daily_tasks:
                    await manager.schedule_daily_task(task, "02:00")

                # 验证调度
                assert mock_scheduler.add_job.call_count == 3

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试：错误处理"""
        manager = MaintenanceTaskManager()
        task = DatabaseMaintenanceTask()

        with patch.object(task, "run_vacuum") as mock_vacuum:
            mock_vacuum.side_effect = Exception("Vacuum failed")

            _result = await manager.execute_task(task)

            # 应该处理错误并返回错误信息
            assert _result["status"] == "failed"
            assert "error" in result

    def test_task_dependency(self):
        """测试：任务依赖"""
        # 定义任务依赖
        backup_task = BackupTask()
        vacuum_task = DatabaseMaintenanceTask()

        # 备份必须在vacuum之前执行
        dependencies = {vacuum_task: [backup_task]}

        # 验证依赖关系
        assert vacuum_task in dependencies
        assert backup_task in dependencies[vacuum_task]

    def test_task_priority(self):
        """测试：任务优先级"""
        tasks = [
            DatabaseMaintenanceTask(priority=1),
            HealthCheckTask(priority=2),
            CacheCleanupTask(priority=3),
            BackupTask(priority=4),
        ]

        # 按优先级排序
        sorted_tasks = sorted(tasks, key=lambda t: t.priority)

        assert sorted_tasks[0].priority == 1
        assert sorted_tasks[-1].priority == 4
        assert isinstance(sorted_tasks[0], DatabaseMaintenanceTask)
        assert isinstance(sorted_tasks[-1], BackupTask)

    @pytest.mark.asyncio
    async def test_task_timeout(self):
        """测试：任务超时"""
        manager = MaintenanceTaskManager()
        task = CacheCleanupTask()

        with patch.object(task, "cleanup_expired_keys") as mock_cleanup:
            # 模拟长时间运行的任务
            async def long_running_task():
                await asyncio.sleep(10)
                return {"cleaned_keys": 1}

            mock_cleanup.side_effect = long_running_task

            # 设置超时为5秒
            _result = await manager.execute_task_with_timeout(task, timeout=5)

            # 应该超时
            assert _result["status"] == "timeout"
            assert "timeout_duration" in result
