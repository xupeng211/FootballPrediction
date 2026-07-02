# L3 Enforcement Design Proposal

## Status

- Phase: L3F enforcement design proposal
- Lifecycle: current-state proposal document
- Runtime behavior changed: no
- Source files changed: no
- CI/workflow changed: no
- Gate enforcement changed: no
- CODEOWNERS changed: no
- GitHub labels created: no
- Enforcement added: no
- Deletion/move/rename: no
- L3A basis: `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md`
- L3B basis: `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md`
- L3C basis: `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md`
- L3D basis: `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md`
- L3E basis: `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md`

## Purpose

L3A identified legacy entrypoints. L3B confirmed the active whitelist. L3C proposed labels and guard wording. L3D proposed review ownership and future CODEOWNERS wording. L3E resolved the 7 unknown-owner-decision categories.

L3F now proposes a **future enforcement design** so that:

1. The L3 taxonomy (labels, ownership, owner decisions) can be gradually enforced.
2. Enforcement is designed before it is implemented, not retrofitted after.
3. Future enforcement implementers have a clear blueprint with layers, criteria, and rollback strategy.
4. Automatable, human-review-only, and never-auto-decide checks are clearly separated.
5. No enforcement is implemented in this PR.

This proposal is **docs-only**. It does not create, modify, or implement any CI check, gate, script, workflow, or CODEOWNERS file.

## Non-implementation statement

This document explicitly does **not**:

- Modify `.github/**` (workflows, templates, branch protection, CODEOWNERS).
- Modify Gatekeeper (`scripts/devops/gatekeeper.sh`).
- Modify AI Workflow Gate (`scripts/ops/ai_workflow_gate.py`).
- Modify any script in `scripts/ops/`, `scripts/devops/`, or `scripts/maintenance/`.
- Create any new GitHub Actions workflow, pre-commit hook, or CI check.
- Add CI enforcement or blocking behavior.
- Add reviewer automation or required-review rules.
- Modify runtime files.
- Run, migrate, delete, move, or rename any entrypoint.
- Create GitHub labels.

It is a **human and AI agent guidance and future design proposal only**. All implementation requires separate, explicitly authorized future PRs.

---

## Enforcement design principles

These principles govern any future enforcement implementation:

1. **Advisory before blocking.** Every check should be advisory or warning-only before it becomes blocking. Dry-run periods are mandatory.
2. **Avoid false positives before hard gates.** A blocking check with false positives is worse than no check. Validate accuracy before enabling blocking mode.
3. **Never promote legacy/unknown to active automatically.** Classification changes require owner decision. Automation must not auto-promote.
4. **Never authorize deletion/move/rename automatically.** These operations require dedicated PRs with explicit authorization. Automation must flag them, not allow them.
5. **Keep L3 separate from L4.** Enforcement checks must not conflate L3 entrypoint isolation with L4 API boundary reconciliation.
6. **Require explicit owner authorization for enforcement implementation.** Each enforcement layer requires a separate, explicitly authorized PR.
7. **Require rollback plan for future gate implementation.** Every enforcement PR must include a rollback plan: disable flag, revert PR, or bypass mechanism.
8. **Docs-only PRs must not be blocked incorrectly.** Any enforcement must recognize docs-only PRs (no `src/`, `tests/`, `scripts/`, `.github/` changes) and not block them for runtime-related checks.

---

## Proposed enforcement layers

Enforcement is proposed in 7 layers, from weakest (documentation-only) to strongest (hard gate). Each layer requires separate authorization before implementation.

| Layer | Name | Purpose | Trigger | Action | Blocking? | Implementation status | Separate authorization required |
|---|---|---|---|---|---|---|---|
| 0 | Documentation reference | Human/agent consults L3 docs | Manual | None (advisory) | No | Already in place (docs exist) | No |
| 1 | Advisory checklist | PR body includes L3 impact table | Manual | Reviewer checks labels, ownership, unknown decisions | No | Not yet (template exists in L3C/L3D) | No (voluntary adoption) |
| 2 | Warning-only changed-file classifier | CI prints L3 labels for changed files | Push/PR | Prints warning to CI log; does not fail | No | Not implemented | Yes — separate PR |
| 3 | Soft gate for missing PR sections | CI fails when required PR-body sections are missing | PR | Fails with message listing missing sections | Yes — low-risk | Already partially in place (AI Workflow Gate checks required sections) | Already authorized |
| 4 | Restricted legacy / unknown touch guard | CI warns or fails when PR touches restricted-legacy or unknown-owner-decision without authorization wording | PR | Warning (non-blocking) → soft fail (blocking after dry-run) | Configurable | Not implemented | Yes — separate PR |
| 5 | High-risk path acknowledgment guard | CI requires explicit high-risk acknowledgment when PR touches sentinel_watch.js or equivalent | PR | Warning (non-blocking) → soft fail | Configurable | Not implemented | Yes — separate PR |
| 6 | Future hard gate | CI blocks merge when restricted-legacy, unknown, or high-risk paths are touched without explicit owner authorization in the PR body | PR | Fail (blocking) | Yes — high-risk | Not implemented | Yes — separate PR + dry-run period + owner approval |

### Layer rollout dependency

- Layer 2 must precede Layer 4 (must know which files are classified before enforcing classification).
- Layer 4 warning mode must run for a dry-run period (suggested: 10 PRs or 2 weeks, whichever is longer) before Layer 4 blocking mode.
- Layer 5 warning mode must run for a dry-run period before Layer 5 blocking mode.
- Layer 6 requires all prior layers to be stable, plus explicit owner approval.

---

## Automatable checks

These checks can be implemented by a future CI script without human judgment.

| Check | Source of truth | Candidate implementation | False-positive risk | Proposed rollout | Blocking candidate? |
|---|---|---|---|---|---|
| Changed-file classifier | L3B whitelist | Grep changed files against whitelist paths; output label for each | Low (exact path match) | Warning-only (Layer 2) | No — advisory only |
| L3 label lookup | L3B whitelist + L3E decisions | Map each changed file to its L3 label | Low (exact path match) | Warning-only (Layer 2) | No — advisory only |
| Restricted-legacy touch detection | L3B whitelist restricted list (18 entries) + L3E restricted-legacy decisions (6 entries) | If any changed file is in restricted-legacy glob, flag | Low (exact glob match) | Warning → soft-fail (Layer 4) | Yes — after dry-run |
| Unknown-owner-decision touch detection | L3B whitelist unknown list (now empty after L3E) | If any changed file matches previously-unknown glob, warn that the entry was recently classified | Low (empty list after L3E) | Warning-only | No — historical check |
| High-risk sentinel_watch.js touch detection | L3E Decision 3 | If `scripts/ops/sentinel_watch.js` is in diff, require explicit acknowledgment | Zero (exact path) | Warning → soft-fail (Layer 5) | Yes — after dry-run |
| Archive-read-only touch detection | L3B whitelist | If `archive_vault_2026/**` is in diff, warn | Low (exact path) | Warning-only (Layer 2) | No — advisory only |
| .github / gate touch detection | L3B whitelist governance list | If `.github/**`, `scripts/devops/**`, or `scripts/ops/ai_workflow_gate.py` is in diff, note governance impact | Medium (some .github changes are benign) | Warning-only (Layer 2) | No — advisory only |
| CODEOWNERS touch detection | `.github/CODEOWNERS` | If CODEOWNERS is in diff, warn that this requires separate authorization | Zero (exact path) | Warning-only (Layer 2) | No — advisory only |
| PR body required section presence | AI Workflow Gate REQUIRED_SECTIONS | Already implemented in `scripts/ops/ai_workflow_gate.py` | Low | Already blocking (Layer 3) | Already active |
| No deletion/move/rename detection | git diff --diff-filter=D,R | If any file is deleted or renamed, warn that this requires a dedicated PR | Low (exact git operation) | Warning-only (Layer 2) | No — advisory only |
| Report artifact backflow check | `docs/_reports/*.md` files added | Already implemented in `scripts/ops/ai_workflow_gate.py` (`check_authoritative_report_backflow`) | Medium (some reports are justified without source-of-truth update) | Already blocking | Already active |

---

## Human-review-only checks

These checks cannot be automated reliably and require human judgment.

| Check | Why not automatable | Who reviews |
|---|---|---|
| Whether a restricted-legacy change is truly justified | Requires understanding of business context, alternative paths, and risk trade-offs | Repo owner / legacy owner decision reviewer |
| Whether an unknown-owner-decision can be reclassified | Requires understanding of the entrypoint's purpose and operational status | Repo owner |
| Whether API boundary reconciliation is being mixed into L3 | Requires understanding of the difference between entrypoint isolation (L3) and API surface changes (L4) | Repo owner / API surface owner |
| Whether sentinel_watch.js shutdown risk is acceptable | Requires understanding of operational impact | Repo owner / operational owner |
| Whether CODEOWNERS handles are correct | Requires knowledge of GitHub team structure and project ownership | Repo owner |
| Whether a docs-only PR is genuinely docs-only | Requires reading the diff and judging whether documentation changes have runtime implications | Reviewer |
| Whether a new entrypoint should be classified as active or restricted | Requires understanding of the entrypoint's role in the system | Repo owner |
| Whether a restricted-legacy entrypoint can be safely archived or deleted | Requires archival judgment and operational awareness | Repo owner |

---

## Never auto-decide checks

These decisions must never be made by automation. They require explicit human owner authorization in every case.

| Decision | Why never auto-decide | Required authorization |
|---|---|---|
| Deleting legacy files | Irreversible; may break undocumented dependencies | Dedicated deletion PR + explicit owner authorization |
| Moving/renaming legacy files | Changes import paths, Docker volumes, documentation references | Dedicated move/rename PR + explicit owner authorization |
| Migrating unknown entrypoints into active runtime | Changes the production surface; requires full testing and rollout | Dedicated migration PR + explicit owner authorization + tests |
| Promoting restricted-legacy to active-runtime | Changes the trust boundary; requires verification that the entrypoint is production-ready | Dedicated promotion PR + explicit owner authorization + tests |
| Implementing CODEOWNERS handles | Changes review requirements; requires GitHub team setup | Dedicated CODEOWNERS PR + explicit owner authorization + handle verification |
| Changing branch protection rules | Affects all contributors; requires admin access | Dedicated branch-protection PR + explicit owner authorization |
| Changing gate policy from warning to blocking | Affects all PRs; may block emergency fixes | Dedicated gate PR + dry-run period + explicit owner authorization |
| Classifying a new unknown entrypoint as active | Same risks as promotion | Owner decision + whitelist update + explicit authorization |

---

## Proposed future PR body enforcement wording

When enforcement layers are implemented, PR bodies touching entrypoint paths must include this section:

```markdown
## L3 Enforcement Impact

| Item | Value |
|---|---|
| L3 labels touched | (list labels, e.g., active-runtime, restricted-legacy) |
| Restricted legacy touched | yes / no |
| Unknown-owner-decision touched | yes / no |
| Archive-read-only touched | yes / no |
| High-risk path touched (sentinel_watch.js or equivalent) | yes / no |
| Deletion / move / rename included | no |
| Runtime execution included | no |
| L4 API boundary reconciliation included | no |
| Explicit owner authorization present | yes / no / not required |
| Enforcement changed in this PR | no |
| CODEOWNERS changed in this PR | no |
```

### Enforcement authorization detail

If restricted-legacy, unknown, or high-risk paths are touched:

```markdown
| Path | L3 label | Action | Authorization |
|---|---|---|---|
| (path) | (label) | (modify / run / migrate / delete) | (how authorized) |
```

---

## Proposed future warning-only output

Example of what a future Layer 2 warning-only classifier might print to CI logs without failing:

```text
[L3-ENFORCEMENT][Layer-2][WARNING-ONLY] L3 changed-file classification:
  docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md → active-governance (techdebt docs)
  docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md → active-governance (techdebt docs)
  No restricted-legacy paths touched.
  No unknown-owner-decision paths touched.
  No high-risk paths touched.
  No archive-read-only paths touched.
  No .github/ or gate paths touched.
  No deletion/move/rename detected.
  Summary: 2 active-governance files. All clear.

[L3-ENFORCEMENT] This is a warning-only check. It does not block the PR.
```

Example with a restricted-legacy touch:

```text
[L3-ENFORCEMENT][Layer-2][WARNING-ONLY] L3 changed-file classification:
  scripts/ops/fotmob_match_id_discovery_db_dry_run.py → restricted-legacy (L3E Decision 1)
  *** WARNING: restricted-legacy path touched. Requires explicit authorization. ***
  docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md → active-governance (techdebt docs)
  Summary: 1 restricted-legacy, 1 active-governance.

[L3-ENFORCEMENT] This is a warning-only check. It does not block the PR.
[L3-ENFORCEMENT] If this PR is authorized to touch restricted-legacy paths,
               ensure the PR body includes the Legacy Entrypoint Authorization table.
```

---

## Proposed future hard-gate criteria

Layer 6 (hard gate) must satisfy all of the following before activation:

1. **Dry-run period completed.** Warning-only mode (Layer 4/5) must have run for at least 10 PRs or 2 weeks (whichever is longer) with zero false positives on docs-only PRs.
2. **Owner approval obtained.** The repo owner must explicitly approve the transition from warning to blocking.
3. **Separate implementation PR.** Hard-gate implementation must be in a dedicated PR, not mixed with other changes.
4. **Tests included.** The hard-gate check must have automated tests that verify:
   - Correctly identifies restricted-legacy paths.
   - Correctly identifies high-risk paths.
   - Does not block docs-only PRs.
   - Does not block PRs with proper authorization wording.
   - Blocks PRs that touch restricted-legacy without authorization.
5. **Rollback plan documented.** The implementation PR must include a rollback plan (disable flag, revert PR, or workflow step removal).
6. **Emergency bypass exists.** A documented bypass mechanism (e.g., owner-only label, commit message prefix) must allow emergency fixes to bypass the hard gate when necessary.
7. **Does not block docs-only PRs.** Hard gate must not block PRs that only change `docs/**` and do not touch restricted-legacy, unknown, archive, or high-risk paths.

---

## L3E owner-decision enforcement mapping

This table maps each L3E decision to its enforcement status for future implementation:

| L3E Decision | Category | Label | Future enforcement action when touched |
|---|---|---|---|
| 1 | `scripts/ops/fotmob_*.py` | restricted-legacy | Layer 4: warn/block unless Legacy Entrypoint Authorization present |
| 2 | `scripts/ops/check_health.js` | restricted-legacy | Layer 4: warn/block unless Legacy Entrypoint Authorization present |
| 3 | `scripts/ops/sentinel_watch.js` | restricted-legacy (HIGH RISK) | Layer 5: warn/block unless High-Risk Path Acknowledgment + Legacy Entrypoint Authorization present |
| 4 | `scripts/ops/audit_dataset.js` | restricted-legacy | Layer 4: warn/block unless Legacy Entrypoint Authorization present |
| 5 | `scripts/maintenance/integrity_guard.sh` | restricted-legacy | Layer 4: warn/block unless Legacy Entrypoint Authorization present |
| 6 | `scripts/test/run_test_suite.js` | test-only | Layer 2: informational only (not blocking, but note test-only status) |
| 7 | `src/**` modules with `__main__` | active-runtime | Layer 2: informational only (modules are active source; `__main__` blocks are self-tests) |

---

## Suggested future implementation candidates

These are potential future PRs, listed in recommended implementation order. None are implemented in this PR.

1. **Warning-only changed-file classifier** (Layer 2): CI step that maps changed files to L3 labels and prints classification without blocking. Sources: L3B whitelist + L3E decisions. Estimated false-positive risk: low. Separate authorization required: yes.

2. **PR body enforcement wording checker** (Layer 3 extension): Extend existing AI Workflow Gate to verify that PRs touching restricted-legacy paths include the Legacy Entrypoint Authorization table. Estimated false-positive risk: low. Separate authorization required: yes.

3. **Restricted-legacy path guard** (Layer 4): Warning mode first; after dry-run, optionally blocking. Flags PRs that touch restricted-legacy paths without authorization wording. Estimated false-positive risk: medium (needs careful docs-only PR exemption). Separate authorization required: yes.

4. **High-risk path acknowledgment guard** (Layer 5): Requires explicit shutdown-risk acknowledgment when sentinel_watch.js is touched. Estimated false-positive risk: zero (exact single path). Separate authorization required: yes.

5. **Report artifact backflow consistency checker** (existing Layer 3 extension): Already partially implemented. Could be extended to check L3-specific report/documentation consistency (e.g., when a new `docs/_reports/L3*.md` file is added, verify that a corresponding source-of-truth doc is updated). Estimated false-positive risk: medium. Separate authorization required: yes.

6. **Hard gate for restricted-legacy + unknown + high-risk** (Layer 6): Combines Layers 4 and 5 into a blocking gate after dry-run periods complete. Estimated false-positive risk: medium. Separate authorization required: yes + owner approval.

---

## Rollback and disable strategy for future enforcement

Any future enforcement implementation must include:

1. **Feature flag / warning-only mode.** Every check must be toggleable between `off`, `warn`, and `block`. Default should be `warn` for new checks.
2. **Revert PR.** The simplest rollback: revert the implementation PR. The enforcement disappears.
3. **Disable workflow step.** If enforcement is a CI workflow step, it can be disabled by commenting out the step or setting a workflow input.
4. **Bypass mechanism.** A documented bypass (owner-only label, commit message prefix like `[skip-l3-gate]`) must exist for emergency fixes. Bypass use must be auditable (logged in CI output).
5. **Owner decision required for strict mode.** Transitioning any check from `warn` to `block` requires explicit owner decision and a separate PR.
6. **Bypass must not become normal process.** If bypass usage becomes frequent (>10% of PRs), the check design must be re-evaluated.

---

## Relationship to L3A / L3B / L3C / L3D / L3E

| Document | Phase | Role |
|---|---|---|
| `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` | L3A | Original inventory and classification framework |
| `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` | L3B | Concrete whitelist with all categories |
| `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` | L3C | Label semantics and guard wording |
| `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md` | L3D | Review ownership and CODEOWNERS wording |
| `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md` | L3E | Unknown category owner decisions |
| `docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md` | L3F | **This document** — enforcement design proposal |

Reports: `docs/_reports/L3A_*` through `docs/_reports/L3F_*`.

## References

- `.github/workflows/production-gate.yml` — existing CI pipeline (not modified by L3F)
- `scripts/ops/ai_workflow_gate.py` — existing AI Workflow Gate (not modified by L3F)
- `scripts/devops/gatekeeper.sh` — existing Gatekeeper (not modified by L3F)
- `scripts/ops/helpers/` — existing gate helper library (not modified by L3F)

## Next recommended task

Do not start automatically.

Recommended next task only after user confirmation:

- Review and merge L3F if CI is green.
- Future task may implement a warning-only changed-file classifier (Layer 2), but only with separate explicit authorization.
- Do not implement enforcement, CODEOWNERS, or L4 without separate authorization.
