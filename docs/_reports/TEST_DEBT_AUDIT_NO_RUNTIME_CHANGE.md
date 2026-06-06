<!-- markdownlint-disable MD013 -->

# Test Debt Audit No Runtime Change

- lifecycle: phase-artifact
- scope: audit-only, no runtime change, no test repair
- line-count exception: required audit tables and static inventory exceed the default phase-report budget

## 1. Executive Summary

The current test system is useful, but it should not be treated as a full proof of product quality. It can prove many
guardrails, pure helper behaviors, parser boundaries, and no-write workflow constraints. It cannot prove full business
correctness, model quality, FotMob safety, DB write safety, scraper safety, or end-to-end data-source reliability.

The largest test debt is not one failing suite; it is signal quality. The repository has many tests that validate
process, phase artifacts, no-write reports, manifests, mocks, and governance metadata. Those tests are valuable as
safety rails, but they are not the same as behavior tests against real system paths.

Static audit found a large phase/process footprint: 498 tracked files under `tests/`, 455 tracked Python/JavaScript
source files, 233 phase-named files, 169 governance/process-named files, 16 disabled test files, 15 skip/skipif hits,
0 xfail hits, 578 mock/monkeypatch/patch hits across 46 files, 0 `assert True` hits, and 2 `pass` hits. Container
`pytest --collect-only -q` collected 819 pytest items successfully, but collect-only proves import/collection shape,
not assertion value.

Do not enter broad business development on the strength of the current test count alone. The next safe step is
classification, not repair: separate behavior tests from governance/process tests, identify mock-only coverage, and
decide which missing integration contracts require real engineering work.

## 2. Test Inventory

Counts use `git ls-files tests` for tracked file inventory and `rg` for static hit counts.

| Item | Count | Notes |
| --- | ---: | --- |
| tests total files | 498 | tracked files under `tests/` |
| unit test files | 413 | tracked files under `tests/unit` |
| integration test files | 13 | tracked files under `tests/integration` |
| e2e test files | 0 | no tracked `tests/e2e` files |
| generated / phase-named test files | 233 | filename/path hit for phase, ADG, no_write, preflight, review, plan, manifest, gate, L1/L2, pageProps, or raw_match_data |
| disabled test files | 16 | `*.disabled` tracked files |
| skip / skipif hits | 15 | 3 files contain `pytest.mark.skip`, `skipif`, or `pytest.skip` |
| xfail hits | 0 | no static `xfail` hits found |
| mock / monkeypatch / patch hits | 578 | 46 files contain mock, monkeypatch, MagicMock, or `patch(` |
| assert True hits | 0 | no static `assert True` hits found |
| TODO / FIXME hits | 0 | no static TODO/FIXME hits in tests |
| weak `pass` hits | 2 | 2 files contain lines ending in `pass` |
| pytest collect-only | 819 items | container `pytest --collect-only -q` passed; host failed due missing pandas |

## 3. Test Debt Categories

| Test debt | Area | Evidence | Risk | Severity | AI-preventable? | Recommended next action |
| --- | --- | --- | --- | --- | --- | --- |
| Over-generated tests | tests/unit, FotMob phases | 233 phase-named tracked files | test count can look like progress without business coverage | high | yes | classify phase/process tests separately |
| Phase-named tests | FotMob, L1/L2, pageProps | ADG/no-write/preflight/review/plan filenames dominate samples | tests can preserve old phase behavior as current truth | high | yes | map phase tests to current source-of-truth docs |
| Process/document/governance tests | docs/checker workflow | 169 governance/process-named files | CI can prove rules while leaving business behavior untested | medium | yes | label governance tests in PR bodies |
| Mock-heavy tests | unit tests and fixtures | 578 hits across 46 files | mock behavior can diverge from real runtime paths | high | partial | audit top mock-heavy files |
| Monkeypatch-heavy tests | Python unit tests | 72 monkeypatch hits across 2 files | patched globals can hide integration failures | medium | partial | require justification for global monkeypatch |
| Skip / skipif usage | Python tests | 15 hits across 3 files | skipped behavior may be forgotten | medium | partial | require owner and unblock condition |
| xfail usage | tests | 0 hits | no immediate xfail debt found | low | yes | keep xfail policy explicit |
| Disabled tests | legacy archive and integration | 16 `*.disabled` files | disabled tests are invisible to CI quality claims | high | partial | classify disabled tests before deletion or rewrite |
| Weak assertions | integration/unit | 2 `pass` hits; 0 `assert True` hits | empty pass blocks can mask no-op paths | low | yes | review weak assertion files |
| Brittle tests | phase metadata tests | many `test_manifest_*`, `test_report_*`, `test_next_phase_*` names | wording/metadata changes can break tests without behavior change | medium | yes | keep metadata tests scoped to governance |
| Flaky risk | integration and browser-adjacent tests | disabled `omni_live_probe`, browser legacy tests, mock browser tests | real environment may differ from mocked/disabled behavior | high | partial | isolate live/browser tests behind explicit authorization |
| Environment-dependent integration tests | integration and conftest | host collect-only fails missing pandas; container passes | host/CI parity can be misunderstood | medium | partial | report host vs container separately |
| Misleading coverage | coverage report evidence | old coverage hotfix targeted branch threshold; `TEST_SUMMARY` cites mock strategy | coverage can measure process or mocks, not product quality | high | partial | run coverage truth audit |
| Tests detached from business behavior | service/mock summary | `tests/unit/TEST_SUMMARY.md` says service layer used simulated tests due dependencies | green tests may not exercise original code | high | no | design behavior contracts and integration seams |
| Tests only prove CI gate | gate/checker tests | governance checker tests and Production Gate pass | gate pass is scoped, not full-system proof | medium | yes | require CI Gate Scope in PRs |
| Cannot prove FotMob / DB / data-source safety | high-risk paths | many no-write/no-network tests and disabled browser/scraper tests | safety restrictions are guards, not live reliability proof | high | partial | keep FotMob/DB/browser blocked unless explicitly authorized |

## 4. AI-Caused or AI-Amplified Test Debt

| Debt type | How AI caused or amplified it | Evidence | Workflow prevention |
| --- | --- | --- | --- |
| Phase test proliferation | AI created a test for each phase/report/manifest to prove progress | 233 phase-named tracked files | no new tests unless they verify real behavior or exact governance scope |
| Mock-only confidence | AI used mocks to avoid unsafe DB/network/browser paths | 578 mock-related hits | mock-only tests must state what real path remains unproven |
| Metadata tests | AI asserted report, manifest, next-phase, and safety strings | many `test_report_*`, `test_manifest_*`, `test_next_phase_*` names | separate governance/process tests from behavior tests |
| Skip debt | AI can defer hard dependencies through skip conditions | 15 skip hits | skips need owner and unblock condition |
| Test count as progress | AI may treat many collected tests as proof of quality | 819 collected items, many process tests | PRs must report behavior-test count separately from governance-test count |
| Governance as business proof | AI can use checker/Production Gate pass to claim system readiness | checker tests pass but no runtime repair happened | CI Gate Scope must say what is not proven |
| Missing distinction of test type | AI often mixes behavior, process, and artifact tests in one summary | `TEST_SUMMARY.md` mixes mock strategy with business confidence | test PRs must classify test intent and lifecycle |

## 5. What Current Tests Prove / Do Not Prove

| Test type | Can prove | Cannot prove | Risk |
| --- | --- | --- | --- |
| Governance checker tests | exact docs/checker allowlist and no-sprawl rules | business correctness or model quality | false confidence if presented as quality gate |
| Documentation workflow tests | reports/manifests contain required fields and safety claims | claims are true in runtime | metadata can drift from behavior |
| Unit tests | pure helpers, validators, parser branches, mocked safety guards | integrated DB/network/browser/runtime behavior | mocks hide missing seams |
| Integration tests | selected container or component wiring where enabled | full end-to-end production quality | disabled/live-adjacent tests reduce confidence |
| Generated / phase tests | historical phase constraints and no-write boundaries | current product behavior or source-of-truth correctness | stale phase contracts can block cleanup |
| Mock-heavy tests | code response to controlled fake inputs | real service behavior under real dependencies | fake inputs can encode the implementation |
| Skipped / disabled tests | known dependency gaps or unsafe legacy paths | passing behavior | invisible failure surface |
| CI Production Gate | scoped gatekeeper checks and Docker build validation | full-system test coverage, model validity, data quality, or live source safety | green gate can be overinterpreted |
| pytest collect-only | import and collection shape in container | assertion strength, correctness, or integration reliability | collected item count can inflate confidence |

## 6. Root Cause Analysis

| Root cause | Description | Example | Workflow preventable? |
| --- | --- | --- | --- |
| AI over-generated tests | tests created per phase/artifact rather than per behavior | ADG/no-write/preflight review tests | yes |
| Missing test quality gate | no rule requires behavior assertion classification | metadata tests mixed with business tests | yes |
| Missing behavior assertion standard | tests can assert artifact presence, not domain outcome | `test_report_exists`, `test_manifest_exists` style names | yes |
| Excessive mocks | unsafe integrations were replaced with mocks without follow-up seams | 46 mock-related files | partial |
| Legacy tests not cleaned | old disabled JS/browser tests remain under tests | 16 `*.disabled` files | partial |
| CI speed vs completeness tradeoff | PR gate favors scoped checks and container build | Production Gate does not run all possible quality gates | partial |
| Environment dependency complexity | host lacks pandas/python/markdownlint but container passes | host collect-only fails, container collect-only passes | partial |
| FotMob/data-source risk | live source and browser tests are constrained for safety | no-write/no-network test chains | partial |
| Business boundary ambiguity | unclear contracts make behavior tests hard | service tests described as simulated due dependencies | no |
| Source-of-truth ambiguity | old phase docs/tests preserve historical state | phase tests reference reports/manifests | yes |

## 7. Workflow Rules to Prevent Future Test Debt

| Suggested rule | Prevents which debt | Enforcement | CI-enforced? |
| --- | --- | --- | --- |
| AI must not generate tests without real behavior assertions | weak/process-only test growth | PR test impact table | partial |
| Mock-only tests must explain why real path is unavailable | false mock confidence | PR body and review checklist | no |
| Every new test states the real behavior being protected | metadata-only tests | test file comment or PR table | partial |
| skip/xfail requires issue, owner, or unblock condition | forgotten disabled behavior | static grep checker | yes |
| generated tests declare source and lifecycle | orphan generated tests | repository hygiene checklist | yes |
| test count is not a completion metric | fake progress | PR template wording | no |
| Every test PR separates behavior tests from governance/process tests | mixed quality claims | PR body section | partial |
| Coverage increases must state whether they cover business logic or process code | misleading coverage | coverage PR template | partial |
| Test repair tasks must not include business changes | mixed risk | diff path guard | yes |
| High-risk data-source tests must not run scraper/browser/DB write | unsafe validation | gatekeeper and explicit authorization | yes |

## 8. What Workflow Rules Cannot Fix

| Test debt | Why workflow rules are not enough | Real engineering work needed |
| --- | --- | --- |
| Missing real integration tests | rules can require them but not create stable seams | design DB/service integration fixtures and contracts |
| Missing data contracts | tests need canonical schemas to assert against | implement canonical match/data contracts |
| FotMob/data-source instability | prompts cannot make live sources stable or authorized | build safe adapters and source-fidelity strategy |
| DB test environment complexity | policy cannot replace reliable isolated DB setup | create repeatable container DB fixtures |
| Model effectiveness validation | CI cannot infer predictive quality from unit tests | define model evaluation datasets and metrics |
| Business boundary ambiguity | tests cannot validate undefined behavior | clarify domain boundaries and ownership |
| Historical test structure sprawl | rules stop new debt but old tests remain | classify, consolidate, and refactor legacy suites |
| Old tests requiring human judgment | archive/delete decisions require owner review | owner-reviewed cleanup and rewrite plan |

## 9. Recommended Next Steps

| Priority | Task | Purpose | Safe next action |
| --- | --- | --- | --- |
| P0 | TEST-DEBT-CLASSIFICATION-NO-RUNTIME-CHANGE | classify tests as behavior, governance/process, mock-heavy, disabled, or legacy | produce classification table only |
| P0 | TEST-GOVERNANCE-RULES-HARDENING-NO-BUSINESS-CODE | add workflow rules for behavior assertions, skip policy, and mock-only justification | update docs/checker only |
| P1 | MOCK-HEAVY-TEST-AUDIT-NO-RUNTIME-CHANGE | inspect top mock-heavy files and identify unproven runtime paths | no code changes |
| P1 | DISABLED-SKIPPED-TEST-AUDIT-NO-RUNTIME-CHANGE | classify 16 disabled files and 15 skip hits | no delete, no repair |
| P1 | COVERAGE-TRUTH-AUDIT-NO-RUNTIME-CHANGE | identify whether coverage measures business logic or process/governance code | no threshold changes |
| P2 | BEHAVIOR-TEST-ROADMAP-NO-RUNTIME-CHANGE | plan true behavior/integration test seams | no implementation |
| P2 | TEST-FIXTURE-AND-DB-SEAM-PLANNING-NO-RUNTIME-CHANGE | plan isolated DB/service fixtures | no DB write |
| P3 | SMALL-SCOPED-TEST-REPAIR-OWNER-APPROVED | repair one classified test cluster at a time | only after owner approval |

Do not start broad test repair, FotMob reconstruction, or business refactoring from this audit.
