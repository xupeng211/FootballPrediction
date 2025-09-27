#!/usr/bin/env python3
"""
Unit tests for features API module.

Tests for src/api/features.py module functions and endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from src.api.features import (
    get_match_features,
    get_team_features,
    calculate_match_features,
    calculate_team_features,
    batch_calculate_features,
    get_historical_features,
    features_health_check
)


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_match():
    """Mock match data."""
    match = MagicMock()
    match.id = 1
    match.home_team_id = 1
    match.away_team_id = 2
    match.match_date = datetime.now()
    match.status = "scheduled"
    return match


@pytest.fixture
def mock_team():
    """Mock team data."""
    team = MagicMock()
    team.id = 1
    team.name = "Test Team"
    team.league = "Test League"
    return team


@pytest.fixture
def mock_feature_store():
    """Mock feature store."""
    store = AsyncMock()
    store.get_match_features_for_prediction = AsyncMock(return_value={
        "home_form": 7.5,
        "away_form": 6.8,
        "recent_goals": [2, 1, 3, 0, 2]
    })

    # Mock for get_online_features - need to return proper data structure
    mock_online_features = MagicMock()
    mock_online_features.empty = False
    # Mock to_dict() for regular calls
    mock_online_features.to_dict.return_value = {"team_recent_performance:recent_5_wins": 3}
    # Mock to_dict("records") for the specific call
    def mock_to_dict_records(format):
        if format == "records":
            return [{"team_recent_performance:recent_5_wins": 3}]
        return {"team_recent_performance:recent_5_wins": 3}
    mock_online_features.to_dict.side_effect = mock_to_dict_records
    store.get_online_features = AsyncMock(return_value=mock_online_features)

    store.calculate_and_store_match_features = AsyncMock(return_value=True)
    store.calculate_and_store_team_features = AsyncMock(return_value=True)
    store.batch_calculate_features = AsyncMock(return_value={"processed": 5, "success": True})
    store.get_historical_features = AsyncMock(return_value=MagicMock())
    store.get_historical_features.return_value.to_dict.return_value = {"feature1": [1, 2, 3]}
    store.get_historical_features.return_value.columns = ["feature1"]
    store.get_historical_features.return_value.__len__ = MagicMock(return_value=3)
    return store


@pytest.fixture
def mock_feature_calculator():
    """Mock feature calculator."""
    calculator = AsyncMock()
    calculator.calculate_all_match_features = AsyncMock(return_value=MagicMock())
    calculator.calculate_all_match_features.return_value.to_dict.return_value = {"expected_goals": 2.5}
    calculator.calculate_all_team_features = AsyncMock(return_value=MagicMock())
    calculator.calculate_all_team_features.return_value.to_dict.return_value = {"attack_strength": 8.2}
    return calculator


class TestGetMatchFeatures:
    """Test cases for get_match_features function."""

    @pytest.mark.asyncio
    async def test_get_match_features_success(self, mock_session, mock_match, mock_feature_store):
        """Test successful match features retrieval."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        with patch('src.api.features.feature_store', mock_feature_store):
            # Execute function directly with session parameter
            result = await get_match_features(1, include_raw=False, session=mock_session)

            # Verify result
            assert result["success"] is True
            assert "data" in result
            assert "match_info" in result["data"]
            assert result["data"]["match_info"]["match_id"] == 1
            assert "features" in result["data"]

    @pytest.mark.asyncio
    async def test_get_match_features_with_raw_data(self, mock_session, mock_match, mock_feature_store, mock_feature_calculator):
        """Test match features retrieval with raw data included."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        with patch('src.api.features.feature_store', mock_feature_store), \
             patch('src.api.features.feature_calculator', mock_feature_calculator):
            # Execute function directly with session parameter
            result = await get_match_features(1, include_raw=True, session=mock_session)

            # Verify result
            assert result["success"] is True
            assert "raw_features" in result["data"]

    @pytest.mark.asyncio
    async def test_get_match_features_not_found(self, mock_session):
        """Test match features retrieval when match not found."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute function and expect exception
        with pytest.raises(Exception):
            await get_match_features(999, include_raw=False, session=mock_session)

    @pytest.mark.asyncio
    async def test_get_match_features_feature_store_error(self, mock_session, mock_match):
        """Test match features retrieval with feature store error."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        with patch('src.api.features.feature_store', None):
            # Execute function and expect exception
            with pytest.raises(Exception):
                await get_match_features(1, include_raw=False, session=mock_session)


class TestGetTeamFeatures:
    """Test cases for get_team_features function."""

    @pytest.mark.asyncio
    async def test_get_team_features_success(self, mock_session, mock_team, mock_feature_store):
        """Test successful team features retrieval."""
        from datetime import datetime

        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_team
        mock_session.execute.return_value = mock_result

        with patch('src.api.features.feature_store', mock_feature_store):
            # Execute function directly with session parameter and datetime
            result = await get_team_features(1, datetime.now(), False, session=mock_session)

            # Verify result
            assert result["success"] is True
            assert result["data"]["team_info"]["team_id"] == 1
            assert "calculation_date" in result["data"]
            assert "features" in result["data"]

    @pytest.mark.asyncio
    async def test_get_team_features_not_found(self, mock_session):
        """Test team features retrieval when team not found."""
        from datetime import datetime

        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute function and expect exception
        with pytest.raises(Exception):
            await get_team_features(999, datetime.now(), False, session=mock_session)


class TestCalculateMatchFeatures:
    """Test cases for calculate_match_features function."""

    @pytest.mark.asyncio
    async def test_calculate_match_features_success(self, mock_session, mock_match, mock_feature_calculator):
        """Test successful match features calculation."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        with patch('src.api.features.feature_store', mock_feature_calculator):
            # Execute function directly with session parameter
            result = await calculate_match_features(1, force_recalculate=False, session=mock_session)

            # Verify result
            assert result["success"] is True
            assert result["data"]["match_id"] == 1
            assert "match_features_stored" in result["data"]

    @pytest.mark.asyncio
    async def test_calculate_match_features_match_not_found(self, mock_session):
        """Test match features calculation when match not found."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute function and expect exception
        with pytest.raises(Exception):
            await calculate_match_features(999, force_recalculate=False, session=mock_session)


class TestCalculateTeamFeatures:
    """Test cases for calculate_team_features function."""

    @pytest.mark.asyncio
    async def test_calculate_team_features_success(self, mock_session, mock_team, mock_feature_calculator):
        """Test successful team features calculation."""
        from datetime import datetime

        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_team
        mock_session.execute.return_value = mock_result

        with patch('src.api.features.feature_store', mock_feature_calculator):
            # Execute function directly with session parameter and datetime
            result = await calculate_team_features(1, datetime.now(), session=mock_session)

            # Verify result
            assert result["success"] is True
            assert result["data"]["team_id"] == 1
            assert "features_stored" in result["data"]


class TestBatchCalculateFeatures:
    """Test cases for batch_calculate_features function."""

    @pytest.mark.asyncio
    async def test_batch_calculate_features_success(self, mock_session, mock_feature_calculator):
        """Test successful batch features calculation."""
        from datetime import datetime

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 7)

        with patch('src.api.features.feature_store', mock_feature_calculator):
            # Execute function directly with session parameter
            result = await batch_calculate_features(start_date, end_date, session=mock_session)

            # Verify result
            assert result["success"] is True
            assert "date_range" in result["data"]
            assert "statistics" in result["data"]

    @pytest.mark.asyncio
    async def test_batch_calculate_features_empty_request(self, mock_session):
        """Test batch features calculation with invalid date range."""
        from datetime import datetime

        start_date = datetime(2024, 1, 7)
        end_date = datetime(2024, 1, 1)  # End before start

        # Execute function and expect exception
        with pytest.raises(Exception):
            await batch_calculate_features(start_date, end_date, session=mock_session)


class TestGetHistoricalFeatures:
    """Test cases for get_historical_features function."""

    @pytest.mark.asyncio
    async def test_get_historical_features_success(self, mock_session, mock_feature_store):
        """Test successful historical features retrieval."""
        # Setup mocks
        mock_match = MagicMock()
        mock_match.id = 1
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.match_time = datetime.now()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        with patch('src.api.features.feature_store', mock_feature_store):
            # Execute function directly with session parameter
            result = await get_historical_features(1, ["feature1", "feature2"], session=mock_session)

            # Verify result
            assert result["success"] is True
            assert result["data"]["match_id"] == 1
            assert "features" in result["data"]
            assert "feature_refs" in result["data"]

    @pytest.mark.asyncio
    async def test_get_historical_features_no_results(self, mock_session, mock_feature_store):
        """Test historical features retrieval when match not found."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch('src.api.features.feature_store', mock_feature_store):
            # Execute function and expect exception
            with pytest.raises(Exception):
                await get_historical_features(999, ["feature1", "feature2"], session=mock_session)


class TestFeaturesHealthCheck:
    """Test cases for features_health_check function."""

    @pytest.mark.asyncio
    async def test_features_health_check_healthy(self, mock_feature_store, mock_feature_calculator):
        """Test features health check when all services are healthy."""
        with patch('src.api.features.feature_store', mock_feature_store), \
             patch('src.api.features.feature_calculator', mock_feature_calculator):
            # Execute function
            result = await features_health_check()

            # Verify result
            assert result["status"] == "healthy"
            assert result["components"]["feature_store"] is True
            assert result["components"]["feature_calculator"] is True

    @pytest.mark.asyncio
    async def test_features_health_check_store_unavailable(self):
        """Test features health check when feature store is unavailable."""
        with patch('src.api.features.feature_store', None), \
             patch('src.api.features.feature_calculator', MagicMock()):
            # Execute function
            result = await features_health_check()

            # Verify result
            assert result["status"] == "unhealthy"
            assert result["components"]["feature_store"] is False

    @pytest.mark.asyncio
    async def test_features_health_check_calculator_unavailable(self):
        """Test features health check when feature calculator is unavailable."""
        with patch('src.api.features.feature_store', MagicMock()), \
             patch('src.api.features.feature_calculator', None):
            # Execute function
            result = await features_health_check()

            # Verify result
            assert result["status"] == "unhealthy"
            assert result["components"]["feature_calculator"] is False

    @pytest.mark.asyncio
    async def test_features_health_check_both_unavailable(self):
        """Test features health check when both services are unavailable."""
        with patch('src.api.features.feature_store', None), \
             patch('src.api.features.feature_calculator', None):
            # Execute function
            result = await features_health_check()

            # Verify result
            assert result["status"] == "unhealthy"
            assert result["components"]["feature_store"] is False
            assert result["components"]["feature_calculator"] is False


class TestFeaturesAPIModule:
    """Test cases for features API module imports and configuration."""

    def test_module_imports(self):
        """Test that the module can be imported successfully."""
        from src.api import features
        assert hasattr(features, 'get_match_features')
        assert hasattr(features, 'get_team_features')
        assert hasattr(features, 'calculate_match_features')
        assert hasattr(features, 'calculate_team_features')
        assert hasattr(features, 'batch_calculate_features')
        assert hasattr(features, 'get_historical_features')
        assert hasattr(features, 'features_health_check')
        assert hasattr(features, 'router')

    def test_router_configuration(self):
        """Test that the router is properly configured."""
        from src.api import features
        assert features.router is not None
        assert features.router.prefix == "/features"
        assert "features" in features.router.tags

    def test_logger_exists(self):
        """Test that the logger is properly configured."""
        from src.api import features
        assert features.logger is not None

    def test_feature_store_initialization(self):
        """Test that feature store is initialized (or None on error)."""
        from src.api import features
        # feature_store could be None if initialization failed
        assert hasattr(features, 'feature_store')

    def test_feature_calculator_initialization(self):
        """Test that feature calculator is initialized (or None on error)."""
        from src.api import features
        # feature_calculator could be None if initialization failed
        assert hasattr(features, 'feature_calculator')