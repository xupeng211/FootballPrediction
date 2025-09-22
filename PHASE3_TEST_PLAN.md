# Phase 3: Data Modules Testing Plan (src/data/)

## Current Coverage Status
- src/data/__init__.py: 100.0% (2/2)
- src/data/collectors/__init__.py: 100.0% (5/5)
- src/data/collectors/base_collector.py: 17.6% (25/142)
- src/data/collectors/fixtures_collector.py: 13.8% (15/109)
- src/data/collectors/odds_collector.py: 11.8% (17/144)
- src/data/collectors/scores_collector.py: 20.2% (36/178)
- src/data/collectors/streaming_collector.py: 0.0% (0/123)
- src/data/features/__init__.py: 100.0% (3/3)
- src/data/features/examples.py: 0.0% (0/121)
- src/data/features/feature_definitions.py: 100.0% (35/35)
- src/data/features/feature_store.py: 19.7% (27/137)
- src/data/processing/__init__.py: 100.0% (3/3)
- src/data/processing/football_data_cleaner.py: 13.7% (25/183)
- src/data/processing/missing_data_handler.py: 19.4% (12/62)
- src/data/quality/__init__.py: 100.0% (6/6)
- src/data/quality/anomaly_detector.py: 10.8% (45/415)
- src/data/quality/data_quality_monitor.py: 12.2% (18/148)
- src/data/quality/exception_handler.py: 11.4% (22/193)
- src/data/quality/ge_prometheus_exporter.py: 13.5% (17/126)
- src/data/quality/great_expectations_config.py: 16.5% (18/109)
- src/data/storage/__init__.py: 100.0% (2/2)
- src/data/storage/data_lake_storage.py: 7.5% (24/318)

Overall data coverage: ~16.4%

## Goals for Phase 3
1. Increase coverage of base_collector.py to 50%+
2. Increase coverage of fixtures_collector.py to 50%+
3. Increase coverage of odds_collector.py to 50%+
4. Increase coverage of scores_collector.py to 50%+
5. Increase coverage of streaming_collector.py to 50%+
6. Increase coverage of data processing modules to 50%+
7. Increase coverage of data quality modules to 50%+
8. Reach 50%+ coverage for the entire src/data/ directory

## Detailed Module Plans

### 1. Collector Modules (Critical Priority)

#### src/data/collectors/base_collector.py (17.6% → 50%+)
Current issues:
- Only 25/142 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization with config
  - `_make_request()` - HTTP request handling
  - `_save_to_bronze_layer()` - Data storage
  - `_is_duplicate_record()` - Duplicate detection
  - `collect_data()` - Abstract collection method
  - `get_collection_result()` - Result retrieval
  - Error handling and retry mechanisms

Test approach:
- Create unit tests for initialization with different configurations
- Mock HTTP responses and test request handling
- Mock database storage and test data persistence
- Test error handling and retry mechanisms
- Test duplicate detection logic

Estimated tests needed: 20-25 new test cases

#### src/data/collectors/fixtures_collector.py (13.8% → 50%+)
Current issues:
- Only 15/109 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization
  - `collect_fixtures()` - Main fixture collection
  - `_generate_match_key()` - Match key generation
  - `_clean_fixture_data()` - Data cleaning
  - Error handling for API responses

Test approach:
- Create unit tests for initialization
- Mock API responses and test fixture collection
- Test data cleaning with various input formats
- Test match key generation with different inputs
- Test error handling for malformed data

Estimated tests needed: 15-20 new test cases

#### src/data/collectors/odds_collector.py (11.8% → 50%+)
Current issues:
- Only 17/144 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization
  - `collect_odds()` - Main odds collection
  - `_generate_odds_key()` - Odds key generation
  - `_clean_odds_data()` - Data cleaning

Test approach:
- Create unit tests for initialization
- Mock API responses and test odds collection
- Test data cleaning with various odds formats
- Test odds key generation with different inputs
- Test handling of different bookmaker formats

Estimated tests needed: 15-20 new test cases

#### src/data/collectors/scores_collector.py (20.2% → 50%+)
Current issues:
- Only 36/178 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization
  - `collect_live_scores()` - Live score collection
  - `collect_scores()` - Score collection
  - `_generate_event_key()` - Event key generation
  - `_clean_scores_data()` - Data cleaning
  - `_update_match_score()` - Score updating

Test approach:
- Create unit tests for initialization
- Mock API responses and test score collection
- Test live score updates
- Test data cleaning with various score formats
- Test match score updating logic

Estimated tests needed: 20-25 new test cases

#### src/data/collectors/streaming_collector.py (0.0% → 50%+)
Current issues:
- Completely untested (0/123 lines)
- Missing test coverage for all methods:
  - `__init__()` - Initialization
  - `initialize_kafka_producer()` - Kafka setup
  - `send_to_stream()` - Message sending
  - `collect_with_streaming()` - Streaming collection
  - Context manager methods

Test approach:
- Create comprehensive unit tests from scratch
- Mock Kafka producer and test streaming functionality
- Test message serialization and sending
- Test error handling and recovery
- Test context manager behavior

Estimated tests needed: 25-30 new test cases

### 2. Processing Modules (High Priority)

#### src/data/processing/football_data_cleaner.py (13.7% → 50%+)
Current issues:
- Only 25/183 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization
  - `clean_match_data()` - Match data cleaning
  - `clean_odds_data()` - Odds data cleaning
  - `validate_match_data()` - Data validation
  - `validate_odds_data()` - Odds validation

Test approach:
- Create unit tests for initialization
- Test data cleaning with various input formats
- Test validation with valid and invalid data
- Test error handling for corrupted data
- Test edge cases (empty data, missing fields)

Estimated tests needed: 20-25 new test cases

#### src/data/processing/missing_data_handler.py (19.4% → 50%+)
Current issues:
- Only 12/62 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization
  - `handle_missing_match_data()` - Missing match data
  - `handle_missing_odds_data()` - Missing odds data
  - `handle_missing_features()` - Missing features
  - `_get_historical_average()` - Historical averages

Test approach:
- Create unit tests for initialization
- Test missing data handling with various scenarios
- Test historical average calculation
- Test interpolation methods
- Test edge cases (no historical data)

Estimated tests needed: 15-20 new test cases

### 3. Quality Modules (High Priority)

#### src/data/quality/anomaly_detector.py (10.8% → 50%+)
Current issues:
- Only 45/415 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization
  - `detect_outliers_3sigma()` - 3-sigma outlier detection
  - `detect_outliers_iqr()` - IQR outlier detection
  - `detect_distribution_shift()` - Distribution shift
  - `detect_data_drift()` - Data drift detection
  - `detect_anomalies_isolation_forest()` - Isolation forest
  - `detect_anomalies_clustering()` - Clustering-based detection

Test approach:
- Create unit tests for initialization
- Test various anomaly detection algorithms
- Test with normal and anomalous data
- Test edge cases (empty data, uniform data)
- Test error handling

Estimated tests needed: 30-35 new test cases

#### src/data/quality/data_quality_monitor.py (12.2% → 50%+)
Current issues:
- Only 18/148 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization
  - `check_data_freshness()` - Freshness checks
  - `check_data_completeness()` - Completeness checks
  - `check_data_consistency()` - Consistency checks
  - `calculate_overall_quality_score()` - Quality scoring
  - `get_quality_trends()` - Trend analysis

Test approach:
- Create unit tests for initialization
- Mock database and test quality checks
- Test quality scoring with various data
- Test trend analysis
- Test error handling

Estimated tests needed: 20-25 new test cases

#### src/data/quality/great_expectations_config.py (16.5% → 50%+)
Current issues:
- Only 18/109 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization
  - `initialize_context()` - GE context setup
  - `create_expectation_suites()` - Expectation creation
  - `run_validation()` - Validation execution
  - `validate_all_tables()` - Table validation

Test approach:
- Create unit tests for initialization
- Mock GE context and test suite creation
- Test validation with different data scenarios
- Test error handling
- Test configuration management

Estimated tests needed: 15-20 new test cases

### 4. Storage Modules (Medium Priority)

#### src/data/storage/data_lake_storage.py (7.5% → 50%+)
Current issues:
- Only 24/318 lines covered
- Missing test coverage for core methods:
  - `__init__()` - Initialization
  - `initialize_storage()` - Storage setup
  - `store_data()` - Data storage
  - `retrieve_data()` - Data retrieval
  - `delete_data()` - Data deletion
  - `list_data_partitions()` - Partition listing
  - `get_storage_stats()` - Storage statistics

Test approach:
- Create unit tests for initialization
- Mock file system operations and test storage
- Test data serialization and deserialization
- Test partitioning logic
- Test error handling for storage operations

Estimated tests needed: 25-30 new test cases

## Implementation Strategy

### Timeline: 3-5 days

Day 1: Base collector and fixtures collector testing
- Create comprehensive test suites for base_collector.py and fixtures_collector.py
- Focus on HTTP request handling, data storage, and error handling
- Target: 50%+ coverage for both modules

Day 2: Odds and scores collector testing
- Create test suites for odds_collector.py and scores_collector.py
- Focus on data cleaning, key generation, and API integration
- Target: 50%+ coverage for both modules

Day 3: Streaming collector testing
- Create comprehensive test suite for streaming_collector.py from scratch
- Focus on Kafka integration, message handling, and error recovery
- Target: 50%+ coverage

Day 4: Processing and quality modules testing
- Create test suites for data processing and quality modules
- Focus on data cleaning, anomaly detection, and quality monitoring
- Target: 50%+ coverage for key modules

Day 5: Storage modules and integration
- Create test suite for data lake storage
- Test integration between all data modules
- Address any remaining coverage gaps
- Run full test suite and verify improvements

## Expected Outcomes

1. Increased coverage for src/data/ directory from ~16.4% to 50%+
2. Better data pipeline reliability and error handling
3. More robust data quality monitoring and anomaly detection
4. Improved documentation through test examples
5. Better integration between data collection, processing, and storage

## Success Metrics

- src/data/collectors/base_collector.py: ≥ 50% coverage
- src/data/collectors/fixtures_collector.py: ≥ 50% coverage
- src/data/collectors/odds_collector.py: ≥ 50% coverage
- src/data/collectors/scores_collector.py: ≥ 50% coverage
- src/data/collectors/streaming_collector.py: ≥ 50% coverage
- src/data/processing/football_data_cleaner.py: ≥ 50% coverage
- src/data/quality/anomaly_detector.py: ≥ 50% coverage
- src/data/storage/data_lake_storage.py: ≥ 50% coverage
- Overall src/data/ directory: ≥ 50% coverage
