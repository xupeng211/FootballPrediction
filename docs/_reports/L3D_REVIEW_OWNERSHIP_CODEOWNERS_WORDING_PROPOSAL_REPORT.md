# L3D Review Ownership CODEOWNERS Wording Proposal Report

## Snapshot

- Main head: `e70a5187e1a9d381bc97f727c0cc01b1dd1a5d2d`
- Main CI run: `28601872656`
- Main CI conclusion: success
- Branch: `techdebt/l3d-review-ownership-codeowners-wording-proposal`
- Scan date: 2026-07-02
- Task type: docs-only

## Source documents

- `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` — L3A planning (merged in #1685)
- `docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md` — L3A scan report (merged in #1685)
- `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` — L3B whitelist (merged in #1686)
- `docs/_reports/L3B_ACTIVE_ENTRYPOINT_WHITELIST_CONFIRMATION_REPORT.md` — L3B report (merged in #1686)
- `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` — L3C label proposal (merged in #1687)
- `docs/_reports/L3C_LEGACY_LABEL_GUARD_WORDING_PROPOSAL_REPORT.md` — L3C report (merged in #1687)
- `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md` — L3D proposal (this PR)

## Method

- L3A/L3B/L3C document review: read all six source documents to understand the full classification, label, and guard wording landscape.
- Ownership / CODEOWNERS wording search: searched existing `.github/CODEOWNERS`, docs, scripts, and workflows for ownership, reviewer, and approval references to avoid conflicts.
- Read existing `.github/CODEOWNERS`: confirmed all entries currently assigned to `@xupeng211`.
- Ownership area design: mapped each of the 8 L3C labels to a review ownership area with a default reviewer role and authorization requirement.
- Future CODEOWNERS proposal: drafted a placeholder-based structure organized around ownership areas, with explicit caveats that it is not implemented.
- Template design: created reviewer checklist, PR body review ownership table, Claude Code prompt guard wording, and unknown owner decision workflow.
- No runtime execution, no Docker, no DB, no secrets, no CODEOWNERS modification, no gate modification.

## Proposed ownership summary

| Ownership area | Applies to label | Default action | Explicit authorization needed | Enforcement status |
|---|---|---|---|---|
| Runtime owner | `active-runtime` | Treat as source-of-truth | Task-scoped authorization | Advisory (docs-only) |
| API surface owner | `active-api-router` | Treat as active API surface | API-scoped task authorization | Advisory (docs-only) |
| Governance owner | `active-governance` | Treat as active governance | Governance task authorization | Advisory (docs-only) |
| Operational owner | `operational-guarded` | Read, do not run | Operational authorization | Advisory (docs-only) |
| Legacy owner decision | `restricted-legacy` | Read-only | Explicit user authorization | Advisory (docs-only) |
| Archive owner decision | `archive-read-only` | Read-only | Dedicated archive authorization | Advisory (docs-only) |
| Test owner | `test-only` | Read; modify in test scope | Test-scoped authorization | Advisory (docs-only) |
| Unknown owner decision | `unknown-owner-decision` | No-touch | Owner decision required first | Advisory (docs-only) |

## Proposed templates

| Template | Purpose | Location in proposal doc |
|---|---|---|
| Reviewer checklist | 12-item checklist for PRs touching entrypoint paths | `## Reviewer checklist template` |
| PR body review ownership table | Per-ownership-area impact declaration | `## PR body review ownership template` |
| Future Claude Code prompt guard wording | 10-rule block + short variant for task prompts | `## Future Claude Code prompt guard wording` |
| Unknown owner decision workflow | 7-step workflow for classifying unknown entries | `## Owner decision workflow for unknown entries` |
| Unknown entry decision record | Template for recording classification decisions | (same section) |
| Future CODEOWNERS structure | Placeholder-based example grouped by ownership area | `## Future CODEOWNERS wording proposal` |

## Key decisions

1. **Eight ownership areas mirror the eight L3C labels.** No new labels are introduced. Each label maps 1:1 to an ownership area, keeping the taxonomy simple and consistent across L3B, L3C, and L3D.

2. **Repo owner is the default reviewer for all restricted/archive/unknown areas.** The existing CODEOWNERS assigns everything to `@xupeng211`. L3D maintains this default for high-risk areas while allowing future delegation for active areas (runtime, API, governance, ops, test).

3. **Future CODEOWNERS uses placeholder handles.** `@REPO_OWNER_RUNTIME`, `@REPO_OWNER_API`, etc. are explicitly marked as placeholders. The proposal does not assume any specific GitHub team or user exists.

4. **CODEOWNERS implementation is gated behind multiple conditions.** A future implementation PR must: be separately authorized, replace all placeholders with real handles, pass CI independently, and receive explicit owner sign-off.

5. **Reviewer checklist covers all L3 boundary dimensions.** The 12-item checklist asks reviewers to verify: entrypoint labels identified, active whitelist, restricted legacy, unknown, archive, L4 boundary, deletion/move/rename, runtime execution, governance files, source-of-truth docs, report lifecycle, and rollback plan.

6. **Unknown owner decision workflow is explicit and blocking.** Agents cannot proceed past an unknown entry without filing a decision request and receiving owner classification. This closes the "unknown" gap in the L3 taxonomy.

7. **Governance files have a dedicated ownership area.** This prevents PRs with runtime, API, data, or docs scope from accidentally modifying CI gates, AI Workflow Gate, or Gatekeeper.

8. **Test-only entries are not runtime source-of-truth.** Reviewers must reject PRs that treat test entrypoints as production runtime surfaces.

9. **No enforcement is added in L3D.** Reviewer checklist, ownership table, and CODEOWNERS wording are all advisory. Enforcement (required reviews, branch protection, CI checks) requires separate authorization.

10. **L3D is the last structural proposal phase before owner decisions.** After L3D, the only remaining gap is the 7 unknown categories. L3E can resolve them through owner decisions without introducing new structural concepts.

## Non-decisions

- **No CODEOWNERS implementation.** The existing `.github/CODEOWNERS` is not modified.
- **No GitHub label creation.** Ownership areas are documentation concepts, not GitHub labels.
- **No CI enforcement decision.** No required-review rules, branch protection changes, or CI checks are added.
- **No branch protection change.**
- **No reviewer automation change.**
- **No file deletion, move, or rename.**
- **No migration.** No legacy entrypoint is migrated.
- **No L4 API boundary decision.**

## Report Lifecycle

- **Owner**: TECHDEBT-L3 legacy entrypoint isolation track.
- **Purpose**: bounded L3D proposal snapshot for review ownership and future CODEOWNERS wording.
- **Source-of-truth relationship**: supports `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md` (the primary L3D artifact). This report is a companion proposal artifact, not the source-of-truth itself.
- **Supersession**: may be superseded by a future L3E unknown-category owner decision round, a future CODEOWNERS implementation PR, or an enforcement proposal.
- **Cleanup**: no immediate cleanup required; future cleanup requires explicit user authorization.
- **Raw scan outputs**: temporary `/tmp` artifacts only, not committed.

## Remaining risks

- **Wording is advisory only and not enforced by CI.** Future agents or PR authors may ignore these ownership guidelines unless prompts or review processes actively reference them.
- **Actual CODEOWNERS handles are not decided.** The placeholder handles (`@REPO_OWNER_RUNTIME`, etc.) have no corresponding GitHub users or teams. Until the repo owner creates them, CODEOWNERS cannot be implemented.
- **Unknown entries still require owner decision.** Seven categories remain unclassified. Until the owner reviews them, agents must treat them as restricted, which may block legitimate work.
- **Reviewer checklist adoption is voluntary.** PR authors are not forced to include the checklist. Adoption depends on team convention and reviewer expectation.
- **Future CODEOWNERS implementation may require significant owner time.** Mapping 18 restricted legacy entries, 11 governance entries, and multiple API routers to specific reviewer groups is non-trivial.
- **Single-owner risk.** The current CODEOWNERS assigns everything to `@xupeng211`. If review responsibility remains centralized, the ownership taxonomy may not reduce review burden in practice.

## Recommended next step

Do not start automatically.

Recommended:
- Review and merge L3D if CI is green.
- Then decide separately whether **L3E** should classify the 7 unknown categories as docs-only owner decisions, completing the L3 taxonomy.
- Do not implement CODEOWNERS or enforcement until separately authorized.
- Do not start L4 API boundary reconciliation.
