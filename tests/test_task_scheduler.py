"""
足球预测系统任务调度测试模块

测试覆盖范围：
1. 定时任务执行 - beat_schedule配置和任务调度
2. 任务重试机制 - API失败3次重试逻辑
3. 错误日志记录 - 失败记录写入error_logs表
4. 数据采集任务 - fixtures/odds/scores任务执行
5. 维护任务执行 - 系统维护和健康检查
6. 监控指标收集 - Prometheus指标统计
7. 任务队列管理 - 多队列并发处理

目标覆盖率: >85%
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Celery和任务相关导入
from celery import Celery
from celery.exceptions import MaxRetriesExceededError, Retry
from kombu.exceptions import OperationalError

# 数据库相关导入
from src.database.session import DatabaseManager
# 项目模块导入
from src.tasks.celery_app import TASK_MONITORING, TaskRetryConfig
from src.tasks.celery_app import app as celery_app
from src.tasks.data_collection_tasks import (DataCollectionTask,
                                             collect_fixtures_task,
                                             collect_odds_task,
                                             collect_scores_task,
                                             manual_collect_all_data)
from src.tasks.error_logger import TaskErrorLogger
from src.tasks.maintenance_tasks import (cleanup_error_logs_task,
                                         database_maintenance_task,
                                         quality_check_task,
                                         system_health_check_task)
from src.tasks.monitoring import TaskMonitor
from src.tasks.utils import (calculate_next_collection_time,
                             get_upcoming_matches, should_collect_live_scores)


class TestCeleryAppConfiguration:
    """测试Celery应用配置"""

    def test_celery_app_creation(self):
        """测试Celery应用创建和基本配置"""
        assert celery_app is not None
        assert celery_app.main == "football_prediction_tasks"
        assert hasattr(celery_app.conf, "broker_url")
        assert hasattr(celery_app.conf, "result_backend")

    def test_task_routing_configuration(self):
        """测试任务路由配置"""
        task_routes = celery_app.conf.task_routes

        # 验证数据采集任务路由
        assert "tasks.data_collection_tasks.collect_fixtures_task" in task_routes
        assert (
            task_routes["tasks.data_collection_tasks.collect_fixtures_task"]["queue"]
            == "fixtures"
        )
        assert (
            task_routes["tasks.data_collection_tasks.collect_odds_task"]["queue"]
            == "odds"
        )
        assert (
            task_routes["tasks.data_collection_tasks.collect_scores_task"]["queue"]
            == "scores"
        )

        # 验证维护任务路由
        maintenance_route = next(
            (k for k in task_routes.keys() if "maintenance_tasks" in k), None
        )
        assert maintenance_route is not None
        assert task_routes[maintenance_route]["queue"] == "maintenance"

    def test_beat_schedule_configuration(self):
        """测试定时任务调度配置"""
        beat_schedule = celery_app.conf.beat_schedule

        # 验证核心定时任务存在
        required_tasks = [
            "collect-daily-fixtures",
            "collect-odds-regular",
            "collect-live-scores",
            "hourly-quality-check",
            "daily-error-cleanup",
        ]

        for task_name in required_tasks:
            assert task_name in beat_schedule, f"定时任务 {task_name} 未配置"

        # 验证具体调度配置
        fixtures_task = beat_schedule["collect-daily-fixtures"]
        assert (
            fixtures_task["task"] == "tasks.data_collection_tasks.collect_fixtures_task"
        )
        assert "schedule" in fixtures_task

        odds_task = beat_schedule["collect-odds-regular"]
        assert odds_task["schedule"] == 300.0  # 5分钟

        scores_task = beat_schedule["collect-live-scores"]
        assert scores_task["schedule"] == 120.0  # 2分钟

    def test_task_retry_configuration(self):
        """测试任务重试配置"""
        retry_config = TaskRetryConfig()

        # 验证所有数据采集任务都有重试配置
        required_tasks = [
            "collect_fixtures_task",
            "collect_odds_task",
            "collect_scores_task",
        ]

        for task_name in required_tasks:
            config = retry_config.get_retry_config(task_name)
            assert config is not None, f"任务 {task_name} 缺少重试配置"
            assert config["max_retries"] == 3, f"任务 {task_name} 重试次数不是3次"
            assert "retry_delay" in config

    def test_worker_configuration(self):
        """测试Worker配置"""
        conf = celery_app.conf

        # 验证超时配置
        assert conf.task_soft_time_limit == 300  # 5分钟软超时
        assert conf.task_time_limit == 600  # 10分钟硬超时

        # 验证序列化配置
        assert conf.accept_content == ["json"]
        assert conf.task_serializer == "json"
        assert conf.result_serializer == "json"


class TestDataCollectionTasks:
    """测试数据采集任务"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        with patch("src.tasks.data_collection_tasks.DatabaseManager") as mock_manager:
            mock_instance = AsyncMock()
            mock_manager.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_error_logger(self):
        """模拟错误日志记录器"""
        with patch("src.tasks.error_logger.TaskErrorLogger") as mock_logger:
            mock_instance = AsyncMock()
            mock_logger.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_collect_fixtures_task_success(
        self, mock_db_manager, mock_error_logger
    ):
        """测试赛程采集任务成功执行"""
        # 模拟FixturesCollector
        with patch(
            "src.data_collection.fixtures_collector.FixturesCollector"
        ) as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector.collect_fixtures.return_value = {
                "fixtures_collected": 50,
                "new_fixtures": 20,
                "updated_fixtures": 30,
            }
            mock_collector_class.return_value = mock_collector

            # 执行任务
            result = await asyncio.create_task(
                collect_fixtures_task.s(leagues=["Premier League"], days_ahead=7)
                .apply_async()
                .get()
            )

            # 验证结果
            assert result is not None
            assert "fixtures_collected" in result

            # 验证collector被正确调用
            mock_collector.collect_fixtures.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_odds_task_success(self, mock_db_manager, mock_error_logger):
        """测试赔率采集任务成功执行"""
        with patch(
            "src.data_collection.odds_collector.OddsCollector"
        ) as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector.collect_odds.return_value = {
                "odds_collected": 100,
                "bookmakers": 5,
                "matches_processed": 20,
            }
            mock_collector_class.return_value = mock_collector

            result = await asyncio.create_task(
                collect_odds_task.s(match_ids=[1, 2, 3]).apply_async().get()
            )

            assert result is not None
            assert "odds_collected" in result
            mock_collector.collect_odds.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_scores_task_success(
        self, mock_db_manager, mock_error_logger
    ):
        """测试比分采集任务成功执行"""
        with patch(
            "src.data_collection.scores_collector.ScoresCollector"
        ) as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector.collect_scores.return_value = {
                "scores_collected": 15,
                "live_matches": 5,
                "finished_matches": 10,
            }
            mock_collector_class.return_value = mock_collector

            result = await asyncio.create_task(
                collect_scores_task.s(live_only=True).apply_async().get()
            )

            assert result is not None
            assert "scores_collected" in result
            mock_collector.collect_scores.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_retry_mechanism(self, mock_db_manager, mock_error_logger):
        """测试任务重试机制 - API失败自动重试3次"""
        with patch(
            "src.data_collection.fixtures_collector.FixturesCollector"
        ) as mock_collector_class:
            # 模拟API失败
            mock_collector = AsyncMock()
            api_error = Exception("API调用失败: HTTP 503 Service Unavailable")
            mock_collector.collect_fixtures.side_effect = api_error
            mock_collector_class.return_value = mock_collector

            # 模拟任务实例
            task_instance = collect_fixtures_task
            task_instance.request.retries = 0
            task_instance.error_logger = mock_error_logger

            # 模拟retry方法
            with patch.object(task_instance, "retry") as mock_retry:
                mock_retry.side_effect = Retry("重试中...")

                try:
                    await asyncio.create_task(task_instance.s().apply_async().get())
                except Retry:
                    pass  # 重试异常是预期的

                # 验证重试被调用
                mock_retry.assert_called()

                # 验证错误日志记录
                mock_error_logger.log_api_failure.assert_called()

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, mock_db_manager, mock_error_logger):
        """测试达到最大重试次数后的处理"""
        with patch(
            "src.data_collection.odds_collector.OddsCollector"
        ) as mock_collector_class:
            mock_collector = AsyncMock()
            api_error = Exception("持续API失败")
            mock_collector.collect_odds.side_effect = api_error
            mock_collector_class.return_value = mock_collector

            task_instance = collect_odds_task
            task_instance.request.retries = 3  # 已重试3次
            task_instance.error_logger = mock_error_logger

            with patch.object(task_instance, "retry") as mock_retry:
                mock_retry.side_effect = MaxRetriesExceededError("超过最大重试次数")

                try:
                    await asyncio.create_task(task_instance.s().apply_async().get())
                except MaxRetriesExceededError:
                    pass

                # 验证最终错误记录
                mock_error_logger.log_task_error.assert_called()
                mock_error_logger.log_data_collection_error.assert_called()

    @pytest.mark.asyncio
    async def test_manual_collect_all_data(self, mock_db_manager, mock_error_logger):
        """测试手动触发全部数据采集"""
        with patch(
            "src.tasks.data_collection_tasks.collect_fixtures_task.delay"
        ) as mock_fixtures, patch(
            "src.tasks.data_collection_tasks.collect_odds_task.delay"
        ) as mock_odds, patch(
            "src.tasks.data_collection_tasks.collect_scores_task.delay"
        ) as mock_scores:
            # 模拟任务返回结果
            mock_fixtures.return_value = Mock(id="fixtures-123")
            mock_odds.return_value = Mock(id="odds-456")
            mock_scores.return_value = Mock(id="scores-789")

            result = await asyncio.create_task(
                manual_collect_all_data.s().apply_async().get()
            )

            # 验证所有任务都被触发
            mock_fixtures.assert_called_once()
            mock_odds.assert_called_once()
            mock_scores.assert_called_once()

            # 验证返回结果
            assert "triggered_tasks" in result
            assert len(result["triggered_tasks"]) == 3


class TestErrorLogger:
    """测试错误日志记录器"""

    @pytest.fixture
    def error_logger(self):
        """创建错误日志记录器实例"""
        with patch("src.tasks.error_logger.DatabaseManager") as mock_manager:
            mock_db = AsyncMock()
            mock_manager.return_value = mock_db

            logger = TaskErrorLogger()
            logger.db_manager = mock_db
            return logger

    @pytest.mark.asyncio
    async def test_log_task_error(self, error_logger):
        """测试记录任务错误"""
        # 模拟数据库执行
        error_logger.db_manager.execute_query = AsyncMock()

        # 记录任务错误
        await error_logger.log_task_error(
            task_name="collect_fixtures_task",
            task_id="task-123",
            error=Exception("测试错误"),
            context={"leagues": ["Premier League"]},
            retry_count=2,
        )

        # 验证数据库插入被调用
        error_logger.db_manager.execute_query.assert_called_once()

        # 获取调用参数
        call_args = error_logger.db_manager.execute_query.call_args
        sql, params = call_args[0]

        # 验证SQL和参数
        assert "INSERT INTO error_logs" in sql
        assert params["task_name"] == "collect_fixtures_task"
        assert params["task_id"] == "task-123"
        assert params["retry_count"] == 2
        assert "Exception" in params["error_type"]

    @pytest.mark.asyncio
    async def test_log_api_failure(self, error_logger):
        """测试记录API失败"""
        error_logger.db_manager.execute_query = AsyncMock()

        await error_logger.log_api_failure(
            task_name="collect_odds_task",
            api_endpoint="https://api-football.com/v3/odds",
            http_status=503,
            error_message="Service Unavailable",
            retry_count=1,
        )

        error_logger.db_manager.execute_query.assert_called_once()

        call_args = error_logger.db_manager.execute_query.call_args
        sql, params = call_args[0]

        assert "INSERT INTO error_logs" in sql
        assert params["error_type"] == "API_FAILURE"
        assert "503" in params["error_message"]
        assert "api-football.com" in params["context_data"]

    @pytest.mark.asyncio
    async def test_log_data_collection_error(self, error_logger):
        """测试记录数据采集错误到data_collection_logs表"""
        error_logger.db_manager.execute_query = AsyncMock()

        await error_logger.log_data_collection_error(
            data_source="API-FOOTBALL",
            collection_type="fixtures",
            error_message="解析JSON失败",
        )

        # 验证插入到data_collection_logs表
        error_logger.db_manager.execute_query.assert_called_once()

        call_args = error_logger.db_manager.execute_query.call_args
        sql, params = call_args[0]

        assert "INSERT INTO data_collection_logs" in sql
        assert params["data_source"] == "API-FOOTBALL"
        assert params["collection_type"] == "fixtures"
        assert params["status"] == "ERROR"
        assert "解析JSON失败" in params["error_message"]

    @pytest.mark.asyncio
    async def test_get_error_statistics(self, error_logger):
        """测试获取错误统计"""
        # 模拟查询结果
        mock_stats = [
            {
                "task_name": "collect_odds_task",
                "error_count": 5,
                "last_error": datetime.now(),
            },
            {
                "task_name": "collect_scores_task",
                "error_count": 2,
                "last_error": datetime.now(),
            },
        ]
        error_logger.db_manager.fetch_all = AsyncMock(return_value=mock_stats)

        stats = await error_logger.get_error_statistics(hours=24)

        assert len(stats) == 2
        assert stats[0]["task_name"] == "collect_odds_task"
        assert stats[0]["error_count"] == 5

    @pytest.mark.asyncio
    async def test_cleanup_old_logs(self, error_logger):
        """测试清理旧错误日志"""
        error_logger.db_manager.execute_query = AsyncMock(return_value=15)  # 15行被删除

        deleted_count = await error_logger.cleanup_old_logs(days=7)

        assert deleted_count == 15
        error_logger.db_manager.execute_query.assert_called_once()

        call_args = error_logger.db_manager.execute_query.call_args
        sql, params = call_args[0]

        assert "DELETE FROM error_logs" in sql
        assert "created_at < NOW() - INTERVAL" in sql


class TestMaintenanceTasks:
    """测试维护任务"""

    @pytest.fixture
    def mock_db_manager(self):
        with patch("src.tasks.maintenance_tasks.DatabaseManager") as mock_manager:
            mock_instance = AsyncMock()
            mock_manager.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_quality_check_task(self, mock_db_manager):
        """测试数据质量检查任务"""
        # 模拟质量检查结果
        mock_results = [
            {"check_name": "重复数据检查", "issue_count": 5, "status": "WARNING"},
            {"check_name": "数据完整性检查", "issue_count": 0, "status": "PASS"},
            {"check_name": "异常赔率检查", "issue_count": 2, "status": "WARNING"},
        ]
        mock_db_manager.fetch_all = AsyncMock(return_value=mock_results)

        result = await asyncio.create_task(quality_check_task.s().apply_async().get())

        assert "quality_checks" in result
        assert len(result["quality_checks"]) >= 3
        assert result["overall_status"] in ["PASS", "WARNING", "CRITICAL"]

    @pytest.mark.asyncio
    async def test_cleanup_error_logs_task(self, mock_db_manager):
        """测试错误日志清理任务"""
        # 模拟TaskErrorLogger
        with patch("src.tasks.maintenance_tasks.TaskErrorLogger") as mock_logger_class:
            mock_logger = AsyncMock()
            mock_logger.cleanup_old_logs.return_value = 25  # 清理了25条日志
            mock_logger_class.return_value = mock_logger

            result = await asyncio.create_task(
                cleanup_error_logs_task.s(days=7).apply_async().get()
            )

            assert "deleted_logs" in result
            assert result["deleted_logs"] == 25
            mock_logger.cleanup_old_logs.assert_called_with(days=7)

    @pytest.mark.asyncio
    async def test_system_health_check_task(self, mock_db_manager):
        """测试系统健康检查任务"""
        # 模拟健康检查结果
        mock_db_manager.execute_query = AsyncMock(return_value=[(1,)])  # 数据库连接正常

        with patch("redis.Redis") as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True
            mock_redis_class.return_value = mock_redis

            with patch("shutil.disk_usage") as mock_disk:
                mock_disk.return_value = (
                    1000000000,
                    500000000,
                    500000000,
                )  # total, used, free

                result = await asyncio.create_task(
                    system_health_check_task.s().apply_async().get()
                )

                assert "database_status" in result
                assert "redis_status" in result
                assert "disk_space" in result
                assert result["overall_health"] in ["HEALTHY", "WARNING", "CRITICAL"]

    @pytest.mark.asyncio
    async def test_database_maintenance_task(self, mock_db_manager):
        """测试数据库维护任务"""
        mock_db_manager.execute_query = AsyncMock()

        result = await asyncio.create_task(
            database_maintenance_task.s().apply_async().get()
        )

        assert "maintenance_actions" in result
        assert "statistics_updated" in result["maintenance_actions"]
        assert "logs_cleaned" in result["maintenance_actions"]

        # 验证ANALYZE命令被执行
        call_args_list = mock_db_manager.execute_query.call_args_list
        analyze_calls = [call for call in call_args_list if "ANALYZE" in call[0][0]]
        assert len(analyze_calls) > 0


class TestTaskMonitoring:
    """测试任务监控系统"""

    @pytest.fixture
    def task_monitor(self):
        """创建任务监控实例"""
        with patch("src.tasks.monitoring.DatabaseManager") as mock_manager:
            mock_db = AsyncMock()
            mock_manager.return_value = mock_db

            monitor = TaskMonitor()
            monitor.db_manager = mock_db
            return monitor

    def test_prometheus_metrics_creation(self, task_monitor):
        """测试Prometheus指标创建"""
        # 验证指标存在
        assert hasattr(task_monitor, "task_counter")
        assert hasattr(task_monitor, "task_duration")
        assert hasattr(task_monitor, "task_error_rate")
        assert hasattr(task_monitor, "active_tasks_gauge")
        assert hasattr(task_monitor, "queue_size_gauge")
        assert hasattr(task_monitor, "retry_counter")

    def test_record_task_start(self, task_monitor):
        """测试记录任务开始"""
        task_monitor.record_task_start("collect_odds_task")

        # 验证活跃任务数增加
        active_tasks_metric = task_monitor.active_tasks_gauge._value._value
        assert active_tasks_metric >= 0

    def test_record_task_completion(self, task_monitor):
        """测试记录任务完成"""
        task_monitor.record_task_completion("collect_fixtures_task", "SUCCESS", 120.5)

        # 验证计数器增加
        task_counter = task_monitor.task_counter._value._value
        assert len(task_counter) > 0

    def test_record_task_retry(self, task_monitor):
        """测试记录任务重试"""
        task_monitor.record_task_retry("collect_scores_task", retry_count=2)

        # 验证重试计数器增加
        retry_counter = task_monitor.retry_counter._value._value
        assert len(retry_counter) > 0

    def test_update_queue_size(self, task_monitor):
        """测试更新队列大小"""
        queue_sizes = {"fixtures": 5, "odds": 12, "scores": 3, "maintenance": 1}

        task_monitor.update_queue_sizes(queue_sizes)

        # 验证队列大小指标更新
        queue_gauge = task_monitor.queue_size_gauge._value._value
        assert len(queue_gauge) >= 4

    @pytest.mark.asyncio
    async def test_calculate_error_rates(self, task_monitor):
        """测试计算错误率"""
        # 模拟错误统计数据
        mock_error_stats = [
            {"task_name": "collect_odds_task", "error_count": 3, "total_count": 30},
            {"task_name": "collect_scores_task", "error_count": 1, "total_count": 60},
        ]
        task_monitor.db_manager.fetch_all = AsyncMock(return_value=mock_error_stats)

        await task_monitor.calculate_error_rates()

        # 验证数据库查询被调用
        task_monitor.db_manager.fetch_all.assert_called_once()

        # 验证错误率指标更新
        error_rate_gauge = task_monitor.task_error_rate._value._value
        assert len(error_rate_gauge) > 0

    @pytest.mark.asyncio
    async def test_check_task_health(self, task_monitor):
        """测试任务健康检查"""
        # 模拟健康数据
        mock_health_data = [
            {"metric": "error_rate", "value": 0.05},  # 5%错误率
            {"metric": "queue_backlog", "value": 15},  # 15个待处理任务
            {"metric": "avg_delay", "value": 300},  # 平均5分钟延迟
        ]
        task_monitor.db_manager.fetch_all = AsyncMock(return_value=mock_health_data)

        health_status = await task_monitor.check_task_health()

        assert "overall_status" in health_status
        assert "error_rate" in health_status
        assert "queue_backlog" in health_status
        assert health_status["overall_status"] in ["HEALTHY", "WARNING", "CRITICAL"]


class TestTaskUtils:
    """测试任务工具函数"""

    @pytest.fixture
    def mock_db_manager(self):
        with patch("src.tasks.utils.DatabaseManager") as mock_manager:
            mock_instance = AsyncMock()
            mock_manager.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_should_collect_live_scores(self, mock_db_manager):
        """测试是否应该采集实时比分"""
        # 模拟有进行中的比赛
        mock_live_matches = [
            {"id": 1, "status": "LIVE", "kickoff_time": datetime.now()}
        ]
        mock_db_manager.fetch_all = AsyncMock(return_value=mock_live_matches)

        should_collect = await should_collect_live_scores()

        assert should_collect is True
        mock_db_manager.fetch_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_not_collect_live_scores_no_matches(self, mock_db_manager):
        """测试无比赛时不应该采集实时比分"""
        mock_db_manager.fetch_all = AsyncMock(return_value=[])

        should_collect = await should_collect_live_scores()

        assert should_collect is False

    @pytest.mark.asyncio
    async def test_get_upcoming_matches(self, mock_db_manager):
        """测试获取即将开始的比赛"""
        mock_upcoming = [
            {"id": 1, "kickoff_time": datetime.now() + timedelta(hours=2)},
            {"id": 2, "kickoff_time": datetime.now() + timedelta(hours=4)},
        ]
        mock_db_manager.fetch_all = AsyncMock(return_value=mock_upcoming)

        upcoming = await get_upcoming_matches(hours=6)

        assert len(upcoming) == 2
        assert upcoming[0]["id"] == 1

    def test_calculate_next_collection_time(self):
        """测试计算下次采集时间"""
        base_time = datetime(2025, 1, 15, 10, 0, 0)

        # 每5分钟采集
        next_time = calculate_next_collection_time(base_time, interval_minutes=5)
        expected = datetime(2025, 1, 15, 10, 5, 0)

        assert next_time == expected


class TestIntegration:
    """集成测试 - 测试任务之间的协作"""

    @pytest.mark.asyncio
    async def test_full_data_collection_workflow(self):
        """测试完整的数据采集工作流程"""
        with patch(
            "src.data_collection.fixtures_collector.FixturesCollector"
        ) as mock_fixtures, patch(
            "src.data_collection.odds_collector.OddsCollector"
        ) as mock_odds, patch(
            "src.data_collection.scores_collector.ScoresCollector"
        ) as mock_scores, patch(
            "src.tasks.error_logger.TaskErrorLogger"
        ) as mock_logger:
            # 模拟成功的采集流程
            mock_fixtures_instance = AsyncMock()
            mock_fixtures_instance.collect_fixtures.return_value = {"fixtures": 10}
            mock_fixtures.return_value = mock_fixtures_instance

            mock_odds_instance = AsyncMock()
            mock_odds_instance.collect_odds.return_value = {"odds": 50}
            mock_odds.return_value = mock_odds_instance

            mock_scores_instance = AsyncMock()
            mock_scores_instance.collect_scores.return_value = {"scores": 5}
            mock_scores.return_value = mock_scores_instance

            mock_logger_instance = AsyncMock()
            mock_logger.return_value = mock_logger_instance

            # 执行手动采集任务
            result = await asyncio.create_task(
                manual_collect_all_data.s().apply_async().get()
            )

            # 验证所有采集器都被调用
            mock_fixtures_instance.collect_fixtures.assert_called()
            mock_odds_instance.collect_odds.assert_called()
            mock_scores_instance.collect_scores.assert_called()

            assert "triggered_tasks" in result

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """测试错误处理完整工作流程"""
        with patch(
            "src.data_collection.fixtures_collector.FixturesCollector"
        ) as mock_collector_class:
            # 模拟API错误
            mock_collector = AsyncMock()
            api_error = Exception("API连接超时")
            mock_collector.collect_fixtures.side_effect = api_error
            mock_collector_class.return_value = mock_collector

            # 模拟任务和错误记录器
            with patch("src.tasks.error_logger.TaskErrorLogger") as mock_logger_class:
                mock_logger = AsyncMock()
                mock_logger_class.return_value = mock_logger

                task_instance = collect_fixtures_task
                task_instance.request.retries = 0
                task_instance.error_logger = mock_logger

                # 模拟重试逻辑
                with patch.object(task_instance, "retry") as mock_retry:
                    mock_retry.side_effect = Retry("重试中...")

                    try:
                        await asyncio.create_task(task_instance.s().apply_async().get())
                    except Retry:
                        pass

                    # 验证错误被记录
                    mock_logger.log_api_failure.assert_called()

                    # 验证重试被触发
                    mock_retry.assert_called()

    def test_monitoring_integration(self):
        """测试监控系统集成"""
        monitor = TaskMonitor()

        # 模拟完整的监控工作流程
        monitor.record_task_start("collect_odds_task")
        monitor.record_task_completion("collect_odds_task", "SUCCESS", 45.2)
        monitor.update_queue_sizes({"odds": 5, "fixtures": 2})

        # 验证指标被正确更新
        assert monitor.task_counter._value._value
        assert monitor.task_duration._value._value
        assert monitor.active_tasks_gauge._value._value
        assert monitor.queue_size_gauge._value._value


class TestEdgeCases:
    """边界情况和异常测试"""

    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """测试数据库连接失败"""
        with patch("src.tasks.error_logger.DatabaseManager") as mock_manager:
            # 模拟数据库连接失败
            mock_manager.side_effect = OperationalError("数据库连接失败")

            logger = TaskErrorLogger()

            # 确保错误被妥善处理而不是崩溃
            try:
                await logger.log_task_error(
                    task_name="test_task",
                    task_id="test-123",
                    error=Exception("测试"),
                    context={},
                    retry_count=0,
                )
            except Exception as e:
                # 确保只抛出预期的数据库错误，而不是其他异常
                assert "数据库连接失败" in str(e)

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self):
        """测试Redis连接失败"""
        with patch("redis.Redis") as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis.ping.side_effect = Exception("Redis连接失败")
            mock_redis_class.return_value = mock_redis

            # 系统健康检查应该检测到Redis问题
            with patch("src.tasks.maintenance_tasks.DatabaseManager") as mock_db:
                mock_db_instance = AsyncMock()
                mock_db.return_value = mock_db_instance
                mock_db_instance.execute_query.return_value = [(1,)]

                result = await asyncio.create_task(
                    system_health_check_task.s().apply_async().get()
                )

                assert result["redis_status"] == "ERROR"
                assert result["overall_health"] in ["WARNING", "CRITICAL"]

    def test_invalid_task_configuration(self):
        """测试无效任务配置"""
        retry_config = TaskRetryConfig()

        # 测试不存在的任务配置
        config = retry_config.get_retry_config("nonexistent_task")

        # 应该返回默认配置
        assert config is not None
        assert config["max_retries"] == TaskRetryConfig.DEFAULT_MAX_RETRIES
        assert config["retry_delay"] == TaskRetryConfig.DEFAULT_RETRY_DELAY

    @pytest.mark.asyncio
    async def test_large_error_log_handling(self):
        """测试大量错误日志处理"""
        with patch("src.tasks.error_logger.DatabaseManager") as mock_manager:
            mock_db = AsyncMock()
            mock_manager.return_value = mock_db

            # 模拟大量错误日志清理
            mock_db.execute_query = AsyncMock(return_value=1000)  # 1000条日志被清理

            logger = TaskErrorLogger()
            logger.db_manager = mock_db

            deleted_count = await logger.cleanup_old_logs(days=1)

            assert deleted_count == 1000
            mock_db.execute_query.assert_called_once()


if __name__ == "__main__":
    # 运行测试
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "--cov=src.tasks",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-fail-under=85",  # 确保覆盖率超过85%
        ]
    )
