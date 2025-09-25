from dataclasses import dataclass

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

    assert result == 1  # 处理计数在异常前已增加
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
