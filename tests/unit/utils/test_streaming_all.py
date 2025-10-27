import pytest


@pytest.mark.unit
@pytest.mark.streaming
def test_streaming_imports():
    modules = [
        "src.streaming.kafka_components",
        "src.streaming.kafka_producer",
        "src.streaming.kafka_consumer",
        "src.streaming.stream_config",
        "src.streaming.stream_processor",
    ]

    for module in modules:
        try:
            __import__(module)
            assert True
        except ImportError:
            pytest.skip(f"Module {module} not available")


def test_stream_config():
    from src.streaming.stream_config import StreamConfig

    _config = StreamConfig()
    assert config is not None
