"""
LineageReporter Batch-Ω-006 测试套件

专门为 lineage_reporter.py 设计的测试，目标是将其覆盖率从 0% 提升至 ≥70%
覆盖所有血缘报告功能、OpenLineage集成、数据采集和转换过程跟踪
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional
import uuid
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

try:
    from openlineage.client import OpenLineageClient
    from openlineage.client.event_v2 import InputDataset, Job, OutputDataset, Run, RunEvent
    from openlineage.client.facet_v2 import (
        error_message_run,
        parent_run,
        schema_dataset,
        source_code_location_job,
        sql_job,
    )
    OPENLINEAGE_AVAILABLE = True
except ImportError:
    OPENLINEAGE_AVAILABLE = False
    # Create mock classes for testing
    class MockOpenLineageClient:
        def __init__(self, **kwargs):
            pass
        def emit(self, event):
            pass

    class MockRunEvent:
        def __init__(self, **kwargs):
            pass

    class MockRun:
        def __init__(self, **kwargs):
            pass

    class MockJob:
        def __init__(self, **kwargs):
            pass

    class MockInputDataset:
        def __init__(self, **kwargs):
            pass

    class MockOutputDataset:
        def __init__(self, **kwargs):
            pass


class TestLineageReporterBatchOmega006:
    """LineageReporter Batch-Ω-006 测试类"""

    @pytest.fixture
    def reporter(self, mock_openlineage_client):
        """创建 LineageReporter 实例"""
        from src.lineage.lineage_reporter import LineageReporter

        # Patch the OpenLineageClient initialization to use our mock
        with patch('src.lineage.lineage_reporter.OpenLineageClient', return_value=mock_openlineage_client):
            return LineageReporter(marquez_url="http://localhost:5000")

    @pytest.fixture
    def mock_openlineage_client(self):
        """创建模拟 OpenLineage 客户端"""
        if OPENLINEAGE_AVAILABLE:
            mock_client = Mock(spec=OpenLineageClient)
        else:
            mock_client = Mock(spec=MockOpenLineageClient)
        mock_client.emit.return_value = None
        return mock_client

    @pytest.fixture
    def sample_inputs(self):
        """示例输入数据集"""
        return [
            {
                "name": "source_table1",
                "namespace": "test_namespace",
                "schema": [{"name": "id", "type": "integer"}]
            },
            {
                "name": "source_table2",
                "namespace": "test_namespace"
            }
        ]

    @pytest.fixture
    def sample_outputs(self):
        """示例输出数据集"""
        return [
            {
                "name": "target_table",
                "namespace": "test_namespace",
                "schema": [{"name": "id", "type": "integer"}],
                "statistics": {"rowCount": 1000}
            }
        ]

    def test_lineage_reporter_initialization(self):
        """测试 LineageReporter 初始化"""
        from src.lineage.lineage_reporter import LineageReporter

        reporter = LineageReporter(
            marquez_url="http:_/localhost:5000",
            namespace="test_namespace"
        )

    assert reporter.namespace == "test_namespace"
    assert reporter._active_runs == {}
    assert hasattr(reporter, 'client')

    def test_lineage_reporter_default_values(self):
        """测试 LineageReporter 默认值"""
        from src.lineage.lineage_reporter import LineageReporter

        reporter = LineageReporter()

    assert reporter.namespace == "football_prediction"
    assert reporter._active_runs == {}

    def test_start_job_run_basic(self, reporter, mock_openlineage_client):
        """测试开始作业运行基本功能"""
        with patch.object(reporter, 'client', mock_openlineage_client):
            run_id = reporter.start_job_run(
                job_name="test_job",
                job_type="BATCH"
            )

            # 验证返回了有效的运行ID
    assert isinstance(run_id, str)
    assert len(run_id) > 0

            # 验证活跃运行记录
    assert "test_job" in reporter._active_runs
    assert reporter._active_runs["test_job"] == run_id

            # 验证客户端emit被调用
            mock_openlineage_client.emit.assert_called_once()

    def test_start_job_run_with_inputs(self, reporter, mock_openlineage_client, sample_inputs):
        """测试开始作业运行带输入数据集"""
        with patch.object(reporter, 'client', mock_openlineage_client):
            run_id = reporter.start_job_run(
                job_name="test_job",
                job_type="BATCH",
                inputs=sample_inputs,
                description="Test job description",
                source_location="https:_/github.com/test/repo"
            )

    assert isinstance(run_id, str)
    assert "test_job" in reporter._active_runs

            # 验证客户端emit被调用
            mock_openlineage_client.emit.assert_called_once()

    def test_start_job_run_with_sql(self, reporter, mock_openlineage_client):
        """测试开始作业运行带SQL转换"""
        with patch.object(reporter, 'client', mock_openlineage_client):
            run_id = reporter.start_job_run(
                job_name="test_job",
                job_type="BATCH",
                transformation_sql="SELECT * FROM table"
            )

    assert isinstance(run_id, str)
    assert "test_job" in reporter._active_runs

            # 验证客户端emit被调用
            mock_openlineage_client.emit.assert_called_once()

    def test_start_job_run_empty_inputs(self, reporter, mock_openlineage_client):
        """测试开始作业运行空输入"""
        with patch.object(reporter, 'client', mock_openlineage_client):
            run_id = reporter.start_job_run(
                job_name="test_job",
                inputs=None
            )

    assert isinstance(run_id, str)
    assert "test_job" in reporter._active_runs

            # 验证客户端emit被调用
            mock_openlineage_client.emit.assert_called_once()

    def test_start_job_run_emit_error(self, reporter):
        """测试开始作业运行发送错误"""
        mock_client = Mock()
        mock_client.emit.side_effect = Exception("Emit error")

        with patch.object(reporter, 'client', mock_client):
            with pytest.raises(Exception, match="Emit error"):
                reporter.start_job_run(job_name="test_job")

    def test_complete_job_run_basic(self, reporter, mock_openlineage_client):
        """测试完成作业运行基本功能"""
        # 先开始一个运行，使用mock client
        with patch.object(reporter, 'client', mock_openlineage_client):
            run_id = reporter.start_job_run(job_name="test_job")

            result = reporter.complete_job_run(job_name="test_job")

    assert result is True

            # 验证活跃运行被清理
    assert "test_job" not in reporter._active_runs

            # 验证客户端emit被调用
    assert mock_openlineage_client.emit.call_count == 2  # start + complete

    def test_complete_job_run_with_outputs(self, reporter, mock_openlineage_client, sample_outputs):
        """测试完成作业运行带输出数据集"""
        # 使用mock client
        with patch.object(reporter, 'client', mock_openlineage_client):
            run_id = reporter.start_job_run(job_name="test_job")

            result = reporter.complete_job_run(
                job_name="test_job",
                outputs=sample_outputs,
                metrics={"processed": 1000}
            )

    assert result is True
    assert "test_job" not in reporter._active_runs

    def test_complete_job_run_with_run_id(self, reporter, mock_openlineage_client):
        """测试完成作业运行指定运行ID"""
        # 不先开始运行，直接指定run_id
        import uuid
        custom_run_id = str(uuid.uuid4())

        with patch.object(reporter, 'client', mock_openlineage_client):
            result = reporter.complete_job_run(
                job_name="test_job",
                run_id=custom_run_id
            )

    assert result is True
    assert "test_job" not in reporter._active_runs  # 不应该影响活跃运行

    def test_complete_job_run_no_active_run(self, reporter, mock_openlineage_client):
        """测试完成作业运行无活跃运行"""
        with patch.object(reporter, 'client', mock_openlineage_client):
            result = reporter.complete_job_run(job_name="nonexistent_job")

    assert result is False

    def test_complete_job_run_emit_error(self, reporter, mock_openlineage_client):
        """测试完成作业运行发送错误"""
        # 先开始一个运行，使用mock client
        with patch.object(reporter, 'client', mock_openlineage_client):
            run_id = reporter.start_job_run(job_name="test_job")

        # 然后模拟emit错误
        mock_client = Mock()
        mock_client.emit.side_effect = Exception("Emit error")

        with patch.object(reporter, 'client', mock_client):
            result = reporter.complete_job_run(job_name="test_job")

    assert result is False
            # 运行应该被清理
    assert "test_job" not in reporter._active_runs

    def test_fail_job_run_basic(self, reporter, mock_openlineage_client):
        """测试标记作业运行失败基本功能"""
        # 使用mock client
        with patch.object(reporter, 'client', mock_openlineage_client):
            run_id = reporter.start_job_run(job_name="test_job")

            result = reporter.fail_job_run(
                job_name="test_job",
                error_message="Test error"
            )

    assert result is True

            # 验证活跃运行被清理
    assert "test_job" not in reporter._active_runs

            # 验证客户端emit被调用
    assert mock_openlineage_client.emit.call_count == 2  # start + fail

    def test_fail_job_run_with_run_id(self, reporter, mock_openlineage_client):
        """测试标记作业运行失败指定运行ID"""
        import uuid
        custom_run_id = str(uuid.uuid4())

        with patch.object(reporter, 'client', mock_openlineage_client):
            result = reporter.fail_job_run(
                job_name="test_job",
                error_message="Test error",
                run_id=custom_run_id
            )

    assert result is True

    def test_fail_job_run_no_active_run(self, reporter, mock_openlineage_client):
        """测试标记作业运行失败无活跃运行"""
        with patch.object(reporter, 'client', mock_openlineage_client):
            result = reporter.fail_job_run(
                job_name="nonexistent_job",
                error_message="Test error"
            )

    assert result is False

    def test_fail_job_run_emit_error(self, reporter, mock_openlineage_client):
        """测试标记作业运行失败发送错误"""
        # 先开始一个运行，使用mock client
        with patch.object(reporter, 'client', mock_openlineage_client):
            run_id = reporter.start_job_run(job_name="test_job")

        # 然后模拟emit错误
        mock_client = Mock()
        mock_client.emit.side_effect = Exception("Emit error")

        with patch.object(reporter, 'client', mock_client):
            result = reporter.fail_job_run(
                job_name="test_job",
                error_message="Test error"
            )

    assert result is False
            # 运行不会被清理（因为emit失败，清理只在成功时执行）
    assert "test_job" in reporter._active_runs

    def test_report_data_collection_basic(self, reporter, mock_openlineage_client):
        """测试报告数据采集基本功能"""
        collection_time = datetime.now(timezone.utc)

        with patch.object(reporter, 'client', mock_openlineage_client), \
             patch.object(reporter, 'start_job_run') as mock_start, \
             patch.object(reporter, 'complete_job_run') as mock_complete:

            mock_start.return_value = "test_run_id"

            run_id = reporter.report_data_collection(
                source_name="api_source",
                target_table="raw_data",
                records_collected=1000,
                collection_time=collection_time
            )

    assert run_id == "test_run_id"

            # 验证调用了start和complete
            mock_start.assert_called_once()
            mock_complete.assert_called_once()

            # 验证参数
            call_args = mock_start.call_args[1]
    assert call_args["job_name"] == "data_collection_api_source"
    assert call_args["job_type"] == "BATCH"
    assert len(call_args["inputs"]) == 1
    assert call_args["inputs"][0]["name"] == "api_source"

    def test_report_data_collection_with_config(self, reporter, mock_openlineage_client):
        """测试报告数据采集带配置"""
        collection_time = datetime.now(timezone.utc)
        source_config = {"schema": [{"name": "id", "type": "integer"}]}

        with patch.object(reporter, 'client', mock_openlineage_client), \
             patch.object(reporter, 'start_job_run') as mock_start, \
             patch.object(reporter, 'complete_job_run') as mock_complete:

            mock_start.return_value = "test_run_id"

            run_id = reporter.report_data_collection(
                source_name="api_source",
                target_table="raw_data",
                records_collected=1000,
                collection_time=collection_time,
                source_config=source_config
            )

    assert run_id == "test_run_id"

            # 验证schema传递
            call_args = mock_start.call_args[1]
    assert call_args["inputs"][0]["schema"] == source_config["schema"]

    def test_report_data_transformation_basic(self, reporter, mock_openlineage_client):
        """测试报告数据转换基本功能"""
        with patch.object(reporter, 'client', mock_openlineage_client), \
             patch.object(reporter, 'start_job_run') as mock_start, \
             patch.object(reporter, 'complete_job_run') as mock_complete:

            mock_start.return_value = "test_run_id"

            run_id = reporter.report_data_transformation(
                source_tables=["source1", "source2"],
                target_table="target_table",
                transformation_sql="SELECT * FROM source1",
                records_processed=500
            )

    assert run_id == "test_run_id"

            # 验证调用了start和complete
            mock_start.assert_called_once()
            mock_complete.assert_called_once()

            # 验证参数
            call_args = mock_start.call_args[1]
    assert call_args["job_name"] == "data_transformation_target_table"
    assert call_args["job_type"] == "BATCH"
    assert len(call_args["inputs"]) == 2
    assert call_args["inputs"][0]["name"] == "source1"
    assert call_args["inputs"][1]["name"] == "source2"

    def test_report_data_transformation_with_type(self, reporter, mock_openlineage_client):
        """测试报告数据转换带类型"""
        with patch.object(reporter, 'client', mock_openlineage_client), \
             patch.object(reporter, 'start_job_run') as mock_start, \
             patch.object(reporter, 'complete_job_run') as mock_complete:

            mock_start.return_value = "test_run_id"

            run_id = reporter.report_data_transformation(
                source_tables=["source1"],
                target_table="target_table",
                transformation_sql="SELECT * FROM source1",
                records_processed=500,
                transformation_type="CLEANING"
            )

    assert run_id == "test_run_id"

            # 验证转换类型传递
            call_args = mock_start.call_args[1]
    assert call_args["description"] == "CLEANING transformation to create target_table"

            complete_args = mock_complete.call_args[1]
    assert complete_args["metrics"]["transformation_type"] == "CLEANING"

    def test_get_active_runs(self, reporter):
        """测试获取活跃运行"""
        # 开始几个运行
        run_id1 = reporter.start_job_run(job_name="job1")
        run_id2 = reporter.start_job_run(job_name="job2")

        active_runs = reporter.get_active_runs()

    assert isinstance(active_runs, dict)
    assert len(active_runs) == 2
    assert active_runs["job1"] == run_id1
    assert active_runs["job2"] == run_id2

        # 验证返回的是副本
        active_runs["job1"] = "modified"
    assert reporter._active_runs["job1"] == run_id1

    def test_clear_active_runs(self, reporter):
        """测试清理活跃运行"""
        # 开始几个运行
        reporter.start_job_run(job_name="job1")
        reporter.start_job_run(job_name="job2")

    assert len(reporter._active_runs) == 2

        reporter.clear_active_runs()

    assert len(reporter._active_runs) == 0

    def test_uuid_generation(self, reporter):
        """测试UUID生成"""
        run_id1 = reporter.start_job_run(job_name="job1")
        run_id2 = reporter.start_job_run(job_name="job2")

        # 验证UUID是唯一的
    assert run_id1 != run_id2
    assert isinstance(run_id1, str)
    assert isinstance(run_id2, str)

    def test_event_construction_start(self, reporter):
        """测试开始事件构建"""
        with patch('src.lineage.lineage_reporter.RunEvent') as mock_event_class:
            mock_event = Mock()
            mock_event_class.return_value = mock_event

            run_id = reporter.start_job_run(job_name="test_job")

            # 验证RunEvent被正确构造
            mock_event_class.assert_called_once()
            call_args = mock_event_class.call_args[1]

    assert call_args["eventType"] == "START"
    assert call_args["run"].runId == run_id
    assert call_args["job"].name == "test_job"
    assert call_args["job"].namespace == "football_prediction"
    assert call_args["producer"] == "football_prediction_lineage_reporter"

    def test_event_construction_complete(self, reporter):
        """测试完成事件构建"""
        run_id = reporter.start_job_run(job_name="test_job")

        with patch('src.lineage.lineage_reporter.RunEvent') as mock_event_class:
            mock_event = Mock()
            mock_event_class.return_value = mock_event

            reporter.complete_job_run(job_name="test_job")

            # 验证RunEvent被正确构造
            mock_event_class.assert_called_once()
            call_args = mock_event_class.call_args[1]

    assert call_args["eventType"] == "COMPLETE"
    assert call_args["run"].runId == run_id
    assert call_args["job"].name == "test_job"
    assert call_args["producer"] == "football_prediction_lineage_reporter"

    def test_event_construction_fail(self, reporter):
        """测试失败事件构建"""
        run_id = reporter.start_job_run(job_name="test_job")

        with patch('src.lineage.lineage_reporter.RunEvent') as mock_event_class:
            mock_event = Mock()
            mock_event_class.return_value = mock_event

            reporter.fail_job_run(job_name="test_job", error_message="Test error")

            # 验证RunEvent被正确构造
            mock_event_class.assert_called_once()
            call_args = mock_event_class.call_args[1]

    assert call_args["eventType"] == "FAIL"
    assert call_args["run"].runId == run_id
    assert call_args["job"].name == "test_job"
    assert call_args["producer"] == "football_prediction_lineage_reporter"

    def test_dataset_facet_handling(self, reporter):
        """测试数据集facet处理"""
        inputs_with_schema = [
            {
                "name": "test_table",
                "namespace": "test_namespace",
                "schema": [{"name": "id", "type": "integer"}]
            }
        ]

        with patch('src.lineage.lineage_reporter.InputDataset') as mock_input_dataset:
            mock_input_dataset.return_value = Mock()

            run_id = reporter.start_job_run(job_name="test_job", inputs=inputs_with_schema)

            # 验证InputDataset被正确构造
            mock_input_dataset.assert_called_once()
            call_args = mock_input_dataset.call_args[1]

    assert call_args["namespace"] == "test_namespace"
    assert call_args["name"] == "test_table"
    assert "facets" in call_args

    def test_job_facet_handling(self, reporter):
        """测试作业facet处理"""
        with patch('src.lineage.lineage_reporter.source_code_location_job') as mock_source_code, \
             patch('src.lineage.lineage_reporter.sql_job') as mock_sql_job:

            run_id = reporter.start_job_run(
                job_name="test_job",
                description="Test description",
                source_location="https:_/github.com/test/repo",
                transformation_sql="SELECT * FROM table"
            )

            # 验证facet被正确处理
            mock_source_code.SourceCodeLocationJobFacet.assert_called_once_with(
                type="git", url="https://github.com/test/repo"
            )
            mock_sql_job.SQLJobFacet.assert_called_once_with(query="SELECT * FROM table")

    def test_metrics_facet_handling(self, reporter):
        """测试指标facet处理"""
        run_id = reporter.start_job_run(job_name="test_job")

        outputs = [
            {
                "name": "test_table",
                "namespace": "test_namespace",
                "statistics": {"rowCount": 1000}
            }
        ]

        with patch('src.lineage.lineage_reporter.OutputDataset') as mock_output_dataset:
            mock_output_dataset.return_value = Mock()

            reporter.complete_job_run(job_name="test_job", outputs=outputs, metrics={"processed": 1000})

            # 验证OutputDataset被正确构造
            mock_output_dataset.assert_called_once()
            call_args = mock_output_dataset.call_args[1]

    assert "facets" in call_args

    def test_error_facet_handling(self, reporter):
        """测试错误facet处理"""
        run_id = reporter.start_job_run(job_name="test_job")

        with patch('src.lineage.lineage_reporter.error_message_run') as mock_error_message:
            mock_error_message.ErrorMessageRunFacet.return_value = Mock()

            reporter.fail_job_run(job_name="test_job", error_message="Test error")

            # 验证错误facet被正确构造
            mock_error_message.ErrorMessageRunFacet.assert_called_once_with(
                message="Test error", programmingLanguage="PYTHON"
            )

    def test_namespace_handling(self, reporter):
        """测试命名空间处理"""
        # 测试默认命名空间
        run_id = reporter.start_job_run(job_name="test_job")

        # 验证使用了默认命名空间
    assert reporter.namespace == "football_prediction"

        # 测试自定义命名空间
        custom_reporter = reporter.__class__(namespace="custom_namespace")
    assert custom_reporter.namespace == "custom_namespace"

    def test_logging_functionality(self, reporter):
        """测试日志记录功能"""
        with patch('src.lineage.lineage_reporter.logger') as mock_logger:
            mock_client = Mock()
            reporter.client = mock_client

            run_id = reporter.start_job_run(job_name="test_job")

            # 验证日志记录
            mock_logger.info.assert_called_with(f"Started job run: test_job with run_id: {run_id}")

    def test_error_logging(self, reporter):
        """测试错误日志记录"""
        with patch('src.lineage.lineage_reporter.logger') as mock_logger:
            mock_client = Mock()
            mock_client.emit.side_effect = Exception("Test error")
            reporter.client = mock_client

            try:
                reporter.start_job_run(job_name="test_job")
            except Exception:
                pass

            # 验证错误日志记录
            mock_logger.error.assert_called_with("Failed to emit start event for job test_job: Test error")

    def test_concurrent_job_runs(self, reporter):
        """测试并发作业运行"""
        # 开始多个作业运行
        run_id1 = reporter.start_job_run(job_name="job1")
        run_id2 = reporter.start_job_run(job_name="job2")
        run_id3 = reporter.start_job_run(job_name="job3")

        # 验证所有运行都在活跃状态
        active_runs = reporter.get_active_runs()
    assert len(active_runs) == 3
    assert "job1" in active_runs
    assert "job2" in active_runs
    assert "job3" in active_runs

        # 完成部分作业
        reporter.complete_job_run(job_name="job2")

        # 验证剩余活跃运行
        active_runs = reporter.get_active_runs()
    assert len(active_runs) == 2
    assert "job1" in active_runs
    assert "job3" in active_runs
    assert "job2" not in active_runs

    def test_run_id_consistency(self, reporter):
        """测试运行ID一致性"""
        # 开始作业运行
        run_id = reporter.start_job_run(job_name="test_job")

        # 验证活跃运行中的ID一致
    assert reporter._active_runs["test_job"] == run_id

        # 完成作业时使用相同的ID
        with patch.object(reporter.client, 'emit'):
            result = reporter.complete_job_run(job_name="test_job")
    assert result is True

    def test_empty_parameters_handling(self, reporter):
        """测试空参数处理"""
        # 测试空输入
        run_id = reporter.start_job_run(job_name="test_job", inputs=[])

        # 测试空输出
        with patch.object(reporter.client, 'emit'):
            result = reporter.complete_job_run(job_name="test_job", outputs=[])
    assert result is True

    def test_global_instance(self):
        """测试全局实例"""
        from src.lineage.lineage_reporter import lineage_reporter

        # 验证全局实例存在
    assert lineage_reporter is not None
    assert hasattr(lineage_reporter, 'namespace')
    assert hasattr(lineage_reporter, '_active_runs')