# Repository Guidelines

## Project Structure & Module Organization
Primary code lives in `src/`: `api` exposes FastAPI routers, `models` defines SQLAlchemy entities, `services` and `tasks` host domain logic and schedulers, `utils` shares helpers, and `config` stores defaults. Tests mirror this layout under `tests/unit`, `tests/integration`, and `tests/e2e`. Documentation and playbooks reside in `docs/`, while automation scripts stay in `scripts/`. Containerization assets include the root `Dockerfile`, `docker-compose.yml`, and environment templates in `config/`.

## Build, Test, and Development Commands
`make venv` provisions the Python 3.11 virtualenv and `make install` syncs dependencies. Run `make context` whenever AI tooling or metadata updates are needed. `make lint` runs Black, isort, Ruff, and mypy; keep the tree clean before committing. `make test` executes pytest, while `make ci` or `./ci-verify.sh` reproduces the full GitHub Actions pipeline. Use `make coverage` for an HTML report, and `docker-compose up --build` to validate the full service stack locally.

## Coding Style & Naming Conventions
Adhere to PEP 8 with four-space indents and an 88-character limit. Let Black and isort format code automatically; do not hand-tune their output. Modules and functions use `lower_snake_case`, classes use `PascalCase`, and async tasks should read as `verb_noun`. Keep functions and endpoints fully type-annotated and resolve lint warnings instead of suppressing them.

## Testing Guidelines
Pytest discovers `test_*.py` and `*_test.py`; mirror source packages for clarity. Use markers declared in `pytest.ini` (`unit`, `integration`, `e2e`, `smoke`, etc.) to scope targeted runs. Maintain ≥80% coverage (CI enforces via `--cov=src --cov-fail-under`); regenerate reports with `pytest --cov=src --cov-report=term-missing`. Inspect `--durations=10` output to catch slow tests before merging.

## Commit & Pull Request Guidelines
Follow commit subjects patterned after Conventional Commits (`feat:`, `fix:`, `docs:`) observed in history and keep the imperative mood under 72 characters. Squash noisy WIP commits before review. PRs should state the problem, summarize the solution, list validation commands, and link issues or Kanban tickets. Include screenshots or API samples when user-facing behavior changes, request at least one reviewer, and wait for green CI before merging.

## Environment & Tooling Checklist
Run `make env-check` on new machines and keep secrets in ignored `.env` files. Inspect app logs in `logs/` and ML artifacts under `mlruns/` when debugging. Clean stale Docker volumes (`docker volume prune`) if migrations drift, and avoid committing generated coverage or context artifacts.
