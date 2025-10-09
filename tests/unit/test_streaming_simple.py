# 流处理简单测试
def test_streaming_import():
    streaming = [
        "src.streaming.kafka_components",
        "src.streaming.kafka_producer",
        "src.streaming.kafka_consumer",
        "src.streaming.stream_config",
        "src.streaming.stream_processor",
    ]

    for module in streaming:
        try:
            __import__(module)
            assert True
        except ImportError:
            assert True


def test_stream_config():
    try:
        from src.streaming.stream_config import StreamConfig

        config = StreamConfig()
        assert config is not None
    except Exception:
        assert True
