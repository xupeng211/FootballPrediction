import pytest
from unittest.mock import AsyncMock, MagicMock
import pandas as pd
import numpy as np

from src.services.data_processing import DataProcessingService


class TestAbnormalDataCleaning:
    """Test data cleaning logic with abnormal input validation"""

    @pytest.fixture
    def data_cleaning_service(self):
        """Create a DataProcessingService with mocked dependencies for cleaning tests"""
        service = DataProcessingService()
        service.data_cleaner = MagicMock()
        service.missing_handler = MagicMock()
        service.quality_validator = MagicMock()
        return service

    @pytest.fixture
    def abnormal_match_data_samples(self):
        """Return samples of abnormal match data for testing"""
        return [
            # Empty or missing critical fields
            {
                "match_id": "",
                "home_team": "",
                "away_team": "",
                "home_score": None,
                "away_score": None,
                "match_date": "invalid_date"
            },
            # Negative scores (invalid)
            {
                "match_id": "002",
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": -2,
                "away_score": -1,
                "match_date": "2023-09-29T15:00:00Z"
            },
            # Extremely large scores (unlikely but possible)
            {
                "match_id": "003",
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 999,
                "away_score": 888,
                "match_date": "2023-09-29T15:00:00Z"
            },
            # Missing team information
            {
                "match_id": "004",
                "home_team": None,
                "away_team": "",
                "home_score": 1,
                "away_score": 0,
                "match_date": "2023-09-29T15:00:00Z"
            },
            # Future date (invalid for historical data)
            {
                "match_id": "005",
                "home_team": "Team E",
                "away_team": "Team F",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2030-01-01T15:00:00Z"
            },
            # Non-numeric scores
            {
                "match_id": "006",
                "home_team": "Team G",
                "away_team": "Team H",
                "home_score": "two",
                "away_score": "one",
                "match_date": "2023-09-29T15:00:00Z"
            },
            # Extra fields that shouldn't exist
            {
                "match_id": "007",
                "home_team": "Team I",
                "away_team": "Team J",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2023-09-29T15:00:00Z",
                "invalid_field": "should_be_removed",
                "another_invalid": 12345
            }
        ]

    @pytest.fixture
    def abnormal_odds_data_samples(self):
        """Return samples of abnormal odds data for testing"""
        return [
            # Negative odds (impossible)
            {
                "match_id": "001",
                "bookmaker": "InvalidBookmaker",
                "home_win": -2.50,
                "draw": -1.50,
                "away_win": -3.00,
                "timestamp": "2023-09-29T14:00:00Z"
            },
            # Zero odds (impossible)
            {
                "match_id": "002",
                "bookmaker": "ZeroOddsBookmaker",
                "home_win": 0.0,
                "draw": 0.0,
                "away_win": 0.0,
                "timestamp": "2023-09-29T14:00:00Z"
            },
            # Odds that don't sum to reasonable range
            {
                "match_id": "003",
                "bookmaker": "UnbalancedBookmaker",
                "home_win": 1.01,
                "draw": 1.01,
                "away_win": 1.01,
                "timestamp": "2023-09-29T14:00:00Z"
            },
            # Extremely high odds
            {
                "match_id": "004",
                "bookmaker": "HighOddsBookmaker",
                "home_win": 1000.0,
                "draw": 500.0,
                "away_win": 2000.0,
                "timestamp": "2023-09-29T14:00:00Z"
            },
            # Non-numeric odds
            {
                "match_id": "005",
                "bookmaker": "StringOddsBookmaker",
                "home_win": "high",
                "draw": "medium",
                "away_win": "low",
                "timestamp": "2023-09-29T14:00:00Z"
            },
            # Missing odds fields
            {
                "match_id": "006",
                "bookmaker": "MissingFieldsBookmaker",
                "home_win": 2.10,
                # Missing draw and away_win
                "timestamp": "2023-09-29T14:00:00Z"
            }
        ]

    @pytest.fixture
    def abnormal_features_data_samples(self):
        """Return samples of abnormal features data for testing"""
        return [
            # DataFrame with NaN values
            pd.DataFrame({
                'feature_1': [1.0, np.nan, 3.0],
                'feature_2': [np.nan, np.nan, np.nan],
                'feature_3': [4.0, 5.0, np.inf]  # Infinity values
            }),
            # DataFrame with negative values where positive expected
            pd.DataFrame({
                'goals_scored': [-1, -2, -3],
                'goals_conceded': [-4, -5, -6],
                'possession': [50.0, 60.0, 70.0]
            }),
            # DataFrame with out-of-range values
            pd.DataFrame({
                'possession': [150.0, -20.0, 500.0],  # Should be 0-100
                'shots_on_target': [-5, 1000, 50],     # Should be non-negative
                'pass_accuracy': [1.5, -0.1, 2.0]     # Should be 0-1
            }),
            # Empty DataFrame
            pd.DataFrame(),
            # DataFrame with string values in numeric columns
            pd.DataFrame({
                'numeric_feature': [1.0, "invalid", 3.0],
                'another_numeric': ["text", 2.0, 3.0]
            })
        ]

    @pytest.mark.asyncio
    async def test_clean_abnormal_match_data_empty_fields(self, data_cleaning_service):
        """Test cleaning match data with empty critical fields"""
        abnormal_data = {
            "match_id": "",
            "home_team": "",
            "away_team": "",
            "home_score": None,
            "away_score": None,
            "match_date": "invalid_date"
        }

        # Mock the cleaner to handle abnormal data
        data_cleaning_service.data_cleaner.clean_match_data = AsyncMock(
            return_value={
                "match_id": "default_001",
                "home_team": "Unknown Team",
                "away_team": "Unknown Team",
                "home_score": 0,
                "away_score": 0,
                "match_date": "2023-01-01T00:00:00Z",
                "status": "unknown"
            }
        )

        result = await data_cleaning_service.process_raw_match_data(abnormal_data)

        # Verify abnormal data was cleaned
        assert result is not None
        assert result.get("match_id") == "default_001"
        assert result.get("home_team") == "Unknown Team"
        assert result.get("home_score") == 0

    @pytest.mark.asyncio
    async def test_clean_abnormal_match_data_negative_scores(self, data_cleaning_service):
        """Test cleaning match data with negative scores"""
        abnormal_data = {
            "match_id": "002",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": -2,
            "away_score": -1,
            "match_date": "2023-09-29T15:00:00Z"
        }

        # Mock cleaner to normalize negative scores to zero
        data_cleaning_service.data_cleaner.clean_match_data = AsyncMock(
            return_value={
                "match_id": "002",
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 0,  # Normalized from -2
                "away_score": 0,  # Normalized from -1
                "match_date": "2023-09-29T15:00:00Z",
                "status": "finished"
            }
        )

        result = await data_cleaning_service.process_raw_match_data(abnormal_data)

        # Verify negative scores were normalized
        assert result is not None
        assert result.get("home_score") >= 0
        assert result.get("away_score") >= 0

    @pytest.mark.asyncio
    async def test_clean_abnormal_match_data_non_numeric_scores(self, data_cleaning_service):
        """Test cleaning match data with non-numeric scores"""
        abnormal_data = {
            "match_id": "006",
            "home_team": "Team G",
            "away_team": "Team H",
            "home_score": "two",
            "away_score": "one",
            "match_date": "2023-09-29T15:00:00Z"
        }

        # Mock cleaner to handle non-numeric scores
        data_cleaning_service.data_cleaner.clean_match_data = AsyncMock(
            return_value={
                "match_id": "006",
                "home_team": "Team G",
                "away_team": "Team H",
                "home_score": 0,  # Default for invalid input
                "away_score": 0,  # Default for invalid input
                "match_date": "2023-09-29T15:00:00Z",
                "status": "unknown"
            }
        )

        result = await data_cleaning_service.process_raw_match_data(abnormal_data)

        # Verify non-numeric scores were handled
        assert result is not None
        assert isinstance(result.get("home_score"), (int, float))
        assert isinstance(result.get("away_score"), (int, float))

    @pytest.mark.asyncio
    async def test_clean_abnormal_odds_data_negative_values(self, data_cleaning_service):
        """Test cleaning odds data with negative values"""
        abnormal_odds = [{
            "match_id": "001",
            "bookmaker": "InvalidBookmaker",
            "home_win": -2.50,
            "draw": -1.50,
            "away_win": -3.00,
            "timestamp": "2023-09-29T14:00:00Z"
        }]

        # Mock cleaner to handle negative odds
        data_cleaning_service.data_cleaner.clean_odds_data = AsyncMock(
            return_value=[{
                "match_id": "001",
                "bookmaker": "InvalidBookmaker",
                "home_win": 2.50,  # Absolute value
                "draw": 1.50,     # Absolute value
                "away_win": 3.00, # Absolute value
                "timestamp": "2023-09-29T14:00:00Z",
                "cleaned": True
            }]
        )

        result = await data_cleaning_service.process_raw_odds_data(abnormal_odds)

        # Verify negative odds were handled
        assert result is not None
        assert result.get("odds")
        odds = result["odds"][0]
        assert odds.get("home_win") > 0
        assert odds.get("draw") > 0
        assert odds.get("away_win") > 0

    @pytest.mark.asyncio
    async def test_clean_abnormal_odds_data_zero_values(self, data_cleaning_service):
        """Test cleaning odds data with zero values"""
        abnormal_odds = [{
            "match_id": "002",
            "bookmaker": "ZeroOddsBookmaker",
            "home_win": 0.0,
            "draw": 0.0,
            "away_win": 0.0,
            "timestamp": "2023-09-29T14:00:00Z"
        }]

        # Mock cleaner to handle zero odds
        data_cleaning_service.data_cleaner.clean_odds_data = AsyncMock(
            return_value=[{
                "match_id": "002",
                "bookmaker": "ZeroOddsBookmaker",
                "home_win": 2.00,  # Default minimum odds
                "draw": 2.00,     # Default minimum odds
                "away_win": 2.00, # Default minimum odds
                "timestamp": "2023-09-29T14:00:00Z",
                "cleaned": True
            }]
        )

        result = await data_cleaning_service.process_raw_odds_data(abnormal_odds)

        # Verify zero odds were replaced with minimum values
        assert result is not None
        odds = result["odds"][0]
        assert odds.get("home_win") > 1.0  # Reasonable minimum odds

    @pytest.mark.asyncio
    async def test_clean_abnormal_features_nan_values(self, data_cleaning_service):
        """Test cleaning features data with NaN values"""
        abnormal_features = pd.DataFrame({
            'feature_1': [1.0, np.nan, 3.0],
            'feature_2': [np.nan, np.nan, np.nan],
            'feature_3': [4.0, 5.0, np.inf]
        })

        # Mock missing handler to clean NaN values
        data_cleaning_service.missing_handler.handle_missing_features = AsyncMock(
            return_value=pd.DataFrame({
                'feature_1': [1.0, 0.0, 3.0],    # NaN filled with 0
                'feature_2': [0.0, 0.0, 0.0],    # All NaN filled with 0
                'feature_3': [4.0, 5.0, 1000.0]  # Infinity replaced with large number
            })
        )

        result = await data_cleaning_service.process_features_data(
            match_id="001",
            features_df=abnormal_features
        )

        # Verify NaN values were handled
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert not result.isnull().any().any()  # No NaN values remaining

    @pytest.mark.asyncio
    async def test_clean_abnormal_features_out_of_range(self, data_cleaning_service):
        """Test cleaning features data with out-of-range values"""
        abnormal_features = pd.DataFrame({
            'possession': [150.0, -20.0, 500.0],  # Should be 0-100
            'shots_on_target': [-5, 1000, 50],     # Should be non-negative
            'pass_accuracy': [1.5, -0.1, 2.0]     # Should be 0-1
        })

        # Mock missing handler to normalize out-of-range values
        data_cleaning_service.missing_handler.handle_missing_features = AsyncMock(
            return_value=pd.DataFrame({
                'possession': [100.0, 0.0, 100.0],    # Clamped to 0-100
                'shots_on_target': [0, 50, 50],         # Negative set to 0, high set to reasonable max
                'pass_accuracy': [1.0, 0.0, 1.0]       # Clamped to 0-1
            })
        )

        result = await data_cleaning_service.process_features_data(
            match_id="002",
            features_df=abnormal_features
        )

        # Verify out-of-range values were normalized
        assert result is not None
        assert isinstance(result, pd.DataFrame)

        # Check possession is within valid range
        possession = result['possession'].tolist()
        assert all(0 <= p <= 100 for p in possession)

        # Check shots on target are non-negative
        shots = result['shots_on_target'].tolist()
        assert all(s >= 0 for s in shots)

        # Check pass accuracy is within valid range
        accuracy = result['pass_accuracy'].tolist()
        assert all(0 <= a <= 1 for a in accuracy)

    @pytest.mark.asyncio
    async def test_clean_empty_features_dataframe(self, data_cleaning_service):
        """Test cleaning empty features DataFrame"""
        empty_features = pd.DataFrame()

        # Mock handler to return empty but valid DataFrame
        data_cleaning_service.missing_handler.handle_missing_features = AsyncMock(
            return_value=pd.DataFrame()
        )

        result = await data_cleaning_service.process_features_data(
            match_id="003",
            features_df=empty_features
        )

        # Verify empty DataFrame handling
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @pytest.mark.asyncio
    async def test_data_quality_validation_abnormal_data(self, data_cleaning_service):
        """Test data quality validation with abnormal data"""
        abnormal_data = {
            "match_id": "",
            "home_team": "",
            "away_team": "",
            "home_score": -999,
            "away_score": None
        }

        # Mock quality validator to detect issues
        data_cleaning_service.quality_validator.validate_match_data = AsyncMock(
            return_value={
                "valid": False,
                "score": 0.1,
                "issues": [
                    "Empty match_id field",
                    "Empty home_team field",
                    "Empty away_team field",
                    "Negative home_score value",
                    "Missing away_score value"
                ]
            }
        )

        result = await data_cleaning_service.validate_data_quality(abnormal_data, "match")

        # Verify quality validation detected issues
        assert result is not None
        assert result.get("valid") is False
        assert result.get("score") < 0.5  # Low quality score
        assert len(result.get("issues", [])) > 0

    @pytest.mark.asyncio
    async def test_batch_cleaning_mixed_data_quality(self, data_cleaning_service):
        """Test batch cleaning with mixed data quality"""
        mixed_data = [
            # Good data
            {
                "match_id": "good_001",
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2023-09-29T15:00:00Z"
            },
            # Bad data
            {
                "match_id": "",
                "home_team": "",
                "away_team": "",
                "home_score": -1,
                "away_score": None,
                "match_date": "invalid"
            },
            # Another good data
            {
                "match_id": "good_002",
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 0,
                "away_score": 0,
                "match_date": "2023-09-29T17:00:00Z"
            }
        ]

        # Mock different cleaning responses based on data quality
        def mock_clean_match_data(data):
            if data["match_id"].startswith("good"):
                return {
                    **data,
                    "status": "finished",
                    "cleaned": True
                }
            else:
                return {
                    "match_id": "cleaned_bad_001",
                    "home_team": "Unknown Team",
                    "away_team": "Unknown Team",
                    "home_score": 0,
                    "away_score": 0,
                    "match_date": "2023-01-01T00:00:00Z",
                    "status": "unknown",
                    "cleaned": True
                }

        data_cleaning_service.data_cleaner.clean_match_data = AsyncMock(
            side_effect=mock_clean_match_data
        )

        results = await data_cleaning_service.process_batch_matches(mixed_data)

        # Verify batch processing handled mixed data quality
        assert len(results) == 3
        assert all(result is not None for result in results)

        # Check that bad data was cleaned
        cleaned_bad = next(r for r in results if r.get("match_id") == "cleaned_bad_001")
        assert cleaned_bad.get("home_team") == "Unknown Team"

        # Check that good data was preserved
        good_data = [r for r in results if r.get("match_id").startswith("good")]
        assert len(good_data) == 2

    @pytest.mark.asyncio
    async def test_extreme_abnormal_data_handling(self, data_cleaning_service):
        """Test handling of extremely abnormal data"""
        extreme_data = {
            "match_id": None,
            "home_team": 12345,  # Wrong data type
            "away_team": [],
            "home_score": "not_a_number",
            "away_score": {"complex": "object"},
            "match_date": "",
            "extra_invalid_field": lambda x: x  # Function object
        }

        # Mock cleaner to handle extreme abnormalities
        data_cleaning_service.data_cleaner.clean_match_data = AsyncMock(
            return_value={
                "match_id": "extreme_case_001",
                "home_team": "Extreme Case Team",
                "away_team": "Extreme Case Opponent",
                "home_score": 0,
                "away_score": 0,
                "match_date": "2023-01-01T00:00:00Z",
                "status": "unknown",
                "extreme_cleaning_applied": True
            }
        )

        result = await data_cleaning_service.process_raw_match_data(extreme_data)

        # Verify extreme abnormalities were handled gracefully
        assert result is not None
        assert result.get("match_id") == "extreme_case_001"
        assert isinstance(result.get("home_team"), str)
        assert isinstance(result.get("home_score"), (int, float))

    @pytest.mark.asyncio
    async def test_data_cleaning_performance_with_abnormal_data(self, data_cleaning_service):
        """Test performance of data cleaning with many abnormal records"""
        # Create a large batch of abnormal data
        abnormal_batch = []
        for i in range(100):
            abnormal_batch.append({
                "match_id": f"abnormal_{i:03d}",
                "home_team": "" if i % 10 == 0 else f"Team {i}",
                "away_team": None if i % 15 == 0 else f"Opponent {i}",
                "home_score": -i if i % 5 == 0 else i,
                "away_score": "invalid" if i % 8 == 0 else i % 5,
                "match_date": "invalid_date" if i % 20 == 0 else f"2023-09-{29-i%28:02d}T15:00:00Z"
            })

        # Mock cleaner to be fast but still clean data
        def fast_clean_match_data(data):
            return {
                "match_id": data.get("match_id", f"cleaned_{hash(str(data))}"),
                "home_team": data.get("home_team") or "Unknown Team",
                "away_team": data.get("away_team") or "Unknown Opponent",
                "home_score": max(0, int(data.get("home_score", 0))),
                "away_score": max(0, int(data.get("away_score", 0))),
                "match_date": data.get("match_date") or "2023-01-01T00:00:00Z",
                "status": "cleaned"
            }

        data_cleaning_service.data_cleaner.clean_match_data = AsyncMock(
            side_effect=fast_clean_match_data
        )

        import time
        start_time = time.time()

        results = await data_cleaning_service.process_batch_matches(abnormal_batch, batch_size=25)

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify performance and correctness
        assert len(results) == 100
        assert all(result is not None for result in results)
        assert processing_time < 10.0  # Should process in reasonable time (adjust as needed)

        # Verify all abnormal data was cleaned
        for result in results:
            assert result.get("match_id") is not None
            assert result.get("home_team") is not None
            assert result.get("away_team") is not None
            assert isinstance(result.get("home_score"), (int, float))
            assert isinstance(result.get("away_score"), (int, float))