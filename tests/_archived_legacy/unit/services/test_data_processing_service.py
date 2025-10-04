import os
import warnings
from types import SimpleNamespace
from typing import Any, Dict

import pandas as pd
import pytest
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("MINIMAL_API_MODE", "true")
warnings.filterwarnings("ignore", category=UserWarning)

from src.services.data_processing import DataProcessingService

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


class DummyCache:
    def __init__(self) -> None:
        self.aset_calls = []
        self.closed = False

    async def aget(self, key: str) -> Dict[str, Any] | None:
        return None

    async def aset(
        self,
        key: str,
        value: Dict[str, Any],
        cache_type: str | None = None,
        expire: int | None = None,
    ) -> None:
        self.aset_calls.append((key, cache_type, expire))

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def service() -> DataProcessingService:
    svc = DataProcessingService()
    svc.logger = MagicMock()

    cleaner = MagicMock()
    cleaner.clean_match_data.side_effect = lambda raw: {
        **raw,
        "cleaned": True,
    }
    svc.data_cleaner = cleaner

    missing_handler = MagicMock()
    missing_handler.handle_missing_match_data.side_effect = lambda data: {
        **data,
        "processed": True,
    }
    missing_handler.handle_missing_features = AsyncMock(
        side_effect=lambda *_: pd.DataFrame()
    )
    svc.missing_handler = missing_handler

    svc.cache_manager = DummyCache()
    svc.db_manager = SimpleNamespace(close=AsyncMock())

    return svc


@pytest.mark.asyncio
async def test_process_raw_match_data_dict(service: DataProcessingService):
    raw = {
        "external_match_id": "match-500",
        "home_team_id": 10,
        "away_team_id": 12,
    }

    processed = await service.process_raw_match_data(raw)

    assert processed is not None
    assert processed["processed"] is True
    assert any(
        call[0].startswith("match:match-500")
        for call in service.cache_manager.aset_calls
    )


@pytest.mark.asyncio
async def test_process_raw_match_data_list_returns_dataframe(
    service: DataProcessingService,
):
    raw_list = [
        {
            "external_match_id": "match-600",
            "home_team_id": 1,
            "away_team_id": 2,
        },
        {
            "external_match_id": "match-601",
            "home_team_id": 3,
            "away_team_id": 4,
        },
    ]

    df = await service.process_raw_match_data(raw_list)

    assert isinstance(df, pd.DataFrame)
    assert sorted(df["external_match_id"]) == ["match-600", "match-601"]
    assert (df["processed"] == True).all()


@pytest.mark.asyncio
async def test_shutdown_closes_dependencies(service: DataProcessingService):
    cache = service.cache_manager
    db_manager = service.db_manager

    await service.shutdown()

    assert cache.closed is True
    db_manager.close.assert_awaited()
