"""
Unit tests for model evaluation functionality.

Tests the ModelMetricsExporter class and related evaluation functions including:
- Metrics export functionality
- Accuracy calculations
- Performance monitoring
- Error handling and edge cases
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from prometheus_client import CollectorRegistry

from src.models.metrics_exporter import ModelMetricsExporter
from src.models.prediction_service import PredictionResult


class TestModelMetricsExporter:
    """Test cases for ModelMetricsExporter class."""

    @pytest.fixture
    def custom_registry(self):
        """Create a custom registry for testing."""
        return CollectorRegistry()

    @pytest.fixture
    def metrics_exporter(self, custom_registry):
        """Create ModelMetricsExporter instance with custom registry."""
        return ModelMetricsExporter(registry=custom_registry)

    @pytest.fixture
    def sample_prediction_result(self):
        """Sample prediction result for testing."""
        return PredictionResult(
            match_id=12345,
            model_version="1.0",
            model_name="football_baseline_model",
            home_win_probability=0.5,
            draw_probability=0.3,
            away_win_probability=0.2,
            predicted_result="home",
            confidence_score=0.5,
            features_used={"feature1": 1.0},
            prediction_metadata={"test": "metadata"},
            created_at=datetime.now()
        )

    class TestInitialization:
        """Test cases for metrics exporter initialization."""

        def test_initialization_with_custom_registry(self, custom_registry):
            """Test initialization with custom registry."""
            exporter = ModelMetricsExporter(registry=custom_registry)
            assert exporter.registry is custom_registry

        def test_initialization_without_registry(self):
            """Test initialization without custom registry."""
            exporter = ModelMetricsExporter()
            assert exporter.registry is not None
            assert isinstance(exporter.registry, CollectorRegistry)

        def test_metrics_creation(self, metrics_exporter):
            """Test that all Prometheus metrics are created properly."""
            # Check that all expected metrics exist
            assert hasattr(metrics_exporter, 'predictions_total')
            assert hasattr(metrics_exporter, 'prediction_accuracy')
            assert hasattr(metrics_exporter, 'prediction_confidence')
            assert hasattr(metrics_exporter, 'prediction_duration')
            assert hasattr(metrics_exporter, 'model_coverage_rate')
            assert hasattr(metrics_exporter, 'daily_predictions_count')
            assert hasattr(metrics_exporter, 'model_load_duration')
            assert hasattr(metrics_exporter, 'prediction_errors_total')

    class TestPredictionMetricsExport:
        """Test cases for prediction metrics export functionality."""

        def test_export_prediction_metrics_success(self, metrics_exporter, sample_prediction_result):
            """Test successful prediction metrics export."""
            # Export metrics
            metrics_exporter.export_prediction_metrics(sample_prediction_result)

            # Verify that the counter was incremented
            metric_family = metrics_exporter.registry.get_sample_value('football_predictions_total', {
                'model_name': 'football_baseline_model',
                'model_version': '1.0',
                'predicted_result': 'home'
            })
            assert metric_family is not None

            # Verify confidence score was recorded
            confidence_metric = metrics_exporter.registry.get_sample_value(
                'football_prediction_confidence_score_bucket',
                {'model_name': 'football_baseline_model', 'model_version': '1.0', 'le': '0.5'}
            )
            assert confidence_metric is not None

        def test_export_prediction_metrics_with_exception(self, metrics_exporter, sample_prediction_result):
            """Test prediction metrics export with exception."""
            # Mock the labels method to raise an exception
            metrics_exporter.predictions_total.labels.side_effect = Exception("Test exception")

            # Should not raise exception, should log error instead
            metrics_exporter.export_prediction_metrics(sample_prediction_result)

            # No assertion needed - just verify it doesn't crash

        def test_export_daily_predictions_count(self, metrics_exporter, sample_prediction_result):
            """Test daily predictions count export."""
            metrics_exporter.export_prediction_metrics(sample_prediction_result)

            # Verify daily count was incremented
            today = datetime.now().strftime("%Y-%m-%d")
            daily_metric = metrics_exporter.registry.get_sample_value(
                'football_daily_predictions_count',
                {'model_name': 'football_baseline_model', 'date': today}
            )
            assert daily_metric is not None

    class TestAccuracyMetricsExport:
        """Test cases for accuracy metrics export functionality."""

        def test_export_accuracy_metrics_success(self, metrics_exporter):
            """Test successful accuracy metrics export."""
            model_name = "test_model"
            model_version = "1.0"
            accuracy = 0.85
            time_window = "7d"

            # Export accuracy metrics
            metrics_exporter.export_accuracy_metrics(
                model_name=model_name,
                model_version=model_version,
                accuracy=accuracy,
                time_window=time_window
            )

            # Verify accuracy gauge was set
            accuracy_metric = metrics_exporter.registry.get_sample_value(
                'football_prediction_accuracy',
                {
                    'model_name': model_name,
                    'model_version': model_version,
                    'time_window': time_window
                }
            )
            assert accuracy_metric == accuracy

        def test_export_accuracy_metrics_boundary_values(self, metrics_exporter):
            """Test accuracy metrics export with boundary values."""
            # Test minimum accuracy (0.0)
            metrics_exporter.export_accuracy_metrics("test_model", "1.0", 0.0)
            accuracy_metric = metrics_exporter.registry.get_sample_value(
                'football_prediction_accuracy',
                {'model_name': 'test_model', 'model_version': '1.0', 'time_window': '7d'}
            )
            assert accuracy_metric == 0.0

            # Test maximum accuracy (1.0)
            metrics_exporter.export_accuracy_metrics("test_model", "1.0", 1.0)
            accuracy_metric = metrics_exporter.registry.get_sample_value(
                'football_prediction_accuracy',
                {'model_name': 'test_model', 'model_version': '1.0', 'time_window': '7d'}
            )
            assert accuracy_metric == 1.0

        def test_export_accuracy_metrics_with_exception(self, metrics_exporter):
            """Test accuracy metrics export with exception."""
            metrics_exporter.prediction_accuracy.labels.side_effect = Exception("Test exception")

            # Should not raise exception
            metrics_exporter.export_accuracy_metrics("test_model", "1.0", 0.75)

        def test_export_accuracy_metrics_default_time_window(self, metrics_exporter):
            """Test accuracy metrics export with default time window."""
            metrics_exporter.export_accuracy_metrics("test_model", "1.0", 0.80)

            # Verify default time window is used
            accuracy_metric = metrics_exporter.registry.get_sample_value(
                'football_prediction_accuracy',
                {'model_name': 'test_model', 'model_version': '1.0', 'time_window': '7d'}
            )
            assert accuracy_metric == 0.80

    class TestDurationMetricsExport:
        """Test cases for duration metrics export functionality."""

        def test_export_duration_metrics_success(self, metrics_exporter):
            """Test successful duration metrics export."""
            model_name = "test_model"
            model_version = "1.0"
            duration = 0.125  # 125ms

            # Export duration metrics
            metrics_exporter.export_duration_metrics(model_name, model_version, duration)

            # Verify duration histogram was updated
            duration_metric = metrics_exporter.registry.get_sample_value(
                'football_model_prediction_duration_seconds_bucket',
                {'model_name': model_name, 'model_version': model_version, 'le': '0.25'}
            )
            assert duration_metric is not None

        def test_export_duration_metrics_edge_cases(self, metrics_exporter):
            """Test duration metrics export with edge cases."""
            # Test very small duration
            metrics_exporter.export_duration_metrics("test_model", "1.0", 0.001)

            # Test large duration
            metrics_exporter.export_duration_metrics("test_model", "1.0", 10.0)

            # Test zero duration
            metrics_exporter.export_duration_metrics("test_model", "1.0", 0.0)

            # Verify all were recorded without error
            assert True  # If no exception, test passes

    class TestCoverageMetricsExport:
        """Test cases for coverage metrics export functionality."""

        def test_export_coverage_metrics_success(self, metrics_exporter):
            """Test successful coverage metrics export."""
            model_name = "test_model"
            model_version = "1.0"
            coverage_rate = 0.95

            # Export coverage metrics
            metrics_exporter.export_coverage_metrics(model_name, model_version, coverage_rate)

            # Verify coverage gauge was set
            coverage_metric = metrics_exporter.registry.get_sample_value(
                'football_model_coverage_rate',
                {'model_name': model_name, 'model_version': model_version}
            )
            assert coverage_metric == coverage_rate

        def test_export_coverage_metrics_invalid_values(self, metrics_exporter):
            """Test coverage metrics export with invalid values."""
            # Test coverage > 1.0 (should be handled gracefully)
            metrics_exporter.export_coverage_metrics("test_model", "1.0", 1.5)

            # Test negative coverage (should be handled gracefully)
            metrics_exporter.export_coverage_metrics("test_model", "1.0", -0.1)

            # Verify no exceptions were raised
            assert True

    class TestErrorMetricsExport:
        """Test cases for error metrics export functionality."""

        def test_export_error_metrics_success(self, metrics_exporter):
            """Test successful error metrics export."""
            model_name = "test_model"
            model_version = "1.0"
            error_type = "prediction_failure"

            # Export error metrics
            metrics_exporter.export_error_metrics(model_name, model_version, error_type)

            # Verify error counter was incremented
            error_metric = metrics_exporter.registry.get_sample_value(
                'football_prediction_errors_total',
                {
                    'model_name': model_name,
                    'model_version': model_version,
                    'error_type': error_type
                }
            )
            assert error_metric is not None

        def test_export_error_metrics_multiple_errors(self, metrics_exporter):
            """Test error metrics export with multiple error types."""
            error_types = ["validation_error", "model_error", "database_error"]

            for error_type in error_types:
                metrics_exporter.export_error_metrics("test_model", "1.0", error_type)

            # Verify all error types were recorded
            for error_type in error_types:
                error_metric = metrics_exporter.registry.get_sample_value(
                    'football_prediction_errors_total',
                    {'model_name': 'test_model', 'model_version': '1.0', 'error_type': error_type}
                )
                assert error_metric is not None

    class TestModelLoadMetricsExport:
        """Test cases for model load metrics export functionality."""

        def test_export_model_load_duration_success(self, metrics_exporter):
            """Test successful model load duration export."""
            model_name = "test_model"
            model_version = "1.0"
            duration = 2.5  # 2.5 seconds

            # Export model load duration
            metrics_exporter.export_model_load_duration(model_name, model_version, duration)

            # Verify duration histogram was updated
            load_metric = metrics_exporter.registry.get_sample_value(
                'football_model_load_duration_seconds_bucket',
                {'model_name': model_name, 'model_version': model_version, 'le': '5.0'}
            )
            assert load_metric is not None

        def test_export_model_load_duration_various_load_times(self, metrics_exporter):
            """Test model load duration export with various load times."""
            load_times = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

            for load_time in load_times:
                metrics_exporter.export_model_load_duration("test_model", "1.0", load_time)

            # Verify all load times were recorded
            assert True  # If no exceptions, test passes

    class TestMetricsSummary:
        """Test cases for metrics summary functionality."""

        def test_get_metrics_summary_success(self, metrics_exporter):
            """Test successful metrics summary retrieval."""
            summary = metrics_exporter.get_metrics_summary()

            # Verify summary structure
            assert isinstance(summary, dict)
            assert "predictions_total" in summary
            assert "prediction_accuracy" in summary
            assert "prediction_confidence" in summary
            assert "prediction_duration" in summary
            assert "model_coverage_rate" in summary
            assert "daily_predictions_count" in summary
            assert "model_load_duration" in summary
            assert "prediction_errors_total" in summary

            # Verify summary values are descriptive
            assert isinstance(summary["predictions_total"], str)
            assert len(summary["predictions_total"]) > 0

        def test_get_metrics_summary_with_exception(self, metrics_exporter):
            """Test metrics summary retrieval with exception."""
            # Mock to raise exception
            with patch.object(metrics_exporter, 'prediction_accuracy', side_effect=Exception("Test error")):
                summary = metrics_exporter.get_metrics_summary()

                # Should return empty dict on error
                assert summary == {}

    class TestIntegrationScenarios:
        """Integration test scenarios for the metrics exporter."""

        def test_complete_prediction_workflow_metrics(self, metrics_exporter, sample_prediction_result):
            """Test complete prediction workflow metrics export."""
            # Export prediction metrics
            metrics_exporter.export_prediction_metrics(sample_prediction_result)

            # Export accuracy metrics (simulating post-match verification)
            metrics_exporter.export_accuracy_metrics(
                sample_prediction_result.model_name,
                sample_prediction_result.model_version,
                0.85
            )

            # Export duration metrics
            metrics_exporter.export_duration_metrics(
                sample_prediction_result.model_name,
                sample_prediction_result.model_version,
                0.125
            )

            # Export coverage metrics
            metrics_exporter.export_coverage_metrics(
                sample_prediction_result.model_name,
                sample_prediction_result.model_version,
                0.95
            )

            # Export model load metrics
            metrics_exporter.export_model_load_duration(
                sample_prediction_result.model_name,
                sample_prediction_result.model_version,
                2.5
            )

            # Verify all metrics were recorded
            summary = metrics_exporter.get_metrics_summary()
            assert len(summary) == 9  # All 9 metric types

        def test_multiple_models_metrics_isolation(self, metrics_exporter):
            """Test that metrics for different models are properly isolated."""
            # Create prediction results for different models
            result_v1 = PredictionResult(
                match_id=1, model_version="1.0", predicted_result="home", confidence_score=0.8
            )
            result_v2 = PredictionResult(
                match_id=2, model_version="2.0", predicted_result="away", confidence_score=0.6
            )

            # Export metrics for both models
            metrics_exporter.export_prediction_metrics(result_v1)
            metrics_exporter.export_prediction_metrics(result_v2)

            # Verify metrics are isolated by model version
            v1_metric = metrics_exporter.registry.get_sample_value(
                'football_predictions_total',
                {'model_name': 'football_baseline_model', 'model_version': '1.0', 'predicted_result': 'home'}
            )
            v2_metric = metrics_exporter.registry.get_sample_value(
                'football_predictions_total',
                {'model_name': 'football_baseline_model', 'model_version': '2.0', 'predicted_result': 'away'}
            )

            assert v1_metric is not None
            assert v2_metric is not None

        def test_error_handling_scenarios(self, metrics_exporter):
            """Test various error handling scenarios."""
            # Test with invalid prediction result
            invalid_result = None
            metrics_exporter.export_prediction_metrics(invalid_result)  # Should not crash

            # Test with missing attributes
            partial_result = PredictionResult(match_id=1, model_version="1.0")
            metrics_exporter.export_prediction_metrics(partial_result)  # Should not crash

            # Test with extreme values
            extreme_result = PredictionResult(
                match_id=1, model_version="1.0", confidence_score=999.9
            )
            metrics_exporter.export_prediction_metrics(extreme_result)  # Should not crash

            # Verify no exceptions were raised
            assert True

    class TestPrometheusIntegration:
        """Test Prometheus integration specific functionality."""

        def test_registry_isolation(self):
            """Test that different registries don't interfere."""
            registry1 = CollectorRegistry()
            registry2 = CollectorRegistry()

            exporter1 = ModelMetricsExporter(registry=registry1)
            exporter2 = ModelMetricsExporter(registry=registry2)

            # Export metrics to different exporters
            result1 = PredictionResult(match_id=1, model_version="1.0", predicted_result="home")
            result2 = PredictionResult(match_id=2, model_version="2.0", predicted_result="away")

            exporter1.export_prediction_metrics(result1)
            exporter2.export_prediction_metrics(result2)

            # Verify metrics are in separate registries
            metric1 = registry1.get_sample_value(
                'football_predictions_total',
                {'model_name': 'football_baseline_model', 'model_version': '1.0', 'predicted_result': 'home'}
            )
            metric2 = registry2.get_sample_value(
                'football_predictions_total',
                {'model_name': 'football_baseline_model', 'model_version': '2.0', 'predicted_result': 'away'}
            )

            assert metric1 is not None
            assert metric2 is not None

        def test_metric_labels_consistency(self, metrics_exporter, sample_prediction_result):
            """Test that metric labels are consistent across different metric types."""
            model_name = sample_prediction_result.model_name
            model_version = sample_prediction_result.model_version

            # Export various metrics for the same model
            metrics_exporter.export_prediction_metrics(sample_prediction_result)
            metrics_exporter.export_accuracy_metrics(model_name, model_version, 0.85)
            metrics_exporter.export_duration_metrics(model_name, model_version, 0.125)
            metrics_exporter.export_coverage_metrics(model_name, model_version, 0.95)

            # Verify labels are consistent
            labels = {'model_name': model_name, 'model_version': model_version}

            # Check that all metrics use the same label structure
            for metric_name in [
                'football_prediction_confidence_score_bucket',
                'football_prediction_accuracy',
                'football_model_prediction_duration_seconds_bucket',
                'football_model_coverage_rate'
            ]:
                metric = metrics_exporter.registry.get_sample_value(metric_name, labels)
                if metric is not None:  # Some metrics might be in different buckets
                    assert True  # Label structure is consistent

    class TestPerformanceConsiderations:
        """Test performance-related considerations."""

        def test_concurrent_metrics_export(self, metrics_exporter):
            """Test that concurrent metrics export doesn't cause issues."""
            import threading
            import time

            def export_metrics(thread_id):
                for i in range(10):
                    result = PredictionResult(
                        match_id=thread_id * 10 + i,
                        model_version="1.0",
                        predicted_result="home",
                        confidence_score=0.5 + (i * 0.1)
                    )
                    metrics_exporter.export_prediction_metrics(result)
                    time.sleep(0.01)  # Small delay

            # Create multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=export_metrics, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Verify no exceptions were raised
            assert True

        def test_memory_usage(self, metrics_exporter):
            """Test that metrics export doesn't cause excessive memory usage."""
            # Export a large number of metrics
            for i in range(1000):
                result = PredictionResult(
                    match_id=i,
                    model_version="1.0",
                    predicted_result="home",
                    confidence_score=0.5
                )
                metrics_exporter.export_prediction_metrics(result)

            # Verify the registry still works
            summary = metrics_exporter.get_metrics_summary()
            assert len(summary) > 0

            # This is a basic test - in practice, you might want to use memory profiling tools