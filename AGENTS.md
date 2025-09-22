# Repository Guidelines

## Project Structure & Module Organization
- Runtime code lives in `src/`: FastAPI routers in `src/api`, domain rules in `src/core`, orchestration in `src/services` and `src/tasks`, persistence in `src/database`, and shared helpers in `src/utils`.
- Tests mirror the modules under `tests/unit`, `tests/integration`, `tests/e2e`, and `tests/monitoring`; reusable fixtures sit in `tests/fixtures` and synthetic datasets in `data/`.
- Generated assets belong in `data/` or `models/`, automation scripts in `scripts/`, and long-form references in `docs/`; keep environment samples synced across `env.template` and `env.example`.

## Build, Test, and Development Commands
- `make venv` then `make install` prepares the local Python 3.10+ toolchain inside `.venv`.
- `make fmt` runs Black and isort; `make lint` layers flake8 plus mypy for static safety.
- `make test` executes the full pytest suite; use `make coverage` to enforce the ≥80% threshold or `make coverage-fast` for quick unit feedback.
- `make context` summarizes the project topology—run it ahead of large refactors or onboarding handoffs.

## Coding Style & Naming Conventions
- Follow four-space indentation, 88-character lines, snake_case for functions and modules, PascalCase for classes, and UPPER_SNAKE_CASE for constants.
- Add type hints and docstrings for public APIs, services, and tasks; align Pydantic response models with endpoints in `src/api`.
- Prefer explicit imports, keep module-level configuration in `config/`, and avoid leaking secrets into code or samples.

## Testing Guidelines
- Name files `test_*.py`, scope markers with `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.e2e`, and register long-running monitors under `tests/monitoring`.
- Reuse fixtures from `tests/fixtures` and synthetic artifacts in `data/`; never rely on production snapshots.
- Investigate coverage dips immediately and add regression cases when bugs reach production.

## Commit & Pull Request Guidelines
- Use Conventional Commit prefixes (`feat:`, `fix:`, `style:`, etc.), limit subjects to 72 characters, and note executed commands in the body.
- Reference tickets in the footer (e.g., `Refs: FP-123`) and confirm lint plus test status before pushing.
- PRs should summarize intent, list verification steps (paste command snippets), attach relevant logs or screenshots, and flag schema, monitoring, or deployment impacts.

## Security & Configuration Tips
- Base local configs on `env.template` or `env.example`, injecting secrets through tooling or runtime variables only.
- Audit `docker-compose*.yml` and reverse-proxy settings whenever new services, ports, or hostnames are introduced.
- Keep security scans current: run `make lint` after dependency bumps and review `reports/` plus `security_report*.json` before releases.
