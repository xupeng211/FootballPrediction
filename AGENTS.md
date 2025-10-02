# Repository Guidelines

## Project Structure & Module Organization
Application code lives in `src/`, mapping routers to `src/api`, domain rules to `src/core`, service orchestration to `src/services`, background jobs to `src/tasks`, persistence adapters to `src/database`, and shared helpers to `src/utils`. Configuration defaults stay in `config/`; keep `.env` variants aligned with `env.template` and `env.example`. Tests mirror the runtime tree (`tests/unit`, `tests/integration`, `tests/e2e`, `tests/monitoring`), reusing fixtures from `tests/fixtures` and datasets staged in `data/`. Generated models and experiment artifacts belong in `models/` or `data/`; automation stays in `scripts/`; long-form references go to `docs/`.

## Build, Test, and Development Commands
Run `make venv && make install` once to bootstrap the Python 3.10 toolchain inside `.venv`. Use `make fmt` for Black + isort, `make lint` for flake8 and mypy, and `make test` for the full pytest suite. Coverage gates run via `make coverage` (enforces ≥80%) or `make coverage-fast` for unit-only iterations. `make context` summarizes the service topology before large refactors. For CI parity, launch services with `docker-compose -f docker-compose.test.yml up --build`.

## Coding Style & Naming Conventions
Follow four-space indentation, 88-character line wraps, and explicit imports. Use snake_case for modules and functions, PascalCase for classes, and UPPER_SNAKE_CASE for constants. Public APIs, services, and tasks must expose type hints and docstrings; align Pydantic schemas in `src/api` with published responses. Configuration toggles live in `config/` modules—never hard-code secrets.

## Testing Guidelines
Pytest drives the suite; mark scope with `@pytest.mark.unit`, `.integration`, or `.e2e`. Keep tests in `tests/*/test_*.py`, leaning on fixtures from `tests/fixtures`. When coverage dips, add regression cases and rerun `make coverage`. Prefer deterministic datasets stored in `data/`.

## Commit & Pull Request Guidelines
Adopt Conventional Commit prefixes (`feat:`, `fix:`, `chore:`) with subjects ≤72 characters and optional command notes in the body. Reference tickets using `Refs: FP-123`. Before pushing, run `make lint` and `make test`; attach outputs or screenshots in PR descriptions, list verification steps, and flag schema, monitoring, or deployment impacts.

## Security & Configuration Tips
Base local secrets on `env.template` and `env.example`, injecting them via tooling or runtime variables. Review `docker-compose*.yml` and reverse-proxy rules before exposing new ports. After dependency upgrades, rerun `make lint` and inspect `reports/security_report*.json` for regressions.
