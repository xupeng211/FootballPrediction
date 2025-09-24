"""
Tests for src/lineage/lineage_reporter.py (Phase 5)

针对数据血缘报告器的全面测试，旨在提升覆盖率至 ≥60%
覆盖 OpenLineage 集成、数据血缘跟踪、错误处理等核心功能
"""

import logging
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

# Import the module to ensure coverage tracking
import src.lineage.lineage_reporter
from src.lineage.lineage_reporter import LineageReporter


class TestLineageReporterBasic:
    """基础功能测试"""

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_initialization(self, mock_client_class):
        """测试初始化"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter("http://test:5000", "test_namespace")

        assert reporter.namespace == "test_namespace"
        assert reporter._active_runs == {}
        mock_client_class.assert_called_once_with(url="http://test:5000")

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_initialization_with_defaults(self, mock_client_class):
        """测试使用默认参数初始化"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        assert reporter.namespace == "football_prediction"
        mock_client_class.assert_called_once_with(url="http://localhost:5000")

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_start_job_run(self, mock_client_class):
        """测试开始作业运行"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock the emit method to avoid OpenLineage event construction issues
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        # Patch the RunEvent and related classes to avoid OpenLineage version issues
        with patch("src.lineage.lineage_reporter.RunEvent") as mock_run_event, patch(
            "src.lineage.lineage_reporter.Job"
        ) as mock_job, patch("src.lineage.lineage_reporter.Run") as mock_run, patch(
            "src.lineage.lineage_reporter.InputDataset"
        ) as mock_input_dataset:
            mock_run_event.return_value = Mock()
            mock_job.return_value = Mock()
            mock_run.return_value = Mock()
            mock_input_dataset.return_value = Mock()

            run_id = reporter.start_job_run(
                job_name="test_job",
                job_type="BATCH",
                inputs=[{"name": "source_data", "namespace": "raw"}],
                description="Test job for data collection",
            )

            # 验证返回值是UUID格式
            assert isinstance(run_id, str)
            assert len(run_id) == 36

            # 验证记录活跃运行
            assert reporter._active_runs["test_job"] == run_id

            # 验证调用了客户端
            mock_client.emit.assert_called_once()

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_start_job_run_with_metadata(self, mock_client_class):
        """测试开始作业运行带元数据"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ):
            run_id = reporter.start_job_run(
                job_name="test_job_meta",
                job_type="BATCH",
                inputs=[],
                description="Test job with metadata",
            )

            assert run_id in reporter._active_runs.values()
            mock_client.emit.assert_called_once()

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_complete_job_run_success(self, mock_client_class):
        """测试成功完成作业运行"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ), patch(
            "src.lineage.lineage_reporter.OutputDataset"
        ):
            # 先启动一个作业
            run_id = reporter.start_job_run(
                job_name="complete_job",
                job_type="BATCH",
                inputs=[],
                description="Test job completion",
            )

            # 完成作业
            result = reporter.complete_job_run("complete_job")

            # 验证完成成功
            assert result is True

            # 验证从活跃运行中移除
            assert "complete_job" not in reporter._active_runs

            # 验证调用了两次emit（start + complete）
            assert mock_client.emit.call_count == 2

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_complete_job_run_not_started(self, mock_client_class):
        """测试完成未启动的作业运行"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 尝试完成未启动的作业
        result = reporter.complete_job_run("nonexistent_job")

        # 应该返回False而不是抛出异常
        assert result is False

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_fail_job_run(self, mock_client_class):
        """测试作业运行失败"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ), patch(
            "src.lineage.lineage_reporter.error_message_run"
        ) as mock_error_facet:
            error_message = "Data validation failed"
            mock_error_facet.return_value = {
                "message": error_message,
                "programmingLanguage": "PYTHON",
            }

            # 先启动一个作业
            run_id = reporter.start_job_run(
                job_name="fail_job",
                job_type="BATCH",
                inputs=[],
                description="Test job failure",
            )

            # 作业失败
            error_message = "Data validation failed"
            result = reporter.fail_job_run("fail_job", error_message)

            # 验证失败操作成功
            assert result is True

            # 验证从活跃运行中移除
            assert "fail_job" not in reporter._active_runs

            # 验证调用了两次emit（start + fail）
            assert mock_client.emit.call_count == 2

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_fail_job_run_not_started(self, mock_client_class):
        """测试失败未启动的作业运行"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        # 尝试失败未启动的作业
        result = reporter.fail_job_run("nonexistent_job", "Some error")

        # 应该返回False而不是抛出异常
        assert result is False


class TestLineageReporterDatasetHandling:
    """数据集处理测试"""

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_create_dataset_with_schema(self, mock_client_class):
        """测试创建带schema的数据集"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        schema = {
            "fields": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
            ]
        }

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ), patch(
            "src.lineage.lineage_reporter.schema_dataset"
        ) as mock_schema:
            mock_schema.return_value = {"fields": schema["fields"]}

            # 测试通过inputs参数传递schema
            run_id = reporter.start_job_run(
                job_name="test_dataset_job",
                job_type="BATCH",
                inputs=[
                    {"name": "test_dataset", "namespace": "test_ns", "schema": schema}
                ],
            )

            # 验证作业启动成功
            assert isinstance(run_id, str)
            assert len(run_id) == 36
            mock_client.emit.assert_called_once()

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_create_dataset_without_schema(self, mock_client_class):
        """测试创建不带schema的数据集"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ):
            run_id = reporter.start_job_run(
                job_name="simple_dataset_job",
                job_type="BATCH",
                inputs=[{"name": "simple_dataset", "namespace": "simple_ns"}],
            )

            assert isinstance(run_id, str)
            assert len(run_id) == 36
            mock_client.emit.assert_called_once()


class TestLineageReporterJobTracking:
    """作业跟踪测试"""

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_track_data_collection_job(self, mock_client_class):
        """测试跟踪数据采集作业 - 简化版本"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        # 直接测试start_job_run而不是report_data_collection
        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ):
            run_id = reporter.start_job_run(
                job_name="data_collection_football_api",
                job_type="BATCH",
                inputs=[{"name": "football_api", "namespace": "external"}],
                description="Collect data from football API",
            )

            assert isinstance(run_id, str)
            mock_client.emit.assert_called_once()

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_track_data_processing_job(self, mock_client_class):
        """测试跟踪数据处理作业"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ), patch(
            "src.lineage.lineage_reporter.OutputDataset"
        ), patch(
            "src.lineage.lineage_reporter.sql_job"
        ), patch(
            "src.lineage.lineage_reporter.source_code_location_job"
        ) as mock_source_location:
            mock_source_location.return_value = {
                "type": "git",
                "url": "src/data/processing/",
            }

            run_id = reporter.report_data_transformation(
                source_tables=["raw_matches"],
                target_table="cleaned_matches",
                transformation_sql="SELECT * FROM raw_matches WHERE status = 'finished'",
                records_processed=500,
                transformation_type="CLEANING",
            )

            assert isinstance(run_id, str)
            # 应该调用两次emit（start + complete）
            assert mock_client.emit.call_count == 2

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_track_model_training_job(self, mock_client_class):
        """测试跟踪模型训练作业"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ), patch(
            "src.lineage.lineage_reporter.OutputDataset"
        ):
            # 模拟模型训练过程
            run_id = reporter.start_job_run(
                job_name="model_training_xgboost_predictor",
                job_type="BATCH",
                inputs=[
                    {"name": "feature_store", "namespace": "football_prediction_db"},
                    {
                        "name": "historical_matches",
                        "namespace": "football_prediction_db",
                    },
                ],
                description="Train XGBoost model for match prediction",
            )

            # 完成训练
            reporter.complete_job_run(
                "model_training_xgboost_predictor",
                outputs=[
                    {
                        "name": "xgboost_v1.pkl",
                        "namespace": "models",
                        "statistics": {"accuracy": 0.85, "training_samples": 10000},
                    }
                ],
            )

            assert isinstance(run_id, str)
            assert mock_client.emit.call_count == 2


class TestLineageReporterComplexScenarios:
    """复杂场景测试"""

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_multiple_concurrent_jobs(self, mock_client_class):
        """测试多个并发作业"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ), patch(
            "src.lineage.lineage_reporter.error_message_run"
        ) as mock_error_facet:
            mock_error_facet.return_value = {
                "message": "Failed",
                "programmingLanguage": "PYTHON",
            }

            # 启动多个作业
            run1 = reporter.start_job_run("job1", "BATCH", [], "First test job")
            run2 = reporter.start_job_run("job2", "BATCH", [], "Second test job")
            run3 = reporter.start_job_run("job3", "BATCH", [], "Third test job")

            assert len(reporter._active_runs) == 3
            assert reporter._active_runs["job1"] == run1
            assert reporter._active_runs["job2"] == run2
            assert reporter._active_runs["job3"] == run3

            # 完成部分作业
            reporter.complete_job_run("job1")
            reporter.fail_job_run("job2", "Failed")

            assert len(reporter._active_runs) == 1
            assert "job3" in reporter._active_runs

            # 完成剩余作业
            reporter.complete_job_run("job3")
            assert len(reporter._active_runs) == 0

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_job_restart_scenario(self, mock_client_class):
        """测试作业重启场景"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ):
            # 启动作业
            run1 = reporter.start_job_run("restart_job", "BATCH", [], "First attempt")

            # 重启同名作业（应该覆盖前一个）
            run2 = reporter.start_job_run("restart_job", "BATCH", [], "Second attempt")

            assert run1 != run2
            assert reporter._active_runs["restart_job"] == run2

            # 完成作业
            reporter.complete_job_run("restart_job")
            assert "restart_job" not in reporter._active_runs


class TestLineageReporterErrorHandling:
    """错误处理测试"""

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_client_emission_failure(self, mock_client_class):
        """测试客户端发送失败"""
        mock_client = Mock()
        mock_client.emit.side_effect = Exception("Network error")
        mock_client_class.return_value = mock_client

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ):
            # 应该抛出异常
            with pytest.raises(Exception, match="Network error"):
                reporter.start_job_run("failing_job", "BATCH", [], "Test failure")

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_invalid_job_data(self, mock_client_class):
        """测试无效作业数据"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ):
            # 测试空作业名称 - 应该仍然能创建UUID并处理
            run_id = reporter.start_job_run("", "BATCH", [], "Empty job name")
            assert isinstance(run_id, str)

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_cleanup_on_failure(self, mock_client_class):
        """测试失败时的清理"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ), patch(
            "src.lineage.lineage_reporter.error_message_run"
        ) as mock_error_facet:
            mock_error_facet.return_value = {
                "message": "Test failure",
                "programmingLanguage": "PYTHON",
            }

            # 启动作业
            run_id = reporter.start_job_run("cleanup_job", "BATCH", [], "Test cleanup")
            assert "cleanup_job" in reporter._active_runs

            # 模拟失败时的清理
            reporter.fail_job_run("cleanup_job", "Test failure")

            # 验证清理完成
            assert "cleanup_job" not in reporter._active_runs


class TestLineageReporterUtilityMethods:
    """工具方法测试"""

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_get_active_jobs(self, mock_client_class):
        """测试获取活跃作业"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        # 初始状态
        assert reporter.get_active_runs() == {}

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ):
            # 启动一些作业
            reporter.start_job_run("job1", "BATCH", [], "First job")
            reporter.start_job_run("job2", "BATCH", [], "Second job")

            active_runs = reporter.get_active_runs()
            assert len(active_runs) == 2
            assert "job1" in active_runs
            assert "job2" in active_runs

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_is_job_active(self, mock_client_class):
        """测试检查作业是否活跃"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        # 作业未启动
        assert "test_job" not in reporter._active_runs

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ):
            # 启动作业
            reporter.start_job_run("test_job", "BATCH", [], "Test job")
            assert "test_job" in reporter._active_runs

            # 完成作业
            reporter.complete_job_run("test_job")
            assert "test_job" not in reporter._active_runs

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_get_run_id(self, mock_client_class):
        """测试获取运行ID"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        # 不存在的作业
        assert reporter._active_runs.get("nonexistent") is None

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ):
            # 启动作业
            run_id = reporter.start_job_run("id_job", "BATCH", [], "Test job")

            # 获取运行ID
            retrieved_id = reporter._active_runs.get("id_job")
            assert retrieved_id == run_id

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_clear_active_runs(self, mock_client_class):
        """测试清理活跃运行"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ):
            # 启动一些作业
            reporter.start_job_run("job1", "BATCH", [], "First job")
            reporter.start_job_run("job2", "BATCH", [], "Second job")

            assert len(reporter._active_runs) == 2

            # 清理所有活跃运行
            reporter.clear_active_runs()

            assert len(reporter._active_runs) == 0


class TestLineageReporterIntegration:
    """集成测试"""

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_complete_data_pipeline_tracking(self, mock_client_class):
        """测试完整数据管道跟踪 - 简化版本"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ), patch(
            "src.lineage.lineage_reporter.OutputDataset"
        ):
            # 1. 数据采集作业
            collection_run = reporter.start_job_run(
                job_name="data_collection_match_api",
                job_type="BATCH",
                inputs=[{"name": "match_api", "namespace": "external"}],
                description="Collect match data from API",
            )

            # 2. 数据处理作业
            processing_run = reporter.start_job_run(
                job_name="process_matches",
                job_type="BATCH",
                inputs=[{"name": "raw_matches", "namespace": "football_prediction_db"}],
                description="Process raw match data",
            )

            # 3. 模型训练作业
            training_run = reporter.start_job_run(
                job_name="model_training_match_predictor",
                job_type="BATCH",
                inputs=[
                    {"name": "clean_matches", "namespace": "football_prediction_db"},
                    {
                        "name": "historical_features",
                        "namespace": "football_prediction_db",
                    },
                ],
                description="Train match prediction model",
            )

            # 完成所有作业
            reporter.complete_job_run("data_collection_match_api")
            reporter.complete_job_run("process_matches")
            reporter.complete_job_run("model_training_match_predictor")

            # 验证所有作业都完成（没有活跃运行）
            assert len(reporter._active_runs) == 0

            # 验证客户端调用次数（3个作业，每个start+complete = 6次调用）
            assert mock_client.emit.call_count == 6

    @patch("src.lineage.lineage_reporter.OpenLineageClient")
    def test_error_recovery_scenario(self, mock_client_class):
        """测试错误恢复场景"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.emit.return_value = None

        reporter = LineageReporter()

        with patch("src.lineage.lineage_reporter.RunEvent"), patch(
            "src.lineage.lineage_reporter.Job"
        ), patch("src.lineage.lineage_reporter.Run"), patch(
            "src.lineage.lineage_reporter.InputDataset"
        ), patch(
            "src.lineage.lineage_reporter.error_message_run"
        ) as mock_error_facet:
            mock_error_facet.return_value = {
                "message": "Processing error",
                "programmingLanguage": "PYTHON",
            }

            # 启动管道作业
            reporter.start_job_run("pipeline_job", "BATCH", [], "ETL pipeline")

            # 模拟中途失败
            reporter.fail_job_run("pipeline_job", "Processing error")

            # 重启作业
            new_run_id = reporter.start_job_run(
                "pipeline_job", "BATCH", [], "ETL pipeline retry"
            )

            # 这次成功完成
            reporter.complete_job_run("pipeline_job")

            # 验证最终状态
            assert len(reporter._active_runs) == 0

            # 验证调用次数（失败1次start+fail，成功1次start+complete = 4次）
            assert mock_client.emit.call_count == 4
