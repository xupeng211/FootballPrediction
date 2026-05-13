# L1 Legacy Entrypoint Deprecation Migration Plan - Phase 5.10G

## 1. Executive summary

项目原本就有一套可用的 L1 discovery engine，核心能力继续保留。

真正需要治理的不是 engine core，而是几个历史遗留的大入口：它们可能直接触网、批量跑、多联赛跑、启 browser/proxy，或者直接写库。Phase 5.03L1 到 Phase 5.09L1 已经补出一条更安全的默认链路：

- L1 safe preview wrapper
- `DiscoveryService.discoverCandidates()`
- controlled external network candidates preview
- matches seed commit planning / authorization / preflight / exact execution

本阶段只做 deprecation / migration plan，不删除旧入口，不改生产 runtime，不写 DB。

## 2. Keep vs deprecate principle

原则很简单：

- 不拆发动机。`DiscoveryService`、parser、mapper、validator、config manager、HTTP/browser/persist 等核心件继续保留。
- 只治理旧大开关。高风险 legacy CLI / npm / Makefile entrypoints 对 agents 默认 deprecated。
- 默认走新 safe workflow。L1 发现与 matches seed 现在已经有 `data-l1-*` 受控替代路径。
- 老入口先标记为 legacy/admin-only，不急着删。
- 删除必须等迁移 inventory、引用清理、CI 证明无依赖、且用户明确批准。

## 3. Legacy entrypoint inventory

| entrypoint                                          | location                                                      | role                                     | risk        | why risky                                                                                                                                                                               | replacement                                                             | recommended action                                             |
| --------------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------- |
| `titan_discovery`                                   | `scripts/ops/titan_discovery.js`                              | 原始 L1 discovery CLI                    | High        | 支持 `--all` / `--all-leagues` / `--tier` / `--full-sync`，并直接调用 `DiscoveryService.discover()`；registry 标记 `accesses_network=true`、`writes_db=true`、`dry_run_trust_level=low` | `data-l1-discovery-candidates-network-preview` + `discoverCandidates()` | agent-blocked legacy；engine core keep                         |
| `run_production` / `npm start` / `make dev-harvest` | `scripts/ops/run_production.js`, `package.json`, `Makefile`   | 生产 harvest 大入口                      | High        | 直接构造 `ProductionHarvester` 并 `harvester.run(...)`；registry 标记 `writes_db=true`、`bulk_risk=high`                                                                                | 暂无直接 safe 替代；未来按 source/scope 拆小                            | admin-only legacy                                              |
| `total_war_pipeline` / `npm run titan:total-war`    | `scripts/ops/total_war_pipeline.js`, `package.json`           | Discovery/Harvest/Recon/Smelt 超级编排器 | High        | 自带 runtime dir、child process、阶段编排；registry 标记 `accesses_network=true`、`writes_db=true`、`deprecation_status=deprecation_candidate`                                          | 暂无；未来按子能力拆分                                                  | admin-only legacy，后续 removal candidate                      |
| `odds_harvest_pipeline` / `npm run odds:harvest`    | `scripts/ops/odds_harvest_pipeline.js`, `package.json`        | 赔率外网抓取与 DB 写入                   | High        | 直接依赖 `playwright` 和 `pg`，访问 results URL 并落赔率数据；registry 标记 `writes_db=true`、`dry_run_trust_level=low`                                                                 | 暂无；未来单独 L3 odds safe path                                        | agent-blocked legacy                                           |
| `recon_scanner`                                     | `scripts/ops/recon_scanner.js`                                | Recon 薄壳入口                           | High        | 虽然入口很薄，但 registry 标记 `accesses_network=true`、`writes_db=true`、`dry_run_trust_level=low`，实际实现仍属高风险 runtime                                                         | 暂无；沿用现有治理 gate                                                 | admin-only legacy                                              |
| `batch_historical_backfill`                         | `scripts/ops/batch_historical_backfill.js`                    | 历史 CSV/FotMob/ELO/L3 批量编排          | High        | 文档直接说明会编排 `titan_discovery`、`fetch_and_adapt_euro_leagues`、`csv_bulk_loader`、`run_production`、ELO、L3；registry `bulk_risk=high`                                           | future single-target / small-write phases                               | agent-blocked legacy                                           |
| `backfill_historical_raw_match_data`                | `scripts/ops/backfill_historical_raw_match_data.js`           | FotMob GSM raw/L2 批量补写               | High        | 自带 FotMob `SOURCE_URL_TEMPLATE`、`Pool`、`--commit`，默认联赛集非单目标                                                                                                               | future L2 controlled raw JSON path                                      | agent-blocked legacy                                           |
| `titan_seeder`                                      | `scripts/ops/titan_seeder.js`                                 | 批量 matches seed 注入器                 | High        | 直接 `https` 请求 FotMob API，并构造 matches insert rows；明显 bulk seed                                                                                                                | `data-l1-matches-seed-commit-execute`                                   | deprecated for agents；future remove candidate after migration |
| `fetch_and_adapt_euro_leagues` / `etl:fetch-*`      | `scripts/ops/fetch_and_adapt_euro_leagues.js`, `package.json` | football-data downloader / adapter       | Medium-High | 旧 downloader/runtime，registry 标记 `accesses_network=true`、`dry_run_trust_level=low`                                                                                                 | 未来 source-manifest + local staging parser path                        | agent-blocked legacy                                           |
| `raw_match_data_local_ingest.js --commit`           | `scripts/ops/raw_match_data_local_ingest.js`                  | raw_match_data 本地写入口                | Medium      | 当前脚本其实已把 `--commit` blocked；但 commit 语义仍属 legacy write surface                                                                                                            | future L2 raw ingest authorization/preflight/write                      | keep preflight gate, commit remains blocked                    |
| `make data-network-dry-run`                         | `Makefile`                                                    | 通用 network dry-run 占位门              | Medium      | 目前是 blocked gate，不是可信的 source-specific safe runtime                                                                                                                            | source-specific safe gates                                              | keep blocked gate; do not advertise as L1 default              |
| `make data-single-target-network-dry-run`           | `Makefile`                                                    | 单目标 network scaffold gate             | Medium      | scaffold-only / blocked，不是已授权的真实 L1 runtime                                                                                                                                    | source-specific authorized safe path                                    | keep blocked gate                                              |
| `make data-harvest`                                 | `Makefile`                                                    | bulk harvesting gate                     | High        | 明确写着 `Blocked bulk harvesting gate`                                                                                                                                                 | 无                                                                      | keep blocked gate                                              |

## 4. Engine core inventory

这些不是 deprecated 对象，而是应保留、复用、继续包在 safe path 里的 engine core：

- `src/infrastructure/services/DiscoveryService.js`
    - 继续作为 L1 核心 service。
    - 已新增 `discoverCandidates()`，说明 core 能被安全抽用，而不是只能走 legacy CLI。
- `src/infrastructure/services/DiscoveryParser.js`
    - discovery 原始 payload 到 fixture/candidate 的解析层。
- `src/infrastructure/services/DiscoveryAttributeMapper.js`
    - 字段映射与标准化。
- `src/infrastructure/services/DiscoveryDataValidator.js`
    - discovery 数据校验器。
- `src/infrastructure/services/L1ConfigManager.js`
    - 联赛配置、赛季窗口、source URL 构造依赖。
- `src/infrastructure/services/HttpClient.js`
    - L1/L2 外网访问基础件之一，继续保留，但不该由 agent 直接驱动 legacy runtime。
- `src/infrastructure/services/FotMobExtractor.js`
    - FotMob 提取逻辑基础件，继续保留。
- `src/infrastructure/services/BrowserProvider.js`
    - browser fallback 相关基础件，继续保留，但 safe L1 path 默认禁用。
- `src/infrastructure/services/FixtureRepository.js`
    - DB persist 能力继续保留，但不该由 Phase 5.03L1-5.09L1 的 safe path 直接调用。
- `config/leagues.json`
    - 联赛 registry/config source。
- `config/season_windows.json`
    - season window guard source。
- `config/acquisition_engines.phase454.json`
    - 当前最有价值的治理 inventory；很多 legacy 风险判断已经明确写在里面。

结论：

- keep
- reuse
- do not delete
- wrap through safe path

## 5. Safe replacement map

- `titan_discovery` 的受控 discovery 用法
    - 替代为 `make data-l1-discovery-candidates-network-preview`
    - 核心调用 `scripts/ops/l1_discovery_safe_preview.js -> DiscoveryService.discoverCandidates()`
- direct matches persist / bulk seed
    - 替代为 `make data-l1-matches-seed-commit-execute`
    - 只允许 exact 2026-05-10 FotMob Ligue 1 8 candidates，且只写 `matches`
- future raw detail acquisition
    - 不复用 `backfill_historical_raw_match_data` 直接落库
    - 改走 Phase 5.10L2+ controlled raw JSON path
- bulk harvest
    - 目前没有直接 safe replacement
    - 应在 L2 受控链路成熟后，再考虑低频 scheduler / admin-only orchestration
- training / prediction
    - 继续走独立后续 phase，不与 L1/L2 safe path 混合

## 6. Deprecation stages

### Stage 1: Document and agent-block

- AGENTS.md 明确 legacy L1/data entrypoints 对 agents deprecated
- docs 标记 legacy/admin-only
- Makefile help 指向 `data-l1-*` safe workflow

### Stage 2: Add warning wrappers

- 对旧 Makefile target 增加 warning/help 指引
- 对危险 npm scripts 增加文档提示
- 不改生产脚本逻辑

### Stage 3: Migrate internal references

- runbooks
- docs
- package usage examples
- tests / governance docs
- 逐步把旧引用换成 `data-l1-*` safe path

### Stage 4: Optional hard block

- 非管理员场景进一步 blocked
- 可要求类似 `CONFIRM_LEGACY_ADMIN_ENTRYPOINT=1`
- 仍不建议 agents 使用

### Stage 5: Removal candidate review

- 连续若干阶段无人引用
- CI / docs / automation 无依赖
- safe replacement 已覆盖
- 用户明确批准

满足这些条件后，才讨论删除。

## 7. Current recommended immediate changes

本阶段实际建议只做这些小变更：

- AGENTS.md 增补 legacy deprecation 规则
- AGENTS.md 明确 engine core 不是 deprecated
- Makefile `data-help` 增加 preferred L1 safe workflow
- 不改旧 target 行为
- 不删除旧入口

## 8. Future work

推荐两个后续方向：

1. Phase 5.10L2: controlled raw JSON acquisition planning
    - 基于 newly seeded matches 梳理现有 L2 raw detail acquisition code
    - 规划 `raw_match_data` 写入 authorization / preflight / controlled write
2. Phase 5.11G: legacy entrypoint warning wrappers
    - 继续治理旧入口
    - 只加 warning，不删除 runtime

## 9. Validation

本阶段验证结果：

- `git diff --check` passed
- `docker compose -f docker-compose.dev.yml exec -T dev npm test` passed
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage` passed
- `docker compose -f docker-compose.dev.yml exec -T dev npx prettier --check --ignore-unknown AGENTS.md Makefile docs/_reports/L1_LEGACY_ENTRYPOINT_DEPRECATION_MIGRATION_PLAN_PHASE5_10G.md` passed
- DB row counts unchanged:
    - `matches=10`
    - `bookmaker_odds_history=2`
    - `raw_match_data=2`
    - `l3_features=2`
    - `match_features_training=2`
    - `predictions=2`
- `find tests/fixtures -maxdepth 1 -type d -name 'l1-config-*'` returned no residue
- `git ls-files 'tests/fixtures/l1-config-*'` returned no tracked residue
- `docs/_staging_preview` absent

## 10. Explicit non-execution

本阶段明确未执行：

- `titan_discovery.js`
- `run_production.js`
- `batch_historical_backfill.js`
- `backfill_historical_raw_match_data.js`
- `titan_seeder.js`
- `total_war_pipeline.js`
- `odds_harvest_pipeline.js`
- `recon_scanner.js`
- external FotMob access
- network dry-run
- browser/proxy runtime
- DB writes
- matches writes
- raw_match_data writes
- harvest / ingest
- training / prediction
- file deletion
