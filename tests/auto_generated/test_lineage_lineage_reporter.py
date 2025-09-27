"""
Auto-generated tests for src.lineage.lineage_reporter module
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4

from src.lineage.lineage_reporter import LineageReporter


class TestLineageReporter:
    """测试数据血缘报告器"""

    def test_lineage_reporter_initialization(self):
        """测试数据血缘报告器初始化"""
        reporter = LineageReporter(
            marquez_url="http://localhost:8080",
            namespace="test_namespace"
        )

        assert reporter.marquez_url == "http://localhost:8080"
        assert reporter.namespace == "test_namespace"
        assert reporter._active_runs == {}

    def test_lineage_reporter_initialization_defaults(self):
        """测试数据血缘报告器默认初始化"""
        reporter = LineageReporter()

        assert reporter.marquez_url == "http://localhost:5000"
        assert reporter.namespace == "football_prediction"
        assert reporter._active_runs == {}

    def test_start_job_run_basic(self):
        """测试开始作业运行基本功能"""
        reporter = LineageReporter(namespace="test_namespace")
        mock_client = MagicMock()
        reporter.client = mock_client

        run_id = reporter.start_job_run(
            job_name="test_job",
            job_type="BATCH",
            inputs=[
                {"name": "input_table", "namespace": "test_db", "schema": {"fields": []}}
            ],
            description="Test job description",
            source_location="https://github.com/test/repo",
            transformation_sql="SELECT * FROM input_table"
        )

        assert isinstance(run_id, str)
        assert run_id in reporter._active_runs
        assert reporter._active_runs["test_job"] == run_id

        # 验证事件发送
        mock_client.emit.assert_called_once()
        call_args = mock_client.emit.call_args[0][0]

        assert call_args.eventType == "START"
        assert call_args.job.name == "test_job"
        assert call_args.job.namespace == "test_namespace"
        assert len(call_args.inputs) == 1
        assert call_args.inputs[0].name == "input_table"

    def test_start_job_run_without_inputs(self):
        """测试开始无输入的作业运行"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        run_id = reporter.start_job_run(
            job_name="simple_job",
            job_type="BATCH"
        )

        assert isinstance(run_id, str)
        assert "simple_job" in reporter._active_runs

        call_args = mock_client.emit.call_args[0][0]
        assert len(call_args.inputs) == 0

    def test_start_job_run_with_parent_run_id(self):
        """测试带父运行ID的作业开始"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        parent_run_id = str(uuid4())
        run_id = reporter.start_job_run(
            job_name="child_job",
            job_type="BATCH",
            parent_run_id=parent_run_id
        )

        assert isinstance(run_id, str)

    def test_start_job_run_with_emit_exception(self):
        """测试开始作业运行时发送异常"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        mock_client.emit.side_effect = Exception("Network error")
        reporter.client = mock_client

        with pytest.raises(Exception, match="Network error"):
            reporter.start_job_run(
                job_name="failing_job",
                job_type="BATCH"
            )

    def test_complete_job_run_basic(self):
        """测试完成作业运行基本功能"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        # 先开始一个作业
        run_id = reporter.start_job_run(
            job_name="test_job",
            job_type="BATCH"
        )

        # 完成作业
        result = reporter.complete_job_run(
            job_name="test_job",
            outputs=[
                {
                    "name": "output_table",
                    "namespace": "test_db",
                    "schema": {"fields": []},
                    "statistics": {"rowCount": 100}
                }
            ],
            metrics={"processing_time": 5.2}
        )

        assert result is True
        assert "test_job" not in reporter._active_runs  # 应该从活跃运行中移除

        # 验证完成事件发送
        assert mock_client.emit.call_count == 2  # 开始 + 完成
        complete_call_args = mock_client.emit.call_args[0][0]
        assert complete_call_args.eventType == "COMPLETE"
        assert len(complete_call_args.outputs) == 1
        assert complete_call_args.outputs[0].name == "output_table"

    def test_complete_job_run_with_specific_run_id(self):
        """测试使用指定运行ID完成作业"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        run_id = str(uuid4())
        result = reporter.complete_job_run(
            job_name="test_job",
            run_id=run_id,
            outputs=[]
        )

        assert result is True

    def test_complete_job_run_no_active_run(self):
        """测试完成无活跃运行的作业"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        result = reporter.complete_job_run(
            job_name="nonexistent_job",
            outputs=[]
        )

        assert result is False

    def test_complete_job_run_with_emit_exception(self):
        """测试完成作业运行时发送异常"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        # 先开始一个作业
        run_id = reporter.start_job_run(
            job_name="test_job",
            job_type="BATCH"
        )

        # 设置发送异常
        mock_client.emit.side_effect = Exception("Send failed")

        result = reporter.complete_job_run(
            job_name="test_job",
            outputs=[]
        )

        assert result is False

    def test_fail_job_run_basic(self):
        """测试标记作业运行失败基本功能"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        # 先开始一个作业
        run_id = reporter.start_job_run(
            job_name="test_job",
            job_type="BATCH"
        )

        # 标记失败
        result = reporter.fail_job_run(
            job_name="test_job",
            error_message="Processing failed due to invalid data"
        )

        assert result is True
        assert "test_job" not in reporter._active_runs

        # 验证失败事件发送
        assert mock_client.emit.call_count == 2
        fail_call_args = mock_client.emit.call_args[0][0]
        assert fail_call_args.eventType == "FAIL"
        assert "errorMessage" in fail_call_args.run.facets

    def test_fail_job_run_with_specific_run_id(self):
        """测试使用指定运行ID标记作业失败"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        run_id = str(uuid4())
        result = reporter.fail_job_run(
            job_name="test_job",
            run_id=run_id,
            error_message="Test error"
        )

        assert result is True

    def test_fail_job_run_no_active_run(self):
        """测试标记无活跃运行的作业失败"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        result = reporter.fail_job_run(
            job_name="nonexistent_job",
            error_message="Test error"
        )

        assert result is False

    def test_fail_job_run_with_emit_exception(self):
        """测试标记作业运行失败时发送异常"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        # 先开始一个作业
        run_id = reporter.start_job_run(
            job_name="test_job",
            job_type="BATCH"
        )

        # 设置发送异常
        mock_client.emit.side_effect = Exception("Send failed")

        result = reporter.fail_job_run(
            job_name="test_job",
            error_message="Test error"
        )

        assert result is False

    def test_report_data_collection_basic(self):
        """测试报告数据采集过程基本功能"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        collection_time = datetime.now(timezone.utc)
        run_id = reporter.report_data_collection(
            source_name="football_api",
            target_table="raw_matches",
            records_collected=150,
            collection_time=collection_time,
            source_config={"schema": {"fields": ["id", "data"]}}
        )

        assert isinstance(run_id, str)

        # 验证开始和完成事件都被发送
        assert mock_client.emit.call_count == 2

        # 验证开始事件
        start_call_args = mock_client.emit.call_args_list[0][0][0]
        assert start_call_args.eventType == "START"
        assert start_call_args.job.name == "data_collection_football_api"
        assert len(start_call_args.inputs) == 1
        assert start_call_args.inputs[0].name == "football_api"

        # 验证完成事件
        complete_call_args = mock_client.emit.call_args_list[1][0][0]
        assert complete_call_args.eventType == "COMPLETE"
        assert len(complete_call_args.outputs) == 1
        assert complete_call_args.outputs[0].name == "raw_matches"

    def test_report_data_collection_without_source_config(self):
        """测试报告无源配置的数据采集"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        collection_time = datetime.now(timezone.utc)
        run_id = reporter.report_data_collection(
            source_name="api_source",
            target_table="target_table",
            records_collected=50,
            collection_time=collection_time
        )

        assert isinstance(run_id, str)

        start_call_args = mock_client.emit.call_args_list[0][0][0]
        # 输入数据集应该有空的schema
        assert len(start_call_args.inputs) == 1
        assert start_call_args.inputs[0].name == "api_source"

    def test_report_data_transformation_basic(self):
        """测试报告数据转换过程基本功能"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        run_id = reporter.report_data_transformation(
            source_tables=["raw_matches", "raw_teams"],
            target_table="processed_matches",
            transformation_sql="SELECT m.*, t.name FROM raw_matches m JOIN raw_teams t ON m.team_id = t.id",
            records_processed=120,
            transformation_type="ETL"
        )

        assert isinstance(run_id, str)

        # 验证开始事件
        start_call_args = mock_client.emit.call_args_list[0][0][0]
        assert start_call_args.eventType == "START"
        assert start_call_args.job.name == "data_transformation_processed_matches"
        assert len(start_call_args.inputs) == 2
        assert start_call_args.inputs[0].name == "raw_matches"
        assert start_call_args.inputs[1].name == "raw_teams"

        # 验证完成事件
        complete_call_args = mock_client.emit.call_args_list[1][0][0]
        assert complete_call_args.eventType == "COMPLETE"
        assert len(complete_call_args.outputs) == 1
        assert complete_call_args.outputs[0].name == "processed_matches"

    def test_report_data_transformation_custom_type(self):
        """测试报告自定义转换类型的数据转换"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        run_id = reporter.report_data_transformation(
            source_tables=["source_table"],
            target_table="target_table",
            transformation_sql="SELECT * FROM source_table",
            records_processed=100,
            transformation_type="CLEANING"
        )

        assert isinstance(run_id, str)

        complete_call_args = mock_client.emit.call_args_list[1][0][0]
        statistics = complete_call_args.outputs[0].facets.get("dataQualityMetrics", {})
        assert statistics.get("dataQualityMetrics", {}).get("transformationType") == "CLEANING"

    def test_get_active_runs(self):
        """测试获取活跃运行"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        # 开始几个作业
        run_id1 = reporter.start_job_run(job_name="job1", job_type="BATCH")
        run_id2 = reporter.start_job_run(job_name="job2", job_type="BATCH")

        active_runs = reporter.get_active_runs()

        assert len(active_runs) == 2
        assert active_runs["job1"] == run_id1
        assert active_runs["job2"] == run_id2

    def test_get_active_runs_empty(self):
        """测试获取空活跃运行列表"""
        reporter = LineageReporter()

        active_runs = reporter.get_active_runs()
        assert active_runs == {}

    def test_clear_active_runs(self):
        """测试清理活跃运行"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        # 开始几个作业
        reporter.start_job_run(job_name="job1", job_type="BATCH")
        reporter.start_job_run(job_name="job2", job_type="BATCH")

        assert len(reporter._active_runs) == 2

        # 清理活跃运行
        reporter.clear_active_runs()

        assert len(reporter._active_runs) == 0

    def test_job_run_state_transitions(self):
        """测试作业运行状态转换"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        # 开始作业
        run_id = reporter.start_job_run(
            job_name="state_test_job",
            job_type="BATCH",
            inputs=[{"name": "input", "namespace": "test"}]
        )

        assert run_id in reporter._active_runs.values()

        # 完成作业
        success = reporter.complete_job_run(
            job_name="state_test_job",
            outputs=[{"name": "output", "namespace": "test"}]
        )

        assert success is True
        assert "state_test_job" not in reporter._active_runs

    def test_error_handling_in_job_operations(self):
        """测试作业操作中的错误处理"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        # 测试无活跃运行时的完成操作
        result = reporter.complete_job_run(
            job_name="nonexistent_job",
            outputs=[]
        )
        assert result is False

        # 测试无活跃运行时的失败操作
        result = reporter.fail_job_run(
            job_name="nonexistent_job",
            error_message="Test error"
        )
        assert result is False

    def test_concurrent_job_runs(self):
        """测试并发作业运行"""
        reporter = LineageReporter()
        mock_client = MagicMock()
        reporter.client = mock_client

        # 开始多个作业
        run_id1 = reporter.start_job_run(job_name="concurrent_job_1", job_type="BATCH")
        run_id2 = reporter.start_job_run(job_name="concurrent_job_2", job_type="BATCH")
        run_id3 = reporter.start_job_run(job_name="concurrent_job_3", job_type="BATCH")

        # 验证所有作业都在活跃状态
        assert len(reporter._active_runs) == 3
        assert reporter._active_runs["concurrent_job_1"] == run_id1
        assert reporter._active_runs["concurrent_job_2"] == run_id2
        assert reporter._active_runs["concurrent_job_3"] == run_id3

        # 完成其中一个作业
        reporter.complete_job_run(
            job_name="concurrent_job_2",
            outputs=[]
        )

        # 验证其他作业仍然活跃
        assert len(reporter._active_runs) == 2
        assert "concurrent_job_1" in reporter._active_runs
        assert "concurrent_job_2" not in reporter._active_runs
        assert "concurrent_job_3" in reporter._active_runs


@pytest.fixture
def sample_lineage_reporter():
    """示例数据血缘报告器fixture"""
    return LineageReporter(
        marquez_url="http://test-marquez:8080",
        namespace="test_namespace"
    )


@pytest.fixture
def mock_openlineage_client():
    """模拟OpenLineage客户端fixture"""
    client = MagicMock()
    return client


@pytest.fixture
def sample_job_inputs():
    """示例作业输入fixture"""
    return [
        {
            "name": "raw_data",
            "namespace": "bronze_layer",
            "schema": {
                "fields": [
                    {"name": "id", "type": "integer"},
                    {"name": "data", "type": "string"}
                ]
            }
        }
    ]


@pytest.fixture
def sample_job_outputs():
    """示例作业输出fixture"""
    return [
        {
            "name": "processed_data",
            "namespace": "silver_layer",
            "statistics": {
                "rowCount": 1000,
                "processingTime": "2025-09-28T15:30:00Z"
            }
        }
    ]


@pytest.mark.parametrize("job_type,expected_type", [
    ("BATCH", "BATCH"),
    ("STREAM", "STREAM"),
    ("batch", "batch"),  # 应该保持原样
    ("stream", "stream"),  # 应该保持原样
])
def test_start_job_run_with_different_types(job_type, expected_type):
    """参数化测试不同作业类型的开始"""
    reporter = LineageReporter()
    mock_client = MagicMock()
    reporter.client = mock_client

    run_id = reporter.start_job_run(
        job_name="typed_job",
        job_type=job_type
    )

    assert isinstance(run_id, str)
    # 验证事件被发送（实际类型检查在OpenLineage库中进行）
    mock_client.emit.assert_called_once()


@pytest.mark.parametrize("error_message,programming_language", [
    ("Division by zero", "PYTHON"),
    ("Connection timeout", "PYTHON"),
    ("Invalid data format", "PYTHON"),
])
def test_fail_job_run_with_different_errors(error_message, programming_language):
    """参数化测试不同错误类型的失败"""
    reporter = LineageReporter()
    mock_client = MagicMock()
    reporter.client = mock_client

    # 先开始作业
    run_id = reporter.start_job_run(job_name="error_test_job", job_type="BATCH")

    # 标记失败
    result = reporter.fail_job_run(
        job_name="error_test_job",
        error_message=error_message
    )

    assert result is True

    # 验证错误信息被正确设置
    fail_call_args = mock_client.emit.call_args[0][0]
    error_facet = fail_call_args.run.facets.get("errorMessage")
    assert error_facet.message == error_message
    assert error_facet.programmingLanguage == programming_language