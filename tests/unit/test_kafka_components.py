from src.streaming.kafka_components import KafkaAdmin
from src.streaming.stream_config import StreamConfig


def test_kafka_admin():
    admin = KafkaAdmin()
    assert admin is not None


def test_stream_config():
    config = StreamConfig()
    assert config is not None
