"""
 lineage_reporter.py 测试文件
 测试 OpenLineage 集成的数据血缘跟踪和 Marquez 报告功能
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import uuid
import json
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lineage.lineage_reporter import LineageReporter


class TestLineageReporter:
    """测试 LineageReporter 数据血缘报告器"""

    def setup_method(self):
        """设置测试环境"""
        self.reporter = LineageReporter(
            marquez_url="http://localhost:5000",
            namespace="test_namespace"
        )

    def test_lineage_reporter_initialization(self):
        """测试数据血缘报告器初始化"""
        assert self.reporter.marquez_url == "http://localhost:5000"
        assert self.reporter.namespace == "test_namespace"
        assert self.reporter._active_runs == {}
        assert self.reporter.client is not None

    def test_lineage_reporter_default_initialization(self):
        """测试默认参数初始化"""
        reporter = LineageReporter()
        assert reporter.marquez_url == "http://localhost:5000"
        assert reporter.namespace == "football_prediction"

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_start_job_run_basic(self, mock_client_class):
        """测试基本作业运行开始"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()
        run_id = reporter.start_job_run(
            job_name="test_job",
            job_type="BATCH"
        )

        assert run_id is not None
        assert isinstance(run_id, str)
        assert len(run_id) > 0

        # 验证运行ID被记录
        assert "test_job" in reporter._active_runs
        assert reporter._active_runs["test_job"] == run_id

        # 验证客户端被调用
        mock_client.emit.assert_called_once()

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_start_job_run_with_inputs(self, mock_client_class):
        """测试带输入数据集的作业运行开始"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        inputs = [
            {
                "name": "source_table",
                "namespace": "test_db",
                "schema": {"columns": ["id", "name", "value"]}
            }
        ]

        run_id = reporter.start_job_run(
            job_name="etl_job",
            job_type="BATCH",
            inputs=inputs,
            description="Test ETL job",
            source_location="https://github.com/test/repo",
            transformation_sql="SELECT * FROM source_table"
        )

        assert run_id is not None
        assert "etl_job" in reporter._active_runs

        # 验证客户端被调用
        mock_client.emit.assert_called_once()

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_start_job_run_with_parent_run(self, mock_client_class):
        """测试带父运行的作业运行开始"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        parent_run_id = str(uuid.uuid4())
        run_id = reporter.start_job_run(
            job_name="child_job",
            job_type="BATCH",
            parent_run_id=parent_run_id
        )

        assert run_id is not None
        assert "child_job" in reporter._active_runs

        mock_client.emit.assert_called_once()

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_start_job_run_error_handling(self, mock_client_class):
        """测试作业运行开始错误处理"""
        mock_client = Mock()
        mock_client.emit.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        with pytest.raises(Exception) as exc_info:
            reporter.start_job_run("test_job")

        assert "Connection failed" in str(exc_info.value)

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_complete_job_run_basic(self, mock_client_class):
        """测试基本作业运行完成"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 先开始一个作业
        run_id = reporter.start_job_run("test_job")
        assert "test_job" in reporter._active_runs

        # 完成作业
        result = reporter.complete_job_run("test_job")

        assert result is True
        assert "test_job" not in reporter._active_runs  # 应该被清理

        # 验证客户端被调用两次（开始 + 完成）
        assert mock_client.emit.call_count == 2

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_complete_job_run_with_outputs(self, mock_client_class):
        """测试带输出数据集的作业运行完成"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 开始作业
        run_id = reporter.start_job_run("etl_job")

        # 定义输出
        outputs = [
            {
                "name": "target_table",
                "namespace": "test_db",
                "schema": {"columns": ["id", "processed_value"]},
                "statistics": {"rowCount": 1000, "processingTime": "2.5s"}
            }
        ]

        metrics = {"records_processed": 1000, "processing_time": 2.5}

        # 完成作业
        result = reporter.complete_job_run(
            job_name="etl_job",
            outputs=outputs,
            metrics=metrics
        )

        assert result is True
        assert "etl_job" not in reporter._active_runs

        # 验证客户端被调用
        assert mock_client.emit.call_count == 2

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_complete_job_run_with_specific_run_id(self, mock_client_class):
        """测试使用指定运行ID完成作业"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 使用指定运行ID完成作业
        specific_run_id = str(uuid.uuid4())
        result = reporter.complete_job_run(
            job_name="test_job",
            run_id=specific_run_id
        )

        assert result is True

        # 验证客户端被调用
        mock_client.emit.assert_called_once()

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_complete_job_run_no_active_run(self, mock_client_class):
        """测试没有活跃运行时的作业完成"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 尝试完成不存在的作业
        result = reporter.complete_job_run("nonexistent_job")

        assert result is False
        mock_client.emit.assert_not_called()

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_complete_job_run_error_handling(self, mock_client_class):
        """测试作业运行完成错误处理"""
        mock_client = Mock()
        mock_client.emit.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 开始作业
        run_id = reporter.start_job_run("test_job")

        # 完成作业（应该失败）
        result = reporter.complete_job_run("test_job")

        assert result is False
        # 作业应该仍然在活跃运行中（因为清理失败）
        assert "test_job" in reporter._active_runs

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_fail_job_run_basic(self, mock_client_class):
        """测试基本作业运行失败"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 开始作业
        run_id = reporter.start_job_run("test_job")

        # 标记作业失败
        result = reporter.fail_job_run(
            job_name="test_job",
            error_message="Test error message"
        )

        assert result is True
        assert "test_job" not in reporter._active_runs

        # 验证客户端被调用两次（开始 + 失败）
        assert mock_client.emit.call_count == 2

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_fail_job_run_with_specific_run_id(self, mock_client_class):
        """测试使用指定运行ID标记作业失败"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 使用指定运行ID标记失败
        specific_run_id = str(uuid.uuid4())
        result = reporter.fail_job_run(
            job_name="test_job",
            error_message="Test error",
            run_id=specific_run_id
        )

        assert result is True

        # 验证客户端被调用
        mock_client.emit.assert_called_once()

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_fail_job_run_no_active_run(self, mock_client_class):
        """测试没有活跃运行时的作业失败标记"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 尝试标记不存在的作业失败
        result = reporter.fail_job_run(
            job_name="nonexistent_job",
            error_message="Test error"
        )

        assert result is False
        mock_client.emit.assert_not_called()

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_fail_job_run_error_handling(self, mock_client_class):
        """测试作业运行失败错误处理"""
        mock_client = Mock()
        mock_client.emit.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 开始作业
        run_id = reporter.start_job_run("test_job")

        # 标记失败（应该失败）
        result = reporter.fail_job_run(
            job_name="test_job",
            error_message="Test error"
        )

        assert result is False
        # 作业应该仍然在活跃运行中（因为清理失败）
        assert "test_job" in reporter._active_runs

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_report_data_collection(self, mock_client_class):
        """测试数据采集报告"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        run_id = reporter.report_data_collection(
            source_name="api_source",
            target_table="matches",
            records_collected=100,
            collection_time=datetime.now(),
            source_config={"schema": {"id": "int", "data": "json"}}
        )

        assert run_id is not None
        assert isinstance(run_id, str)

        # 验证作业被创建和完成（两个客户端调用）
        assert mock_client.emit.call_count == 2

        # 验证活跃运行被清理
        expected_job_name = "data_collection_api_source"
        assert expected_job_name not in reporter._active_runs

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_report_data_collection_minimal(self, mock_client_class):
        """测试最小参数的数据采集报告"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        run_id = reporter.report_data_collection(
            source_name="simple_source",
            target_table="teams",
            records_collected=50,
            collection_time=datetime.now()
        )

        assert run_id is not None
        assert mock_client.emit.call_count == 2

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_report_data_transformation(self, mock_client_class):
        """测试数据转换报告"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        run_id = reporter.report_data_transformation(
            source_tables=["raw_matches", "raw_teams"],
            target_table="processed_matches",
            transformation_sql="SELECT * FROM raw_matches JOIN raw_teams...",
            records_processed=200,
            transformation_type="CLEANSING"
        )

        assert run_id is not None
        assert isinstance(run_id, str)

        # 验证作业被创建和完成
        assert mock_client.emit.call_count == 2

        # 验证活跃运行被清理
        expected_job_name = "data_transformation_processed_matches"
        assert expected_job_name not in reporter._active_runs

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_report_data_transformation_default_type(self, mock_client_class):
        """测试默认转换类型的数据转换报告"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        run_id = reporter.report_data_transformation(
            source_tables=["source_table"],
            target_table="target_table",
            transformation_sql="SELECT * FROM source_table",
            records_processed=100
        )

        assert run_id is not None
        assert mock_client.emit.call_count == 2

    def test_get_active_runs(self):
        """测试获取活跃运行"""
        # 初始状态应该为空
        active_runs = self.reporter.get_active_runs()
        assert active_runs == {}

        # 添加一些活跃运行
        self.reporter._active_runs = {
            "job1": "run_id_1",
            "job2": "run_id_2"
        }

        active_runs = self.reporter.get_active_runs()
        assert active_runs == {
            "job1": "run_id_1",
            "job2": "run_id_2"
        }

        # 验证返回的是副本
        active_runs["job3"] = "run_id_3"
        assert "job3" not in self.reporter._active_runs

    def test_clear_active_runs(self):
        """测试清理活跃运行"""
        # 添加一些活跃运行
        self.reporter._active_runs = {
            "job1": "run_id_1",
            "job2": "run_id_2"
        }

        # 清理活跃运行
        self.reporter.clear_active_runs()

        assert self.reporter._active_runs == {}

    @patch('lineage.lineage_reporter.logger')
    def test_clear_active_runs_logging(self, mock_logger):
        """测试清理活跃运行的日志记录"""
        self.reporter.clear_active_runs()

        mock_logger.info.assert_called_once_with("Cleared all active runs")

    def test_run_id_generation(self):
        """测试运行ID生成"""
        # 测试多个运行ID都是唯一的
        run_ids = []
        for i in range(100):
            run_id = self.reporter.start_job_run(f"job_{i}")
            run_ids.append(run_id)

        # 验证所有ID都是唯一的
        assert len(set(run_ids)) == len(run_ids)

        # 清理活跃运行
        self.reporter.clear_active_runs()

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_job_lifecycle_complete_workflow(self, mock_client_class):
        """测试完整的作业生命周期工作流"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 1. 开始作业
        run_id = reporter.start_job_run(
            job_name="complete_workflow_job",
            job_type="BATCH",
            description="Complete workflow test",
            inputs=[{"name": "input_table", "namespace": "test_db"}]
        )

        assert run_id is not None
        assert "complete_workflow_job" in reporter._active_runs

        # 2. 完成作业
        result = reporter.complete_job_run(
            job_name="complete_workflow_job",
            outputs=[{"name": "output_table", "namespace": "test_db"}],
            metrics={"success": True}
        )

        assert result is True
        assert "complete_workflow_job" not in reporter._active_runs

        # 验证所有事件都被发送
        assert mock_client.emit.call_count == 2

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_job_lifecycle_failure_workflow(self, mock_client_class):
        """测试作业失败生命周期工作流"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 1. 开始作业
        run_id = reporter.start_job_run(
            job_name="failure_workflow_job",
            job_type="BATCH"
        )

        assert run_id is not None
        assert "failure_workflow_job" in reporter._active_runs

        # 2. 标记作业失败
        result = reporter.fail_job_run(
            job_name="failure_workflow_job",
            error_message="Simulated failure"
        )

        assert result is True
        assert "failure_workflow_job" not in reporter._active_runs

        # 验证所有事件都被发送
        assert mock_client.emit.call_count == 2

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_concurrent_job_runs(self, mock_client_class):
        """测试并发作业运行"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 开始多个并发作业
        run_ids = []
        for i in range(5):
            run_id = reporter.start_job_run(f"concurrent_job_{i}")
            run_ids.append(run_id)

        # 验证所有作业都在活跃运行中
        for i in range(5):
            assert f"concurrent_job_{i}" in reporter._active_runs

        # 完成所有作业
        for i in range(5):
            result = reporter.complete_job_run(f"concurrent_job_{i}")
            assert result is True

        # 验证所有作业都被清理
        assert len(reporter._active_runs) == 0

        # 验证所有事件都被发送（5个开始 + 5个完成 = 10个事件）
        assert mock_client.emit.call_count == 10

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_data_pipeline_workflow(self, mock_client_class):
        """测试数据管道工作流"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 1. 数据采集
        collection_run_id = reporter.report_data_collection(
            source_name="external_api",
            target_table="raw_matches",
            records_collected=500,
            collection_time=datetime.now()
        )

        # 2. 数据转换
        transformation_run_id = reporter.report_data_transformation(
            source_tables=["raw_matches"],
            target_table="processed_matches",
            transformation_sql="SELECT * FROM raw_matches WHERE is_valid = true",
            records_processed=450,
            transformation_type="VALIDATION"
        )

        # 3. 聚合转换
        aggregation_run_id = reporter.report_data_transformation(
            source_tables=["processed_matches"],
            target_table="match_aggregates",
            transformation_sql="SELECT team_id, COUNT(*) as match_count FROM processed_matches GROUP BY team_id",
            records_processed=20,
            transformation_type="AGGREGATION"
        )

        # 验证所有运行ID都有效
        assert collection_run_id is not None
        assert transformation_run_id is not None
        assert aggregation_run_id is not None

        # 验证所有作业都完成（没有活跃运行）
        assert len(reporter._active_runs) == 0

        # 验证事件数量（每个报告2个事件，总共6个事件）
        assert mock_client.emit.call_count == 6

    def test_namespace_isolation(self):
        """测试命名空间隔离"""
        # 创建不同命名空间的报告器
        reporter1 = LineageReporter(namespace="namespace1")
        reporter2 = LineageReporter(namespace="namespace2")

        assert reporter1.namespace == "namespace1"
        assert reporter2.namespace == "namespace2"

        # 验证它们不会互相影响
        assert reporter1._active_runs == {}
        assert reporter2._active_runs == {}

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_error_recovery(self, mock_client_class):
        """测试错误恢复"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 测试开始作业失败后仍能继续
        mock_client.emit.side_effect = [Exception("Temporary failure"), None]

        with pytest.raises(Exception):
            reporter.start_job_run("failed_job")

        # 下一个作业应该成功
        mock_client.emit.side_effect = None
        run_id = reporter.start_job_run("successful_job")
        assert run_id is not None

    def test_input_validation(self):
        """测试输入验证"""
        # 测试空作业名称
        with pytest.raises(ValueError):
            self.reporter.start_job_run("")

        # 测试空错误消息
        with pytest.raises(ValueError):
            self.reporter.fail_job_run("test_job", "")

    def test_event_time_format(self):
        """测试事件时间格式"""
        # 这个测试验证事件时间使用正确的UTC格式
        with patch('lineage.lineage_reporter.OpenLineageClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # 记录发送的事件
            events_sent = []

            def capture_event(event):
                events_sent.append(event)
                # 验证时间格式
                assert isinstance(event.eventTime, str)
                assert "T" in event.eventTime
                assert "Z" in event.eventTime
                try:
                    datetime.fromisoformat(event.eventTime.replace("Z", "+00:00"))
                except ValueError:
                    pytest.fail(f"Invalid time format: {event.eventTime}")

            mock_client.emit.side_effect = capture_event

            reporter = LineageReporter()
            reporter.start_job_run("test_job")

            assert len(events_sent) == 1

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_producer_field(self, mock_client_class):
        """测试生产者字段设置"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 记录发送的事件
        events_sent = []

        def capture_event(event):
            events_sent.append(event)

        mock_client.emit.side_effect = capture_event

        reporter.start_job_run("test_job")

        assert len(events_sent) == 1
        assert events_sent[0].producer == "football_prediction_lineage_reporter"

    def test_uuid_consistency(self):
        """测试UUID一致性"""
        # 测试UUID生成的一致性
        run_id1 = self.reporter.start_job_run("test_job")
        run_id2 = self.reporter.start_job_run("test_job")

        # UUID应该是唯一的
        assert run_id1 != run_id2

        # UUID应该是有效的UUID格式
        try:
            uuid.UUID(run_id1)
            uuid.UUID(run_id2)
        except ValueError:
            pytest.fail("Generated run IDs are not valid UUIDs")


class TestLineageReporterIntegration:
    """测试 LineageReporter 集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.reporter = LineageReporter(
            marquez_url="http://localhost:5000",
            namespace="test_integration"
        )

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_end_to_end_data_lineage_tracking(self, mock_client_class):
        """测试端到端数据血缘跟踪"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # 模拟完整的数据处理管道
        # 1. 数据采集
        collection_run = self.reporter.report_data_collection(
            source_name="football_api",
            target_table="raw_matches",
            records_collected=1000,
            collection_time=datetime.now(),
            source_config={
                "schema": {
                    "match_id": "string",
                    "home_team": "string",
                    "away_team": "string",
                    "score": "object"
                }
            }
        )

        # 2. 数据清洗
        cleaning_run = self.reporter.report_data_transformation(
            source_tables=["raw_matches"],
            target_table="clean_matches",
            transformation_sql="SELECT match_id, home_team, away_team, score->>'home' as home_score, score->>'away' as away_score FROM raw_matches WHERE score IS NOT NULL",
            records_processed=950,
            transformation_type="CLEANING"
        )

        # 3. 数据验证
        validation_run = self.reporter.report_data_transformation(
            source_tables=["clean_matches"],
            target_table="validated_matches",
            transformation_sql="SELECT * FROM clean_matches WHERE home_score >= 0 AND away_score >= 0",
            records_processed=920,
            transformation_type="VALIDATION"
        )

        # 4. 特征工程
        feature_run = self.reporter.report_data_transformation(
            source_tables=["validated_matches"],
            target_table="match_features",
            transformation_sql="SELECT match_id, home_team, away_team, home_score + away_score as total_goals, CASE WHEN home_score > away_score THEN 1 ELSE 0 END as home_win FROM validated_matches",
            records_processed=920,
            transformation_type="FEATURE_ENGINEERING"
        )

        # 验证所有运行都成功
        assert collection_run is not None
        assert cleaning_run is not None
        assert validation_run is not None
        assert feature_run is not None

        # 验证没有活跃运行残留
        assert len(self.reporter._active_runs) == 0

        # 验证事件数量（每个步骤2个事件，总共8个事件）
        assert mock_client.emit.call_count == 8

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_error_handling_and_recovery(self, mock_client_class):
        """测试错误处理和恢复"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # 模拟部分失败的情况
        mock_client.emit.side_effect = [
            None,  # 开始成功
            Exception("Completion failed"),  # 完成失败
            None,  # 下一个开始成功
            None   # 下一个完成成功
        ]

        reporter = LineageReporter()

        # 第一个作业应该开始成功但完成失败
        run_id1 = reporter.start_job_run("partial_failure_job")
        assert run_id1 is not None

        result1 = reporter.complete_job_run("partial_failure_job")
        assert result1 is False

        # 第二个作业应该完全成功
        run_id2 = reporter.start_job_run("successful_job")
        assert run_id2 is not None

        result2 = reporter.complete_job_run("successful_job")
        assert result2 is True

        # 验证状态
        assert "partial_failure_job" in reporter._active_runs  # 未被清理
        assert "successful_job" not in reporter._active_runs  # 已被清理

    @patch('lineage.lineage_reporter.OpenLineageClient')
    def test_concurrent_data_processing(self, mock_client_class):
        """测试并发数据处理"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 模拟多个数据源同时处理
        sources = ["api_source1", "api_source2", "api_source3"]
        run_ids = []

        # 并发开始多个数据采集作业
        for source in sources:
            run_id = reporter.start_job_run(
                job_name=f"data_collection_{source}",
                inputs=[{"name": source, "namespace": "external"}]
            )
            run_ids.append(run_id)

        # 验证所有作业都在运行
        for source in sources:
            job_name = f"data_collection_{source}"
            assert job_name in reporter._active_runs

        # 并发完成所有作业
        for i, source in enumerate(sources):
            result = reporter.complete_job_run(
                job_name=f"data_collection_{source}",
                outputs=[{"name": f"raw_{source}", "namespace": "staging"}]
            )
            assert result is True

        # 验证所有作业都完成
        assert len(reporter._active_runs) == 0

        # 验证事件数量（3个开始 + 3个完成 = 6个事件）
        assert mock_client.emit.call_count == 6

    def test_performance_and_scalability(self):
        """测试性能和可扩展性"""
        import time

        # 测试大量作业的处理性能
        start_time = time.time()

        # 创建多个作业
        for i in range(100):
            run_id = self.reporter.start_job_run(f"perf_test_job_{i}")

        # 验证所有作业都被创建
        assert len(self.reporter._active_runs) == 100

        # 完成所有作业
        for i in range(100):
            self.reporter.complete_job_run(f"perf_test_job_{i}")

        # 验证所有作业都完成
        assert len(self.reporter._active_runs) == 0

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证处理时间在合理范围内
        assert processing_time < 10.0  # 100个作业应该在10秒内完成


if __name__ == "__main__":
    pytest.main([__file__, "-v"])