## Summary

- TBD

## Scope

| Item | Value |
|---|---|
| Task type |  |
| One task / one branch / one PR | yes / no |
| Business code changed | yes / no |
| DB touched | no |
| Scraper run | no |
| Browser automation | no |
| Training executed | no |
| Data expansion | no |

## PR Authorization Matrix

Fill every row. Machine-readable — consumed by CI enforcement.

| Item | Value |
|---|---|
| Task type | choose one: docs-only / test-only / source-code / config-runtime / docker-deploy / workflow-governance / db-migration-sql / sc-002-db-governance / model-artifact / data-artifact / mixed |
| Authorized path categories | docs / tests / source / runtime-config / docker-deploy / workflow-governance / db-migration-sql / sc-002-db-governance / model-artifact / data-artifact / env-secret |
| Authorized paths | list exact paths; separate with `,` |
| Mixed task authorization | no / yes with explicit reason |
| High-risk categories present | no / yes: list |
| Requires Dangerous File Authorization | no / yes |
| Matrix enforcement expectation | template-only / report-only / blocking |

### Task type rules (summary)

Choose one primary task type. If files cross categories, use `mixed` only when explicitly authorized.
- **`docs-only`**: `docs/**`, `*.md`, `README*`, `AGENTS.md`, `CLAUDE.md`. Must not touch `src/`, `tests/`, `config/`, Docker, DB, SC-002, workflows, models, or data.
- **`test-only`**: `tests/**`. Must not touch `src/`, `config/`, Docker, DB, SC-002, workflows, models, or data.
- **`source-code`**: `src/**` (+ `tests/` and `docs/`). Must not touch Docker, DB, SC-002, workflows, models, or data unless mixed.
- **`config-runtime`**: `pyproject.toml`, `ruff.toml`, `mypy.ini`, `config/**`. Must not touch Docker, DB, SC-002, workflows, models, or data.
- **`docker-deploy`** / **`workflow-governance`** / **`db-migration-sql`** / **`sc-002-db-governance`** / **`model-artifact`** / **`data-artifact`** / **`mixed`**: Requires `## Dangerous File Authorization`.

If this PR touches Docker, workflow/governance, DB/migration/SQL, SC-002, env/secret, model, or data paths,
the `## Dangerous File Authorization` section must be substantive (≥2 lines of non-hollow content).

## Files Changed

| Path | Purpose |
|---|---|
|  |  |

## Documentation Impact

| Item | Value |
|---|---|
| New docs added |  |
| Reports added |  |
| Adds docs/_reports artifact | yes / no |
| Manifests added |  |
| Source-of-truth docs updated | yes / no |
| Updated authoritative docs | list paths |
| If not updated, explicit reason | required when no |

## Safety Impact

| Item | Value |
|---|---|
| Existing files deleted | 0 |
| Existing files moved | 0 |
| Existing files renamed | 0 |
| Business code changed | no |
| DB used | no |
| Browser automation used | no |
| Scraper run | no |

## Validation

| Validation | Result |
|---|---|
| Host validation |  |
| Container validation |  |
| GitHub Production Gate |  |

## CI Gate Scope

- What the validation proves:
- What the validation does not prove:

## No deletion / no move / no rename confirmation

| Item | Value |
|---|---|
| Deleted files | 0 |
| Moved files | 0 |
| Renamed files | 0 |

## Rollback Plan

- TBD

## Next Recommended Task

Do not start automatically.

Recommended next task only after user confirmation:

- TBD

## Safety Status

- no live fetch: yes / no / n/a
- no network request: yes / no / n/a
- no DB writes: yes / no / n/a
- no raw_match_data inserts: yes / no / n/a
- no matches writes: yes / no / n/a
- no parser/features/training/prediction: yes / no / n/a
- no full body/raw_data/pageProps saved or printed: yes / no / n/a

If any answer is `no`, list the explicit authorization:

- Authorization details:

## SC-002 status

- SC-002 is partial mitigation only.
- This PR does / does not change SC-002 guard coverage.
- This PR does / does not claim SC-002 is complete.
- training / data expansion / real DB write remain blocked.

## Remaining risks

- TBD

## Agent Workflow Hardening Checklist

Confirm every item. If any item is unchecked, explain why in the PR body.

- [ ] I did not work directly on main
- [ ] I started from clean latest origin/main
- [ ] This PR has a narrow, declared scope
- [ ] I did not rewrite unrelated modules
- [ ] I did not create V2 / FINAL / rewritten / replacement / backup duplicates
- [ ] I did not delete or move historical code without explicit cleanup scope
- [ ] I did not run DB write scripts
- [ ] I did not connect to DB for write operations
- [ ] I did not run SQL / migration
- [ ] I did not run scraper / browser / Playwright
- [ ] I did not train or expand data
- [ ] I did not mark partial mitigation as complete
- [ ] I listed remaining risks
- [ ] I waited for PR Gate to pass
- [ ] I will verify post-merge main Gate before task completion
