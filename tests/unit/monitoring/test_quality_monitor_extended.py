"""
Extended tests for the QualityMonitor to increase coverage.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.monitoring.quality_monitor import QualityMonitor


@pytest.fixture
def mock_db_manager():
    """Fixture for a mocked DatabaseManager."""
    db_manager = MagicMock()
    mock_session = AsyncMock()
    async_context_manager = AsyncMock()
    async_context_manager.__aenter__.return_value = mock_session
    db_manager.get_async_session.return_value = async_context_manager
    return db_manager, mock_session


@pytest.fixture
def quality_monitor(mock_db_manager):
    """Returns a mocked instance of the QualityMonitor."""
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "src.monitoring.quality_monitor.DatabaseManager", lambda: mock_db_manager[0]
        )
        monitor = QualityMonitor()
        yield monitor, mock_db_manager[1]


@pytest.mark.asyncio
async def test_check_table_freshness_is_fresh(quality_monitor):
    """Test the _check_table_freshness method when data is fresh."""
    monitor, mock_session = quality_monitor
    mock_row = MagicMock()
    mock_row.last_update = datetime.now() - timedelta(hours=1)
    mock_row.record_count = 100
    mock_result = MagicMock()
    mock_result.first.return_value = mock_row
    mock_session.execute.return_value = mock_result
    result = await monitor._check_table_freshness(mock_session, "matches")
    assert result.is_fresh is True
    assert result.records_count == 100


@pytest.mark.asyncio
async def test_check_table_freshness_is_stale(quality_monitor):
    """Test the _check_table_freshness method when data is stale."""
    monitor, mock_session = quality_monitor
    mock_row = MagicMock()
    mock_row.last_update = datetime.now() - timedelta(hours=48)
    mock_row.record_count = 50
    mock_result = AsyncMock()
    mock_result.first.return_value = mock_row
    mock_session.execute.return_value = mock_result
    result = await monitor._check_table_freshness(mock_session, "matches")
    assert result.is_fresh is False
    assert result.freshness_hours > 24


@pytest.mark.asyncio
async def test_check_table_completeness(quality_monitor):
    """Test the _check_table_completeness method."""
    monitor, mock_session = quality_monitor
    mock_total_row = MagicMock()
    mock_total_row.total = 100
    mock_total_result = AsyncMock()
    mock_total_result.first.return_value = mock_total_row
    mock_missing_row = MagicMock()
    mock_missing_row.missing = 5
    mock_missing_result = AsyncMock()
    mock_missing_result.first.return_value = mock_missing_row
    critical_fields_count = len(monitor.critical_fields.get("matches", []))
    mock_session.execute.side_effect = [mock_total_result] + [
        mock_missing_result
    ] * critical_fields_count
    result = await monitor._check_table_completeness(mock_session, "matches")
    assert result.total_records == 100
    assert result.completeness_score < 100
    assert "home_team_id" in result.missing_critical_fields
    assert result.missing_critical_fields["home_team_id"] == 5
