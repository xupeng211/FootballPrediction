# Stage C — Canonical Market Evidence Pilot

## 目标与边界

Stage C 建立 provider-neutral、不可变、可版本化、可重放且可审计的 EPL 赛前 1X2 market-evidence spine。The Odds API 是初始 acquisition provider，不是 canonical provider；canonical authority 属于 FootballPrediction transaction-v1 contract。本阶段不包含 PostgreSQL、scheduler、value/de-vig/CLV、backtest、training、second provider、OddsPortal 或 betting automation。

当前文档描述实现事实和安全边界，不宣称 Stage C 已 merge、已完成 fresh Sol review 或已获得独立 review approval。

## Canonical architecture

真实 capture 或已有离线证据统一经过：

`capture receipt + immutable RAW → verified allocation authority → current authority snapshot → prospective builder → atomic publisher → fresh authority reader`

`transaction-v1` 的 committed transaction directory 是唯一 canonical authority。Prospective builder 只做全批次内存校验和 candidate 构造，不写 identity、observation、registry 或 authority。Publisher 在同一 filesystem 上获取 writer lock，重新读取并校验 parent，独占写入并 fsync staging 文件和目录，再以一次 directory rename 进入 `committed/`，之后由 authority reader 重建整条 parent chain。旧 JSONL identity/observation ledger 仅保留为 legacy/derived compatibility surface，不能成为新 canonical live/replay 的 authority。

机器可读合同见 [market observation schema](../../schemas/market_evidence/market_observation.schema.json)、[transaction manifest schema](../../schemas/market_evidence/market_evidence_transaction_manifest.schema.json) 和 [transaction store schema](../../schemas/market_evidence/market_evidence_transaction_store.schema.json)。

## Stage C 信任模型与边界

### APPLICATION_DATA_INTEGRITY_FAILURE_MODEL

Stage C 的保证范围是受信任的本地 FootballPrediction authority root 之内的应用级数据完整性。该范围内，系统提供 immutable persisted evidence、append-only publication、内部 content/hash/state consistency、fail-closed reconstruction、stale/concurrent publication protection、allocation binding、replay correctness、bitemporal/as-of correctness，以及对 partial corruption 或 inconsistent state 的检测。已提交 authority 不存在合法的应用层 rewrite 路径。

### WHOLE_STORE_TRUST_COMPROMISE_MODEL

Stage C 不声称能够在具备足够管理权限的行为者替换整个 authority root/history，并一致地重算所有无密钥 digest 后，继续提供 cryptographic origin authentication。SHA-256/content-addressing 在本 Pilot 中提供的是 integrity + consistency，而不是在 complete trust-root replacement 之后独立的 origin authentication。

针对该更强威胁的保护需要单独设计的 independent authentication/trust anchor；它不属于 Stage C Pilot。本节不会削弱 trusted local authority root 内已有的 fail-closed、链完整性或发布原子性保证。

## Bitemporal contract 与 T2

Source time（`bookmaker_last_update_at`、`source_snapshot_at`）表示 provider 描述的市场时间；capture time（`capture_started_at`、`response_received_at`、`ingested_at`）表示证据被取得和接收的时间；knowledge time / projection availability（T2，`projection_available_at`）表示 FootballPrediction 实际发布 canonical projection 的时间。三者不能互换。

调用方不能通过 `projectionAvailableAt`、`projection_available_at`、`knowledge_time`、`ingested_at` 或旧 raw timestamp backdate T2。Adapter 和 replay 对 caller projection time fail closed；prospective builder 不接受 projection time。Candidate 中的时间只用于内存验证；publisher 只有在 lock、fresh parent reread 和 publication boundary 都通过后，才生成当前 publisher-owned `knowledge_time`，并把所有已发布 observation 的 `projection_available_at` 与 manifest metadata 绑定。

逻辑批次身份与 authoritative transaction content identity 分离。`logical_batch_key` / `logical_content_hash` 用于识别同一 acquisition/projection 工作和冲突；transaction ID、exact artifact descriptors、manifest 及 parent content chain 则绑定 publisher-owned T2 的精确字节。已提交逻辑批次的重试复用原 transaction 与原 T2；未提交的重试可获得新的 T2。`STORE.json` 的 immutable `authority_created_at` 与严格递增的 transaction knowledge time 共同拒绝完整重哈希后的历史回填。因而晚到 replay 在旧 `AS_OF(decision_time)` 不可见，在 publisher knowledge time 及之后可见。

`deriveTimeline` / `latestAsOf` 仍要求显式 UTC `decision_time`，并只选择 knowledge boundary 不晚于该时间且没有 quality flags 的 observation。历史 source timestamp 不能让后知数据泄漏到过去。

## Identity、observation 与 receipt

### CANONICAL_ID_ALLOCATION_MODEL=RANDOM_ONCE_THEN_PERSIST

Fixture/Event canonical IDs 只由 FootballPrediction 内部 bootstrap allocator 生成，public production API 拒绝 caller allocator。它们是 opaque、FootballPrediction-owned、provider-neutral 的随机一次性分配；分配后稳定、不从 provider/team/date/kickoff 派生、不重新计算且永不复用。相同 RAW seed 从零开始不要求重新生成相同 canonical IDs。replay determinism 的含义是：相同 persisted allocation 加相同 governed evidence/versioned semantics，得到相同 replay interpretation。

首次 bootstrap 把完整 allocation bytes、hash、provenance、Fixture/Event ID 与 Fixture→Event relation 写入 immutable `STORE.json` trust root；在 trusted local authority root 内，reopen/replay 必须逐字节匹配该根，provider-shaped ID、mapping swap、fake/duck-typed ledger 或错误 governance 都 fail closed。该描述不表示无密钥自描述 hash 可防御上一节定义的 complete trust-root replacement。

### HISTORICAL_RESOLVER_MODEL=PERSISTED_VERSIONED_DECISION_IS_AUTHORITY

Fresh authority reader 会验证 RAW hash binding、capture receipt binding、allocation binding、resolver/ruleset version、deterministic decision identity、supersession、ACTIVE+MATCHED relationship、registry binding、observation binding 以及 transaction/content/state chain。它不会在 authority reopen 时 rerun 当前 resolver。

RAW→resolver replay 可以作为独立 audit/reconstruction tooling；若执行，该 replay 必须使用精确的历史 resolver/ruleset semantics。新的 resolver interpretation 必须通过 append/supersede 产生新的历史记录，绝不能静默重解释既有 committed decision。`MATCHED → QUARANTINED → MATCHED` 通过已发布 transaction 恢复；quarantined event 不产生 market observations。

每条 observation 绑定 canonical/provider identity、decision、registry version/hash、adapter version、RAW SHA-256、verified persisted capture receipt 和 publisher T2。RAW content identity 与 acquisition identity 分离：不同 `capture_id` 可以引用相同 RAW；同一 `(provider, capture_id)` 在 transaction chain 中只允许同一 receipt SHA 与 RAW SHA，exact retry 复用既有 transaction，冲突 fail closed。普通 caller receipt object 不能进入 prospective builder。旧 JSONL derived append 对同一 observation identity 只允许 T2-neutral semantic retry，市场内容变化仍拒绝。

## Live 与 offline replay

`scripts/ops/stage_c_the_odds_api_live_smoke.js` 是 transaction-v1 live/offline integration entrypoint。默认优先读取已有本地 FotMob RAW、The Odds API RAW、receipt 和 allocation evidence，因此验证不产生 provider request；network capture 只有显式 `STAGE_C_ALLOW_NETWORK=yes` 且具备 key 时才可运行。live 与 replay 都调用同一个 `offlinePipeline`、prospective builder、atomic publisher 和 fresh authority reader，不再执行 legacy identity append、observation append 或 registry authority write。

`scripts/ops/stage_c_fixture_identity_replay.js` 只接受已有 immutable provider evidence；早期 allocation snapshot 仅用于校验 fixture coverage/provenance，不能提供或替换 canonical IDs。首次 canonical bootstrap 由内部 allocator 建立 allocation artifact 与 STORE trust root；之后 replay 必须同时重开两者，缺一即 fail closed。`PROJECTION_AVAILABLE_AT` 被禁止，T2 由 publisher 生成。缺失 RAW、receipt 或 provenance 不得用 synthetic data 替代。

本地已有 capture evidence 可离线重放并用于验证：20 个 provider events 中 16 个 MATCHED、4 个 QUARANTINED，生成 915 条 canonical observations；这些是当前 worktree 的 local evidence，不是 production coverage、provider terms 或 merge/review approval。

## Provider 与生产边界

Adapter 只解析 The Odds API 当前 EPL `h2h` / `h2h_lay` 形状；未知、重复、冲突或不完整 payload fail closed。receipt 只保存 allowlisted sanitized request、endpoint、timing、status、size、quota 和 hashes，不保存 secret。任何新的 provider acquisition、production DB/Redis mutation、raw write、migration、training、prediction、backtest、model activation、second provider 和 Stage D 均不在本阶段授权范围内。

生产 promotion 仍需 Owner 单独确认 provider retention/analytical-use/redistribution/commercial terms、真实 governed event/bookmaker mappings、覆盖率/quota evidence 以及 production storage/operations controls。本 pilot 不作法律或 production readiness 结论。

## 验证与状态

受影响测试覆盖 observation contract、schema、production allocation bootstrap/reopen、trusted local root 内的 mapping/decision/T2 consistency、quarantine recovery、prospective zero-write、receipt/capture idempotency、transaction parent chain、candidate/staging tamper、I/O failure、atomic rename 与 post-rename unknown outcome。独立 Node 子进程测试同时覆盖 identical writers（one commit + reuse）、competing writers（one commit + stale parent）和 fresh-process reopen。canonical validation profiles 为 `make verify-targeted`、`make verify-pr`、`make verify-strict`；targeted JS profile 会先校验/初始化 lockfile dependency tree，并拒绝 global ESLint fallback；`changed_files=0` / no-op 不算通过。

实现闭环后仍需 fresh independent Sol exact-head strict review、owner merge decision 以及 merge 后 main Production Gate；本文不把这些治理状态提前标记为通过。

## FUTURE_WORK

生产 promotion、真实 mapping governance、受控 live pilot、production persistence/operations、value/de-vig/CLV、backtest、scheduler、additional provider、exchange APIs、UI 和 Stage D 另行授权，当前不启动。
