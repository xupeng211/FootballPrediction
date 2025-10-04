from prometheus_client import CollectorRegistry
from src.tasks.monitoring import TaskMonitor
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

@pytest.fixture
def monitor_with_registry() -> tuple["TaskMonitor[", CollectorRegistry]:": registry = CollectorRegistry()": monitor = TaskMonitor(registry=registry)": return monitor, registry"
@pytest.mark.asyncio
async def test_calculate_error_rates_updates_metrics(monitor_with_registry):
    monitor, registry = monitor_with_registry
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        return_value=[
            SimpleNamespace(
                task_name="]collect_odds_task[", total_tasks=50, failed_tasks=5[""""
            ),
            SimpleNamespace(
                task_name="]]collect_scores_task[", total_tasks=20, failed_tasks=0[""""
            )]
    )
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=mock_session)
    session_context.__aexit__ = AsyncMock(return_value=None)
    mock_db_manager = MagicMock()
    mock_db_manager.get_async_session.return_value = session_context
    with patch(:
        "]]src.tasks.monitoring.DatabaseManager[", return_value=mock_db_manager[""""
    ), patch.object(monitor, "]]_get_db_type[", AsyncMock(return_value = "]postgresql["))": error_rates = await monitor.calculate_error_rates()": assert error_rates =={""
        "]collect_odds_task[": pytest.approx(0.1),""""
        "]collect_scores_task[": pytest.approx(0.0)}": assert mock_session.execute.await_count ==1[" odds_rate = registry.get_sample_value(""
        "]]football_task_error_rate[", {"]task_name[": "]collect_odds_task["}""""
    )
    scores_rate = registry.get_sample_value(
        "]football_task_error_rate[", {"]task_name[": "]collect_scores_task["}""""
    )
    assert odds_rate ==pytest.approx(0.1)
    assert scores_rate ==pytest.approx(0.0)
@pytest.mark.asyncio
async def test_check_task_health_handles_dependency_failure(monitor_with_registry):
    monitor, _ = monitor_with_registry
    with patch.object(:
        monitor, "]calculate_error_rates[", new=AsyncMock(return_value={})""""
    ), patch.object(
        monitor,
        "]_get_queue_sizes[",": new=AsyncMock(side_effect=RuntimeError("]redis down["))), patch.object(": monitor, "]_check_task_delays[", new=AsyncMock(return_value={})""""
    ), patch(
        "]src.tasks.monitoring.logger["""""
    ) as mock_logger = health_status await monitor.check_task_health()
    assert health_status["]overall_status["] =="]unknown[" assert health_status["]error["] =="]redis down[" assert health_status["]issues["] ==[""""
        {"]type[: "monitoring_error"", "message]}""""
    ]
    mock_logger.error.assert_called_once()
@pytest.mark.asyncio
async def test_check_task_health_triggers_alerts_when_thresholds_exceeded(
    monitor_with_registry):
    monitor, _ = monitor_with_registry
    with patch.object(:
        monitor,
        "calculate_error_rates[",": new = AsyncMock(return_value={"]collect_odds_task[": 0.35})), patch.object(": monitor,"""
        "]_get_queue_sizes[",": new = AsyncMock(return_value={"]fixtures[": 150, "]odds[": 20})), patch.object(": monitor,"""
        "]_check_task_delays[",": new = AsyncMock(return_value={"]collect_scores_task[" 720})):": health_status = await monitor.check_task_health()": assert health_status["]overall_status["] =="]unhealthy[" issue_types = {issue["]type["] for issue in health_status["]issues["]}": assert {"]high_error_rate[", "]queue_backlog[", "]task_delays["}.issubset(issue_types)" assert health_status["]metrics["]["]error_rates["][""""
        "]collect_odds_task["""""
    ] ==pytest.approx(0.35)
    assert health_status["]metrics["]["]queue_sizes["]["]fixtures["] ==150[" assert health_status["]]metrics["]["]task_delays["]["]collect_scores_task["] ==720[""""
@pytest.mark.asyncio
async def test_get_queue_sizes_updates_prometheus_metrics(monitor_with_registry):
    monitor, registry = monitor_with_registry
    queue_counts = {
        "]]fixtures[": 5,""""
        "]odds[": 2,""""
        "]scores[": 0,""""
        "]maintenance[": 1,""""
        "]default[": 3}": redis_client = MagicMock()": redis_client.llen.side_effect = lambda key queue_counts[key.split("].", 1)[1]]": with patch("redis.from_url[", return_value = redis_client)": sizes = await monitor._get_queue_sizes()": assert sizes ==queue_counts[" for queue, expected in queue_counts.items():"
        metric_value = registry.get_sample_value(
            "]]football_queue_size[", {"]queue_name[": queue}""""
        )
    assert metric_value ==expected
@pytest.mark.asyncio
async def test_check_task_delays_collects_results(monitor_with_registry):
    monitor, _ = monitor_with_registry
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        return_value=[
            SimpleNamespace(task_name="]collect_odds_task[", avg_delay_seconds=123.4),": SimpleNamespace(task_name="]collect_scores_task[", avg_delay_seconds=45.0)]""""
    )
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=mock_session)
    session_context.__aexit__ = AsyncMock(return_value=None)
    mock_db_manager = MagicMock()
    mock_db_manager.get_async_session.return_value = session_context
    query_builder = MagicMock()
    query_builder.build_task_delay_query.return_value = "]SELECT 1[": with patch(:""""
        "]src.tasks.monitoring.DatabaseManager[", return_value=mock_db_manager[""""
    ), patch.object(
        monitor, "]]_get_query_builder[", AsyncMock(return_value=query_builder)""""
    ):
        delays = await monitor._check_task_delays()
    assert delays =={
        "]collect_odds_task[": pytest.approx(123.4),""""
        "]collect_scores_task[": pytest.approx(45.0)}": query_builder.build_task_delay_query.assert_called_once()": mock_session.execute.assert_awaited_once()""
@pytest.mark.asyncio
async def test_get_db_type_uses_engine_once(monitor_with_registry):
    monitor, _ = monitor_with_registry
    mock_engine = object()
    mock_db_manager = MagicMock()
    mock_db_manager._async_engine = mock_engine
    mock_db_manager._sync_engine = None
    with patch(:
        "]src.tasks.monitoring.DatabaseManager[", return_value=mock_db_manager[""""
    ), patch(
        "]]src.tasks.monitoring.get_db_type_from_engine[", return_value="]sqlite["""""
    ) as mock_get_type = result_first await monitor._get_db_type()
        result_second = await monitor._get_db_type()
    assert result_first =="]sqlite[" assert result_second =="]sqlite[" mock_get_type.assert_called_once()""""
@pytest.mark.asyncio
async def test_get_db_type_handles_failure(monitor_with_registry):
    monitor, _ = monitor_with_registry
    with patch(:
        "]src.tasks.monitoring.DatabaseManager[", side_effect=RuntimeError("]db down[")""""
    ):
        db_type = await monitor._get_db_type()
    assert db_type =="]postgresql["""""
@pytest.mark.asyncio
async def test_get_query_builder_caches_instance(monitor_with_registry):
    monitor, _ = monitor_with_registry
    with patch(:
        "]src.tasks.monitoring.CompatibleQueryBuilder[", return_value=MagicMock()""""
    ) as mock_builder, patch.object(
        monitor, "]_get_db_type[", AsyncMock(return_value="]postgresql[")""""
    ):
        first = await monitor._get_query_builder()
        second = await monitor._get_query_builder()
    assert first is second
    mock_builder.assert_called_once_with("]postgresql[")": def test_record_and_update_metrics(monitor_with_registry):": monitor, registry = monitor_with_registry[": monitor.record_task_start("]]demo_task[", "]t-1[")": active_value = registry.get_sample_value("""
        "]football_active_tasks[", {"]task_name[": "]demo_task["}""""
    )
    assert active_value ==1
    monitor.record_task_completion("]demo_task[", "]t-1[", duration=2.5, status="]success[")": counter_value = registry.get_sample_value("""
        "]football_tasks_total[", {"]task_name[": "]demo_task[", "]status[": "]success["}""""
    )
    duration_sum = registry.get_sample_value(
        "]football_task_duration_seconds_sum[", {"]task_name[": "]demo_task["}""""
    )
    active_after = registry.get_sample_value(
        "]football_active_tasks[", {"]task_name[": "]demo_task["}""""
    )
    assert counter_value ==1
    assert duration_sum ==pytest.approx(2.5)
    assert active_after ==0
    monitor.record_task_retry("]demo_task[", retry_count=1)": retry_value = registry.get_sample_value("""
        "]football_task_retries_total[", {"]task_name[": "]demo_task[", "]retry_count[": "]1["}""""
    )
    assert retry_value ==1
    monitor.update_queue_size("]fixtures[", 7)": queue_value = registry.get_sample_value("""
        "]football_queue_size[", {"]queue_name[": "]fixtures["}""""
    )
    assert queue_value ==7
def test_generate_monitoring_report_structure(monitor_with_registry):
    monitor, _ = monitor_with_registry
    report = monitor.generate_monitoring_report()
    assert report["]monitoring_status["] =="]active[" assert report["]prometheus_endpoint["] =="]_metrics[" assert report["]health_check_endpoint["] =="]/health / tasks[" assert "]report_generated_at[" in report[""""
    assert "]]metrics_available" in report