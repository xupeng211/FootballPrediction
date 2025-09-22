# Coverage Improvement Roadmap

## Baseline Snapshot (Week 0)
- Threshold raised to **55%** (`pytest.ini`), current unit suite reports **64.5%** after excluding helper scripts via `.coveragerc`.
- 1906 tests passing, 49 skipped, no flaky cases observed in the last run (`timeout 600 ./venv/bin/pytest tests/unit ...`).
- Primary gaps: long-tail services (`src/services/data_processing.py`, 57%), monitoring/quality modules (≤15%), streaming stack (≤37%).

## Board Structure (Kanban)
- **Backlog**: Modules below 50% coverage with no active owner.
- **In Progress**: Stories with active PRs or test design (link to branch when available).
- **Ready for Review**: Tests implemented, waiting on code review + coverage report snippet.
- **Done**: Merged and reflected in main; capture coverage delta in comments.
- Recommended labels: `coverage-phase-2`, `coverage-phase-3`, `coverage-phase-4`, plus module tags (e.g., `module:prediction-service`).

## Phase 2 – Raise to 60%
1. `src/models/prediction_service.py` – add tests for caching, metrics, batch prediction, negative mlflow paths (reuse `mock_mlflow_client`, `mock_db_manager`).
2. `src/services/data_processing.py` – isolate pure transformation helpers; write table-driven tests with synthetic Pandas DataFrames.
3. `src/tasks/data_collection_tasks.py` – cover Celery retry, logging, and metrics paths using `AsyncMock`.
- Exit criteria: green CI with `--cov-fail-under=60`, coverage ≥61%.

## Phase 3 – Raise to 65%
1. `src/data/quality/anomaly_detector.py` – scenario tests (normal, outlier, empty sets) with fixture DataFrames.
2. `src/monitoring/quality_monitor.py` & `src/tasks/monitoring.py` – validate metric emission, error handling via patched exporters.
3. Extend regression tests for fallback behaviour in `prediction_service` (e.g., stale cache, feature store failure).
- Exit criteria: sustained coverage ≥66%, board items for monitoring closed.

## Phase 4 – Raise to 70%
1. `src/streaming/kafka_consumer.py` + `src/streaming/stream_processor.py` – contract tests using mocked Kafka clients and sample payloads.
2. `src/data/storage/data_lake_storage.py` – use `tmp_path`/`pyfakefs` to cover partition writes, recovery flows.
3. `src/tasks/streaming_tasks.py` – verify orchestrations and retry policies with patched brokers.
- Exit criteria: coverage ≥71%, CI updated to `--cov-fail-under=70`, documentation of streaming coverage in PR summary.

## Operating Cadence
- Weekly stand-up checklist: review open coverage tickets, inspect slowest failing tests, confirm CI threshold.
- PR template addition: include `pytest --cov=src` summary and affected modules.
- Dashboard idea: export `coverage.json` diff to the board once per week; flag any file dipping below 50%.

## Assistance Needed
- Provide access or link to the team's issue tracker so board columns can be mirrored there.
- Confirm availability of `pyfakefs` or approve adding it to `requirements-dev.txt` for Phase 4 filesystem tests.
