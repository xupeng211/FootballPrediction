# L1 Controlled Network Candidates Preview - Phase 5.05L1

## 1. Executive summary

Phase 5.05L1 将 L1 candidates preview 从 no-network plan-only 提升为显式授权后的 controlled external network preview。

本阶段仍不运行 `titan_discovery.js`，不调用 `DiscoveryService.discover()`，不调用 `FixtureRepository.persist()`，不写 DB，不写 `matches` / `raw_match_data`，不启动 browser / proxy。

## 2. Implemented files

- `src/infrastructure/services/DiscoveryService.js`
- `scripts/ops/l1_discovery_safe_preview.js`
- `tests/unit/DiscoveryService.discoverCandidates.test.js`
- `tests/unit/l1_discovery_safe_preview.test.js`
- `Makefile`
- `AGENTS.md`
- `docs/_reports/L1_CONTROLLED_NETWORK_CANDIDATES_PREVIEW_PHASE5_05L1.md`

## 3. Why this is safe

- `discoverCandidates()` 与 `FixtureRepository.persist()` 保持分离，候选发现只返回 candidates。
- 外网 preview 必须显式传入 `NETWORK_AUTHORIZATION=yes`，且只能通过 `data-l1-discovery-candidates-network-preview`。
- scope 固定为 `controlled_candidates_preview`，source 固定为 `fotmob`。
- `CONCURRENCY=1`，`MAX_TARGETS<=10`。
- DB write、matches write、raw_match_data write 全部固定为 false。
- browser / proxy runtime 固定 disabled。
- `data-l1-discovery-commit` 仍 blocked。
- 网络错误、403、429、captcha 或 block 信号停止，不自动 retry。

## 4. Validation

本地验证通过：

- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/DiscoveryService.discoverCandidates.test.js`
- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/l1_discovery_safe_preview.test.js`
- `make data-l1-discovery-candidates-preview SOURCE=fotmob SCOPE=controlled_candidates_preview LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 CONCURRENCY=1 MAX_TARGETS=1 NETWORK_AUTHORIZATION=no`
- `make data-l1-discovery-commit SOURCE=fotmob SCOPE=controlled_candidates_preview LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 CONCURRENCY=1 MAX_TARGETS=1 CONFIRM_L1_DISCOVERY_COMMIT=1 || true`
- `docker compose -f docker-compose.dev.yml exec -T dev npm test`
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage`
- `git diff --check`
- `docker compose -f docker-compose.dev.yml exec -T dev npx eslint src/infrastructure/services/DiscoveryService.js scripts/ops/l1_discovery_safe_preview.js tests/unit/l1_discovery_safe_preview.test.js tests/unit/DiscoveryService.discoverCandidates.test.js --no-cache`
- `docker compose -f docker-compose.dev.yml exec -T dev npx prettier --check --ignore-unknown AGENTS.md Makefile src/infrastructure/services/DiscoveryService.js scripts/ops/l1_discovery_safe_preview.js tests/unit/l1_discovery_safe_preview.test.js tests/unit/DiscoveryService.discoverCandidates.test.js docs/_reports/L1_CONTROLLED_NETWORK_CANDIDATES_PREVIEW_PHASE5_05L1.md`

No-network preview returned `external_network_used=false`, `candidate_count=0`, and all DB / persist / browser / proxy write indicators false.

Commit gate remained blocked.

Safety review passed:

- no `tests/fixtures/l1-config-*` residue
- no `docs/_staging_preview` directory
- DB row counts unchanged: `matches=2`, `bookmaker_odds_history=2`, `raw_match_data=2`, `l3_features=2`, `match_features_training=2`, `predictions=2`

## 5. Actual controlled network preview result

本阶段代码合并前不执行真实外网 preview。若 PR 合并且 main push CI 成功，将在 main 上按授权范围执行一次：

- source: `fotmob`
- league_id: `53`
- season: `2025/2026`
- date: `2026-05-10`
- concurrency: `1`
- max_targets: `10`

合并前实际结果：未执行真实外网 preview；原因是本阶段要求真实 network preview 仅在 PR 合并、main push CI 成功、main 工作区 clean 且 DB 行数复核通过后执行。

## 6. Recommended next step

如果 preview 成功发现目标 candidates，推荐 Phase 5.06L1：controlled matches seed commit planning。

Phase 5.06L1 仍不写 `raw_match_data`，只规划是否将 candidates 写入 `matches` seed；需要用户明确授权，并需要 backup / rollback / upsert policy。

如果 preview 失败，则停止，不绕过，不启用 browser/proxy，由用户决定是否调整范围、retry 或单独授权后续能力。

## 7. Explicit non-execution

- no titan_discovery execution
- no DiscoveryService.discover execution
- no FixtureRepository.persist
- no DB writes
- no matches writes
- no raw_match_data writes
- no browser/proxy
- no harvest/ingest
- no training/prediction
