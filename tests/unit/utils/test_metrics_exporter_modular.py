from unittest.mock import MagicMock, patch

"""
测试模块化的指标导出器
Test Modular Metrics Exporter
"""

import time
from datetime import datetime

import pytest
from prometheus_client import CollectorRegistry


@pytest.mark.unit
def test_metric_definitions():
    """测试指标定义"""
    from src.monitoring.metrics_exporter_mod.metric_definitions import (
        MetricsDefinitions, _MockCounter, _MockGauge, _MockHistogram)

    # 创建独立注册表用于测试
    registry = CollectorRegistry()
    defs = MetricsDefinitions(registry=registry)

    # 检查所有指标都已创建
    assert defs.data_collection_total is not None
    assert defs.data_collection_errors is not None
    assert defs.data_collection_duration is not None
    assert defs.data_cleaning_total is not None
    assert defs.scheduler_task_delay is not None
    assert defs.table_row_count is not None
    assert defs.system_info is not None

    # 测试Mock指标
    mock_counter = _MockCounter()
    mock_counter.inc()
    mock_counter.labels(test="value")

    mock_gauge = _MockGauge()
    mock_gauge.set(1.0)
    mock_gauge.labels(test="value")


def test_data_collection_metrics():
    """测试数据采集指标记录"""
    from src.monitoring.metrics_exporter_mod.data_collection_metrics import \
        DataCollectionMetrics
    from src.monitoring.metrics_exporter_mod.metric_definitions import \
        MetricsDefinitions

    registry = CollectorRegistry()
    defs = MetricsDefinitions(registry=registry)
    metrics = DataCollectionMetrics(defs)

    # 记录成功的采集
    metrics.record_success("api_source", 10, "fixtures", 1.5)

    # 记录失败的采集
    metrics.record_failure("api_source", "timeout", "fixtures", 2.0)

    # 记录详细的采集
    metrics.record_collection(
        data_source="api_source",
        collection_type="odds",
        success=True,
        duration=0.5,
        records_count=5,
    )

    # 批量记录
    collections = [
        {
            "data_source": "source1",
            "collection_type": "fixtures",
            "success": True,
            "duration": 1.0,
            "records_count": 3,
        },
        {
            "data_source": "source2",
            "collection_type": "odds",
            "success": False,
            "duration": 2.0,
            "error_type": "network_error",
        },
    ]
    metrics.record_batch(collections)


def test_data_cleaning_metrics():
    """测试数据清洗指标记录"""
    from src.monitoring.metrics_exporter_mod.data_cleaning_metrics import \
        DataCleaningMetrics
    from src.monitoring.metrics_exporter_mod.metric_definitions import \
        MetricsDefinitions

    registry = CollectorRegistry()
    defs = MetricsDefinitions(registry=registry)
    metrics = DataCleaningMetrics(defs)

    # 记录成功的清洗
    metrics.record_success(100, "matches", 0.5)

    # 记录失败的清洗
    metrics.record_failure("matches", "invalid_format", 1.0)

    # 记录详细的清洗
    metrics.record_cleaning(
        data_type="odds", success=True, duration=0.3, records_processed=50
    )


def test_scheduler_metrics():
    """测试调度器指标记录"""
    from src.monitoring.metrics_exporter_mod.metric_definitions import \
        MetricsDefinitions
    from src.monitoring.metrics_exporter_mod.scheduler_metrics import \
        SchedulerMetrics

    registry = CollectorRegistry()
    defs = MetricsDefinitions(registry=registry)
    metrics = SchedulerMetrics(defs)

    # 记录详细的任务执行
    scheduled_time = datetime.now()
    start_time = datetime.now()
    duration = 5.0

    metrics.record_task(
        task_name="data_collection",
        scheduled_time=scheduled_time,
        actual_start_time=start_time,
        duration=duration,
        success=True,
    )

    # 记录失败的任务
    metrics.record_task(
        task_name="data_cleaning",
        scheduled_time=scheduled_time,
        actual_start_time=start_time,
        duration=2.0,
        success=False,
        failure_reason="memory_error",
    )

    # 使用简化接口
    metrics.record_task_simple("test_task", "success", 1.0)
    metrics.record_task_simple("test_task2", "failed", 2.0)

    # 记录延迟
    metrics.record_delay("delayed_task", 10.5)

    # 记录失败
    metrics.record_failure("failed_task", "resource_limit")


def test_database_metrics():
    """测试数据库指标记录"""
    from src.monitoring.metrics_exporter_mod.database_metrics import \
        DatabaseMetrics
    from src.monitoring.metrics_exporter_mod.metric_definitions import \
        MetricsDefinitions

    registry = CollectorRegistry()
    defs = MetricsDefinitions(registry=registry)
    metrics = DatabaseMetrics(defs, ["matches", "teams", "odds"])

    # 测试设置表监控列表
    metrics.set_tables_to_monitor(["matches", "teams"])
    assert metrics.get_monitored_tables() == ["matches", "teams"]

    # 测试表名验证
    assert not metrics._is_safe_table_name("")  # 空字符串
    assert not metrics._is_safe_table_name("matches; DROP TABLE")  # SQL注入
    assert metrics._is_safe_table_name("valid_table_name")  # 有效名称

    # 测试更新表行数（测试模式）
    table_counts = {"matches": 100, "teams": 20, "odds": 500}

    # 使用mock避免实际数据库操作
    with patch.object(defs.table_row_count, "labels") as mock_labels:
        mock_gauge = MagicMock()
        mock_labels.return_value = mock_gauge
        import asyncio

        # 创建新事件循环运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(metrics.update_table_row_counts(table_counts))
        finally:
            loop.close()

    # 记录查询耗时
    metrics.record_query_duration("SELECT", 0.1)


def test_metrics_exporter():
    """测试主导出器"""
    from src.monitoring.metrics_exporter_mod.metrics_exporter import \
        MetricsExporter

    # 创建独立注册表用于测试
    registry = CollectorRegistry()
    exporter = MetricsExporter(registry=registry)

    # 测试数据采集接口
    exporter.record_data_collection_success("test_source", 5)
    exporter.record_data_collection_failure("test_source", "timeout")
    exporter.record_data_collection(
        data_source="api",
        collection_type="fixtures",
        success=True,
        duration=1.0,
        records_count=10,
    )

    # 测试数据清洗接口
    exporter.record_data_cleaning_success(50)
    exporter.record_data_cleaning(
        data_type="matches", success=True, duration=0.5, records_processed=20
    )

    # 测试调度器接口
    exporter.record_scheduler_task_simple("test_task", "success", 1.5)
    exporter.record_scheduler_task(
        task_name="daily_job",
        scheduled_time=datetime.now(),
        actual_start_time=datetime.now(),
        duration=10.0,
        success=False,
        failure_reason="timeout",
    )

    # 测试数据库接口
    exporter.update_table_row_counts({"matches": 100})
    exporter.set_tables_to_monitor(["matches", "teams"])

    # 获取指标数据
    content_type, metrics_data = exporter.get_metrics()
    assert content_type == "text/plain; version=0.0.4; charset=utf-8"
    assert "football_" in metrics_data

    # 获取指标摘要
    summary = exporter.get_metric_summary()
    assert "total_metrics" in summary
    assert "metrics_by_type" in summary
    assert "metric_names" in summary


def test_utils():
    """测试工具函数"""
    from src.monitoring.metrics_exporter_mod.utils import (
        calculate_delay_seconds, filter_metrics_by_prefix, safe_cast_to_float,
        validate_table_name)

    # 测试表名验证
    assert validate_table_name("valid_table")
    assert not validate_table_name("invalid-table;")
    assert not validate_table_name("")

    # 测试延迟计算
    now = datetime.now()
    later = datetime.fromtimestamp(now.timestamp() + 10)
    assert calculate_delay_seconds(now, later) == 10.0
    assert calculate_delay_seconds(later, now) == -10.0

    # 测试类型转换
    assert safe_cast_to_float("10.5") == 10.5
    assert safe_cast_to_float("invalid", 0.0) == 0.0
    assert safe_cast_to_float(None, 1.0) == 1.0

    # 测试指标过滤
    metrics_data = """# HELP football_test_metric Test metric
# TYPE football_test_metric counter
football_test_metric{label="value"} 10
other_metric 5
# HELP football_another Another test
football_another_metric 15
"""

    filtered = filter_metrics_by_prefix(metrics_data, "football_test")
    assert "football_test_metric" in filtered
    assert "football_another_metric" not in filtered
    assert "other_metric" not in filtered


def test_global_functions():
    """测试全局函数"""
    from src.monitoring.metrics_exporter_mod.metrics_exporter import (
        get_metrics_exporter, reset_metrics_exporter)

    # 测试获取默认实例
    exporter1 = get_metrics_exporter()
    assert exporter1 is not None

    # 测试获取相同实例（单例）
    exporter2 = get_metrics_exporter()
    assert exporter1 is exporter2

    # 测试创建独立实例（用于测试）
    registry = CollectorRegistry()
    exporter3 = get_metrics_exporter(registry=registry)
    assert exporter3 is not exporter1
    assert exporter3.registry is registry

    # 测试重置
    reset_metrics_exporter()
    exporter4 = get_metrics_exporter()
    assert exporter4 is not exporter1  # 应该是新实例


def test_backward_compatibility():
    """测试向后兼容性"""
    # 应该能从原始位置导入
    from src.monitoring.metrics_exporter import (MetricsExporter,
                                                 get_metrics_exporter,
                                                 reset_metrics_exporter)

    # 创建实例
    exporter = MetricsExporter()
    assert exporter is not None

    # 使用全局函数
    exporter2 = get_metrics_exporter()
    assert exporter2 is not None

    # 重置
    reset_metrics_exporter()
    exporter3 = get_metrics_exporter()
    assert exporter3 is not None


def test_async_methods():
    """测试异步方法"""
    import asyncio

    from src.monitoring.metrics_exporter_mod.metrics_exporter import \
        MetricsExporter

    registry = CollectorRegistry()
    exporter = MetricsExporter(registry=registry)

    async def test_async():
        # 测试异步更新表行数
        await exporter.update_table_row_counts_async()

        # 测试异步更新数据库指标
        await exporter.update_database_metrics()

        # 测试异步收集所有指标
        await exporter.collect_all_metrics()

    # 运行异步测试
    asyncio.run(test_async())
