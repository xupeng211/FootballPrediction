# Repository Guidelines

## Project Structure & Module Organization
- `src/` hosts domain code: `api` for FastAPI routers, `models` for SQLAlchemy entities, `services` and `tasks` for business logic and schedulers, `utils` for shared helpers, and `config` for defaults.
- Tests mirror the source tree in `tests/unit`, `tests/integration`, and `tests/e2e`; add fixtures under the matching directory to keep scope clear.
- Operational assets live in `docs/` for playbooks, `scripts/` for automation, and `config/` for environment templates. Container files (`Dockerfile`, `docker-compose.yml`) stay at the repository root.

## Build, Test, and Development Commands
- `make venv` and `make install` bootstrap the Python 3.11 environment and sync dependencies.
- `make lint` runs Black, isort, Ruff, and mypy; resolve findings instead of suppressing them.
- `make test` executes pytest suites; use `make coverage` for an HTML report, and `make ci` or `./ci-verify.sh` to mirror the full pipeline.
- `docker-compose up --build` spins up the service stack for end-to-end validation.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indents and an 88-character limit; allow Black and isort to handle formatting.
- Use `lower_snake_case` for modules and functions, `PascalCase` for classes, and verb-first names for async tasks (e.g., `fetch_fixtures`).
- Keep files ASCII unless existing code requires otherwise; document nonobvious logic with concise comments.

## Testing Guidelines
- Pytest auto-discovers `test_*.py`/`*_test.py`; mirror source packages to maintain traceability.
- Enforce ≥80% coverage (`pytest --cov=src --cov-report=term-missing`); inspect `--durations=10` output for hotspots.
- Apply markers from `pytest.ini` (`unit`, `integration`, `e2e`, `smoke`) to target suites during local runs.

## Commit & Pull Request Guidelines
- Use Conventional Commit subjects (`feat:`, `fix:`, `docs:`) in imperative mood under 72 characters.
- PRs should describe the problem, solution, and validation commands; link issues or Kanban tickets and attach screenshots or API samples for user-facing changes.
- Wait for green CI before merge and request at least one reviewer.

## Security & Configuration Tips
- Keep secrets in ignored `.env` files and refresh context artifacts with `make context` when tooling changes.
- Run `make env-check` on new machines; clean stale Docker volumes with `docker volume prune` if migrations drift.
- Inspect runtime logs under `logs/` and ML artifacts in `mlruns/` when troubleshooting.
