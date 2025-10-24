from src.streaming.stream_processor import StreamProcessor
import pytest


@pytest.mark.unit

def test_stream_processor():
    processor = StreamProcessor()
    assert processor is not None


def test_processor_methods():
    processor = StreamProcessor()
    assert hasattr(processor, "process_stream")
    assert hasattr(processor, "handle_message")
