from datetime import datetime

import pytest

from src.lineage import lineage_reporter as lineage_module


class DummyClient:
    def __init__(self, url):
        self.url = url
        self.events = []

    def emit(self, event):
        self.events.append(event)


class DummyEvent:
    def __init__(self, **payload):
        self.payload = payload
        self.eventType = payload.get("eventType")
        self.run = payload.get("run")
        self.job = payload.get("job")
        self.inputs = payload.get("inputs")
        self.outputs = payload.get("outputs")


class DummyDataset:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class DummyJob:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.name = kwargs.get("name")


class DummyRun:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.runId = kwargs.get("runId")


@pytest.fixture(autouse=True)
def patch_openlineage(monkeypatch):
    monkeypatch.setattr(lineage_module, "OpenLineageClient", DummyClient)
    monkeypatch.setattr(lineage_module, "RunEvent", DummyEvent)
    monkeypatch.setattr(lineage_module, "InputDataset", DummyDataset)
    monkeypatch.setattr(lineage_module, "OutputDataset", DummyDataset)
    monkeypatch.setattr(lineage_module, "Run", DummyRun)
    monkeypatch.setattr(lineage_module, "Job", DummyJob)
    monkeypatch.setattr(
        lineage_module, "schema_dataset", lambda schema: {"schema": schema}
    )
    monkeypatch.setattr(
        lineage_module, "source_code_location_job", lambda payload: payload
    )
    monkeypatch.setattr(lineage_module, "sql_job", lambda sql: {"query": sql})
    monkeypatch.setattr(lineage_module, "parent_run", lambda payload: payload)
    monkeypatch.setattr(
        lineage_module, "error_message_run", lambda payload: {"error": payload}
    )
    reporter = lineage_module.LineageReporter(marquez_url="http://test")
    monkeypatch.setattr(lineage_module, "lineage_reporter", reporter)
    yield
    reporter.clear_active_runs()


def test_start_job_run_tracks_active_run():
    reporter = lineage_module.lineage_reporter
    run_id = reporter.start_job_run(job_name="unit_test_job", description="demo")

    assert reporter._active_runs["unit_test_job"] == run_id
    emitted = reporter.client.events[-1]
    assert emitted.eventType == "START"
    assert emitted.job.kwargs["name"] == "unit_test_job"


def test_complete_job_run_uses_active_run(monkeypatch):
    reporter = lineage_module.lineage_reporter
    run_id = reporter.start_job_run(job_name="finish_job")
    success = reporter.complete_job_run(
        job_name="finish_job",
        outputs=[{"name": "table", "schema": {"fields": []}}],
        metrics={"rows": 10},
    )
    assert success is True
    emitted = reporter.client.events[-1]
    assert emitted.eventType == "COMPLETE"
    assert emitted.outputs[0].kwargs["name"] == "table"
    assert emitted.run.runId == run_id


def test_complete_job_run_returns_false_when_missing():
    reporter = lineage_module.lineage_reporter
    reporter.clear_active_runs()
    assert reporter.complete_job_run("missing") is False


def test_fail_job_run_removes_active():
    reporter = lineage_module.lineage_reporter
    run_id = reporter.start_job_run("failing_job")
    success = reporter.fail_job_run("failing_job", "boom", run_id=run_id)
    assert success is True
    assert "failing_job" not in reporter.get_active_runs()
    emitted = reporter.client.events[-1]
    assert emitted.eventType == "FAIL"
    assert emitted.run.runId == run_id


def test_report_data_collection_calls_start_and_complete(monkeypatch):
    reporter = lineage_module.lineage_reporter
    run_id = reporter.report_data_collection(
        source_name="api",
        target_table="raw_matches",
        records_collected=42,
        collection_time=datetime.utcnow(),
        source_config={"schema": {"fields": []}},
    )
    events = reporter.client.events[-2:]
    assert events[0].eventType == "START"
    assert events[1].eventType == "COMPLETE"
    assert run_id == events[0].run.runId


def test_report_data_transformation_builds_sql_facet():
    reporter = lineage_module.lineage_reporter
    run_id = reporter.report_data_transformation(
        source_tables=["bronze_fixtures"],
        target_table="silver_fixtures",
        transformation_sql="SELECT * FROM bronze_fixtures",
        records_processed=123,
        transformation_type="ETL",
    )
    events = reporter.client.events[-2:]
    assert events[0].eventType == "START"
    assert events[0].job.kwargs["facets"]["sql"]["query"].startswith("SELECT")
    assert events[1].eventType == "COMPLETE"
    assert run_id == events[0].run.runId


def test_get_and_clear_active_runs():
    reporter = lineage_module.lineage_reporter
    reporter.start_job_run(job_name="tmp")
    assert reporter.get_active_runs()
    reporter.clear_active_runs()
    assert reporter.get_active_runs() == {}
