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

## Files Changed

| Path | Purpose |
|---|---|
|  |  |

## Documentation Impact

| Item | Value |
|---|---|
| New docs added |  |
| Reports added |  |
| Manifests added |  |
| Review reports added |  |
| Decision reports added |  |
| Next plans added |  |
| Exact allowed report paths, if any |  |

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

## Review Notes

- Reviewer focus:
- Residual risk:
- Follow-up PR, if any:
