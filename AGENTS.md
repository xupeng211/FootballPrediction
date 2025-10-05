# Repository Guidelines

## Project Structure & Module Organization
Source lives in `src/` with key domains split by responsibility: routers under `src/api`, persistence in `src/models`, business logic in `src/services`, scheduled jobs in `src/tasks`, helpers in `src/utils`, and startup defaults in `src/config`. Tests mirror this layout inside `tests/unit`, `tests/integration`, and `tests/e2e`, while specialized suites sit in `tests/performance` and `tests/mutation`. Place fixtures beside the code they support, and keep operational assets under `docs/`, `scripts/`, `config/`, `security/`, and Docker files with the root `Makefile`.

## Build, Test, and Development Commands
Run `make venv && make install` to bootstrap the Python 3.11 virtualenv from `requirements/requirements.lock`. Use `make fmt` to apply Black and isort, and `make lint` to run flake8 and mypy. Execute `make test`, `make test.unit`, `make test.int`, or `make test.e2e` for the respective pytest suites; `make coverage` enforces the 80% threshold. Before merging, run `make ci` or `./ci-verify.sh`, and use `docker-compose up --build` to launch the full stack locally.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation and 88-character lines. Keep modules, functions, and variables in `lower_snake_case`, classes in `PascalCase`, and prefer verb-led async names (e.g., `fetch_fixtures`). Always format code with Black and isort, and address lint feedback from flake8, mypy, and Ruff before committing.

## Testing Guidelines
Pytest auto-discovers `test_*.py` and `*_test.py`; align test directories with their source counterparts and respect markers defined in `pytest.ini` such as `unit`, `integration`, `e2e`, `smoke`, and `slow`. Maintain project coverage above 80%; review slow tests via `pytest --durations=10`. Generate reports with `make coverage` and capture any new fixtures alongside the modules they exercise.

## Commit & Pull Request Guidelines
Write Conventional Commit subjects under 72 characters (e.g., `feat: add match ingest task`). Pull requests should restate the problem, outline the fix, list validation commands (tests, lint), link relevant tickets, and attach artefacts (logs, payloads, screenshots) for user-facing changes. Wait for green CI and at least one reviewer approval before merging.

## Security & Configuration Tips
Copy `.env.example` to `.env`, then run `make check-env` and `make env-check` before first boot. Keep secrets out of Git, monitor `logs/` for runtime diagnostics, prune stale volumes with `docker volume prune`, and refresh tooling metadata with `make context` whenever dependencies change.
