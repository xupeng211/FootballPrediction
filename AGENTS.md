# Repository Guidelines

## Project Structure & Module Organization
Source lives in `src/` with routers in `src/api`, persistence in `src/models`, business logic in `src/services`, recurring jobs in `src/tasks`, helpers in `src/utils`, and defaults in `src/config`. Tests mirror this layout under `tests/unit`, `tests/integration`, and `tests/e2e`; specialized suites sit in `tests/performance` and `tests/mutation`. Place fixtures beside the scope they support, and keep operational assets in `docs/`, `scripts/`, `config/`, `security/`, and Docker files plus the `Makefile` at the root.

## Build, Test, and Development Commands
Run `make venv && make install` to create the Python 3.11 env using `requirements/requirements.lock`. Use `make lint` for flake8 and mypy, and `make fmt` to apply Black and isort. Execute `make test`, `make test.unit`, `make test.int`, or `make test.e2e` to drive pytest suites; `make coverage` enforces the 80% threshold. Before PRs, run `make ci` or `./ci-verify.sh`, and use `docker-compose up --build` to launch the full stack.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation and 88-character lines. Use `lower_snake_case` for modules, functions, and variables, `PascalCase` for classes, and verb-led names like `fetch_fixtures` for async tasks. Rely on Black, isort, Ruff, and flake8; never merge unformatted changes.

## Testing Guidelines
Pytest discovers `test_*.py` and `*_test.py`; align test directories with their source counterparts. Respect markers from `pytest.ini` (`unit`, `integration`, `e2e`, `smoke`, `slow`, `performance`, `security`, `api`, `database`, `cache`). Maintain coverage above 80%, review `--durations=10`, and regenerate reports with `make coverage`.

## Commit & Pull Request Guidelines
Use Conventional Commit subjects (e.g., `feat: add match ingest task`) under 72 characters. PRs should describe the problem, summarize the solution, list validation commands run, link tickets, and attach artefacts like screenshots or payload samples for user-facing changes. Wait for green CI and at least one reviewer approval before merging.

## Security & Configuration Tips
Copy `.env.example` to `.env`, then run `make check-env` and `make env-check` before first boot. Keep secrets out of Git, monitor `logs/` for runtime diagnostics, and prune stale Docker volumes with `docker volume prune`. Refresh tooling metadata with `make context` when dependencies change.
