# Repository Guidelines

## Project Structure & Module Organization
Runtime code lives in `src/`: FastAPI routers in `src/api`, domain logic in `src/core`, orchestration flows in `src/services` and `src/tasks`, persistence adapters in `src/database`, and shared helpers in `src/utils`. Test suites mirror this layout under `tests/unit`, `tests/integration`, `tests/slow`, and `tests/e2e`; reusable datasets sit in `tests/fixtures`, `data/`, and `models/`. Operational docs and runbooks belong in `docs/`, while automation lives in `scripts/`.

## Build, Test, and Development Commands
- `make venv && make install` — create the local `.venv` and install runtime + dev dependencies.
- `make fmt` — apply Black and isort formatting across Python sources.
- `make lint` — run flake8 and mypy with project type stubs.
- `make test` — execute the full pytest matrix; emits coverage to `coverage.xml` and terminal.
- `make coverage-fast` — run time-boxed unit suites for fast feedback.
- `make coverage` — enforce the ≥80% line coverage gate and write `coverage.txt`.

## Coding Style & Naming Conventions
Use four-space indentation and keep lines ≤88 characters. Modules, functions, and variables use `snake_case`; classes use `PascalCase`; constants use `UPPER_SNAKE_CASE`. Exported APIs, services, tasks, and Pydantic models require type hints plus docstrings aligned with FastAPI responses. Prefer explicit relative imports and keep configuration code scoped to `config/` modules.

## Testing Guidelines
Name files `test_*.py` and decorate suites with `@pytest.mark.unit`, `.integration`, `.slow`, or `.e2e` as appropriate. Reproduce regressions with targeted tests under the matching directory. Use shared fixtures from `tests/fixtures` and snapshot data from `data/`. Review `coverage.txt` or `coverage.xml` after `make coverage` to track drift, and investigate failures recorded in `reports/`.

## Commit & Pull Request Guidelines
Follow Conventional Commits (e.g., `feat: add win probability api`) with subjects ≤72 characters. Document executed verification commands in the body and link tickets in the footer using `Refs: FP-123`. Pull requests should describe intent, note schema or deployment impacts, attach relevant logs or screenshots, and confirm lint/test commands run locally.

## Security & Configuration Tips
Base local configuration on `env.template` or `env.example`; never commit secrets. When adding services, update `docker-compose*.yml` and related reverse-proxy rules under `nginx/`. After dependency changes, run `make lint` and inspect security artefacts in `reports/` or `security_report*.json` before merging.
