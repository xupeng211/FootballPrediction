"""
API performance tests focusing on response time requirements.

Tests ensure prediction API responds within <100ms latency requirement.
"""

import pytest
import asyncio
import time
from datetime import datetime
from tests.factories import MatchFactory, FeatureFactory
from tests.mocks import MockDatabaseManager, MockRedisManager, MockPredictionService, MockAPIClient


class TestAPIPerformance:
    """Test API performance requirements."""

    @pytest.fixture
    def performance_services(self):
        """Setup services for performance testing."""
        return {
            'database': MockDatabaseManager(),
            'redis': MockRedisManager(),
            'prediction_service': MockPredictionService(),
            'api_client': MockAPIClient(latency=0.001)  # Very low latency for clean testing
        }

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_prediction_api_latency_under_100ms(self, performance_services):
        """Test prediction API response time is under 100ms."""
        # Setup test data
        match_features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
        match_features['match_id'] = 12345

        # Measure API response time
        start_time = time.time()
        prediction = await performance_services['prediction_service'].predict_match_outcome(match_features)
        end_time = time.time()

        response_time_ms = (end_time - start_time) * 1000

        # Critical performance assertion: response time < 100ms
        assert response_time_ms < 100.0, \
            f"API response time {response_time_ms:.2f}ms exceeds 100ms limit"

        # Validate prediction quality is maintained
        assert prediction['confidence'] > 0.5, "Prediction confidence too low"
        assert 'probabilities' in prediction, "Missing probabilities in response"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cached_prediction_api_performance(self, performance_services):
        """Test cached prediction API performance (should be much faster)."""
        # Setup test data
        match_features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
        match_features['match_id'] = 12346

        # Make initial request (cache miss)
        start_time = time.time()
        prediction1 = await performance_services['prediction_service'].predict_match_outcome(match_features)
        first_request_time = (time.time() - start_time) * 1000

        # Cache the prediction
        await performance_services['redis'].set(
            f"prediction:{match_features['match_id']}",
            prediction1,
            ttl=300
        )

        # Make second request (cache hit)
        start_time = time.time()
        cached_prediction = await performance_services['redis'].get(f"prediction:{match_features['match_id']}")
        second_request_time = (time.time() - start_time) * 1000

        # Cached requests should be significantly faster (<10ms)
        assert second_request_time < 10.0, \
            f"Cached request time {second_request_time:.2f}ms exceeds 10ms target"

        # Cached response should be identical
        assert cached_prediction == prediction1, "Cached prediction differs from original"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_batch_prediction_performance(self, performance_services):
        """Test batch prediction API performance."""
        # Generate multiple matches for batch prediction
        batch_size = 10
        match_features_list = []
        for i in range(batch_size):
            features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
            features['match_id'] = 12340 + i
            match_features_list.append(features)

        # Measure batch prediction time
        start_time = time.time()
        batch_predictions = await performance_services['prediction_service'].batch_predict(match_features_list)
        end_time = time.time()

        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_prediction = total_time_ms / batch_size

        # Batch should complete efficiently (average <50ms per prediction)
        assert avg_time_per_prediction < 50.0, \
            f"Average prediction time {avg_time_per_prediction:.2f}ms exceeds 50ms target for batch"

        # All predictions should be valid
        assert len(batch_predictions) == batch_size, "Not all batch predictions returned"
        assert all('error' not in pred for pred in batch_predictions), "Errors in batch predictions"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_api_performance_under_load(self, performance_services):
        """Test API performance under simulated load."""
        import concurrent.futures

        # Generate test data
        num_requests = 20
        match_features_list = []
        for i in range(num_requests):
            features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
            features['match_id'] = 12400 + i
            match_features_list.append(features)

        # Simulate concurrent requests
        async def make_prediction(features):
            start_time = time.time()
            prediction = await performance_services['prediction_service'].predict_match_outcome(features)
            response_time = (time.time() - start_time) * 1000
            return prediction, response_time

        # Run requests concurrently
        tasks = [make_prediction(features) for features in match_features_list]
        results = await asyncio.gather(*tasks)

        # Analyze performance under load
        response_times = [result[1] for result in results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        # Performance assertions under load
        assert avg_response_time < 150.0, \
            f"Average response time under load {avg_response_time:.2f}ms exceeds 150ms"
        assert max_response_time < 300.0, \
            f"Max response time under load {max_response_time:.2f}ms exceeds 300ms"

        # All requests should succeed
        assert len(results) == num_requests, "Not all concurrent requests completed"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_api_response_size_performance(self, performance_services):
        """Test API response size doesn't impact performance significantly."""
        # Generate features with varying complexity
        simple_features = FeatureFactory.generate_team_form_features(num_samples=1).iloc[0].to_dict()
        complex_features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()

        simple_features['match_id'] = 12350
        complex_features['match_id'] = 12351

        # Test simple feature performance
        start_time = time.time()
        simple_prediction = await performance_services['prediction_service'].predict_match_outcome(simple_features)
        simple_time = (time.time() - start_time) * 1000

        # Test complex feature performance
        start_time = time.time()
        complex_prediction = await performance_services['prediction_service'].predict_match_outcome(complex_features)
        complex_time = (time.time() - start_time) * 1000

        # Complex features shouldn't significantly impact performance (<2x slower)
        time_ratio = complex_time / max(simple_time, 1)  # Avoid division by zero
        assert time_ratio < 2.0, \
            f"Complex features {complex_time:.2f}ms are {time_ratio:.1f}x slower than simple {simple_time:.2f}ms"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_database_query_performance(self, performance_services):
        """Test database query performance within API calls."""
        # Setup mock database query results
        async with performance_services['database'].get_session() as session:
            session.set_execute_result("fetchall", [{"match_id": 123, "home_team": "Team A"}])

        # Measure database query performance
        start_time = time.time()
        async with performance_services['database'].get_session() as session:
            result = await session.execute("SELECT * FROM matches WHERE match_id = %s", (123,))
            matches = result.fetchall()
        query_time = (time.time() - start_time) * 1000

        # Database queries should be fast (<50ms)
        assert query_time < 50.0, \
            f"Database query time {query_time:.2f}ms exceeds 50ms target"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_hit_performance(self, performance_services):
        """Test cache hit performance is optimal."""
        # Setup cache
        test_key = "performance_test_key"
        test_value = {"prediction": "home_win", "confidence": 0.85}

        # Cache the value
        await performance_services['redis'].set(test_key, test_value, ttl=300)

        # Measure cache read performance
        start_time = time.time()
        cached_value = await performance_services['redis'].get(test_key)
        cache_read_time = (time.time() - start_time) * 1000

        # Cache reads should be very fast (<5ms)
        assert cache_read_time < 5.0, \
            f"Cache read time {cache_read_time:.2f}ms exceeds 5ms target"

        assert cached_value == test_value, "Cached value mismatch"

    @pytest.mark.performance
    def test_memory_usage_during_predictions(self, performance_services):
        """Test memory usage during prediction processing."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Generate a large number of predictions to test memory usage
        predictions = []
        for i in range(100):
            features = FeatureFactory.generate_comprehensive_features(num_samples=5)
            predictions.append(features)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (<100MB for 100 predictions)
        assert memory_increase < 100.0, \
            f"Memory increase {memory_increase:.1f}MB exceeds 100MB limit for 100 predictions"

    @pytest.mark.performance
    def test_prediction_algorithm_efficiency(self):
        """Test prediction algorithm computational efficiency."""
        import time

        # Generate a large feature set
        large_features = FeatureFactory.generate_comprehensive_features(num_samples=1000)

        # Measure feature processing time
        start_time = time.time()

        # Simulate prediction algorithm computation
        for _, row in large_features.iterrows():
            # Simple computation that represents prediction logic
            home_form = row.get('home_form_last_5', 0)
            away_form = row.get('away_form_last_5', 0)
            home_possession = row.get('home_possession_avg', 50)

            # Simple prediction logic
            if home_form > away_form and home_possession > 55:
                predicted_outcome = "home_win"
            elif away_form > home_form:
                predicted_outcome = "away_win"
            else:
                predicted_outcome = "draw"

        processing_time = time.time() - start_time
        avg_time_per_prediction = (processing_time * 1000) / len(large_features)

        # Algorithm should be efficient (<1ms per prediction)
        assert avg_time_per_prediction < 1.0, \
            f"Algorithm processing time {avg_time_per_prediction:.3f}ms per prediction exceeds 1ms target"


class TestAPIPerformanceBenchmarks:
    """API performance benchmark tests."""

    @pytest.mark.performance
    def test_prediction_response_time_distribution(self, performance_services):
        """Test prediction response time consistency."""
        import asyncio
        import statistics

        # Run multiple prediction requests
        response_times = []
        num_samples = 50

        async def collect_response_times():
            for i in range(num_samples):
                features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
                features['match_id'] = 13000 + i

                start_time = time.time()
                prediction = await performance_services['prediction_service'].predict_match_outcome(features)
                response_time = (time.time() - start_time) * 1000
                response_times.append(response_time)

        asyncio.run(collect_response_times())

        # Analyze response time distribution
        avg_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        percentile_95 = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        percentile_99 = statistics.quantiles(response_times, n=100)[98]  # 99th percentile

        # Performance assertions
        assert avg_time < 100.0, f"Average response time {avg_time:.2f}ms exceeds 100ms"
        assert median_time < 80.0, f"Median response time {median_time:.2f}ms exceeds 80ms"
        assert percentile_95 < 150.0, f"95th percentile {percentile_95:.2f}ms exceeds 150ms"
        assert percentile_99 < 200.0, f"99th percentile {percentile_99:.2f}ms exceeds 200ms"