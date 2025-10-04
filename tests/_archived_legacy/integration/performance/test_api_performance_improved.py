"""""""
Improved API performance tests with high-quality assertions.

Demonstrates assertion quality improvements with detailed error messages,
structured validation, and comprehensive performance analysis.
"""""""

import pytest
import asyncio
import time
import statistics
from datetime import datetime
from tests.factories import FeatureFactory
from tests.mocks import (
    MockDatabaseManager,
    MockRedisManager,
    MockPredictionService,
    MockAPIClient,
)


def assert_valid_prediction_response(response_data):
    """Validate prediction response data structure and content."""""""
    # Basic structure validation
    assert isinstance(
        response_data, dict
    ), f["Prediction response should be dict, got {type(response_data)}"]""""

    # Required fields validation
    required_fields = [
        "match_id[",""""
        "]predicted_outcome[",""""
        "]probabilities[",""""
        "]confidence[",""""
        "]model_version[",""""
    ]
    missing_fields = [field for field in required_fields if field not in response_data]
    assert (
        not missing_fields
    ), f["]Missing required fields in prediction response["]: [{missing_fields}]""""

    # Data type validation
    assert isinstance(
        response_data["]match_id["], int[""""
    ), f["]]match_id should be int, got {type(response_data['match_id'])}"]: assert isinstance(" response_data["confidence["], (int, float)""""
    ), f["]confidence should be numeric, got {type(response_data['confidence'])}"]: assert isinstance(" response_data["probabilities["], dict[""""
    ), f["]]probabilities should be dict, got {type(response_data['probabilities'])}"]""""

    # Value range validation
    assert (
        0 <= response_data["confidence["] <= 1[""""
    ), f["]]confidence should be between 0 and 1, got {response_data['confidence']}"]""""

    # Probabilities validation
    probabilities = response_data["probabilities["]": assert_probabilities_valid(probabilities)"""

    # Predicted outcome validation
    valid_outcomes = ["]home_win[", "]draw[", "]away_win["]": assert (" response_data["]predicted_outcome["] in valid_outcomes[""""
    ), f["]]predicted_outcome should be one of {valid_outcomes}, got {response_data['predicted_outcome']}"]""""

    # Model version validation
    assert isinstance(
        response_data["model_version["], str[""""
    ), f["]]model_version should be string, got {type(response_data['model_version'])}"]: assert response_data["model_version["], "]model_version should not be empty[" def assert_probabilities_valid("
    """"
    "]""Validate probability distribution."""""""
    assert isinstance(
        probabilities, dict
    ), f["Probabilities should be dict, got {type(probabilities)}"]""""

    # Required outcomes
    required_outcomes = ["home_win[", "]draw[", "]away_win["]": missing_outcomes = [": outcome for outcome in required_outcomes if outcome not in probabilities[""
    ]
    assert (
        not missing_outcomes
    ), f["]]Missing probabilities for outcomes["]: [{missing_outcomes}]""""

    # Probability values validation
    for outcome, prob in probabilities.items():
        assert isinstance(
            prob, (int, float)
        ), f["]Probability for {outcome} should be numeric, got {type(prob)}"]: assert (""""
            0 <= prob <= 1
        ), f["Probability for {outcome} should be between 0 and 1, got {prob}"]""""

    # Probability sum validation
    total_prob = sum(probabilities.values())
    assert (
        abs(total_prob - 1.0) < 1e-6
    ), f["Probabilities sum to {total_prob["]: [{abs(total_prob - 1.0):.6f})]"]": def assert_performance_requirements("
    """"
    "]""Validate performance requirements with detailed error reporting."""""""
    critical_threshold = 100.0  # 100ms critical limit
    warning_threshold = 50.0  # 50ms warning threshold

    error_msg = (
        f["{operation_name} response time {response_time_ms:.2f}ms exceeds "]": f["critical threshold of {critical_threshold}ms["]"]"""
    )

    assert response_time_ms < critical_threshold, error_msg

    # Performance analysis
    if response_time_ms >= warning_threshold:
        pytest.warns(
            UserWarning,
            match = f["{operation_name} response time {response_time_ms.2f}ms "]": f["exceeds warning threshold of {warning_threshold}ms["],"]"""
        )


def assert_performance_consistency(
    """"
    "]""Validate performance consistency across multiple measurements."""""""
    if not response_times:
        pytest.fail("No response times provided for consistency analysis[")""""

    # Basic statistics
    avg_time = statistics.mean(response_times)
    median_time = statistics.median(response_times)
    min_time = min(response_times)
    max_time = max(response_times)
    std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0

    # Consistency validation
    consistency_threshold = avg_time * 0.5  # 50% variation threshold
    max_deviation = max(abs(time - avg_time) for time in response_times)

    assert max_deviation <= consistency_threshold, (
        f["]{operation_name} performance inconsistent. Max deviation {max_deviation:.2f}ms "]: f["exceeds threshold {consistency_threshold:.2f}ms. "]": f["Stats["]: [avg = {avg_time:.2f}ms, min={min_time:.2f}ms, max={max_time.2f}ms, ]"]": f["std = {std_dev.2f}ms["]"]"""
    )

    # Performance tier assessment
    performance_tier = (
        "excellent[": if avg_time < 50 else "]good[": if avg_time < 100 else "]acceptable["""""
    )
    return {
        "]avg_time[": avg_time,""""
        "]median_time[": median_time,""""
        "]min_time[": min_time,""""
        "]max_time[": max_time,""""
        "]std_dev[": std_dev,""""
        "]performance_tier[": performance_tier,""""
    }


class TestAPIPerformanceWithImprovedAssertions:
    "]""Test API performance with high-quality assertions."""""""

    @pytest.fixture
    def performance_services(self):
        """Setup services for performance testing."""""""
        return {
            "database[": MockDatabaseManager(),""""
            "]redis[": MockRedisManager(),""""
            "]prediction_service[": MockPredictionService(),""""
            "]api_client[": MockAPIClient(latency=0.001),""""
        }

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_prediction_api_latency_under_100ms(self, performance_services):
        "]""Test prediction API response time meets performance requirements."""""""
        # Setup test data with validation
        match_features = (
            FeatureFactory.generate_comprehensive_features(num_samples=1)
            .iloc[0]
            .to_dict()
        )
        assert isinstance(
            match_features, dict
        ), "Generated features should be a dictionary[": assert match_features, "]Generated features should not be empty[" match_features["]match_id["] = 12345[""""

        # Measure API response time
        start_time = time.time()
        prediction = await performance_services[
            "]]prediction_service["""""
        ].predict_match_outcome(match_features)
        end_time = time.time()

        # Validate measurement
        assert end_time > start_time, "]End time should be after start time[" response_time_ms = (end_time - start_time) * 1000[""""

        # Performance requirement validation
        assert_performance_requirements(response_time_ms, "]]Prediction API[")""""

        # Validate prediction quality is maintained despite performance focus
        assert_valid_prediction_response(prediction)

        # Additional performance analysis
        assert (
            response_time_ms > 0
        ), f["]Response time should be positive, got {response_time_ms}ms["]""""

        # Log performance metrics for analysis
        {
            "]response_time_ms[": round(response_time_ms, 2),""""
            "]match_id[": prediction["]match_id["],""""
            "]confidence[": prediction["]confidence["],""""
            "]model_version[": prediction["]model_version["],""""
            "]timestamp[": datetime.now().isoformat(),""""
        }

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cached_prediction_performance_superiority(
        self, performance_services
    ):
        "]""Test that cached predictions provide superior performance."""""""
        # Setup test data
        match_features = (
            FeatureFactory.generate_comprehensive_features(num_samples=1)
            .iloc[0]
            .to_dict()
        )
        match_features["match_id["] = 12346[""""

        # Initial request (cache miss)
        start_time = time.time()
        prediction1 = await performance_services[
            "]]prediction_service["""""
        ].predict_match_outcome(match_features)
        first_request_time = (time.time() - start_time) * 1000

        # Validate first prediction
        assert_valid_prediction_response(prediction1)

        # Cache the prediction
        cache_key = f["]prediction{match_features['match_id']}"]: cache_success = await performance_services["redis["].set(": cache_key, prediction1, ttl=300["""
        )
        assert cache_success, f["]]Failed to cache prediction for key {cache_key}"]""""

        # Verify cache storage
        cached_data = await performance_services["redis["].get(cache_key)": assert (" cached_data ==prediction1[""
        ), "]]Cached data differs from original prediction["""""

        # Second request (cache hit)
        start_time = time.time()
        await performance_services["]redis["].get(cache_key)": second_request_time = (time.time() - start_time) * 1000["""

        # Cache performance validation
        cache_performance_threshold = 10.0  # 10ms for cache reads
        assert (
            second_request_time < cache_performance_threshold
        ), f["]]Cached request time {second_request_time:.2f}ms exceeds cache threshold of {cache_performance_threshold}ms["]""""

        # Performance improvement validation
        performance_improvement = first_request_time - second_request_time
        improvement_ratio = first_request_time / max(
            second_request_time, 0.001
        )  # Avoid division by zero

        assert (
            performance_improvement > 0
        ), f["]Cached response should be faster, but took {second_request_time:.2f}ms vs {first_request_time:.2f}ms["]: assert (" improvement_ratio > 2.0["""
        ), f["]]Cached response should be at least 2x faster, but was only {improvement_ratio:.1f}x faster["]""""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_batch_prediction_performance_efficiency(self, performance_services):
        "]""Test batch prediction performance with comprehensive validation."""""""
        # Setup test data
        batch_size = 10
        match_features_list = []

        for i in range(batch_size):
            features = (
                FeatureFactory.generate_comprehensive_features(num_samples=1)
                .iloc[0]
                .to_dict()
            )
            features["match_id["] = 12340 + i[": match_features_list.append(features)"""

        # Validate test setup
        assert (
            len(match_features_list) ==batch_size
        ), f["]]Expected {batch_size} match features, got {len(match_features_list)}"]""""

        # Measure batch prediction performance
        start_time = time.time()
        batch_predictions = await performance_services[
            "prediction_service["""""
        ].batch_predict(match_features_list)
        end_time = time.time()

        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_prediction = total_time_ms / batch_size

        # Batch efficiency validation
        batch_efficiency_threshold = 50.0  # 50ms per prediction in batch
        assert (
            avg_time_per_prediction < batch_efficiency_threshold
        ), f["]Average prediction time {avg_time_per_prediction:.2f}ms exceeds batch threshold of {batch_efficiency_threshold}ms["]""""

        # Batch completeness validation
        assert len(batch_predictions) ==batch_size, (
            f["]Expected {batch_size} predictions, got {len(batch_predictions)}. "]: f["Missing["]: [{batch_size - len(batch_predictions)} predictions]"]"""
        )

        # Batch quality validation
        failed_predictions = [pred for pred in batch_predictions if "error[": in pred]": assert (" not failed_predictions[""
        ), f["]]Batch contained {len(failed_predictions)} failed predictions["]: [{failed_predictions}]""""

        # Individual prediction validation
        for i, prediction in enumerate(batch_predictions):
            assert_valid_prediction_response(prediction)
            expected_match_id = match_features_list[i]["]match_id["]": assert (" prediction["]match_id["] ==expected_match_id[""""
            ), f["]]Prediction {i} has match_id {prediction['match_id']}, expected {expected_match_id}"]""""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_api_performance_under_concurrent_load(self, performance_services):
        """Test API performance under realistic concurrent load conditions."""""""
        # Setup test data for concurrent testing
        num_requests = 20
        match_features_list = []

        for i in range(num_requests):
            features = (
                FeatureFactory.generate_comprehensive_features(num_samples=1)
                .iloc[0]
                .to_dict()
            )
            features["match_id["] = 12400 + i[": match_features_list.append(features)"""

        # Simulate concurrent requests
        async def make_prediction_with_validation(features, request_id):
            "]]""Make prediction with comprehensive validation."""""""
            try = start_time time.time()
                prediction = await performance_services[
                    "prediction_service["""""
                ].predict_match_outcome(features)
                response_time = (time.time() - start_time) * 1000

                # Validate prediction quality
                assert_valid_prediction_response(prediction)

                return {
                    "]success[": True,""""
                    "]prediction[": prediction,""""
                    "]response_time_ms[": response_time,""""
                    "]request_id[": request_id,""""
                }
            except Exception as e:
                return {"]success[": False, "]error[": str(e), "]request_id[": request_id}""""

        # Execute concurrent requests
        start_time = time.time()
        tasks = [
            make_prediction_with_validation(features, i)
            for i, features in enumerate(match_features_list)
        ]
        results = await asyncio.gather(*tasks)
        total_execution_time = time.time() - start_time

        # Analyze concurrent performance
        successful_results = [r for r in results if r["]success["]]": failed_results = [r for r in results if not r["]success["]]""""

        # Success rate validation
        success_rate = len(successful_results) / num_requests
        assert success_rate >= 0.95, (
            f["]Success rate {success_rate:.1%} below 95% threshold. "]: f["Successful["]: [{len(successful_results)}, Failed]"]"""
        )

        # Response time analysis
        response_times = [r["response_time_ms["] for r in successful_results]""""

        # Performance consistency validation
        performance_stats = assert_performance_consistency(
            response_times, "]Concurrent API calls["""""
        )

        # Throughput validation
        throughput = num_requests / total_execution_time
        min_throughput = 10.0  # 10 requests per second minimum

        assert (
            throughput >= min_throughput
        ), f["]Throughput {throughput:.1f} requests/second below minimum {min_throughput} requests/second["]""""

        # Performance tier validation
        avg_response_time = performance_stats["]avg_time["]": assert (" avg_response_time < 150.0[""
        ), f["]]Average concurrent response time {avg_response_time:.2f}ms exceeds 150ms limit["]""""

        # Detailed performance report
        {
            "]total_requests[": num_requests,""""
            "]successful_requests[": len(successful_results),""""
            "]failed_requests[": len(failed_results),""""
            "]success_rate[": success_rate,""""
            "]throughput_rps[": throughput,""""
            "]total_execution_time_s[": total_execution_time,""""
            "]response_time_stats[": performance_stats,""""
            "]performance_tier[": performance_stats["]performance_tier["],""""
        }

        # Performance tier should be at least "]good[": assert performance_stats["]performance_tier["] in [""""
            "]excellent[",""""
            "]good[",""""
        ], f["]Performance tier '{performance_stats['performance_tier']}' not meeting minimum requirement["]"]"""
