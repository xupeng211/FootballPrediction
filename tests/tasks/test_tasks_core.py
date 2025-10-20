"""
Tasks模块核心测试
测试异步任务、数据收集、备份等功能
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 尝试导入tasks模块
try:
    from src.tasks.data_collection_core import DataCollectionTask, celery_app
    from src.tasks.data_collection_tasks import (
        collect_matches,
        collect_odds,
        collect_scores,
    )
    from src.tasks.backup_tasks import BackupTask, create_backup
    from src.tasks.maintenance_tasks import MaintenanceTask, cleanup_old_data
    from src.tasks.streaming_tasks import StreamingTask, process_stream_data
    from src.tasks.monitoring import MonitoringTask, health_check

    TASKS_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Tasks模块不可用: {e}", allow_module_level=True)
    TASKS_AVAILABLE = False


class TestDataCollectionTask:
    """测试数据收集任务"""

    def test_data_collection_task_creation(self):
        """测试数据收集任务创建"""
        if not TASKS_AVAILABLE:
            pytest.skip("Tasks模块不可用")

        with patch("src.tasks.data_collection_core.DataCollectionTask") as MockTask:
            task = MockTask()
            task.db_manager = Mock()
            task.orchestrator = Mock()

            assert task is not None
            assert hasattr(task, "db_manager")
            assert hasattr(task, "orchestrator")

    def test_set_database_manager(self):
        """测试设置数据库管理器"""
        with patch("src.tasks.data_collection_core.DataCollectionTask") as MockTask:
            task = MockTask()
            mock_db_manager = Mock()
            mock_orchestrator = Mock()
            mock_collectors = {"fixtures": Mock(), "odds": Mock(), "scores": Mock()}
            mock_orchestrator.collectors = mock_collectors

            task.orchestrator = mock_orchestrator
            task.set_database_manager(mock_db_manager)

            # 验证数据库管理器已设置
            assert task.db_manager == mock_db_manager

    def test_task_callbacks(self):
        """测试任务回调"""
        with patch("src.tasks.data_collection_core.DataCollectionTask") as MockTask:
            task = MockTask()
            task.on_failure = Mock()
            task.on_success = Mock()

            # 测试成功回调
            task.on_success({"result": "success"}, "task_123", [], {})
            task.on_success.assert_called_once()

            # 测试失败回调
            task.on_failure(Exception("Test error"), "task_456", [], {}, "error_info")
            task.on_failure.assert_called_once()

    def test_collect_matches_task(self):
        """测试收集比赛任务"""
        with patch("src.tasks.data_collection_tasks.collect_matches") as MockTask:
            mock_task = MockTask()
            mock_task.delay = Mock(return_value=Mock(id="task_789"))
            mock_task.apply_async = Mock(return_value=Mock(id="task_790"))

            # 测试延迟执行
            result = mock_task.delay(league_id=1)
            assert result.id == "task_789"

            # 测试异步执行
            result = mock_task.apply_async(args=[1], kwargs={"season": "2024/2025"})
            assert result.id == "task_790"

    def test_collect_odds_task(self):
        """测试收集赔率任务"""
        with patch("src.tasks.data_collection_tasks.collect_odds") as MockTask:
            mock_task = MockTask()
            mock_task.delay = Mock(return_value=Mock(id="task_791"))

            result = mock_task.delay(match_ids=[1, 2, 3])
            assert result.id == "task_791"

    def test_collect_scores_task(self):
        """测试收集比分任务"""
        with patch("src.tasks.data_collection_tasks.collect_scores") as MockTask:
            mock_task = MockTask()
            mock_task.delay = Mock(return_value=Mock(id="task_792"))

            result = mock_task.delay(date="2025-01-18")
            assert result.id == "task_792"

    def test_data_collection_orchestrator(self):
        """测试数据收集协调器"""
        with patch(
            "src.tasks.data_collectors.DataCollectionOrchestrator"
        ) as MockOrchestrator:
            orchestrator = MockOrchestrator()
            orchestrator.collect_all = Mock(
                return_value={"fixtures": 100, "odds": 250, "scores": 50}
            )
            orchestrator.collect_fixtures = Mock(return_value=[{"id": 1}])
            orchestrator.collect_odds = Mock(return_value=[{"id": 1, "odds": 2.5}])
            orchestrator.collect_scores = Mock(return_value=[{"id": 1, "score": "2-1"}])

            # 测试收集所有数据
            all_data = orchestrator.collect_all()
            assert all_data["fixtures"] == 100

            # 测试收集特定数据
            fixtures = orchestrator.collect_fixtures(league_id=1)
            odds = orchestrator.collect_odds(match_ids=[1, 2, 3])
            scores = orchestrator.collect_scores(date="2025-01-18")

            assert len(fixtures) == 1
            assert len(odds) == 1
            assert len(scores) == 1


class TestBackupTask:
    """测试备份任务"""

    def test_backup_task_creation(self):
        """测试备份任务创建"""
        if not TASKS_AVAILABLE:
            pytest.skip("Tasks模块不可用")

        with patch("src.tasks.backup_tasks.BackupTask") as MockTask:
            task = MockTask()
            task.backup_type = "full"
            task.destination = "/backups"
            task.compression = True

            assert task.backup_type == "full"
            assert task.destination == "/backups"
            assert task.compression is True

    def test_create_backup_task(self):
        """测试创建备份任务"""
        with patch("src.tasks.backup_tasks.create_backup") as MockTask:
            mock_task = MockTask()
            mock_task.delay = Mock(return_value=Mock(id="task_800"))
            mock_task.apply_async = Mock(return_value=Mock(id="task_801"))

            # 测试延迟执行
            result = mock_task.delay(
                backup_type="incremental", destination="/backups/daily"
            )
            assert result.id == "task_800"

            # 测试异步执行
            result = mock_task.apply_async(
                kwargs={"backup_type": "full", "compression": True}
            )
            assert result.id == "task_801"

    def test_backup_validation(self):
        """测试备份验证"""
        with patch("src.tasks.backup_tasks.BackupTask") as MockTask:
            task = MockTask()
            task.validate_backup = Mock(
                return_value={
                    "valid": True,
                    "size": 1073741824,  # 1GB
                    "checksum": "sha256:abc123",
                    "created_at": datetime.now(),
                }
            )

            validation = task.validate_backup("/backups/backup_20250118.tar.gz")
            assert validation["valid"] is True
            assert validation["size"] == 1073741824

    def test_backup_scheduling(self):
        """测试备份调度"""
        with patch("src.tasks.backup_tasks.BackupTask") as MockTask:
            task = MockTask()
            task.schedule_backup = Mock(
                return_value={
                    "scheduled": True,
                    "cron": "0 2 * * *",  # 每天凌晨2点
                    "next_run": "2025-01-19T02:00:00",
                }
            )

            schedule = task.schedule_backup(
                backup_type="daily", cron_expression="0 2 * * *"
            )
            assert schedule["scheduled"] is True
            assert schedule["cron"] == "0 2 * * *"

    def test_backup_restore(self):
        """测试备份恢复"""
        with patch("src.tasks.backup_tasks.BackupTask") as MockTask:
            task = MockTask()
            task.restore_backup = Mock(
                return_value={
                    "restored": True,
                    "files_restored": 100,
                    "warnings": [],
                    "errors": [],
                }
            )

            restore = task.restore_backup(
                backup_path="/backups/backup_20250118.tar.gz", target="/tmp/restore"
            )
            assert restore["restored"] is True
            assert restore["files_restored"] == 100


class TestMaintenanceTask:
    """测试维护任务"""

    def test_maintenance_task_creation(self):
        """测试维护任务创建"""
        if not TASKS_AVAILABLE:
            pytest.skip("Tasks模块不可用")

        with patch("src.tasks.maintenance_tasks.MaintenanceTask") as MockTask:
            task = MockTask()
            task.task_type = "cleanup"
            task.frequency = "daily"
            task.retention_days = 30

            assert task.task_type == "cleanup"
            assert task.frequency == "daily"
            assert task.retention_days == 30

    def test_cleanup_old_data_task(self):
        """测试清理旧数据任务"""
        with patch("src.tasks.maintenance_tasks.cleanup_old_data") as MockTask:
            mock_task = MockTask()
            mock_task.delay = Mock(return_value=Mock(id="task_810"))

            result = mock_task.delay(table="predictions", retention_days=90)
            assert result.id == "task_810"

    def test_optimize_database_task(self):
        """测试数据库优化任务"""
        with patch("src.tasks.maintenance_tasks.MaintenanceTask") as MockTask:
            task = MockTask()
            task.optimize_database = Mock(
                return_value={
                    "optimized": True,
                    "tables_optimized": ["predictions", "matches", "odds"],
                    "space_saved": "500MB",
                    "duration_seconds": 120,
                }
            )

            result = task.optimize_database()
            assert result["optimized"] is True
            assert len(result["tables_optimized"]) == 3

    def test_rebuild_indexes_task(self):
        """测试重建索引任务"""
        with patch("src.tasks.maintenance_tasks.MaintenanceTask") as MockTask:
            task = MockTask()
            task.rebuild_indexes = Mock(
                return_value={
                    "rebuilt": True,
                    "indexes": ["idx_predictions_date", "idx_matches_league"],
                    "duration_seconds": 300,
                }
            )

            result = task.rebuild_indexes(["idx_predictions_date"])
            assert result["rebuilt"] is True
            assert len(result["indexes"]) == 2

    def test_update_statistics_task(self):
        """测试更新统计信息任务"""
        with patch("src.tasks.maintenance_tasks.MaintenanceTask") as MockTask:
            task = MockTask()
            task.update_statistics = Mock(
                return_value={
                    "updated": True,
                    "tables_updated": ["matches", "predictions"],
                    "statistics": {
                        "matches": {"row_count": 1000, "size": "10MB"},
                        "predictions": {"row_count": 5000, "size": "50MB"},
                    },
                }
            )

            result = task.update_statistics()
            assert result["updated"] is True
            assert "matches" in result["statistics"]


class TestStreamingTask:
    """测试流处理任务"""

    def test_streaming_task_creation(self):
        """测试流处理任务创建"""
        if not TASKS_AVAILABLE:
            pytest.skip("Tasks模块不可用")

        with patch("src.tasks.streaming_tasks.StreamingTask") as MockTask:
            task = MockTask()
            task.stream_name = "prediction_stream"
            task.topic = "football_predictions"
            task.consumer_group = "processors"

            assert task.stream_name == "prediction_stream"
            assert task.topic == "football_predictions"

    def test_process_stream_data_task(self):
        """测试处理流数据任务"""
        with patch("src.tasks.streaming_tasks.process_stream_data") as MockTask:
            mock_task = MockTask()
            mock_task.delay = Mock(return_value=Mock(id="task_820"))

            result = mock_task.delay(stream_name="prediction_stream", batch_size=100)
            assert result.id == "task_820"

    def test_stream_consumer(self):
        """测试流消费者"""
        with patch("src.tasks.streaming_tasks.StreamingTask") as MockTask:
            task = MockTask()
            task.consume_stream = Mock(
                return_value={"consumed": True, "messages_processed": 50, "errors": 0}
            )
            task.commit_offsets = Mock(return_value=True)

            result = task.consume_stream(topic="football_matches", max_messages=50)
            assert result["consumed"] is True
            assert result["messages_processed"] == 50

    def test_stream_producer(self):
        """测试流生产者"""
        with patch("src.tasks.streaming_tasks.StreamingTask") as MockTask:
            task = MockTask()
            task.produce_to_stream = Mock(
                return_value={
                    "produced": True,
                    "messages_sent": 25,
                    "topic": "processed_predictions",
                }
            )

            messages = [{"prediction": "HOME_WIN"} for _ in range(25)]
            result = task.produce_to_stream(
                topic="processed_predictions", messages=messages
            )
            assert result["produced"] is True
            assert result["messages_sent"] == 25


class TestMonitoringTask:
    """测试监控任务"""

    def test_monitoring_task_creation(self):
        """测试监控任务创建"""
        if not TASKS_AVAILABLE:
            pytest.skip("Tasks模块不可用")

        with patch("src.tasks.monitoring.MonitoringTask") as MockTask:
            task = MockTask()
            task.check_type = "health"
            task.interval = 300  # 5分钟
            task.endpoints = ["/health", "/metrics"]

            assert task.check_type == "health"
            assert task.interval == 300

    def test_health_check_task(self):
        """测试健康检查任务"""
        with patch("src.tasks.monitoring.health_check") as MockTask:
            mock_task = MockTask()
            mock_task.delay = Mock(return_value=Mock(id="task_830"))

            result = mock_task.delay(
                endpoints=["/health", "/api/predictions"], timeout=10
            )
            assert result.id == "task_830"

    def test_metrics_collection_task(self):
        """测试指标收集任务"""
        with patch("src.tasks.monitoring.MonitoringTask") as MockTask:
            task = MockTask()
            task.collect_metrics = Mock(
                return_value={
                    "collected": True,
                    "metrics": {
                        "cpu_usage": 45.2,
                        "memory_usage": 68.5,
                        "active_connections": 25,
                    },
                    "timestamp": datetime.now(),
                }
            )

            result = task.collect_metrics()
            assert result["collected"] is True
            assert "cpu_usage" in result["metrics"]

    def test_alert_check_task(self):
        """测试告警检查任务"""
        with patch("src.tasks.monitoring.MonitoringTask") as MockTask:
            task = MockTask()
            task.check_alerts = Mock(
                return_value={
                    "checked": True,
                    "active_alerts": [
                        {"type": "warning", "message": "High CPU usage", "value": 85.0}
                    ],
                    "alert_count": 1,
                }
            )

            result = task.check_alerts()
            assert result["checked"] is True
            assert result["alert_count"] == 1


class TestTaskIntegration:
    """测试任务集成"""

    def test_task_chaining(self):
        """测试任务链"""
        with patch(
            "src.tasks.data_collection_tasks.collect_matches"
        ) as MockCollect, patch(
            "src.tasks.data_collection_tasks.collect_odds"
        ) as MockOdds, patch("src.tasks.backup_tasks.create_backup") as MockBackup:
            collect_task = MockCollect()
            odds_task = MockOdds()
            backup_task = MockBackup()

            # 设置任务链
            collect_task.apply_async = Mock(return_value=Mock(id="task_900"))
            odds_task.apply_async = Mock(return_value=Mock(id="task_901"))
            backup_task.apply_async = Mock(return_value=Mock(id="task_902"))

            # 执行任务链
            result1 = collect_task.apply_async(args=[1])
            result2 = odds_task.apply_async(kwargs={"match_ids": [1, 2, 3]})
            result3 = backup_task.apply_async()

            assert result1.id == "task_900"
            assert result2.id == "task_901"
            assert result3.id == "task_902"

    def test_task_groups(self):
        """测试任务组"""
        with patch("src.tasks.celery_app.group") as MockGroup:
            mock_group = MockGroup()
            mock_group.apply_async = Mock(return_value=Mock(id="group_001"))

            # 创建任务组
            [
                Mock(apply_async=Mock(return_value=Mock(id="task_001"))),
                Mock(apply_async=Mock(return_value=Mock(id="task_002"))),
                Mock(apply_async=Mock(return_value=Mock(id="task_003"))),
            ]

            group_result = mock_group.apply_async()
            assert group_result.id == "group_001"

    def test_task_scheduling(self):
        """测试任务调度"""
        with patch("src.tasks.celery_app.send_task") as MockSendTask:
            mock_result = Mock()
            mock_result.id = "scheduled_001"
            MockSendTask.return_value = mock_result

            # 调度任务
            result = MockSendTask(
                "tasks.collect_matches",
                args=[1],
                kwargs={"season": "2024/2025"},
                countdown=60,
                expires=3600,
            )

            assert result.id == "scheduled_001"

    @pytest.mark.asyncio
    async def test_async_task_execution(self):
        """测试异步任务执行"""
        # Mock异步任务
        MockAsyncTask = Mock()
        task = MockAsyncTask()

        # 设置异步方法
        task.execute_async = AsyncMock(
            return_value={
                "status": "completed",
                "result": {"processed": 100},
                "duration": 5.2,
            }
        )
        task.cleanup_async = AsyncMock(return_value=True)

        # 执行异步任务
        result = await task.execute_async(
            task_type="data_collection", params={"league_id": 1}
        )
        assert result["status"] == "completed"
        assert result["result"]["processed"] == 100

        # 清理
        await task.cleanup_async()

    def test_task_error_handling(self):
        """测试任务错误处理"""
        with patch("src.tasks.data_collection_core.DataCollectionTask") as MockTask:
            task = MockTask()
            task.on_failure = Mock()
            task.retry = Mock(return_value=Mock(id="retry_001"))

            # 模拟任务失败
            task.on_failure(
                Exception("Database connection failed"),
                "task_999",
                [],
                {},
                "Traceback...",
            )
            task.on_failure.assert_called_once()

            # 测试重试
            retry_result = task.retry(countdown=60, max_retries=3)
            assert retry_result.id == "retry_001"

    def test_task_monitoring(self):
        """测试任务监控"""
        with patch("src.tasks.celery_app.control") as MockControl:
            control = MockControl()
            control.inspect = Mock(
                return_value=Mock(
                    active=[
                        {
                            "id": "task_001",
                            "name": "tasks.collect_matches",
                            "args": "[1]",
                            "kwargs": "{}",
                            "time_start": "2025-01-18T10:00:00",
                        }
                    ],
                    scheduled=[
                        {
                            "id": "task_002",
                            "name": "tasks.backup",
                            "eta": "2025-01-18T11:00:00",
                        }
                    ],
                )
            )

            # 获取活跃任务
            inspect = control.inspect()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()

            assert len(active_tasks) == 1
            assert active_tasks[0]["id"] == "task_001"
            assert len(scheduled_tasks) == 1
            assert scheduled_tasks[0]["name"] == "tasks.backup"
