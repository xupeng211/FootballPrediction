# L3F Enforcement Design Proposal Report

## Snapshot

- Main head: `37494d6275c3689850b620a10e5ac491b2a07afc`
- Main CI run: `28616176919`
- Main CI conclusion: success
- Branch: `techdebt/l3f-enforcement-design-proposal`
- Scan date: 2026-07-03
- Task type: docs-only

## Source documents

- `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` — L3A planning (merged in #1685)
- `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` — L3B whitelist (merged in #1686)
- `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` — L3C label proposal (merged in #1687)
- `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md` — L3D ownership proposal (merged in #1688)
- `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md` — L3E owner decisions (merged in #1689)
- `docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md` — L3F enforcement design (this PR)
- All corresponding `docs/_reports/L3*_REPORT.md` files

## Method

- L3A-L3E document review: read all ten source documents (5 proposals + 5 reports) to understand the full classification chain before designing enforcement.
- Static gate/workflow/policy recheck: searched existing enforcement patterns in `scripts/ops/ai_workflow_gate.py`, `scripts/ops/helpers/`, `.github/workflows/production-gate.yml`, and `scripts/devops/gatekeeper.sh` to understand current enforcement capabilities and avoid redundant design.
- Enforcement layer design: mapped the L3 taxonomy to a 7-layer enforcement model (Layer 0 through Layer 6), from documentation-only to hard gate.
- Automatable vs. human-review-only separation: classified each potential check by whether it can be automated (11 automatable candidates identified) or requires human judgment (8 human-review-only checks).
- Never-auto-decide enumeration: identified 8 decision types that must never be automated.
- Future templates: designed PR body enforcement wording, warning-only CI output examples, and hard-gate activation criteria.
- No runtime execution, no Docker, no DB, no secrets, no gate modification, no script modification.

## Proposed enforcement layers summary

| Layer | Name | Blocking? | Implementation status | Future authorization needed |
|---|---|---|---|---|
| 0 | Documentation reference | No | In place (L3A-L3E docs exist) | No |
| 1 | Advisory checklist | No | Template exists (L3C/L3D) | No (voluntary) |
| 2 | Warning-only changed-file classifier | No | Not implemented | Yes — separate PR |
| 3 | Soft gate for missing PR sections | Yes (low-risk) | Partially active (AI Workflow Gate) | Already authorized |
| 4 | Restricted legacy / unknown touch guard | Configurable | Not implemented | Yes — separate PR |
| 5 | High-risk path acknowledgment guard | Configurable | Not implemented | Yes — separate PR |
| 6 | Future hard gate | Yes (high-risk) | Not implemented | Yes — separate PR + dry-run + owner approval |

## Automatable vs human-review-only summary

### Automatable candidates (11)

- Changed-file classifier (grep against whitelist)
- L3 label lookup (map file to label)
- Restricted-legacy touch detection (glob match)
- Unknown-owner-decision touch detection (glob match, empty after L3E)
- High-risk sentinel_watch.js touch detection (exact path)
- Archive-read-only touch detection (exact path)
- .github / gate touch detection (glob match)
- CODEOWNERS touch detection (exact path)
- PR body required section presence (already implemented)
- No deletion/move/rename detection (git diff filter)
- Report artifact backflow check (already partially implemented)

### Human-review-only checks (8)

- Restricted-legacy change justification
- Unknown-owner-decision reclassification
- L3/L4 boundary mixing detection
- Sentinel shutdown risk acceptance
- CODEOWNERS handle correctness
- Docs-only PR classification verification
- New entrypoint classification
- Legacy entrypoint archival/deletion readiness

### Never auto-decide items (8)

- Deleting legacy files
- Moving/renaming legacy files
- Migrating unknown entries to active runtime
- Promoting restricted-legacy to active-runtime
- Implementing CODEOWNERS handles
- Changing branch protection rules
- Changing gate policy from warning to blocking
- Classifying new unknown entries as active

## Key decisions

1. **7-layer enforcement model with progressive blocking.** Layers 0-2 are advisory, Layer 3 is already partially blocking, Layers 4-5 are configurable (warning or blocking), and Layer 6 is a future hard gate requiring dry-run, owner approval, and separate implementation PR.

2. **Layer 2 (warning-only classifier) is the recommended next implementation step.** It has the lowest risk (warning-only, no blocking), provides immediate value (visible L3 classification on every PR), and establishes the infrastructure for Layers 4-6.

3. **All new blocking checks require dry-run periods.** Suggested minimum: 10 PRs or 2 weeks (whichever is longer) in warning mode before transitioning to blocking. This prevents false-positive disruptions.

4. **Docs-only PRs must never be blocked by enforcement.** Any enforcement check must recognize PRs that only change `docs/**` (and do not touch restricted-legacy, unknown, archive, or high-risk paths) and pass them without blocking.

5. **L3E decisions are directly mappable to enforcement actions.** Each of the 7 L3E owner decisions has a clear enforcement action: 5 restricted-legacy entries map to Layer 4, 1 high-risk entry maps to Layer 5, 1 test-only entry maps to Layer 2 (informational), and 1 active-runtime entry maps to Layer 2.

6. **Existing AI Workflow Gate infrastructure can be extended rather than replaced.** The AI Workflow Gate already checks PR body sections (Layer 3), runs matrix validation, and enforces report backflow. Future enforcement can add checks to this existing pipeline rather than creating a separate system.

7. **8 decision types must never be automated.** These include deletion, migration, promotion, CODEOWNERS implementation, and gate policy changes. Listing these explicitly prevents future agents from attempting to automate irreversible or high-risk decisions.

8. **All enforcement implementation requires separate PRs with explicit authorization.** L3F is a design document. Each layer implementation (2, 4, 5, 6) requires its own PR, its own CI validation, its own rollback plan, and explicit owner sign-off.

9. **Bypass mechanisms are required for emergency use but must be auditable.** Suggested bypass: owner-only label or `[skip-l3-gate]` commit message prefix. Bypass usage must be logged in CI output. If bypass usage exceeds 10% of PRs, the check design must be re-evaluated.

10. **L3F completes the TECHDEBT-L3 documentation chain (L3A through L3F).** L3A identified, L3B classified, L3C labeled, L3D assigned ownership, L3E resolved unknowns, and L3F designed enforcement. Implementation is deferred to future phases.

## Non-decisions

- **No runtime change.** No source file is modified, executed, or imported differently.
- **No source code change.** No Python, JavaScript, TypeScript, or shell file is modified.
- **No CI enforcement implementation.** No workflow, gate, or check is added or modified.
- **No Gatekeeper change.** `scripts/devops/gatekeeper.sh` is unchanged.
- **No AI Workflow Gate change.** `scripts/ops/ai_workflow_gate.py` is unchanged.
- **No CODEOWNERS implementation.** No `.github/CODEOWNERS` changes.
- **No GitHub label creation.**
- **No branch protection change.**
- **No reviewer automation change.**
- **No file deletion, move, or rename.**
- **No migration.** No entrypoint is migrated.
- **No L4 API boundary decision.**
- **No enforcement implementation.** This is a design document only.

## Report Lifecycle

- **Owner**: TECHDEBT-L3 legacy entrypoint isolation track.
- **Purpose**: bounded L3F proposal snapshot for future enforcement design.
- **Source-of-truth relationship**: supports `docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md` (the primary L3F artifact). This report is a companion proposal artifact, not the source-of-truth itself.
- **Supersession**: may be superseded by a future Layer 2 implementation PR, a future Layer 4/5/6 implementation PR, or a future enforcement operations runbook.
- **Cleanup**: no immediate cleanup required; future cleanup requires explicit user authorization.
- **Raw scan outputs**: temporary `/tmp` artifacts only, not committed.

## Remaining risks

- **Design is advisory only and not enforced by CI.** Future agents or PR authors may ignore this design unless implementation proceeds.
- **Future implementation may create false positives.** The changed-file classifier relies on exact path matching. New files or renamed files may not be recognized by the glob patterns, leading to false negatives (missed classifications) or false positives (incorrect classifications).
- **Future strict mode may block legitimate emergency fixes.** The bypass mechanism must be well-designed and well-documented before Layer 6 activation.
- **CODEOWNERS handles are still not implemented.** Enforcement of review ownership (L3D) depends on CODEOWNERS implementation, which is not part of L3F.
- **L4 API boundary reconciliation remains out of scope.** Enforcement of L3/L4 separation depends on human review, not automation.
- **Adoption of PR body templates is voluntary until enforcement is implemented.** The Entrypoint Boundary Impact table and Legacy Entrypoint Authorization table are not currently required by any CI check.

## Recommended next step

Do not start automatically.

Recommended:
- Review and merge L3F if CI is green.
- Future task may implement a warning-only changed-file classifier (Layer 2), but only with separate explicit authorization.
- Do not implement enforcement, CODEOWNERS, or L4 without separate authorization.
