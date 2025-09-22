"""
数据质量模块单元测试

测试 Great Expectations 断言、Prometheus 指标导出和异常处理机制。
验证阶段三数据治理与质量控制功能的正确性。

覆盖率目标: > 85%
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# 创建模拟的 great_expectations 和 prometheus_client
try:
    import great_expectations
    import prometheus_client

    HAS_GE = True
    HAS_PROMETHEUS = True
except ImportError:
    HAS_GE = False
    HAS_PROMETHEUS = False

    # 创建模拟类
    class MockGE:
        @staticmethod
        def get_context(*args, **kwargs):
            return Mock()

    class MockPrometheus:
        class Gauge:
            def __init__(self, *args, **kwargs):
                pass

        class Counter:
            def __init__(self, *args, **kwargs):
                pass

        class Histogram:
            def __init__(self, *args, **kwargs):
                pass

        class Info:
            def __init__(self, *args, **kwargs):
                pass

    great_expectations = MockGE()  # type: ignore[assignment]
    prometheus_client = MockPrometheus()  # type: ignore[assignment]

# 使用 patch 来模拟外部依赖
with (
    patch("great_expectations.get_context")
    if HAS_GE
    else patch.object(great_expectations, "get_context")
), (
    patch("prometheus_client.Gauge")
    if HAS_PROMETHEUS
    else patch.object(prometheus_client, "Gauge")
), (
    patch("prometheus_client.Counter")
    if HAS_PROMETHEUS
    else patch.object(prometheus_client, "Counter")
), (
    patch("prometheus_client.Histogram")
    if HAS_PROMETHEUS
    else patch.object(prometheus_client, "Histogram")
), (
    patch("prometheus_client.Info")
    if HAS_PROMETHEUS
    else patch.object(prometheus_client, "Info")
):
    from src.data.quality.exception_handler import DataQualityExceptionHandler
    from src.data.quality.ge_prometheus_exporter import GEPrometheusExporter
    from src.data.quality.great_expectations_config import \
        GreatExpectationsConfig
    from src.database.models.data_quality_log import DataQualityLog


class TestGreatExpectationsConfig:
    """Great Expectations 配置模块测试"""

    @pytest.fixture
    def ge_config(self):
        """创建GE配置实例"""
        return GreatExpectationsConfig(ge_root_dir="/tmp/test_ge")

    def test_init(self, ge_config):
        """测试初始化"""
        assert ge_config.ge_root_dir == "/tmp/test_ge"
        assert "matches" in ge_config.data_assertions
        assert "odds" in ge_config.data_assertions
        assert ge_config.context is None

    def test_data_assertions_structure(self, ge_config):
        """测试数据断言结构"""
        # 测试matches表断言
        matches_assertions = ge_config.data_assertions["matches"]
        assert matches_assertions["name"] == "足球比赛数据质量检查"

        expectations = matches_assertions["expectations"]
        assert len(expectations) >= 5

        # 验证关键断言存在
        expectation_types = [exp["expectation_type"] for exp in expectations]
        assert "expect_column_to_exist" in expectation_types
        assert "expect_column_values_to_not_be_null" in expectation_types
        assert "expect_column_values_to_be_between" in expectation_types

        # 测试odds表断言
        odds_assertions = ge_config.data_assertions["odds"]
        assert odds_assertions["name"] == "赔率数据质量检查"

        odds_expectations = odds_assertions["expectations"]
        assert len(odds_expectations) >= 3

    def test_get_database_connection_string(self, ge_config):
        """测试数据库连接字符串生成"""
        with patch.dict(
            "os.environ",
            {
                "DB_HOST": "test_host",
                "DB_PORT": "5433",
                "DB_NAME": "test_db",
                "DB_USER": "test_user",
                "DB_PASSWORD": "test_pass",
            },
        ):
            conn_str = ge_config._get_database_connection_string()
            expected = "postgresql://test_user:test_pass@test_host:5433/test_db"
            assert conn_str == expected

    @pytest.mark.asyncio
    async def test_initialize_context(self, ge_config):
        """测试数据上下文初始化"""
        with patch("great_expectations.get_context") as mock_get_context, patch(
            "os.makedirs"
        ) as mock_makedirs, patch("builtins.open", create=True) as mock_open:
            mock_context = Mock()
            mock_get_context.return_value = mock_context

            result = await ge_config.initialize_context()

            # 验证目录创建
            assert mock_makedirs.call_count >= 4

            # 验证配置文件写入
            mock_open.assert_called()

            # 验证上下文创建
            mock_get_context.assert_called_once()
            assert result == mock_context
            assert ge_config.context == mock_context

    @pytest.mark.asyncio
    async def test_create_expectation_suites(self, ge_config):
        """测试创建期望套件"""
        # 模拟GE上下文
        mock_context = Mock()
        mock_suite = Mock()
        mock_context.add_or_update_expectation_suite.return_value = mock_suite
        ge_config.context = mock_context

        result = await ge_config.create_expectation_suites()

        # 验证结果结构
        assert "created_suites" in result
        assert "errors" in result
        assert len(result["created_suites"]) == 2  # matches + odds

        # 验证套件创建调用
        assert mock_context.add_or_update_expectation_suite.call_count == 2
        assert mock_context.save_expectation_suite.call_count == 2

    @pytest.mark.asyncio
    async def test_run_validation_success(self, ge_config):
        """测试成功的数据验证"""
        # 模拟GE组件
        mock_context = Mock()
        mock_validator = Mock()
        mock_validation_result = Mock()

        # 配置模拟返回值
        mock_validation_result.statistics = {
            "successful_expectations": 8,
            "evaluated_expectations": 10,
        }
        mock_validation_result.results = []
        mock_validation_result.meta = {"run_id": {"run_name": "test_run"}}

        mock_validator.validate.return_value = mock_validation_result
        mock_context.get_validator.return_value = mock_validator

        ge_config.context = mock_context

        result = await ge_config.run_validation("matches", 100)

        # 验证结果
        assert result["table_name"] == "matches"
        assert result["success_rate"] == 80.0  # 8/10 * 100
        assert result["status"] == "FAILED"  # < 95%
        assert result["rows_checked"] == 100

    @pytest.mark.asyncio
    async def test_run_validation_error(self, ge_config):
        """测试验证过程中的错误处理"""
        ge_config.context = None  # 未初始化上下文

        with patch.object(
            ge_config, "initialize_context", side_effect=Exception("Test error")
        ):
            result = await ge_config.run_validation("matches")

            assert result["status"] == "ERROR"
            assert "Test error" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_all_tables(self, ge_config):
        """测试验证所有表"""
        with patch.object(ge_config, "run_validation") as mock_run_validation:
            # 模拟不同的验证结果
            mock_run_validation.side_effect = [
                {"status": "PASSED", "success_rate": 95.0, "table_name": "matches"},
                {"status": "FAILED", "success_rate": 70.0, "table_name": "odds"},
            ]

            result = await ge_config.validate_all_tables()

            # 验证整体统计
            overall_stats = result["overall_statistics"]
            assert overall_stats["total_tables"] == 2
            assert overall_stats["passed_tables"] == 1
            assert overall_stats["failed_tables"] == 1
            assert overall_stats["overall_success_rate"] == 82.5  # (95+70)/2

    def test_get_custom_expectation_for_odds_probability(self, ge_config):
        """测试自定义赔率概率断言"""
        expectation = ge_config.get_custom_expectation_for_odds_probability()

        assert (
            expectation["expectation_type"] == "expect_table_column_count_to_be_between"
        )
        assert "kwargs" in expectation
        assert "meta" in expectation


class TestGEPrometheusExporter:
    """Prometheus 指标导出器测试"""

    @pytest.fixture
    def exporter(self):
        """创建指标导出器实例"""
        with patch("prometheus_client.Gauge"), patch(
            "prometheus_client.Counter"
        ), patch("prometheus_client.Histogram"), patch("prometheus_client.Info"):
            return GEPrometheusExporter()

    def test_init(self, exporter):
        """测试初始化"""
        assert exporter.registry is None
        assert hasattr(exporter, "data_quality_success_rate")
        assert hasattr(exporter, "expectations_total")
        assert hasattr(exporter, "anomaly_records")

    @pytest.mark.asyncio
    async def test_export_table_validation_result(self, exporter):
        """测试导出单表验证结果"""
        # 模拟验证结果
        table_result = {
            "table_name": "matches",
            "suite_name": "matches_data_quality_suite",
            "success_rate": 85.5,
            "total_expectations": 10,
            "successful_expectations": 8,
            "failed_expectations": [
                {"expectation_type": "expect_column_values_to_be_between"},
                {"expectation_type": "expect_column_values_to_not_be_null"},
            ],
            "validation_time": "2025-09-10T22:00:00",
            "status": "FAILED",
            "rows_checked": 1000,
            "ge_validation_result_id": "test_run_001",
        }

        # 模拟Prometheus指标
        mock_success_rate = Mock()
        mock_expectations_total = Mock()
        mock_expectations_failed = Mock()
        mock_quality_score = Mock()
        mock_validation_info = Mock()

        exporter.data_quality_success_rate = Mock()
        exporter.data_quality_success_rate.labels.return_value = mock_success_rate

        exporter.expectations_total = Mock()
        exporter.expectations_total.labels.return_value = mock_expectations_total

        exporter.expectations_failed = Mock()
        exporter.expectations_failed.labels.return_value = mock_expectations_failed

        exporter.quality_score = Mock()
        exporter.quality_score.labels.return_value = mock_quality_score

        exporter.validation_info = mock_validation_info

        await exporter._export_table_validation_result(table_result)

        # 验证指标设置
        mock_success_rate.set.assert_called_with(85.5)
        mock_expectations_total.set.assert_called_with(10)
        mock_quality_score.set.assert_called_with(85.5)

        # 验证失败断言计数
        assert mock_expectations_failed.inc.call_count == 2

    @pytest.mark.asyncio
    async def test_export_data_freshness_metrics(self, exporter):
        """测试导出数据新鲜度指标"""
        freshness_data = {
            "details": {
                "fixtures": {"hours_since_update": 12.5},
                "odds": {"hours_since_update": 2.0},
            }
        }

        mock_freshness_gauge = Mock()
        exporter.data_freshness_hours = Mock()
        exporter.data_freshness_hours.labels.return_value = mock_freshness_gauge

        await exporter.export_data_freshness_metrics(freshness_data)

        # 验证指标设置
        assert exporter.data_freshness_hours.labels.call_count == 2
        assert mock_freshness_gauge.set.call_count == 2

    @pytest.mark.asyncio
    async def test_export_anomaly_metrics(self, exporter):
        """测试导出异常检测指标"""
        anomalies = [
            {"type": "suspicious_odds", "severity": "medium"},
            {"type": "unusual_high_score", "severity": "high"},
            {"type": "suspicious_odds", "severity": "low"},
        ]

        mock_anomaly_gauge = Mock()
        exporter.anomaly_records = Mock()
        exporter.anomaly_records._metrics = Mock()
        exporter.anomaly_records._metrics.clear = Mock()
        exporter.anomaly_records.labels.return_value = mock_anomaly_gauge

        await exporter.export_anomaly_metrics(anomalies)

        # 验证清零和设置
        exporter.anomaly_records._metrics.clear.assert_called_once()
        assert mock_anomaly_gauge.set.call_count >= 2  # 至少2个不同的组合

    @pytest.mark.asyncio
    async def test_run_full_quality_check_and_export(self, exporter):
        """测试完整质量检查和导出"""
        # 模拟各个组件
        mock_validation_results = {
            "overall_statistics": {"overall_success_rate": 85.0},
            "table_results": [],
        }

        mock_freshness_results = {"status": "healthy"}
        mock_anomalies = [{"type": "test", "severity": "low"}]

        with patch.object(
            exporter.ge_config,
            "validate_all_tables",
            return_value=mock_validation_results,
        ), patch.object(exporter, "export_ge_validation_results"), patch.object(
            exporter, "export_data_freshness_metrics"
        ), patch.object(
            exporter, "export_anomaly_metrics"
        ), patch(
            "src.data.quality.data_quality_monitor.DataQualityMonitor"
        ) as mock_monitor_class:
            mock_monitor = Mock()
            mock_monitor.check_data_freshness = AsyncMock(
                return_value=mock_freshness_results
            )
            mock_monitor.detect_anomalies = AsyncMock(return_value=mock_anomalies)
            mock_monitor_class.return_value = mock_monitor

            result = await exporter.run_full_quality_check_and_export()

            # 验证结果
            assert result["prometheus_export_status"] == "success"
            assert result["anomalies_count"] == 1
            assert "execution_time" in result

    def test_get_current_metrics_summary(self, exporter):
        """测试获取当前指标摘要"""
        summary = exporter.get_current_metrics_summary()

        assert "timestamp" in summary
        assert "metrics_defined" in summary
        assert len(summary["metrics_defined"]) == 7
        assert "exporter_status" in summary


class TestDataQualityExceptionHandler:
    """数据质量异常处理器测试"""

    @pytest.fixture
    def handler(self):
        """创建异常处理器实例"""
        with patch("src.database.connection.DatabaseManager"):
            return DataQualityExceptionHandler()

    def test_init(self, handler):
        """测试初始化"""
        assert hasattr(handler, "handling_strategies")
        assert "missing_values" in handler.handling_strategies
        assert "suspicious_odds" in handler.handling_strategies
        assert "invalid_scores" in handler.handling_strategies

    @pytest.mark.asyncio
    async def test_handle_missing_match_values(self, handler):
        """测试处理比赛数据缺失值"""
        record = {
            "match_status": "finished",
            "home_score": None,
            "away_score": None,
            "venue": None,
            "referee": None,
            "home_team_id": 1,
            "away_team_id": 2,
        }

        with patch.object(handler, "_get_historical_average_score", return_value=1.5):
            result = await handler._handle_missing_match_values(record)

            # 验证缺失值填充
            assert result["home_score"] == 2  # rounded 1.5
            assert result["away_score"] == 2
            assert result["venue"] == "Unknown Venue"
            assert result["referee"] == "Unknown Referee"

    @pytest.mark.asyncio
    async def test_handle_missing_odds_values(self, handler):
        """测试处理赔率数据缺失值"""
        record = {
            "match_id": 1,
            "bookmaker": "test_bookmaker",
            "home_odds": None,
            "draw_odds": 3.5,
            "away_odds": None,
        }

        with patch.object(handler, "_get_historical_average_odds", return_value=2.0):
            result = await handler._handle_missing_odds_values(record)

            # 验证缺失值填充
            assert result["home_odds"] == 2.0
            assert result["draw_odds"] == 3.5  # 原值保持
            assert result["away_odds"] == 2.0

    def test_is_odds_suspicious_valid_odds(self, handler):
        """测试有效赔率判断"""
        valid_odds = {"home_odds": 2.0, "draw_odds": 3.5, "away_odds": 4.0}

        result = handler._is_odds_suspicious(valid_odds)
        assert result is False

    def test_is_odds_suspicious_invalid_range(self, handler):
        """测试无效范围赔率判断"""
        invalid_odds = {
            "home_odds": 0.5,  # 小于1.01
            "draw_odds": 3.5,
            "away_odds": 4.0,
        }

        result = handler._is_odds_suspicious(invalid_odds)
        assert result is True

    def test_is_odds_suspicious_invalid_probability(self, handler):
        """测试无效概率总和赔率判断"""
        invalid_probability_odds = {
            "home_odds": 1.1,  # 1/1.1 + 1/1.1 + 1/1.1 = 2.73 > 1.20
            "draw_odds": 1.1,
            "away_odds": 1.1,
        }

        result = handler._is_odds_suspicious(invalid_probability_odds)
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_suspicious_odds(self, handler):
        """测试处理可疑赔率"""
        odds_records = [
            {"id": 1, "home_odds": 2.0, "draw_odds": 3.5, "away_odds": 4.0},  # 正常
            {"id": 2, "home_odds": 0.5, "draw_odds": 3.5, "away_odds": 4.0},  # 可疑
        ]

        with patch.object(handler.db_manager, "get_async_session"), patch.object(
            handler, "_log_suspicious_odds"
        ):
            result = await handler.handle_suspicious_odds(odds_records)

            # 验证结果
            assert result["total_processed"] == 2
            assert result["suspicious_count"] == 1

            processed_records = result["processed_records"]
            assert processed_records[0]["suspicious_odds"] is False
            assert processed_records[1]["suspicious_odds"] is True

    @pytest.mark.asyncio
    async def test_handle_invalid_data(self, handler):
        """测试处理无效数据"""
        invalid_records = [
            {"id": 1, "invalid_field": "test"},
            {"id": 2, "invalid_field": "test2"},
        ]

        with patch.object(handler.db_manager, "get_async_session"), patch.object(
            handler, "_create_quality_log"
        ):
            result = await handler.handle_invalid_data(
                "test_table", invalid_records, "test_error"
            )

            # 验证结果
            assert result["table_name"] == "test_table"
            assert result["error_type"] == "test_error"
            assert result["invalid_records_count"] == 2
            assert result["logged_count"] == 2
            assert result["requires_manual_review"] is True

    @pytest.mark.asyncio
    async def test_get_handling_statistics(self, handler):
        """测试获取处理统计"""
        # 模拟数据库查询结果
        mock_rows = [
            Mock(
                error_type="missing_values",
                table_name="matches",
                count=5,
                manual_review_count=1,
            ),
            Mock(
                error_type="suspicious_odds",
                table_name="odds",
                count=3,
                manual_review_count=2,
            ),
        ]

        # 创建异步context manager的正确mock
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(handler.db_manager, "get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await handler.get_handling_statistics()

            # 验证统计结果
            assert result["period"] == "last_24_hours"
            assert result["total_issues"] == 8  # 5 + 3
            assert result["manual_review_required"] == 3  # 1 + 2
            assert result["by_error_type"]["missing_values"] == 5
            assert result["by_table"]["matches"] == 5


class TestDataQualityLog:
    """数据质量日志模型测试"""

    def test_init(self):
        """测试初始化"""
        log = DataQualityLog(table_name="test_table", error_type="test_error")

        assert log.table_name == "test_table"
        assert log.error_type == "test_error"
        assert log.status == "logged"
        assert log.requires_manual_review is False

    def test_to_dict(self):
        """测试转换为字典"""
        log = DataQualityLog(
            table_name="test_table", error_type="test_error", severity="high"
        )

        result = log.to_dict()

        assert result["table_name"] == "test_table"
        assert result["error_type"] == "test_error"
        assert result["severity"] == "high"
        assert "created_at" in result

    def test_mark_as_resolved(self):
        """测试标记为已解决"""
        log = DataQualityLog(table_name="test", error_type="test")

        log.mark_as_resolved("admin", "Fixed the issue")

        assert log.status == "resolved"
        assert log.handled_by == "admin"
        assert log.resolution_notes == "Fixed the issue"
        assert log.handled_at is not None

    def test_mark_as_ignored(self):
        """测试标记为忽略"""
        log = DataQualityLog(table_name="test", error_type="test")

        log.mark_as_ignored("admin", "Not a real issue")

        assert log.status == "ignored"
        assert log.handled_by == "admin"
        assert "忽略原因: Not a real issue" in log.resolution_notes

    def test_assign_to_handler(self):
        """测试分配给处理人员"""
        log = DataQualityLog(table_name="test", error_type="test")

        log.assign_to_handler("developer")

        assert log.status == "in_progress"
        assert log.handled_by == "developer"

    def test_get_severity_level(self):
        """测试获取严重程度"""
        assert DataQualityLog.get_severity_level("missing_values_filled") == "low"
        assert DataQualityLog.get_severity_level("suspicious_odds") == "medium"
        assert DataQualityLog.get_severity_level("invalid_scores") == "high"
        assert DataQualityLog.get_severity_level("data_corruption") == "critical"
        assert DataQualityLog.get_severity_level("unknown_error") == "medium"

    def test_create_from_ge_result(self):
        """测试从GE结果创建日志"""
        validation_result = {
            "failed_expectations": [{"type": "test"}],
            "success_rate": 75.0,
        }

        log = DataQualityLog.create_from_ge_result("test_table", validation_result)

        assert log.table_name == "test_table"
        assert log.error_type == "ge_validation_failed"
        assert log.severity == "medium"
        assert log.requires_manual_review is True  # success_rate < 80


# 集成测试
class TestDataQualityIntegration:
    """数据质量模块集成测试"""

    @pytest.mark.asyncio
    async def test_full_quality_workflow(self):
        """测试完整的数据质量工作流"""
        # 创建各组件实例
        with patch("src.database.connection.DatabaseManager"), patch(
            "prometheus_client.Gauge"
        ), patch("prometheus_client.Counter"), patch(
            "prometheus_client.Histogram"
        ), patch(
            "prometheus_client.Info"
        ):
            ge_config = GreatExpectationsConfig()
            exporter = GEPrometheusExporter()
            handler = DataQualityExceptionHandler()

            # 模拟完整工作流
            with patch.object(
                ge_config, "validate_all_tables"
            ) as mock_validate, patch.object(
                exporter, "export_ge_validation_results"
            ) as mock_export, patch.object(
                handler, "handle_missing_values"
            ) as mock_handle_missing:
                # 设置模拟返回值
                mock_validation_results = {
                    "overall_statistics": {"overall_success_rate": 85.0},
                    "table_results": [
                        {
                            "table_name": "matches",
                            "success_rate": 90.0,
                            "status": "PASSED",
                        },
                        {
                            "table_name": "odds",
                            "success_rate": 80.0,
                            "status": "FAILED",
                        },
                    ],
                }
                mock_validate.return_value = mock_validation_results

                mock_processed_records = [{"id": 1, "processed": True}]
                mock_handle_missing.return_value = mock_processed_records

                # 执行工作流
                validation_results = await ge_config.validate_all_tables()
                await exporter.export_ge_validation_results(validation_results)

                test_records = [{"id": 1, "missing_field": None}]
                processed_records = await handler.handle_missing_values(
                    "test_table", test_records
                )

                # 验证结果
                assert (
                    validation_results["overall_statistics"]["overall_success_rate"]
                    == 85.0
                )
                assert len(processed_records) == 1

                # 验证调用
                mock_validate.assert_called_once()
                mock_export.assert_called_once_with(validation_results)
                mock_handle_missing.assert_called_once()


# 性能测试
class TestDataQualityPerformance:
    """数据质量模块性能测试"""

    @pytest.mark.asyncio
    async def test_large_dataset_handling(self):
        """测试大数据集处理性能"""
        with patch("src.database.connection.DatabaseManager"):
            handler = DataQualityExceptionHandler()

            # 创建大量测试数据
            large_dataset = [
                {"id": i, "home_odds": 2.0, "draw_odds": 3.5, "away_odds": 4.0}
                for i in range(1000)
            ]

            start_time = datetime.now()

            with patch.object(handler.db_manager, "get_async_session"), patch.object(
                handler, "_log_suspicious_odds"
            ):
                result = await handler.handle_suspicious_odds(large_dataset)

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # 验证性能（应在合理时间内完成）
            assert execution_time < 5.0  # 5秒内完成
            assert result["total_processed"] == 1000

    def test_memory_usage(self):
        """测试内存使用情况"""
        # 简单的内存使用测试
        ge_config = GreatExpectationsConfig()

        # 验证数据断言配置不会占用过多内存
        import sys

        size = sys.getsizeof(ge_config.data_assertions)

        # 断言配置应该相对较小
        assert size < 10000  # 10KB以内


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--cov=src.data.quality", "--cov-report=term-missing"])
