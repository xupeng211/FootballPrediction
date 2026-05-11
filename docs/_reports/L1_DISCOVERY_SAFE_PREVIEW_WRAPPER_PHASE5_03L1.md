# L1 Discovery Safe Preview Wrapper - Phase 5.03L1

## 1. Executive summary

项目已经有工业级 L1 Discovery Engine，本阶段不是重写 L1，也不是继续手搓 FotMob 单场链路。

本阶段新增的是一个 thin safe wrapper：[`scripts/ops/l1_discovery_safe_preview.js`](/home/xupeng/FootballPrediction.clean-dev/scripts/ops/l1_discovery_safe_preview.js)，目标是安全 preview L1 discovery plan。

这个 wrapper 只读本地配置和治理 registry，输出 JSON preview，不触网，不写 DB，不写 `matches`，不写 `raw_match_data`。

## 2. Implemented files

- [`scripts/ops/l1_discovery_safe_preview.js`](/home/xupeng/FootballPrediction.clean-dev/scripts/ops/l1_discovery_safe_preview.js)
- [`tests/unit/l1_discovery_safe_preview.test.js`](/home/xupeng/FootballPrediction.clean-dev/tests/unit/l1_discovery_safe_preview.test.js)
- [`Makefile`](/home/xupeng/FootballPrediction.clean-dev/Makefile)
- [`AGENTS.md`](/home/xupeng/FootballPrediction.clean-dev/AGENTS.md)
- [`docs/_reports/L1_DISCOVERY_SAFE_PREVIEW_WRAPPER_PHASE5_03L1.md`](/home/xupeng/FootballPrediction.clean-dev/docs/_reports/L1_DISCOVERY_SAFE_PREVIEW_WRAPPER_PHASE5_03L1.md)

## 3. Why wrapper lowers risk

`titan_discovery` 是大入口，默认可能触网、批量扫描、调用 `DiscoveryService.discover()`，最后落到 `FixtureRepository.persist()` 写 `matches`。

这个 wrapper 是窄入口：

- `source` 必须显式给出，首期只允许 `fotmob`
- `scope` 必须显式给出
- `concurrency` 固定收紧到 `1`
- `max_targets` 固定收紧到 `1`
- 默认 preview-only
- 默认 no DB
- 默认不调用 `persist`
- commit 固定 blocked

这样后续如果要放开 network preview 或小范围写入，可以单独授权，不会误撞 legacy 大入口。

## 4. Current L1 boundary

当前 L1 负责 discovery / match candidates。

raw JSON 入库属于 L2 / raw acquisition。现在 `raw_match_data` 对 `matches` 有 FK，所以最终路线应该还是：

1. L1 controlled seed matches
2. L2 raw JSON acquisition
3. `raw_match_data` ingest
4. local parser

所以本阶段 wrapper 只做 plan preview，不去碰 L2/L3/训练/预测链路。

## 5. Validation

本地验证范围：

- 新增 unit tests
- `make data-l1-discovery-preview` preview 成功
- `make data-l1-discovery-commit` blocked
- `npm test`
- `npm run test:coverage`
- `eslint`
- `prettier`
- `git diff --check`
- DB row counts unchanged
- `tests/fixtures/l1-config-*` absent
- `docs/_staging_preview` absent

`npm run test:integration` 没有本地执行；如果该 suite 需要真实 Chromium / browser automation，则按本阶段 no-browser / no-network 约束留给 PR CI / main CI。

## 6. Recommended next phase

推荐下一步是 Phase 5.04L1：controlled L1 network preview design / `discoverCandidates()` extraction。

目标：

- 不直接跑 `titan_discovery`
- 尽量复用 `DiscoveryService` 核心能力
- 增加 `discoverCandidates()` 或 safe dependency injection
- 允许未来受控 network discovery preview
- 仍默认不写 DB
- 后续再讨论 controlled matches seed commit

## 7. Explicit non-execution

本阶段明确未执行：

- external FotMob access
- network dry-run
- browser automation
- proxy runtime
- harvest
- ingest
- DB writes
- `raw_match_data` writes
- `matches` writes
- feature writes
- prediction writes
- staging writes
- file deletion
- `titan_discovery` execution
