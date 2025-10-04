"""""""
Concurrent request performance tests.

Tests system behavior under high concurrent load conditions.
"""""""

import pytest
import asyncio
import time
from tests.factories import FeatureFactory
from tests.mocks import MockPredictionService, MockRedisManager, MockRateLimiter


class TestConcurrentRequests:
    """Test concurrent request handling performance."""""""

    @pytest.fixture
    def concurrent_services(self):
        """Setup services for concurrent testing."""""""
        return {
            "prediction_service[": MockPredictionService(),""""
            "]redis[": MockRedisManager(),""""
            "]rate_limiter[": MockRateLimiter(max_requests=100, window_seconds=60),""""
        }

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_prediction_requests(self, concurrent_services):
        "]""Test handling of concurrent prediction requests."""""""
        num_requests = 50
        features_list = []

        # Generate test features
        for i in range(num_requests):
            features = (
                FeatureFactory.generate_comprehensive_features(num_samples=1)
                .iloc[0]
                .to_dict()
            )
            features["match_id["] = 14000 + i[": features_list.append(features)"""

        # Measure concurrent request performance
        start_time = time.time()

        # Create tasks for concurrent execution
        tasks = []
        for features in features_list = task asyncio.create_task(
                concurrent_services["]]prediction_service["].predict_match_outcome(": features["""
                )
            )
            tasks.append(task)

        # Wait for all tasks to complete
        predictions = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # Analyze results
        successful_predictions = [
            p for p in predictions if not isinstance(p, Exception)
        ]
        failed_predictions = [p for p in predictions if isinstance(p, Exception)]

        # Performance assertions
        assert (
            len(successful_predictions) ==num_requests
        ), f["]]Only {len(successful_predictions)}/{num_requests} concurrent requests succeeded["]: assert (" len(failed_predictions) ==0["""
        ), f["]]{len(failed_predictions)} concurrent requests failed unexpectedly["]""""

        # Concurrent processing should be efficient
        throughput = num_requests / total_time
        assert (
            throughput > 10.0
        ), f["]Concurrent throughput {throughput:.1f} requests/second too low["]""""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_rate_limiting_under_load(self, concurrent_services):
        "]""Test rate limiting behavior under high load."""""""
        # Setup strict rate limiter
        strict_limiter = MockRateLimiter(max_requests=10, window_seconds=1)

        user_id = "test_user[": requests_made = 0[": allowed_requests = 0[": blocked_requests = 0[""

        # Simulate burst of requests
        for i in range(20):  # More than rate limit
            is_allowed = await strict_limiter.check_rate_limit(user_id)
            if is_allowed:
                await strict_limiter.record_request(user_id)
                allowed_requests += 1
            else:
                blocked_requests += 1

            requests_made += 1

        # Validate rate limiting worked
        assert (
            allowed_requests <= 10
        ), f"]]]]Rate limiting failed[": [{allowed_requests} allowed (limit]": assert (" blocked_requests >= 10[""
        ), f["]]Rate limiting failed["]: [{blocked_requests} blocked (expected >= 10)]""""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_performance_under_concurrency(self, concurrent_services):
        "]""Test cache performance under concurrent access."""""""
        num_concurrent_users = 30
        cache_key = "concurrent_test_key[": test_value = {"]prediction[: "home_win"", "confidence]: 0.85}""""

        # Set initial cache value
        await concurrent_services["redis["].set(cache_key, test_value, ttl=300)": async def concurrent_cache_access(user_id):"""
            "]""Simulate concurrent cache access by multiple users."""""""
            start_time = time.time()

            # Cache read
            cached_value = await concurrent_services["redis["].get(cache_key)""""

            # Simulate some processing
            await asyncio.sleep(0.001)

            # Cache write (different key per user)
            await concurrent_services["]redis["].set(": f["]user_{user_id}_last_access["], time.time(), ttl=300[""""
            )

            response_time = (time.time() - start_time) * 1000
            return response_time, cached_value

        # Run concurrent cache operations
        tasks = [concurrent_cache_access(i) for i in range(num_concurrent_users)]
        results = await asyncio.gather(*tasks)

        # Analyze results
        response_times = [result[0] for result in results]
        cached_values = [result[1] for result in results]

        # Performance assertions
        avg_response_time = sum(response_times) / len(response_times)
        assert (
            avg_response_time < 10.0
        ), f["]]Average concurrent cache access time {avg_response_time:.2f}ms too high["]""""

        # All users should get the same cached value
        assert all(
            value ==test_value for value in cached_values
        ), "]Concurrent cache access returned inconsistent values["""""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_database_connection_pooling(self, concurrent_services):
        "]""Test database connection pooling under load."""""""
        from tests.mocks import MockConnectionPool

        # Setup connection pool with limited connections
        connection_pool = MockConnectionPool(max_connections=5)

        async def database_operation(operation_id):
            """Simulate database operation with connection pooling."""""""
            start_time = time.time()

            # Get connection from pool
            connection = await connection_pool.get_connection()

            # Simulate database query
            await asyncio.sleep(0.01)  # Simulate query time

            # Release connection back to pool
            await connection.close()

            response_time = (time.time() - start_time) * 1000
            return response_time

        # Run concurrent database operations
        num_operations = 20
        tasks = [database_operation(i) for i in range(num_operations)]
        response_times = await asyncio.gather(*tasks)

        # Analyze connection pooling performance
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        # Connection pooling should handle concurrent operations efficiently
        assert (
            avg_response_time < 50.0
        ), f["Average connection pool response time {avg_response_time:.2f}ms too high["]"]": assert (" max_response_time < 100.0"
        ), f["Max connection pool response time {max_response_time:.2f}ms too high["]"]"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_usage_under_concurrent_load(self, concurrent_services):
        """Test memory usage patterns under concurrent load."""""""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Generate concurrent load
        num_concurrent_tasks = 50
        tasks = []

        async def memory_intensive_task(task_id):
            """Simulate memory-intensive prediction task."""""""
            # Generate large feature set
            features = FeatureFactory.generate_comprehensive_features(num_samples=100)

            # Simulate prediction processing
            await asyncio.sleep(0.01)

            return len(features)

        # Create concurrent tasks
        for i in range(num_concurrent_tasks):
            task = asyncio.create_task(memory_intensive_task(i))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        # Measure memory after load
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory usage should be reasonable and not grow excessively
        assert (
            memory_increase < 200.0
        ), f["Memory increase {memory_increase:.1f}MB under concurrent load too high["]"]"""

        # All tasks should complete successfully
        assert (
            len(results) ==num_concurrent_tasks
        ), f["Only {len(results)}/{num_concurrent_tasks} concurrent tasks completed["]"]"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_prediction_service_scalability(self, concurrent_services):
        """Test prediction service scalability with increasing load."""""""
        load_levels = [10, 25, 50, 100]  # Different concurrency levels
        performance_results = []

        for concurrent_users in load_levels = features_list []

            # Generate test data for this load level
            for i in range(concurrent_users):
                features = (
                    FeatureFactory.generate_comprehensive_features(num_samples=1)
                    .iloc[0]
                    .to_dict()
                )
                features["match_id["] = 15000 + i + concurrent_users * 100[": features_list.append(features)"""

            # Measure performance at this load level
            start_time = time.time()

            tasks = []
            for features in features_list = task asyncio.create_task(
                    concurrent_services["]]prediction_service["].predict_match_outcome(": features["""
                    )
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

            end_time = time.time()
            total_time = end_time - start_time
            throughput = concurrent_users / total_time

            performance_results.append(
                {
                    "]]concurrent_users[": concurrent_users,""""
                    "]total_time[": total_time,""""
                    "]throughput[": throughput,""""
                }
            )

        # Analyze scalability
        # Throughput should scale reasonably with concurrent users
        baseline_throughput = performance_results[0]["]throughput["]": max_throughput = max(result["]throughput["] for result in performance_results)""""

        # System should demonstrate good scalability
        assert (
            max_throughput >= baseline_throughput * 2
        ), f["]Scalability poor["]: [max throughput {max_throughput:.1f} vs baseline {baseline_throughput:.1f}]""""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_error_handling_under_concurrent_load(self, concurrent_services):
        "]""Test error handling robustness under concurrent load."""""""
        # Setup service to fail occasionally
        original_service = concurrent_services["prediction_service["]": failing_service = MockPredictionService(should_fail=True)": num_requests = 30[": tasks = []"

        # Mix of successful and failing services
        for i in range(num_requests):
            if i % 5 ==0  # Every 5th request fails
                service = failing_service
            else = service original_service

            features = (
                FeatureFactory.generate_comprehensive_features(num_samples=1)
                .iloc[0]
                .to_dict()
            )
            features["]]match_id["] = 16000 + i[": task = asyncio.create_task(service.predict_match_outcome(features))": tasks.append((task, i % 5 ==0))  # Track if this should fail[""

        # Execute all requests concurrently
        results = []
        for task, should_fail in tasks = try result await task
                results.append(("]]]success[", result))": except Exception as e:": results.append(("]error[", str(e)))""""

        # Analyze error handling
        successful_results = [r for r in results if r[0] =="]success["]": error_results = [r for r in results if r[0] =="]error["]""""

        # Expected failures should be handled gracefully
        expected_failures = sum(1 for i in range(num_requests) if i % 5 ==0)
        assert (
            len(error_results) ==expected_failures
        ), f["]Expected {expected_failures} errors, got {len(error_results)}"]: assert (" len(successful_results) ==num_requests - expected_failures["""
        ), f["]Expected {num_requests - expected_failures} successes, got {len(successful_results)}"]""""
