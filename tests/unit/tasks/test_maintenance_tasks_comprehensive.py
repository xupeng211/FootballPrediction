"""
Maintenance Tasks 综合测试
提升 tasks 模块覆盖率的关键测试
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import tempfile
import os

# 测试导入
import sys
sys.path.insert(0, 'src')

try:
    from src.tasks.maintenance_tasks import (
        MaintenanceTaskManager,
        DatabaseCleanupTask,
        CacheCleanupTask,
        LogRotationTask,
        BackupTask,
        SystemHealthCheckTask
    )
    TASKS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import maintenance tasks: {e}")
    TASKS_AVAILABLE = False


@pytest.mark.skipif(not TASKS_AVAILABLE, reason="Maintenance tasks not available")
class TestMaintenanceTasks:
    """维护任务测试"""

    @pytest.fixture
    def task_manager(self):
        """创建任务管理器"""
        with patch('src.tasks.maintenance_tasks.database'), \
             patch('src.tasks.maintenance_tasks.redis_client'):
            manager = MaintenanceTaskManager()
            return manager

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.query = Mock()
        session.delete = Mock()
        return session

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端"""
        redis = AsyncMock()
        redis.flushdb = AsyncMock()
        redis.keys = AsyncMock(return_value=[])
        redis.delete = AsyncMock()
        return redis

    def test_task_manager_initialization(self, task_manager):
        """测试任务管理器初始化"""
        assert hasattr(task_manager, 'tasks')
        assert hasattr(task_manager, 'scheduler')
        assert hasattr(task_manager, 'logger')

    @pytest.mark.asyncio
    async def test_database_cleanup_task(self, task_manager, mock_db_session):
        """测试数据库清理任务"""
        task = DatabaseCleanupTask()

        with patch('src.tasks.maintenance_tasks.get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_db_session
            # 模拟删除过期数据
            mock_db_session.execute.return_value.rowcount = 100

        result = await task.execute()

        assert result is True
        assert "deleted_records" in result
        assert result["deleted_records"] >= 0

    @pytest.mark.asyncio
    async def test_cache_cleanup_task(self, task_manager, mock_redis_client):
        """测试缓存清理任务"""
        task = CacheCleanupTask()

        with patch('src.tasks.maintenance_tasks.redis_client', mock_redis_client):
            # 模拟Redis中的过期键
            mock_redis_client.keys.return_value = [b"expired:1", b"expired:2"]
            mock_redis_client.delete.return_value = 2

        result = await task.execute()

        assert result is True
        assert "deleted_keys" in result
        assert result["deleted_keys"] == 2

    @pytest.mark.asyncio
    async def test_log_rotation_task(self, task_manager):
        """测试日志轮转任务"""
        task = LogRotationTask()

        # 创建临时日志文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("Test log content\n" * 1000)
            log_file = f.name

        try:
            with patch('src.tasks.maintenance_tasks.LOG_DIR', os.path.dirname(log_file)):
                result = await task.execute()

            assert result is True
            assert "rotated_files" in result
        finally:
            # 清理临时文件
            if os.path.exists(log_file):
                os.unlink(log_file)

    @pytest.mark.asyncio
    async def test_backup_task(self, task_manager):
        """测试备份任务"""
        task = BackupTask()

        with patch('src.tasks.maintenance_tasks.create_database_backup') as mock_backup, \
             patch('src.tasks.maintenance_tasks.upload_to_cloud_storage') as mock_upload:

            mock_backup.return_value = "/backup/path/backup_20240101.sql"
            mock_upload.return_value = True

        result = await task.execute()

        assert result is True
        assert "backup_file" in result
        assert "uploaded" in result

    @pytest.mark.asyncio
    async def test_system_health_check_task(self, task_manager):
        """测试系统健康检查任务"""
        task = SystemHealthCheckTask()

        with patch('src.tasks.maintenance_tasks.check_database_health') as mock_db_health, \
             patch('src.tasks.maintenance_tasks.check_redis_health') as mock_redis_health, \
             patch('src.tasks.maintenance_tasks.check_disk_space') as mock_disk:

            mock_db_health.return_value = {"status": "healthy", "connections": 5}
            mock_redis_health.return_value = {"status": "healthy", "memory": "100MB"}
            mock_disk.return_value = {"status": "healthy", "usage": "40%"}

        result = await task.execute()

        assert result is True
        assert "database" in result
        assert "redis" in result
        assert "disk" in result
        assert result["database"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_task_scheduling(self, task_manager):
        """测试任务调度"""
        task = DatabaseCleanupTask()

        # 模拟任务执行
        with patch.object(task, 'execute') as mock_execute:
            mock_execute.return_value = True

        # 添加到调度器
        task_manager.add_task(task, schedule="0 2 * * *")  # 每天凌晨2点

        assert task in task_manager.tasks
        assert task_manager.tasks[task]["schedule"] == "0 2 * * *"

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, task_manager):
        """测试并发任务执行"""
        tasks = [
            DatabaseCleanupTask(),
            CacheCleanupTask(),
            SystemHealthCheckTask()
        ]

        # 模拟所有任务成功执行
        for task in tasks:
            with patch.object(task, 'execute') as mock_execute:
                mock_execute.return_value = True

        results = await task_manager.execute_tasks(tasks)

        assert len(results) == len(tasks)
        assert all(result is True for result in results)

    @pytest.mark.asyncio
    async def test_task_failure_handling(self, task_manager):
        """测试任务失败处理"""
        failing_task = DatabaseCleanupTask()

        with patch.object(failing_task, 'execute') as mock_execute:
            mock_execute.side_effect = Exception("Task failed")

        result = await failing_task.execute()

        assert result is False
        # 应该记录错误日志

    def test_task_configuration_validation(self):
        """测试任务配置验证"""
        # 有效配置
        valid_config = {
            "schedule": "0 2 * * *",
            "timeout": 3600,
            "retry_attempts": 3,
            "enabled": True
        }

        assert DatabaseCleanupTask.validate_config(valid_config) is True

        # 无效配置 - 缺少必需字段
        invalid_config = {
            "timeout": 3600,
            "retry_attempts": 3
        }

        assert DatabaseCleanupTask.validate_config(invalid_config) is False

    @pytest.mark.asyncio
    async def test_task_dependency_management(self, task_manager):
        """测试任务依赖管理"""
        cleanup_task = DatabaseCleanupTask()
        backup_task = BackupTask()

        # 设置依赖：备份任务依赖清理任务
        backup_task.add_dependency(cleanup_task)

        assert cleanup_task in backup_task.dependencies

        # 执行任务（应该先执行依赖）
        with patch.object(cleanup_task, 'execute') as mock_cleanup, \
             patch.object(backup_task, 'execute') as mock_backup:

            mock_cleanup.return_value = True
            mock_backup.return_value = True

        result = await task_manager.execute_task_with_dependencies(backup_task)

        assert result is True
        mock_cleanup.assert_called_once()
        mock_backup.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_timeout_handling(self, task_manager):
        """测试任务超时处理"""
        task = DatabaseCleanupTask()

        with patch.object(task, 'execute') as mock_execute:
            # 模拟长时间运行的任务
            async def long_running_task():
                await asyncio.sleep(5)  # 模拟长时间运行
                return True

            mock_execute.side_effect = long_running_task

        # 设置短超时
        result = await task_manager.execute_task_with_timeout(task, timeout=1.0)

        assert result is False
        # 应该记录超时错误

    @pytest.mark.asyncio
    async def test_task_retry_mechanism(self, task_manager):
        """测试任务重试机制"""
        task = DatabaseCleanupTask()

        with patch.object(task, 'execute') as mock_execute:
            # 前两次失败，第三次成功
            mock_execute.side_effect = [
                Exception("First failure"),
                Exception("Second failure"),
                True
            ]

        result = await task_manager.execute_task_with_retry(task, max_attempts=3)

        assert result is True
        assert mock_execute.call_count == 3

    def test_task_metrics_collection(self, task_manager):
        """测试任务指标收集"""
        task = DatabaseCleanupTask()

        # 模拟任务执行历史
        task_manager.record_task_execution(task, success=True, duration=10.5)
        task_manager.record_task_execution(task, success=False, duration=5.2)
        task_manager.record_task_execution(task, success=True, duration=8.3)

        metrics = task_manager.get_task_metrics(task)

        assert "total_executions" in metrics
        assert "success_rate" in metrics
        assert "average_duration" in metrics
        assert metrics["total_executions"] == 3
        assert metrics["success_rate"] == 2/3

    @pytest.mark.asyncio
    async def test_maintenance_workflow(self, task_manager):
        """测试完整维护工作流"""
        workflow_tasks = [
            DatabaseCleanupTask(),
            CacheCleanupTask(),
            LogRotationTask(),
            SystemHealthCheckTask()
        ]

        # 模拟所有任务成功
        for task in workflow_tasks:
            with patch.object(task, 'execute') as mock_execute:
                mock_execute.return_value = True

        workflow_result = await task_manager.execute_maintenance_workflow()

        assert workflow_result["success"] is True
        assert "executed_tasks" in workflow_result
        assert "failed_tasks" in workflow_result
        assert len(workflow_result["executed_tasks"]) == len(workflow_tasks)
        assert len(workflow_result["failed_tasks"]) == 0

    @pytest.mark.asyncio
    async def test_maintenance_notifications(self, task_manager):
        """测试维护通知"""
        task = DatabaseCleanupTask()

        with patch.object(task_manager, 'send_notification') as mock_notify:
            # 成功通知
            await task_manager.notify_task_success(task, {"deleted_records": 100})
            mock_notify.assert_called_once()

            mock_notify.reset_mock()
            # 失败通知
            await task_manager.notify_task_failure(task, Exception("Task failed"))
            mock_notify.assert_called_once()

    def test_task_configuration_from_file(self, task_manager):
        """测试从文件加载任务配置"""
        config_data = {
            "database_cleanup": {
                "schedule": "0 2 * * *",
                "enabled": True,
                "retention_days": 30
            },
            "cache_cleanup": {
                "schedule": "0 3 * * *",
                "enabled": True
            }
        }

        with patch('src.tasks.maintenance_tasks.load_config_from_file') as mock_load:
            mock_load.return_value = config_data

        loaded_tasks = task_manager.load_tasks_from_config()

        assert "database_cleanup" in loaded_tasks
        assert "cache_cleanup" in loaded_tasks


@pytest.mark.skipif(not TASKS_AVAILABLE, reason="Maintenance tasks not available")
class TestTaskErrorScenarios:
    """维护任务错误场景测试"""

    @pytest.fixture
    def task_manager(self):
        """创建任务管理器"""
        with patch('src.tasks.maintenance_tasks.database'), \
             patch('src.tasks.maintenance_tasks.redis_client'):
            return MaintenanceTaskManager()

    @pytest.mark.asyncio
    async def test_database_connection_failure(self, task_manager):
        """测试数据库连接失败"""
        task = DatabaseCleanupTask()

        with patch('src.tasks.maintenance_tasks.get_db_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

        result = await task.execute()
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, task_manager):
        """测试Redis连接失败"""
        task = CacheCleanupTask()

        with patch('src.tasks.maintenance_tasks.redis_client') as mock_redis:
            mock_redis.flushdb.side_effect = Exception("Redis connection failed")

        result = await task.execute()
        assert result is False

    @pytest.mark.asyncio
    async def test_file_permission_error(self, task_manager):
        """测试文件权限错误"""
        task = LogRotationTask()

        with patch('src.tasks.maintenance_tasks.os.chmod') as mock_chmod:
            mock_chmod.side_effect = PermissionError("Permission denied")

        result = await task.execute()
        assert result is False

    @pytest.mark.asyncio
    async def test_disk_space_insufficient(self, task_manager):
        """测试磁盘空间不足"""
        task = BackupTask()

        with patch('src.tasks.maintenance_tasks.check_disk_space') as mock_check:
            mock_check.return_value = {"available": "1GB", "required": "10GB"}

        result = await task.execute()
        assert result is False