"""
Enhanced test file for lineage_reporter.py module
Provides comprehensive coverage for OpenLineage integration and data lineage tracking
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, Any, List, Optional

# Import from src directory
from src.lineage.lineage_reporter import LineageReporter


class TestLineageReporter:
    """Test LineageReporter class methods and functionality"""

    @pytest.fixture
    def mock_openlineage_client(self):
        """Mock OpenLineageClient for testing"""
        mock_client = Mock()
        mock_client.emit = Mock()
        return mock_client

    @pytest.fixture
    def lineage_reporter(self, mock_openlineage_client):
        """Create LineageReporter instance with mocked client"""
        with patch('src.lineage.lineage_reporter.OpenLineageClient', return_value=mock_openlineage_client):
            reporter = LineageReporter(
                marquez_url="http://test-marquez:5000",
                namespace="test_namespace"
            )
            return reporter

    @pytest.fixture
    def sample_job_inputs(self):
        """Sample input datasets for testing"""
        return [
            {
                "name": "input_table_1",
                "namespace": "test_db",
                "schema": {"fields": [{"name": "id", "type": "integer"}]}
            },
            {
                "name": "input_table_2",
                "namespace": "test_db",
                "schema": {"fields": [{"name": "name", "type": "string"}]}
            }
        ]

    @pytest.fixture
    def sample_job_outputs(self):
        """Sample output datasets for testing"""
        return [
            {
                "name": "output_table_1",
                "namespace": "test_db",
                "schema": {"fields": [{"name": "result_id", "type": "integer"}]},
                "statistics": {"rowCount": 100, "processingTime": "5s"}
            }
        ]

    def test_lineage_reporter_init(self, mock_openlineage_client):
        """Test LineageReporter initialization"""
        with patch('src.lineage.lineage_reporter.OpenLineageClient', return_value=mock_openlineage_client):
            reporter = LineageReporter(
                marquez_url="http://custom-marquez:8080",
                namespace="custom_namespace"
            )

            assert reporter.namespace == "custom_namespace"
            assert isinstance(reporter._active_runs, dict)
            assert len(reporter._active_runs) == 0
            assert reporter.client == mock_openlineage_client

    def test_lineage_reporter_init_defaults(self, mock_openlineage_client):
        """Test LineageReporter initialization with default values"""
        with patch('src.lineage.lineage_reporter.OpenLineageClient', return_value=mock_openlineage_client):
            reporter = LineageReporter()

            assert reporter.namespace == "football_prediction"
            assert len(reporter._active_runs) == 0

    def test_start_job_run_basic(self, lineage_reporter):
        """Test basic job run start"""
        job_name = "test_job"
        run_id = lineage_reporter.start_job_run(job_name)

        assert isinstance(run_id, str)
        assert job_name in lineage_reporter._active_runs
        assert lineage_reporter._active_runs[job_name] == run_id

        # Verify client.emit was called
        lineage_reporter.client.emit.assert_called_once()
        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert call_args.eventType == "START"
        assert call_args.job.name == job_name
        assert call_args.job.namespace == lineage_reporter.namespace

    def test_start_job_run_with_inputs(self, lineage_reporter, sample_job_inputs):
        """Test job run start with input datasets"""
        job_name = "test_job_with_inputs"
        run_id = lineage_reporter.start_job_run(
            job_name=job_name,
            inputs=sample_job_inputs
        )

        assert run_id is not None
        assert job_name in lineage_reporter._active_runs

        # Verify input datasets were included
        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert len(call_args.inputs) == len(sample_job_inputs)
        assert call_args.inputs[0].name == "input_table_1"

    def test_start_job_run_with_all_parameters(self, lineage_reporter, sample_job_inputs):
        """Test job run start with all optional parameters"""
        job_name = "comprehensive_job"
        description = "Test job with all parameters"
        source_location = "https://github.com/test/repo"
        parent_run_id = "parent_run_123"
        transformation_sql = "SELECT * FROM table"

        run_id = lineage_reporter.start_job_run(
            job_name=job_name,
            job_type="STREAM",
            inputs=sample_job_inputs,
            description=description,
            source_location=source_location,
            parent_run_id=parent_run_id,
            transformation_sql=transformation_sql
        )

        assert run_id is not None
        assert lineage_reporter._active_runs[job_name] == run_id

        # Verify all parameters were included in the event
        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert call_args.job.name == job_name
        assert description in call_args.job.facets["description"]["description"]
        # TODO: Add parent_run test when implemented

    def test_start_job_run_emit_failure(self, lineage_reporter):
        """Test job run start when emit fails"""
        lineage_reporter.client.emit.side_effect = Exception("Network error")

        with pytest.raises(Exception) as exc_info:
            lineage_reporter.start_job_run("failing_job")

        assert "Network error" in str(exc_info.value)

    def test_complete_job_run_basic(self, lineage_reporter):
        """Test basic job run completion"""
        job_name = "test_job"

        # First start a job
        run_id = lineage_reporter.start_job_run(job_name)

        # Then complete it
        result = lineage_reporter.complete_job_run(job_name)

        assert result is True
        assert job_name not in lineage_reporter._active_runs  # Should be removed

        # Verify client.emit was called with COMPLETE event
        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert call_args.eventType == "COMPLETE"
        assert call_args.run.runId == run_id

    def test_complete_job_run_with_outputs(self, lineage_reporter, sample_job_outputs):
        """Test job run completion with output datasets"""
        job_name = "test_job"
        run_id = lineage_reporter.start_job_run(job_name)

        result = lineage_reporter.complete_job_run(
            job_name=job_name,
            outputs=sample_job_outputs,
            metrics={"records_processed": 100}
        )

        assert result is True

        # Verify output datasets were included
        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert len(call_args.outputs) == len(sample_job_outputs)
        assert call_args.outputs[0].name == "output_table_1"

    def test_complete_job_run_with_custom_run_id(self, lineage_reporter):
        """Test job run completion with custom run_id"""
        job_name = "test_job"
        custom_run_id = "550e8400-e29b-41d4-a716-446655440000"  # Valid UUID

        # Don't start the job, use custom run_id
        result = lineage_reporter.complete_job_run(
            job_name=job_name,
            run_id=custom_run_id
        )

        assert result is True

        # Verify custom run_id was used
        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert call_args.run.runId == custom_run_id

    def test_complete_job_run_no_active_run(self, lineage_reporter):
        """Test job run completion when no active run exists"""
        result = lineage_reporter.complete_job_run("nonexistent_job")

        assert result is False

    def test_complete_job_run_emit_failure(self, lineage_reporter):
        """Test job run completion when emit fails"""
        job_name = "test_job"
        lineage_reporter.start_job_run(job_name)
        lineage_reporter.client.emit.side_effect = Exception("Network error")

        result = lineage_reporter.complete_job_run(job_name)

        assert result is False
        # Job should still be removed from active runs despite failure
        assert job_name not in lineage_reporter._active_runs

    def test_fail_job_run_basic(self, lineage_reporter):
        """Test basic job run failure"""
        job_name = "test_job"
        run_id = lineage_reporter.start_job_run(job_name)
        error_message = "Test error message"

        result = lineage_reporter.fail_job_run(job_name, error_message)

        assert result is True
        assert job_name not in lineage_reporter._active_runs

        # Verify FAIL event was sent
        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert call_args.eventType == "FAIL"
        assert call_args.run.runId == run_id
        assert "errorMessage" in call_args.run.facets

    def test_fail_job_run_with_custom_run_id(self, lineage_reporter):
        """Test job run failure with custom run_id"""
        job_name = "test_job"
        custom_run_id = "550e8400-e29b-41d4-a716-446655440001"  # Valid UUID
        error_message = "Custom error"

        result = lineage_reporter.fail_job_run(
            job_name=job_name,
            error_message=error_message,
            run_id=custom_run_id
        )

        assert result is True

        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert call_args.run.runId == custom_run_id
        assert call_args.run.facets["errorMessage"].message == error_message

    def test_fail_job_run_no_active_run(self, lineage_reporter):
        """Test job run failure when no active run exists"""
        result = lineage_reporter.fail_job_run("nonexistent_job", "error")

        assert result is False

    def test_fail_job_run_emit_failure(self, lineage_reporter):
        """Test job run failure when emit fails"""
        job_name = "test_job"
        lineage_reporter.start_job_run(job_name)
        lineage_reporter.client.emit.side_effect = Exception("Network error")

        result = lineage_reporter.fail_job_run(job_name, "error")

        assert result is False

    def test_report_data_collection(self, lineage_reporter):
        """Test data collection reporting"""
        source_name = "football_api"
        target_table = "raw_matches"
        records_collected = 1000
        collection_time = datetime.now(timezone.utc)
        source_config = {"schema": {"fields": ["id", "name"]}}

        run_id = lineage_reporter.report_data_collection(
            source_name=source_name,
            target_table=target_table,
            records_collected=records_collected,
            collection_time=collection_time,
            source_config=source_config
        )

        assert isinstance(run_id, str)

        # Verify two events were sent (START and COMPLETE)
        assert lineage_reporter.client.emit.call_count == 2

        # Check START event
        start_call = lineage_reporter.client.emit.call_args_list[0][0][0]
        assert start_call.eventType == "START"
        assert "data_collection_football_api" in start_call.job.name

        # Check COMPLETE event
        complete_call = lineage_reporter.client.emit.call_args_list[1][0][0]
        assert complete_call.eventType == "COMPLETE"
        assert len(complete_call.outputs) == 1
        assert complete_call.outputs[0].name == target_table

    def test_report_data_transformation(self, lineage_reporter):
        """Test data transformation reporting"""
        source_tables = ["raw_matches", "teams"]
        target_table = "processed_matches"
        transformation_sql = "SELECT * FROM raw_matches JOIN teams ON..."
        records_processed = 500

        run_id = lineage_reporter.report_data_transformation(
            source_tables=source_tables,
            target_table=target_table,
            transformation_sql=transformation_sql,
            records_processed=records_processed,
            transformation_type="ETL"
        )

        assert isinstance(run_id, str)

        # Verify two events were sent
        assert lineage_reporter.client.emit.call_count == 2

        # Check inputs in start event and outputs in complete event
        start_call = lineage_reporter.client.emit.call_args_list[0][0][0]
        complete_call = lineage_reporter.client.emit.call_args_list[1][0][0]

        assert len(start_call.inputs) == len(source_tables)
        assert len(complete_call.outputs) == 1
        assert complete_call.outputs[0].name == target_table

    def test_get_active_runs(self, lineage_reporter):
        """Test getting active runs"""
        # Initially no active runs
        active_runs = lineage_reporter.get_active_runs()
        assert active_runs == {}

        # Start some jobs
        run1 = lineage_reporter.start_job_run("job1")
        run2 = lineage_reporter.start_job_run("job2")

        active_runs = lineage_reporter.get_active_runs()
        assert len(active_runs) == 2
        assert active_runs["job1"] == run1
        assert active_runs["job2"] == run2

        # Should return a copy, not the original
        active_runs["job1"] = "modified"
        original_runs = lineage_reporter.get_active_runs()
        assert original_runs["job1"] == run1  # Should not be modified

    def test_clear_active_runs(self, lineage_reporter):
        """Test clearing all active runs"""
        # Start some jobs
        lineage_reporter.start_job_run("job1")
        lineage_reporter.start_job_run("job2")

        assert len(lineage_reporter._active_runs) == 2

        lineage_reporter.clear_active_runs()

        assert len(lineage_reporter._active_runs) == 0

    def test_job_lifecycle_complete_workflow(self, lineage_reporter, sample_job_inputs, sample_job_outputs):
        """Test complete job lifecycle: start -> complete"""
        job_name = "lifecycle_test_job"

        # Start job
        run_id = lineage_reporter.start_job_run(
            job_name=job_name,
            inputs=sample_job_inputs,
            description="Complete lifecycle test"
        )

        # Complete job
        result = lineage_reporter.complete_job_run(
            job_name=job_name,
            outputs=sample_job_outputs,
            metrics={"success": True, "records": 42}
        )

        assert result is True
        assert job_name not in lineage_reporter._active_runs

        # Verify events
        assert lineage_reporter.client.emit.call_count == 2

        start_event = lineage_reporter.client.emit.call_args_list[0][0][0]
        complete_event = lineage_reporter.client.emit.call_args_list[1][0][0]

        assert start_event.eventType == "START"
        assert complete_event.eventType == "COMPLETE"
        assert start_event.run.runId == complete_event.run.runId == run_id

    def test_job_lifecycle_failure_workflow(self, lineage_reporter, sample_job_inputs):
        """Test job lifecycle with failure: start -> fail"""
        job_name = "failure_test_job"
        error_message = "Intentional test failure"

        # Start job
        run_id = lineage_reporter.start_job_run(
            job_name=job_name,
            inputs=sample_job_inputs
        )

        # Fail job
        result = lineage_reporter.fail_job_run(job_name, error_message)

        assert result is True
        assert job_name not in lineage_reporter._active_runs

        # Verify events
        assert lineage_reporter.client.emit.call_count == 2

        start_event = lineage_reporter.client.emit.call_args_list[0][0][0]
        fail_event = lineage_reporter.client.emit.call_args_list[1][0][0]

        assert start_event.eventType == "START"
        assert fail_event.eventType == "FAIL"
        assert start_event.run.runId == fail_event.run.runId == run_id
        assert fail_event.run.facets["errorMessage"].message == error_message


class TestLineageReporterEdgeCases:
    """Edge case tests for LineageReporter"""

    def test_start_job_run_empty_inputs(self, lineage_reporter):
        """Test job run start with empty inputs list"""
        run_id = lineage_reporter.start_job_run(
            job_name="empty_inputs_job",
            inputs=[]
        )

        assert run_id is not None
        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert len(call_args.inputs) == 0

    def test_start_job_run_inputs_with_missing_names(self, lineage_reporter):
        """Test job run start with inputs missing names"""
        inputs = [
            {"namespace": "test_db"},  # Missing name
            {"name": "table2"}  # Missing namespace
        ]

        run_id = lineage_reporter.start_job_run(
            job_name="malformed_inputs_job",
            inputs=inputs
        )

        assert run_id is not None
        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert len(call_args.inputs) == 2
        # Should use default values
        assert call_args.inputs[0].name == "unknown"

    def test_complete_job_run_empty_outputs(self, lineage_reporter):
        """Test job run completion with empty outputs list"""
        lineage_reporter.start_job_run("test_job")

        result = lineage_reporter.complete_job_run(
            job_name="test_job",
            outputs=[]
        )

        assert result is True
        call_args = lineage_reporter.client.emit.call_args[0][0]
        assert len(call_args.outputs) == 0

    def test_report_data_collection_minimal_params(self, lineage_reporter):
        """Test data collection reporting with minimal parameters"""
        run_id = lineage_reporter.report_data_collection(
            source_name="test_source",
            target_table="test_table",
            records_collected=100,
            collection_time=datetime.now(timezone.utc)
        )

        assert run_id is not None
        # Should still work without source_config

    def test_report_data_transformation_minimal_params(self, lineage_reporter):
        """Test data transformation reporting with minimal parameters"""
        run_id = lineage_reporter.report_data_transformation(
            source_tables=["source1"],
            target_table="target1",
            transformation_sql="SELECT * FROM source1",
            records_processed=50
        )

        assert run_id is not None
        # Should work with default transformation_type

    def test_multiple_concurrent_jobs(self, lineage_reporter):
        """Test handling multiple concurrent jobs"""
        jobs = []
        for i in range(5):
            run_id = lineage_reporter.start_job_run(f"concurrent_job_{i}")
            jobs.append((f"concurrent_job_{i}", run_id))

        # All jobs should be active
        active_runs = lineage_reporter.get_active_runs()
        assert len(active_runs) == 5

        # Complete all jobs
        for job_name, run_id in jobs:
            result = lineage_reporter.complete_job_run(
                job_name=job_name,
                run_id=run_id
            )
            assert result is True

        # No active runs should remain
        active_runs = lineage_reporter.get_active_runs()
        assert len(active_runs) == 0

    def test_job_run_id_uniqueness(self, lineage_reporter):
        """Test that each job run gets a unique ID"""
        run_ids = []
        for i in range(10):
            run_id = lineage_reporter.start_job_run(f"unique_test_job_{i}")
            run_ids.append(run_id)

        # All run IDs should be unique
        assert len(set(run_ids)) == len(run_ids)
        for run_id in run_ids:
            assert isinstance(run_id, str)
            assert len(run_id) > 0

    def test_clear_active_runs_with_no_runs(self, lineage_reporter):
        """Test clearing active runs when none exist"""
        # Should not raise an error
        lineage_reporter.clear_active_runs()
        assert len(lineage_reporter._active_runs) == 0

    def test_complete_job_after_clear(self, lineage_reporter):
        """Test completing job after clearing active runs"""
        lineage_reporter.start_job_run("test_job")
        lineage_reporter.clear_active_runs()

        # Should fail since active run was cleared
        result = lineage_reporter.complete_job_run("test_job")
        assert result is False


class TestLineageReporterIntegration:
    """Integration tests for LineageReporter"""

    def test_football_prediction_workflow(self, lineage_reporter):
        """Test realistic football prediction data workflow"""
        # 1. Data collection from external API
        collection_run_id = lineage_reporter.report_data_collection(
            source_name="football_data_api",
            target_table="raw_matches",
            records_collected=1500,
            collection_time=datetime.now(timezone.utc),
            source_config={
                "schema": {
                    "fields": [
                        {"name": "match_id", "type": "string"},
                        {"name": "home_team", "type": "string"},
                        {"name": "away_team", "type": "string"}
                    ]
                },
                "api_endpoint": "https://api.football-data.org/v4/matches"
            }
        )

        # 2. Data transformation
        transformation_run_id = lineage_reporter.report_data_transformation(
            source_tables=["raw_matches", "teams"],
            target_table="processed_matches",
            transformation_sql="""
                INSERT INTO processed_matches
                SELECT
                    r.match_id,
                    r.home_team_id,
                    r.away_team_id,
                    t.home_team_name,
                    t.away_team_name,
                    r.match_date
                FROM raw_matches r
                JOIN teams t ON r.home_team_id = t.team_id
            """,
            records_processed=1500,
            transformation_type="CLEANSING"
        )

        # 3. Feature engineering
        feature_run_id = lineage_reporter.report_data_transformation(
            source_tables=["processed_matches", "team_stats"],
            target_table="match_features",
            transformation_sql="""
                SELECT
                    m.match_id,
                    m.home_team_id,
                    m.away_team_id,
                    ts.home_recent_form,
                    ts.away_recent_form,
                    m.home_win_probability
                FROM processed_matches m
                JOIN team_stats ts ON m.match_id = ts.match_id
            """,
            records_processed=1450,
            transformation_type="FEATURE_ENGINEERING"
        )

        # Verify all run IDs are unique
        run_ids = [collection_run_id, transformation_run_id, feature_run_id]
        assert len(set(run_ids)) == len(run_ids)

        # Verify correct number of events (2 per operation)
        assert lineage_reporter.client.emit.call_count == 6

        # Verify the workflow sequence
        events = [call[0][0] for call in lineage_reporter.client.emit.call_args_list]
        event_types = [event.eventType for event in events]

        # Should alternate START, COMPLETE for each operation
        expected_sequence = ["START", "COMPLETE", "START", "COMPLETE", "START", "COMPLETE"]
        assert event_types == expected_sequence

    def test_error_handling_workflow(self, lineage_reporter):
        """Test error handling in realistic workflow"""
        # Start a data collection job
        run_id = lineage_reporter.start_job_run(
            job_name="data_collection_failed_api",
            inputs=[{
                "name": "external_api",
                "namespace": "external",
                "schema": {"fields": ["id", "data"]}
            }],
            description="Data collection from unstable API"
        )

        # Simulate failure
        error_result = lineage_reporter.fail_job_run(
            job_name="data_collection_failed_api",
            error_message="API timeout after 30 seconds",
            run_id=run_id
        )

        assert error_result is True

        # Verify error event was properly formatted
        fail_event = lineage_reporter.client.emit.call_args_list[1][0][0]
        assert fail_event.eventType == "FAIL"
        assert fail_event.run.facets["errorMessage"]["message"] == "API timeout after 30 seconds"
        assert fail_event.run.facets["errorMessage"]["programmingLanguage"] == "PYTHON"

    def test_complex_nested_job_relationships(self, lineage_reporter):
        """Test complex job relationships with parent-child dependencies"""
        # Start parent job
        parent_run_id = lineage_reporter.start_job_run(
            job_name="parent_etl_workflow",
            job_type="BATCH",
            description="Master ETL workflow coordinating multiple child jobs"
        )

        # Start child job with parent relationship
        child_run_id = lineage_reporter.start_job_run(
            job_name="child_data_processing",
            job_type="BATCH",
            inputs=[{"name": "input_data", "namespace": "staging"}],
            description="Child data processing task",
            parent_run_id=parent_run_id
        )

        # Complete child job
        lineage_reporter.complete_job_run(
            job_name="child_data_processing",
            outputs=[{"name": "processed_data", "namespace": "production"}],
            run_id=child_run_id
        )

        # Complete parent job
        lineage_reporter.complete_job_run(
            job_name="parent_etl_workflow",
            outputs=[{"name": "final_results", "namespace": "production"}],
            run_id=parent_run_id
        )

        # Verify parent-child relationship
        child_start_event = lineage_reporter.client.emit.call_args_list[1][0][0]
        assert "parent" in child_start_event.run.facets
        assert child_start_event.run.facets["parent"]["runId"] == parent_run_id

        # Verify all jobs completed successfully
        assert len(lineage_reporter._active_runs) == 0

    def test_dataset_schema_propagation(self, lineage_reporter):
        """Test that dataset schemas are properly propagated through lineage"""
        input_schema = {
            "fields": [
                {"name": "id", "type": "INTEGER", "description": "Primary key"},
                {"name": "match_data", "type": "JSONB", "description": "Match information"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Creation timestamp"}
            ]
        }

        run_id = lineage_reporter.start_job_run(
            job_name="schema_propagation_test",
            inputs=[{
                "name": "source_table",
                "namespace": "bronze",
                "schema": input_schema
            }],
            outputs=[{
                "name": "target_table",
                "namespace": "silver",
                "schema": input_schema  # Same schema
            }]
        )

        lineage_reporter.complete_job_run(
            job_name="schema_propagation_test",
            run_id=run_id
        )

        # Verify schema was included in both input and output datasets
        start_event = lineage_reporter.client.emit.call_args_list[0][0][0]
        complete_event = lineage_reporter.client.emit.call_args_list[1][0][0]

        assert "schema" in start_event.inputs[0].facets
        assert "schema" in complete_event.outputs[0].facets


if __name__ == "__main__":
    pytest.main([__file__, "-v"])