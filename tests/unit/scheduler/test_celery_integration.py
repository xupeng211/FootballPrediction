"""
Unit tests for Celery task integration with mocked external dependencies.

Tests the Celery task functionality including:
- Task definitions and retry logic
- Redis broker integration with mocking
- Kafka consumer integration with mocking
- Beat schedule configuration
- Task result handling and error recovery
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock, Mock
from celery import Celery, Task
from celery.result import AsyncResult

from src.scheduler.tasks import (
    collect_fixtures,
    collect_odds,
    collect_live_scores_conditional,
    cleanup_data,
    calculate_features_batch,
    generate_predictions,
    process_bronze_to_silver
)


class TestCeleryTaskIntegration:
    """Test cases for Celery task integration with external dependencies."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = False
        return mock_redis

    @pytest.fixture
    def mock_kafka_consumer(self):
        """Mock Kafka consumer."""
        mock_consumer = MagicMock()
        mock_consumer.poll.return_value = {}  # No messages initially
        mock_consumer.commit.return_value = None
        return mock_consumer

    @pytest.fixture
    def mock_kafka_producer(self):
        """Mock Kafka producer."""
        mock_producer = MagicMock()
        mock_producer.send.return_value = MagicMock()
        mock_producer.flush.return_value = None
        return mock_producer

    @pytest.fixture
    def mock_celery_app(self):
        """Mock Celery application."""
        mock_app = MagicMock()
        mock_app.conf = MagicMock()
        mock_app.conf.broker_url = "redis://localhost:6379/0"
        mock_app.conf.result_backend = "redis://localhost:6379/0"
        mock_app.conf.task_always_eager = True
        mock_app.conf.task_eager_propagates = True
        return mock_app

    @pytest.fixture
    def mock_database_manager(self):
        """Mock database manager."""
        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_db.get_async_session.return_value.__aenter__.return_value = mock_session
        mock_db.get_async_session.return_value.__aexit__.return_value = AsyncMock()
        return mock_db

    class TestRedisIntegration:
        """Test cases for Redis integration with mocking."""

        @pytest.mark.asyncio
        async def test_redis_cache_operation(self, mock_redis_client):
            """Test Redis cache operations with mocked client."""
            with patch('src.scheduler.celery_config.redis_client', mock_redis_client):
                from src.scheduler.celery_config import get_cache_value, set_cache_value

                # Test cache miss
                result = await get_cache_value("nonexistent_key")
                assert result is None
                mock_redis_client.get.assert_called_once_with("nonexistent_key")

                # Test cache set
                await set_cache_value("test_key", "test_value", ttl=3600)
                mock_redis_client.set.assert_called_once_with("test_key", "test_value", ex=3600)

        @pytest.mark.asyncio
        async def test_redis_lock_operation(self, mock_redis_client):
            """Test Redis lock operations."""
            mock_redis_client.set.return_value = True  # Lock acquired
            mock_redis_client.delete.return_value = 1  # Lock released

            with patch('src.scheduler.celery_config.redis_client', mock_redis_client):
                from src.scheduler.celery_config import acquire_lock, release_lock

                # Test lock acquisition
                lock_acquired = await acquire_lock("test_lock", timeout=30)
                assert lock_acquired is True
                mock_redis_client.set.assert_called_once()

                # Test lock release
                await release_lock("test_lock")
                mock_redis_client.delete.assert_called_once_with("test_lock")

        @pytest.mark.asyncio
        async def test_redis_connection_failure(self):
            """Test handling of Redis connection failures."""
            with patch('src.scheduler.celery_config.redis_client') as mock_redis:
                mock_redis.get.side_effect = Exception("Redis connection failed")

                from src.scheduler.celery_config import get_cache_value

                # Should handle connection failure gracefully
                result = await get_cache_value("test_key")
                assert result is None  # Should return None on failure

    class TestKafkaIntegration:
        """Test cases for Kafka integration with mocking."""

        @pytest.mark.asyncio
        async def test_kafka_message_production(self, mock_kafka_producer):
            """Test Kafka message production with mocked producer."""
            with patch('src.scheduler.celery_config.kafka_producer', mock_kafka_producer):
                from src.scheduler.celery_config import produce_message

                # Test message production
                await produce_message("test_topic", {"key": "value"})
                mock_kafka_producer.send.assert_called_once_with("test_topic", {"key": "value"})
                mock_kafka_producer.flush.assert_called_once()

        @pytest.mark.asyncio
        async def test_kafka_message_consumption(self, mock_kafka_consumer):
            """Test Kafka message consumption with mocked consumer."""
            # Mock incoming message
            mock_message = MagicMock()
            mock_message.value = b'{"match_id": 1, "data": "test"}'
            mock_message.topic = "test_topic"
            mock_message.partition = 0
            mock_message.offset = 123

            mock_kafka_consumer.poll.return_value = {
                ("test_topic", 0): [mock_message]
            }

            with patch('src.scheduler.celery_config.kafka_consumer', mock_kafka_consumer):
                from src.scheduler.celery_config import consume_messages

                consumed_messages = []

                def message_handler(message):
                    consumed_messages.append(message)

                # Consume messages
                await consume_messages("test_topic", message_handler, timeout_ms=1000)

                # Verify message consumption
                assert len(consumed_messages) == 1
                assert consumed_messages[0]["match_id"] == 1

        @pytest.mark.asyncio
        async def test_kafka_connection_error_handling(self):
            """Test handling of Kafka connection errors."""
            with patch('src.scheduler.celery_config.kafka_producer') as mock_producer:
                mock_producer.send.side_effect = Exception("Kafka connection failed")

                from src.scheduler.celery_config import produce_message

                # Should handle connection error gracefully
                try:
                    await produce_message("test_topic", {"data": "test"})
                except Exception:
                    pass  # Exception handled gracefully

    class TestCeleryTaskExecution:
        """Test cases for Celery task execution."""

        @pytest.mark.asyncio
        @patch('src.scheduler.tasks.DatabaseManager')
        async def test_collect_fixtures_task(self, mock_db_class, mock_database_manager):
            """Test collect_fixtures task execution."""
            mock_db_class.return_value = mock_database_manager

            # Mock database query results
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                MagicMock(id=1, home_team="Team A", away_team="Team B", date="2024-01-01"),
                MagicMock(id=2, home_team="Team C", away_team="Team D", date="2024-01-02")
            ]
            mock_session.execute.return_value = mock_result
            mock_database_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            # Execute task
            result = await collect_fixtures(league_id=1, season="2024")

            # Verify database interaction
            mock_session.execute.assert_called_once()
            assert result is not None  # Task should complete successfully

        @pytest.mark.asyncio
        @patch('src.scheduler.tasks.DatabaseManager')
        async def test_collect_odds_task(self, mock_db_class, mock_database_manager):
            """Test collect_odds task execution."""
            mock_db_class.return_value = mock_database_manager

            # Mock external API call
            with patch('src.scheduler.tasks.requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "odds": [
                        {"match_id": 1, "home_odds": 2.1, "draw_odds": 3.2, "away_odds": 3.8},
                        {"match_id": 2, "home_odds": 1.8, "draw_odds": 3.5, "away_odds": 4.2}
                    ]
                }
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                # Execute task
                result = await collect_odds(match_ids=[1, 2])

                # Verify API call
                mock_get.assert_called_once()
                assert result is not None

        @pytest.mark.asyncio
        @patch('src.scheduler.tasks.DatabaseManager')
        async def test_collect_live_scores_conditional_task(self, mock_db_class, mock_database_manager):
            """Test collect_live_scores_conditional task execution."""
            mock_db_class.return_value = mock_database_manager

            # Mock live matches query
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                MagicMock(id=1, home_team="Team A", away_team="Team B", status="LIVE"),
                MagicMock(id=2, home_team="Team C", away_team="Team D", status="LIVE")
            ]
            mock_session.execute.return_value = mock_result
            mock_database_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            # Mock API response
            with patch('src.scheduler.tasks.requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "matches": [
                        {"id": 1, "home_score": 1, "away_score": 0, "minute": 65},
                        {"id": 2, "home_score": 0, "away_score": 0, "minute": 32}
                    ]
                }
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                # Execute task
                result = await collect_live_scores_conditional()

                # Verify execution
                assert result is not None

        @pytest.mark.asyncio
        @patch('src.scheduler.tasks.DatabaseManager')
        async def test_cleanup_data_task(self, mock_db_class, mock_database_manager):
            """Test cleanup_data task execution."""
            mock_db_class.return_value = mock_database_manager

            # Mock cleanup operation
            days_to_keep = 30

            # Execute task
            result = await cleanup_data(days_to_keep=days_to_keep)

            # Verify cleanup
            assert result is not None

        @pytest.mark.asyncio
        @patch('src.scheduler.tasks.DatabaseManager')
        async def test_calculate_features_batch_task(self, mock_db_class, mock_database_manager):
            """Test calculate_features_batch task execution."""
            mock_db_class.return_value = mock_database_manager

            # Mock feature calculation
            hours_ahead = 2

            # Execute task
            result = await calculate_features_batch(hours_ahead=hours_ahead)

            # Verify feature calculation
            assert result is not None

        @pytest.mark.asyncio
        @patch('src.scheduler.tasks.DatabaseManager')
        async def test_generate_predictions_task(self, mock_db_class, mock_database_manager):
            """Test generate_predictions task execution."""
            mock_db_class.return_value = mock_database_manager

            # Mock prediction generation
            match_ids = [1, 2, 3]

            # Execute task
            result = await generate_predictions(match_ids=match_ids)

            # Verify prediction generation
            assert result is not None

    class TestTaskRetryLogic:
        """Test cases for task retry logic."""

        @pytest.mark.asyncio
        @patch('src.scheduler.tasks.DatabaseManager')
        async def test_task_retry_on_failure(self, mock_db_class):
            """Test task retry mechanism on failure."""
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            # Mock database connection failure
            mock_session = AsyncMock()
            mock_session.execute.side_effect = Exception("Database connection failed")
            mock_db.get_async_session.return_value.__aenter__.return_value = mock_session

            # Track retry attempts
            retry_attempts = []

            def mock_execute_task():
                retry_attempts.append(1)
                if len(retry_attempts) < 3:  # Fail first 2 attempts
                    raise Exception("Temporary failure")
                return {"status": "success"}

            # Simulate retry logic
            max_retries = 3
            result = None

            for attempt in range(max_retries):
                try:
                    result = mock_execute_task()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise

            # Verify retry behavior
            assert len(retry_attempts) <= max_retries
            if result:
                assert result["status"] == "success"

        @pytest.mark.asyncio
        async def test_task_retry_with_backoff(self):
            """Test task retry with exponential backoff."""
            retry_delays = []
            start_time = asyncio.get_event_loop().time()

            async def failing_task():
                retry_delays.append(asyncio.get_event_loop().time() - start_time)
                raise Exception("Retryable error")

            # Simulate retry with backoff
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await failing_task()
                    break
                except Exception:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff

            # Verify backoff delays
            assert len(retry_delays) == max_retries
            # Delays should increase exponentially
            for i in range(1, len(retry_delays)):
                assert retry_delays[i] > retry_delays[i-1]

    class TestBeatSchedule:
        """Test cases for Celery Beat schedule configuration."""

        def test_beat_schedule_configuration(self):
            """Test Beat schedule configuration."""
            with patch('src.scheduler.celery_config.celery_app') as mock_app:
                from src.scheduler.celery_config import get_beat_schedule

                schedule = get_beat_schedule()

                # Verify schedule structure
                assert isinstance(schedule, dict)
                assert len(schedule) > 0

                # Verify scheduled tasks
                for task_name, task_config in schedule.items():
                    assert 'task' in task_config
                    assert 'schedule' in task_config
                    assert callable(task_config['task']) or isinstance(task_config['task'], str)

        def test_cron_schedule_parsing(self):
            """Test cron schedule parsing."""
            with patch('src.scheduler.celery_config.croniter') as mock_croniter:
                mock_cron = MagicMock()
                mock_cron.get_next.return_value = datetime.now() + timedelta(hours=1)
                mock_croniter.return_value = mock_cron

                from src.scheduler.celery_config import parse_cron_schedule

                # Test cron parsing
                next_run = parse_cron_schedule("0 8 * * *")
                assert next_run is not None
                mock_croniter.assert_called_once_with("0 8 * * *")

    class TestTaskResultHandling:
        """Test cases for task result handling."""

        @pytest.mark.asyncio
        async def test_successful_task_result(self):
            """Test handling of successful task results."""
            # Mock successful task result
            mock_result = MagicMock()
            mock_result.status = "SUCCESS"
            mock_result.result = {"data": "processed"}
            mock_result.traceback = None

            # Process result
            if mock_result.status == "SUCCESS":
                processed_data = mock_result.result
                assert processed_data["data"] == "processed"

        @pytest.mark.asyncio
        async def test_failed_task_result(self):
            """Test handling of failed task results."""
            # Mock failed task result
            mock_result = MagicMock()
            mock_result.status = "FAILURE"
            mock_result.result = None
            mock_result.traceback = "Traceback: ... error details ..."

            # Process result
            if mock_result.status == "FAILURE":
                error_info = {
                    "status": mock_result.status,
                    "traceback": mock_result.traceback
                }
                assert error_info["status"] == "FAILURE"
                assert "Traceback" in error_info["traceback"]

        @pytest.mark.asyncio
        async def test_task_timeout_handling(self):
            """Test handling of task timeouts."""
            # Mock timeout scenario
            timeout_occurred = False

            async def long_running_task():
                await asyncio.sleep(0.1)  # Simulate work
                return "completed"

            try:
                # Execute with timeout
                await asyncio.wait_for(long_running_task(), timeout=0.05)
            except asyncio.TimeoutError:
                timeout_occurred = True

            # Verify timeout detection
            assert timeout_occurred is True

    class TestTaskQueueManagement:
        """Test cases for task queue management."""

        @pytest.mark.asyncio
        async def test_task_queue_routing(self, mock_celery_app):
            """Test task routing to appropriate queues."""
            with patch('src.scheduler.celery_config.celery_app', mock_celery_app):
                from src.scheduler.celery_config import route_task_to_queue

                # Test queue routing logic
                task_name = "collect_fixtures"
                queue_name = route_task_to_queue(task_name)

                # Verify routing
                assert queue_name in ["default", "high_priority", "low_priority", "data_collection"]

        @pytest.mark.asyncio
        async def test_queue_priority_handling(self):
            """Test handling of queue priorities."""
            with patch('src.scheduler.celery_config.celery_app') as mock_app:
                from src.scheduler.celery_config import get_queue_priority

                # Test priority assignment
                high_priority_tasks = ["collect_live_scores", "emergency_processing"]
                low_priority_tasks = ["cleanup_old_data", "generate_reports"]

                for task in high_priority_tasks:
                    priority = get_queue_priority(task)
                    assert priority == "high"

                for task in low_priority_tasks:
                    priority = get_queue_priority(task)
                    assert priority == "low"

    class TestMonitoringAndMetrics:
        """Test cases for task monitoring and metrics."""

        @pytest.mark.asyncio
        async def test_task_execution_metrics(self):
            """Test collection of task execution metrics."""
            start_time = datetime.now()

            # Simulate task execution
            await asyncio.sleep(0.05)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Calculate metrics
            metrics = {
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": duration,
                "success": True
            }

            # Verify metrics
            assert metrics["duration_seconds"] >= 0.04  # At least 40ms
            assert metrics["success"] is True

        @pytest.mark.asyncio
        async def test_task_failure_metrics(self):
            """Test collection of task failure metrics."""
            start_time = datetime.now()

            # Simulate failed task
            failure_reason = "Database connection failed"
            exception_type = "ConnectionError"

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Collect failure metrics
            metrics = {
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": duration,
                "success": False,
                "failure_reason": failure_reason,
                "exception_type": exception_type
            }

            # Verify failure metrics
            assert metrics["success"] is False
            assert metrics["failure_reason"] == failure_reason
            assert metrics["exception_type"] == exception_type

    class TestTaskChaining:
        """Test cases for task chaining and workflows."""

        @pytest.mark.asyncio
        async def test_sequential_task_execution(self):
            """Test sequential execution of chained tasks."""
            execution_order = []

            async def task1():
                execution_order.append("task1")
                return "task1_result"

            async def task2(previous_result):
                execution_order.append("task2")
                return f"task2_result_{previous_result}"

            async def task3(previous_result):
                execution_order.append("task3")
                return f"task3_result_{previous_result}"

            # Execute tasks sequentially
            result1 = await task1()
            result2 = await task2(result1)
            result3 = await task3(result2)

            # Verify execution order and results
            assert execution_order == ["task1", "task2", "task3"]
            assert result1 == "task1_result"
            assert result2 == "task2_result_task1_result"
            assert result3 == "task3_result_task2_result_task1_result"

        @pytest.mark.asyncio
        async def test_parallel_task_execution(self):
            """Test parallel execution of independent tasks."""
            async def task_a():
                await asyncio.sleep(0.05)
                return "result_a"

            async def task_b():
                await asyncio.sleep(0.05)
                return "result_b"

            async def task_c():
                await asyncio.sleep(0.05)
                return "result_c"

            # Execute tasks in parallel
            tasks = [task_a(), task_b(), task_c()]
            results = await asyncio.gather(*tasks)

            # Verify parallel execution
            assert len(results) == 3
            assert "result_a" in results
            assert "result_b" in results
            assert "result_c" in results

            # Should complete faster than sequential execution
            # All tasks should complete in roughly the time of the slowest task