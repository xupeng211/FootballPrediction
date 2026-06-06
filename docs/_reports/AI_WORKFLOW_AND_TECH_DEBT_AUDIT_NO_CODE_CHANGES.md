<!-- markdownlint-disable MD013 -->

# AI Workflow And Tech Debt Audit No Code Changes

- lifecycle: phase-artifact
- scope: audit-only, no code changes

## 1. Executive Summary

The AI workflow is established enough for bounded documentation, audit, and merge-only tasks. It already controls branches, PRs, safety impact, validation, destructive actions, and high-risk FotMob/DB/browser work. Risk remains in large legacy evidence sets, weak source-of-truth coverage for some domains, test quality, and technical debt that workflow rules can slow but not repair. Codex can work more independently only inside explicitly scoped, non-destructive tasks; feature, data, scraper, DB, and archive move work still need user confirmation and owner review.

## 2. Current AI Workflow Controls

| Control | Current status | Evidence | Risk if missing |
|---|---|---|---|
| no direct main work | working | `docs/CODEX_WORKFLOW.md`, gatekeeper protected-branch guard | unreviewed main mutations |
| branch-per-task | working | recent PR branches and workflow rules | mixed scopes |
| PR-per-task | working | PR body requirements | hidden changes |
| no automatic next phase | working | final reports say do not start automatically | runaway phase chains |
| no merge inside feature task | working | merge-only task separation | feature PRs hide cleanup |
| merge-only task separation | working | #1457-#1459 merge tasks | accidental edits |
| no destructive file operations | working | governance and archive rules | evidence loss |
| report/manifest/next-plan budget | improving | exact-path checker and docs policy | document sprawl |
| PR body safety impact | working | required PR sections | unclear risk |
| validation commands | working with host/container split | PR bodies and gatekeeper | false confidence |
| GitHub CI gate | working | `.github/workflows/production-gate.yml` | local-only checks |
| FotMob/DB/browser/proxy guards | strong but high-maintenance | `docs/data/FOTMOB_CURRENT_STATE.md`, gatekeeper proxy checks | unsafe data work |

## 3. Workflow Gaps

| Gap | Why it matters | Risk level | Recommended workflow rule |
|---|---|---|---|
| exact allowlist updates are manual | new allowed audit reports fail local checker first | medium | require same-task exact-path checker update when explicitly allowed |
| source-of-truth docs still missing | reports remain current by default | high | create planned source-of-truth docs before new feature phases |
| archive ownership not explicit per file | safe move cannot be proven by pattern | high | require owner-approved file list, no broad patterns |
| test quality not audited | many tests can assert plans not behavior | high | require behavior assertion review for generated tests |
| host validation differs from container | host lacks python/markdownlint/pandas | medium | final reports must separate host unavailable from container pass |
| PR gate does not prove full system quality | PR mode runs targeted gates, not every coverage guard | medium | label PR gate scope and run deeper gates for runtime work |
| debt ownership is unclear | cleanup can stall after reports | medium | every debt report must name next owner/review task |
| stale evidence conflict policy is manual | old reports can override active docs in AI context | medium | require active-doc citation before using old evidence |

## 4. Technical Debt Inventory

| Technical debt | Area | Evidence | Root cause | Severity | AI-preventable? | Recommended next action |
|---|---|---|---|---|---|---|
| documentation sprawl | docs | 615 docs files, 362 reports | AI phase artifacts | high | yes | continue owner-reviewed cleanup |
| stale reports | docs | Phase3B kept 8/8 candidates out of safe move | weak archive policy | high | partial | summarize before moving |
| duplicated plans | docs | 49 review, 6 next-plan, 13 decision reports | repeated planning phases | medium | yes | block report bundles |
| source-of-truth ambiguity | docs | planned `PROJECT_STATUS`, `DATA_SOURCE_STRATEGY`, schema docs | reports filled source role | high | yes | create scoped source docs |
| over-generated tests | tests | 500 test files, many phase-named tests | AI used tests as process proof | medium | yes | test debt audit |
| skipped/disabled tests | tests | 16 disabled test files | legacy failures and unsafe paths | medium | partial | classify disabled tests |
| brittle tests | tests | many phase-specific guard tests | implementation tied to phase metadata | medium | partial | consolidate behavior contracts |
| over-mocking | tests | 810 mock/nock/monkeypatch references | no stable integration seam | medium | partial | mark mock-only tests |
| low/misleading coverage | CI/tests | PR mode targeted gates, pytest cov optional note | incomplete coverage enforcement | high | partial | add scoped coverage policy |
| old generated files | docs/tests | reports/manifests and phase tests | artifact-first work | medium | yes | lifecycle inventory |
| legacy workflow complexity | devops | large `gatekeeper.sh` mode matrix | many safety gates accreted | high | no | refactor gatekeeper modules |
| CI weakness | CI | one Production Gate workflow, mode-specific checks | speed vs coverage tradeoff | medium | partial | declare required gate depth |
| scraper/FotMob uncertainty | data | active blockers in FotMob current state | legacy exploratory scraping | high | partial | keep FotMob paused |
| data-source boundary confusion | data/model | optional adapter and canonical schema planned | source drove schema discussion | high | partial | define canonical schema |
| dependency/environment drift | env | host commands missing; container passes | container-only toolchain | medium | partial | document validation surface |
| unclear archive ownership | docs | Phase3B requires owner review | no per-file owner map | medium | yes | owner-approved small move |

## 5. Root Cause Analysis

| Root cause | Description | Examples | Preventable by workflow? |
|---|---|---|---|
| AI generated too many artifacts | reports/manifests/tests used to show progress | 362 reports, 172 manifests | yes |
| AI continued to next phase without permission | phase chains grew before cleanup | next-plan and review chains | yes |
| AI created plans instead of closing work | planning artifacts replaced implementation decisions | Phase3A/3B needed to review plans | yes |
| weak source-of-truth discipline | active state stayed in reports | planned status/schema docs | yes |
| weak deletion/archive policy | no owner-reviewed move list existed | Phase3B found no automatic safe moves | yes |
| lack of test quality gate | tests can validate metadata, not behavior | phase-named tests | partial |
| incomplete CI enforcement | PR gate is not full quality proof | mode-specific gatekeeper | partial |
| legacy exploratory scraping work | FotMob work produced high-risk evidence | endpoint/probe reports | partial |
| evidence vs active docs unclear | old reports may conflict with current docs | FotMob evidence boundaries | yes |
| human urgency / feature-first work | cleanup followed feature exploration | delayed governance PRs | partial |

## 6. AI Workflow Rules to Prevent Future Debt

| Rule | Prevents which debt | Enforcement method | Should be CI-enforced? |
|---|---|---|---|
| one task = one branch = one PR | mixed scope | PR template and branch check | yes |
| no next phase unless user confirms | phase chains | final report rule | no |
| no new report unless explicitly allowed | doc sprawl | exact-path checker | yes |
| exact-path allowlist for reports | broad artifact sprawl | checker constants | yes |
| no destructive ops without approved list | evidence loss | PR body and diff guard | yes |
| no broad archive patterns | unsafe archive moves | owner-approved map | yes |
| no generated tests without behavior assertions | misleading tests | test review checklist | partial |
| no mock-only tests unless justified | over-mocking | PR body test impact | partial |
| no scraper/browser/proxy/cookie without authorization | data risk | gatekeeper/docs guard | yes |
| no DB/raw write without authorization | data corruption | make/gatekeeper rules | yes |
| Documentation Impact and Safety Impact required | hidden cost | PR template | yes |
| final report states deleted/moved/renamed | auditability | user-facing format | no |
| merge-only tasks must not modify files | merge safety | diff check before merge | yes |

## 7. What Workflow Rules Cannot Fix

| Technical debt | Why workflow rules are not enough | What real engineering work is needed |
|---|---|---|
| legacy gatekeeper complexity | shell mode matrix remains hard to maintain | modularize gatekeeper checks |
| insufficient real tests | rules cannot create meaningful coverage | design behavior/integration test suites |
| missing data contracts | docs cannot replace canonical schema | implement and enforce schemas |
| broken/uncertain collectors | authorization rules only stop unsafe runs | refactor collectors/adapters |
| model/data quality issues | workflow cannot prove predictive validity | data validation and model evaluation |
| environment drift | container policy helps but host remains inconsistent | standard dev bootstrap and tooling docs |

## 8. Recommended Next Steps

| Priority | Task | Why | Safe next action |
|---|---|---|---|
| P0 | AI-WORKFLOW-GUARDRAIL-HARDENING-FROM-AUDIT-NO-BUSINESS-CODE | convert audit findings into enforceable guardrails | update checker/templates only |
| P0 | TEST-DEBT-AUDIT-NO-RUNTIME-CHANGE | separate behavior tests from phase metadata tests | inventory tests and disabled files |
| P1 | SOURCE-OF-TRUTH-DOCS-CREATION-SCOPED | reduce report dependency | create missing planned source docs |
| P1 | CI-GUARDRAIL-SCOPE-DECLARATION | make PR gate meaning explicit | document and check gate tiers |
| P1 | DOCUMENTATION-CLEANUP-PHASE3C-OWNER-APPROVED-SMALL-ARCHIVE-MOVE-NO-DELETION | move only reviewed low-risk docs | owner-approved file list |
| P2 | GATEKEEPER-MODULE-REFACTOR-PLAN | reduce shell complexity | plan-only refactor proposal |
| P2 | CANONICAL-SCHEMA-CONTRACT-PLANNING | unblock data-source boundary | no-write schema planning |
| P3 | FOTMOB-RECONSTRUCTION-RESUME-ONLY-AFTER-EVIDENCE-STABLE | avoid reactivating high-risk paths | wait for stable docs and authorization |
