## Summary

- TBD

## Scope

| Item | Value |
|---|---|
| Task type |  |
| One task / one branch / one PR | yes / no |
| Combines feature + cleanup, audit + repair, merge + new work, or docs governance + business code | no |
| Merge-only zero-change task | yes / no / n/a |
| Business code changed | yes / no |
| FotMob code changed | yes / no |

## PR Authorization Matrix

Fill every row. This section is machine-readable and will be consumed by future
CI enforcement. See `docs/AGENT_WORKFLOW.md` §Task-Level PR Authorization Matrix.

| Item | Value |
|---|---|
| Task type | choose one: docs-only / test-only / source-code / config-runtime / docker-deploy / workflow-governance / db-migration-sql / sc-002-db-governance / model-artifact / data-artifact / mixed |
| Authorized path categories | docs / tests / source / runtime-config / docker-deploy / workflow-governance / db-migration-sql / sc-002-db-governance / model-artifact / data-artifact / env-secret / unknown |
| Authorized paths | list exact paths or globs; separate with `,` |
| Mixed task authorization | no / yes with explicit reason |
| High-risk categories present | no / yes: list categories |
| Requires Dangerous File Authorization | no / yes |
| Matrix enforcement expectation | template-only / report-only / blocking |

### Task type rules

Choose exactly one primary task type. If changed files cross categories, use
`mixed` only when explicitly authorized — not as a convenience fallback.

- **`docs-only`**: documentation-only changes (`docs/**`, `*.md`, `README*`,
  `AGENTS.md`, `CLAUDE.md`). Must not touch `src/`, `tests/`, `config/`,
  Docker, DB, SC-002, workflows, models, or data.
- **`test-only`**: tests-only changes (`tests/**`). Must not touch `src/`,
  `config/`, Docker, DB, SC-002, workflows, models, or data.
- **`source-code`**: runtime/source implementation changes (`src/**`, plus
  `tests/` and `docs/`). Must not touch Docker, DB, SC-002, workflows, models,
  or data unless mixed.
- **`config-runtime`**: runtime configuration (`pyproject.toml`, `ruff.toml`,
  `mypy.ini`, `config/**`). Must not touch Docker, DB, SC-002, workflows,
  models, or data.
- **`docker-deploy`**: Docker, Compose, devcontainer, deploy (`Dockerfile*`,
  `docker-compose*`, `compose*`, `.devcontainer/**`, `deploy/docker/**`).
  Requires `## Dangerous File Authorization`.
- **`workflow-governance`**: GitHub workflows, PR template, CODEOWNERS, AI
  workflow gate, governance helpers, agent workflow docs. Requires
  `## Dangerous File Authorization`.
- **`db-migration-sql`**: SQL files, migrations, Alembic, schema changes.
  Requires `## Dangerous File Authorization`.
- **`sc-002-db-governance`**: SC-002 scripts, DB write guards, DB role
  governance files. Requires `## Dangerous File Authorization`.
- **`model-artifact`**: model files, `.joblib`, `.pkl` (`models/**`,
  `model_zoo/**`). Requires `## Dangerous File Authorization`.
- **`data-artifact`**: data files, generated artifacts (`data/**`,
  `artifacts/**`). Requires `## Dangerous File Authorization`.
- **`mixed`**: only when the user explicitly authorized a cross-category PR.
  Requires `## Dangerous File Authorization` and explicit reason.

### High-risk path rule

If this PR touches Docker/deploy, GitHub workflow/governance, DB/migration/SQL,
SC-002, env/secret, model artifact, or data artifact paths, the
`## Dangerous File Authorization` section must be substantive (at least 2 lines
of non-hollow content). Do not claim `docs-only`, `test-only`, or `no DB / no
Docker / no workflow` if changed files contradict that claim.

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
| Review reports added |  |
| Decision reports added |  |
| Next plans added |  |
| Exact allowed report paths, if any |  |
| Source-of-truth docs updated | yes / no |
| Updated authoritative docs | list paths |
| If not updated, explicit reason | required when no; do not use n/a, none, not needed, no, 无, 无需 |
| Active conclusions reflected in PROJECT_STATUS.md | yes / no / n/a with reason |

## Safety Impact

| Item | Value |
|---|---|
| Existing files deleted | 0 |
| Existing files moved | 0 |
| Existing files renamed | 0 |
| Archive operation performed | no |
| Business code changed | no |
| FotMob code changed | no |
| DB used | no |
| Browser automation used | no |
| Scraper run | no |
| New manifest created | no |
| New next-plan created | no |
| New review report created | no |
| New decision report created | no |

## Validation

| Validation | Result |
|---|---|
| Host validation |  |
| Container validation |  |
| GitHub Production Gate |  |

## CI Gate Scope

- What the validation proves:
- What the validation does not prove:
- Host unavailable results, if any:
- Container validation results, if any:

## No deletion / no move / no rename confirmation

| Item | Value |
|---|---|
| Deleted files | 0 |
| Moved files | 0 |
| Renamed files | 0 |
| Created docs/_archive content | no |
| Performed archive move | no |

## Rollback Plan

- TBD

## Next Recommended Task

Do not start automatically.

Recommended next task only after user confirmation:

- TBD

## PR Type

选择一个主类型：

- [ ] runtime-code-change
- [ ] governance-only
- [ ] docs-only
- [ ] test-only
- [ ] ci-fix
- [ ] data-artifact

## Runtime Behavior

- Runtime code change included: yes / no
- Runtime code paths changed: n/a
- Runtime behavior changed: n/a

如果这是 implementation phase 但没有 runtime code change，默认 No-Go。请说明原因、blocker 和人工确认：

- Explanation:
- Human confirmation:

## Artifact Scope

- Docs/report/manifest changes included: yes / no
- Added/modified report lines:
- Added/modified manifest lines:
- Copies full historical state: yes / no
- Includes large artifact: yes / no
- Large artifact justification, if any:

## Business Progress

- Business progress:
- Blocker removed:
- Blocker remaining:
- Next step:

## Ingestion Convergence Gate

Fill this section for any data ingestion, source inventory, target identity, raw write readiness,
accepted mapping, baseline, suspended target, or blocked target PR. Use `n/a` only when the PR is
not part of ingestion.

- Ingestion blocker removed:
- Target state delta:
- Count moved to clean_candidate:
- Count moved to rejected/superseded:
- Count moved to eligible_for_re_acceptance_review:
- Count moved to needs_new_evidence:
- Count remain_suspended:
- Count still blocked:
- No-progress justification:
- Does this PR trigger architecture decision gate? yes / no / n/a
- Is next step bounded? yes / no / n/a
- Is this the second consecutive no-progress ingestion PR? yes / no / n/a

## Safety Status

- no live fetch: yes / no / n/a
- no detail fetch: yes / no / n/a
- no network request: yes / no / n/a
- no DB writes: yes / no / n/a
- no raw_match_data inserts: yes / no / n/a
- no matches writes: yes / no / n/a
- no matches.external_id changes: yes / no / n/a
- no raw write execution: yes / no / n/a
- no re-acceptance execution: yes / no / n/a
- no suspension reversal: yes / no / n/a
- no rollback execution: yes / no / n/a
- no parser/features/training/prediction: yes / no / n/a
- no full body/raw_data/pageProps saved or printed: yes / no / n/a

If any answer is `no`, list the explicit authorization, scope, command, and verification:

- Authorization details:

## Tests Run

- [ ] lint
- [ ] unit tests
- [ ] coverage
- [ ] formatter
- [ ] git diff --check
- [ ] hidden/bidi scan
- [ ] full payload marker scan
- [ ] DB SELECT-only safety check, if applicable
- [ ] other:

Commands and results:

```text

```

## Repository Hygiene / Debt Impact

- New files added:
- File lifecycle for each new file:
  permanent / phase-artifact / one-shot-helper / test-fixture / temporary /
  archive-candidate / delete-after-use
- Permanent files:
- Phase-only artifacts:
- One-shot helpers (describe cleanup condition):
- Test fixtures:
- Files superseded:
- Files deleted or archived:
- Cleanup required later:
- Current-state doc updated? yes / no / not needed:
- Report line count:
- Manifest size (lines / fields):
- Does this PR increase repository noise? yes / no:
- If yes, why is it justified:
- Next cleanup trigger:

## Artifact limits checklist

- [ ] No full HTML/pageProps/raw_data/source body saved
- [ ] No large report unless justified in comments above
- [ ] No full historical recap copied
- [ ] No orphan helper/script without lifecycle
- [ ] Tests protect runtime behavior where applicable

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

## Review Notes

- Reviewer focus:
- Residual risk:
- Follow-up PR, if any:
