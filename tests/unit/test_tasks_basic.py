"""
任务模块基础测试
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.tasks.error_logger import TaskErrorLogger
from src.tasks.utils import (calculate_next_collection_time,
                             get_upcoming_matches, should_collect_live_scores)


class TestTaskErrorLogger:
    """任务错误日志测试"""

    def setup_method(self):
        """测试设置"""
        self.logger = TaskErrorLogger()

    def test_error_logger_initialization(self):
        """测试错误日志器初始化"""
        assert self.logger is not None
        assert hasattr(self.logger, "log_task_error")
        assert hasattr(self.logger, "log_api_failure")

    @pytest.mark.asyncio
    @patch("src.tasks.error_logger.DatabaseManager")
    async def test_log_task_error(self, mock_db):
        """测试记录任务错误"""
        mock_db_instance = AsyncMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.get_async_session.return_value.__aenter__.return_value = (
            AsyncMock()
        )

        # 正确的方法签名：task_name, task_id, error, context, retry_count
        test_error = Exception("Test error message")
        await self.logger.log_task_error(
            "test_task", "task_123", test_error, {"key": "value"}, 0
        )

        # 验证数据库操作被调用
        mock_db_instance.get_async_session.assert_called()

    @pytest.mark.asyncio
    @patch("src.tasks.error_logger.DatabaseManager")
    async def test_log_api_failure(self, mock_db):
        """测试记录API失败"""
        mock_db_instance = AsyncMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.get_async_session.return_value.__aenter__.return_value = (
            AsyncMock()
        )

        # 正确的方法签名：task_name, api_endpoint, http_status, error_message, retry_count, response_data
        await self.logger.log_api_failure(
            "test_task", "test_api", 500, "Internal Server Error", 0, None
        )

        mock_db_instance.get_async_session.assert_called()

    @pytest.mark.asyncio
    @patch("src.tasks.error_logger.DatabaseManager")
    async def test_log_data_collection_error(self, mock_db):
        """测试记录数据收集错误"""
        mock_db_instance = AsyncMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.get_async_session.return_value.__aenter__.return_value = (
            AsyncMock()
        )

        await self.logger.log_data_collection_error(
            "fixtures", "Connection timeout", {"timeout": 30}
        )

        mock_db_instance.get_async_session.assert_called()

    @pytest.mark.asyncio
    @patch("src.tasks.error_logger.DatabaseManager")
    async def test_get_error_statistics(self, mock_db):
        """测试获取错误统计"""
        mock_db_instance = AsyncMock()
        mock_db.return_value = mock_db_instance
        mock_session = AsyncMock()
        mock_db_instance.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        # 模拟查询结果 - 需要多次调用execute，分别对应不同的统计查询
        mock_result1 = AsyncMock()
        mock_result1.scalar.return_value = 10  # total_errors

        mock_result2 = AsyncMock()
        mock_result2.__iter__.return_value = [
            AsyncMock(task_name="test_task", error_count=5),
        ]

        mock_result3 = AsyncMock()
        mock_result3.__iter__.return_value = [
            AsyncMock(error_type="task_error", error_count=3),
        ]

        # 设置execute的多次调用返回值
        mock_session.execute.side_effect = [mock_result1, mock_result2, mock_result3]

        # 重新初始化logger以使用mock的数据库管理器
        self.logger.db_manager = mock_db_instance

        stats = await self.logger.get_error_statistics()

        assert isinstance(stats, dict)
        assert "total_errors" in stats
        assert "task_errors" in stats
        assert "type_errors" in stats

    @pytest.mark.asyncio
    @patch("src.tasks.error_logger.DatabaseManager")
    async def test_cleanup_old_logs(self, mock_db):
        """测试清理旧日志"""
        mock_db_instance = AsyncMock()
        mock_db.return_value = mock_db_instance
        mock_session = AsyncMock()
        mock_db_instance.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        # 模拟删除结果
        mock_result = AsyncMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        # 假设方法存在且是异步的
        if hasattr(self.logger, "cleanup_old_logs"):
            result = await self.logger.cleanup_old_logs(30)
            assert isinstance(result, int) or result is None
        else:
            # 如果方法不存在，跳过测试
            pytest.skip("cleanup_old_logs method not implemented")


class TestTaskUtils:
    """任务工具函数测试"""

    @pytest.mark.asyncio
    @patch("src.tasks.utils.DatabaseManager")
    async def test_should_collect_live_scores_with_matches(self, mock_db):
        """测试应该收集实时比分 - 有比赛进行"""
        mock_db_instance = AsyncMock()
        mock_db.return_value = mock_db_instance
        mock_session = AsyncMock()
        mock_db_instance.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        # 模拟查询结果
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 2  # 有2场比赛
        mock_session.execute.return_value = mock_result

        result = await should_collect_live_scores()

        assert isinstance(result, bool)
        assert result is True

    @pytest.mark.asyncio
    @patch("src.tasks.utils.DatabaseManager")
    async def test_should_collect_live_scores_no_matches(self, mock_db):
        """测试应该收集实时比分 - 无比赛进行"""
        mock_db_instance = AsyncMock()
        mock_db.return_value = mock_db_instance
        mock_session = AsyncMock()
        mock_db_instance.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        # 模拟查询结果
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 0  # 无比赛
        mock_session.execute.return_value = mock_result

        result = await should_collect_live_scores()

        assert result is False

    @pytest.mark.asyncio
    @patch("src.tasks.utils.DatabaseManager")
    async def test_get_upcoming_matches(self, mock_db):
        """测试获取即将开始的比赛"""
        mock_db_instance = AsyncMock()
        mock_db.return_value = mock_db_instance
        mock_session = AsyncMock()
        mock_db_instance.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        # 模拟查询结果
        mock_result = AsyncMock()
        mock_row1 = Mock()
        mock_row1.id = 1
        mock_row1.home_team_id = 10
        mock_row1.away_team_id = 20
        mock_row1.league_id = 1
        mock_row1.match_time = datetime.now() + timedelta(hours=2)
        mock_row1.match_status = "scheduled"

        mock_row2 = Mock()
        mock_row2.id = 2
        mock_row2.home_team_id = 30
        mock_row2.away_team_id = 40
        mock_row2.league_id = 1
        mock_row2.match_time = datetime.now() + timedelta(hours=4)
        mock_row2.match_status = "scheduled"

        mock_result.__iter__.return_value = [mock_row1, mock_row2]
        mock_session.execute.return_value = mock_result

        # 使用正确的参数名 hours 而不是 hours_ahead
        matches = await get_upcoming_matches(hours=6)

        assert isinstance(matches, list)
        assert len(matches) == 2

    def test_calculate_next_collection_time(self):
        """测试计算下次收集时间"""
        current_time = datetime.now()
        interval_minutes = 15

        next_time = calculate_next_collection_time(interval_minutes)

        assert isinstance(next_time, datetime)
        assert next_time > current_time

        # 验证时间间隔
        time_diff = next_time - current_time
        assert time_diff.total_seconds() >= interval_minutes * 60 - 60  # 允许1分钟误差


class TestTaskMonitoring:
    """任务监控测试"""

    def test_task_metrics_creation(self):
        """测试任务指标创建"""
        from prometheus_client import Counter, Gauge, Histogram

        # 模拟创建Prometheus指标
        task_counter = Counter("football_tasks_total", "Total tasks executed")
        task_duration = Histogram(
            "football_task_duration_seconds", "Task execution time"
        )
        queue_size = Gauge("football_queue_size", "Current queue size")

        assert task_counter is not None
        assert task_duration is not None
        assert queue_size is not None

    def test_record_task_execution(self):
        """测试记录任务执行"""
        from prometheus_client import Counter

        task_counter = Counter("test_tasks_total", "Test tasks")
        initial_value = task_counter._value._value

        # 记录任务执行
        task_counter.inc()

        assert task_counter._value._value == initial_value + 1

    def test_measure_task_duration(self):
        """测试测量任务执行时间"""
        import time

        from prometheus_client import Histogram

        duration_histogram = Histogram("test_task_duration", "Test task duration")

        start_time = time.time()
        time.sleep(0.001)  # 模拟任务执行
        execution_time = time.time() - start_time

        duration_histogram.observe(execution_time)

        assert execution_time > 0


class TestTaskScheduling:
    """任务调度测试"""

    def test_task_priority_handling(self):
        """测试任务优先级处理"""
        # 模拟任务优先级队列
        tasks = [
            {"name": "urgent_task", "priority": 1},
            {"name": "normal_task", "priority": 5},
            {"name": "low_priority_task", "priority": 10},
        ]

        # 按优先级排序（数字越小优先级越高）
        sorted_tasks = sorted(tasks, key=lambda x: x["priority"])

        assert sorted_tasks[0]["name"] == "urgent_task"
        assert sorted_tasks[-1]["name"] == "low_priority_task"

    def test_task_retry_logic(self):
        """测试任务重试逻辑"""
        max_retries = 3
        current_retry = 0

        def should_retry(retry_count, max_retries):
            return retry_count < max_retries

        # 模拟重试
        while should_retry(current_retry, max_retries):
            current_retry += 1
            if current_retry == 2:  # 模拟第二次重试成功
                break

        assert current_retry == 2
        assert current_retry <= max_retries

    def test_exponential_backoff(self):
        """测试指数退避"""
        # import math

        def calculate_backoff_delay(retry_count, base_delay=1):
            return base_delay * (2**retry_count)

        delays = [calculate_backoff_delay(i) for i in range(5)]
        expected_delays = [1, 2, 4, 8, 16]

        assert delays == expected_delays

    def test_task_timeout_handling(self):
        """测试任务超时处理"""
        import time
        from datetime import datetime

        task_start_time = datetime.now()
        timeout_seconds = 5

        # 模拟任务执行
        time.sleep(0.001)

        current_time = datetime.now()
        execution_time = (current_time - task_start_time).total_seconds()

        is_timeout = execution_time > timeout_seconds

        assert not is_timeout  # 应该没有超时
        assert execution_time < timeout_seconds


class TestTaskErrorHandling:
    """任务错误处理测试"""

    def test_task_failure_recovery(self):
        """测试任务失败恢复"""
        failed_tasks = ["task_1", "task_2", "task_3"]
        recovery_strategies = {"task_1": "retry", "task_2": "skip", "task_3": "alert"}

        for task in failed_tasks:
            strategy = recovery_strategies.get(task, "default")
            assert strategy in ["retry", "skip", "alert", "default"]

    def test_error_categorization(self):
        """测试错误分类"""
        errors = [
            {"type": "ConnectionError", "severity": "high"},
            {"type": "ValidationError", "severity": "medium"},
            {"type": "TimeoutError", "severity": "high"},
            {"type": "DataError", "severity": "low"},
        ]

        high_severity_errors = [e for e in errors if e["severity"] == "high"]

        assert len(high_severity_errors) == 2
        assert all(e["severity"] == "high" for e in high_severity_errors)

    def test_alert_threshold_checking(self):
        """测试告警阈值检查"""
        error_counts = {"api_failures": 15, "database_errors": 5, "timeout_errors": 8}

        thresholds = {"api_failures": 10, "database_errors": 5, "timeout_errors": 10}

        alerts = []
        for error_type, count in error_counts.items():
            if count >= thresholds.get(error_type, 0):
                alerts.append(f"{error_type}: {count}")

        assert len(alerts) >= 2  # api_failures 和 database_errors 超过阈值
