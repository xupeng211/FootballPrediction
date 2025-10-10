# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `src/`, grouped by capability (FastAPI routes in `api`, domain logic in `core`/`domain`, data contracts in `models`, orchestration in `services`, background tasks in `scheduler` and `streaming`). Shared helpers sit in `src/utils` and `src/common`. Tests mirror the runtime layout in `tests/` (unit, integration, e2e, plus fixtures and factories). Documentation stays in `docs/`, automation in `scripts/`, and dependency specs in `requirements/`. Treat the root `Makefile`, `docker-compose*.yml`, and `pyproject.toml` as the canonical toolchain definition.

## Build, Test, and Development Commands
Provision once with `make venv && make install`, then run `make context` to load project metadata. Day-to-day rely on `make lint`, `make fmt`, `make test`, and `make coverage`. `make ci` mirrors GitHub Actions, and `./ci-verify.sh` or `docker-compose up --build` rehearse production-like validation whenever infrastructure changes.

## Coding Style & Naming Conventions
- Target Python 3.11 with 4-space indentation and snake_case modules, functions, and variables; keep classes in PascalCase.
- Enforce formatting with Ruff (`make fmt`) using an 88-character limit and automated import cleanups—avoid manual tweaks.
- Static checks rely on Ruff lint plus mypy (`make lint`); keep type hints current and prefer explicit return types for public APIs.
- Store configuration constants under `config/` or dedicated settings modules instead of hard-coded literals.

## Testing Guidelines
Pytest discovers `test_*.py` and `*_test.py` inside `tests/unit`, `tests/integration`, and `tests/e2e`; place reusable fixtures in `tests/fixtures`. Always launch suites through Make targets (`make test`, `make test-phase1`, or `make coverage`) so defaults like `--cov=src`, `--strict-markers`, and `--maxfail=5` stay active. Tag slow or external checks with existing markers (`slow`, `integration`, `performance`, etc.), and hold coverage at ≥80%, reviewing `htmlcov/index.html` when regressions appear.

## Commit & Pull Request Guidelines
Follow the Conventional Commit verbs in history (`feat:`, `fix:`, `test:`, etc.) and keep each commit focused. Reuse `.github/PULL_REQUEST_TEMPLATE.md`: summarize the change, list module-level updates, note migration steps when imports move, and include proof of `make ci` (or equivalent) succeeding. Link the relevant issue or kanban card, and attach screenshots or logs when you alter user flows or operational dashboards.

## Environment & Security Notes
Copy `.env.example` to `.env` and run `make check-env` before bootstrapping services; never commit secrets. Use `make verify-deps` or `make smart-deps` after adjusting requirements to keep the lock files accurate. For security-sensitive work, consult the `security/` playbooks and, when isolating stateful dependencies, run the Make targets inside containers via `docker-compose.test.yml`.
