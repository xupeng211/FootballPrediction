# Repository Guidelines

## Project Structure & Module Organization
- Domain code lives in `src/`: routers in `src/api`, persistence in `src/models`, business rules in `src/services`, schedulers in `src/tasks`, helpers in `src/utils`, defaults in `src/config`.
- Tests mirror the tree (`tests/unit`, `tests/integration`, `tests/e2e`) and extend to `tests/performance` and `tests/mutation`; keep fixtures alongside their scope.
- Operational assets stay outside code: `docs/` for runbooks, `scripts/` for automation, `config/` for environment templates, `security/` for audits. Docker files and the Makefile sit at the repository root.

## Build, Test, and Development Commands
- `make venv && make install` bootstrap the Python 3.11 virtualenv with `requirements/requirements.lock`.
- `make lint` runs flake8 and mypy; follow with `make fmt` for Black and isort.
- `make test` drives pytest with verbose output; target suites via `make test.unit`, `make test.int`, or `make test.e2e`.
- `make coverage` enforces the 80% threshold, while `make ci` or `./ci-verify.sh` run the full gate. `docker-compose up --build` starts the local stack for end-to-end checks.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indents and 88-character lines. Black, isort, Ruff, and flake8 are configured in `pyproject.toml` and the Make targets.
- Prefer `lower_snake_case` for modules, functions, and variables, `PascalCase` for classes, and verb-first names for async tasks (e.g., `fetch_fixtures`).
- Keep files ASCII unless legacy code requires Unicode; add concise comments only when behavior is non-obvious.

## Testing Guidelines
- Pytest discovers `test_*.py` and `*_test.py`; mirror the source layout for fixtures and helpers.
- Respect markers from `pytest.ini` (unit, integration, e2e, smoke, slow, performance, security, api, database, cache) to filter runs.
- Maintain ≥80% coverage; inspect `--durations=10` output for hotspots and regenerate HTML reports in `htmlcov/` with `make coverage`.

## Commit & Pull Request Guidelines
- Use Conventional Commit subjects such as `feat: add match ingest task` or `fix: handle missing odds`, keeping them under 72 characters.
- Pull requests should explain the problem, summarize the solution, list validation commands, link tickets, and attach screenshots or API payloads for user-visible changes.
- Wait for green CI and secure at least one reviewer approval before merging.

## Security & Configuration Tips
- Copy `.env.example` to `.env`, then run `make check-env` and `make env-check` before first boot.
- Store secrets outside Git; inspect runtime logs in `logs/` and ML artifacts in `mlruns/`.
- Use `docker volume prune` if database state drifts and refresh tooling context with `make context`.
