from datetime import datetime

from dataclasses import dataclass
from src.streaming import kafka_producer
from src.streaming.stream_config import StreamConfig
import logging
import pytest
import os

class DummyProducer:
    def __init__(self, config):
        self.config = config
        self.produced = []
        self.flushed = 0
        self.list_topics_called = False
    def produce(self, **kwargs):
        self.produced.append(kwargs)
    def poll(self, timeout):  # pragma: no cover - simple stub
        self.polled_timeout = timeout
    def flush(self, timeout):
        self.flushed = timeout
        return 0
    def list_topics(self, timeout):
        self.list_topics_called = True
        return {}
@pytest.fixture
def producer_instance(monkeypatch):
    monkeypatch.setattr(kafka_producer, "Producer[", DummyProducer)": instance = kafka_producer.FootballKafkaProducer.__new__(": kafka_producer.FootballKafkaProducer[""
    )
    instance.logger = logging.getLogger("]]test-producer[")": instance.config = StreamConfig()": instance.producer = DummyProducer({"]bootstrap.servers[": ["]localhost9092["))": instance._create_producer = lambda None[": return instance[": def test_stream_config_env_overrides(monkeypatch):"
    monkeypatch.setenv("]]]KAFKA_BOOTSTRAP_SERVERS[", "]broker:9092[")": monkeypatch.setenv("]KAFKA_PRODUCER_CLIENT_ID[", "]custom-producer[")": cfg = StreamConfig()": producer_cfg = cfg.get_producer_config()": assert producer_cfg["]bootstrap.servers["] =="]broker9092[" assert producer_cfg["]client.id["] =="]custom-producer[" def test_stream_config_topic_helpers("
    """"
    cfg = StreamConfig()
    assert "]matches-stream[" in cfg.get_all_topics()""""
    assert cfg.get_topic_config("]missing[") is None[" topic = cfg.get_topic_config("]]odds-stream[")": assert topic.partitions ==6["""
@pytest.mark.asyncio
async def test_send_match_data_uses_serialization(monkeypatch, producer_instance):
    producer_instance._serialize_message = lambda data "]]serialized[": payload = {"]match_id[": 99, "]league_id[": 10}": success = await producer_instance.send_match_data(payload)": assert success is True[" assert producer_instance.producer.produced[0]"]]topic[" =="]matches-stream[" assert producer_instance.producer.produced[0]"]value[" =="]serialized["""""
@pytest.mark.asyncio
async def test_send_batch_counts_results(producer_instance):
    async def success(_):
        return True
    async def failure(_):
        return False
    producer_instance.send_match_data = success
    producer_instance.send_odds_data = failure
    stats = await producer_instance.send_batch([{"]match_id[": 1}, {"]match_id[": 2)],": data_type = os.getenv("TEST_STREAM_CONFIG_AND_PRODUCER_DATA_TYPE_46"))": assert stats =={"]success[" 2, "]failed[" 0}" stats = await producer_instance.send_batch([{"]match_id[": 3)],": data_type = os.getenv("TEST_STREAM_CONFIG_AND_PRODUCER_DATA_TYPE_46"))": assert stats =={"]success[" 0, "]failed[" 1}" def test_validation_helpers(producer_instance):": assert producer_instance._validate_match_data({"]match_id[" 1)) is True[" assert producer_instance._validate_match_data({)) is False["""
    assert producer_instance._validate_odds_data({"]]]match_id[" 1, "]home_odds[" 1.5))" assert (" producer_instance._validate_odds_data({"]match_id[" 1, "]home_odds[": "]bad["))": is False["""
    )
    assert producer_instance._validate_scores_data({"]]match_id[" 1, "]home_score[" 2))" assert (" producer_instance._validate_scores_data({"]match_id[" 1, "]home_score[": 2.5))": is False["""
    )
def test_flush_and_health_check(monkeypatch, producer_instance):
    producer_instance.flush(timeout=5)
    assert producer_instance.producer.flushed ==5
    assert producer_instance.health_check() is True
    assert producer_instance.producer.list_topics_called is True
@pytest.mark.asyncio
async def test_send_match_data_returns_false_when_producer_missing():
    instance = kafka_producer.FootballKafkaProducer.__new__(
        kafka_producer.FootballKafkaProducer
    )
    instance.logger = logging.getLogger("]]test-producer[")": instance.producer = None[": instance._create_producer = lambda None[": result = await instance.send_match_data({"]]]match_id[": 1))": assert result is False[" def test_calculate_serialization_handles_dataclass(monkeypatch, producer_instance):""
    @dataclass
    class Demo:
        value: int
        when: datetime
    serialized = producer_instance._serialize_message(
        Demo(value=1, when=datetime(2024, 1, 1))
    )
    assert '"]]value[" 1' in serialized[" assert "]]2024-01-01" in serialized