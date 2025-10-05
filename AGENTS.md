# Repository Guidelines

## Project Structure & Module Organization
Source lives in `src/` with routers in `src/api`, persistence in `src/models`, business logic in `src/services`, recurring jobs in `src/tasks`, helpers in `src/utils`, and defaults in `src/config`. Tests mirror this tree under `tests/unit`, `tests/integration`, `tests/e2e`, with `tests/performance` and `tests/mutation` for specialized suites; place fixtures beside the scope they support. Operational assets stay outside code: runbooks in `docs/`, automation in `scripts/`, environment templates in `config/`, audits in `security/`, and Docker files plus `Makefile` at the project root.

## Build, Test, and Development Commands
Run `make venv && make install` to bootstrap the Python 3.11 virtualenv from `requirements/requirements.lock`. Use `make lint` for flake8 and mypy, followed by `make fmt` to apply Black and isort. `make test`, `make test.unit`, `make test.int`, and `make test.e2e` drive pytest suites; `make coverage` enforces the 80% threshold. Run `make ci` or `./ci-verify.sh` before opening a pull request, and `docker-compose up --build` to start the full stack.

## Coding Style & Naming Conventions
Adhere to PEP 8 with four-space indentation and 88-character lines. Use `lower_snake_case` for modules, functions, and variables, `PascalCase` for classes, and verb-led names for async tasks such as `fetch_fixtures`. Let Black, isort, Ruff, and flake8 format and lint the codebase; never merge unformatted changes.

## Testing Guidelines
Pytest discovers `test_*.py` and `*_test.py`; align test directories with their source counterparts. Respect markers defined in `pytest.ini` (`unit`, `integration`, `e2e`, `smoke`, `slow`, `performance`, `security`, `api`, `database`, `cache`) when selecting suites. Maintain coverage above 80%, inspect `--durations=10` output for hotspots, and regenerate reports with `make coverage`.

## Commit & Pull Request Guidelines
Use Conventional Commit subjects (e.g., `feat: add match ingest task`), keeping them under 72 characters. Pull requests should describe the problem, summarize the solution, list validation commands run, link tickets, and attach screenshots or payload samples for user-facing changes. Wait for green CI and at least one reviewer approval before merging.

## Security & Configuration Tips
Copy `.env.example` to `.env`, then run `make check-env` and `make env-check` before first boot. Keep secrets out of Git, monitor `logs/` for runtime diagnostics, and prune local Docker volumes with `docker volume prune` if the database state drifts. Refresh tooling context with `make context` when dependencies change.
