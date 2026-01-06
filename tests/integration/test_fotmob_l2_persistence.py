#!/usr/bin/env python3
"""V145.0 FotMob L2 High-Level Data Persistence Integration Tests (TDD).

Test suite for FotMob L2 (match details) data collection:
- L2 JSON fetching and storage
- l2_raw_json field validation
- ON CONFLICT backfill logic
- Mock-only testing (no real API calls)

Author: V145.0 Data Engineering Team
Version: 1.0.0
Date: 2026-01-06
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# Task D: FotMob L2 Persistence Tests (Mock Data Only)
# ============================================================================

class TestFotMobL2Persistence:
    """Test suite for FotMob L2 (match details) data persistence."""

    @pytest.fixture
    def mock_l2_json_data(self):
        """Mock FotMob L2 API response data."""
        return {
            "header": {
                "status": {
                    "utcTime": "2024-04-20T15:00:00Z"
                },
                "match": {
                    "matchTime": "2024-04-20T15:00:00Z",
                    "league": "Premier League"
                },
                "teams": [
                    {"name": "Arsenal", "score": 2},
                    {"name": "Chelsea", "score": 1}
                ],
                "league": {"name": "Premier League", "id": 47},
                "venue": {"name": "Emirates Stadium"}
            },
            "content": {
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {
                                    "key": "BallPossesion",
                                    "stats": [55, 45]
                                },
                                {
                                    "key": "ShotsOnTarget",
                                    "stats": [8, 4]
                                },
                                {
                                    "key": "expected_goals",
                                    "stats": [1.85, 0.92]
                                }
                            ]
                        }
                    }
                },
                "lineup": {
                    "homeTeam": {
                        "formation": "4-3-3",
                        "rating": 7.2
                    },
                    "awayTeam": {
                        "formation": "4-2-3-1",
                        "rating": 6.8
                    }
                }
            },
            # V145.0: Add padding data to pass 16KB sentinel check
            "padding": ["x" * 20000]  # Pad to > 16KB
        }

    def test_l2_json_structure_is_valid(self, mock_l2_json_data):
        """Test that mock L2 JSON has valid structure."""
        # Verify header exists
        assert "header" in mock_l2_json_data
        assert "teams" in mock_l2_json_data["header"]
        assert len(mock_l2_json_data["header"]["teams"]) == 2

        # Verify content.stats exists
        assert "content" in mock_l2_json_data
        assert "stats" in mock_l2_json_data["content"]
        assert "Periods" in mock_l2_json_data["content"]["stats"]
        assert "All" in mock_l2_json_data["content"]["stats"]["Periods"]

    @pytest.mark.asyncio
    async def test_fetch_l2_with_mock_data(self, mock_l2_json_data):
        """Test fetching L2 data with mock (NO real API calls)."""
        from src.api.collectors.fotmob_core import FotMobCoreCollector

        # Mock the session.get method
        collector = FotMobCoreCollector()

        with patch.object(collector.session, 'get') as mock_get:
            # Mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = json.dumps(mock_l2_json_data).encode('utf-8')
            mock_response.headers = {}
            mock_get.return_value = mock_response

            # Fetch L2 data
            result = collector.get_match_details(4030001)

            # Verify success
            assert result is not None
            assert "match_info" in result
            assert "l2_json" in result
            assert result["match_info"]["home_team"] == "Arsenal"
            assert result["match_info"]["away_team"] == "Chelsea"

    @pytest.mark.asyncio
    async def test_l2_persistence_to_database(self, mock_l2_json_data):
        """Test L2 JSON is persisted to database l2_raw_json field."""
        from src.api.collectors.fotmob_core import FotMobCoreCollector

        # Mock database connection with proper context manager support
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Set up cursor context manager to return itself
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        match_info = {
            "match_id": 4030001,
            "external_id": "4030001",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "match_time": "2024-04-20T15:00:00Z",
            "match_date": "2024-04-20"
        }

        l2_json = {
            "l2_json": mock_l2_json_data,
            "collected_at": "2026-01-06T08:00:00Z"
        }

        # Patch get_database_connection method
        with patch.object(FotMobCoreCollector, "get_database_connection", return_value=mock_conn):
            collector = FotMobCoreCollector()
            result = collector.upsert_match_data(match_info, l2_json, league_id=47, season="2324")

            # Verify UPSERT was called
            assert result is True
            mock_cursor.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

            # Verify SQL contains l2_raw_json
            call_args = mock_cursor.execute.call_args
            sql = call_args[0][0]
            assert "l2_raw_json" in sql
            assert "ON CONFLICT" in sql

    def test_l2_json_field_is_parseable(self, mock_l2_json_data):
        """Test that stored L2 JSON can be parsed back."""
        # Serialize to JSON string (simulating database storage)
        json_str = json.dumps(mock_l2_json_data)

        # Parse back
        parsed = json.loads(json_str)

        # Verify structure preserved
        assert parsed["header"]["teams"][0]["name"] == "Arsenal"
        assert parsed["header"]["teams"][1]["name"] == "Chelsea"
        assert parsed["content"]["stats"]["Periods"]["All"]["stats"][0]["key"] == "BallPossesion"

    @pytest.mark.asyncio
    async def test_on_conflict_backfill_logic(self):
        """Test ON CONFLICT logic for L2 backfill."""
        from src.api.collectors.fotmob_core import FotMobCoreCollector

        # Mock database connection with proper context manager support
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Set up cursor context manager to return itself
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        # First insert (L1 data only)
        match_info = {
            "match_id": 4030002,
            "external_id": "4030002",
            "home_team": "Liverpool",
            "away_team": "Man City",
            "match_time": "2024-04-21T16:30:00Z",
            "match_date": "2024-04-21"
        }

        l2_json = {
            "l2_json": {"header": {"teams": [{"name": "Liverpool"}, {"name": "Man City"}]}},
            "collected_at": "2026-01-06T08:00:00Z"
        }

        # Patch get_database_connection method
        with patch.object(FotMobCoreCollector, "get_database_connection", return_value=mock_conn):
            collector = FotMobCoreCollector()

            # First UPSERT (simulating L1 exists)
            result1 = collector.upsert_match_data(match_info, l2_json, league_id=47, season="2324")
            assert result1 is True

            # Second UPSERT (simulating L2 backfill - same ID)
            result2 = collector.upsert_match_data(match_info, l2_json, league_id=47, season="2324")
            assert result2 is True

            # Verify ON CONFLICT clause is present
            call_args = mock_cursor.execute.call_args
            sql = call_args[0][0]
            assert "ON CONFLICT (id) DO UPDATE SET" in sql
            assert "l2_raw_json = EXCLUDED.l2_raw_json" in sql

    @pytest.mark.asyncio
    async def test_l2_data_contains_all_required_features(self, mock_l2_json_data):
        """Test that L2 data contains all required features."""
        # Verify header data
        assert "header" in mock_l2_json_data
        assert "teams" in mock_l2_json_data["header"]
        assert "league" in mock_l2_json_data["header"]
        assert "venue" in mock_l2_json_data["header"]

        # Verify stats data
        stats = mock_l2_json_data["content"]["stats"]["Periods"]["All"]["stats"]
        stat_keys = [s["key"] for s in stats]
        assert "BallPossesion" in stat_keys
        assert "ShotsOnTarget" in stat_keys

        # Verify lineup data
        assert "lineup" in mock_l2_json_data["content"]
        assert "homeTeam" in mock_l2_json_data["content"]["lineup"]
        assert "awayTeam" in mock_l2_json_data["content"]["lineup"]

    @pytest.mark.asyncio
    async def test_ghost_protocol_headers_applied(self):
        """Test that Ghost Protocol headers are applied."""
        from src.api.collectors.fotmob_core import FotMobCoreCollector
        from src.api.collectors.base_extractor import BaseExtractor

        collector = FotMobCoreCollector()

        # Verify Ghost Protocol integration
        assert hasattr(collector, 'headers')
        assert 'User-Agent' in collector.headers
        assert 'Sec-Ch-Ua' in collector.headers
        assert 'Sec-Ch-Ua-Mobile' in collector.headers
        assert 'Sec-Ch-Ua-Platform' in collector.headers
        assert 'Sec-Ch-Ua-Viewport' in collector.headers

        # Verify UA is from BaseExtractor pool
        ua = collector.headers['User-Agent']
        assert 'Mozilla' in ua or 'Chrome' in ua or 'Safari' in ua or 'Firefox' in ua


# ============================================================================
# Test Discovery
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
