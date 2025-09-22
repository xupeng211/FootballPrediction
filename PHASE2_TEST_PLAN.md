# Phase 2: Feature Modules Testing Plan (src/features/)

## Current Coverage Status
- src/features/__init__.py: 100.0% (5/5)
- src/features/entities.py: 78.9% (30/38)
- src/features/feature_calculator.py: 13.1% (23/175)
- src/features/feature_definitions.py: 72.7% (80/110)
- src/features/feature_store.py: 13.6% (25/184)

Overall features coverage: ~33.4%

## Goals for Phase 2
1. Increase coverage of feature_calculator.py to 50%+
2. Increase coverage of feature_store.py to 50%+
3. Maintain coverage for other feature modules
4. Reach 50%+ coverage for the entire src/features/ directory

## Detailed Module Plans

### 1. src/features/feature_calculator.py (13.1% → 50%+)

Current issues:
- Only 23/175 lines covered
- Missing test coverage for core classes:
  - `FeatureCalculator` - Main feature calculator
- Missing test coverage for core methods:
  - `__init__()` - Initialization with config
  - `add_feature_definition()` - Feature definition registration
  - `calculate_basic_features()` - Basic feature calculation
  - `calculate_rolling_features()` - Rolling window features
  - `calculate_statistical_features()` - Statistical features
  - `calculate_team_performance_features()` - Team performance metrics
  - `calculate_head_to_head_features()` - Head-to-head statistics
  - `calculate_form_features()` - Recent form metrics
  - `_validate_data()` - Data validation
  - `_normalize_feature()` - Feature normalization
  - `_aggregate_features()` - Feature aggregation
  - `batch_calculate_features()` - Batch feature calculation

Test approach:
- Create unit tests for initialization with different configurations
- Mock data inputs and test feature calculation methods
- Test error handling for invalid data
- Test feature normalization and aggregation
- Test batch processing scenarios

Estimated tests needed: 25-30 new test cases

### 2. src/features/feature_store.py (13.6% → 50%+)

Current issues:
- Only 25/184 lines covered
- Missing test coverage for core classes:
  - `FootballFeatureStore` - Main feature store
- Missing test coverage for core methods:
  - `__init__()` - Initialization with config
  - `_initialize_feast_store()` - Feast initialization
  - `get_entity_definitions()` - Entity definitions
  - `get_feature_view_definitions()` - Feature view definitions
  - `register_features()` - Feature registration
  - `get_online_features()` - Online feature retrieval
  - `get_historical_features()` - Historical feature retrieval
  - `push_features_to_online_store()` - Online store updates
  - `calculate_and_store_team_features()` - Team feature calculation
  - `calculate_and_store_match_features()` - Match feature calculation
  - `get_match_features_for_prediction()` - Prediction feature retrieval
  - `batch_calculate_features()` - Batch feature calculation

Test approach:
- Create unit tests for initialization with mocked Feast components
- Mock database sessions and test feature calculation
- Mock online/offline feature stores
- Test feature registration and retrieval
- Test error handling for missing features or data

Estimated tests needed: 30-35 new test cases

### 3. Maintain/Improve Other Modules

### src/features/entities.py (78.9% → 85%+)
- Already well-covered but can add edge case tests
- Test with unusual team/league names
- Test serialization/deserialization

### src/features/feature_definitions.py (72.7% → 80%+)
- Add tests for edge cases in feature definitions
- Test feature validation logic
- Test feature categorization

## Implementation Strategy

### Timeline: 3-5 days

Day 1-2: feature_calculator.py testing
- Create comprehensive test suite for feature calculator
- Focus on initialization, feature calculation, and error handling
- Target: 50%+ coverage

Day 2-3: feature_store.py testing
- Create test suite for feature store
- Focus on Feast integration, feature registration, and retrieval
- Target: 50%+ coverage

Day 3-4: entities.py and feature_definitions.py enhancement
- Add edge case tests for existing well-covered modules
- Improve overall coverage percentage

Day 4-5: Integration and refinement
- Ensure all feature modules work together correctly
- Address any coverage gaps
- Run full test suite and verify improvements

## Expected Outcomes

1. Increased coverage for src/features/ directory from ~33.4% to 50%+
2. Better integration between feature calculator and feature store
3. More robust feature engineering and storage capabilities
4. Improved documentation through test examples

## Success Metrics

- src/features/feature_calculator.py: ≥ 50% coverage
- src/features/feature_store.py: ≥ 50% coverage
- src/features/entities.py: ≥ 80% coverage
- src/features/feature_definitions.py: ≥ 75% coverage
- Overall src/features/ directory: ≥ 50% coverage
