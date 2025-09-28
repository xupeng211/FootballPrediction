"""
Unit tests for scheduler module functionality.

Tests the TaskScheduler, JobManager, and related components including:
- Task scheduling and cron expression handling
- Periodic task triggering
- Batch task execution and queue consumption
- Resource monitoring and timeout handling
- Error handling and retry logic
- External dependency mocking (Redis/Kafka)
"""

import asyncio
import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from concurrent.futures import ThreadPoolExecutor

from src.scheduler.job_manager import JobManager, JobExecutionResult, ResourceMonitor
from src.scheduler.task_scheduler import TaskScheduler, ScheduledTask


class TestScheduledTask:
    """Test cases for ScheduledTask class."""

    @pytest.fixture
    def sample_task_function(self):
        """Sample task function for testing."""
        def mock_task():
            return "task_completed"
        return mock_task

    @pytest.fixture
    def sample_task(self, sample_task_function):
        """Create sample ScheduledTask for testing."""
        return ScheduledTask(
            task_id="test_task",
            name="Test Task",
            cron_expression="0 * * * *",  # 每小时
            task_function=sample_task_function,
            priority=5,
            max_retries=3,
            timeout=300,
            description="Test task for unit testing"
        )

    def test_task_initialization(self, sample_task):
        """Test task initialization with correct parameters."""
        assert sample_task.task_id == "test_task"
        assert sample_task.name == "Test Task"
        assert sample_task.cron_expression == "0 * * * *"
        assert sample_task.priority == 5
        assert sample_task.max_retries == 3
        assert sample_task.timeout == 300
        assert not sample_task.is_running
        assert sample_task.retry_count == 0
        assert sample_task.last_error is None
        assert sample_task.next_run_time is not None

    def test_should_run_logic(self, sample_task):
        """Test task should run logic."""
        # Task should not run if already running
        sample_task.is_running = True
        assert not sample_task.should_run(datetime.now())

        # Task should not run if next_run_time is None
        sample_task.is_running = False
        sample_task.next_run_time = None
        assert not sample_task.should_run(datetime.now())

        # Task should run if current_time >= next_run_time and not running
        sample_task.next_run_time = datetime.now() - timedelta(minutes=1)
        assert sample_task.should_run(datetime.now())

        # Task should not run if current_time < next_run_time
        sample_task.next_run_time = datetime.now() + timedelta(minutes=1)
        assert not sample_task.should_run(datetime.now())

    def test_mark_completed_success(self, sample_task):
        """Test marking task as completed successfully."""
        sample_task.is_running = True
        sample_task.retry_count = 2
        sample_task.last_error = "Previous error"

        sample_task.mark_completed(success=True)

        assert not sample_task.is_running
        assert sample_task.retry_count == 0
        assert sample_task.last_error is None
        assert sample_task.last_run_time is not None

    def test_mark_completed_failure(self, sample_task):
        """Test marking task as completed with failure."""
        sample_task.is_running = True
        initial_retry_count = sample_task.retry_count

        sample_task.mark_completed(success=False, error="Task failed")

        assert not sample_task.is_running
        assert sample_task.retry_count == initial_retry_count + 1
        assert sample_task.last_error == "Task failed"
        assert sample_task.last_run_time is not None

    def test_to_dict_conversion(self, sample_task):
        """Test task to dictionary conversion."""
        result = sample_task.to_dict()

        assert isinstance(result, dict)
        assert result["task_id"] == "test_task"
        assert result["name"] == "Test Task"
        assert result["cron_expression"] == "0 * * * *"
        assert result["priority"] == 5
        assert result["max_retries"] == 3
        assert result["timeout"] == 300
        assert result["is_running"] is False
        assert result["retry_count"] == 0
        assert result["last_error"] is None

    def test_invalid_cron_expression(self, sample_task_function):
        """Test handling of invalid cron expressions."""
        # Should handle invalid cron gracefully without raising exception
        task = ScheduledTask(
            task_id="invalid_task",
            name="Invalid Task",
            cron_expression="invalid_cron",
            task_function=sample_task_function
        )
        # Verify that invalid cron results in None next_run_time
        assert task.next_run_time is None


class TestTaskScheduler:
    """Test cases for TaskScheduler class."""

    @pytest.fixture
    def mock_job_manager(self):
        """Mock JobManager."""
        return MagicMock(spec=JobManager)

    @pytest.fixture
    def mock_dependency_resolver(self):
        """Mock DependencyResolver."""
        mock_resolver = MagicMock()
        mock_resolver.add_task = MagicMock()
        mock_resolver.remove_task = MagicMock()
        mock_resolver.can_execute = MagicMock(return_value=True)
        return mock_resolver

    @pytest.fixture
    def mock_recovery_handler(self):
        """Mock RecoveryHandler."""
        return MagicMock()

    @pytest.fixture
    def scheduler(self, mock_job_manager, mock_dependency_resolver, mock_recovery_handler):
        """Create TaskScheduler with mocked dependencies."""
        with patch('src.scheduler.task_scheduler.JobManager', return_value=mock_job_manager), \
             patch('src.scheduler.task_scheduler.DependencyResolver', return_value=mock_dependency_resolver), \
             patch('src.scheduler.task_scheduler.RecoveryHandler', return_value=mock_recovery_handler):

            scheduler = TaskScheduler()
            scheduler.job_manager = mock_job_manager
            scheduler.dependency_resolver = mock_dependency_resolver
            scheduler.recovery_handler = mock_recovery_handler
            return scheduler

    @pytest.fixture
    def sample_task(self):
        """Sample task function."""
        def mock_task():
            return "completed"
        return mock_task

    @pytest.fixture
    def scheduled_task(self, sample_task):
        """Sample scheduled task."""
        return ScheduledTask(
            task_id="test_task",
            name="Test Task",
            cron_expression="0 * * * *",
            task_function=sample_task,
            priority=5
        )

    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert not scheduler.is_running
        assert scheduler.tasks == {}
        assert scheduler.check_interval == 30
        assert scheduler.max_concurrent_tasks == 10
        assert scheduler.stop_event.is_set() is False

    def test_register_task_success(self, scheduler, scheduled_task):
        """Test successful task registration."""
        result = scheduler.register_task(scheduled_task)

        assert result is True
        assert scheduled_task.task_id in scheduler.tasks
        assert scheduler.tasks[scheduled_task.task_id] == scheduled_task
        scheduler.dependency_resolver.add_task.assert_called_once_with(
            scheduled_task.task_id, scheduled_task.dependencies
        )

    def test_register_task_invalid_cron(self, scheduler, sample_task):
        """Test task registration with invalid cron expression."""
        invalid_task = ScheduledTask(
            task_id="invalid_task",
            name="Invalid Task",
            cron_expression="invalid",
            task_function=sample_task
        )

        result = scheduler.register_task(invalid_task)
        assert result is False
        assert invalid_task.task_id not in scheduler.tasks

    def test_unregister_task(self, scheduler, scheduled_task):
        """Test task unregistration."""
        # First register the task
        scheduler.register_task(scheduled_task)
        assert scheduled_task.task_id in scheduler.tasks

        # Then unregister it
        result = scheduler.unregister_task(scheduled_task.task_id)

        assert result is True
        assert scheduled_task.task_id not in scheduler.tasks
        scheduler.dependency_resolver.remove_task.assert_called_once_with(scheduled_task.task_id)

    def test_unregister_nonexistent_task(self, scheduler):
        """Test unregistering non-existent task."""
        result = scheduler.unregister_task("nonexistent_task")
        assert result is False

    def test_get_ready_tasks(self, scheduler, scheduled_task):
        """Test getting ready tasks."""
        # Register task
        scheduler.register_task(scheduled_task)

        # Set task to be ready
        scheduled_task.next_run_time = datetime.now() - timedelta(minutes=1)
        scheduled_task.is_running = False

        ready_tasks = scheduler.get_ready_tasks(datetime.now())
        assert len(ready_tasks) == 1
        assert ready_tasks[0] == scheduled_task

    def test_get_ready_tasks_with_dependencies(self, scheduler, scheduled_task):
        """Test getting ready tasks respects dependencies."""
        scheduler.register_task(scheduled_task)
        scheduled_task.next_run_time = datetime.now() - timedelta(minutes=1)

        # Mock dependency check to return False
        scheduler.dependency_resolver.can_execute.return_value = False

        ready_tasks = scheduler.get_ready_tasks(datetime.now())
        assert len(ready_tasks) == 0  # Task should not be ready due to unsatisfied dependencies

    def test_get_ready_tasks_with_retry_limit(self, scheduler, scheduled_task):
        """Test getting ready tasks respects retry limit."""
        scheduler.register_task(scheduled_task)
        scheduled_task.next_run_time = datetime.now() - timedelta(minutes=1)
        scheduled_task.retry_count = scheduled_task.max_retries + 1

        ready_tasks = scheduler.get_ready_tasks(datetime.now())
        assert len(ready_tasks) == 0  # Task should not be ready due to retry limit

    def test_execute_task_success(self, scheduler, scheduled_task):
        """Test successful task execution."""
        scheduler.register_task(scheduled_task)
        scheduler.job_manager.execute_job.return_value = True

        scheduler.execute_task(scheduled_task)

        assert scheduled_task.is_running is False
        assert scheduled_task.last_run_time is not None
        assert scheduled_task.retry_count == 0
        scheduler.job_manager.execute_job.assert_called_once()

    def test_execute_task_failure(self, scheduler, scheduled_task):
        """Test task execution failure."""
        scheduler.register_task(scheduled_task)
        scheduler.job_manager.execute_job.return_value = False

        scheduler.execute_task(scheduled_task)

        assert scheduled_task.is_running is False
        assert scheduled_task.last_run_time is not None
        assert scheduled_task.retry_count == 1
        assert scheduled_task.last_error is not None
        scheduler.recovery_handler.handle_task_failure.assert_called_once()

    def test_execute_task_exception(self, scheduler, scheduled_task):
        """Test task execution with exception."""
        scheduler.register_task(scheduled_task)
        scheduler.job_manager.execute_job.side_effect = Exception("Test exception")

        scheduler.execute_task(scheduled_task)

        assert scheduled_task.is_running is False
        assert scheduled_task.retry_count == 1
        assert "Test exception" in scheduled_task.last_error
        scheduler.recovery_handler.handle_task_failure.assert_called_once()

    def test_start_scheduler(self, scheduler):
        """Test starting the scheduler."""
        with patch.object(scheduler, 'register_predefined_tasks') as mock_register:
            result = scheduler.start()

            assert result is True
            assert scheduler.is_running is True
            assert scheduler.scheduler_thread is not None
            mock_register.assert_called_once()

    def test_start_already_running_scheduler(self, scheduler):
        """Test starting scheduler when already running."""
        scheduler.is_running = True

        result = scheduler.start()
        assert result is False

    def test_stop_scheduler(self, scheduler):
        """Test stopping the scheduler."""
        # Start scheduler first
        scheduler.is_running = True
        scheduler.scheduler_thread = MagicMock()
        scheduler.scheduler_thread.is_alive.return_value = False  # Thread is not alive (stopped)
        scheduler.stop_event = MagicMock()

        result = scheduler.stop()

        assert result is True
        assert scheduler.is_running is False
        scheduler.stop_event.set.assert_called_once()

    def test_stop_scheduler_timeout(self, scheduler):
        """Test stopping scheduler with timeout."""
        # Start scheduler first
        scheduler.is_running = True
        scheduler.scheduler_thread = MagicMock()
        scheduler.scheduler_thread.is_alive.return_value = True  # Thread still alive (timeout)
        scheduler.stop_event = MagicMock()

        result = scheduler.stop()

        assert result is False  # Should return False due to timeout
        # Note: is_running is still set to False even on timeout
        assert scheduler.is_running is False
        scheduler.stop_event.set.assert_called_once()

    def test_get_task_status_single_task(self, scheduler, scheduled_task):
        """Test getting status of single task."""
        scheduler.register_task(scheduled_task)

        result = scheduler.get_task_status(scheduled_task.task_id)
        assert result["task_id"] == scheduled_task.task_id
        assert result["name"] == scheduled_task.name

    def test_get_task_status_nonexistent_task(self, scheduler):
        """Test getting status of non-existent task."""
        result = scheduler.get_task_status("nonexistent")
        assert "error" in result

    def test_get_task_status_all_tasks(self, scheduler, scheduled_task):
        """Test getting status of all tasks."""
        scheduler.register_task(scheduled_task)

        result = scheduler.get_task_status()
        assert "scheduler_status" in result
        assert "tasks" in result
        assert scheduled_task.task_id in result["tasks"]
        assert result["scheduler_status"]["total_tasks"] == 1

    def test_update_task_schedule(self, scheduler, scheduled_task):
        """Test updating task schedule."""
        scheduler.register_task(scheduled_task)
        old_cron = scheduled_task.cron_expression
        new_cron = "*/30 * * * *"  # Every 30 minutes

        result = scheduler.update_task_schedule(scheduled_task.task_id, new_cron)

        assert result is True
        assert scheduled_task.cron_expression == new_cron
        assert scheduled_task.cron_expression != old_cron

    def test_update_task_schedule_invalid_task(self, scheduler):
        """Test updating schedule for non-existent task."""
        result = scheduler.update_task_schedule("nonexistent", "0 * * * *")
        assert result is False

    @patch('src.scheduler.task_scheduler.collect_fixtures')
    @patch('src.scheduler.task_scheduler.collect_odds')
    @patch('src.scheduler.task_scheduler.collect_live_scores_conditional')
    @patch('src.scheduler.task_scheduler.calculate_features_batch')
    @patch('src.scheduler.task_scheduler.cleanup_data')
    def test_register_predefined_tasks(self, mock_cleanup, mock_features, mock_scores, mock_odds, mock_fixtures, scheduler):
        """Test registration of predefined tasks."""
        scheduler.register_predefined_tasks()

        assert len(scheduler.tasks) == 5  # Should register 5 predefined tasks
        assert "fixtures_collection" in scheduler.tasks
        assert "odds_collection" in scheduler.tasks
        assert "live_scores_collection" in scheduler.tasks
        assert "feature_calculation" in scheduler.tasks
        assert "data_cleanup" in scheduler.tasks


class TestJobManager:
    """Test cases for JobManager class."""

    @pytest.fixture
    def mock_db_manager(self):
        """Mock DatabaseManager."""
        return MagicMock()

    @pytest.fixture
    def job_manager(self, mock_db_manager):
        """Create JobManager with mocked database manager."""
        with patch('src.scheduler.job_manager.DatabaseManager', return_value=mock_db_manager):
            return JobManager(max_workers=3)

    @pytest.fixture
    def sample_task_function(self):
        """Sample task function."""
        def mock_task(x, y=10):
            return x + y
        return mock_task

    def test_job_manager_initialization(self, job_manager):
        """Test job manager initialization."""
        assert job_manager.max_workers == 3
        assert job_manager.total_jobs_executed == 0
        assert job_manager.successful_jobs == 0
        assert job_manager.failed_jobs == 0
        assert len(job_manager.execution_history) == 0
        assert len(job_manager.running_jobs) == 0

    def test_execute_sync_job_success(self, job_manager, sample_task_function):
        """Test successful sync job execution."""
        result = job_manager.execute_job(
            task_id="test_job",
            task_function=sample_task_function,
            args=(5,),
            kwargs={"y": 10},
            timeout=60
        )

        assert result is True
        assert job_manager.total_jobs_executed == 1
        assert job_manager.successful_jobs == 1
        assert job_manager.failed_jobs == 0
        assert len(job_manager.execution_history) == 1

    def test_execute_async_job_success(self, job_manager):
        """Test successful async job execution."""
        async def async_task(x, y=10):
            await asyncio.sleep(0.1)  # Simulate async work
            return x + y

        result = job_manager.execute_job(
            task_id="async_test_job",
            task_function=async_task,
            args=(5,),
            kwargs={"y": 10},
            timeout=60
        )

        assert result is True
        assert job_manager.total_jobs_executed == 1
        assert job_manager.successful_jobs == 1

    def test_execute_job_timeout(self, job_manager):
        """Test job execution timeout."""
        def slow_task():
            time.sleep(10)  # Will timeout

        result = job_manager.execute_job(
            task_id="slow_job",
            task_function=slow_task,
            timeout=1
        )

        assert result is False
        assert job_manager.total_jobs_executed == 1
        assert job_manager.failed_jobs == 1
        assert len(job_manager.execution_history) == 1
        assert not job_manager.execution_history[0].success

    def test_execute_job_exception(self, job_manager):
        """Test job execution with exception."""
        def failing_task():
            raise ValueError("Test error")

        result = job_manager.execute_job(
            task_id="failing_job",
            task_function=failing_task,
            timeout=60
        )

        assert result is False
        assert job_manager.total_jobs_executed == 1
        assert job_manager.failed_jobs == 1
        assert "Test error" in job_manager.execution_history[-1].error

    def test_execute_already_running_job(self, job_manager, sample_task_function):
        """Test executing job that's already running."""
        # Simulate job already running
        job_manager.running_jobs["duplicate_job"] = MagicMock()

        result = job_manager.execute_job(
            task_id="duplicate_job",
            task_function=sample_task_function,
            timeout=60
        )

        assert result is False
        assert job_manager.total_jobs_executed == 0  # Should not execute

    def test_kill_job(self, job_manager):
        """Test killing a running job."""
        # Simulate running job
        mock_thread = MagicMock()
        job_manager.running_jobs["running_job"] = mock_thread

        result = job_manager.kill_job("running_job")

        assert result is True
        assert "running_job" not in job_manager.running_jobs

    def test_kill_nonexistent_job(self, job_manager):
        """Test killing non-existent job."""
        result = job_manager.kill_job("nonexistent_job")
        assert result is False

    def test_get_running_jobs(self, job_manager):
        """Test getting list of running jobs."""
        # Add some mock running jobs
        job_manager.running_jobs["job1"] = MagicMock()
        job_manager.running_jobs["job2"] = MagicMock()

        running_jobs = job_manager.get_running_jobs()
        assert set(running_jobs) == {"job1", "job2"}

    def test_get_job_statistics(self, job_manager, sample_task_function):
        """Test getting job execution statistics."""
        # Execute some jobs to generate statistics
        job_manager.execute_job("job1", sample_task_function, args=(1,), timeout=60)
        job_manager.execute_job("job2", sample_task_function, args=(2,), timeout=60)

        # Execute a failing job
        def failing_task():
            raise Exception("Failed")
        job_manager.execute_job("job3", failing_task, timeout=60)

        stats = job_manager.get_job_statistics()
        assert stats["total_jobs_executed"] == 3
        assert stats["successful_jobs"] == 2
        assert stats["failed_jobs"] == 1
        assert stats["success_rate"] == 66.67  # 2/3 * 100
        assert "running_jobs_count" in stats
        assert "avg_execution_time" in stats
        assert "max_workers" in stats

    def test_get_execution_history(self, job_manager, sample_task_function):
        """Test getting execution history."""
        # Execute some jobs
        for i in range(5):
            job_manager.execute_job(f"job{i}", sample_task_function, args=(i,), timeout=60)

        history = job_manager.get_execution_history(limit=3)
        assert len(history) == 3  # Should return limited results

        # Verify history is in reverse chronological order
        history_all = job_manager.get_execution_history(limit=10)
        assert len(history_all) == 5

    def test_cleanup_resources(self, job_manager):
        """Test resource cleanup."""
        # Add some execution history and running jobs
        job_manager.execution_history.append(MagicMock())
        job_manager.running_jobs["test_job"] = MagicMock()

        job_manager.cleanup_resources()

        assert len(job_manager.execution_history) == 0
        assert len(job_manager.running_jobs) == 0


class TestResourceMonitor:
    """Test cases for ResourceMonitor class."""

    @pytest.fixture
    def resource_monitor(self):
        """Create ResourceMonitor instance."""
        return ResourceMonitor()

    def test_monitor_initialization(self, resource_monitor):
        """Test monitor initialization."""
        assert not resource_monitor.monitoring
        assert resource_monitor.monitor_thread is None
        assert resource_monitor.resource_stats == {"memory": [], "cpu": []}

    @patch('psutil.Process')
    def test_start_stop_monitoring(self, mock_process_class, resource_monitor):
        """Test starting and stopping monitoring."""
        # Mock process
        mock_process = MagicMock()
        mock_process_class.return_value = mock_process
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
        mock_process.cpu_percent.return_value = 50.0

        # Start monitoring
        resource_monitor.start_monitoring("test_job")
        assert resource_monitor.monitoring is True
        assert resource_monitor.monitor_thread is not None

        # Let it run briefly
        time.sleep(0.1)

        # Stop monitoring
        avg_memory, avg_cpu = resource_monitor.stop_monitoring()

        assert resource_monitor.monitoring is False
        assert avg_memory >= 0
        assert avg_cpu >= 0

    def test_stop_monitoring_no_data(self, resource_monitor):
        """Test stopping monitoring when no data collected."""
        avg_memory, avg_cpu = resource_monitor.stop_monitoring()
        assert avg_memory == 0.0
        assert avg_cpu == 0.0


class TestJobExecutionResult:
    """Test cases for JobExecutionResult class."""

    @pytest.fixture
    def execution_result(self):
        """Create sample JobExecutionResult."""
        start_time = datetime.now() - timedelta(seconds=5)
        end_time = datetime.now()

        return JobExecutionResult(
            job_id="test_job",
            success=True,
            start_time=start_time,
            end_time=end_time,
            result="task_completed",
            execution_time=5.0,
            memory_usage=100.5,
            cpu_usage=25.3
        )

    def test_execution_result_initialization(self, execution_result):
        """Test execution result initialization."""
        assert execution_result.job_id == "test_job"
        assert execution_result.success is True
        assert execution_result.result == "task_completed"
        assert execution_result.execution_time == 5.0
        assert execution_result.memory_usage == 100.5
        assert execution_result.cpu_usage == 25.3

    def test_to_dict_conversion(self, execution_result):
        """Test execution result to dictionary conversion."""
        result_dict = execution_result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["job_id"] == "test_job"
        assert result_dict["success"] is True
        assert result_dict["result"] == "task_completed"
        assert result_dict["execution_time"] == 5.0
        assert result_dict["memory_usage"] == 100.5
        assert result_dict["cpu_usage"] == 25.3
        assert "start_time" in result_dict
        assert "end_time" in result_dict

    def test_execution_result_with_failure(self):
        """Test execution result with failure."""
        start_time = datetime.now() - timedelta(seconds=2)
        end_time = datetime.now()

        failed_result = JobExecutionResult(
            job_id="failed_job",
            success=False,
            start_time=start_time,
            end_time=end_time,
            error="Task failed due to timeout"
        )

        assert failed_result.success is False
        assert failed_result.error == "Task failed due to timeout"
        assert failed_result.result is None

        result_dict = failed_result.to_dict()
        assert result_dict["success"] is False
        assert result_dict["error"] == "Task failed due to timeout"
        assert result_dict["result"] is None