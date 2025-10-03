from datetime import datetime

from src.scheduler.job_manager import JobManager, JobExecutionResult
from src.scheduler.task_scheduler import TaskScheduler, ScheduledTask
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import pytest

"""
Unit tests for batch task execution functionality.:

Tests the batch processing capabilities including:
- Bulk task registration and execution
- Queue consumption and processing
- Resource management during batch operations
- Error handling and recovery
"""

class TestBatchTaskExecution:
    """Test cases for batch task execution scenarios."""
    @pytest.fixture
    def mock_database(self):
        """Mock database connection."""
        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_db.get_async_session.return_value.__aenter__.return_value = mock_session
        mock_db.get_async_session.return_value.__aexit__.return_value = AsyncMock()
        return mock_db
    @pytest.fixture
    def mock_feature_store(self):
        """Mock feature store."""
        mock_store = MagicMock()
        mock_store.get_features = AsyncMock()
        return mock_store
    @pytest.fixture
    def task_scheduler(self, mock_database, mock_feature_store):
        """Create TaskScheduler instance with mocked dependencies."""
        with patch(:
            "src.scheduler.task_scheduler.DatabaseManager[", return_value=mock_database[""""
        ), patch(
            "]]src.scheduler.task_scheduler.FootballFeatureStore[",": return_value=mock_feature_store):": scheduler = TaskScheduler()": scheduler.db_manager = mock_database"
            scheduler.feature_store = mock_feature_store
            return scheduler
    @pytest.fixture
    def job_manager(self):
        "]""Create JobManager instance with mocked dependencies."""
        with patch("src.scheduler.job_manager.psutil[") as mock_psutil:": mock_psutil.cpu_percent.return_value = 50.0[": mock_psutil.virtual_memory.return_value = MagicMock(percent=60.0)": return JobManager()"
    @pytest.fixture
    def sample_tasks(self):
        "]]""Create sample tasks for batch testing."""
        tasks = []
        for i in range(5):
            task = ScheduledTask(
                task_id=f["batch_task_{i}"],": name=f["Batch Task {i}"],": func = lambda x f["result_{x}"],": args=["i[",": cron_expression="]0 8 * * *",  # Daily at 8 AM[": enabled=True,": timeout=300,": retry_count=3)"
            tasks.append(task)
        return tasks
    @pytest.fixture
    def failing_tasks(self):
        "]""Create sample tasks that will fail for testing error handling."""
        tasks = []
        for i in range(3):
            task = ScheduledTask(
                task_id=f["failing_task_{i}"],": name=f["Failing Task {i}"],": func = lambda x 1 / 0,  # This will raise ZeroDivisionError[": args=["]i[",": cron_expression="]0 8 * * *",": enabled=True,": timeout=300,": retry_count=2)"
            tasks.append(task)
        return tasks
    class TestBulkTaskRegistration:
        """Test cases for bulk task registration."""
        def test_register_multiple_tasks_success(self, task_scheduler, sample_tasks):
            """Test successful registration of multiple tasks."""
            # Register all tasks
            results = []
            for task in sample_tasks = result task_scheduler.register_task(task)
                results.append(result)
            # Verify all tasks were registered
            assert all(results)
            assert len(task_scheduler.tasks) ==len(sample_tasks)
            # Verify individual task registration
            for task in sample_tasks:
                assert task.task_id in task_scheduler.tasks
                assert task_scheduler.tasks[task.task_id] ==task
        def test_register_duplicate_tasks_handling(self, task_scheduler, sample_tasks):
            """Test handling of duplicate task registration."""
            # Register first task
            first_task = sample_tasks[0]
            result1 = task_scheduler.register_task(first_task)
            assert result1 is True
            # Try to register same task again
            result2 = task_scheduler.register_task(first_task)
            assert result2 is False  # Should return False for duplicate
            # Verify only one instance exists
            assert len(task_scheduler.tasks) ==1
            assert first_task.task_id in task_scheduler.tasks
        def test_register_mixed_valid_invalid_tasks(self, task_scheduler):
            """Test registration mix of valid and invalid tasks."""
            valid_task = ScheduledTask(
                task_id="valid_task[",": name="]Valid Task[",": func = lambda "]valid_result[",": cron_expression="]0 8 * * *",": enabled=True)": invalid_task = ScheduledTask(": task_id="",  # Invalid empty ID[": name="]Invalid Task[",": func = lambda "]invalid_result[",": cron_expression="]invalid_cron[",  # Invalid cron[": enabled=True)"""
            # Should handle both without crashing
            valid_result = task_scheduler.register_task(valid_task)
            invalid_result = task_scheduler.register_task(invalid_task)
            assert valid_result is True
            assert invalid_result is False  # Should fail for invalid task
            assert len(task_scheduler.tasks) ==1  # Only valid task registered
    class TestBatchTaskExecution:
        "]]""Test cases for batch task execution."""
        @pytest.mark.asyncio
        async def test_execute_all_tasks_success(self, task_scheduler, sample_tasks):
            """Test successful execution of all registered tasks."""
            # Register all tasks
            for task in sample_tasks:
                task_scheduler.register_task(task)
            # Mock the execution method
            executed_tasks = []
            def mock_execute(task_id):
                executed_tasks.append(task_id)
                return {"status[: "success"", "result[": f["]executed_{task_id}]}"]": task_scheduler.execute_task = mock_execute[""
            # Execute all tasks
            results = []
            for task in sample_tasks = result await task_scheduler.execute_task(task.task_id)
                results.append(result)
            # Verify all tasks were executed
            assert len(executed_tasks) ==len(sample_tasks)
            assert all(result["]status["] =="]success[" for result in results)""""
            assert set(executed_tasks) ==set(task.task_id for task in sample_tasks)
        @pytest.mark.asyncio
        async def test_execute_batch_with_failures(
            self, task_scheduler, sample_tasks, failing_tasks
        ):
            "]""Test batch execution with some failing tasks."""
            # Register both successful and failing tasks
            all_tasks = sample_tasks + failing_tasks
            for task in all_tasks:
                task_scheduler.register_task(task)
            # Mock execution that simulates failures
            executed_tasks = []
            failed_tasks = []
            def mock_execute(task_id):
                executed_tasks.append(task_id)
                if "failing_task[": in task_id:": failed_tasks.append(task_id)": raise Exception(f["]Task {task_id} failed["])": return {"]status[: "success"", "result[": f["]executed_{task_id}]}"]": task_scheduler.execute_task = mock_execute[""
            # Execute all tasks and collect results
            results = []
            exceptions = []
            for task in all_tasks = try result await task_scheduler.execute_task(task.task_id)
                    results.append(result)
                except Exception as e:
                   pass  # Auto-fixed empty except block
 exceptions.append(e)
            # Verify execution results
            assert len(executed_tasks) ==len(all_tasks)
            assert len(results) ==len(sample_tasks)  # Only successful tasks
            assert len(exceptions) ==len(
                failing_tasks
            )  # Failed tasks raised exceptions
            assert len(failed_tasks) ==len(failing_tasks)
        @pytest.mark.asyncio
        async def test_concurrent_task_execution(self, task_scheduler, sample_tasks):
            "]""Test concurrent execution of multiple tasks."""
            # Register tasks
            for task in sample_tasks:
                task_scheduler.register_task(task)
            # Mock execution with slight delay to simulate concurrent processing = execution_order []
            async def mock_execute(task_id):
                await asyncio.sleep(0.1)  # Simulate processing time
                execution_order.append(task_id)
                return {"status[: "success"", "result[": f["]executed_{task_id}]}"]": task_scheduler.execute_task = mock_execute[""
            # Execute tasks concurrently
            tasks = [task_scheduler.execute_task(task.task_id) for task in sample_tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Verify all tasks executed (order might vary due to concurrency)
            assert len(execution_order) ==len(sample_tasks)
            assert all(not isinstance(r, Exception) for r in results)  # No exceptions
    class TestQueueConsumption:
        "]""Test cases for task queue consumption."""
        @pytest.fixture
        def mock_task_queue(self):
            """Mock task queue."""
            return MagicMock()
        def test_queue_task_processing(self, job_manager, mock_task_queue):
            """Test processing tasks from a queue."""
            # Mock queue with tasks = mock_tasks [
                {"task_id[: "queue_task_1"", "data]},""""
                {"task_id[: "queue_task_2"", "data]},""""
                {"task_id[: "queue_task_3"", "data]}]": mock_task_queue.get.side_effect = mock_tasks + ["None["  # None to signal end[": processed_tasks = []": def mock_process_task(task_data):": processed_tasks.append(task_data)"
                return JobExecutionResult(
                    task_id=task_data["]]task_id["],": status="]success[",": result=f["]processed_{task_data['data']}"],": start_time=datetime.now(),": end_time=datetime.now(),": duration_ms=100)"
            # Process queue
            while True = task_data mock_task_queue.get()
                if task_data is None:
                    break
                result = mock_process_task(task_data)
                assert result.status =="success["""""
            # Verify all tasks processed
            assert len(processed_tasks) ==len(mock_tasks)
            assert set(t["]task_id["] for t in processed_tasks) ==set(" t["]task_id["] for t in mock_tasks:""""
            )
        def test_queue_empty_handling(self, job_manager, mock_task_queue):
            "]""Test handling of empty queue."""
            mock_task_queue.get.return_value = None  # Empty queue
            processed_count = 0
            def mock_process_task(task_data):
                nonlocal processed_count
                processed_count += 1
            # Process empty queue
            task_data = mock_task_queue.get()
            if task_data is not None:
                mock_process_task(task_data)
            # Verify no tasks processed
            assert processed_count ==0
        def test_queue_error_handling(self, job_manager, mock_task_queue):
            """Test error handling during queue processing."""
            # Mock queue with a failing task = failing_task {"task_id[: "failing_task"", "data]}": mock_task_queue.get.side_effect = ["failing_task[", None]": processed_tasks = []": errors = []": def mock_process_task(task_data):"
                if task_data["]task_id["] =="]failing_task[":": raise Exception("]Queue processing error[")": processed_tasks.append(task_data)"""
            # Process queue with error handling:
            while True = try task_data mock_task_queue.get()
                    if task_data is None:
                        break
                    mock_process_task(task_data)
                except Exception as e:
                    pass  # Auto-fixed empty except block
errors.append(e)
            # Verify error handled gracefully
            assert len(processed_tasks) ==0  # No successful processing
            assert len(errors) ==1  # One error captured
    class TestResourceManagement:
        "]""Test cases for resource management during batch operations."""
        @pytest.mark.asyncio
        async def test_memory_usage_monitoring(self, job_manager):
            """Test memory usage monitoring during batch execution."""
            with patch("src.scheduler.job_manager.psutil[") as mock_psutil:""""
                # Mock memory usage changes
                memory_values = [50.0, 60.0, 70.0, 65.0, 55.0]
                mock_psutil.virtual_memory.side_effect = [
                    MagicMock(percent = val) for val in memory_values
                ]
                memory_samples = []
                # Simulate batch operation with memory monitoring:
                for i in range(5):
                    memory_percent = job_manager.resource_monitor.get_memory_usage()
                    memory_samples.append(memory_percent)
                    await asyncio.sleep(0.01)  # Small delay
                # Verify memory tracking
                assert len(memory_samples) ==5
                assert memory_samples ==memory_values
                assert all(
                    0 <= sample <= 100 for sample in memory_samples:
                )  # Valid percentages
        @pytest.mark.asyncio
        async def test_cpu_usage_monitoring(self, job_manager):
            "]""Test CPU usage monitoring during batch execution."""
            with patch("src.scheduler.job_manager.psutil[") as mock_psutil:""""
                # Mock CPU usage changes
                cpu_values = [30.0, 45.0, 60.0, 40.0, 25.0]
                mock_psutil.cpu_percent.side_effect = cpu_values
                cpu_samples = []
                # Simulate batch operation with CPU monitoring:
                for i in range(5):
                    cpu_percent = job_manager.resource_monitor.get_cpu_usage()
                    cpu_samples.append(cpu_percent)
                    await asyncio.sleep(0.01)  # Small delay
                # Verify CPU tracking
                assert len(cpu_samples) ==5
                assert cpu_samples ==cpu_values
                assert all(
                    0 <= sample <= 100 for sample in cpu_samples:
                )  # Valid percentages
        @pytest.mark.asyncio
        async def test_resource_threshold_handling(self, job_manager):
            "]""Test handling of resource threshold violations."""
            with patch("src.scheduler.job_manager.psutil[") as mock_psutil:""""
                # Mock resource usage exceeding thresholds
                mock_psutil.virtual_memory.return_value = MagicMock(
                    percent=95.0
                )  # High memory
                mock_psutil.cpu_percent.return_value = 90.0  # High CPU
                # Check resource status
                memory_ok = job_manager.resource_monitor.check_memory_usage(
                    threshold=90.0
                )
                cpu_ok = job_manager.resource_monitor.check_cpu_usage(threshold=85.0)
                # Verify threshold detection
                assert not memory_ok  # Memory exceeds threshold
                assert not cpu_ok  # CPU exceeds threshold
    class TestBatchPerformance:
        "]""Test cases for batch execution performance."""
        @pytest.mark.asyncio
        async def test_execution_time_tracking(self, job_manager):
            """Test tracking of execution times for batch operations."""
            start_time = datetime.now()
            # Simulate work
            await asyncio.sleep(0.1)
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            # Create execution result
            result = JobExecutionResult(
                task_id="performance_test[",": status="]success[",": result="]test_completed[",": start_time=start_time,": end_time=end_time,": duration_ms=duration_ms)"
            # Verify timing accuracy
            assert result.duration_ms >= 80  # At least 80ms (allowing for overhead)
            assert result.duration_ms <= 200  # At most 200ms
            assert result.status =="]success["""""
        @pytest.mark.asyncio
        async def test_batch_throughput(self, task_scheduler, sample_tasks):
            "]""Test throughput of batch task execution."""
            # Register tasks
            for task in sample_tasks:
                task_scheduler.register_task(task)
            # Mock fast execution
            async def mock_execute(task_id):
                await asyncio.sleep(0.001)  # Very fast execution
                return {"status[: "success"", "result[": f["]executed_{task_id}]}"]": task_scheduler.execute_task = mock_execute[""
            # Measure batch execution time
            start_time = datetime.now()
            tasks = [task_scheduler.execute_task(task.task_id) for task in sample_tasks]
            results = await asyncio.gather(*tasks)
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            # Verify throughput
            assert len(results) ==len(sample_tasks)
            assert all(r["]status["] =="]success[" for r in results)""""
            assert total_duration < 1.0  # Should complete within 1 second
            # Calculate throughput (tasks per second)
            throughput = len(sample_tasks) / total_duration
            assert throughput > 1.0  # At least 1 task per second
    class TestCleanupAndRecovery:
        "]""Test cases for cleanup and recovery after batch operations."""
        @pytest.mark.asyncio
        async def test_task_cleanup_after_completion(
            self, task_scheduler, sample_tasks
        ):
            """Test cleanup of resources after task completion."""
            # Register and execute tasks
            for task in sample_tasks:
                task_scheduler.register_task(task)
            # Track cleanup calls
            cleanup_called = []
            def mock_cleanup(task_id):
                cleanup_called.append(task_id)
            # Mock execution with cleanup:
            async def mock_execute(task_id):
                try:
                    return {"status[: "success"", "result[": f["]executed_{task_id}]}"]": finally:": mock_cleanup(task_id)"
            task_scheduler.execute_task = mock_execute
            # Execute all tasks
            for task in sample_tasks:
                await task_scheduler.execute_task(task.task_id)
            # Verify cleanup for all tasks:
            assert len(cleanup_called) ==len(sample_tasks)
            assert set(cleanup_called) ==set(task.task_id for task in sample_tasks)
        @pytest.mark.asyncio
        async def test_state_recovery_after_failure(self, task_scheduler, sample_tasks):
            """Test state recovery after execution failures."""
            # Register tasks
            for task in sample_tasks:
                task_scheduler.register_task(task)
            # Track failed executions
            failed_executions = []
            def mock_execute(task_id):
                if task_id.endswith("3["):  # Simulate failure for task_3:": failed_executions.append(task_id)": raise Exception(f["]Execution failed for {task_id}"]):": return {"status[: "success"", "result[": f["]executed_{task_id}]}"]": task_scheduler.execute_task = mock_execute[""
            # Execute tasks with failure handling = successful_results []
            for task in sample_tasks = try result await task_scheduler.execute_task(task.task_id)
                    successful_results.append(result)
                except Exception:
                    pass  # Continue with other tasks:
            # Verify state consistency
            assert len(successful_results) ==len(sample_tasks) - 1  # One task failed
            assert len(failed_executions) ==1
            assert failed_executions[0].endswith("]3[")"]"""
            # Verify scheduler still functional
            remaining_tasks = len(task_scheduler.tasks)
            assert remaining_tasks ==len(sample_tasks)  # All tasks still registered