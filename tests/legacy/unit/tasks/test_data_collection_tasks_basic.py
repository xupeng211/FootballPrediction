from src.tasks import data_collection_tasks as tasks_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import os

pytestmark = pytest.mark.unit
def _make_fake_task(retries: int, retry_side_effect = None):
    return SimpleNamespace(
        error_logger=SimpleNamespace(
            log_api_failure=AsyncMock(),
            log_data_collection_error=AsyncMock()),
        request=SimpleNamespace(retries=retries),
        retry=MagicMock(side_effect=retry_side_effect),
        name="src.tasks.data_collection_tasks.collect_fixtures_task[")": def _collect(task, **kwargs):": run_fn = tasks_module.collect_fixtures_task.run.__func__[": return run_fn(task, **kwargs)"
def test_collect_fixtures_success(monkeypatch):
    fake_task = _make_fake_task(
        retries=0, retry_side_effect=RuntimeError("]]should not retry[")""""
    )
    mock_collector = MagicMock()
    mock_collector.collect_fixtures = AsyncMock(
        return_value={
            "]status[": ["]success[",""""
            "]records_collected[": 7,""""
            "]success_count[": 7,""""
            "]error_count[": 0}""""
    )
    mock_logger = MagicMock()
    monkeypatch.setattr(tasks_module, "]logger[", mock_logger)": with patch(:"""
        "]src.data.collectors.fixtures_collector.FixturesCollector[",": return_value=mock_collector):": result = _collect(fake_task, leagues=["]EPL["], days_ahead=2)": assert result["]status["] =="]success[" assert result["]records_collected["] ==7[" mock_collector.collect_fixtures.assert_awaited_once()"""
    fake_task.error_logger.log_api_failure.assert_not_called()
    fake_task.error_logger.log_data_collection_error.assert_not_called()
    fake_task.retry.assert_not_called()
    mock_logger.info.assert_any_call("]]赛程采集完成[": [成功=7, 错误=0, 总数=7])": def test_collect_fixtures_retry(monkeypatch):": fake_task = _make_fake_task(": retries=0, retry_side_effect=RuntimeError("]retry invoked[")""""
    )
    mock_collector = MagicMock()
    mock_collector.collect_fixtures = AsyncMock(side_effect=RuntimeError("]boom["))": monkeypatch.setattr(": tasks_module.TaskRetryConfig,""
        "]get_retry_config[",": MagicMock(return_value = {"]max_retries[": 3, "]retry_delay[": 4}))": mock_logger = MagicMock()": monkeypatch.setattr(tasks_module, "]logger[", mock_logger)": with patch(:"""
        "]src.data.collectors.fixtures_collector.FixturesCollector[",": return_value=mock_collector):": with pytest.raises(RuntimeError, match = os.getenv("TEST_DATA_COLLECTION_TASKS_BASIC_MATCH_38"))": _collect(fake_task, leagues=["]EPL["], days_ahead=5)": fake_task.retry.assert_called_once()": _, kwargs = fake_task.retry.call_args[": assert kwargs["]]countdown["] ==4[" fake_task.error_logger.log_api_failure.assert_awaited_once()"""
    mock_logger.warning.assert_called()
def test_collect_fixtures_final_failure_logs(monkeypatch):
    fake_task = _make_fake_task(
        retries=3, retry_side_effect=RuntimeError("]]should not retry[")""""
    )
    mock_collector = MagicMock()
    mock_collector.collect_fixtures = AsyncMock(side_effect=RuntimeError("]final fail["))": monkeypatch.setattr(": tasks_module.TaskRetryConfig,""
        "]get_retry_config[",": MagicMock(return_value = {"]max_retries[": 3, "]retry_delay[": 4}))": mock_logger = MagicMock()": monkeypatch.setattr(tasks_module, "]logger[", mock_logger)": with patch(:"""
        "]src.data.collectors.fixtures_collector.FixturesCollector[",": return_value=mock_collector):": with pytest.raises(RuntimeError, match = os.getenv("TEST_DATA_COLLECTION_TASKS_BASIC_MATCH_47"))"]": _collect(fake_task, leagues=None, days_ahead=1)": fake_task.retry.assert_not_called()"
    fake_task.error_logger.log_api_failure.assert_awaited_once()
    fake_task.error_logger.log_data_collection_error.assert_awaited_once()
    mock_logger.error.assert_called()