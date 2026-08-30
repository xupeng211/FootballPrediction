# Stage C — Canonical Market Evidence Pilot

## 目标与边界

Stage C 建立 provider-neutral、不可变、可版本化、可重放且可审计的 EPL 赛前 1X2 market-evidence spine。The Odds API 是初始 acquisition provider，不是 canonical provider；canonical authority 属于 FootballPrediction transaction-v1 contract。本阶段不包含 PostgreSQL、scheduler、value/de-vig/CLV、backtest、training、second provider、OddsPortal 或 betting automation。

当前文档描述实现事实和安全边界，不宣称 Stage C 已 merge、已完成 fresh Sol review 或已获得独立 review approval。

## Canonical architecture

真实 capture 或已有离线证据统一经过：

`capture receipt + immutable RAW → verified allocation authority → current authority snapshot → prospective builder → atomic publisher → fresh authority reader`

`transaction-v1` 的 committed transaction directory 是唯一 canonical authority。Prospective builder 只做全批次内存校验和 candidate 构造，不写 identity、observation、registry 或 authority。Publisher 在同一 filesystem 上获取 writer lock，重新读取并校验 parent，独占写入并 fsync staging 文件和目录，再以一次 directory rename 进入 `committed/`，之后由 authority reader 重建整条 parent chain。旧 JSONL identity/observation ledger 仅保留为 legacy/derived compatibility surface，不能成为新 canonical live/replay 的 authority。

机器可读合同见 [market observation schema](../../schemas/market_evidence/market_observation.schema.json)、[transaction manifest schema](../../schemas/market_evidence/market_evidence_transaction_manifest.schema.json) 和 [transaction store schema](../../schemas/market_evidence/market_evidence_transaction_store.schema.json)。

## Bitemporal contract 与 T2

Source time（`bookmaker_last_update_at`、`source_snapshot_at`）表示 provider 描述的市场时间；capture time（`capture_started_at`、`response_received_at`、`ingested_at`）表示证据被取得和接收的时间；knowledge time / projection availability（T2，`projection_available_at`）表示 FootballPrediction 实际发布 canonical projection 的时间。三者不能互换。

调用方不能通过 `projectionAvailableAt`、`projection_available_at`、`knowledge_time`、`ingested_at` 或旧 raw timestamp backdate T2。Adapter 和 replay 对 caller projection time fail closed；prospective builder 不接受 projection time。Candidate 中的时间只用于内存验证；publisher 只有在 lock、fresh parent reread 和 publication boundary 都通过后，才生成当前 publisher-owned `knowledge_time`，并把所有已发布 observation 的 `projection_available_at` 与 manifest metadata 绑定。

T2 不进入 transaction 的 deterministic retry identity：observation semantic digest、batch semantic digest 和 authority state hash 对 publisher-owned T2 做规范化；manifest/artifact 的实际 SHA-256 仍绑定磁盘上的精确 T2。因而晚到的 replay 在旧 `AS_OF(decision_time)` 不可见，在 publisher knowledge time 及之后可见，且相同 canonical batch 的重试不会因新的 wall-clock T2 产生 fork。

`deriveTimeline` / `latestAsOf` 仍要求显式 UTC `decision_time`，并只选择 knowledge boundary 不晚于该时间且没有 quality flags 的 observation。历史 source timestamp 不能让后知数据泄漏到过去。

## Identity、observation 与 receipt

Fixture/Event canonical IDs 由 FootballPrediction verified allocation authority 和 governed identity registry 提供；provider-shaped ID、swapped team/kickoff、未绑定 allocation 的 registry、fake/duck-typed ledger、错误 decision/ruleset/resolver 或 active 非 `MATCHED` 映射都 fail closed。`MATCHED → QUARANTINED → MATCHED` 通过 append-only supersession 恢复；quarantined event 不产生 market observations。

每条 observation 绑定 canonical/provider identity、decision、registry version/hash、adapter version、RAW SHA-256、capture receipt 和 publisher T2。RAW 与 receipt 不可变。相同 `capture_id` 的 receipt retry 只有在 canonical receipt bytes 完全一致时才 no-op；相同 identity 的不同内容 fail closed，不覆盖原 receipt。旧 JSONL derived append 对同一 observation identity 只允许 T2-neutral semantic retry，市场内容变化仍拒绝。

## Live 与 offline replay

`scripts/ops/stage_c_the_odds_api_live_smoke.js` 是 transaction-v1 live/offline integration entrypoint。默认优先读取已有本地 FotMob RAW、The Odds API RAW、receipt 和 allocation evidence，因此验证不产生 provider request；network capture 只有显式 `STAGE_C_ALLOW_NETWORK=yes` 且具备 key 时才可运行。live 与 replay 都调用同一个 `offlinePipeline`、prospective builder、atomic publisher 和 fresh authority reader，不再执行 legacy identity append、observation append 或 registry authority write。

`scripts/ops/stage_c_fixture_identity_replay.js` 只接受已有 immutable evidence，支持把早期 allocation snapshot 补足当前 provenance/hash envelope 后重新验证；`PROJECTION_AVAILABLE_AT` 被禁止，T2 由 publisher 生成。缺失 RAW、receipt、allocation 或 hash/provenance 不得用 synthetic data 替代。

本地已有 capture evidence 可离线重放并用于验证：20 个 provider events 中 16 个 MATCHED、4 个 QUARANTINED，生成 915 条 canonical observations；这些是当前 worktree 的 local evidence，不是 production coverage、provider terms 或 merge/review approval。

## Provider 与生产边界

Adapter 只解析 The Odds API 当前 EPL `h2h` / `h2h_lay` 形状；未知、重复、冲突或不完整 payload fail closed。receipt 只保存 allowlisted sanitized request、endpoint、timing、status、size、quota 和 hashes，不保存 secret。任何新的 provider acquisition、production DB/Redis mutation、raw write、migration、training、prediction、backtest、model activation、second provider 和 Stage D 均不在本阶段授权范围内。

生产 promotion 仍需 Owner 单独确认 provider retention/analytical-use/redistribution/commercial terms、真实 governed event/bookmaker mappings、覆盖率/quota evidence 以及 production storage/operations controls。本 pilot 不作法律或 production readiness 结论。

## 验证与状态

受影响测试覆盖 observation contract、schema、identity trust root、allocation/ledger binding、quarantine recovery、prospective zero-write、T2 no-lookahead、receipt idempotency、transaction parent chain、candidate/staging tamper、I/O failure、atomic rename、concurrency 和 cross-process reopen。canonical validation profiles 为 `make verify-targeted`、`make verify-pr`、`make verify-strict`；gate 必须实际识别并执行受影响 Stage C paths，`changed_files=0` / no-op 不算通过。

实现闭环后仍需 fresh independent Sol exact-head strict review、owner merge decision 以及 merge 后 main Production Gate；本文不把这些治理状态提前标记为通过。

## FUTURE_WORK

生产 promotion、真实 mapping governance、受控 live pilot、production persistence/operations、value/de-vig/CLV、backtest、scheduler、additional provider、exchange APIs、UI 和 Stage D 另行授权，当前不启动。
