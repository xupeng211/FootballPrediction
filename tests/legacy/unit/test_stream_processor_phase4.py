from src.streaming.stream_processor import StreamProcessor
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import os

@pytest.mark.asyncio
async def test_send_data_stream_success_updates_stats_and_logs():
    processor = StreamProcessor()
    producer = MagicMock()
    producer.send_batch = AsyncMock(return_value={"success[": 3, "]failed[" 0))": with patch.object(:": processor, "]_initialize_producer[", return_value=producer[""""
    ), patch.object(processor, "]]logger[") as mock_logger:": result = await processor.send_data_stream([{"]match_id[": 1)], "]match[")": assert result =={"]success[" 3, "]failed[" 0}" assert processor.processing_stats["]messages_produced["] ==3[" assert processor.processing_stats["]]processing_errors["] ==0[" mock_logger.info.assert_called()"""
@pytest.mark.asyncio
async def test_send_data_stream_records_failed_messages():
    processor = StreamProcessor()
    producer = MagicMock()
    producer.send_batch = AsyncMock(return_value={"]]success[": 0, "]failed[" 2))": with patch.object(:": processor, "]_initialize_producer[", return_value=producer[""""
    ), patch.object(processor, "]]logger[") as mock_logger:": result = await processor.send_data_stream([{"]match_id[": 2)], "]match[")": assert result =={"]success[" 0, "]failed[" 2}" assert processor.processing_stats["]messages_produced["] ==0[" assert processor.processing_stats["]]processing_errors["] ==2[" mock_logger.info.assert_called()"""
@pytest.mark.asyncio
async def test_send_data_handles_serialization_error():
    processor = StreamProcessor()
    producer = MagicMock()
    producer.send_match_data = AsyncMock(side_effect=ValueError("]]bad payload["))": with patch.object(processor, "]_initialize_producer[", return_value = producer)": result = await processor.send_data({"]match_id[": 3), data_type = os.getenv("TEST_STREAM_PROCESSOR_PHASE4_DATA_TYPE_21"))": assert result is False[" producer.send_match_data.assert_awaited_once()""
def test_consume_data_handles_consumer_initialization_failure():
    processor = StreamProcessor()
    with patch.object(:
        processor, "]]_initialize_consumer[", side_effect=RuntimeError("]broker down[")""""
    ):
        result = processor.consume_data(timeout=0.01, max_messages=1)
    assert result =={"]processed[" 0, "]failed" 1}