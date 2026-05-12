# L1 Discovery Candidates Extraction - Phase 5.04L1

## 1. Executive summary

本阶段不是重写 L1 discovery 引擎，也没有直接运行 `titan_discovery.js`。

本阶段从现有 `DiscoveryService` 中新增 candidates-only 的 `discoverCandidates()` 路径，目的是把 discovery candidates 和 DB persist 拆开。新的路径只做受控输入校验、可注入 fetch provider、解析、标准化 candidates 输出，不调用 `FixtureRepository.persist()`。

默认行为仍然是：

- 不触网
- 不写 DB
- 不写 `matches`
- 不写 `raw_match_data`
- 不启动 browser
- 不使用 proxy
- commit gate 继续 blocked

## 2. Implemented files

- `src/infrastructure/services/DiscoveryService.js`
- `scripts/ops/l1_discovery_safe_preview.js`
- `tests/unit/l1_discovery_safe_preview.test.js`
- `tests/unit/DiscoveryService.discoverCandidates.test.js`
- `Makefile`
- `AGENTS.md`
- `docs/_reports/L1_DISCOVERY_CANDIDATES_EXTRACTION_PHASE5_04L1.md`

## 3. What changed

- 新增 `DiscoveryService.discoverCandidates()` candidates-only path。
- `DiscoveryService` 的生产依赖支持 lazy load，并支持在 preview 构造中禁用 DB、browser、proxy、HTTP client、repository。
- `discoverCandidates()` 支持 fake `fetchLeagueFixtures` / `httpClient` dependency injection。
- `discoverCandidates()` 默认 `previewOnly=true`、`dryRun=true`、`allowNetwork=false`、`writeDb=false`。
- `discoverCandidates()` 不调用 `DiscoveryService.discover()`，不调用 `FixtureRepository.persist()`。
- L1 safe wrapper 新增 `controlled_candidates_preview` scope。
- 新增 `make data-l1-discovery-candidates-preview`。
- 即使传入 `NETWORK_AUTHORIZATION=yes`，Phase 5.04L1 CLI 仍 blocked，不执行 external network preview。

## 4. Why this lowers risk

原来 L1 discovery 的 fetch / parse / persist 是绑在一起的，AI 如果想看候选赛程，容易被迫接近 `titan_discovery.js` 大入口或 `DiscoveryService.discover()` 写库路径。

现在可以先拿 candidates，不写库。AI 不需要跑 `titan_discovery.js`，也不需要触碰 `FixtureRepository.persist()`。未来可以先审计 candidates，再由单独阶段决定是否授权写 `matches` seed。DB write、matches seed commit、真实 external network preview 都继续需要单独授权。

## 5. Validation

已运行：

- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/l1_discovery_safe_preview.test.js`
- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/DiscoveryService.discoverCandidates.test.js`
- `make data-l1-discovery-candidates-preview SOURCE=fotmob SCOPE=controlled_candidates_preview LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 CONCURRENCY=1 MAX_TARGETS=1 NETWORK_AUTHORIZATION=no`
- `make data-l1-discovery-commit SOURCE=fotmob SCOPE=controlled_candidates_preview LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 CONCURRENCY=1 MAX_TARGETS=1 CONFIRM_L1_DISCOVERY_COMMIT=1 || true`
- `docker compose -f docker-compose.dev.yml exec -T dev npm test`
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage`
- `git diff --check`
- `docker compose -f docker-compose.dev.yml exec -T dev npx eslint src/infrastructure/services/DiscoveryService.js scripts/ops/l1_discovery_safe_preview.js tests/unit/l1_discovery_safe_preview.test.js tests/unit/DiscoveryService.discoverCandidates.test.js --no-cache`
- `docker compose -f docker-compose.dev.yml exec -T dev npx prettier --check --ignore-unknown AGENTS.md Makefile src/infrastructure/services/DiscoveryService.js scripts/ops/l1_discovery_safe_preview.js tests/unit/l1_discovery_safe_preview.test.js tests/unit/DiscoveryService.discoverCandidates.test.js docs/_reports/L1_DISCOVERY_CANDIDATES_EXTRACTION_PHASE5_04L1.md`

验证结果：

- discoverCandidates unit tests passed.
- L1 safe wrapper tests passed.
- Makefile candidates preview passed with `external_network_used=false`, `candidate_count=0`, and `fetch_mode=not_executed`.
- commit gate remained blocked.
- `npm test` passed.
- `npm run test:coverage` passed.
- `git diff --check`, targeted ESLint, and targeted Prettier passed.
- DB row counts check after validation: `matches=2`, `bookmaker_odds_history=2`, `raw_match_data=2`, `l3_features=2`, `match_features_training=2`, `predictions=2`.
- `find tests/fixtures -maxdepth 1 -type d -name 'l1-config-*'` returned no residue.
- `git ls-files 'tests/fixtures/l1-config-*'` returned no tracked residue.
- `docs/_staging_preview` was absent.

`npm run test:integration` was skipped locally because that suite can cover browser / Chromium automation; this phase keeps local validation inside no-browser/no-network constraints and relies on PR CI / main CI for broader gates.

## 6. Recommended next phase

推荐 Phase 5.05L1：controlled L1 external network preview authorization。

建议约束：

- 仍不直接运行 `titan_discovery.js`
- 只走 `discoverCandidates()` safe path
- 用户显式授权 `source=fotmob`
- 默认只允许 `league_id=53 / season=2025/2026 / date=2026-05-10` 或用户明确范围
- `concurrency=1`
- `max_targets` 小范围
- 只输出 candidates stdout
- 不写 `matches`
- 不写 `raw_match_data`
- 不启动 browser / proxy
- 不训练 / 不预测

## 7. Explicit non-execution

本阶段未执行：

- external FotMob access
- network dry-run
- browser automation
- proxy runtime
- `titan_discovery.js` execution
- `DiscoveryService.discover()` execution
- `FixtureRepository.persist()` execution
- harvest
- ingest
- DB writes
- `raw_match_data` writes
- `matches` writes
- feature writes
- prediction writes
- staging writes
- file deletion
