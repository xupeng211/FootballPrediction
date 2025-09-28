"""
Demonstration of assertion quality improvements.

This file shows examples of poor assertions vs improved assertions
side by side for educational purposes.
"""

import pytest
import time
import statistics
from tests.factories import FeatureFactory
from tests.mocks import MockPredictionService


class TestAssertionQualityExamples:
    """Examples showing assertion quality improvements."""

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing assertion examples."""
        return {
            "prediction": {
                "match_id": 12345,
                "predicted_outcome": "home_win",
                "probabilities": {"home_win": 0.5, "draw": 0.3, "away_win": 0.2},
                "confidence": 0.85,
                "model_version": "v1.2"
            },
            "api_response": {
                "status": "success",
                "data": {"value": 42},
                "timestamp": "2024-01-15T10:00:00Z"
            }
        }

    def test_poor_assertions_example(self, sample_data):
        """Example of poor assertions - DON'T DO THIS."""
        prediction = sample_data["prediction"]
        response = sample_data["api_response"]

        # Poor assertions - basic checks without context
        assert prediction["confidence"] > 0
        assert len(prediction["probabilities"]) == 3
        assert response["status"] == "success"
        assert prediction["match_id"] == 12345

    def test_improved_assertions_example(self, sample_data):
        """Example of improved assertions - DO THIS."""
        prediction = sample_data["prediction"]
        response = sample_data["api_response"]

        # Improved assertions with context and validation
        assert prediction["confidence"] > 0, \
            f"Prediction confidence should be positive, got {prediction['confidence']}"

        assert len(prediction["probabilities"]) == 3, \
            f"Expected 3 outcomes in probabilities, got {len(prediction['probabilities'])}"

        assert response["status"] == "success", \
            f"Expected API status 'success', got '{response['status']}'"

        assert prediction["match_id"] == 12345, \
            f"Expected match_id 12345, got {prediction['match_id']}"

    def test_performance_poor_assertions(self):
        """Example of poor performance assertions."""
        service = MockPredictionService()
        features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
        features['match_id'] = 12345

        # Poor performance assertions
        start = time.time()
        result = service.predict_match_outcome(features)
        end = time.time()
        assert (end - start) * 1000 < 100

    def test_performance_improved_assertions(self):
        """Example of improved performance assertions."""
        service = MockPredictionService()
        features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
        features['match_id'] = 12345

        # Improved performance assertions
        start_time = time.time()
        result = service.predict_match_outcome(features)
        end_time = time.time()

        # Validate measurement
        assert end_time > start_time, "End time should be after start time"
        response_time_ms = (end_time - start_time) * 1000

        # Performance requirement with detailed error message
        max_acceptable_time = 100.0
        assert response_time_ms < max_acceptable_time, \
            f"Prediction API response time {response_time_ms:.2f}ms exceeds " \
            f"maximum acceptable time of {max_acceptable_time}ms"

        # Additional performance analysis
        assert response_time_ms > 0, f"Response time should be positive, got {response_time_ms}ms"

        # Performance tier assessment
        performance_tier = "excellent" if response_time_ms < 50 else "good" if response_time_ms < 100 else "acceptable"
        assert performance_tier in ["excellent", "good"], \
            f"Performance tier '{performance_tier}' not meeting minimum requirement of 'good'"

    def test_data_validation_poor_assertions(self, sample_data):
        """Example of poor data validation assertions."""
        prediction = sample_data["prediction"]

        # Poor data validation
        assert "match_id" in prediction
        assert "probabilities" in prediction
        assert prediction["confidence"] >= 0 and prediction["confidence"] <= 1

    def test_data_validation_improved_assertions(self, sample_data):
        """Example of improved data validation assertions."""
        prediction = sample_data["prediction"]

        # Improved data validation with structured approach
        required_fields = ["match_id", "predicted_outcome", "probabilities", "confidence", "model_version"]
        missing_fields = [field for field in required_fields if field not in prediction]

        assert not missing_fields, \
            f"Prediction missing required fields: {missing_fields}. " \
            f"Available fields: {list(prediction.keys())}"

        # Type validation
        assert isinstance(prediction["match_id"], int), \
            f"match_id should be int, got {type(prediction['match_id'])}"

        # Value range validation
        confidence = prediction["confidence"]
        assert 0 <= confidence <= 1, \
            f"Prediction confidence should be between 0 and 1, got {confidence}"

        # Probabilities validation
        probabilities = prediction["probabilities"]
        self._assert_probabilities_valid(probabilities)

    def _assert_probabilities_valid(self, probabilities):
        """Helper method for probabilities validation."""
        assert isinstance(probabilities, dict), \
            f"Probabilities should be dict, got {type(probabilities)}"

        required_outcomes = ["home_win", "draw", "away_win"]
        missing_outcomes = [outcome for outcome in required_outcomes if outcome not in probabilities]

        assert not missing_outcomes, \
            f"Probabilities missing required outcomes: {missing_outcomes}"

        # Probability sum validation
        total_prob = sum(probabilities.values())
        assert abs(total_prob - 1.0) < 1e-6, \
            f"Probabilities sum to {total_prob:.6f}, expected 1.0"

        # Individual probability validation
        for outcome, prob in probabilities.items():
            assert isinstance(prob, (int, float)), \
                f"Probability for {outcome} should be numeric, got {type(prob)}"
            assert 0 <= prob <= 1, \
                f"Probability for {outcome} should be between 0 and 1, got {prob}"

    def test_error_handling_poor_assertions(self):
        """Example of poor error handling assertions."""
        service = MockPredictionService(should_fail=True)
        features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
        features['match_id'] = 12345

        # Poor error handling assertion
        try:
            service.predict_match_outcome(features)
            assert False, "Expected exception"
        except Exception:
            pass

    def test_error_handling_improved_assertions(self):
        """Example of improved error handling assertions."""
        service = MockPredictionService(should_fail=True)
        features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
        features['match_id'] = 12345

        # Improved error handling assertion
        with pytest.raises(Exception) as exc_info:
            service.predict_match_outcome(features)

        # Validate exception properties
        exception_message = str(exc_info.value)
        assert "failed" in exception_message.lower(), \
            f"Expected exception message to contain 'failed', got: '{exception_message}'"

        # Validate exception type
        assert isinstance(exc_info.value, Exception), \
            f"Expected Exception type, got {type(exc_info.value)}"

    def test_multiple_measurements_poor_assertions(self):
        """Example of poor multiple measurements assertions."""
        service = MockPredictionService()
        response_times = []

        for i in range(5):
            features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
            features['match_id'] = 12340 + i

            start = time.time()
            service.predict_match_outcome(features)
            end = time.time()
            response_times.append((end - start) * 1000)

        # Poor multiple measurements assertions
        assert max(response_times) < 200
        assert sum(response_times) / len(response_times) < 100

    def test_multiple_measurements_improved_assertions(self):
        """Example of improved multiple measurements assertions."""
        service = MockPredictionService()
        response_times = []

        # Collect measurements with validation
        for i in range(5):
            features = FeatureFactory.generate_comprehensive_features(num_samples=1).iloc[0].to_dict()
            features['match_id'] = 12340 + i

            start_time = time.time()
            result = service.predict_match_outcome(features)
            end_time = time.time()

            # Validate each measurement
            assert end_time > start_time, f"Measurement {i}: end time should be after start time"
            response_time = (end_time - start_time) * 1000
            assert response_time > 0, f"Measurement {i}: response time should be positive"
            response_times.append(response_time)

        # Validate measurements collection
        assert len(response_times) == 5, \
            f"Expected 5 measurements, got {len(response_times)}"

        # Statistical analysis
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        std_dev = statistics.stdev(response_times)

        # Performance requirements with detailed analysis
        assert max_time < 200.0, \
            f"Maximum response time {max_time:.2f}ms exceeds 200ms limit. " \
            f"Response times: {response_times}"

        assert avg_time < 100.0, \
            f"Average response time {avg_time:.2f}ms exceeds 100ms limit. " \
            f"Stats: min={min_time:.2f}ms, max={max_time:.2f}ms, std={std_dev:.2f}ms"

        # Consistency validation
        consistency_threshold = avg_time * 0.5  # 50% variation
        max_deviation = max(abs(time - avg_time) for time in response_times)

        assert max_deviation <= consistency_threshold, \
            f"Response times inconsistent. Max deviation {max_deviation:.2f}ms " \
            f"exceeds threshold {consistency_threshold:.2f}ms. " \
            f"All times: {response_times}"

        # Performance tier assessment
        performance_tier = "excellent" if avg_time < 50 else "good" if avg_time < 100 else "acceptable"
        assert performance_tier in ["excellent", "good"], \
            f"Performance tier '{performance_tier}' not meeting minimum requirement of 'good'. " \
            f"Average time: {avg_time:.2f}ms"


class TestAssertionQualityGuidelines:
    """Guidelines for writing high-quality assertions."""

    def test_assertion_guideline_1_descriptive_messages(self):
        """Guideline 1: Use descriptive error messages."""
        value = 42

        # Poor
        # assert value == 100

        # Improved
        assert value == 100, f"Expected value to be 100, got {value}"

    def test_assertion_guideline_2_specific_validations(self):
        """Guideline 2: Use specific validation methods."""
        data = {"name": "test", "age": 25}

        # Poor
        # assert "name" in data and "age" in data

        # Improved
        required_fields = ["name", "age"]
        missing_fields = [field for field in required_fields if field not in data]
        assert not missing_fields, f"Data missing required fields: {missing_fields}"

    def test_assertion_guideline_3_range_validation(self):
        """Guideline 3: Validate ranges appropriately."""
        score = 0.85

        # Poor
        # assert score >= 0 and score <= 1

        # Improved
        assert 0 <= score <= 1, f"Score should be between 0 and 1, got {score}"

    def test_assertion_guideline_4_type_validation(self):
        """Guideline 4: Validate data types."""
        value = "hello"

        # Poor
        # assert type(value) == str

        # Improved
        assert isinstance(value, str), f"Expected string, got {type(value)}"

    def test_assertion_guideline_5_floating_point_comparison(self):
        """Guideline 5: Use proper floating-point comparison."""
        result = 1.0 / 3.0
        expected = 0.3333333333

        # Poor
        # assert result == expected

        # Improved
        import math
        assert math.isclose(result, expected, rel_tol=1e-9), \
            f"Values not close enough: {result} vs {expected}"

    def test_assertion_guideline_6_collection_validation(self):
        """Guideline 6: Validate collections properly."""
        list1 = [1, 2, 3]
        list2 = [3, 2, 1]

        # Poor
        # assert sorted(list1) == sorted(list2)

        # Improved
        assert set(list1) == set(list2), \
            f"Sets differ. In list1 only: {set(list1) - set(list2)}, " \
            f"In list2 only: {set(list2) - set(list1)}"