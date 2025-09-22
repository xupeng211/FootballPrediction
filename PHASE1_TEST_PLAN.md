# Phase 1: Core Modules Testing Plan (src/models/)

## Current Coverage Status
- src/models/__init__.py: 100.0% (5/5)
- src/models/common_models.py: 78.9% (56/71)
- src/models/metrics_exporter.py: 23.7% (14/59)
- src/models/model_training.py: 14.4% (30/208)
- src/models/prediction_service.py: 22.9% (44/192)

Overall models coverage: ~30.6%

## Goals for Phase 1
1. Increase coverage of metrics_exporter.py to 50%+
2. Increase coverage of model_training.py to 50%+
3. Increase coverage of prediction_service.py to 50%+
4. Reach 50%+ coverage for the entire src/models/ directory

## Detailed Module Plans

### 1. src/models/metrics_exporter.py (23.7% → 50%+)

Current issues:
- Only 14/59 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization with different configs
  - `_get_metric_value()` - Metric value extraction
  - `_record_prediction_metrics()` - Recording prediction metrics
  - `_record_model_metrics()` - Recording model performance metrics
  - `_record_system_metrics()` - Recording system metrics
  - `export_metrics()` - Main export method
  - `get_metrics_summary()` - Summary statistics

Test approach:
- Create unit tests for initialization with different configurations
- Mock Prometheus collectors and test metric recording
- Test error handling scenarios
- Test metrics aggregation and export

Estimated tests needed: 15-20 new test cases

### 2. src/models/model_training.py (14.4% → 50%+)

Current issues:
- Only 30/208 lines covered
- Missing test coverage for core classes:
  - `BaselineModelTrainer` - Main trainer class
  - `ModelTrainingResult` - Training result dataclass
- Missing test coverage for core methods:
  - `__init__()` - Initialization with different configs
  - `calculate_match_result()` - Result calculation helper
  - `get_historical_matches()` - Data fetching
  - `prepare_training_data()` - Data preparation
  - `train_baseline_model()` - Main training method
  - `evaluate_model()` - Model evaluation
  - `save_model()` - Model persistence
  - `register_model()` - MLflow registration
  - `get_model_performance_summary()` - Performance reporting

Test approach:
- Create unit tests for initialization with mocked dependencies
- Mock database connections and test data fetching
- Mock MLflow client and test model registration
- Test various error scenarios (database errors, MLflow errors)
- Test different match result scenarios

Estimated tests needed: 25-30 new test cases

### 3. src/models/prediction_service.py (22.9% → 50%+)

Current issues:
- Only 44/192 lines covered
- Missing test coverage for core classes:
  - `PredictionResult` - Prediction result dataclass
  - `PredictionService` - Main prediction service
- Missing test coverage for core methods:
  - `__init__()` - Service initialization
  - `_load_model_from_mlflow()` - Model loading
  - `predict_match()` - Single match prediction
  - `batch_predict_matches()` - Batch prediction
  - `verify_prediction()` - Prediction verification
  - `_get_match_info()` - Match data fetching
  - `_prepare_features_for_prediction()` - Feature preparation
  - `_store_prediction()` - Prediction persistence
  - `get_model_accuracy()` - Accuracy calculation
  - `get_prediction_statistics()` - Statistics aggregation

Test approach:
- Create unit tests for service initialization with mocked dependencies
- Mock MLflow client and test model loading scenarios
- Mock database sessions and test prediction storage
- Mock feature store and test feature preparation
- Test various prediction scenarios (normal, error conditions)
- Test batch prediction with multiple matches
- Test prediction verification with different match outcomes

Estimated tests needed: 30-35 new test cases

## Implementation Strategy

### Timeline: 3-5 days

Day 1-2: metrics_exporter.py testing
- Create comprehensive test suite for metrics exporter
- Focus on initialization, metric recording, and export functionality
- Target: 50%+ coverage

Day 2-3: model_training.py testing
- Create test suite for model trainer
- Focus on data preparation, training, and MLflow integration
- Target: 50%+ coverage

Day 3-4: prediction_service.py testing
- Create test suite for prediction service
- Focus on prediction workflow, MLflow integration, and database operations
- Target: 50%+ coverage

Day 5: Integration and refinement
- Ensure all modules work together correctly
- Address any coverage gaps
- Run full test suite and verify improvements

## Expected Outcomes

1. Increased coverage for src/models/ directory from ~30.6% to 50%+
2. Better error handling and edge case coverage
3. Improved documentation through test examples
4. More robust and maintainable model components

## Success Metrics

- src/models/metrics_exporter.py: ≥ 50% coverage
- src/models/model_training.py: ≥ 50% coverage
- src/models/prediction_service.py: ≥ 50% coverage
- Overall src/models/ directory: ≥ 50% coverage
