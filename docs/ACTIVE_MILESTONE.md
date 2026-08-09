# Active Milestone — 当前活动里程碑

> lifecycle: current-state（本文档随里程碑推进更新 / 替换）
>
> 首次建立：2026-08-01（PROJECT_KNOWLEDGE_ENTRY_AND_DOCUMENTATION_SAFETY 任务）。

## 本文档回答什么 / 不回答什么

回答：当前活动里程碑是什么、基线在哪、已完成什么、未完成什么、下一步需要什么授权、
绝对不能做什么。
不回答：完整能力清单（docs/CAPABILITY_INDEX.md）、仓库结构（docs/PROJECT_MAP.md）。

## 当前里程碑

- Active Issue: **#1793 — M3: Historical odds staging and import foundation**（OPEN）
- Milestone: **M3 historical odds staging / import foundation**
- 当前 main 基线：
  `2532a7b95fb9e52e065619b904a2865dc56649c2`（PR #1830 squash merge；
  post-merge main Production Gate 31327367581 success）
- 最近完成：**PR #1830** — M3-R2 official provider temporal contract reconciliation
  （squash merge `2532a7b95…`，post-merge main Production Gate 31327367581
  success）；**PR #1819** — FotMob bounded transport-phase observability
  （squash merge `b5e6d8bf9…`，post-merge main Production Gate 31204100182
  success）；**PR #1820** — Production Gate manual-dispatch baseline resolution
  （squash merge `d3bcf3f15…`，post-merge main Production Gate 31153912121
  success）；**PR #1818** — post-PR1817 state + SC-002 messaging reconciliation
  （squash merge `b64df1fe0…`，post-merge main Production Gate 31100339588
  success）；此前为 **PR #1817** — FotMob offline detail staging converter/validator
  （squash merge `fd60117d2…`，post-merge main Production Gate 31075669344
  success，staging 能力已在 main 上可用）；**PR #1816** — bounded auditable
  FotMob detail capture pipeline（squash merge `b6f9f385…`，真实抓取仍需单独授权）；
  此前为 **PR #1815** — pre-capture status/revision hardening（squash merge
  `a7da729fd…`，阶段A 三项代码加固：malformed reason fail closed、
  started+postponed 矛盾 fail closed、核心层 40-hex collector_code_revision）；
  **PR #1814** — docs knowledge map + stale-document safety guardrails（squash
  merge `49469ba10…`）；再此前为 **PR #1813** — FotMob v2 provenance export
  （provider status、dual hash、raw retention + capture manifest、
  clean-worktree 40-hex git revision 绑定、unknown / started fail closed、
  v1 输出路径不变）
- 关键 current-state 文档：docs/data/FOTMOB_CURRENT_STATE.md、docs/PROJECT_STATUS.md

## 已完成（勿重复）

- M3 离线主线 → D4F：离线 staging pipeline、CSV recovery、确定性候选导出与身份、
  D4B 持久化合同（38,616 accepted / 216 quarantined 冻结合同）、
  D4C / D4E 受控 synthetic 写入验证（1 run / 1 source / 6 accepted / 3 quarantine）、
  D4D readiness 评审、D4F 交叉来源审计
  （888 exact / 4 kickoff conflicts / 248 canonical-only / 252 无 exact link /
  1,140 候选总人口）。
- **M3-R1 — historical odds current-main reproducibility（COMPLETE：PR #1829 squash-merged
  `eb924b59e`，post-merge push Gate `31320043403` success；M3_R1_STATUS=COMPLETE；
  M3_R1_CLOSEOUT_COMPLETE=YES）**：
  新增 committed 有界重建入口 `npm run odds:staging:rebuild`
  （`scripts/ops/odds_staging/historical_odds_rebuild.js` + sibling `historical_odds_rebuild_canonical.js`，
  lifecycle: permanent；bundle/emit-dir 必须仓库外；no-write 默认；收据 v2 只记实际、无硬编码基线常量），
  从 current main 完全复现冻结基线（38,832 / 38,616 accepted / 216 quarantined；892 候选 380/380/132；
  888 exact / 3×15m + 1×30m conflicts；0 unmatched / 0 ambiguous）；BUILD_A/BUILD_B 字节一致；
  业务哈希 40b02195…（M3-R1 定义组合；D4F 遗留 07e579ed… 组合不可复算）。
  **Canonical self-recovering mode**（GAP-01）：从固定 Git 对象身份恢复来源（有界只读 git 子进程，
  仅 rev-parse/cat-file/show，shell=false，剥 GIT_* 环境，GIT_NO_LAZY_FETCH/GIT_ALLOW_PROTOCOL=none，
  仓库外确定性物化）；candidates artifact 绑定冻结基线（1140 + eff8817284…，fail closed）。
  **Output-aware self-verification**（GAP-02，--validate）：重算 emitted_digest、计数、业务哈希、
  linkage、manifest 派生字段、temporal facts/semantics/readiness；任何篡改被拒绝（真实数据验收
  BUILD_A/B 字节一致 + VERIFY PASS ×2 + 篡改探针 REJECTED）。
  **Machine-readable temporal contract**（GAP-03）：evaluation_readiness + temporal_semantics +
  rebuild_status；facts 从实际观测计算（38,832 unknown / 0 known），fail-closed classifier，
  手改 READY 被拒。**Temporal readiness = NOT_READY_FOR_TEMPORAL_VALUE_EVALUATION**
  （100% snapshot_type unknown、无观测/采集时间；plain ≠ opening、C ≠ closing；2024/2025 仅 4/6 家族、
  2023/2024 Interwetten 稀疏；上游 provenance/license/capture time 未验证）。68 回归测试；
  Codex focused review 2 轮（cap，P0/P1/P2=0，round-2 修复各附定向测试）；eslint 8.57.1 全绿；
  git diff --check 干净；本地 gatekeeper commit-mode 门禁通过。
- **M3-R2 — official provider temporal contract reconciliation（COMPLETE：PR #1830
  squash-merged `2532a7b95`，post-merge push Production Gate `31327367581` success；
  M3_R2_STATUS=COMPLETE；M3_R2_CLOSEOUT_COMPLETE=YES）**：
  Football-Data.co.uk 官方文档核验 C 系列 = provider 定义 closing、普通系列 =
  first_collection_after_market_open（per-source 判定，无全局 C 后缀推断）；
  机器可读合同模块 `footballDataProviderContract.js`（fail closed）+ 适配器
  1.3.0 overlay + 收据 v3（provider_semantic_contract / series_semantics_distribution /
  7 维 evaluation_readiness）；population 不变量与业务哈希 40b02195… 不变；
  BUILD_A/B 字节一致 + 6/6 tamper probes REJECTED；readiness =
  NOT_READY_FOR_TEMPORAL_VALUE_EVALUATION（closing 语义 YES / exact timestamp NO /
  strict decision-time NO / benchmark YES）。详见 docs/PROJECT_STATUS.md M3-R2 节。
- **VALUE_MVP-1 — offline probability benchmark: prematch baseline vs closing 1X2 market
  （IMPLEMENTED，Draft PR #1831 已建立待 Owner 验收；VALUE_MVP_1_STATUS=
  IMPLEMENTED_AWAITING_OWNER_ACCEPTANCE；final code `1c53a00b7`（门禁两轮修复后）；
  门禁闭环节点：PR body 已按仓库模板对齐（Task type=source-code），本地 gate 预验证
  PASS，待自然 synchronize Production Gate exact-head 通过；不得自动 Mark Ready /
  Merge / 开始下一步）**：
  回答 "a simple football-only prematch model 是否包含与 provider 定义 closing 1X2 market
  竞争力相当的可预测信息"；offline probability benchmark evaluation（非 executable
  betting backtest）；zero DB / zero network / zero new data；13 个 football-only feature
  （无任何 odds feature）；walk-forward by season；protocol 冻结
  （PROTOCOL_SHA256=`c6716e91…`）后真实 OOS：RUN_A/RUN_B 字节一致、pooled n=511
  delta log loss 0.1268463858（95% CI [0.0846640358, 0.1691520672]）→
  **FINAL CLASSIFICATION = MARKET_BETTER_THAN_MODEL**（合法结果）；validator 17 项
  全 PASS + 3 个 tamper 探针 REJECTED（含 coordinated CI 伪造）；Codex Round 1/2 均
  P0=P1=P2=0；run-receipt v2 记录环境指纹与 lbfgs 收敛状态；
  入口 `scripts/model_training/value_mvp_baseline_vs_closing.py`（internal，未登记
  README canonical 表）。详见 docs/PROJECT_STATUS.md VALUE_MVP-1 节。
- PR #1810：canonical inventory 写入设计评审（已结案）。
- PR #1811：canonical inventory writer proof（已结案）。
- PR #1812：disposable canonical proof SQL scan 范围修复（已结案）。
- PR #1813：FotMob v2 provenance export（已结案）。
- FOTMOB_REAL_CAPTURE_READINESS 阶段A 三项代码加固（出处：PR #1813 Debt Impact
  P3-1 / P3-2）：已在 exporter 核心层实现并测试 —— malformed `reason.short`
  fail closed（确定性 `malformed_reason_object:<type>` /
  `non_string_reason_short:<type>`）、started=true + postponed/Postp 矛盾 fail closed
  （`contradictory_status_flags:started_and_postponed`）、`buildCaptureManifest()`
  核心层强制 40-hex `collector_code_revision`（直接核心调用 / 依赖注入不可绕过，
  非法 revision 不产生任何文件）。`ALLOWED_PROVIDER_STATUSES` /
  `STATUS_MAPPING_VERSION` / identity-v1 输出 / 双 hash 均未变。
- **FOTMOB_DETAIL_STAGING_CONTRACT_IMPLEMENTATION_REVIEW_OFFLINE_ONLY（PR #1817 已于 2026-08-06 squash 合并入 main：merge commit `fd60117d2…`，post-merge main Production Gate 31075669344 success；以下为合并前的实现/修复记录）**：
  独立评审 8 项阻塞问题全部离线修复 —— 纯离线 detail staging converter/validator 已实现并全量测试 ——
  `make data-fotmob-detail-staging-{help,receipt,build,validate}`（直接 Node CLI
  `scripts/ops/fotmob_detail_staging.js` 为 internal engine）将归档的
  capture payload+manifest 对转换为不可变 `fotmob-detail-staging-artifact/v1`
  快照：5 个 versioned JSONB sections 逐字节保留、直接复用 pipeline 捕获
  hashing（无自实现副本）、确定性 observation_id（RFC 4122 UUIDv5）+ generated_at
  字节精确取自 manifest 的 response_received_at（并记录为 artifact 的
  source_response_received_at 字段）、canonical_match_id 恒
  null + UNLINKED_NOT_ATTEMPTED、append-only 文件 store + 编号
  store-state-<seq>.json 账本版本（无数据库、无 migration）、每次写入
  O_EXCL tmp+fsync+同文件系统 rename 的 per-file 原子写 + 独占 per-store lock、
  冲突 fail-closed、LOGICAL_COMMIT_MARKER 唯一提交点（residue 报告不当作已提交）、
  -validate 重验 artifact/summary/store ledger（MODE_1_UNANCHORED /
  MODE_2_EXTERNALLY_ANCHORED）。340 项 staging 测试 + 395 项受影响旧测试全绿，
  ESLint/git diff --check 干净；16 场归档（one/five/ten-match pilot
  archives）两次 build + 两次 validate 字节一致、ID set 精确一致、
  canonical_match_id 全 null、无 HTML/凭据/绝对路径，派生输出已删除。
  marker_event（parser 注入 AddedTime/Half 分钟标记、无 id 设计）记录为合法
  变体（真实 16 场均有 4 个）。零网络、零数据库、零采集、无真实 payload/
  manifest/artifact 提交；提交时 PR #1817 保持 Draft、未合并（等待外部独立
  实现验收；该 PR 已于 2026-08-06 合并入 main，见上）。

  修复内容：F1 逻辑 commit-marker 原子提交/回滚（commit-<seq>.json 为唯一提交点、
  最后写入、绑定文件列表+sha256 链、回滚只删本次写入文件、residue 扫描 fail-closed）；
  F2 REPEAT_EQUIVALENT 重建 artifact（business/integrity hash 重算、旧 artifact
  字节不变）；F3 VERIFIED_PACKAGE_RECEIPT（真实 archive SHA-256 验证 + 纯 Node
  安全 tar reader、无 child_process，每条 entry 绑定唯一 package）；F4 所有输入
  类型 symlink-ancestor 检查 + 输入输出非重叠规则；F5 完整 A–E 38 项 validator
  （无条件深检 + 13 项篡改测试）；F6 LAYER_A observation_id UUIDv5 重算 +
  generated_at 严格 ISO 等于 source_response_received_at，LAYER_B
  artifact_integrity_sha256 覆盖除自身外全部字段（7 项篡改测试）；F7 SC-002 状态
  更正（SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE /
  SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING / PR1817_CHANGES_SC002=NO）；
  F8 CLAUDE_POST_REMEDIATION_SELF_REVIEW P0/P1/P2=0、
  EXTERNAL_IMPLEMENTATION_ACCEPTANCE=PENDING、READY_TO_MERGE=NO。
  340 项 staging 测试（122 retention 故障注入/篡改（含 3 个 R18-P2-1
  短写注入回归 a/b/c + 1 个 R19-P2-1 lockCreated 回归 + 2 个 R20-P1-1
  stale-lock fail-closed 回归 + 3 个 R20-P2-1 final-artifact 一致性回归；
  原 P1-4 stale 自动恢复测试已改写为 R20-P1-1 fail-closed 回归）+ 82 source verification（含 4 个 R17-P2-1 PAX size
  覆盖回归 a/b/c/d + 3 个 R17-P2-1 PAX 合并语义回归 e/f/g）+
  89 contract [54 个显式声明 + 16 个 PAIRS 循环生成的逐字段冲突测试 + 3 个
  R6-P1-2 身份语义（R6-P1-2b/c/d）+ 3 个 R7-P3-2 长度上限 + 1 个 R8-P2-1
  严格数组 plainness + 3 个 R12-P3-1 cycle/深度守卫 + 3 个 R13-P2-3 validator
  深度门 + 1 个 R13-P3-2 proxy 数组拒绝 + 1 个 R14-P3-1 Symbol own key 拒绝
  + 4 个 R15-P2-1 __proto__ own-key 回归（R15-P2-1a/b/c/d）]
  + 17 converter + 30 CLI（25 + 4 个 R20-P2-2 limits-file 回归
  + 1 个 R21-P3-2 frozen-cap 回归，
  独立文件 fotmob_detail_staging_cli_limits.test.js）；Codex round-8（head
  7bbbd7658）2 项新 P2 —— R8-P2-1 isPlainJsonData 严格数组语义
  （非枚举 own toJSON / 空洞 / symbol / 额外 key / 非 Array 原型 / 非有限
  数字全部拒绝，.every() 无法覆盖，direct accepted 与 REPEAT_EQUIVALENT
  重建两条路径均补零写入回归）、R8-P2-2 commit 预检拒绝不可保留的
  LINKED_*/未知 terminal state（ok:false 逐字透传时唯一拦截点；白名单
  accepted/rejected/quarantine + ok 与分类一致性 + 写入前 summary 自校验，
  均补零写入回归与合法对照）—— 全部离线修复；Codex round-9（head
  8b1fc9034）1 项新 P2 + 1 项 P3 —— R9-P2-1 分类前 raw result 契约门
  （ok 必须为真布尔，truthy 字符串 'false' 不再视为成功；ok:true 必须声明
  ACCEPTED_NEW（最终状态由 retention 对 store 派生，原始 rejected 声明
  不得被丢弃后按 accepted 提交）；ok:false 不得声明 accepted —— 补 3 项
  零写入回归 + 合法对照）、R9-P3-1 文档字段名准确性（generated_at 取自
  manifest 的 response_received_at 并记录为 artifact 的
  source_response_received_at，两处文档已修正）—— 全部离线修复；
  Codex round-10（head 4c1609945，17 个 commit）2 项新 P2 + 2 项新 P3
  —— R10-P2-1 直接调用 commitObservations 的注入面收敛（quarantine_reason
  不再持久化调用者提供的 errors[0].message，改为由已验证 error_code 派生
  的固定白名单 reason；rejected ok:false envelope 必须携带注册表 E###
  error_code；builtAt 非严格 ISO 拒绝；写入计划中每个 commit 文档强制
  isPlainJsonData；D-group 校验 recorded_at 严格 ISO + 文件与账本一致 ——
  补 5 项回归 + 合法对照）、R10-P2-2 validator observations 形状硬化
  （数组 observations 拒绝为 LEDGER_INVALID；null/非对象 entry 返回
  LEDGER_INVALID 而非抛异常 —— 补 2 项 mutation 回归）、R10-P3-1 字段名
  收口（CAPABILITY_INDEX.md:70 与 PR body 统一为 manifest response_
  received_at → artifact source_response_received_at；计数同步 279）、
  R10-P3-2 tar parser 悬空 GNU L / PAX x 元数据 EOF 拒绝（SAFETY_ERROR，
  补 2 项 EOF fixture 测试）—— 全部离线修复；
  Codex round-11（head d9a47e1，18 个 commit）2 项新 P2 + 3 项新 P3 ——
  R11-P2-1 直接调用 commitObservations 的结果信封注入面收敛（每个 result
  在读取前先做 descriptor 扫描 + 标量快照，accessor/proxy 一律
  INPUT_ERROR；ok:true 不得携带 error_code；runId 必须为纯标识符 ——
  补 4 项回归 + 合法对照）、R11-P2-2 validateStagingArtifact 对整份
  artifact 执行 prohibited raw content 扫描（E013：HTML/凭据签名 ——
  补 1 项篡改回归）、R11-P3-1 D-group quarantine_reason 必须由注册表
  error_code 白名单派生且与账本一致（补 1 项回归）、R11-P3-2 marker
  篡改回归改用重算哈希的 marker（测试辅助修复）、R11-P3-3 tar PAX 路径
  支持多字节 UTF-8 名称（补 1 项回归）—— 全部离线修复；
  Codex round-12（head 1350ef4de，review relay 4867154234 后新 commit，18 个
  commit）2 项新 P2 + 1 项新 P3 —— R12-P2-1 artifact 深快照（artifact 不再保留
  调用者原引用：descriptor 驱动深拷贝 + util.types.isProxy 拒绝 + 从不调用
  调用者对象上的 JSON.stringify/toJSON，验证、hash、写入、marker 全部读取同一份
  物化字节 —— 补 2 项回归 + 合法对照）、R12-P2-2 inspectArchive 资源上限
  （压缩文件读前 fstat 大小上限、gunzipSync maxOutputLength、tar 成员数/
  单成员/累计大小上限，全部 fail-closed SAFETY_ERROR —— 补 4 项回归 + 合法
  对照）、R12-P3-1 isPlainJsonData / 禁止内容扫描的 cycle/深度/Proxy 守卫
  （循环或超深 → 结构化 INPUT_ERROR/E013，而非 RangeError —— 补 3 项回归）
  —— 全部离线修复；计数同步 297；
  Codex round-13（head c00343a58，19 个 commit）4 项新 P2 + 3 项新 P3 ——
  R13-P2-1 verifyArchive 合并 DEFAULT_ARCHIVE_LIMITS 并把 maxCompressedBytes
  传给读前 fstat（receipt 首遍 SHA 不再无界读入整个归档 —— 补 1 项回归 +
  合法对照）、R13-P2-2 提供已注册 inspected capability 时无条件校验
  receipt↔binding SHA，且 capability 携带已验证 archive 的规范路径
  （archive_path 入 inspect 结果 + 深冻结），与 binding 路径不一致即拒绝
  （补 2 项回归）、R13-P2-3 validateStagingArtifact 开头增加
  isPlainJsonData 深度/cycle/plain 门（直接 API/CLI/store validator 与
  commit 的 128 层门一致，循环/超深 → 结构化 validation error 且跳过
  canonicalJsonHash 无界遍历 —— 补 2 项回归 + 合法对照）、R13-P2-4
  validateSummaryDoc 在遍历前校验每个 observation 为非数组 object，
  null/raw 行 → SUMMARY_INVALID 并短路，validateOutputRoot 对畸形行跳过
  而非抛异常（补 1 项 marker-consistent mutation 回归）、R13-P3-1 result
  envelope 本身拒绝 Proxy（util.types.isProxy，读取任何字段之前 —— 补
  1 项零写入回归）、R13-P3-2 scanProhibitedContent 的 Proxy 拒绝移到
  array/object 分派之前（Proxy 数组也结构化 E013 —— 补 1 项回归 +
  合法对照）、R13-P3-3 PROJECT_STATUS.md current-baseline 段 contract
  计数 77→80（含 R12-P3-1）—— 全部离线修复；计数同步 307；
  Codex round-14（head 35a1409b2，20 个 commit）1 项新 P2 + 2 项新 P3 ——
  R14-P2-1 payload/manifest 读前大小上限（entry selector 先于任何读取解析，
  读上限取自 live archive member size（本身受 archive limits 约束）、缺失
  member 封顶 0，超大外部文件在 fstat 大小门 SAFETY_ERROR 拒绝、读入内存之前
  —— 补 direct API（R14-P2-1a）+ CLI/build（G57，E008 REJECTED_PROVENANCE_BROKEN
  批次隔离、零接受）+ 合法对照）、R14-P3-1 isPlainJsonData 与
  snapshotStrictPlainData 的 object 分支改用 Reflect.ownKeys 拒绝 Symbol own
  keys（snapshot 不再静默丢弃 —— 补回归 + 合法对照）、R14-P3-2 当前概述
  计数 260→307 —— 全部离线修复；计数同步 310；
  Codex round-15（head ec2f29037，21 个 commit）1 项新 P2 + 1 项新 P3 ——
  R15-P2-1 合法 own "__proto__" key 处理（`{}` + `target[key] = value` 写入
  模式触发 legacy __proto__ setter：标量被静默丢弃、对象值改变临时对象原型；
  影响 shared `canonicalizeJson`（FotMobRawDetailFetcher.js，staging artifact
  hash 链 canonicalJsonHash → sha256CanonicalJson → canonicalizeJson 的共享
  底层）、snapshotStrictPlainData（Contract.js）与两个 artifact hash
  projection —— 全部改为 Object.defineProperty 安全创建 enumerable data
  property（行为对非 "__proto__" 输入完全不变；Retention 的
  newObservations 键为 sourceMatchId:sha256 内部派生、结构性含冒号、不
  可达 —— 无需修改），补 5 项回归：R15-P2-1a JSON.parse 生成的 own
  "__proto__" 标量经 snapshot 保留为 data property（原型不被劫持）、
  R15-P2-1b 对象值变体（值保持为 plain 值而非原型）、R15-P2-1c artifact
  级 hash 敏感性（business/integrity hash 对该字段敏感）+ 合法对照
  validateStagingArtifact ok:true、R15-P2-1d section 内嵌套 "__proto__"
  只经 shared canonicalizeJson 路径的 hash 敏感性判别、R15-P2-1e 端到端
  convert→commit→validate 保留（字段落盘为 own enumerable data property，
  剥离该字段成为被检测的篡改 —— 修复前恰可通过校验）、R15-P3-1 selector
  顺序注释精确收窄为"在 payload/manifest 输入文件 gate/read 前"（归档本身
  在其自有上限下先行 live-inspect —— P3 不阻塞合并）—— 全部离线修复；
  计数同步 315；
  （本段 remediation 叙述为历史截止点：round-16..21（计数 315→320→324→330→331→339→340）
  的逐轮 finding、映射、回归与 Production Gate 行见权威 current-state 文档
  docs/data/FOTMOB_CURRENT_STATE.md——当前 head 的完整 Codex 闭环状态以其为准。）
  运行时计数 = node --test # pass，与静态 test() 声明的差异仅来自
  循环生成测试）+
  347 项 legacy FotMob + 769 项 unit 全绿；
  ESLint 干净。16 场离线复验（固定归档 e3679262/9bc50640/02635cee）：
  RUN_1 16 ACCEPTED_NEW、RUN_2 16 REPEAT_EXACT 字节一致、RUN_3 synthetic
  REPEAT_EQUIVALENT（SYNTHETIC_DERIVED_TEST=YES / REAL_NEW_OBSERVATION_CLAIM=NO），
  三轮 validate 全部 PASS、零 residue。Codex 独立复审 4863122944 的 13 项发现
  （P0-1/P0-2/P1-1..P1-5/P2-1..P2-5/P3-1）已全部离线修复并补回归测试；
  Codex 复审轮 2（4863831437）3 项发现、轮 3（4863962003）4 项发现
  （R3-P1-1 source index source_match_id 身份绑定、R3-P2-1 quarantine
  证据 (source_match_id, error_code) 键隔离复用 + ledger Object.fromEntries
  修复、R3-P3-1 ACTIVE_MILESTONE 入口表、R3-P3-2 测试计数核算）、轮 4
  （8c48d9ef5 复审）4 项发现（R4-P1-1 多 pair archive 的 entry 级
  payload/manifest member selector、R4-P2-1 数组结构化垃圾保持 E001
  而非 E007、R4-P3-1 PROJECT_STATUS 旧段落替换、R4-P3-2 GNU L 记录
  尾部 NUL 剥离）也全部离线修复并补回归测试（round-7 完成时 260 项 staging
  测试全绿，含 round-6 的 5 项发现修复：R6-P1-1 validate 失败退出码、
  R6-P1-2 observed 球队必填 + artifact 身份语义、R6-P2-1 导出 API 严格类型
  合同、R6-P2-2 quarantine key/entry/file/summary 语义三方绑定、
  R6-P3-1 archive input gate 非重叠检查）；
  零网络、零数据库、零采集、无 migration；PR #1817 已于 2026-08-06 squash
  合并入 main（merge commit `fd60117d2…`），post-merge main Production
  Gate 31075669344 success；staging 能力已在 main 上可用。
- **FOTMOB_BOUNDED_AUDITABLE_DETAIL_CAPTURE_PIPELINE（PR #1816，已于 2026-08-04 squash 合并入 main：merge commit `b6f9f385…`）**：已实现并
  全量离线测试的有界、可审计、可恢复 detail capture 流水线 —— 四阶段
  PLAN（确定性 plan + 重算 plan_business_sha256，PLAN 构建器与 CAPTURE 校验器
  共享同一 hash 逻辑）/ PREFLIGHT（完全离线验证 plan、重算 hash、校验
  git/路径/run id/预算/授权变量，打印候选数与 URL 摘要，零 mkdir/fetch/write）/
  CAPTURE（授权门、单 URL 网络合同、19 项内容有效性门含可信 observed-match-id
  来源与冲突检测、稳定 payload+manifest 配对原子保留（不落盘原始 HTML）、
  run-state 全面绑定校验、run-bound 不可变 plan snapshot、预算只计本次真实
  fetch、失败请求计入 attempted 计数）/ REPLAY（完全离线，要求 run plan
  snapshot，从稳定 payload 确定性物化 fotmob-match-detail-artifact/v1，
  parsed_at 取自捕获记录，重复 replay 字节一致）。canonical 运行时入口为
  `make data-fotmob-detail-capture-{help,plan,preflight,execute,replay}`；
  直接 Node CLI 是 internal engine（非 canonical 接口）。复用
  FotMobCandidateExporter / FotMobRawDetailFetcher / FotMobRouteIdentityReconciler /
  NextDataParser / FotMobRawParser，未创建重复 parser；不写数据库。
  **未执行任何真实 detail-capture 请求**（唯一真实 FotMob 网络流量 = 已完成的有界
  两路径兼容性 probe，2 次请求）：CAPTURE 默认关闭，真实执行仍须单独授权
  （OWNER_REAL_CAPTURE_AUTHORIZATION=NO）。

## 未完成 / 未授权（不得自动开始）

1. **VALUE_MVP-1（offline probability benchmark: prematch baseline vs closing 1X2
   market）待 Owner 验收**：Draft PR 已建立；M3-R2 已 COMPLETE（PR #1830，见"已完成"）；
   VALUE_MVP_1_STATUS=IMPLEMENTED_AWAITING_OWNER_ACCEPTANCE；不得自动 Mark Ready /
   Merge / 开始下一步。验收前不得开始 historical odds → production import 集成。
2. **historical odds production import 集成（NOT_ESTABLISHED）**：与 canonical
   inventory writer 分开 —— CanonicalInventoryWriter、V26.10 canonical inventory
   contract（artifact / import-run / lineage 表）与 disposable canonical writer proof
   已实现（PR #1811，docs/PROJECT_STATUS.md）；尚未建立的是 historical odds staging →
   production bookmaker odds / matches 表的正式 import 集成、授权表面与执行流程。
   真实持久化 / 生产写入仍 BLOCKED，未授权未执行。
3. **FOTMOB_REAL_CAPTURE_READINESS（planning milestone）**：仓库内无该里程碑的
   独立 Issue / tag / 文档；唯一出处为 PR #1813 正文与 Issue #1793 结案评论
   （"begin a separate FOTMOB_REAL_CAPTURE_READINESS milestone. Do not start real
   capture automatically."）。它未被授权为可执行里程碑，不得自动开始真实采集。
4. **阶段A 剩余 P3（出处：PR #1813 Debt Impact）**：P3-1 / P3-2 代码加固已完成
   （见"已完成"）；以下各项**不属于**阶段A、本轮未处理：
   P3-3 v1 paired-write 弱点（标注 unchanged scope）、injected filesystem
   path-validation consistency、final readback cleanup semantic inconsistency。
   阶段A 仅为代码加固：未执行真实 FotMob 网络请求、未生成真实 capture artifact。
   公共条款 / 使用边界审查已完成（written permission 缺失）；有界两路径兼容性
   probe 已完成 = 2 次请求，match detail 路由与 EPL fixtures 路由均兼容，
   未见 access-control 信号。
5. **三赛季真实采集**（2022/2023–2024/2025 范围的网络抓取）：未授权。
6. **一场已结束比赛的受控真实 FotMob 详情端到端试运行（下一项推荐的数据任务）**：
   单场、单请求、仓库外输出、零数据库连接/写入、零 SQL、零 migration、
   零训练/回测/预测。任务边界（MATCH_COUNT=1 / MAX_FOTMOB_REQUESTS=1 /
   MATCH_STATUS=FINISHED）经 canonical 入口表达为：plan 阶段
   `make data-fotmob-detail-capture-plan`（`MATCH_ID=<精确 match id>` +
   `LIMIT=1` 选择单场）、execute 预算 `MAX_REQUESTS=1` 且
   `CONFIRM_MAX_FOTMOB_REQUESTS=1`（确认变量仅 execute 强制；preflight
   仅 `MAX_REQUESTS=1`）、FINISHED 为执行前用户确认环节核实
   的人工确认条件（capture 脚本无该 filter 参数）。流程为 PLAN → PREFLIGHT
   → 用户确认精确 match id 与预算 → CAPTURE 一场（execute 需全部授权变量
   与 `NETWORK_AUTHORIZATION=yes`）→ package/archive/receipt → offline
   staging build → staging validate → repeat offline build → 确定性输出比对 →
   证据评审 → 停止。**尚未授权**：需要新的明确用户授权标识
   `OWNER_AUTHORIZES_ONE_MATCH_REAL_FOTMOB_END_TO_END_TRIAL=YES`（当前=NO），
   不得自动开始，不得自动扩展到 5 场或 16 场。
7. **生产 import schema 与真实写入**：需后续单独授权（须先满足 status-complete
   artifact、FotMob endpoint/capture/licence provenance、disposable proof、
   dedicated sandbox/ACL/backup-restore 等 Gate，见 Issue #1793 评论）。
8. **训练 / 回测 / 预测**：仍禁止 / 未授权（README canonical 表、CLAUDE.md）。

## 当前授权下一步

- 只读审计与阅读（无需另行授权）：docs/data/FOTMOB_CURRENT_STATE.md、docs/PROJECT_STATUS.md、
  PR #1813 证据、Issue #1793 记录。
- 文档维护（不自动执行：需用户明确确认后方可发起，且连续 governance/docs-only PR 须人工确认）：
  本文档与 docs/CAPABILITY_INDEX.md、docs/PROJECT_MAP.md 的 current-state 更新。
- 等待主会话 / 用户对下一授权步骤的明确指令（如阶段A 实现、canonical inventory provenance review）。

## 明确停止边界（不得越界）

- 不执行任何真实网络抓取、浏览器自动化、DB 写入、migration、artifact 写盘、
  训练、预测或生产操作。
- 不执行 detail capture CAPTURE 的真实 FotMob 请求：即使
  `make data-fotmob-detail-capture-execute` 已实现，也必须满足全部授权门
  （--execute、CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE=1、CONFIRM_MAX_FOTMOB_REQUESTS、
  authorization-id、expected-plan-sha256、max-requests、clean worktree、40-hex
  HEAD、仓库外非 symlink 输出根、非 symlink plan、安全 run-id；make 层另要求
  NETWORK_AUTHORIZATION=yes，任何变量缺失在 Node 之前失败）并另行获得用户明确
  授权（canonical 入口 ≠ 已获授权）。
- 不把 FOTMOB_REAL_CAPTURE_READINESS 写成已授权里程碑或已有独立 Issue/tag。
- 不重建 M3 staging 已完成的任何模块（防重复开发，AGENTS.md §2.1）。
- 不新增 Phase/ADG 编号脚本、report、manifest（M2 增长冻结，AGENTS.md）。
- 不修改本任务授权文件集合之外的任何文件（该限制仅适用于本文档 PR #1814 的修复任务，合并后不再生效；后续已授权的任务按其自身授权范围执行）。

## 链接

- 仓库结构：docs/PROJECT_MAP.md
- 能力索引：docs/CAPABILITY_INDEX.md
- FotMob 当前状态：docs/data/FOTMOB_CURRENT_STATE.md
- 总体状态与 blocker：docs/PROJECT_STATUS.md
- 业务命令入口：README "Canonical Business Entrypoints"
