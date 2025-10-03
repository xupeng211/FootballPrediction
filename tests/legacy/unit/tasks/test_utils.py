from datetime import datetime

from src.tasks import utils
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# tests/unit/tasks/test_utils.py

# =============================================================================
# Tests for Pure Logic Functions
# =============================================================================
@pytest.mark.parametrize(
    "task_name, expected_priority[",""""
    [
        ("]collect_scores_task[", 1),""""
        ("]collect_odds_task[", 2),""""
        ("]collect_fixtures_task[", 3),""""
        ("]unknown_task[", 5)])": def test_get_task_priority(task_name, expected_priority):": assert utils.get_task_priority(task_name) ==expected_priority[""
@pytest.mark.parametrize(
    "]]test_date, expected_result[",""""
    [
        (datetime(2023, 1, 2), False),  # Monday
        (datetime(2023, 1, 6), False),  # Friday
        (datetime(2023, 1, 7), True),  # Saturday
        (datetime(2023, 1, 8), True),  # Sunday
    ])
def test_is_match_day(test_date, expected_result):
    assert utils.is_match_day(test_date) ==expected_result
def test_is_match_day_default_date():
    is_weekend = datetime.now().weekday() in [5, 6]
    assert utils.is_match_day() ==is_weekend
@pytest.mark.parametrize(
    "]task_name, hour, minute, expected_delta_minutes[",""""
    [
        ("]collect_fixtures_task[", 1, 0, 60),""""
        ("]collect_odds_task[", 1, 4, 1),""""
        ("]collect_scores_task[", 1, 3, 1),""""
        ("]unknown_task[", 1, 0, 60)])": def test_calculate_next_collection_time(": task_name, hour, minute, expected_delta_minutes[""
):
    now = datetime(2023, 1, 1, hour, minute)
    with patch("]]src.tasks.utils.datetime[") as mock_dt:": mock_dt.now.return_value = now[": next_time = utils.calculate_next_collection_time(task_name)": delta = (next_time - now).total_seconds() / 60"
    assert abs(delta - expected_delta_minutes) < 1
# =============================================================================
# Tests for Database Interaction Functions (Async)
# =============================================================================
@pytest.mark.asyncio
@patch("]]src.tasks.utils.DatabaseManager[")": async def test_should_collect_live_scores_with_matches(MockDatabaseManager):": mock_result = MagicMock()": mock_result.scalar.return_value = 1"
    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    mock_db_manager = MockDatabaseManager.return_value
    mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
    )
    assert await utils.should_collect_live_scores() is True
@pytest.mark.asyncio
@patch("]src.tasks.utils.DatabaseManager[")": async def test_should_collect_live_scores_no_matches(MockDatabaseManager):": mock_result = MagicMock()": mock_result.scalar.return_value = 0"
    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    mock_db_manager = MockDatabaseManager.return_value
    mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
    )
    assert await utils.should_collect_live_scores() is False
@pytest.mark.asyncio
@patch("]src.tasks.utils.DatabaseManager[")": async def test_get_active_leagues_success(MockDatabaseManager):": mock_row = MagicMock()": mock_row.name = "]Premier League[": mock_result = ["]mock_row["]": mock_session = AsyncMock()": mock_session.execute.return_value = mock_result[": mock_db_manager = MockDatabaseManager.return_value"
    mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
    )
    leagues = await utils.get_active_leagues()
    assert leagues == ["]]Premier League["]""""
@pytest.mark.asyncio
@patch("]src.tasks.utils.DatabaseManager[")": async def test_get_active_leagues_db_error(MockDatabaseManager):": mock_db_manager = MockDatabaseManager.return_value[": mock_db_manager.get_async_session.side_effect = Exception("]]DB Error[")": leagues = await utils.get_active_leagues()": assert leagues ==["]Premier League[", "]La Liga[", "]Serie A[", "]Bundesliga["]""""
@pytest.mark.asyncio
@patch("]src.tasks.utils.DatabaseManager[")": async def test_cleanup_stale_tasks_success(MockDatabaseManager):": mock_result = MagicMock()": mock_result.rowcount = 5"
    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    mock_db_manager = MockDatabaseManager.return_value
    mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
    )
    cleaned_rows = await utils.cleanup_stale_tasks()
    assert cleaned_rows ==5
    mock_session.commit.assert_called_once()
@pytest.mark.asyncio
@patch("]src.tasks.utils.DatabaseManager[")": async def test_get_upcoming_matches_db_error(MockDatabaseManager):": mock_db_manager = MockDatabaseManager.return_value[": mock_db_manager.get_async_session.side_effect = Exception("]]DB Error[")"]": assert await utils.get_upcoming_matches() ==[]