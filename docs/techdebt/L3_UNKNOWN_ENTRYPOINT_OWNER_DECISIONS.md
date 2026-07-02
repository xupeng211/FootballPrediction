# L3 Unknown Entrypoint Owner Decisions

## Status

- Phase: L3E unknown entrypoint owner decisions
- Lifecycle: current-state governance document
- Runtime behavior changed: no
- Source files changed: no
- CI/workflow changed: no
- Gate enforcement changed: no
- CODEOWNERS changed: no
- GitHub labels created: no
- Deletion/move/rename: no
- Enforcement added: no
- L3A basis: `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md`
- L3B basis: `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md`
- L3C basis: `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md`
- L3D basis: `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md`

## Purpose

L3A identified legacy entrypoints. L3B confirmed the active whitelist and left **7 unknown categories** that could not be confidently classified from static evidence alone.

L3C proposed label semantics and guard wording. L3D proposed review ownership and future CODEOWNERS wording.

L3E now records **docs-only owner decisions** for each of the 7 unknown categories, applying conservative classification rules to close the last open taxonomy gap in the TECHDEBT-L3 track.

This proposal is **docs-only**. It does not run, migrate, delete, move, rename, or modify any entrypoint.

## Non-enforcement statement

This document explicitly does **not**:

- Modify runtime files (`src/**`, `tests/**`, `scripts/**`).
- Modify `.github/**` or CODEOWNERS.
- Modify AI Workflow Gate or Gatekeeper.
- Add CI enforcement checks.
- Create GitHub labels.
- Run, migrate, delete, move, or rename any entrypoint.
- Implement automated policy enforcement.

It is a **human and AI agent guidance proposal only**. Enforcement requires a separate, explicitly authorized future task.

---

## Decision rules

These conservative rules were applied to every unknown category:

1. **Active whitelist evidence required**: a category is only classified as `active-runtime`, `active-api-router`, `active-governance`, or `operational-guarded` if there is clear evidence (Dockerfile CMD, CI workflow invocation, Makefile guarded target, or router mount in `src/main.py`).

2. **Default to restricted-legacy**: if a category looks like an old pipeline, CLI tool, scraper, probe, health check, audit tool, or maintenance script — and is not mounted by the active runtime or invoked by CI — it defaults to `restricted-legacy`. Read-only by default. Modification, execution, migration, or deletion requires explicit user authorization.

3. **Archive path → archive-read-only**: any path under `archive_vault_2026/**` defaults to `archive-read-only`.

4. **Test infrastructure → test-only**: test runners, test suites, and test helpers default to `test-only`. They are active test infrastructure but are not production runtime entrypoints.

5. **Source modules with `__main__` → active-runtime with note**: if the primary purpose of a file is being imported by the active runtime (it lives in `src/` and is imported by `src/main.py` or its transitive dependencies), it remains `active-runtime`. The `__main__` blocks are self-test/demo utilities, not production entrypoints.

6. **Insufficient evidence → retain unknown-owner-decision**: if evidence is genuinely insufficient to classify, the category stays `unknown-owner-decision` (no-touch until owner review).

7. **No "probably active"**: uncertainty defaults to the more restrictive classification.

8. **No deletion decisions**: L3E does not decide to delete, move, or rename any file.

9. **No execution**: no entrypoint is executed to gather evidence. All evidence is static.

---

## Extracted unknown categories

These are the 7 categories extracted verbatim from `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` (lines 178–192).

| No. | Unknown category / path group | Source document | Current status | Evidence summary | Current risk |
|---|---|---|---|---|---|
| 1 | `scripts/ops/fotmob_*.py` (66 files) | L3B whitelist §Unknown | unknown-owner-decision | 66 FotMob investigation/probe scripts. Most have `_no_write`, `_dry_run`, or `_check` naming. Have `argparse` CLIs and `__main__` guards. Used for FotMob data ingestion investigation and planning. Not referenced by CI, Docker, or active runtime. | Medium — could trigger network requests or DB reads if executed |
| 2 | `scripts/ops/check_health.js` | L3B whitelist §Unknown | unknown-owner-decision | `package.json` `titan:check` references it. Script header: "TITAN 生产环境健康检查脚本" — checks env vars, DB connectivity, storage write permissions. | Medium — requires Docker/DB access |
| 3 | `scripts/ops/sentinel_watch.js` | L3B whitelist §Unknown | unknown-owner-decision | `package.json` `titan:watch` references it. Script header: "TITAN 哨兵监控系统 — 自动化满仓检测与安全停机系统". Operational monitoring with shutdown capability. | High — can trigger automated shutdown |
| 4 | `scripts/ops/audit_dataset.js` | L3B whitelist §Unknown | unknown-owner-decision | `package.json` `titan:audit` references it. Script header: "TITAN 数据资产审计系统 — 数据质量全面体检：物理清点、内容抽检、DB对齐、质量报告". May read or write DB. | Medium — potential DB access |
| 5 | `scripts/maintenance/integrity_guard.sh` | L3B whitelist §Unknown | unknown-owner-decision | `package.json` `status` references it. Script uses `docker-compose -f docker-compose.dev.yml` and `DB_USER`. Requires Docker and DB access. | Medium — requires Docker/DB |
| 6 | `scripts/test/run_test_suite.js` | L3B whitelist §Unknown | unknown-owner-decision | `package.json` `test`, `test:unit`, `test:affected`, `test:integration`, `test:coverage` all reference it. Canonical test runner for the project. | Low — test infrastructure |
| 7 | `src/core/**`, `src/utils/**`, `src/schemas/**` modules with `__main__` | L3B whitelist §Unknown | unknown-owner-decision | 9 files: `environment_detector.py`, `environment_validator.py`, `path_manager.py`, `types.py`, `safe_eval.py`, `typed_matcher.py`, `notifier.py`, `team_alias.py`, `match_features.py`. All have `if __name__ == "__main__"` self-test/demo blocks. Primary purpose of each module is being imported by active runtime. | Low — self-test blocks only |

Count: **7** unknown categories (matches L3B whitelist count).

---

## Owner decision matrix

| No. | Category | Proposed target label | Owner decision | Confidence | Default action | Future modification auth | Future runtime execution auth | Future deletion/move/rename auth | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `scripts/ops/fotmob_*.py` (66 files) | **restricted-legacy** | FotMob data investigation tools; tied to FotMob ingestion pipeline; not active runtime, not governance, not test-only | medium | Read-only by default | Explicit data ingestion authorization | Explicit data ingestion authorization | Dedicated cleanup PR with explicit authorization | Conservative: 66 files is too large a surface to auto-classify as active. Many are one-shot investigation artifacts. |
| 2 | `scripts/ops/check_health.js` | **restricted-legacy** | TITAN operational health check; requires Docker/DB access; not invoked by CI | medium | Read-only by default | Explicit operational authorization | Explicit operational authorization | Dedicated cleanup PR with explicit authorization | Conservative: operational tool for legacy TITAN pipeline. |
| 3 | `scripts/ops/sentinel_watch.js` | **restricted-legacy** | TITAN monitoring/shutdown system; can trigger automated shutdown; high-risk operational tool | high | Read-only by default | Explicit operational authorization | **Never** without explicit operational authorization + shutdown risk acknowledgement | Dedicated cleanup PR with explicit authorization | High risk: automated shutdown capability. |
| 4 | `scripts/ops/audit_dataset.js` | **restricted-legacy** | TITAN data audit tool; may access DB (read or write unconfirmed); conservative classification | medium | Read-only by default | Explicit data/audit authorization | Explicit data/audit authorization with DB access confirmation | Dedicated cleanup PR with explicit authorization | Conservative: DB access unconfirmed, treat as potentially data-touching. |
| 5 | `scripts/maintenance/integrity_guard.sh` | **restricted-legacy** | Maintenance integrity check; requires Docker and DB; not invoked by CI | medium | Read-only by default | Explicit maintenance authorization | Explicit maintenance authorization | Dedicated cleanup PR with explicit authorization | Conservative: requires Docker/DB. |
| 6 | `scripts/test/run_test_suite.js` | **test-only** | Canonical test runner; referenced by all `package.json` test scripts; active test infrastructure | high | Test-scope only | Test-scoped task authorization | Only via `make test` / `npm test` / `npm run test:*` | Dedicated test-infra PR with explicit authorization | Active test infrastructure. Not a production runtime entrypoint. |
| 7 | `src/core/**`, `src/utils/**`, `src/schemas/**` modules with `__main__` | **active-runtime** (modules) with **test-only** note for `__main__` blocks | Modules are part of active source tree imported by runtime. `__main__` blocks are self-test/demo utilities, not production entrypoints. | high | Modules: treat as active-runtime. `__main__` blocks: treat as test-only self-tests. | Modules: task-scoped authorization naming the path. `__main__` blocks: test-scoped authorization. | Modules: only via active runtime import. Standalone `python -m` execution: test-scope only. | Modules: require dedicated PR with explicit authorization. `__main__` blocks: may be modified as part of normal source changes. | The concern was about standalone execution; resolved: `__main__` blocks are benign self-tests. |

---

## Per-category decision records

### Decision 1: `scripts/ops/fotmob_*.py` (66 files)

- **Source evidence**: 66 FotMob investigation/probe scripts in `scripts/ops/`. Most have `_no_write`, `_dry_run`, or `_check` naming conventions, suggesting they were designed as read-only investigation tools. Many have `argparse` CLIs and `if __name__ == "__main__"` guards. Named patterns include: `controlled_json_probe`, `endpoint_runtime_candidate_probe`, `html_hydration_extraction_plan`, `match_id_discovery`, `registry_seed_dry_run`, `target_selection_db_dry_run`, `live_fetch_route_review`. None are referenced by CI workflows, Dockerfile, or `src/main.py`.
- **Proposed target label**: `restricted-legacy`
- **Owner decision**: These are FotMob data ingestion investigation and planning tools. They are not active runtime, not governance, not test-only. The `_no_write` naming suggests many are read-only, but some (`_dry_run`, `db_dry_run`, `dev_execution`) may have DB or network access. Given the volume (66 files) and the uncertainty about which have side effects, the conservative classification is restricted-legacy.
- **Confidence**: medium — the naming conventions strongly suggest investigation tools, but the sheer volume and variety preclude confident per-file classification in a docs-only phase.
- **Default action**: Read-only by default. Do not run, modify, migrate, delete, move, or rename without explicit authorization.
- **Allowed future operations**: Read (static analysis). Modification or execution requires explicit data ingestion authorization naming the specific files.
- **Required explicit authorization**: Data ingestion task authorization naming each affected file.
- **Validation needed before future change**: Per-file audit to confirm `_no_write` status; owner confirmation of which files are active investigation tools vs. one-shot artifacts.
- **Rollback / supersession note**: This decision may be refined by a future per-file audit. Until then, the entire glob is restricted-legacy.

### Decision 2: `scripts/ops/check_health.js`

- **Source evidence**: `package.json` `titan:check` script: `"titan:check": "node scripts/ops/check_health.js"`. Script header: "TITAN 生产环境健康检查脚本 — 自动检查：环境变量、数据库联通性、存储目录写入权限". Not listed in AGENTS.md as blocked. Not invoked by CI.
- **Proposed target label**: `restricted-legacy`
- **Owner decision**: This is an operational health check for the TITAN production pipeline. It reads environment variables and checks DB connectivity — side effects may include connection attempts. It is part of the legacy TITAN toolchain, not the active FastAPI runtime.
- **Confidence**: medium — clear operational purpose, but uncertain whether it is still actively used.
- **Default action**: Read-only by default. Do not run, modify, migrate, delete, move, or rename without explicit authorization.
- **Allowed future operations**: Read (static analysis). Execution requires explicit operational authorization.
- **Required explicit authorization**: Operational health-check authorization.
- **Validation needed before future change**: Confirm whether TITAN pipeline is still actively monitored; confirm DB credentials are still valid.
- **Rollback / supersession note**: If the TITAN pipeline is fully decommissioned, this script may become an archive candidate.

### Decision 3: `scripts/ops/sentinel_watch.js`

- **Source evidence**: `package.json` `titan:watch` script: `"titan:watch": "node scripts/ops/sentinel_watch.js"`. Script header: "TITAN 哨兵监控系统 (Sentinel Watch) — 自动化满仓检测与安全停机系统". Has shutdown capability.
- **Proposed target label**: `restricted-legacy`
- **Owner decision**: This is a high-risk operational tool with automated shutdown capability. It is part of the legacy TITAN pipeline. Not invoked by CI. The shutdown capability makes it the highest-risk entry in the unknown category list.
- **Confidence**: high — clear operational semantics with explicit risk (automated shutdown).
- **Default action**: Read-only by default. **Never** execute without explicit operational authorization and shutdown risk acknowledgement.
- **Allowed future operations**: Read (static analysis) only.
- **Required explicit authorization**: Explicit operational authorization + explicit shutdown risk acknowledgement.
- **Validation needed before future change**: Confirm shutdown scope (which services are affected); confirm whether TITAN monitoring is still active.
- **Rollback / supersession note**: If TITAN monitoring is decommissioned, this script should be archived. Do not run even for "testing" without explicit authorization.

### Decision 4: `scripts/ops/audit_dataset.js`

- **Source evidence**: `package.json` `titan:audit` script: `"titan:audit": "docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/audit_dataset.js"`. Script header: "TITAN 数据资产审计系统 — 数据质量全面体检：物理清点、内容抽检、DB对齐、质量报告". Runs inside Docker container. May access DB.
- **Proposed target label**: `restricted-legacy`
- **Owner decision**: This is a data audit tool for the TITAN pipeline. It runs inside Docker and may access the database. Whether it is read-only or can write is unclear from static scan. Conservative: treat as potentially data-touching.
- **Confidence**: medium — clear audit purpose, uncertain DB access level.
- **Default action**: Read-only by default. Do not run, modify, migrate, delete, move, or rename without explicit authorization.
- **Allowed future operations**: Read (static analysis). Execution requires explicit data audit authorization with DB access confirmation.
- **Required explicit authorization**: Explicit data audit authorization + confirmation of DB access level (read-only vs. write).
- **Validation needed before future change**: Audit the script to confirm it only performs SELECT queries; confirm DB credentials.
- **Rollback / supersession note**: If confirmed read-only, could be reclassified as operational-guarded. Until confirmed, restricted-legacy.

### Decision 5: `scripts/maintenance/integrity_guard.sh`

- **Source evidence**: `package.json` `status` script: `"status": "bash scripts/maintenance/integrity_guard.sh"`. Script uses `docker-compose -f docker-compose.dev.yml` and references `DB_USER`. Requires Docker and database access.
- **Proposed target label**: `restricted-legacy`
- **Owner decision**: This is a maintenance integrity check script. It requires Docker (references `docker-compose.dev.yml`) and database access (`DB_USER`). It is not invoked by CI. It is a maintenance tool, not active runtime or governance.
- **Confidence**: medium — clear maintenance purpose, uncertain whether actively used.
- **Default action**: Read-only by default. Do not run, modify, migrate, delete, move, or rename without explicit authorization.
- **Allowed future operations**: Read (static analysis). Execution requires explicit maintenance authorization.
- **Required explicit authorization**: Explicit maintenance authorization.
- **Validation needed before future change**: Confirm what integrity checks are performed; confirm DB access is read-only.
- **Rollback / supersession note**: If confirmed read-only and actively used, could be reclassified as operational-guarded.

### Decision 6: `scripts/test/run_test_suite.js`

- **Source evidence**: Referenced by 6 `package.json` scripts: `test`, `test:unit`, `test:affected`, `test:integration`, `test:coverage`, `test:coverage:recon-core`. This is the canonical test runner for the project's Node.js test suite.
- **Proposed target label**: `test-only`
- **Owner decision**: This is active test infrastructure. It is the primary test entrypoint for the Node.js side of the project. It should be treated as test-only: modifications require test-scoped authorization, and it must not be treated as a production runtime entrypoint.
- **Confidence**: high — clearly and unambiguously test infrastructure.
- **Default action**: Test-scope only. Read and execute within test tasks. Do not treat as production runtime source-of-truth.
- **Allowed future operations**: Read, execute via `make test` / `npm test` / `npm run test:*` with test authorization. Modify with test-scoped task authorization.
- **Required explicit authorization**: Test-scoped task authorization for modifications.
- **Validation needed before future change**: Standard test validation (run the test suite after changes).
- **Rollback / supersession note**: This is the least controversial decision in L3E. The file was only unknown because L3B wanted explicit confirmation.

### Decision 7: `src/core/**`, `src/utils/**`, `src/schemas/**` modules with `__main__`

- **Source evidence**: 9 files across `src/core/` (3), `src/utils/` (4), `src/schemas/` (1): `environment_detector.py`, `environment_validator.py`, `path_manager.py`, `types.py`, `safe_eval.py`, `typed_matcher.py`, `notifier.py`, `team_alias.py`, `match_features.py`. Each has `if __name__ == "__main__"` with self-test/demo code. These modules are primarily imported by the active runtime (e.g., `src/main.py` imports from `src.core`, `src.api.schemas` imports from `src.schemas`). The `__main__` blocks are incidental.
- **Proposed target label**: `active-runtime` (modules) with note: `__main__` blocks are self-test/demo utilities.
- **Owner decision**: These are active source modules whose primary purpose is being imported by the runtime. They should follow the `active-runtime` label for the modules themselves. The `__main__` blocks are self-test/demo utilities that do not constitute separate production entrypoints. Standalone execution (`python -m src.core.environment_detector` or `python src/core/environment_detector.py`) is a test/demo operation, not a production runtime path.
- **Confidence**: high — clear from module locations and import patterns.
- **Default action**: Modules: treat as active-runtime (task-scoped authorization for modification). `__main__` blocks: treat as test-only self-tests (no production significance).
- **Allowed future operations**: Modules: normal source modification with task authorization. `__main__` blocks: may be modified or removed as part of normal source changes. Standalone execution: test-scope only.
- **Required explicit authorization**: Task-scoped authorization for module changes (same as any `src/**` file). No special authorization needed for `__main__` block modifications.
- **Validation needed before future change**: Standard validation (tests, lint, type-check).
- **Rollback / supersession note**: If any specific `__main__` block is found to have production side effects (unlikely given static scan), that specific file should be reclassified. The general principle — source module `__main__` blocks are self-tests — stands.

---

## Future PR wording

### Unknown category already classified (post-L3E)

Copy this into PR bodies for tasks touching previously-unknown categories:

```markdown
## L3 Unknown Owner Decision Impact

| Item | Value |
|---|---|
| Previously unknown category touched | yes |
| L3E decision document checked | yes (`docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md`) |
| Category number and name | (e.g., Decision 6: `scripts/test/run_test_suite.js`) |
| Target label from L3E | (e.g., `test-only`) |
| Owner decision followed | yes |
| Additional authorization required | (yes/no — specify) |
| Runtime execution included | no |
| Deletion/move/rename included | no |
| L4 API boundary reconciliation included | no |
```

### Unknown category still unclassified

```markdown
## L3 Unknown Owner Decision Impact

This PR does not modify the unknown entrypoint category `(path)` because no L3E owner decision exists for it yet.

The category remains **no-touch** (unknown-owner-decision) until an explicit owner decision is recorded in `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md`.

If this task requires touching this category, stop and request an owner decision before proceeding.
```

---

## Future Claude Code prompt guard wording

Copy this block into Claude Code task prompts for L3E-aware unknown entrypoint handling:

```text
## L3E Unknown Entrypoint Owner Decisions (active for this task)

Before working on this task, read:
- `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` — active whitelist
- `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` — label semantics
- `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md` — review ownership
- `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md` — unknown category owner decisions (this document)

During this task, follow these rules:

1. **All 7 previously-unknown categories now have owner decisions.** See the Owner Decision Matrix in this document.
2. **6 categories classified as restricted-legacy**: `fotmob_*.py` (66 files), `check_health.js`, `sentinel_watch.js` (HIGH RISK — automated shutdown), `audit_dataset.js`, `integrity_guard.sh`, and also entries already in the restricted-legacy list. Do NOT run, modify, migrate, delete, move, or rename without explicit authorization.
3. **1 category classified as test-only**: `scripts/test/run_test_suite.js`. Use for test execution with test authorization. Do not treat as production runtime.
4. **1 category classified as active-runtime with test-only __main__ blocks**: `src/core/**`, `src/utils/**`, `src/schemas/**` modules. The modules are active source. The `__main__` blocks are self-tests.
5. **If you encounter a NEW unknown path** not covered by L3E decisions: stop, flag it, and request an owner decision. Do not assume.
6. **Do not run `sentinel_watch.js` under any circumstances** without explicit shutdown risk acknowledgement.
7. **Do not combine L3 with L4.**
8. **Do not implement CODEOWNERS or enforcement without separate authorization.**
```

### Short prompt variant

```text
L3E unknown decisions active. Read `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md`.
6 categories → restricted-legacy (do not touch). 1 → test-only. 1 → active-runtime + test-only __main__.
Do not run sentinel_watch.js. Flag new unknowns. Do not mix L3 with L4.
```

---

## Relationship to L3A / L3B / L3C / L3D

| Document | Phase | Role |
|---|---|---|
| `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` | L3A | Original inventory and classification framework |
| `docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md` | L3A | Scan evidence and risk map |
| `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` | L3B | Concrete whitelist with 7 unknown categories |
| `docs/_reports/L3B_ACTIVE_ENTRYPOINT_WHITELIST_CONFIRMATION_REPORT.md` | L3B | Confirmation snapshot |
| `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` | L3C | Label semantics and guard wording |
| `docs/_reports/L3C_LEGACY_LABEL_GUARD_WORDING_PROPOSAL_REPORT.md` | L3C | Label proposal report |
| `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md` | L3D | Review ownership and CODEOWNERS wording |
| `docs/_reports/L3D_REVIEW_OWNERSHIP_CODEOWNERS_WORDING_PROPOSAL_REPORT.md` | L3D | Review ownership report |
| `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md` | L3E | **This document** — unknown category owner decisions |
| `docs/_reports/L3E_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS_REPORT.md` | L3E | Bounded decision report |

## References

- `AGENTS.md` — agent workflow hardening rules
- `CLAUDE.md` — project instructions and safety discipline
- `.github/workflows/production-gate.yml` — CI pipeline definition
- `package.json` — script references for unknown categories

## Next recommended task

Do not start automatically.

Recommended next task only after user confirmation:

- Review and merge L3E if CI is green.
- This completes the TECHDEBT-L3 taxonomy (all 5 phases: L3A inventory, L3B whitelist, L3C labels, L3D ownership, L3E unknown decisions).
- Future task may propose docs-only enforcement design for the now-fully-classified L3 taxonomy.
- Do not implement enforcement, CODEOWNERS, or L4 without separate authorization.
