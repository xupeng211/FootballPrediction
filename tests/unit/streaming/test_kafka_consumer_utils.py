import json
import logging
from datetime import datetime

import pytest

from src.streaming import kafka_consumer


class DummySessionContext:
    def __init__(self):
        self.added = []
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True


class DummyDBManager:
    def __init__(self, context):
        self._context = context

    def get_async_session(self):
        return self._context


class DummyKafka:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


@pytest.fixture
def consumer_instance():
    instance = kafka_consumer.FootballKafkaConsumer.__new__(
        kafka_consumer.FootballKafkaConsumer
    )
    instance.logger = logging.getLogger("test-consumer")
    instance.config = None
    instance.consumer = DummyKafka()
    instance.running = False
    context = DummySessionContext()
    instance.db_manager = DummyDBManager(context)
    instance._session_context = context
    return instance


def test_deserialize_message_success(consumer_instance):
    payload = {"key": "value"}
    raw = json.dumps(payload).encode("utf-8")
    assert consumer_instance._deserialize_message(raw) == payload


def test_deserialize_message_failure(consumer_instance):
    with pytest.raises(json.JSONDecodeError):
        consumer_instance._deserialize_message(b"not-json")


@pytest.mark.asyncio
async def test_process_match_message_writes_raw_data(consumer_instance):
    message = {
        "data": {
            "match_id": 1,
            "league_id": 99,
            "match_time": datetime.utcnow().isoformat(),
        },
        "source": "pytest",
    }

    result = await consumer_instance._process_match_message(message)
    context = consumer_instance.db_manager._context
    assert result is True
    assert context.committed is True
    assert context.added[0].raw_data["match_id"] == 1


@pytest.mark.asyncio
async def test_process_odds_message_handles_basic_payload(consumer_instance):
    message = {
        "data": {"match_id": 2, "bookmaker": "demo", "market_type": "1x2"},
    }

    result = await consumer_instance._process_odds_message(message)
    context = consumer_instance.db_manager._context
    assert result is True
    assert context.added[-1].raw_data["bookmaker"] == "demo"


@pytest.mark.asyncio
async def test_process_scores_message_handles_optional_fields(consumer_instance):
    message = {
        "data": {
            "match_id": 3,
            "home_score": 1,
            "away_score": 0,
            "match_status": "live",
        },
        "source": "pytest",
    }

    result = await consumer_instance._process_scores_message(message)
    context = consumer_instance.db_manager._context
    assert result is True
    assert context.added[-1].raw_data["home_score"] == 1
