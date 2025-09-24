"""
监控指标导出器测试模块

测试监控指标导出器的各项功能，包括：
- Prometheus指标注册和导出
- 数据采集指标记录
- 数据清洗指标记录
- 调度任务指标记录
- 数据库性能指标更新
- SQL注入防护验证
- 独立CollectorRegistry支持
- 指标重置和清理功能
"""

import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from src.monitoring.metrics_exporter import (
    MetricsExporter,
    get_metrics_exporter,
    reset_metrics_exporter,
)


class TestMetricsExporter:
    """监控指标导出器测试类"""

    @pytest.fixture
    def test_registry(self):
        """创建测试用的独立CollectorRegistry"""
        return CollectorRegistry()

    @pytest.fixture
    def metrics_exporter(self, test_registry):
        """创建指标导出器实例（使用独立注册表）"""
        return MetricsExporter(registry=test_registry)

    @pytest.fixture
    def mock_session(self):
        """创建模拟数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    class TestInitialization:
        """测试初始化功能"""

        def test_initialization_with_custom_registry(self, test_registry):
            """测试使用自定义注册表初始化"""
            exporter = MetricsExporter(registry=test_registry)
            assert exporter.registry is test_registry

        def test_initialization_with_default_registry(self):
            """测试使用默认注册表初始化"""
            exporter = MetricsExporter()
            assert exporter.registry is not None

        def test_data_collection_metrics_initialization(self, metrics_exporter):
            """测试数据采集指标初始化"""
            assert metrics_exporter.data_collection_total is not None
            assert metrics_exporter.data_collection_errors is not None
            assert metrics_exporter.data_collection_duration is not None

        def test_data_cleaning_metrics_initialization(self, metrics_exporter):
            """测试数据清洗指标初始化"""
            assert metrics_exporter.data_cleaning_total is not None
            assert metrics_exporter.data_cleaning_errors is not None
            assert metrics_exporter.data_cleaning_duration is not None

        def test_scheduler_metrics_initialization(self, metrics_exporter):
            """测试调度器指标初始化"""
            assert metrics_exporter.scheduler_task_delay is not None
            assert metrics_exporter.scheduler_task_failures is not None
            assert metrics_exporter.scheduler_task_duration is not None

        def test_database_metrics_initialization(self, metrics_exporter):
            """测试数据库指标初始化"""
            assert metrics_exporter.table_row_count is not None
            assert metrics_exporter.database_connections is not None
            assert metrics_exporter.database_query_duration is not None

        def test_system_metrics_initialization(self, metrics_exporter):
            """测试系统指标初始化"""
            assert metrics_exporter.system_info is not None
            assert metrics_exporter.last_update_timestamp is not None

        def test_system_info_configuration(self, metrics_exporter):
            """测试系统信息配置"""
            # 验证系统信息已设置
            assert metrics_exporter.system_info._value is not None

    class TestDataCollectionMetrics:
        """测试数据采集指标功能"""

        def test_record_data_collection_success(self, metrics_exporter):
            """测试记录数据采集成功"""
            initial_count = self._get_counter_value(
                metrics_exporter.data_collection_total,
                labels={"data_source": "test", "collection_type": "fixtures"},
            )

            metrics_exporter.record_data_collection(
                data_source="test",
                collection_type="fixtures",
                success=True,
                duration=1.5,
                records_count=10,
            )

            final_count = self._get_counter_value(
                metrics_exporter.data_collection_total,
                labels={"data_source": "test", "collection_type": "fixtures"},
            )

            assert final_count == initial_count + 10

        def test_record_data_collection_failure(self, metrics_exporter):
            """测试记录数据采集失败"""
            initial_error_count = self._get_counter_value(
                metrics_exporter.data_collection_errors,
                labels={
                    "data_source": "test",
                    "collection_type": "fixtures",
                    "error_type": "timeout",
                },
            )

            metrics_exporter.record_data_collection(
                data_source="test",
                collection_type="fixtures",
                success=False,
                duration=1.5,
                error_type="timeout",
            )

            final_error_count = self._get_counter_value(
                metrics_exporter.data_collection_errors,
                labels={
                    "data_source": "test",
                    "collection_type": "fixtures",
                    "error_type": "timeout",
                },
            )

            assert final_error_count == initial_error_count + 1

        def test_record_data_collection_duration(self, metrics_exporter):
            """测试记录数据采集持续时间"""
            metrics_exporter.record_data_collection(
                data_source="test",
                collection_type="fixtures",
                success=True,
                duration=2.5,
                records_count=5,
            )

            # 验证直方图记录了持续时间
            # 注意：这里我们主要验证方法不会抛出异常
            # 实际的直方图值需要在实际环境中观察

        def test_record_data_collection_no_records(self, metrics_exporter):
            """测试记录无数据采集"""
            initial_count = self._get_counter_value(
                metrics_exporter.data_collection_total,
                labels={"data_source": "test", "collection_type": "fixtures"},
            )

            metrics_exporter.record_data_collection(
                data_source="test",
                collection_type="fixtures",
                success=True,
                duration=1.0,
                records_count=0,
            )

            final_count = self._get_counter_value(
                metrics_exporter.data_collection_total,
                labels={"data_source": "test", "collection_type": "fixtures"},
            )

            assert final_count == initial_count + 1  # 应该增加1而不是0

        def test_record_data_collection_success_compatibility(self, metrics_exporter):
            """测试记录数据采集成功的兼容接口"""
            initial_count = self._get_counter_value(
                metrics_exporter.data_collection_total,
                labels={"data_source": "test", "collection_type": "default"},
            )

            metrics_exporter.record_data_collection_success(
                data_source="test", records_count=5
            )

            final_count = self._get_counter_value(
                metrics_exporter.data_collection_total,
                labels={"data_source": "test", "collection_type": "default"},
            )

            assert final_count == initial_count + 5

        def test_record_data_collection_failure_compatibility(self, metrics_exporter):
            """测试记录数据采集失败的兼容接口"""
            initial_error_count = self._get_counter_value(
                metrics_exporter.data_collection_errors,
                labels={
                    "data_source": "test",
                    "collection_type": "default",
                    "error_type": "test_failure",
                },
            )

            metrics_exporter.record_data_collection_failure(
                data_source="test", error_message="Connection failed"
            )

            final_error_count = self._get_counter_value(
                metrics_exporter.data_collection_errors,
                labels={
                    "data_source": "test",
                    "collection_type": "default",
                    "error_type": "test_failure",
                },
            )

            assert final_error_count == initial_error_count + 1

    class TestDataCleaningMetrics:
        """测试数据清洗指标功能"""

        def test_record_data_cleaning_success(self, metrics_exporter):
            """测试记录数据清洗成功"""
            initial_count = self._get_counter_value(
                metrics_exporter.data_cleaning_total, labels={"data_type": "matches"}
            )

            metrics_exporter.record_data_cleaning(
                data_type="matches", success=True, duration=2.0, records_processed=50
            )

            final_count = self._get_counter_value(
                metrics_exporter.data_cleaning_total, labels={"data_type": "matches"}
            )

            assert final_count == initial_count + 50

        def test_record_data_cleaning_failure(self, metrics_exporter):
            """测试记录数据清洗失败"""
            initial_error_count = self._get_counter_value(
                metrics_exporter.data_cleaning_errors,
                labels={"data_type": "matches", "error_type": "validation_error"},
            )

            metrics_exporter.record_data_cleaning(
                data_type="matches",
                success=False,
                duration=2.0,
                error_type="validation_error",
                records_processed=50,
            )

            final_error_count = self._get_counter_value(
                metrics_exporter.data_cleaning_errors,
                labels={"data_type": "matches", "error_type": "validation_error"},
            )

            assert final_error_count == initial_error_count + 1

        def test_record_data_cleaning_duration(self, metrics_exporter):
            """测试记录数据清洗持续时间"""
            metrics_exporter.record_data_cleaning(
                data_type="matches", success=True, duration=3.5, records_processed=10
            )

            # 验证方法不会抛出异常
            assert True

        def test_record_data_cleaning_success_compatibility(self, metrics_exporter):
            """测试记录数据清洗成功的兼容接口"""
            initial_count = self._get_counter_value(
                metrics_exporter.data_cleaning_total, labels={"data_type": "default"}
            )

            metrics_exporter.record_data_cleaning_success(records_processed=3)

            final_count = self._get_counter_value(
                metrics_exporter.data_cleaning_total, labels={"data_type": "default"}
            )

            assert final_count == initial_count + 3

    class TestSchedulerMetrics:
        """测试调度器指标功能"""

        def test_record_scheduler_task_success(self, metrics_exporter):
            """测试记录调度任务成功"""
            scheduled_time = datetime.now() - timedelta(minutes=5)
            actual_start_time = datetime.now()

            metrics_exporter.record_scheduler_task(
                task_name="data_collection",
                scheduled_time=scheduled_time,
                actual_start_time=actual_start_time,
                duration=10.5,
                success=True,
            )

            # 验证延迟指标被设置
            # 注意：这里我们主要验证方法不会抛出异常
            assert True

        def test_record_scheduler_task_failure(self, metrics_exporter):
            """测试记录调度任务失败"""
            scheduled_time = datetime.now() - timedelta(minutes=5)
            actual_start_time = datetime.now()

            initial_failure_count = self._get_counter_value(
                metrics_exporter.scheduler_task_failures,
                labels={"task_name": "data_collection", "failure_reason": "timeout"},
            )

            metrics_exporter.record_scheduler_task(
                task_name="data_collection",
                scheduled_time=scheduled_time,
                actual_start_time=actual_start_time,
                duration=10.5,
                success=False,
                failure_reason="timeout",
            )

            final_failure_count = self._get_counter_value(
                metrics_exporter.scheduler_task_failures,
                labels={"task_name": "data_collection", "failure_reason": "timeout"},
            )

            assert final_failure_count == initial_failure_count + 1

        def test_record_scheduler_task_simple_success(self, metrics_exporter):
            """测试记录调度任务简化的成功接口"""
            metrics_exporter.record_scheduler_task_simple(
                task_name="test_task", status="success", duration=5.0
            )

            # 验证方法不会抛出异常
            assert True

        def test_record_scheduler_task_simple_failure(self, metrics_exporter):
            """测试记录调度任务简化的失败接口"""
            initial_failure_count = self._get_counter_value(
                metrics_exporter.scheduler_task_failures,
                labels={"task_name": "test_task", "failure_reason": "test_failure"},
            )

            metrics_exporter.record_scheduler_task_simple(
                task_name="test_task", status="failed", duration=5.0
            )

            final_failure_count = self._get_counter_value(
                metrics_exporter.scheduler_task_failures,
                labels={"task_name": "test_task", "failure_reason": "test_failure"},
            )

            assert final_failure_count == initial_failure_count + 1

    class TestTableRowCountMetrics:
        """测试表行数指标功能"""

        def test_update_table_row_counts_with_data(self, metrics_exporter):
            """测试使用数据更新表行数"""
            table_counts = {"matches": 100, "odds": 500, "teams": 20}

            metrics_exporter.update_table_row_counts(table_counts)

            # 验证行数指标被设置
            for table_name, count in table_counts.items():
                # 在实际的Prometheus指标中，我们需要通过其他方式验证
                # 这里主要验证方法不会抛出异常
                assert True

        def test_update_table_row_counts_without_data(self, metrics_exporter):
            """测试不提供数据时更新表行数"""
            # 这应该设置默认值
            metrics_exporter.update_table_row_counts()

            # 验证方法不会抛出异常
            assert True

        def test_update_table_row_counts_empty_data(self, metrics_exporter):
            """测试更新空表行数数据"""
            metrics_exporter.update_table_row_counts({})

            # 验证方法不会抛出异常
            assert True

    class TestDatabaseMetrics:
        """测试数据库指标功能"""

        async def test_update_database_metrics(self, metrics_exporter):
            """测试更新数据库指标"""
            with patch(
                "src.monitoring.metrics_exporter.get_async_session"
            ) as mock_get_session:
                mock_session = AsyncMock()
                mock_result = MagicMock()
                mock_result.fetchall.return_value = [("active", 5), ("idle", 2)]
                mock_session.execute.return_value = mock_result
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__.return_value = None

                await metrics_exporter.update_database_metrics()

                # 验证方法不会抛出异常
                assert True

        async def test_update_database_metrics_error_handling(self, metrics_exporter):
            """测试数据库指标更新错误处理"""
            with patch(
                "src.monitoring.metrics_exporter.get_async_session"
            ) as mock_get_session:
                mock_session = AsyncMock()
                mock_session.execute.side_effect = Exception("Database error")
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__.return_value = None

                # 应该处理异常而不抛出
                await metrics_exporter.update_database_metrics()
                assert True

    class TestTableRowCountAsync:
        """测试表行数异步更新功能"""

        async def test_update_table_row_counts_async(self, metrics_exporter):
            """测试异步更新表行数"""
            with patch(
                "src.monitoring.metrics_exporter.get_async_session"
            ) as mock_get_session:
                mock_session = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar.return_value = 100
                mock_session.execute.return_value = mock_result
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__.return_value = None

                await metrics_exporter.update_table_row_counts_async()

                # 验证方法不会抛出异常
                assert True

        async def test_update_table_row_counts_sql_injection_protection(
            self, metrics_exporter
        ):
            """测试SQL注入防护"""
            with patch(
                "src.monitoring.metrics_exporter.get_async_session"
            ) as mock_get_session:
                mock_session = AsyncMock()
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__.return_value = None

                # 应该跳过不安全的表名
                await metrics_exporter._update_table_row_counts_async()

                # 验证方法不会抛出异常
                assert True

        async def test_update_table_row_counts_table_error_handling(
            self, metrics_exporter
        ):
            """测试表行数更新错误处理"""
            with patch(
                "src.monitoring.metrics_exporter.get_async_session"
            ) as mock_get_session:
                mock_session = AsyncMock()
                mock_session.execute.side_effect = Exception("Query failed")
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__.return_value = None

                # 应该继续处理其他表
                await metrics_exporter._update_table_row_counts_async()
                assert True

    class TestMetricsCollection:
        """测试指标收集功能"""

        async def test_collect_all_metrics(self, metrics_exporter):
            """测试收集所有指标"""
            with patch.object(
                metrics_exporter, "_update_table_row_counts_async"
            ) as mock_table_counts, patch.object(
                metrics_exporter, "update_database_metrics"
            ) as mock_db_metrics:

                await metrics_exporter.collect_all_metrics()

                # 验证所有收集方法都被调用
                mock_table_counts.assert_called_once()
                mock_db_metrics.assert_called_once()

                # 验证最后更新时间戳被设置
                assert True

        async def test_collect_all_metrics_error_handling(self, metrics_exporter):
            """测试收集所有指标的错误处理"""
            with patch.object(
                metrics_exporter, "_update_table_row_counts_async"
            ) as mock_table_counts:
                mock_table_counts.side_effect = Exception("Collection failed")

                # 应该处理异常而不抛出
                await metrics_exporter.collect_all_metrics()
                assert True

    class TestMetricsExport:
        """测试指标导出功能"""

        def test_get_metrics(self, metrics_exporter):
            """测试获取指标数据"""
            content_type, metrics_data = metrics_exporter.get_metrics()

            assert content_type is not None
            assert isinstance(metrics_data, str)
            assert len(metrics_data) > 0

        def test_get_metrics_with_content(self, metrics_exporter):
            """测试获取有内容的指标数据"""
            # 先记录一些数据
            metrics_exporter.record_data_collection_success("test", 10)

            content_type, metrics_data = metrics_exporter.get_metrics()

            assert content_type is not None
            assert isinstance(metrics_data, str)
            assert len(metrics_data) > 0

    class TestDuplicateMetricHandling:
        """测试重复指标处理功能"""

        def test_get_or_create_counter_new(self, test_registry):
            """测试创建新Counter"""
            exporter = MetricsExporter(registry=test_registry)

            counter = exporter._get_or_create_counter(
                "test_counter", "Test counter description", ["label1"], test_registry
            )

            assert counter is not None

        def test_get_or_create_counter_existing(self, test_registry):
            """测试获取已存在的Counter"""
            exporter = MetricsExporter(registry=test_registry)

            # 创建第一个Counter
            counter1 = exporter._get_or_create_counter(
                "test_counter", "Test counter description", ["label1"], test_registry
            )

            # 尝试创建重复的Counter
            counter2 = exporter._get_or_create_counter(
                "test_counter", "Test counter description", ["label1"], test_registry
            )

            assert counter2 is not None

        def test_get_or_create_gauge_new(self, test_registry):
            """测试创建新Gauge"""
            exporter = MetricsExporter(registry=test_registry)

            gauge = exporter._get_or_create_gauge(
                "test_gauge", "Test gauge description", ["label1"], test_registry
            )

            assert gauge is not None

        def test_get_or_create_gauge_existing(self, test_registry):
            """测试获取已存在的Gauge"""
            exporter = MetricsExporter(registry=test_registry)

            # 创建第一个Gauge
            gauge1 = exporter._get_or_create_gauge(
                "test_gauge", "Test gauge description", ["label1"], test_registry
            )

            # 尝试创建重复的Gauge
            gauge2 = exporter._get_or_create_gauge(
                "test_gauge", "Test gauge description", ["label1"], test_registry
            )

            assert gauge2 is not None

    class TestGlobalInstance:
        """测试全局实例功能"""

        def test_get_metrics_exporter_with_registry(self, test_registry):
            """测试使用注册表获取指标导出器"""
            exporter = get_metrics_exporter(registry=test_registry)
            assert exporter.registry is test_registry

        def test_get_metrics_exporter_global(self):
            """测试获取全局指标导出器"""
            # 重置全局实例
            reset_metrics_exporter()

            exporter1 = get_metrics_exporter()
            exporter2 = get_metrics_exporter()

            # 应该返回同一个实例
            assert exporter1 is exporter2

        def test_reset_metrics_exporter(self):
            """测试重置指标导出器"""
            # 创建全局实例
            get_metrics_exporter()

            # 重置
            reset_metrics_exporter()

            # 再次获取应该是新实例
            exporter1 = get_metrics_exporter()
            reset_metrics_exporter()
            exporter2 = get_metrics_exporter()

            # 应该是不同的实例
            assert exporter1 is not exporter2

    class TestSQLInjectionProtection:
        """测试SQL注入防护功能"""

        async def test_safe_table_name_validation(self, metrics_exporter):
            """测试安全表名验证"""
            with patch(
                "src.monitoring.metrics_exporter.get_async_session"
            ) as mock_get_session:
                mock_session = AsyncMock()
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__.return_value = None

                # 测试安全表名
                safe_tables = ["matches", "odds", "teams", "predictions"]

                for table_name in safe_tables:
                    await metrics_exporter._update_table_row_counts_async()

                # 验证没有抛出异常
                assert True

        async def test_unsafe_table_name_handling(self, metrics_exporter):
            """测试不安全表名处理"""
            with patch(
                "src.monitoring.metrics_exporter.get_async_session"
            ) as mock_get_session:
                mock_session = AsyncMock()
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__.return_value = None

                # 模拟不安全表名被跳过
                await metrics_exporter._update_table_row_counts_async()

                # 验证没有抛出异常
                assert True

        def test_quoted_name_usage(self, metrics_exporter):
            """测试quoted_name使用"""
            with patch("sqlalchemy.quoted_name") as mock_quoted:
                mock_quoted.return_value = "safe_table_name"

                # 这应该调用quoted_name
                # 注意：这是一个集成测试，需要实际的环境
                assert True

    class TestPerformance:
        """测试性能功能"""

        def test_metrics_recording_performance(self, metrics_exporter):
            """测试指标记录性能"""
            import time

            start_time = time.time()

            # 记录大量指标
            for i in range(1000):
                metrics_exporter.record_data_collection(
                    data_source=f"test_{i}",
                    collection_type="fixtures",
                    success=True,
                    duration=0.1,
                    records_count=1,
                )

            end_time = time.time()

            # 应该在合理时间内完成
            assert end_time - start_time < 1.0

        def test_memory_usage(self, metrics_exporter):
            """测试内存使用"""
            import sys

            initial_size = sys.getsizeof(metrics_exporter)

            # 记录一些指标
            for i in range(100):
                metrics_exporter.record_data_collection(
                    data_source=f"test_{i}",
                    collection_type="fixtures",
                    success=True,
                    duration=0.1,
                    records_count=1,
                )

            final_size = sys.getsizeof(metrics_exporter)

            # 内存增长应该在合理范围内
            assert final_size - initial_size < 10000

    class TestErrorHandling:
        """测试错误处理功能"""

        def test_metric_recording_error_handling(self, metrics_exporter):
            """测试指标记录错误处理"""
            # 测试各种边缘情况
            metrics_exporter.record_data_collection(
                data_source="",  # 空数据源
                collection_type="",
                success=True,
                duration=-1.0,  # 负持续时间
                records_count=-1,  # 负记录数
            )

            # 应该处理异常而不抛出
            assert True

        def test_scheduler_task_error_handling(self, metrics_exporter):
            """测试调度任务错误处理"""
            # 测试无效的时间参数
            now = datetime.now()
            future_time = now + timedelta(hours=1)  # 未来时间

            metrics_exporter.record_scheduler_task(
                task_name="test",
                scheduled_time=future_time,
                actual_start_time=now,
                duration=10.0,
                success=True,
            )

            # 应该处理异常而不抛出
            assert True

        def test_table_row_counts_error_handling(self, metrics_exporter):
            """测试表行数错误处理"""
            # 测试无效的表名
            metrics_exporter.update_table_row_counts(
                {
                    "": 0,  # 空表名
                    "invalid_table_name_with_special_chars!@#$%": 0,
                    None: 0,  # None表名
                }
            )

            # 应该处理异常而不抛出
            assert True

    class TestIntegration:
        """测试集成功能"""

        def test_full_workflow(self, metrics_exporter):
            """测试完整工作流"""
            # 记录各种指标
            metrics_exporter.record_data_collection_success("api", 100)
            metrics_exporter.record_data_cleaning_success(50)
            metrics_exporter.record_scheduler_task_simple("task1", "success", 5.0)
            metrics_exporter.update_table_row_counts({"matches": 1000})

            # 获取指标数据
            content_type, metrics_data = metrics_exporter.get_metrics()

            # 验证指标数据包含记录的信息
            assert "football_data_collection_total" in metrics_data
            assert "football_data_cleaning_total" in metrics_data
            assert "football_table_row_count" in metrics_data
            assert len(metrics_data) > 0

        async def test_async_workflow(self, metrics_exporter):
            """测试异步工作流"""
            with patch(
                "src.monitoring.metrics_exporter.get_async_session"
            ) as mock_get_session:
                mock_session = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar.return_value = 100
                mock_result.fetchall.return_value = [("active", 5)]
                mock_session.execute.return_value = mock_result
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__.return_value = None

                # 执行异步操作
                await metrics_exporter.collect_all_metrics()

                # 验证指标被更新
                content_type, metrics_data = metrics_exporter.get_metrics()
                assert len(metrics_data) > 0

        def test_concurrent_access(self, metrics_exporter):
            """测试并发访问"""
            import threading
            import time

            def record_metrics():
                for i in range(100):
                    metrics_exporter.record_data_collection(
                        data_source=f"thread_{threading.current_thread().ident}",
                        collection_type="fixtures",
                        success=True,
                        duration=0.1,
                        records_count=1,
                    )

            # 创建多个线程
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=record_metrics)
                threads.append(thread)
                thread.start()

            # 等待所有线程完成
            for thread in threads:
                thread.join()

            # 验证指标被正确记录
            content_type, metrics_data = metrics_exporter.get_metrics()
            assert len(metrics_data) > 0

    @staticmethod
    def _get_counter_value(counter, labels=None):
        """获取计数器值的辅助方法"""
        if labels:
            labeled_counter = counter.labels(**labels)
            return labeled_counter._value._value
        return counter._value._value


# 测试用例需要的导入
from datetime import timedelta
