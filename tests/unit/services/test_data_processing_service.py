from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from datetime import datetime
import asyncio

import pandas as pd
import pytest

from src.services.data_processing import DataProcessingService


class DummyCleaner:
    async def clean_match_data(self, raw_data):
        df = pd.DataFrame([raw_data])
        return df.iloc[0].to_dict()

    async def clean_odds_data(self, odds_list):
        return odds_list

    def _validate_score(self, value):
        return value or 0

    def _standardize_match_status(self, status):
        return status or "scheduled"


class DummyMissingHandler:
    async def handle_missing_match_data(self, data):
        return data

    async def handle_missing_features(self, match_id, features_df):
        return features_df.fillna(0)


class DummyDataLake:
    def __init__(self):
        self.saved_payloads = []
        self.raise_on_save = False

    async def save_historical_data(self, table_name, data):
        if self.raise_on_save:
            raise RuntimeError("save failed")
        self.saved_payloads.append((table_name, data))


class DummyQualityValidator:
    async def validate_match_data(self, data):
        return {"valid": True, "score": 0.95, "issues": []}

    async def validate_odds_data(self, data):
        return {"valid": True, "score": 0.90, "issues": []}

    async def validate_features_data(self, features_df):
        return {"valid": True, "score": 0.88, "issues": []}


class DummyRedisManager:
    def __init__(self):
        self.cache = {}

    async def get(self, key):
        return self.cache.get(key)

    async def set(self, key, value, ttl=None):
        self.cache[key] = value

    async def delete(self, key):
        if key in self.cache:
            del self.cache[key]


@dataclass
class RawMatchStub:
    id: int
    raw_data: dict
    data_source: str
    processed: bool = False

    def mark_processed(self):
        self.processed = True


class FakeQuery:
    def __init__(self, items):
        self._items = items

    def filter(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self, matches):
        self._matches = matches
        self.committed = False
        self.rolled_back = False

    def query(self, model):
        return FakeQuery(self._matches)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeSessionCtx:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeDBManager:
    def __init__(self, session):
        self._session = session

    def get_session(self):
        return FakeSessionCtx(self._session)


class TestDataProcessingServiceBasic:
    """Test basic DataProcessingService initialization and configuration"""

    @pytest.fixture
    def data_processing_service(self):
        """Create a DataProcessingService instance with mocked dependencies"""
        service = DataProcessingService()
        service.data_cleaner = DummyCleaner()
        service.missing_handler = DummyMissingHandler()
        service.quality_validator = DummyQualityValidator()
        service.data_lake = DummyDataLake()
        service.redis_manager = DummyRedisManager()
        service.db_manager = FakeDBManager(FakeSession([]))
        return service

    def test_service_initialization(self, data_processing_service):
        """Test that DataProcessingService initializes correctly"""
        assert data_processing_service is not None
        assert hasattr(data_processing_service, 'data_cleaner')
        assert hasattr(data_processing_service, 'missing_handler')
        assert hasattr(data_processing_service, 'quality_validator')
        assert hasattr(data_processing_service, 'data_lake')
        assert hasattr(data_processing_service, 'redis_manager')
        assert hasattr(data_processing_service, 'db_manager')


class TestDataProcessingServiceRawMatch:
    """Test raw match data processing functionality"""

    @pytest.fixture
    def data_processing_service(self):
        service = DataProcessingService()
        service.data_cleaner = DummyCleaner()
        service.missing_handler = DummyMissingHandler()
        service.quality_validator = DummyQualityValidator()
        service.data_lake = DummyDataLake()
        service.redis_manager = DummyRedisManager()
        service.db_manager = FakeDBManager(FakeSession([]))
        return service

    @pytest.fixture
    def sample_raw_match_data(self):
        return {
            "match_id": "12345",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2023-09-29T15:00:00Z",
            "status": "finished",
            "competition": "Premier League"
        }

    @pytest.mark.asyncio
    async def test_process_raw_match_data_success(self, data_processing_service, sample_raw_match_data):
        """Test successful processing of raw match data"""
        # Mock database session
        mock_session = AsyncMock()
        data_processing_service.db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # No existing record
        mock_session.execute.return_value = mock_result

        result = await data_processing_service.process_raw_match_data(sample_raw_match_data)

        # Verify processing was successful
        assert result is not None
        assert result.get("processed") is True
        assert result.get("match_id") == "12345"

    @pytest.mark.asyncio
    async def test_process_raw_match_data_with_missing_fields(self, data_processing_service):
        """Test processing raw match data with missing fields"""
        incomplete_data = {
            "match_id": "12346",
            "home_team": "Team C",
            # Missing away_team and other required fields
        }

        mock_session = AsyncMock()
        data_processing_service.db_manager.get_session.return_value.__enter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await data_processing_service.process_raw_match_data(incomplete_data)

        # Verify missing data handling
        assert result is not None
        assert result.get("match_id") == "12346"

    @pytest.mark.asyncio
    async def test_process_raw_match_data_database_error(self, data_processing_service, sample_raw_match_data):
        """Test handling of database errors during match data processing"""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database connection failed")
        data_processing_service.db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Should handle database errors gracefully
        result = await data_processing_service.process_raw_match_data(sample_raw_match_data)

        # Verify error handling
        assert result is not None


class TestDataProcessingServiceOdds:
    """Test odds data processing functionality"""

    @pytest.fixture
    def data_processing_service(self):
        service = DataProcessingService()
        service.data_cleaner = DummyCleaner()
        service.missing_handler = DummyMissingHandler()
        service.quality_validator = DummyQualityValidator()
        service.data_lake = DummyDataLake()
        service.redis_manager = DummyRedisManager()
        service.db_manager = FakeDBManager(FakeSession([]))
        return service

    @pytest.fixture
    def sample_odds_data(self):
        return [
            {
                "match_id": "12345",
                "bookmaker": "Bet365",
                "home_win": 2.10,
                "draw": 3.40,
                "away_win": 3.80,
                "timestamp": "2023-09-29T14:00:00Z"
            },
            {
                "match_id": "12345",
                "bookmaker": "William Hill",
                "home_win": 2.05,
                "draw": 3.50,
                "away_win": 3.90,
                "timestamp": "2023-09-29T14:00:00Z"
            }
        ]

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_success(self, data_processing_service, sample_odds_data):
        """Test successful processing of raw odds data"""
        mock_session = AsyncMock()
        data_processing_service.db_manager.get_session.return_value.__enter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await data_processing_service.process_raw_odds_data(sample_odds_data)

        # Verify odds processing was successful
        assert result is not None
        assert result.get("processed_count") == 2
        assert len(result.get("odds", [])) == 2

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_with_invalid_values(self, data_processing_service):
        """Test processing odds data with invalid values"""
        invalid_odds_data = [
            {
                "match_id": "12347",
                "bookmaker": "Invalid Bookmaker",
                "home_win": -1.0,  # Invalid negative odds
                "draw": 0,        # Invalid zero odds
                "away_win": "invalid",  # Invalid non-numeric odds
                "timestamp": "2023-09-29T14:00:00Z"
            }
        ]

        mock_session = AsyncMock()
        data_processing_service.db_manager.get_session.return_value.__enter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await data_processing_service.process_raw_odds_data(invalid_odds_data)

        # Verify invalid odds handling
        assert result is not None


class TestDataProcessingServiceFeatures:
    """Test features data processing functionality"""

    @pytest.fixture
    def data_processing_service(self):
        service = DataProcessingService()
        service.data_cleaner = DummyCleaner()
        service.missing_handler = DummyMissingHandler()
        service.quality_validator = DummyQualityValidator()
        service.data_lake = DummyDataLake()
        service.redis_manager = DummyRedisManager()
        service.db_manager = FakeDBManager(FakeSession([]))
        return service

    @pytest.mark.asyncio
    async def test_process_features_data_with_dataframe(self, data_processing_service):
        """Test processing features data with pandas DataFrame"""
        features = pd.DataFrame([
            {"stat_a": 1.0, "stat_b": None, "stat_c": 5.5},
            {"stat_a": 2.0, "stat_b": 3.0, "stat_c": None}
        ])

        processed = await data_processing_service.process_features_data(match_id=123, features_df=features)

        # Verify features processing and missing data handling
        assert isinstance(processed, pd.DataFrame)
        assert processed.shape[0] == 2
        assert processed.isnull().sum().sum() == 0  # No missing values after processing

    @pytest.mark.asyncio
    async def test_process_features_data_with_dict(self, data_processing_service):
        """Test processing features data with dictionary input"""
        features = {
            "home_form": 3.0,
            "away_form": 1.5,
            "home_goals_scored": 10,
            "away_goals_conceded": 8
        }

        processed = await data_processing_service.process_features_data(match_id=124, features_dict=features)

        # Verify features processing
        assert processed is not None
        assert isinstance(processed, dict)

    @pytest.mark.asyncio
    async def test_process_features_data_empty_input(self, data_processing_service):
        """Test processing features data with empty input"""
        empty_features = pd.DataFrame()

        processed = await data_processing_service.process_features_data(match_id=125, features_df=empty_features)

        # Verify empty input handling
        assert processed is not None


class TestDataProcessingServiceQualityValidation:
    """Test data quality validation functionality"""

    @pytest.fixture
    def data_processing_service(self):
        service = DataProcessingService()
        service.data_cleaner = DummyCleaner()
        service.missing_handler = DummyMissingHandler()
        service.quality_validator = DummyQualityValidator()
        service.data_lake = DummyDataLake()
        service.redis_manager = DummyRedisManager()
        service.db_manager = FakeDBManager(FakeSession([]))
        return service

    @pytest.mark.asyncio
    async def test_validate_data_quality_success(self, data_processing_service):
        """Test successful data quality validation"""
        data = {"match_id": "12345", "home_team": "Team A", "away_team": "Team B"}

        result = await data_processing_service.validate_data_quality(data, "match")

        # Verify quality validation
        assert result is not None
        assert result.get("valid") is True
        assert result.get("score") > 0.8

    @pytest.mark.asyncio
    async def test_validate_data_quality_failure(self, data_processing_service):
        """Test data quality validation failure"""
        # Mock quality validator to return failure
        data_processing_service.quality_validator.validate_match_data = AsyncMock(
            return_value={"valid": False, "score": 0.3, "issues": ["Missing required fields"]}
        )

        data = {"match_id": "", "home_team": "", "away_team": ""}

        result = await data_processing_service.validate_data_quality(data, "match")

        # Verify quality validation failure handling
        assert result is not None
        assert result.get("valid") is False
        assert len(result.get("issues", [])) > 0

    @pytest.mark.asyncio
    async def test_validate_data_quality_with_unknown_type(self, data_processing_service):
        """Test data quality validation with unknown data type"""
        data = {"some_data": "value"}

        result = await data_processing_service.validate_data_quality(data, "unknown_type")

        # Verify unknown type handling
        assert result is not None


class TestDataProcessingServiceBatch:
    """Test batch processing functionality"""

    @pytest.fixture
    def data_processing_service(self):
        service = DataProcessingService()
        service.data_cleaner = DummyCleaner()
        service.missing_handler = DummyMissingHandler()
        service.quality_validator = DummyQualityValidator()
        service.data_lake = DummyDataLake()
        service.redis_manager = DummyRedisManager()
        service.db_manager = FakeDBManager(FakeSession([]))
        return service

    @pytest.mark.asyncio
    async def test_process_batch_matches(self, data_processing_service):
        """Test batch processing of matches"""
        batch_data = [
            {"match_id": "001", "home_team": "Team A", "away_team": "Team B"},
            {"match_id": "002", "home_team": "Team C", "away_team": "Team D"},
            {"match_id": "003", "home_team": "Team E", "away_team": "Team F"}
        ]

        results = await data_processing_service.process_batch_matches(batch_data, batch_size=2)

        # Verify batch processing
        assert len(results) == 3
        assert all(result.get("processed") for result in results)

    @pytest.mark.asyncio
    async def test_process_batch_matches_empty(self, data_processing_service):
        """Test batch processing with empty input"""
        results = await data_processing_service.process_batch_matches([], batch_size=10)

        # Verify empty batch handling
        assert results == []

    @pytest.mark.asyncio
    async def test_process_batch_matches_with_errors(self, data_processing_service):
        """Test batch processing with some errors"""
        batch_data = [
            {"match_id": "001", "home_team": "Team A", "away_team": "Team B"},
            {"invalid_data": "missing_required_fields"},
            {"match_id": "003", "home_team": "Team E", "away_team": "Team F"}
        ]

        results = await data_processing_service.process_batch_matches(batch_data, batch_size=2)

        # Verify batch processing with errors
        assert len(results) == 3


class TestDataProcessingServiceETL:
    """Test ETL pipeline functionality"""

    @pytest.fixture
    def data_processing_service(self):
        service = DataProcessingService()
        service.data_cleaner = DummyCleaner()
        service.missing_handler = DummyMissingHandler()
        service.quality_validator = DummyQualityValidator()
        service.data_lake = DummyDataLake()
        service.redis_manager = DummyRedisManager()
        service.db_manager = FakeDBManager(FakeSession([]))
        return service

    @pytest.mark.asyncio
    async def test_run_etl_pipeline_success(self, data_processing_service):
        """Test successful ETL pipeline execution"""
        pipeline_config = {
            "source": "bronze",
            "target": "silver",
            "data_type": "matches",
            "batch_size": 100
        }

        result = await data_processing_service.run_etl_pipeline(pipeline_config)

        # Verify ETL pipeline execution
        assert result is not None
        assert result.get("status") == "success"
        assert result.get("processed_count") >= 0

    @pytest.mark.asyncio
    async def test_run_etl_pipeline_with_invalid_config(self, data_processing_service):
        """Test ETL pipeline with invalid configuration"""
        invalid_config = {
            "source": "invalid_source",
            "target": "silver",
            "data_type": "matches"
        }

        result = await data_processing_service.run_etl_pipeline(invalid_config)

        # Verify invalid config handling
        assert result is not None
        assert result.get("status") in ["error", "partial_success"]

    @pytest.mark.asyncio
    async def test_run_etl_pipeline_data_lake_error(self, data_processing_service):
        """Test ETL pipeline with data lake storage error"""
        # Mock data lake to raise error
        data_processing_service.data_lake = DummyDataLake()
        data_processing_service.data_lake.raise_on_save = True

        pipeline_config = {
            "source": "bronze",
            "target": "silver",
            "data_type": "matches",
            "batch_size": 10
        }

        result = await data_processing_service.run_etl_pipeline(pipeline_config)

        # Verify data lake error handling
        assert result is not None


class TestDataProcessingServiceCaching:
    """Test caching functionality"""

    @pytest.fixture
    def data_processing_service(self):
        service = DataProcessingService()
        service.data_cleaner = DummyCleaner()
        service.missing_handler = DummyMissingHandler()
        service.quality_validator = DummyQualityValidator()
        service.data_lake = DummyDataLake()
        service.redis_manager = DummyRedisManager()
        service.db_manager = FakeDBManager(FakeSession([]))
        return service

    @pytest.mark.asyncio
    async def test_cache_processed_data(self, data_processing_service):
        """Test caching of processed data"""
        data_key = "processed_match_12345"
        processed_data = {"match_id": "12345", "processed": True, "timestamp": datetime.now().isoformat()}

        await data_processing_service.cache_processed_data(data_key, processed_data)

        # Verify caching
        cached_data = await data_processing_service.redis_manager.get(data_key)
        assert cached_data is not None

    @pytest.mark.asyncio
    async def test_get_cached_data(self, data_processing_service):
        """Test retrieval of cached data"""
        data_key = "processed_match_12346"
        cached_data = {"match_id": "12346", "processed": True}

        # Pre-populate cache
        await data_processing_service.redis_manager.set(data_key, cached_data)

        retrieved_data = await data_processing_service.get_cached_data(data_key)

        # Verify cache retrieval
        assert retrieved_data is not None
        assert retrieved_data.get("match_id") == "12346"

    @pytest.mark.asyncio
    async def test_cache_miss(self, data_processing_service):
        """Test cache miss scenario"""
        data_key = "nonexistent_key"

        result = await data_processing_service.get_cached_data(data_key)

        # Verify cache miss handling
        assert result is None


class TestDataProcessingServiceErrorHandling:
    """Test comprehensive error handling"""

    @pytest.fixture
    def data_processing_service(self):
        service = DataProcessingService()
        service.data_cleaner = DummyCleaner()
        service.missing_handler = DummyMissingHandler()
        service.quality_validator = DummyQualityValidator()
        service.data_lake = DummyDataLake()
        service.redis_manager = DummyRedisManager()
        service.db_manager = FakeDBManager(FakeSession([]))
        return service

    @pytest.mark.asyncio
    async def test_handle_processing_error(self, data_processing_service):
        """Test handling of processing errors"""
        error = Exception("Processing failed")
        context = {"match_id": "12345", "operation": "data_processing"}

        error_info = await data_processing_service.handle_processing_error(error, context)

        # Verify error handling
        assert error_info is not None
        assert error_info.get("error_type") == "ProcessingError"
        assert error_info.get("context") == context

    @pytest.mark.asyncio
    async def test_handle_database_connection_error(self, data_processing_service):
        """Test handling of database connection errors"""
        # Mock database manager to raise connection error
        data_processing_service.db_manager.get_session.side_effect = Exception("Connection failed")

        try:
            await data_processing_service.process_raw_match_data({})
        except Exception as e:
            # Verify database connection error handling
            assert "Connection failed" in str(e)

    @pytest.mark.asyncio
    async def test_handle_data_validation_error(self, data_processing_service):
        """Test handling of data validation errors"""
        # Mock quality validator to raise validation error
        data_processing_service.quality_validator.validate_match_data = AsyncMock(
            side_effect = Exception("Validation failed")
        )

        result = await data_processing_service.validate_data_quality({}, "match")

        # Verify validation error handling
        assert result is not None


class TestDataProcessingServiceIntegration:
    """Test integration scenarios"""

    @pytest.fixture
    def data_processing_service(self):
        service = DataProcessingService()
        service.data_cleaner = DummyCleaner()
        service.missing_handler = DummyMissingHandler()
        service.quality_validator = DummyQualityValidator()
        service.data_lake = DummyDataLake()
        service.redis_manager = DummyRedisManager()
        service.db_manager = FakeDBManager(FakeSession([]))
        return service

    @pytest.mark.asyncio
    async def test_end_to_end_match_processing(self, data_processing_service):
        """Test end-to-end match processing pipeline"""
        raw_match = {
            "match_id": "12345",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2023-09-29T15:00:00Z",
            "status": "finished"
        }

        # Process raw match data
        processed_match = await data_processing_service.process_raw_match_data(raw_match)

        # Cache the processed data
        await data_processing_service.cache_processed_data(
            f"processed_match_{raw_match['match_id']}",
            processed_match
        )

        # Retrieve cached data
        cached_match = await data_processing_service.get_cached_data(
            f"processed_match_{raw_match['match_id']}"
        )

        # Verify end-to-end processing
        assert processed_match is not None
        assert cached_match is not None
        assert cached_match.get("match_id") == raw_match["match_id"]

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, data_processing_service):
        """Test concurrent data processing"""
        async def process_single_match(match_id):
            match_data = {
                "match_id": match_id,
                "home_team": f"Team {match_id}",
                "away_team": f"Opponent {match_id}",
                "home_score": 1,
                "away_score": 0,
                "match_date": "2023-09-29T15:00:00Z",
                "status": "finished"
            }
            return await data_processing_service.process_raw_match_data(match_data)

        # Process multiple matches concurrently
        tasks = [process_single_match(f"match_{i}") for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify concurrent processing
        assert len(results) == 5
        assert all(result is not None for result in results if not isinstance(result, Exception))


# Legacy test functions maintained for compatibility
@pytest.mark.asyncio
async def test_process_raw_matches_bronze_to_silver_success():
    service = DataProcessingService()
    service.data_cleaner = DummyCleaner()
    service.missing_handler = DummyMissingHandler()
    service.data_lake = DummyDataLake()

    raw_matches = [
        RawMatchStub(
            id=1,
            raw_data={
                "external_match_id": "m1",
                "home_team_id": 10,
                "away_team_id": 20,
            },
            data_source="api",
        ),
        RawMatchStub(
            id=2,
            raw_data={
                "external_match_id": "m2",
                "home_team_id": 30,
                "away_team_id": 40,
            },
            data_source="api",
        ),
    ]

    session = FakeSession(raw_matches)
    service.db_manager = FakeDBManager(session)

    processed_count = await service._process_raw_matches_bronze_to_silver(batch_size=10)

    assert processed_count == 2
    assert session.committed is True
    for stub in raw_matches:
        assert stub.processed is True
    assert service.data_lake.saved_payloads
    table_name, payload = service.data_lake.saved_payloads[0]
    assert table_name == "processed_matches"
    assert payload[0]["bronze_id"] == 1
    assert payload[1]["bronze_id"] == 2


@pytest.mark.asyncio
async def test_process_raw_matches_bronze_to_silver_failure_triggers_rollback():
    service = DataProcessingService()
    service.data_cleaner = DummyCleaner()
    service.missing_handler = DummyMissingHandler()
    failing_data_lake = DummyDataLake()
    failing_data_lake.raise_on_save = True
    service.data_lake = failing_data_lake

    raw_matches = [
        RawMatchStub(
            id=99,
            raw_data={
                "external_match_id": "m99",
                "home_team_id": 50,
                "away_team_id": 60,
            },
            data_source="feed",
        )
    ]

    session = FakeSession(raw_matches)
    service.db_manager = FakeDBManager(session)

    result = await service._process_raw_matches_bronze_to_silver(batch_size=1)

    assert result == 1
    assert session.committed is False
    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_process_features_data_with_dataframe():
    service = DataProcessingService()
    service.missing_handler = DummyMissingHandler()

    features = pd.DataFrame(
        [
            {"stat_a": 1.0, "stat_b": None},
        ]
    )

    processed = await service.process_features_data(match_id=123, features_df=features)

    assert isinstance(processed, pd.DataFrame)
    assert processed.loc[0, "stat_b"] == 0
