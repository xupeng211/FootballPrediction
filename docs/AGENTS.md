# Repository Guidelines

This FastAPI service powers football prediction workflows. Use this guide to navigate the repo, follow the engineering conventions, and land changes that ship smoothly.

## Project Structure & Module Organization
- `src/` contains runtime code: `api/` routers, `services/` orchestration, `models/` domain types, `features/` ML pipelines, and `core/` settings/constants.
- `tests/` mirrors production layers via `unit/`, `integration/`, and `e2e/`; legacy suites live under `tests/legacy/` and stay opt-in.
- `config/` houses env templates and pytest/coverage profiles; start from `config/envs/env.template` when provisioning.
- `docs/` records process playbooks—consult `docs/INDEX.md` before adding or moving material.
- Automation and analytics assets live in `scripts/`, `reports/`, and `mlflow/` (alongside tracked experiment metadata).

## Build, Test, and Development Commands
- `make context` primes AI tooling with repository metadata each session.
- `make venv` or `make install` prepare dependencies; rerun after editing `pyproject.toml` or requirements files.
- `make fmt` applies black and isort; `make lint` runs ruff, flake8, mypy, and safety.
- `make test` executes the standard pytest suite; `make coverage` enforces the ≥80% threshold.
- `./ci-verify.sh` reproduces the full CI pipeline, including docker-compose orchestration.

## Coding Style & Naming Conventions
- Format Python with black’s 88-character width and 4-space indents; keep imports ordered via isort (black profile).
- Favor type hints, dataclasses, and snake_case module names; align FastAPI endpoints with descriptive handler names.
- Store configuration defaults in `src/core`, and expose environment keys in ALL_CAPS.

## Testing Guidelines
- Use pytest markers (`unit`, `integration`, `e2e`, `slow`) defined in `pyproject.toml`; e.g., `pytest -m "unit and not slow"` for fast checks.
- Maintain ≥80% CI coverage (`make coverage-ci`); local iterations can target `coverage-local` (≥60%) but raise before merge.
- Centralize fixtures in `tests/conftest.py`; place reusable datasets under `tests/data/`.

## Commit & Pull Request Guidelines
- Follow conventional commits (`fix(tests):`, `refactor(api):`, etc.); keep subject lines imperative and concise.
- Document PR intent, list executed checks (`make lint`, `make test`, `./ci-verify.sh`), and link the relevant issue or Kanban card.
- Provide screenshots or logs for non-obvious changes (dashboards, analytics) and run `make docs.check` when touching documentation.

## Security & Configuration Tips
- Commit only sanitized configs; never check in secrets—use `.env` files sourced from `config/envs`.
- Run `make safety` (part of `make lint`) after dependency updates and review `SECURITY_RISK_ACCEPTED.md` for approved exceptions.
