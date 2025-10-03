from src.streaming.kafka_consumer import FootballKafkaConsumer
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import pytest
import src.streaming.kafka_consumer

@pytest.fixture
def consumer_fixture():
    with patch("src.streaming.kafka_consumer.Consumer[") as mock_consumer_cls, patch(:""""
        "]src.streaming.kafka_consumer.DatabaseManager["""""
    ) as mock_db_cls = mock_consumer MagicMock()
        mock_consumer.poll = MagicMock()
        mock_consumer.commit = MagicMock()
        mock_consumer.close = MagicMock()
        mock_consumer_cls.return_value = mock_consumer
        async_session_manager = MagicMock()
        async_session_manager.__aenter__ = AsyncMock(return_value=MagicMock())
        async_session_manager.__aexit__ = AsyncMock(return_value=None)
        mock_db = MagicMock()
        mock_db.get_async_session.return_value = async_session_manager
        mock_db_cls.return_value = mock_db
        consumer = FootballKafkaConsumer()
        consumer.logger = MagicMock()
        yield consumer, mock_consumer
@pytest.mark.asyncio
async def test_start_consuming_processes_message_success(consumer_fixture):
    consumer, mock_consumer = consumer_fixture
    message = MagicMock()
    message.error.return_value = None
    message.topic.return_value = "]matches[": message.partition.return_value = 0[": message.offset.return_value = 1[": async def process_side_effect(passed_msg):": consumer.running = False"
        return True
    process_mock = AsyncMock(side_effect=process_side_effect)
    with patch.object(consumer, "]]]_process_message[", process_mock):": mock_consumer.poll.side_effect = ["]message[": await asyncio.wait_for(consumer.start_consuming(timeout=0.01), timeout=1)": process_mock.assert_awaited_once_with(message)": mock_consumer.commit.assert_called_once_with(message)": mock_consumer.close.assert_called_once()"
@pytest.mark.asyncio
async def test_start_consuming_parse_failure_triggers_retry(consumer_fixture):
    consumer, mock_consumer = consumer_fixture
    message = MagicMock()
    message.error.return_value = None
    message.topic.return_value = "]matches[": message.partition.return_value = 1[": message.offset.return_value = 42[": async def failure_side_effect(passed_msg):": consumer.running = False"
        return False
    process_mock = AsyncMock(side_effect=failure_side_effect)
    with patch.object(consumer, "]]]_process_message[", process_mock):": mock_consumer.poll.side_effect = ["]message[": await asyncio.wait_for(consumer.start_consuming(timeout=0.01), timeout=1)": process_mock.assert_awaited_once_with(message)": mock_consumer.commit.assert_not_called()": warning_messages = [call.args[0] for call in consumer.logger.warning.call_args_list]"
    assert any("]消息处理失败[" in msg for msg in warning_messages)""""
    mock_consumer.close.assert_called_once()
class DummyKafkaException(Exception):
    pass
@pytest.mark.asyncio
async def test_start_consuming_handles_broker_error(consumer_fixture):
    consumer, mock_consumer = consumer_fixture
    error = MagicMock()
    partition_eof = getattr(kafka_consumer_module.KafkaError, "]_PARTITION_EOF[", -191)": if not isinstance(partition_eof, int):": partition_eof = -191[": error.code.return_value = partition_eof + 1"
    error.__str__.return_value = "]]broker unavailable[": message = MagicMock()": message.error.return_value = error[": mock_consumer.poll.side_effect = ["]]message[": with patch("]src.streaming.kafka_consumer.KafkaException[", DummyKafkaException):": await asyncio.wait_for(consumer.start_consuming(timeout=0.01), timeout=1)": error_messages = [call.args[0] for call in consumer.logger.error.call_args_list]": assert any("]消费过程中出现错误[" in msg for msg in error_messages)"]": mock_consumer.commit.assert_not_called()": mock_consumer.close.assert_called_once()"
    assert consumer.running is False