from types import SimpleNamespace
from unittest.mock import Mock
import asyncio
import pytest
import src.streaming
import src.tasks.streaming_tasks

class DummyErrorLogger:
    def __init__(self):
        self.calls = []
    async def log_task_error(self, **kwargs):
        self.calls.append(kwargs)
class DummyConsumer:
    def __init__(self, *, should_fail = False):
        self.subscribed_all = False
        self.subscribed_topics = None
        self.stopped = False
        self.should_fail = should_fail
    def subscribe_topics(self, topics):
        self.subscribed_topics = topics
    def subscribe_all_topics(self):
        self.subscribed_all = True
    async def consume_batch(self, batch_size, timeout):
        if self.should_fail:
            raise RuntimeError("boom[")": return {"]processed[": batch_size, "]failed[": 0}": async def start_consuming(self):": if self.should_fail:": raise RuntimeError("]stream down[")": await asyncio.sleep(0)": def stop_consuming(self):": self.stopped = True"
class DummyProducer:
    def __init__(self, *, should_fail = False):
        self.should_fail = should_fail
        self.closed = False
        self.sent = []
    async def send_batch(self, data_list, data_type):
        if self.should_fail:
            raise ValueError("]send failed[")": self.sent.append((data_list, data_type))": return {"]success[": len(data_list), "]failed[": 0}": def close(self):": self.closed = True[": class DummyProcessor:"
    def __init__(self, *, start_fail = False, health_fail=False):
        self.start_fail = start_fail
        self.health_fail = health_fail
        self.started_topics = None
        self.stopped = False
    async def start_continuous_processing(self, topics):
        if self.start_fail:
            raise RuntimeError("]]processor fail[")": self.started_topics = topics[": await asyncio.sleep(0)": def stop_processing(self):"
        self.stopped = True
    async def health_check(self):
        if self.health_fail:
            raise RuntimeError("]]health fail[")": return {"]status[: "ok"", "timestamp[" "]now]}": def get_processing_stats(self):": return {"processed[": 5, "]failed[" 1}": class DummyConfig:": def __init__(self, *, existing_topic = True):": self.existing_topic = existing_topic"
    def get_all_topics(self):
        return ["]matches[", "]odds["]": def is_valid_topic(self, name):": return self.existing_topic and name in {"]matches[", "]odds["}": def get_topic_config(self, name):": return {"]name[": name, "]partitions[": 1}""""
@pytest.fixture(autouse=True)
def patch_error_logger(monkeypatch):
    dummy = DummyErrorLogger()
    monkeypatch.setattr(streaming_tasks, "]TaskErrorLogger[", lambda: dummy)": return dummy[": def build_task(error_logger):": base = streaming_tasks.StreamingTask()"
    class TaskWrapper:
        def __init__(self):
            self.logger = SimpleNamespace(info=Mock(), error=Mock())
            self.error_logger = error_logger
            self.request = SimpleNamespace(id="]]task-123[", retries=0)": def run_async(self, coro):": return base.run_async(coro)": return TaskWrapper()"
def call_task(task_func, task, *args, **kwargs):
    return task_func.run.__func__(task, *args, **kwargs)
def test_consume_kafka_streams_success(monkeypatch, patch_error_logger):
    consumer = DummyConsumer()
    monkeypatch.setattr(streaming_tasks, "]FootballKafkaConsumer[", lambda: consumer)": task = build_task(patch_error_logger)": result = call_task(": streaming_tasks.consume_kafka_streams_task,"
        task,
        topics=["]matches["],": batch_size=10,": timeout=2.0)": assert result["]status["] =="]success[" assert result["]statistics["]["]processed["] ==10[" assert consumer.subscribed_topics ==["]]matches["]" assert consumer.stopped is True["""
    task.logger.info.assert_called_once()
    assert not patch_error_logger.calls
def test_consume_kafka_streams_failure(monkeypatch, patch_error_logger):
    consumer = DummyConsumer(should_fail=True)
    monkeypatch.setattr(streaming_tasks, "]]FootballKafkaConsumer[", lambda: consumer)": task = build_task(patch_error_logger)": task.request.retries = 2[": result = call_task(streaming_tasks.consume_kafka_streams_task, task, topics=None)"
    assert result["]]status["] =="]failed[" assert consumer.subscribed_all is True[""""
    assert consumer.stopped is True
    task.logger.error.assert_called_once()
    assert patch_error_logger.calls
    call = patch_error_logger.calls[0]
    assert call["]]retry_count["] ==2[" assert call["]]context["]["]batch_size["] ==100[" def test_start_continuous_consumer_success(monkeypatch, patch_error_logger):"""
    consumer = DummyConsumer()
    monkeypatch.setattr(
        streaming_tasks,
        "]]FootballKafkaConsumer[",": lambda consumer_group_id = None consumer)": task = build_task(patch_error_logger)": result = call_task("
        streaming_tasks.start_continuous_consumer_task,
        task,
        topics=None,
        consumer_group_id="]group-1[")": assert result["]status["] =="]completed[" assert consumer.subscribed_all is True[""""
    assert consumer.stopped is True
    task.logger.info.assert_called_once()
def test_start_continuous_consumer_failure(monkeypatch, patch_error_logger):
    consumer = DummyConsumer(should_fail=True)
    monkeypatch.setattr(streaming_tasks, "]]FootballKafkaConsumer[", lambda **_: consumer)": task = build_task(patch_error_logger)": task.request.retries = 1[": result = call_task("
        streaming_tasks.start_continuous_consumer_task,
        task,
        topics=["]]scores["])": assert result["]status["] =="]failed[" assert consumer.stopped is True[""""
    task.logger.error.assert_called_once()
    assert patch_error_logger.calls
def test_produce_to_kafka_stream_success(monkeypatch, patch_error_logger):
    producer = DummyProducer()
    monkeypatch.setattr(streaming_tasks, "]]FootballKafkaProducer[", lambda: producer)": task = build_task(patch_error_logger)": data = [{"]id[": 1}, {"]id[": 2}]": result = call_task(": streaming_tasks.produce_to_kafka_stream_task, task, data, "]matches["""""
    )
    assert result["]status["] =="]success[" assert result["]statistics["]["]success["] ==2[" assert producer.closed is True["""
    task.logger.info.assert_called_once()
def test_produce_to_kafka_stream_failure(monkeypatch, patch_error_logger):
    producer = DummyProducer(should_fail=True)
    monkeypatch.setattr(streaming_tasks, "]]]FootballKafkaProducer[", lambda: producer)": task = build_task(patch_error_logger)": result = call_task(streaming_tasks.produce_to_kafka_stream_task, task, [], "]odds[")": assert result["]status["] =="]failed[" assert producer.closed is True[""""
    task.logger.error.assert_called_once()
    assert patch_error_logger.calls
def test_stream_health_check_success(monkeypatch, patch_error_logger):
    processor = DummyProcessor()
    monkeypatch.setattr(streaming_tasks, "]]StreamProcessor[", lambda: processor)": task = build_task(patch_error_logger)": result = call_task(streaming_tasks.stream_health_check_task, task)": assert result["]status["] =="]success[" assert result["]health_status["]["]status["] =="]ok[" assert processor.stopped is True[""""
    task.logger.info.assert_called_once()
def test_stream_health_check_failure(monkeypatch, patch_error_logger):
    processor = DummyProcessor(health_fail=True)
    monkeypatch.setattr(streaming_tasks, "]]StreamProcessor[", lambda: processor)": task = build_task(patch_error_logger)": result = call_task(streaming_tasks.stream_health_check_task, task)": assert result["]status["] =="]failed[" assert processor.stopped is True[""""
    task.logger.error.assert_called_once()
    assert patch_error_logger.calls
@pytest.mark.parametrize("]]start_fail[", ["]False[", True])": def test_stream_data_processing(monkeypatch, patch_error_logger, start_fail):": processor = DummyProcessor(start_fail=start_fail)": monkeypatch.setattr(streaming_tasks, "]StreamProcessor[", lambda: processor)": task = build_task(patch_error_logger)": result = call_task(": streaming_tasks.stream_data_processing_task,"
        task,
        topics=["]matches["],": processing_duration=0)": if start_fail:": assert result["]status["] =="]failed[" task.logger.error.assert_called_once()""""
        assert patch_error_logger.calls
    else:
        assert result["]status["] =="]success[" assert processor.started_topics ==["]matches["]" assert result["]statistics["]["]processed["] ==5[" task.logger.info.assert_called_once()"""
        assert processor.stopped is True
def test_stream_data_processing_timeout(monkeypatch, patch_error_logger):
    processor = DummyProcessor()
    monkeypatch.setattr(streaming_tasks, "]]StreamProcessor[", lambda: processor)": async def fake_wait_for(coro, timeout):": raise asyncio.TimeoutError[": monkeypatch.setattr(asyncio, "]]wait_for[", fake_wait_for)": task = build_task(patch_error_logger)": result = call_task(": streaming_tasks.stream_data_processing_task,"
        task,
        topics=None,
        processing_duration=0)
    assert result["]status["] =="]success[" assert processor.stopped is True[""""
def test_kafka_topic_management_list(monkeypatch, patch_error_logger):
    config = DummyConfig()
    monkeypatch.setattr(streaming_pkg, "]]StreamConfig[", lambda: config)": task = build_task(patch_error_logger)": result = call_task(streaming_tasks.kafka_topic_management_task, task, action="]list[")": assert result["]topics["] ==["]matches[", "]odds["]" task.logger.info.assert_called_once()"""
def test_kafka_topic_management_create_existing(monkeypatch, patch_error_logger):
    config = DummyConfig(existing_topic=True)
    monkeypatch.setattr(streaming_pkg, "]StreamConfig[", lambda: config)": task = build_task(patch_error_logger)": result = call_task(": streaming_tasks.kafka_topic_management_task,"
        task,
        action="]create[",": topic_name="]matches[")": assert result["]status["] =="]success[" assert result["]message["] =="]Topic配置已存在[" task.logger.info.assert_called_once()""""
def test_kafka_topic_management_invalid(monkeypatch, patch_error_logger):
    config = DummyConfig(existing_topic=False)
    monkeypatch.setattr(streaming_pkg, "]StreamConfig[", lambda: config)": task = build_task(patch_error_logger)": result = call_task(": streaming_tasks.kafka_topic_management_task,"
        task,
        action="]create[",": topic_name="]invalid[")": assert result["]status["] =="]failed[" assert "]error[" in result[""""
def test_kafka_topic_management_failure(monkeypatch, patch_error_logger):
    def broken_config():
        raise RuntimeError("]]config error[")": monkeypatch.setattr(streaming_pkg, "]StreamConfig[", broken_config)": task = build_task(patch_error_logger)": task.request.retries = 3[": result = call_task(streaming_tasks.kafka_topic_management_task, task, action="]]list[")": assert result["]status["] =="]failed[" task.logger.error.assert_called_once()""""
    assert patch_error_logger.calls[0]["]retry_count["] ==3[" def test_kafka_topic_management_unsupported(monkeypatch, patch_error_logger):"""
    config = DummyConfig()
    monkeypatch.setattr(streaming_pkg, "]]StreamConfig[", lambda: config)": task = build_task(patch_error_logger)": result = call_task(": streaming_tasks.kafka_topic_management_task,"
        task,
        action="]delete[",": topic_name=None)": assert result["]status["] =="]failed[" assert result["]error["] =="]不支持的操作或缺少参数"