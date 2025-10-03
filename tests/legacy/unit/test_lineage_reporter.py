from datetime import datetime

from src.lineage.lineage_reporter import LineageReporter, lineage_reporter
from unittest.mock import Mock
import pytest
import os

"""
Test suite for lineage reporter module
"""

@pytest.fixture
def lineage_reporter_instance():
    """Create a lineage reporter instance for testing"""
    return LineageReporter(marquez_url = os.getenv("TEST_LINEAGE_REPORTER_MARQUEZ_URL_14"))": def test_lineage_reporter_initialization():"""
    "]""Test initialization of LineageReporter"""
    reporter = LineageReporter()
    assert reporter is not None
    assert reporter.namespace =="football_prediction[" assert hasattr(reporter, "]_active_runs[")" assert reporter._active_runs =={}"""
def test_start_job_run(lineage_reporter_instance):
    "]""Test starting a job run"""
    # Mock the OpenLineageClient
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    # Mock emit method
    mock_client.emit = Mock()
    run_id = lineage_reporter_instance.start_job_run(job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_26"),": job_type = os.getenv("TEST_LINEAGE_REPORTER_JOB_TYPE_26"),": inputs = [{"]name[: "input_dataset"", "namespace])],": description = os.getenv("TEST_LINEAGE_REPORTER_DESCRIPTION_26"),": source_location = os.getenv("TEST_LINEAGE_REPORTER_SOURCE_LOCATION_26"),": transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_TRANSFORMATION_SQL_26"))""""
    # Verify that run_id was returned and stored
    assert run_id is not None
    assert "]test_job[" in lineage_reporter_instance._active_runs[""""
    assert lineage_reporter_instance._active_runs["]]test_job["] ==run_id[""""
    # Verify emit was called
    mock_client.emit.assert_called_once()
def test_complete_job_run_with_run_id(lineage_reporter_instance):
    "]]""Test completing a job run with explicit run_id"""
    # Mock the OpenLineageClient
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    mock_client.emit = Mock()
    # Manually add a run to active runs
    test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_34"): lineage_reporter_instance._active_runs["]test_job["] = test_run_id[": result = lineage_reporter_instance.complete_job_run(job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_38"),": outputs = [{"]name[: "output_dataset"", "namespace]}],": metrics = {"records_processed[": 100),": run_id=test_run_id)"""
    # Verify emit was called
    mock_client.emit.assert_called_once()
    assert result is True
    # Verify the run was removed from active runs
    assert "]test_job[" not in lineage_reporter_instance._active_runs[""""
def test_complete_job_run_without_run_id(lineage_reporter_instance):
    "]]""Test completing a job run without explicit run_id (using active runs)"""
    # Mock the OpenLineageClient
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    mock_client.emit = Mock()
    # Manually add a run to active runs
    test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_46"): lineage_reporter_instance._active_runs["]test_job["] = test_run_id[": result = lineage_reporter_instance.complete_job_run(job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_38"),": outputs = [{"]name[: "output_dataset"", "namespace]}],": metrics = {"records_processed[": 100))""""
    # Verify emit was called
    mock_client.emit.assert_called_once()
    assert result is True
    # Verify the run was removed from active runs
    assert "]test_job[" not in lineage_reporter_instance._active_runs[""""
def test_complete_job_run_no_active_run(lineage_reporter_instance):
    "]]""Test completing a job run when no active run exists"""
    result = lineage_reporter_instance.complete_job_run(job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_56"),": outputs = [{"]name[: "output_dataset"", "namespace])])": assert result is False[" def test_fail_job_run_with_run_id(lineage_reporter_instance):""
    "]""Test failing a job run with explicit run_id"""
    # Mock the OpenLineageClient
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    mock_client.emit = Mock()
    # Manually add a run to active runs
    test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_61"): lineage_reporter_instance._active_runs["]test_job["] = test_run_id[": result = lineage_reporter_instance.fail_job_run(": job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_38"), error_message = os.getenv("TEST_LINEAGE_REPORTER_ERROR_MESSAGE_62"), run_id=test_run_id[""""
    )
    # Verify emit was called
    mock_client.emit.assert_called_once()
    assert result is True
    # Verify the run was removed from active runs
    assert "]]test_job[" not in lineage_reporter_instance._active_runs[""""
def test_fail_job_run_without_run_id(lineage_reporter_instance):
    "]]""Test failing a job run without explicit run_id (using active runs)"""
    # Mock the OpenLineageClient
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    mock_client.emit = Mock()
    # Manually add a run to active runs
    test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_72"): lineage_reporter_instance._active_runs["]test_job["] = test_run_id[": result = lineage_reporter_instance.fail_job_run(": job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_38"), error_message = os.getenv("TEST_LINEAGE_REPORTER_ERROR_MESSAGE_62")""""
    )
    # Verify emit was called
    mock_client.emit.assert_called_once()
    assert result is True
    # Verify the run was removed from active runs
    assert "]test_job[" not in lineage_reporter_instance._active_runs[""""
def test_fail_job_run_no_active_run(lineage_reporter_instance):
    "]]""Test failing a job run when no active run exists"""
    result = lineage_reporter_instance.fail_job_run(
        job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_56"), error_message = os.getenv("TEST_LINEAGE_REPORTER_ERROR_MESSAGE_62")""""
    )
    assert result is False
def test_report_data_collection(lineage_reporter_instance):
    "]""Test reporting data collection process"""
    # Mock the OpenLineageClient
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    mock_client.emit = Mock()
    run_id = lineage_reporter_instance.report_data_collection(
        source_name = os.getenv("TEST_LINEAGE_REPORTER_SOURCE_NAME_89"),": target_table = os.getenv("TEST_LINEAGE_REPORTER_TARGET_TABLE_90"),": records_collected=100,": collection_time=datetime.now(),": source_config = {"]schema[": [{"]name[": "]id[", "]type[": "]int["}]})""""
    # Verify that emit was called twice (start and complete events)
    assert mock_client.emit.call_count >= 1  # At least one emit call
    assert run_id is not None
def test_report_data_transformation(lineage_reporter_instance):
    "]""Test reporting data transformation process"""
    # Mock the OpenLineageClient
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    mock_client.emit = Mock()
    run_id = lineage_reporter_instance.report_data_transformation(
        source_tables=["table1[", "]table2["],": target_table = os.getenv("TEST_LINEAGE_REPORTER_TARGET_TABLE_102"),": transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_TRANSFORMATION_SQL_102"),": records_processed=50,": transformation_type = os.getenv("TEST_LINEAGE_REPORTER_TRANSFORMATION_TYPE_102"))""""
    # Verify that emit was called (start and complete events)
    assert mock_client.emit.call_count >= 1  # At least one emit call
    assert run_id is not None
def test_get_active_runs(lineage_reporter_instance):
    "]""Test getting active runs"""
    # Add a test run manually
    lineage_reporter_instance._active_runs["test_job["] = "]test_run_id[": active_runs = lineage_reporter_instance.get_active_runs()""""
    # Verify it returns a copy of the active runs
    assert "]test_job[" in active_runs[""""
    assert active_runs["]]test_job["] =="]test_run_id["""""
    # Modify the returned dict shouldn't affect internal state
    active_runs["]test_job["] = "]modified[": assert lineage_reporter_instance._active_runs["]test_job["] =="]test_run_id[" def test_clear_active_runs("
    """"
    "]""Test clearing active runs"""
    # Add some test runs
    lineage_reporter_instance._active_runs["test_job1["] = "]run1[": lineage_reporter_instance._active_runs["]test_job2["] = "]run2[": lineage_reporter_instance.clear_active_runs()""""
    # Verify all runs were cleared
    assert len(lineage_reporter_instance._active_runs) ==0
def test_global_instance():
    "]""Test that the global lineage reporter instance exists"""
    assert lineage_reporter is not None
    assert isinstance(lineage_reporter, LineageReporter)
def test_start_job_run_with_parent_run(lineage_reporter_instance):
    """Test starting a job run with parent run ID"""
    # Mock the OpenLineageClient
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    mock_client.emit = Mock()
    run_id = lineage_reporter_instance.start_job_run(
        job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_128"), parent_run_id = os.getenv("TEST_LINEAGE_REPORTER_PARENT_RUN_ID_129")""""
    )
    # Verify that run_id was returned and stored
    assert run_id is not None
    assert "]child_job[" in lineage_reporter_instance._active_runs[""""
def test_detect_exception_in_start_job_run(lineage_reporter_instance):
    "]]""Test exception handling in start_job_run"""
    # Mock the OpenLineageClient to raise an exception
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    mock_client.emit.side_effect = Exception("Client error[")": with pytest.raises(Exception, match = os.getenv("TEST_LINEAGE_REPORTER_MATCH_137"))": lineage_reporter_instance.start_job_run(job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_139"))": def test_detect_exception_in_complete_job_run(lineage_reporter_instance):"""
    "]""Test exception handling in complete_job_run"""
    # Mock the OpenLineageClient to raise an exception
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    mock_client.emit.side_effect = Exception("Client error[")""""
    # Add a run to active runs
    test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_147"): lineage_reporter_instance._active_runs["]test_job["] = test_run_id[": result = lineage_reporter_instance.complete_job_run(": job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_38"), run_id=test_run_id[""""
    )
    # Should return False due to exception
    assert result is False
    # Run should still be removed from active runs even with exception:
    assert "]]test_job[" not in lineage_reporter_instance._active_runs[""""
def test_detect_exception_in_fail_job_run(lineage_reporter_instance):
    "]]""Test exception handling in fail_job_run"""
    # Mock the OpenLineageClient to raise an exception
    mock_client = Mock()
    lineage_reporter_instance.client = mock_client
    mock_client.emit.side_effect = Exception("Client error[")""""
    # Add a run to active runs
    test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_147"): lineage_reporter_instance._active_runs["]test_job["] = test_run_id[": result = lineage_reporter_instance.fail_job_run(": job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_38"), error_message = os.getenv("TEST_LINEAGE_REPORTER_ERROR_MESSAGE_160"), run_id=test_run_id[""""
    )
    # Should return False due to exception
    assert result is False
    # Run should still be removed from active runs even with exception:
    assert "]]test_job" not in lineage_reporter_instance._active_runs