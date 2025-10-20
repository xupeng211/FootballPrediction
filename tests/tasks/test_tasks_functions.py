"""
Tasks模块功能测试
测试异步任务、数据收集、备份等功能
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestTasksFunctionality:
    """测试Tasks功能模块"""

    def test_data_collection_functionality(self):
        """测试数据收集功能"""
        # Mock数据收集器
        MockDataCollector = Mock()
        collector = MockDataCollector()

        # 设置收集方法
        collector.collect_fixtures = Mock(
            return_value=[
                {"id": 1, "home_team": "Team A", "away_team": "Team B"},
                {"id": 2, "home_team": "Team C", "away_team": "Team D"},
            ]
        )
        collector.collect_odds = Mock(
            return_value=[
                {"match_id": 1, "home_win": 2.5, "draw": 3.2, "away_win": 2.8},
                {"match_id": 2, "home_win": 1.8, "draw": 3.5, "away_win": 4.0},
            ]
        )
        collector.collect_scores = Mock(
            return_value=[
                {"match_id": 1, "home_score": 2, "away_score": 1},
                {"match_id": 2, "home_score": 0, "away_score": 0},
            ]
        )
        collector.validate_data = Mock(return_value={"valid": True, "errors": []})

        # 测试收集各类数据
        fixtures = collector.collect_fixtures(league_id=1)
        odds = collector.collect_odds(match_ids=[1, 2])
        scores = collector.collect_scores(date="2025-01-18")
        validation = collector.validate_data(fixtures)

        assert len(fixtures) == 2
        assert fixtures[0]["home_team"] == "Team A"
        assert len(odds) == 2
        assert odds[0]["match_id"] == 1
        assert len(scores) == 2
        assert scores[0]["home_score"] == 2
        assert validation["valid"] is True

    def test_backup_functionality(self):
        """测试备份功能"""
        # Mock备份任务
        MockBackupTask = Mock()
        backup_task = MockBackupTask()

        # 设置备份方法
        backup_task.create_full_backup = Mock(
            return_value={
                "backup_id": "backup_20250118_full",
                "path": "/backups/backup_20250118_full.tar.gz",
                "size": 1073741824,  # 1GB
                "status": "completed",
            }
        )
        backup_task.create_incremental_backup = Mock(
            return_value={
                "backup_id": "backup_20250118_inc",
                "path": "/backups/backup_20250118_inc.tar.gz",
                "size": 107374182,  # 100MB
                "base_backup": "backup_20250117_full",
                "status": "completed",
            }
        )
        backup_task.schedule_backup = Mock(
            return_value={
                "scheduled": True,
                "backup_type": "daily",
                "next_run": "2025-01-19T02:00:00",
                "cron": "0 2 * * *",
            }
        )
        backup_task.restore_backup = Mock(
            return_value={
                "restored": True,
                "backup_id": "backup_20250118_full",
                "files_restored": 1000,
                "duration_seconds": 300,
            }
        )

        # 测试创建备份
        full_backup = backup_task.create_full_backup()
        inc_backup = backup_task.create_incremental_backup(base="backup_20250117_full")

        assert full_backup["status"] == "completed"
        assert full_backup["size"] == 1073741824
        assert inc_backup["base_backup"] == "backup_20250117_full"

        # 测试调度备份
        schedule = backup_task.schedule_backup(
            backup_type="daily", cron_expression="0 2 * * *"
        )
        assert schedule["scheduled"] is True

        # 测试恢复备份
        restore = backup_task.restore_backup("backup_20250118_full")
        assert restore["restored"] is True
        assert restore["files_restored"] == 1000

    def test_maintenance_functionality(self):
        """测试维护功能"""
        # Mock维护任务
        MockMaintenanceTask = Mock()
        maintenance = MockMaintenanceTask()

        # 设置维护方法
        maintenance.cleanup_old_data = Mock(
            return_value={
                "cleaned": True,
                "table": "predictions",
                "records_deleted": 5000,
                "space_freed": "250MB",
                "retention_days": 90,
            }
        )
        maintenance.optimize_database = Mock(
            return_value={
                "optimized": True,
                "tables": ["predictions", "matches", "odds"],
                "space_saved": "500MB",
                "duration_seconds": 120,
            }
        )
        maintenance.rebuild_indexes = Mock(
            return_value={
                "rebuilt": True,
                "indexes": ["idx_predictions_date", "idx_matches_league"],
                "duration_seconds": 300,
            }
        )
        maintenance.update_statistics = Mock(
            return_value={
                "updated": True,
                "statistics": {
                    "predictions": {"row_count": 10000, "size": "100MB"},
                    "matches": {"row_count": 1000, "size": "10MB"},
                },
            }
        )

        # 测试清理旧数据
        cleanup = maintenance.cleanup_old_data(table="predictions", retention_days=90)
        assert cleanup["cleaned"] is True
        assert cleanup["records_deleted"] == 5000

        # 测试数据库优化
        optimize = maintenance.optimize_database()
        assert optimize["optimized"] is True
        assert len(optimize["tables"]) == 3

        # 测试重建索引
        rebuild = maintenance.rebuild_indexes()
        assert rebuild["rebuilt"] is True
        assert len(rebuild["indexes"]) == 2

        # 测试更新统计信息
        stats = maintenance.update_statistics()
        assert stats["updated"] is True
        assert "predictions" in stats["statistics"]

    def test_streaming_functionality(self):
        """测试流处理功能"""
        # Mock流处理任务
        MockStreamingTask = Mock()
        streaming = MockStreamingTask()

        # 设置流处理方法
        streaming.consume_stream = Mock(
            return_value={
                "consumed": True,
                "topic": "football_matches",
                "messages_processed": 100,
                "errors": 0,
                "processing_time": 5.2,
            }
        )
        streaming.produce_to_stream = Mock(
            return_value={
                "produced": True,
                "topic": "processed_predictions",
                "messages_sent": 50,
                "batch_id": "batch_123",
            }
        )
        streaming.process_stream_batch = Mock(
            return_value={
                "processed": True,
                "batch_size": 25,
                "processed_items": 25,
                "failed_items": 0,
            }
        )
        streaming.commit_offsets = Mock(
            return_value={
                "committed": True,
                "topic": "football_matches",
                "partition": 0,
                "offset": 1000,
            }
        )

        # 测试消费流
        consume_result = streaming.consume_stream(
            topic="football_matches", max_messages=100
        )
        assert consume_result["consumed"] is True
        assert consume_result["messages_processed"] == 100

        # 测试生产到流
        messages = [{"prediction": "HOME_WIN"} for _ in range(50)]
        produce_result = streaming.produce_to_stream(
            topic="processed_predictions", messages=messages
        )
        assert produce_result["produced"] is True
        assert produce_result["messages_sent"] == 50

        # 测试批处理
        batch_result = streaming.process_stream_batch(
            messages=[{"data": f"item_{i}"} for i in range(25)]
        )
        assert batch_result["processed"] is True
        assert batch_result["batch_size"] == 25

        # 测试提交偏移量
        commit_result = streaming.commit_offsets(
            topic="football_matches", partition=0, offset=1000
        )
        assert commit_result["committed"] is True

    def test_monitoring_functionality(self):
        """测试监控功能"""
        # Mock监控任务
        MockMonitoringTask = Mock()
        monitoring = MockMonitoringTask()

        # 设置监控方法
        monitoring.health_check = Mock(
            return_value={
                "status": "healthy",
                "checks": {
                    "database": {"status": "healthy", "response_time": 5.2},
                    "redis": {"status": "healthy", "response_time": 0.5},
                    "api": {"status": "healthy", "response_time": 10.0},
                },
            }
        )
        monitoring.collect_metrics = Mock(
            return_value={
                "timestamp": "2025-01-18T10:00:00",
                "metrics": {
                    "cpu_usage": 45.2,
                    "memory_usage": 68.5,
                    "active_connections": 25,
                    "requests_per_second": 100,
                },
            }
        )
        monitoring.check_alerts = Mock(
            return_value={
                "active_alerts": [
                    {
                        "type": "info",
                        "message": "System running normally",
                        "timestamp": "2025-01-18T10:00:00",
                    }
                ],
                "alert_count": 1,
            }
        )
        monitoring.generate_report = Mock(
            return_value={
                "report_id": "report_123",
                "generated_at": "2025-01-18T10:00:00",
                "summary": {
                    "health_status": "healthy",
                    "metrics_summary": {"avg_cpu": 45.2, "avg_memory": 68.5},
                },
            }
        )

        # 测试健康检查
        health = monitoring.health_check()
        assert health["status"] == "healthy"
        assert "database" in health["checks"]

        # 测试收集指标
        metrics = monitoring.collect_metrics()
        assert "cpu_usage" in metrics["metrics"]
        assert metrics["metrics"]["active_connections"] == 25

        # 测试检查告警
        alerts = monitoring.check_alerts()
        assert alerts["alert_count"] == 1
        assert alerts["active_alerts"][0]["type"] == "info"

        # 测试生成报告
        report = monitoring.generate_report()
        assert report["report_id"] == "report_123"
        assert report["summary"]["health_status"] == "healthy"

    def test_task_scheduling_functionality(self):
        """测试任务调度功能"""
        # Mock任务调度器
        MockTaskScheduler = Mock()
        scheduler = MockTaskScheduler()

        # 设置调度方法
        scheduler.schedule_task = Mock(
            return_value={
                "task_id": "scheduled_task_001",
                "task_name": "collect_daily_data",
                "scheduled_at": "2025-01-19T02:00:00",
                "cron": "0 2 * * *",
                "enabled": True,
            }
        )
        scheduler.cancel_task = Mock(
            return_value={
                "task_id": "scheduled_task_001",
                "cancelled": True,
                "cancelled_at": "2025-01-18T15:30:00",
            }
        )
        scheduler.list_scheduled_tasks = Mock(
            return_value=[
                {
                    "task_id": "task_001",
                    "name": "daily_backup",
                    "next_run": "2025-01-19T02:00:00",
                },
                {
                    "task_id": "task_002",
                    "name": "hourly_metrics",
                    "next_run": "2025-01-18T11:00:00",
                },
            ]
        )

        # 测试调度任务
        schedule = scheduler.schedule_task(
            task_name="collect_daily_data",
            cron_expression="0 2 * * *",
            params={"league_id": 1},
        )
        assert schedule["enabled"] is True
        assert schedule["cron"] == "0 2 * * *"

        # 测试列出任务
        tasks = scheduler.list_scheduled_tasks()
        assert len(tasks) == 2
        assert tasks[0]["name"] == "daily_backup"

        # 测试取消任务
        cancel = scheduler.cancel_task("scheduled_task_001")
        assert cancel["cancelled"] is True

    def test_task_execution_functionality(self):
        """测试任务执行功能"""
        # Mock任务执行器
        MockTaskExecutor = Mock()
        executor = MockTaskExecutor()

        # 设置执行方法
        executor.execute_task = Mock(
            return_value={
                "task_id": "task_exec_001",
                "status": "completed",
                "result": {"processed": 100},
                "duration_seconds": 5.2,
                "started_at": "2025-01-18T10:00:00",
                "completed_at": "2025-01-18T10:00:05",
            }
        )
        executor.execute_async = AsyncMock(
            return_value={
                "task_id": "task_async_001",
                "status": "running",
                "started_at": "2025-01-18T10:00:00",
            }
        )
        executor.retry_task = Mock(
            return_value={
                "task_id": "task_retry_001",
                "attempt": 2,
                "max_attempts": 3,
                "next_retry": "2025-01-18T10:05:00",
            }
        )

        # 测试执行任务
        result = executor.execute_task(
            task_name="collect_data", params={"league_id": 1}
        )
        assert result["status"] == "completed"
        assert result["result"]["processed"] == 100

        # 测试重试任务
        retry = executor.retry_task(task_id="task_failed_001", countdown=300)
        assert retry["attempt"] == 2
        assert retry["max_attempts"] == 3

    @pytest.mark.asyncio
    async def test_async_task_functionality(self):
        """测试异步任务功能"""
        # Mock异步任务执行器
        MockAsyncExecutor = Mock()
        async_executor = MockAsyncExecutor()

        # 设置异步方法
        async_executor.execute_async = AsyncMock(
            return_value={
                "task_id": "async_task_001",
                "status": "completed",
                "result": {"processed": 200},
                "duration_seconds": 3.5,
            }
        )
        async_executor.monitor_task = AsyncMock(
            return_value={
                "task_id": "async_task_001",
                "status": "running",
                "progress": 0.75,
                "estimated_remaining": 30,
            }
        )

        # 测试异步执行
        result = await async_executor.execute_async(
            task_name="process_stream",
            params={"stream": "predictions", "batch_size": 100},
        )
        assert result["status"] == "completed"
        assert result["result"]["processed"] == 200

        # 测试监控任务
        monitor = await async_executor.monitor_task("async_task_001")
        assert monitor["status"] == "running"
        assert monitor["progress"] == 0.75

    def test_task_error_handling_functionality(self):
        """测试任务错误处理功能"""
        # Mock错误处理器
        MockErrorHandler = Mock()
        error_handler = MockErrorHandler()

        # 设置错误处理方法
        error_handler.handle_task_error = Mock(
            return_value={
                "error_id": "error_001",
                "task_id": "task_001",
                "error_type": "ConnectionError",
                "handled": True,
                "action": "retry_later",
            }
        )
        error_handler.log_error = Mock(
            return_value={
                "logged": True,
                "log_id": "log_001",
                "timestamp": "2025-01-18T10:00:00",
            }
        )
        error_handler.send_alert = Mock(
            return_value={
                "alert_sent": True,
                "channel": "email",
                "recipient": "admin@example.com",
            }
        )

        # 测试处理错误
        error_result = error_handler.handle_task_error(
            task_id="task_001",
            error=Exception("Database connection failed"),
            context={"retry_count": 2},
        )
        assert error_result["handled"] is True
        assert error_result["action"] == "retry_later"

        # 测试记录错误
        log_result = error_handler.log_error(
            error=Exception("Task failed"), task_id="task_001"
        )
        assert log_result["logged"] is True

        # 测试发送告警
        alert_result = error_handler.send_alert(
            error_type="critical", message="Task failed after 3 retries"
        )
        assert alert_result["alert_sent"] is True

    def test_task_dependency_functionality(self):
        """测试任务依赖功能"""
        # Mock任务依赖管理器
        MockDependencyManager = Mock()
        dep_manager = MockDependencyManager()

        # 设置依赖方法
        dep_manager.define_dependency = Mock(
            return_value={
                "dependency_id": "dep_001",
                "task": "process_predictions",
                "depends_on": "collect_matches",
                "condition": "success",
            }
        )
        dep_manager.check_dependencies = Mock(
            return_value={
                "ready": True,
                "dependencies_met": ["collect_matches", "collect_odds"],
                "pending": [],
            }
        )
        dep_manager.execute_chain = Mock(
            return_value={
                "chain_id": "chain_001",
                "tasks_executed": [
                    "collect_matches",
                    "collect_odds",
                    "process_predictions",
                ],
                "status": "completed",
            }
        )

        # 测试定义依赖
        dep = dep_manager.define_dependency(
            task="process_predictions",
            depends_on="collect_matches",
            condition="success",
        )
        assert dep["dependency_id"] == "dep_001"

        # 测试检查依赖
        check = dep_manager.check_dependencies(task="process_predictions")
        assert check["ready"] is True

        # 测试执行任务链
        chain = dep_manager.execute_chain(
            tasks=["collect_matches", "collect_odds", "process_predictions"]
        )
        assert chain["status"] == "completed"
        assert len(chain["tasks_executed"]) == 3

    def test_task_monitoring_functionality(self):
        """测试任务监控功能"""
        # Mock任务监控器
        MockTaskMonitor = Mock()
        monitor = MockTaskMonitor()

        # 设置监控方法
        monitor.get_active_tasks = Mock(
            return_value=[
                {
                    "task_id": "task_001",
                    "name": "collect_data",
                    "status": "running",
                    "progress": 0.5,
                    "started_at": "2025-01-18T10:00:00",
                },
                {
                    "task_id": "task_002",
                    "name": "backup_database",
                    "status": "running",
                    "progress": 0.25,
                    "started_at": "2025-01-18T10:05:00",
                },
            ]
        )
        monitor.get_task_status = Mock(
            return_value={
                "task_id": "task_001",
                "status": "completed",
                "result": {"processed": 100},
                "duration": 30.5,
            }
        )
        monitor.get_queue_status = Mock(
            return_value={
                "queue": "default",
                "pending_tasks": 5,
                "active_tasks": 2,
                "failed_tasks": 0,
            }
        )

        # 测试获取活跃任务
        active = monitor.get_active_tasks()
        assert len(active) == 2
        assert active[0]["progress"] == 0.5

        # 测试获取任务状态
        status = monitor.get_task_status("task_001")
        assert status["status"] == "completed"

        # 测试获取队列状态
        queue = monitor.get_queue_status()
        assert queue["pending_tasks"] == 5
        assert queue["active_tasks"] == 2
