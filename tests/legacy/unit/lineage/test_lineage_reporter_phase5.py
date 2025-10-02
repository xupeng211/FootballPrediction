from datetime import datetime, timezone

from src.lineage.lineage_reporter import LineageReporter
from unittest.mock import Mock, patch
from uuid import uuid4
import pytest

pytestmark = pytest.mark.unit
import pytest
from src.lineage.lineage_reporter import LineageReporter
class TestLineageReporterBasic:
    """数据血缘报告器基础功能测试"""
    def test_lineage_reporter_initialization(self):
        """测试血缘报告器初始化"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter(
                marquez_url = "]http:_/localhost8080[", namespace="]test_namespace["""""
                )
    assert reporter.client ==mock_client
    assert reporter.namespace =="]test_namespace[" assert reporter._active_runs =={}""""
        mock_client_class.assert_called_once_with(url = "]http://localhost8080[")": def test_lineage_reporter_default_initialization(self):"""
        "]""测试血缘报告器默认初始化"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
    assert reporter.client ==mock_client
    assert reporter.namespace =="]football_prediction[" assert reporter._active_runs =={}""""
class TestJobRunLifecycle:
    "]""作业运行生命周期测试"""
    def test_start_job_run_minimal(self):
        """测试启动作业运行（最小参数）"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                run_id = reporter.start_job_run("]test_job[")": assert run_id is not None[" assert len(run_id) ==36  # UUID length[""
    assert "]]]test_job[" in reporter._active_runs[""""
    assert reporter._active_runs["]]test_job["] ==run_id[""""
        # 验证事件发送
        mock_client.emit.assert_called_once()
    def test_start_job_run_error_handling(self):
        "]]""测试启动作业运行错误处理"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client.emit.side_effect = Exception("]Connection failed[")": mock_client_class.return_value = mock_client["""
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                with pytest.raises(Exception, match = "]Connection failed[")": reporter.start_job_run("]test_job[")": def test_complete_job_run_minimal(self):"""
        "]""测试完成作业运行（最小参数）"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                run_id = str(uuid4())
                reporter._active_runs["]test_job["] = run_id[": result = reporter.complete_job_run("]]test_job[")": assert result is True[" assert "]]test_job[" not in reporter._active_runs[""""
        mock_client.emit.assert_called_once()
    def test_complete_job_run_no_active_run(self):
        "]]""测试完成作业运行（无活跃运行）"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                result = reporter.complete_job_run("]nonexistent_job[")": assert result is False[" mock_client.emit.assert_not_called()""
    def test_complete_job_run_error_handling(self):
        "]]""测试完成作业运行错误处理"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client.emit.side_effect = Exception("]Emit failed[")": mock_client_class.return_value = mock_client["""
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                run_id = str(uuid4())
                reporter._active_runs["]test_job["] = run_id[": result = reporter.complete_job_run("]]test_job[")": assert result is False["""
            # 运行记录应该保留，因为发送失败
    assert "]]test_job[" in reporter._active_runs[""""
    def test_fail_job_run(self):
        "]]""测试作业运行失败"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                run_id = str(uuid4())
                reporter._active_runs["]test_job["] = run_id[": result = reporter.fail_job_run("]]test_job[", "]Test error message[")": assert result is True[" assert "]]test_job[" not in reporter._active_runs[""""
        mock_client.emit.assert_called_once()
    def test_fail_job_run_no_active_run(self):
        "]]""测试作业运行失败（无活跃运行）"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                result = reporter.fail_job_run("]nonexistent_job[", "]Error message[")": assert result is False[" mock_client.emit.assert_not_called()""
class TestSpecializedReporting:
    "]]""专业报告功能测试"""
    def test_report_data_collection(self):
        """测试报告数据采集"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                collection_time = datetime.now(timezone.utc)
                run_id = reporter.report_data_collection(
                source_name="]football_api[",": target_table="]raw_matches[",": records_collected=500,": collection_time=collection_time,": source_config = {"]schema[": {"]type[": "]json["}})": assert run_id is not None["""
                # 应该调用了 start_job_run 和 complete_job_run，所以 emit 被调用两次
    assert mock_client.emit.call_count ==2
    def test_report_data_transformation(self):
        "]]""测试报告数据转换"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                run_id = reporter.report_data_transformation(
                source_tables=["]raw_matches[", "]raw_teams["],": target_table="]processed_matches[",": transformation_sql="]SELECT * FROM raw_matches JOIN raw_teams...",": records_processed=300,": transformation_type="CLEANING[")": assert run_id is not None[" assert mock_client.emit.call_count ==2[""
class TestActiveRunsManagement:
    "]]]""活跃运行管理测试"""
    def test_get_active_runs(self):
        """测试获取活跃运行"""
        reporter = LineageReporter()
        # 添加一些活跃运行
        run_id1 = str(uuid4())
        run_id2 = str(uuid4())
        reporter._active_runs["job1["] = run_id1[": reporter._active_runs["]]job2["] = run_id2[": active_runs = reporter.get_active_runs()": assert active_runs =={"]]job1[" run_id1, "]job2[": run_id2}""""
        # 应该返回副本，不影响原数据
    assert active_runs is not reporter._active_runs
    def test_get_active_runs_empty(self):
        "]""测试获取活跃运行（空）"""
        reporter = LineageReporter()
        active_runs = reporter.get_active_runs()
    assert active_runs =={}
    def test_clear_active_runs(self):
        """测试清理活跃运行"""
        reporter = LineageReporter()
        # 添加一些活跃运行
        reporter._active_runs["job1["] = str(uuid4())": reporter._active_runs["]job2["] = str(uuid4())": assert len(reporter._active_runs) ==2[" reporter.clear_active_runs()""
    assert len(reporter._active_runs) ==0
    def test_active_runs_state_management(self):
        "]]""测试活跃运行状态管理"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                # 启动作业
                reporter.start_job_run("]job1[")": reporter.start_job_run("]job2[")": assert len(reporter._active_runs) ==2["""
            # 完成作业
            reporter.complete_job_run("]]job1[")": assert len(reporter._active_runs) ==1[" assert "]]job2[" in reporter._active_runs[""""
    assert "]]job1[" not in reporter._active_runs[""""
        # 失败作业
        reporter.fail_job_run("]]job2[", "]Error[")": assert len(reporter._active_runs) ==0[" class TestLineageReporterEdgeCases:""
    "]]""数据血缘报告器边界情况测试"""
    def test_start_job_run_empty_inputs(self):
        """测试启动作业运行（空输入）"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                # 显式传递空输入列表
                run_id = reporter.start_job_run("]test_job[", inputs=[])": assert run_id is not None[" mock_client.emit.assert_called_once()""
    def test_complete_job_run_empty_outputs(self):
        "]]""测试完成作业运行（空输出）"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                run_id = str(uuid4())
                reporter._active_runs["]test_job["] = run_id[""""
                # 显式传递空输出列表
                result = reporter.complete_job_run("]]test_job[", outputs=[])": assert result is True[" mock_client.emit.assert_called_once()""
    def test_fail_job_run_error_handling(self):
        "]]""测试作业运行失败错误处理"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client.emit.side_effect = Exception("]Network error[")": mock_client_class.return_value = mock_client["""
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                run_id = str(uuid4())
                reporter._active_runs["]test_job["] = run_id[": result = reporter.fail_job_run("]]test_job[", "]Error message[")": assert result is False["""
            # 发送失败时运行记录应该保留
    assert "]]test_job[" in reporter._active_runs[""""
class TestLineageReporterIntegration:
    "]]""数据血缘报告器集成测试"""
    def test_complete_job_lifecycle(self):
        """测试完整作业生命周期"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                # 1. 启动作业
                run_id = reporter.start_job_run("]integration_test[")": assert run_id is not None[" assert len(reporter._active_runs) ==1[""
        # 2. 完成作业
        result = reporter.complete_job_run("]]]integration_test[")": assert result is True[" assert len(reporter._active_runs) ==0[""
    assert mock_client.emit.call_count ==2
    def test_failed_job_lifecycle(self):
        "]]]""测试失败作业生命周期"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                # 1. 启动作业
                run_id = reporter.start_job_run("]failed_job[")": assert run_id is not None[" assert len(reporter._active_runs) ==1[""
        # 2. 标记失败
        result = reporter.fail_job_run("]]]failed_job[", "]Critical error occurred[")": assert result is True[" assert len(reporter._active_runs) ==0[""
    assert mock_client.emit.call_count ==2
    def test_concurrent_job_runs(self):
        "]]]""测试并发作业运行"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                # 启动多个作业
                job_names = [f["]job_{i}"]: for i in range(5)]": run_ids = []": for job_name in job_names = run_id reporter.start_job_run(job_name)": run_ids.append(run_id)"
    assert len(reporter._active_runs) ==5
    assert mock_client.emit.call_count ==5
        # 完成所有作业
        for job_name in job_names:
            reporter.complete_job_run(job_name)
    assert len(reporter._active_runs) ==0
    assert mock_client.emit.call_count ==10
    def test_mixed_success_failure_jobs(self):
        """测试混合成功失败作业"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                # 启动多个作业
                success_jobs = ["]success_1[", "]success_2["]": failed_jobs = ["]failed_1[", "]failed_2["]": for job_name in success_jobs + failed_jobs:": reporter.start_job_run(job_name)": assert len(reporter._active_runs) ==4"
            # 完成成功作业
            for job_name in success_jobs:
            reporter.complete_job_run(job_name)
                # 标记失败作业
                for job_name in failed_jobs:
                reporter.fail_job_run(job_name, f["]{job_name} failed["])": assert len(reporter._active_runs) ==0[" assert mock_client.emit.call_count ==8[""
class TestLineageReporterErrorHandling:
    "]]]""数据血缘报告器错误处理测试"""
    def test_report_data_collection_with_none_time(self):
        """测试报告数据采集（None 时间）"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                # collection_time 参数是必需的，不能为 None，应该抛出 AttributeError
                with pytest.raises(:
                    AttributeError,
                    match="]'NoneType' object has no attribute 'isoformat'"):": reporter.report_data_collection(": source_name="test_source[",": target_table="]test_table[",": records_collected=100,": collection_time=None)": def test_report_data_transformation_empty_sources(self):"
        "]""测试报告数据转换（空数据源）"""
        with patch(:
            "src.lineage.lineage_reporter.OpenLineageClient["""""
        ) as mock_client_class = mock_client Mock()
            mock_client_class.return_value = mock_client
            # Mock all OpenLineage dependencies
            with patch.multiple(:
                "]src.lineage.lineage_reporter[",": InputDataset=Mock,": OutputDataset=Mock,": Run=Mock,"
                Job=Mock,
                RunEvent=Mock,
                source_code_location_job = lambda x x,
                parent_run = lambda x x,
                sql_job = lambda x x,
                schema_dataset = lambda x x,
                error_message_run = lambda x x):
                reporter = LineageReporter()
                run_id = reporter.report_data_transformation(
                source_tables=[],  # 空数据源列表
                target_table="]target_table[",": transformation_sql="]SELECT 1[",": records_processed=1)": assert run_id is not None[" assert mock_client.emit.call_count ==2"
if __name__ =="]]__main__[": pytest.main(["]__file__[", "]-v"])