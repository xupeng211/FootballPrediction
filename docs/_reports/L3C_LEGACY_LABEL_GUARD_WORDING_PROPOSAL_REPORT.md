# L3C Legacy Label Guard Wording Proposal Report

## Snapshot

- Main head: `ac545bb18606e124bc0144dbb35b2abaf1e08903`
- Main CI run: `28595878906`
- Main CI conclusion: success
- Branch: `techdebt/l3c-legacy-label-guard-wording-proposal`
- Scan date: 2026-07-02
- Task type: docs-only

## Source documents

- `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` — L3A planning (merged in #1685)
- `docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md` — L3A scan report (merged in #1685)
- `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` — L3B whitelist (merged in #1686)
- `docs/_reports/L3B_ACTIVE_ENTRYPOINT_WHITELIST_CONFIRMATION_REPORT.md` — L3B report (merged in #1686)
- `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` — L3C proposal (this PR)

## Method

- L3A and L3B document review: read all four source documents to understand the full classification landscape.
- Static wording search: grepped existing governance wording across `docs/`, `scripts/`, and `.github/` to ensure the L3C proposal does not conflict with existing AI Workflow Gate, Gatekeeper, PR Authorization Matrix, or Dangerous File Authorization wording.
- Label design: mapped each L3B classification category to an advisory label with clear default-action, modification-authorization, and runtime-execution rules.
- Template design: created copyable PR-body sections for the five most common boundary-crossing scenarios.
- Prompt guard wording: designed both a full and a short variant for inclusion in future Claude Code task prompts.
- No runtime execution, no Docker, no DB, no secrets, no gate modification.

## Proposed label summary

| Label | Default action | Explicit authorization needed for modification | Enforcement status |
|---|---|---|---|
| `active-runtime` | Treat as source-of-truth | Task-scoped authorization naming the path | Advisory (docs-only) |
| `active-api-router` | Treat as active API surface | API-scoped task authorization | Advisory (docs-only) |
| `active-governance` | Treat as active governance | Governance task authorization | Advisory (docs-only) |
| `operational-guarded` | Read, do not run | Operational authorization naming the target | Advisory (docs-only) |
| `restricted-legacy` | Read-only | Explicit user authorization naming exact path | Advisory (docs-only) |
| `archive-read-only` | Read-only | Dedicated archive authorization | Advisory (docs-only) |
| `test-only` | Read; modify in test scope | Test-scoped task authorization | Advisory (docs-only) |
| `unknown-owner-decision` | No-touch (treat as restricted) | Owner decision required first | Advisory (docs-only) |

## Proposed guard templates

| Template | Purpose | Location in proposal doc |
|---|---|---|
| Entrypoint Boundary Impact | PR body table declaring which entrypoint classes are affected | `## Entrypoint Boundary Impact — PR body template` |
| Legacy Entrypoint Authorization | Authorization request when a PR must touch a restricted legacy path | `## Legacy Entrypoint Authorization — PR body template` |
| Unknown Entrypoint Owner Decision | Request owner classification of an unknown entry | `## Unknown Entrypoint Owner Decision — template` |
| Archive Exception Authorization | Authorization request for archive path access | `## Archive Exception Authorization — template` |
| No L4 mixing wording | Statement that a PR does not include L4 API boundary reconciliation | `## No L4 mixing — wording` |
| Full prompt guard wording | Claude Code task prompt block with all 8 boundary rules | `## Prompt guard wording for future Claude Code tasks` |
| Short prompt variant | Abbreviated 3-line prompt guard for brief task prompts | (same section) |

## Key decisions

1. **Labels are advisory, not enforced.** L3C explicitly does not add CI enforcement, GitHub labels, code annotations, or gate modifications. This keeps L3C purely in the documentation domain and avoids scope creep into CI/gate changes.

2. **Eight-label taxonomy covers the full L3B classification.** Every category from the L3B whitelist (active runtime, active API router, active governance, operational guarded, restricted legacy, archive, test-only, unknown) maps to exactly one label. No gaps, no overlaps.

3. **"Restricted legacy" is the default stance for anything not active.** The 18 restricted legacy entries from L3B, plus the 7 unknown categories (treated as restricted until classified), form a clear "do not touch without authorization" boundary.

4. **Templates are copyable, not auto-injected.** The PR body templates are designed to be copied manually by PR authors. L3C does not propose auto-injection into PR bodies or CI checks.

5. **Prompt guard wording is opt-in.** Future Claude Code tasks can include the guard block, but L3C does not mandate it. The short variant exists for tasks where the full block would be excessive.

6. **L4 API boundary reconciliation is explicitly excluded.** Every template and rule includes a "no L4 mixing" clause to prevent scope drift from L3 (entrypoint isolation) into L4 (API boundary changes).

7. **Unknown entries require owner decision before any action.** The 7 unknown categories from L3B remain blocked until the owner classifies them. L3C provides a template for requesting that decision.

8. **Enforcement is deferred to a future phase (L3E+).** L3C is the "wording" phase. Enforcement (CI integration, gate updates, automated checks) requires a separate, explicitly authorized future task.

9. **Existing governance wording is not duplicated or contradicted.** The static wording search confirmed that L3C labels and templates complement — not replace — the existing AI Workflow Gate, PR Authorization Matrix, and Dangerous File Authorization wording.

10. **Labels do not create new authorization paths.** A label like `active-runtime` does not mean "free to modify." Task authorization is always required. Labels only define the default boundary and the type of authorization needed.

## Non-decisions

- **No CI enforcement decision.** L3C does not decide whether, when, or how to enforce label boundaries in CI.
- **No GitHub label creation.** The label names are documentation descriptors, not GitHub issue/PR labels.
- **No CODEOWNERS change.** L3C does not propose changes to `.github/CODEOWNERS`.
- **No file deletion, move, or rename.** All 18 restricted legacy entries and 7 unknown categories remain in place.
- **No migration.** No legacy entrypoint is migrated to a new location or API surface.
- **No L4 API boundary decision.** The relationship between `src/main.py` inline `/predict` and `src/api/predictions/predict_router.py` is not resolved.
- **No gate modification.** AI Workflow Gate, Gatekeeper, and all CI workflows are unchanged.

## Report Lifecycle

- **Owner**: TECHDEBT-L3 legacy entrypoint isolation track.
- **Purpose**: bounded L3C proposal snapshot for label semantics and guard wording.
- **Source-of-truth relationship**: supports `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` (the primary L3C artifact). This report is a companion proposal artifact, not the source-of-truth itself.
- **Supersession**: may be superseded by a future L3D review ownership wording proposal, a future L3E enforcement proposal, or actual CI enforcement implementation.
- **Cleanup**: no immediate cleanup required; future cleanup requires explicit user authorization.
- **Raw scan outputs**: temporary `/tmp` artifacts only, not committed.

## Remaining risks

- **Wording is advisory only and not enforced by CI.** Future agents or PR authors may ignore these labels and templates unless prompts or review processes actively reference them.
- **Future agents may ignore docs unless prompts reference them.** The prompt guard wording is opt-in; agents working from bare task descriptions without the guard block may not consult the whitelist.
- **Unknown entries still require owner decision.** Seven categories remain unclassified. Until the owner reviews them, agents must treat them as restricted, which may block legitimate work.
- **Enforcement requires separate authorization.** If the team wants CI-enforced label boundaries, that is a separate task with its own risk assessment, implementation, and rollout.
- **Label drift over time.** As the codebase evolves, new entrypoints may appear that are not yet classified. A periodic re-scan (L3-maintenance) may be needed.
- **Template adoption is voluntary.** PR authors are not forced to use the Entrypoint Boundary Impact table. Adoption depends on team convention and reviewer expectation.

## Recommended next step

Do not start automatically.

Recommended:
- Review and merge L3C if CI is green.
- Then decide separately whether **L3D** should propose docs-only review ownership / CODEOWNERS wording that maps labels to reviewer responsibility.
- Do not implement gate enforcement without separate explicit authorization.
- Priority: owner should review and classify the 7 unknown categories to complete the L3 taxonomy.
