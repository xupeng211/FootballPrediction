# L3E Unknown Entrypoint Owner Decisions Report

## Snapshot

- Main head: `b5baf368a8917c2a1426fe469049acb037b1185f`
- Main CI run: `28612711860`
- Main CI conclusion: success
- Branch: `techdebt/l3e-unknown-entrypoint-owner-decisions`
- Scan date: 2026-07-03
- Task type: docs-only

## Source documents

- `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` — L3A planning (merged in #1685)
- `docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md` — L3A scan report (merged in #1685)
- `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` — L3B whitelist (merged in #1686)
- `docs/_reports/L3B_ACTIVE_ENTRYPOINT_WHITELIST_CONFIRMATION_REPORT.md` — L3B report (merged in #1686)
- `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` — L3C label proposal (merged in #1687)
- `docs/_reports/L3C_LEGACY_LABEL_GUARD_WORDING_PROPOSAL_REPORT.md` — L3C report (merged in #1687)
- `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md` — L3D ownership proposal (merged in #1688)
- `docs/_reports/L3D_REVIEW_OWNERSHIP_CODEOWNERS_WORDING_PROPOSAL_REPORT.md` — L3D report (merged in #1688)
- `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md` — L3E owner decisions (this PR)

## Method

- L3A/L3B/L3C/L3D document review: read all eight source documents to understand the full classification chain.
- Unknown category extraction: extracted the 7 unknown-owner-decision categories from `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` lines 178–192.
- Static evidence recheck: ran `ls`, `head -5`, and `grep` on each unknown path to gather additional static evidence without executing anything.
- Conservative classification: applied 9 decision rules (see L3E document §Decision rules) prioritizing restrictive classifications when evidence was insufficient.
- Per-category decision records: wrote detailed decisions with source evidence, proposed label, confidence, default action, allowed operations, authorization requirements, validation needs, and rollback notes.
- No runtime execution, no Docker, no DB, no secrets, no gate modification, no CODEOWNERS modification.

## Unknown category extraction result

| Item | Value |
|---|---|
| Expected unknown categories | 7 |
| Actual extracted unknown categories | 7 |
| Source document | `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` §Unknown / needs owner decision (lines 178–192) |
| Extraction status | **match — all 7 extracted** |

## Proposed owner decisions summary

| No. | Category | Proposed target label | Confidence | Default action | Explicit authorization needed | Enforcement status |
|---|---|---|---|---|---|---|
| 1 | `scripts/ops/fotmob_*.py` (66 files) | `restricted-legacy` | medium | Read-only | Data ingestion authorization | Advisory (docs-only) |
| 2 | `scripts/ops/check_health.js` | `restricted-legacy` | medium | Read-only | Operational authorization | Advisory (docs-only) |
| 3 | `scripts/ops/sentinel_watch.js` | `restricted-legacy` | high | Read-only (HIGH RISK) | Operational + shutdown risk acknowledgement | Advisory (docs-only) |
| 4 | `scripts/ops/audit_dataset.js` | `restricted-legacy` | medium | Read-only | Data/audit authorization + DB access confirmation | Advisory (docs-only) |
| 5 | `scripts/maintenance/integrity_guard.sh` | `restricted-legacy` | medium | Read-only | Maintenance authorization | Advisory (docs-only) |
| 6 | `scripts/test/run_test_suite.js` | `test-only` | high | Test-scope only | Test-scoped task authorization | Advisory (docs-only) |
| 7 | `src/core/**`, `src/utils/**`, `src/schemas/**` modules with `__main__` | `active-runtime` (modules) + `test-only` note for `__main__` blocks | high | Modules: active-runtime. `__main__` blocks: test-only. | Task-scoped authorization (modules). Test-scope (standalone execution). | Advisory (docs-only) |

## Key decisions

1. **6 of 7 unknown categories classified as restricted-legacy.** The FotMob probe scripts, health check, sentinel watch, audit tool, and integrity guard are all operational tools tied to the legacy TITAN/FotMob pipeline. None are invoked by CI or mounted by the active runtime. Conservative classification: read-only by default, requiring explicit authorization for any action.

2. **`sentinel_watch.js` flagged as highest-risk.** This script has automated shutdown capability. It is the only L3 entry with a "**Never** execute without explicit authorization" rule. Even "testing" it requires shutdown risk acknowledgement.

3. **`run_test_suite.js` classified as test-only.** This was the easiest decision — it is unambiguously the canonical Node.js test runner, referenced by 6 `package.json` test scripts. It was only unknown because L3B wanted explicit confirmation.

4. **`src/**` `__main__` blocks resolved as benign self-tests.** The 9 source modules with `__main__` blocks are active-runtime modules whose primary purpose is being imported. The `__main__` blocks are self-test/demo utilities, not production entrypoints. Standalone execution is a test/demo operation.

5. **`fotmob_*.py` (66 files) kept as a single glob for now.** Per-file classification of 66 FotMob probe scripts would require execution or deep code review, which is beyond docs-only scope. The entire glob is restricted-legacy. A future per-file audit could refine this.

6. **No category retained as unknown-owner-decision.** All 7 categories had sufficient static evidence for a conservative classification. The L3 unknown category list is now empty.

7. **L3 taxonomy is now complete.** With L3E, every entrypoint category identified by L3A has a label (L3C), an ownership area (L3D), and — for the 7 previously unknown — an owner decision (L3E). The TECHDEBT-L3 documentation chain is structurally complete.

8. **All decisions are conservative.** Where evidence was insufficient for an active classification, the default was restricted-legacy. No file was classified as "probably active" or "probably safe to run."

9. **No deletion, migration, or execution decisions.** L3E is purely classification. All files remain in place with their new labels.

10. **L3E closes the last open taxonomy gap.** The 7 unknown categories were the only remaining unclassified entries in the L3B whitelist. The full entrypoint population is now labeled.

## Non-decisions

- **No runtime change.** No source file is modified, executed, or imported differently.
- **No CI enforcement decision.** Labels are advisory.
- **No CODEOWNERS implementation.** No `.github/CODEOWNERS` changes.
- **No GitHub label creation.**
- **No branch protection change.**
- **No reviewer automation change.**
- **No file deletion, move, or rename.** All 66 fotmob scripts, 4 TITAN tools, 1 test runner, and 9 source modules remain in place.
- **No per-file audit of `fotmob_*.py`.** The glob classification is intentionally coarse.
- **No L4 API boundary decision.**

## Report Lifecycle

- **Owner**: TECHDEBT-L3 legacy entrypoint isolation track.
- **Purpose**: bounded L3E proposal snapshot for unknown entrypoint owner decisions.
- **Source-of-truth relationship**: supports `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md` (the primary L3E artifact). This report is a companion proposal artifact, not the source-of-truth itself.
- **Supersession**: may be superseded by a future per-file audit of `fotmob_*.py`, a future enforcement design proposal, or future CODEOWNERS implementation.
- **Cleanup**: no immediate cleanup required; future cleanup requires explicit user authorization.
- **Raw scan outputs**: temporary `/tmp` artifacts only, not committed.

## Remaining risks

- **`fotmob_*.py` glob is coarse.** 66 files are classified as a single restricted-legacy glob. Some may be genuinely read-only investigation artifacts that could be reclassified as operational-guarded or archive-read-only after per-file audit. Until then, the conservative glob stands.
- **`audit_dataset.js` DB access level is unconfirmed.** It is classified as restricted-legacy because static scan cannot confirm whether it performs only SELECT queries. If confirmed read-only, it could be reclassified.
- **`sentinel_watch.js` shutdown scope is unverified.** The exact services affected by the automated shutdown are not confirmed from static scan alone.
- **Wording is advisory only.** Agents may ignore these classifications unless prompts reference them.
- **Enforcement requires separate authorization.** No CI gate, required review, or automated check enforces these classifications.

## Recommended next step

Do not start automatically.

Recommended:
- Review and merge L3E if CI is green.
- This completes the TECHDEBT-L3 documentation chain (L3A → L3B → L3C → L3D → L3E). All entrypoints are now classified with labels, ownership areas, and — for previously unknown categories — owner decisions.
- Future task may propose docs-only enforcement design for the L3 taxonomy.
- Do not implement enforcement, CODEOWNERS, or L4 without separate authorization.
