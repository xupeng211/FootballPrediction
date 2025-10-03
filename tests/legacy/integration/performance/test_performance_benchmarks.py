"""""""
Extended performance benchmark tests using pytest-benchmark.

This module provides comprehensive performance benchmarking for the football prediction system,
establishing baseline metrics and detecting performance regressions.
"""""""

import pytest
import asyncio
import time
import json
from datetime import datetime
import psutil
import os

from tests.factories import FeatureFactory
from tests.mocks import MockDatabaseManager, MockRedisManager, MockPredictionService


class TestPredictionServiceBenchmarks:
    """Benchmark tests for prediction service performance."""""""

    @pytest.fixture
    def benchmark_services(self):
        """Setup services for benchmark testing."""""""
        return {
            "database[": MockDatabaseManager(),""""
            "]redis[": MockRedisManager(),""""
            "]prediction_service[": MockPredictionService(),""""
        }

    @pytest.mark.benchmark
    def test_single_prediction_benchmark(self, benchmark, benchmark_services):
        "]""Benchmark single prediction performance."""""""
        # Setup test data
        features = (
            FeatureFactory.generate_comprehensive_features(num_samples=1)
            .iloc[0]
            .to_dict()
        )
        features["match_id["] = 14000[": async def make_prediction():": return await benchmark_services["]]prediction_service["].predict_match_outcome(": features["""
            )

        # Benchmark the prediction
        result = benchmark.pedantic(make_prediction, rounds=50, warmup=False)

        # Validate result
        assert result["]]confidence["] > 0.5[" assert "]]probabilities[" in result[""""

    @pytest.mark.benchmark
    def test_batch_prediction_benchmark(self, benchmark, benchmark_services):
        "]]""Benchmark batch prediction performance."""""""
        # Setup test data
        batch_sizes = [1, 5, 10, 20, 50]
        results = {}

        for batch_size in batch_sizes = features_list []
            for i in range(batch_size):
                features = (
                    FeatureFactory.generate_comprehensive_features(num_samples=1)
                    .iloc[0]
                    .to_dict()
                )
                features["match_id["] = 14100 + i[": features_list.append(features)": async def make_batch_prediction():": return await benchmark_services["]]prediction_service["].batch_predict(": features_list["""
                )

            # Benchmark batch prediction
            result = benchmark.pedantic(make_batch_prediction, rounds=20, warmup=False)
            results[batch_size] = {
                "]]time[": benchmark.stats.stats.mean,""""
                "]predictions_per_second[": (": batch_size / benchmark.stats.stats.mean[": if benchmark.stats.stats.mean > 0[": else 0"
                ),
                "]]]result_count[": len(result),""""
            }

        # Validate scaling performance
        for batch_size, metrics in results.items():
            assert (
                metrics["]predictions_per_second["] > 10[""""
            ), f["]]Batch size {batch_size}: {metrics['predictions_per_second']:.1f} predictions/second too slow["]: assert (" metrics["]result_count["] ==batch_size[""""
            ), f["]]Batch size {batch_size}: Expected {batch_size} results, got {metrics['result_count']}"]""""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_cached_prediction_benchmark(self, benchmark, benchmark_services):
        """Benchmark cached prediction performance."""""""
        features = (
            FeatureFactory.generate_comprehensive_features(num_samples=1)
            .iloc[0]
            .to_dict()
        )
        features["match_id["] = 14200[": cache_key = f["]]prediction{features['match_id']}"]""""

        # Pre-cache the prediction
        prediction = await benchmark_services[
            "prediction_service["""""
        ].predict_match_outcome(features)
        await benchmark_services["]redis["].set(cache_key, prediction, ttl=300)": async def get_cached_prediction():": return await benchmark_services["]redis["].get(cache_key)""""

        # Benchmark cache retrieval
        result = benchmark.pedantic(get_cached_prediction, rounds=100, warmup=False)

        # Cache should be extremely fast
        assert (
            benchmark.stats.stats.mean < 0.001
        ), f["]Cache retrieval too slow["]: [{benchmark.stats.stats.mean:.6f}s]": assert result ==prediction, "]Cached result mismatch["""""

    @pytest.mark.benchmark
    def test_feature_generation_benchmark(self, benchmark):
        "]""Benchmark feature generation performance."""""""

        def generate_features():
            return FeatureFactory.generate_comprehensive_features(num_samples=10)

        # Benchmark feature generation
        result = benchmark.pedantic(generate_features, rounds=30, warmup=False)

        # Validate feature generation
        assert len(result) ==10, "Should generate 10 feature sets[" assert len(result.columns) > 20, "]Should have sufficient features["""""

    @pytest.mark.benchmark
    def test_database_query_benchmark(self, benchmark, benchmark_services):
        "]""Benchmark database query performance."""""""
        # Setup mock data
        mock_matches = []
        for i in range(100):
            mock_matches.append(
                {
                    "match_id[": 14300 + i,""""
                    "]home_team[": f["]Team {i}"],""""
                    "away_team[": f["]Team {i+1}"],""""
                    "home_score[": i % 3,""""
                    "]away_score[": (i + 1) % 3,""""
                }
            )

        async def query_database():
            async with benchmark_services["]database["].get_session() as session:": session.set_execute_result("]fetchall[", mock_matches)": result = await session.execute("]SELECT * FROM matches LIMIT 100[")": return result.fetchall()"""

        # Benchmark database query
        result = benchmark.pedantic(query_database, rounds=50, warmup=False)

        # Validate query performance and results
        assert (
            benchmark.stats.stats.mean < 0.01
        ), f["]Database query too slow["]: [{benchmark.stats.stats.mean:.6f}s]": assert len(result) ==100, "]Should return 100 matches[" class TestMemoryUsageBenchmarks:""""
    "]""Benchmark tests for memory usage."""""""

    @pytest.mark.benchmark
    def test_memory_usage_scaling_benchmark(self, benchmark):
        """Benchmark memory usage scaling with prediction volume."""""""
        process = psutil.Process(os.getpid())

        def test_memory_scaling():
            # Generate increasing volumes of predictions
            volumes = [10, 50, 100, 500, 1000]
            memory_usage = []

            for volume in volumes:
                # Clear memory before test
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB

                # Generate predictions
                features = FeatureFactory.generate_comprehensive_features(
                    num_samples=volume
                )

                # Simulate prediction processing
                predictions = []
                for _, row in features.iterrows():
                    prediction = {
                        "match_id[": row.get("]match_id[", 0),""""
                        "]home_win_prob[": 0.5,""""
                        "]draw_prob[": 0.3,""""
                        "]away_win_prob[": 0.2,""""
                    }
                    predictions.append(prediction)

                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = final_memory - initial_memory
                memory_usage.append(
                    {
                        "]volume[": volume,""""
                        "]memory_increase_mb[": memory_increase,""""
                        "]memory_per_prediction_mb[": (": memory_increase / volume if volume > 0 else 0["""
                        ),
                    }
                )

                # Clean up
                del features
                del predictions

            return memory_usage

        # Run memory scaling test
        memory_results = benchmark.pedantic(test_memory_scaling, rounds=5, warmup=False)

        # Analyze memory scaling
        last_result = memory_results[-1]  # 1000 predictions
        assert (
            last_result["]]memory_per_prediction_mb["] < 0.1[""""
        ), f["]]Memory usage per prediction too high: {last_result['memory_per_prediction_mb']:.6f}MB["]: assert (" last_result["]memory_increase_mb["] < 100[""""
        ), f["]]Total memory increase for 1000 predictions too high: {last_result['memory_increase_mb']:.1f}MB["]: class TestConcurrentPerformanceBenchmarks:""""
    "]""Benchmark tests for concurrent performance."""""""

    @pytest.mark.benchmark
    def test_concurrent_predictions_benchmark(self, benchmark, benchmark_services):
        """Benchmark concurrent prediction performance."""""""

        async def concurrent_predictions():
            num_concurrent = 20
            features_list = []

            for i in range(num_concurrent):
                features = (
                    FeatureFactory.generate_comprehensive_features(num_samples=1)
                    .iloc[0]
                    .to_dict()
                )
                features["match_id["] = 14400 + i[": features_list.append(features)"""

            # Create concurrent tasks
            tasks = [
                benchmark_services["]]prediction_service["].predict_match_outcome(features)": for features in features_list["""
            ]

            # Execute concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            return {
                "]]total_time[": total_time,""""
                "]predictions_per_second[": num_concurrent / total_time,""""
                "]results_count[": len(results),""""
            }

        # Benchmark concurrent performance
        result = benchmark.pedantic(concurrent_predictions, rounds=20, warmup=False)

        # Validate concurrent performance
        assert (
            result["]predictions_per_second["] > 15[""""
        ), f["]]Concurrent performance too slow: {result['predictions_per_second']:.1f} predictions/second["]: assert (" result["]results_count["] ==20[""""
        ), "]]Should complete all 20 concurrent predictions[": class TestPerformanceRegressionDetection:""""
    "]""Performance regression detection benchmarks."""""""

    @pytest.mark.benchmark
    def test_regression_detection_benchmark(self, benchmark, benchmark_services):
        """Establish baseline metrics for regression detection."""""""
        # This test establishes baseline metrics that can be used for regression detection

        metrics = {}

        # Test 1: Single prediction baseline
        features = (
            FeatureFactory.generate_comprehensive_features(num_samples=1)
            .iloc[0]
            .to_dict()
        )
        features["match_id["] = 14500[": async def single_prediction_baseline():": return await benchmark_services["]]prediction_service["].predict_match_outcome(": features["""
            )

        benchmark.pedantic(single_prediction_baseline, rounds=50, warmup=False)
        metrics["]]single_prediction_mean_ms["] = benchmark.stats.stats.mean * 1000[": metrics["]]single_prediction_std_ms["] = benchmark.stats.stats.stdev * 1000[""""

        # Test 2: Batch prediction baseline
        batch_features = []
        for i in range(10):
            features = (
                FeatureFactory.generate_comprehensive_features(num_samples=1)
                .iloc[0]
                .to_dict()
            )
            features["]]match_id["] = 14510 + i[": batch_features.append(features)": async def batch_prediction_baseline():": return await benchmark_services["]]prediction_service["].batch_predict(": batch_features["""
            )

        benchmark.pedantic(batch_prediction_baseline, rounds=20, warmup=False)
        metrics["]]batch_prediction_mean_ms["] = benchmark.stats.stats.mean * 1000[": metrics["]]batch_predictions_per_second["] = 10 / benchmark.stats.stats.mean[""""

        # Test 3: Memory usage baseline
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024

        FeatureFactory.generate_comprehensive_features(num_samples=100)
        final_memory = process.memory_info().rss / 1024 / 1024

        metrics["]]memory_usage_per_100_predictions_mb["] = final_memory - initial_memory[""""

        # Store baseline metrics for future regression detection
        baseline_file = os.getenv("TEST_PERFORMANCE_BENCHMARKS_BASELINE_FILE_292"): try:": with open(baseline_file, "]w[") as f:": json.dump("""
                    {"]timestamp[": datetime.now().isoformat(), "]metrics[": metrics},": f,": indent=2,""
                )
        except Exception:
            # If file write fails, continue with test
            pass

        # Validate baseline metrics are reasonable
        assert (
            metrics["]single_prediction_mean_ms["] < 100[""""
        ), f["]]Single prediction baseline too slow: {metrics['single_prediction_mean_ms']:.2f}ms["]: assert (" metrics["]batch_predictions_per_second["] > 10[""""
        ), f["]]Batch prediction baseline too slow: {metrics['batch_predictions_per_second']:.1f} predictions/second["]: assert (" metrics["]memory_usage_per_100_predictions_mb["] < 50[""""
        ), f["]]Memory usage baseline too high: {metrics['memory_usage_per_100_predictions_mb']:.1f}MB["]: return metrics[": class TestPerformanceBaselines:"""
    "]]""Define and validate performance baselines."""""""

    PERFORMANCE_BASELINES = {
        "single_prediction_ms[": 50.0,  # Maximum 50ms for single prediction[""""
        "]]batch_prediction_pps[": 20.0,  # Minimum 20 predictions per second for batch[""""
        "]]cache_read_ms[": 1.0,  # Maximum 1ms for cache read[""""
        "]]database_query_ms[": 10.0,  # Maximum 10ms for database query[""""
        "]]memory_per_prediction_mb[": 0.05,  # Maximum 0.05MB per prediction[""""
        "]]concurrent_pps[": 15.0,  # Minimum 15 predictions per second concurrent[""""
    }

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_baselines(self, benchmark_services):
        "]]""Validate current performance against established baselines."""""""
        results = {}

        # Test single prediction baseline
        features = (
            FeatureFactory.generate_comprehensive_features(num_samples=1)
            .iloc[0]
            .to_dict()
        )
        features["match_id["] = 14600[": start_time = time.time()": prediction = asyncio.run(": benchmark_services["]]prediction_service["].predict_match_outcome(features)""""
        )
        single_prediction_time = (time.time() - start_time) * 1000
        results["]single_prediction_ms["] = single_prediction_time[""""

        # Test batch prediction baseline
        batch_features = []
        for i in range(10):
            features = (
                FeatureFactory.generate_comprehensive_features(num_samples=1)
                .iloc[0]
                .to_dict()
            )
            features["]]match_id["] = 14610 + i[": batch_features.append(features)": start_time = time.time()": batch_predictions = asyncio.run("
            benchmark_services["]]prediction_service["].batch_predict(batch_features)""""
        )
        batch_time = time.time() - start_time
        results["]batch_prediction_pps["] = len(batch_predictions) / batch_time[""""

        # Test cache read baseline
        cache_key = os.getenv("TEST_PERFORMANCE_BENCHMARKS_CACHE_KEY_347"): await benchmark_services["]redis["].set(cache_key, prediction, ttl=300)": start_time = time.time()": asyncio.run(benchmark_services["]redis["].get(cache_key))": cache_read_time = (time.time() - start_time) * 1000[": results["]]cache_read_ms["] = cache_read_time[""""

        # Validate against baselines
        violations = []
        for metric, actual in results.items():
            baseline = self.PERFORMANCE_BASELINES.get(metric)
            if baseline is None:
                continue

            if metric.endswith("]]_pps["):  # Higher is better[": if actual < baseline:": violations.append(": f["]]{metric}"]: [{actual:.1f} < {baseline:.1f} (minimum required)]""""
                    )
            else:  # Lower is better
                if actual > baseline:
                    violations.append(
                        f["{metric}"]: [{actual:.2f} > {baseline:.2f} (maximum allowed)]""""
                    )

        # Assert no violations
        assert not violations, f["Performance baseline violations {violations}"]""""

        # Return results for reporting
        return {
            "baselines[": self.PERFORMANCE_BASELINES,""""
            "]actual[": results,""""
            "]timestamp[": datetime.now().isoformat(),""""
        }


# Benchmark configuration for pytest-benchmark
def pytest_benchmark_scale_unit(config):
    "]""Configure benchmark scale units."""""""
    return "microseconds"""""
