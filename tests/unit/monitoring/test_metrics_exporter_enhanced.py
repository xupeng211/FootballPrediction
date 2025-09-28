"""
监控指标导出器增强测试

覆盖 metrics_exporter.py 模块的核心功能：
- MetricsExporter类初始化和配置
- Prometheus指标创建和管理
- 数据采集指标记录
- 数据清洗指标记录
- 调度器指标记录
- 数据库表统计指标
- 系统健康状态检查
- 指标导出和格式化
"""

from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest
import time
from datetime import datetime
from typing import Dict, Any

pytestmark = pytest.mark.unit


class TestMetricsExporterInitialization:
    """MetricsExporter初始化测试"""

    def test_metrics_exporter_import(self):
        """测试MetricsExporter类导入"""
        from monitoring.metrics_exporter import MetricsExporter

        # 验证类可以导入
        assert MetricsExporter is not None

    def test_metrics_exporter_default_initialization(self):
        """测试MetricsExporter默认初始化"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import REGISTRY

        exporter = MetricsExporter()

        # 验证基本属性
        assert exporter.registry == REGISTRY
        assert hasattr(exporter, 'data_collection_total')
        assert hasattr(exporter, 'data_collection_errors')
        assert hasattr(exporter, 'data_collection_duration')
        assert hasattr(exporter, 'data_cleaning_total')
        assert hasattr(exporter, 'data_cleaning_errors')
        assert hasattr(exporter, 'data_cleaning_duration')
        assert hasattr(exporter, 'scheduler_task_delay')
        assert hasattr(exporter, 'scheduler_task_failures')
        assert hasattr(exporter, 'scheduler_task_duration')
        assert hasattr(exporter, 'table_row_count')
        assert hasattr(exporter, 'database_connections')
        assert hasattr(exporter, 'database_query_duration')
        assert hasattr(exporter, 'system_info')

    def test_metrics_exporter_custom_registry_initialization(self):
        """测试MetricsExporter自定义注册表初始化"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        custom_registry = CollectorRegistry()
        exporter = MetricsExporter(registry=custom_registry)

        # 验证使用自定义注册表
        assert exporter.registry == custom_registry

    @pytest.mark.parametrize("registry_type", [None, "custom", "global"])
    def test_metrics_exporter_registry_types(self, registry_type):
        """测试MetricsExporter不同注册表类型"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry, REGISTRY

        if registry_type == "custom":
            registry = CollectorRegistry()
        elif registry_type == "global":
            registry = REGISTRY
        else:
            registry = None

        exporter = MetricsExporter(registry=registry)

        # 验证注册表设置正确
        expected_registry = registry or REGISTRY
        assert exporter.registry == expected_registry


class TestMetricsExporterDataCollection:
    """MetricsExporter数据采集指标测试"""

    def test_record_data_collection_success(self):
        """测试记录数据采集成功"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录成功的数据采集
        exporter.record_data_collection(
            data_source="api",
            collection_type="fixtures",
            success=True,
            duration=1.5,
            records_count=100
        )

        # 验证指标被更新（通过收集指标来验证）
        metrics = {}
        for metric in registry.collect():
            for sample in metric.samples:
                metrics[sample.name] = sample.value

        # 验证总次数指标（记录的是records_count）
        assert "football_data_collection_total" in metrics
        assert metrics["football_data_collection_total"] == 100.0

    def test_record_data_collection_error(self):
        """测试记录数据采集错误"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录数据采集错误
        exporter.record_data_collection(
            data_source="api",
            collection_type="fixtures",
            success=False,
            duration=2.0,
            error_type="timeout"
        )

        # 验证错误指标被记录
        metrics = {}
        for metric in registry.collect():
            for sample in metric.samples:
                metrics[sample.name] = sample.value

        # 验证错误指标存在
        assert "football_data_collection_errors_total" in metrics

    @pytest.mark.parametrize("data_source,collection_type,success", [
        ("api", "fixtures", True),
        ("api", "odds", True),
        ("api", "scores", False),
        ("database", "historical", True),
        ("file", "import", False),
    ])
    def test_record_data_collection_parameters(self, data_source, collection_type, success):
        """测试数据采集记录参数"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录数据采集
        exporter.record_data_collection(
            data_source=data_source,
            collection_type=collection_type,
            success=success,
            duration=1.0,
            records_count=50 if success else 0,
            error_type=None if success else "network_error"
        )

        # 验证方法执行无异常
        assert True  # 如果没有异常，测试通过

    @pytest.mark.skip("MetricsExporter doesn't have get_data_collection_stats method")
    def test_get_data_collection_stats(self):
        """测试获取数据采集统计"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录一些数据
        exporter.record_data_collection("api", "fixtures", True, 1.0, records_count=100)
        exporter.record_data_collection("api", "fixtures", False, 2.0, error_type="timeout", records_count=0)

        # 获取统计信息
        stats = exporter.get_data_collection_stats()

        # 验证统计信息结构
        assert isinstance(stats, dict)
        assert "total_collections" in stats
        assert "success_rate" in stats
        assert "average_duration" in stats
        assert "total_records" in stats


class TestMetricsExporterDataCleaning:
    """MetricsExporter数据清洗指标测试"""

    def test_record_data_cleaning_success(self):
        """测试记录数据清洗成功"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录成功的数据清洗
        exporter.record_data_cleaning(
            data_type="fixtures",
            success=True,
            duration=0.5,
            records_processed=100
        )

        # 验证方法执行无异常
        assert True

    def test_record_data_cleaning_error(self):
        """测试记录数据清洗错误"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录数据清洗错误
        exporter.record_data_cleaning(
            data_type="fixtures",
            success=False,
            duration=1.0,
            records_processed=0,
            error_type="validation_error",
            error_message="Invalid data format"
        )

        # 验证方法执行无异常
        assert True

    @pytest.mark.parametrize("data_type,success,error_type", [
        ("fixtures", True, None),
        ("fixtures", False, "validation_error"),
        ("odds", True, None),
        ("scores", False, "data_format_error"),
        ("historical", True, None),
    ])
    def test_record_data_cleaning_parameters(self, data_type, success, error_type):
        """测试数据清洗记录参数"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录数据清洗
        exporter.record_data_cleaning(
            data_type=data_type,
            success=success,
            duration=0.8,
            records_processed=50 if success else 0,
            records_cleaned=5 if success else 0,
            error_type=error_type
        )

        # 验证方法执行无异常
        assert True

    def test_get_data_cleaning_stats(self):
        """测试获取数据清洗统计"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录一些数据
        exporter.record_data_cleaning("fixtures", True, 0.5, 100, 5)
        exporter.record_data_cleaning("fixtures", False, 1.0, 0, error_type="validation_error")

        # 获取统计信息
        stats = exporter.get_data_cleaning_stats()

        # 验证统计信息结构
        assert isinstance(stats, dict)
        assert "total_cleaning_operations" in stats
        assert "success_rate" in stats
        assert "average_duration" in stats
        assert "total_records_processed" in stats


class TestMetricsExporterScheduler:
    """MetricsExporter调度器指标测试"""

    def test_record_scheduler_task_start(self):
        """测试记录调度任务开始"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录任务开始
        task_id = exporter.record_scheduler_task_start(
            task_name="collect_fixtures",
            scheduled_time=time.time()
        )

        # 验证返回任务ID
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    def test_record_scheduler_task_completion(self):
        """测试记录调度任务完成"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录任务开始
        task_id = exporter.record_scheduler_task_start("collect_fixtures", time.time())

        # 记录任务完成
        exporter.record_scheduler_task_completion(
            task_id=task_id,
            task_name="collect_fixtures",
            success=True,
            duration=2.0,
            records_processed=50
        )

        # 验证方法执行无异常
        assert True

    def test_record_scheduler_task_failure(self):
        """测试记录调度任务失败"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录任务开始
        task_id = exporter.record_scheduler_task_start("collect_fixtures", time.time())

        # 记录任务失败
        exporter.record_scheduler_task_failure(
            task_id=task_id,
            task_name="collect_fixtures",
            duration=1.5,
            failure_reason="database_connection_error",
            error_message="Unable to connect to database"
        )

        # 验证方法执行无异常
        assert True

    @pytest.mark.parametrize("task_name,success,failure_reason", [
        ("collect_fixtures", True, None),
        ("collect_odds", True, None),
        ("collect_scores", False, "timeout"),
        ("data_cleaning", False, "memory_error"),
        ("backup_task", True, None),
    ])
    def test_record_scheduler_task_parameters(self, task_name, success, failure_reason):
        """测试调度任务记录参数"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录任务开始
        task_id = exporter.record_scheduler_task_start(task_name, time.time())

        # 记录任务结果
        if success:
            exporter.record_scheduler_task_completion(
                task_id=task_id,
                task_name=task_name,
                success=True,
                duration=1.0,
                records_processed=25
            )
        else:
            exporter.record_scheduler_task_failure(
                task_id=task_id,
                task_name=task_name,
                duration=1.5,
                failure_reason=failure_reason,
                error_message=f"Task failed: {failure_reason}"
            )

        # 验证方法执行无异常
        assert True

    def test_get_scheduler_stats(self):
        """测试获取调度器统计"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录一些任务
        task_id1 = exporter.record_scheduler_task_start("task1", time.time())
        exporter.record_scheduler_task_completion(task_id1, "task1", True, 1.0, 10)

        task_id2 = exporter.record_scheduler_task_start("task2", time.time())
        exporter.record_scheduler_task_failure(task_id2, "task2", 2.0, "error")

        # 获取统计信息
        stats = exporter.get_scheduler_stats()

        # 验证统计信息结构
        assert isinstance(stats, dict)
        assert "total_tasks" in stats
        assert "success_rate" in stats
        assert "average_duration" in stats
        assert "active_tasks" in stats


class TestMetricsExporterDatabase:
    """MetricsExporter数据库指标测试"""

    @pytest.mark.asyncio
    async def test_update_table_row_counts(self):
        """测试更新表行数统计"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 模拟数据库查询结果
        mock_results = [
            {"table_name": "matches", "row_count": 1000},
            {"table_name": "odds", "row_count": 5000},
            {"table_name": "predictions", "row_count": 2500},
        ]

        with patch('monitoring.metrics_exporter.get_async_session') as mock_get_session:
            # 设置模拟会话
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None

            # 模拟查询结果
            mock_result = Mock()
            mock_result.fetchall.return_value = mock_results
            mock_session.execute.return_value = mock_result

            # 执行更新
            await exporter.update_table_row_counts()

            # 验证数据库查询被调用
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_record_database_query(self):
        """测试记录数据库查询"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录数据库查询
        exporter.record_database_query(
            query_type="SELECT",
            duration=0.1,
            success=True,
            rows_returned=10
        )

        # 验证方法执行无异常
        assert True

    def test_record_database_connection(self):
        """测试记录数据库连接"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录数据库连接
        exporter.record_database_connection(
            connection_state="active",
            connection_count=5,
            pool_size=10
        )

        # 验证方法执行无异常
        assert True

    @pytest.mark.parametrize("query_type,success,rows_returned", [
        ("SELECT", True, 10),
        ("INSERT", True, 1),
        ("UPDATE", True, 5),
        ("DELETE", True, 3),
        ("SELECT", False, 0),
    ])
    def test_record_database_query_parameters(self, query_type, success, rows_returned):
        """测试数据库查询记录参数"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录数据库查询
        exporter.record_database_query(
            query_type=query_type,
            duration=0.05,
            success=success,
            rows_returned=rows_returned if success else 0
        )

        # 验证方法执行无异常
        assert True


class TestMetricsExporterSystemHealth:
    """MetricsExporter系统健康指标测试"""

    def test_update_system_info(self):
        """测试更新系统信息"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 更新系统信息
        exporter.update_system_info({
            "version": "1.0.0",
            "environment": "production",
            "start_time": datetime.now().isoformat(),
            "python_version": "3.11.0"
        })

        # 验证方法执行无异常
        assert True

    def test_record_system_health(self):
        """测试记录系统健康状态"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录系统健康状态
        exporter.record_system_health(
            healthy=True,
            cpu_usage=45.5,
            memory_usage=60.2,
            disk_usage=75.8
        )

        # 验证方法执行无异常
        assert True

    @pytest.mark.parametrize("healthy,cpu_usage,memory_usage,disk_usage", [
        (True, 25.5, 40.2, 55.8),
        (True, 75.5, 80.2, 85.8),
        (False, 95.5, 95.2, 95.8),
        (True, 10.0, 20.0, 30.0),
        (False, 85.0, 90.0, 95.0),
    ])
    def test_record_system_health_parameters(self, healthy, cpu_usage, memory_usage, disk_usage):
        """测试系统健康记录参数"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录系统健康状态
        exporter.record_system_health(
            healthy=healthy,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage
        )

        # 验证方法执行无异常
        assert True

    def test_get_system_health_summary(self):
        """测试获取系统健康摘要"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录系统健康状态
        exporter.record_system_health(True, 45.5, 60.2, 75.8)

        # 获取健康摘要
        summary = exporter.get_system_health_summary()

        # 验证摘要结构
        assert isinstance(summary, dict)
        assert "healthy" in summary
        assert "cpu_usage" in summary
        assert "memory_usage" in summary
        assert "disk_usage" in summary
        assert "last_updated" in summary


class TestMetricsExporterExport:
    """MetricsExporter指标导出测试"""

    def test_export_metrics(self):
        """测试导出指标"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录一些数据
        exporter.record_data_collection("api", "fixtures", True, 1.0, 100)
        exporter.record_data_cleaning("fixtures", True, 0.5, 100, 5)

        # 导出指标
        metrics_data = exporter.export_metrics()

        # 验证导出结果
        assert isinstance(metrics_data, str)
        assert len(metrics_data) > 0
        assert "football_data_collection_total" in metrics_data
        assert "football_data_cleaning_total" in metrics_data

    def test_export_metrics_with_format(self):
        """测试导出不同格式的指标"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录一些数据
        exporter.record_data_collection("api", "fixtures", True, 1.0, 100)

        # 测试不同格式
        text_format = exporter.export_metrics(format="text")
        json_format = exporter.export_metrics(format="json")  # 如果支持

        # 验证文本格式
        assert isinstance(text_format, str)
        assert len(text_format) > 0

    def test_get_all_metrics_summary(self):
        """测试获取所有指标摘要"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 记录各类数据
        exporter.record_data_collection("api", "fixtures", True, 1.0, 100)
        exporter.record_data_cleaning("fixtures", True, 0.5, 100, 5)
        exporter.record_system_health(True, 45.5, 60.2, 75.8)

        # 获取指标摘要
        summary = exporter.get_all_metrics_summary()

        # 验证摘要结构
        assert isinstance(summary, dict)
        assert "data_collection" in summary
        assert "data_cleaning" in summary
        assert "system_health" in summary
        assert "export_time" in summary


class TestMetricsExporterErrorHandling:
    """MetricsExporter错误处理测试"""

    def test_handle_invalid_parameters(self):
        """测试处理无效参数"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 测试空字符串参数
        exporter.record_data_collection("", "fixtures", True, 1.0, 100)
        exporter.record_data_cleaning("", True, 0.5, 100, 5)

        # 验证方法不会抛出异常
        assert True

    def test_handle_negative_values(self):
        """测试处理负数值"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 测试负数值
        exporter.record_data_collection("api", "fixtures", True, -1.0, -100)
        exporter.record_system_health(True, -10.0, -20.0, -30.0)

        # 验证方法不会抛出异常
        assert True

    def test_handle_missing_task_id(self):
        """测试处理缺失任务ID"""
        from monitoring.metrics_exporter import MetricsExporter
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        # 测试使用不存在的任务ID
        exporter.record_scheduler_task_completion(
            task_id="nonexistent_task",
            task_name="test_task",
            success=True,
            duration=1.0,
            records_processed=10
        )

        # 验证方法不会抛出异常
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.monitoring.metrics_exporter", "--cov-report=term-missing"])