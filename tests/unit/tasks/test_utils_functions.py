from datetime import datetime, timedelta

import pytest

from src.tasks import utils

pytestmark = pytest.mark.unit


class _ResultWithScalar:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _AsyncSessionContext:
    def __init__(self, result, commit=False):
        self._result = result
        self.commit_called = False
        self._needs_commit = commit

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def execute(self, *_, **__):
        return self._result

    async def commit(self):
        self.commit_called = True

    def __iter__(self):
        return iter(self._result)


class _ManagerFactory:
    def __init__(self, result, commit=False):
        self._result = result
        self._commit = commit

    def __call__(self):
        return self

    def get_async_session(self):
        return _AsyncSessionContext(self._result, commit=self._commit)


@pytest.mark.asyncio
async def test_should_collect_live_scores_returns_true(monkeypatch):
    manager = _ManagerFactory(_ResultWithScalar(3))
    monkeypatch.setattr(utils, "DatabaseManager", manager)

    assert await utils.should_collect_live_scores() is True


@pytest.mark.asyncio
async def test_should_collect_live_scores_handles_errors(monkeypatch):
    class _FailingManager:
        def __call__(self):
            raise RuntimeError("db error")

    monkeypatch.setattr(utils, "DatabaseManager", _FailingManager())
    assert await utils.should_collect_live_scores() is False


@pytest.mark.asyncio
async def test_get_upcoming_matches_returns_serializable_rows(monkeypatch):
    now = datetime.now()

    class _Row:
        def __init__(self, idx):
            self.id = idx
            self.home_team_id = f"home-{idx}"
            self.away_team_id = f"away-{idx}"
            self.league_id = f"league-{idx}"
            self.match_time = now + timedelta(hours=idx)
            self.match_status = "scheduled"

    rows = [_Row(1), _Row(2)]
    manager = _ManagerFactory(rows)
    monkeypatch.setattr(utils, "DatabaseManager", manager)

    matches = await utils.get_upcoming_matches(hours=6)
    assert len(matches) == 2
    assert matches[0]["id"] == 1
    assert "T" in matches[0]["match_time"]


@pytest.mark.asyncio
async def test_cleanup_stale_tasks_returns_rowcount(monkeypatch):
    class _Result:
        rowcount = 5

    manager = _ManagerFactory(_Result())
    monkeypatch.setattr(utils, "DatabaseManager", manager)

    assert await utils.cleanup_stale_tasks() == 5


@pytest.mark.asyncio
async def test_cleanup_stale_tasks_returns_zero_when_rowcount_missing(monkeypatch):
    class _Result:
        rowcount = None

    manager = _ManagerFactory(_Result())
    monkeypatch.setattr(utils, "DatabaseManager", manager)

    assert await utils.cleanup_stale_tasks() == 0


@pytest.mark.asyncio
async def test_cleanup_stale_tasks_handles_exception(monkeypatch):
    class _FailingManager:
        def __call__(self):
            return self

        def get_async_session(self):
            raise RuntimeError("cleanup failure")

    monkeypatch.setattr(utils, "DatabaseManager", _FailingManager())
    assert await utils.cleanup_stale_tasks() == 0


def test_is_match_day_and_next_collection_time_branches(monkeypatch):
    saturday = datetime(2025, 9, 20, 10, 0, 0)
    assert utils.is_match_day(saturday) is True
    assert utils.is_match_day(saturday + timedelta(days=2)) is False

    class _EarlyMorning(datetime):
        @classmethod
        def now(cls):
            return datetime(2025, 9, 23, 1, 30, 0)

    monkeypatch.setattr(utils, "datetime", _EarlyMorning)
    next_fixtures = utils.calculate_next_collection_time("collect_fixtures_task")
    assert next_fixtures.hour == 2

    class _LateMorning(datetime):
        @classmethod
        def now(cls):
            return datetime(2025, 9, 23, 5, 0, 0)

    monkeypatch.setattr(utils, "datetime", _LateMorning)
    next_fixtures_late = utils.calculate_next_collection_time("collect_fixtures_task")
    assert next_fixtures_late.hour == 2
    assert next_fixtures_late.date() == (_LateMorning.now() + timedelta(days=1)).date()

    class _LateForOdds(datetime):
        @classmethod
        def now(cls):
            return datetime(2025, 9, 23, 10, 58, 0)

    monkeypatch.setattr(utils, "datetime", _LateForOdds)
    next_odds = utils.calculate_next_collection_time("collect_odds_task")
    assert next_odds.minute == 0
    assert next_odds.hour == 11

    class _LateForScores(datetime):
        @classmethod
        def now(cls):
            return datetime(2025, 9, 23, 10, 59, 0)

    monkeypatch.setattr(utils, "datetime", _LateForScores)
    next_scores = utils.calculate_next_collection_time("collect_scores_task")
    assert next_scores.minute == 0
    assert next_scores.hour == 11

    class _DefaultTime(datetime):
        @classmethod
        def now(cls):
            return datetime(2025, 9, 23, 14, 15, 0)

    monkeypatch.setattr(utils, "datetime", _DefaultTime)
    default_run = utils.calculate_next_collection_time("other")
    assert default_run - _DefaultTime.now() == timedelta(hours=1)


def test_get_task_priority_defaults() -> None:
    assert utils.get_task_priority("collect_scores_task") == 1
    assert utils.get_task_priority("unknown") == 5


@pytest.mark.asyncio
async def test_get_upcoming_matches_returns_empty_on_error(monkeypatch):
    class _FailingManager:
        def __call__(self):
            return self

        def get_async_session(self):
            raise RuntimeError("db failure")

    monkeypatch.setattr(utils, "DatabaseManager", _FailingManager())
    assert await utils.get_upcoming_matches() == []


@pytest.mark.asyncio
async def test_get_active_leagues_fallback(monkeypatch):
    class _FailingManager:
        def __call__(self):
            return self

        def get_async_session(self):
            raise RuntimeError("db failure")

    monkeypatch.setattr(utils, "DatabaseManager", _FailingManager())
    leagues = await utils.get_active_leagues()
    assert "Premier League" in leagues
