# Repository Guidelines

## Project Structure & Module Organization
- Core runtime lives in `src/`, segmented by capability: `api/` for FastAPI routes, `core/` plus `domain/` for business rules, `models/` for data contracts, `services/` for orchestrators, and background workers under `scheduler/` and `streaming/`.
- Shared helpers stay in `src/utils` and `src/common`. Configuration modules reside in `config/` and `configs/` to keep literals out of runtime code.
- Tests mirror production layout inside `tests/` (`unit`, `integration`, `e2e`) with fixtures in `tests/fixtures`. Docs sit under `docs/`, automation under `scripts/`, and dependency specs in `requirements/`.
- Treat the root `Makefile`, `docker-compose*.yml`, and `pyproject.toml` as authoritative for tooling and dependency versions.

## Build, Test, and Development Commands
- `make venv && make install`: create the virtualenv and install project dependencies.
- `make context`: load project metadata (paths, env defaults) into the shell.
- `make fmt`: run Ruff formatting and import tidying; rely on it before committing.
- `make lint`: execute Ruff lint plus mypy for static checks.
- `make test` or `make coverage`: run pytest with coverage flags; CI uses the same defaults through `make ci`.
- `./ci-verify.sh` or `docker-compose up --build`: rehearse production-style verification when infrastructure changes.

## Coding Style & Naming Conventions
- Python 3.11, 4-space indentation, 88-character lines. Modules, functions, and variables use `snake_case`; classes use `PascalCase`.
- Keep public APIs explicitly typed. Prefer dependency injection over singletons.
- Store secrets in `.env`, not code; load via settings modules inside `config/`.

## Testing Guidelines
- Pytest discovers `test_*.py` and `*_test.py`. Co-locate mocks and fixtures in `tests/fixtures` to avoid duplication.
- Maintain ≥80% coverage; inspect `htmlcov/index.html` after significant changes.
- Tag slow or external suites with `@pytest.mark.slow` or `@pytest.mark.integration` so CI gating remains predictable.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat:`, `fix:`, `test:`, etc.); keep commits scoped and runnable.
- Reference `.github/PULL_REQUEST_TEMPLATE.md` when opening a PR. Include summary, module-level notes, linked issues or kanban cards, and proof of `make ci` (or equivalent) passing.
- Attach relevant logs or screenshots when altering user-visible flows or operations dashboards.

## Security & Configuration Tips
- Copy `.env.example` to `.env`, then run `make check-env` before starting services.
- After touching dependencies, run `make verify-deps` or `make smart-deps` to sync lock files.
- For stateful or sensitive tasks, prefer containerized runs (`docker-compose.test.yml`) and consult `security/` playbooks before production changes.
