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
- 本任务基线（PR base；main 在合并本 PR 后将前移，不再等于该 SHA）：
  `635773a7e8015b8e4e4e4293fa4ac4db8cb7f7a9`（PR #1813 merge 后；
  post-merge main gate 结果以主会话最终核验为准）
- 最近完成：**PR #1813** — FotMob v2 provenance export（provider status、dual hash、
  raw retention + capture manifest、clean-worktree 40-hex git revision 绑定、
  unknown / started fail closed、v1 输出路径不变）
- 关键 current-state 文档：docs/data/FOTMOB_CURRENT_STATE.md、docs/PROJECT_STATUS.md

## 已完成（勿重复）

- M3 离线主线 → D4F：离线 staging pipeline、CSV recovery、确定性候选导出与身份、
  D4B 持久化合同（38,616 accepted / 216 quarantined 冻结合同）、
  D4C / D4E 受控 synthetic 写入验证（1 run / 1 source / 6 accepted / 3 quarantine）、
  D4D readiness 评审、D4F 交叉来源审计
  （888 exact / 4 kickoff conflicts / 248 canonical-only / 252 无 exact link /
  1,140 候选总人口）。
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
- **FOTMOB_DETAIL_STAGING_CONTRACT_IMPLEMENTATION_REVIEW_OFFLINE_ONLY（Draft PR，待评审；PR #1817 阻塞问题修复已离线完成）**：
  独立评审 8 项阻塞问题全部离线修复 —— 纯离线 detail staging converter/validator 已实现并全量测试 ——
  `make data-fotmob-detail-staging-{help,receipt,build,validate}`（直接 Node CLI
  `scripts/ops/fotmob_detail_staging.js` 为 internal engine）将归档的
  capture payload+manifest 对转换为不可变 `fotmob-detail-staging-artifact/v1`
  快照：5 个 versioned JSONB sections 逐字节保留、直接复用 pipeline 捕获
  hashing（无自实现副本）、确定性 observation_id（RFC 4122 UUIDv5）+ generated_at
  字节精确取自 manifest 的 source_response_received_at、canonical_match_id 恒
  null + UNLINKED_NOT_ATTEMPTED、append-only 文件 store + 编号
  store-state-<seq>.json 账本版本（无数据库、无 migration）、每次写入
  O_EXCL tmp+fsync+同文件系统 rename 的 per-file 原子写 + 独占 per-store lock、
  冲突 fail-closed、LOGICAL_COMMIT_MARKER 唯一提交点（residue 报告不当作已提交）、
  -validate 重验 artifact/summary/store ledger（MODE_1_UNANCHORED /
  MODE_2_EXTERNALLY_ANCHORED）。249 项 staging 测试 + 395 项受影响旧测试全绿，
  ESLint/git diff --check 干净；16 场归档（one/five/ten-match pilot
  archives）两次 build + 两次 validate 字节一致、ID set 精确一致、
  canonical_match_id 全 null、无 HTML/凭据/绝对路径，派生输出已删除。
  marker_event（parser 注入 AddedTime/Half 分钟标记、无 id 设计）记录为合法
  变体（真实 16 场均有 4 个）。零网络、零数据库、零采集、无真实 payload/
  manifest/artifact 提交；PR 保持 Draft、未合并。

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
  249 项 staging 测试（79 retention 故障注入/篡改 + 57 source verification +
  70 contract [54 个显式声明 + 16 个 PAIRS 循环生成的逐字段冲突测试] + 17
  converter + 23 CLI；运行时计数 = node --test # pass，与静态 test() 声明
  的差异仅来自循环生成测试）+ 347 项 legacy FotMob + 769 项 unit 全绿；
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
  尾部 NUL 剥离）也全部离线修复并补回归测试（249 项 staging 测试全绿，含
  round-6 的 5 项发现修复：R6-P1-1 validate 失败退出码、R6-P1-2 observed
  球队必填 + artifact 身份语义、R6-P2-1 导出 API 严格类型合同、R6-P2-2
  quarantine key/entry/file/summary 语义三方绑定、R6-P3-1 archive
  input gate 非重叠检查）；
  零网络、零数据库、零采集、无 migration；PR 保持
  Draft、未合并，等待外部独立实现验收。
- **FOTMOB_BOUNDED_AUDITABLE_DETAIL_CAPTURE_PIPELINE（本 PR，待合并）**：已实现并
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

1. **M3 主线收尾未完成**：Issue #1793 保持 open —— historical odds staging/import
   主线尚未完整收尾。
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
6. **生产 import schema 与真实写入**：需后续单独授权（须先满足 status-complete
   artifact、FotMob endpoint/capture/licence provenance、disposable proof、
   dedicated sandbox/ACL/backup-restore 等 Gate，见 Issue #1793 评论）。
7. **训练 / 回测 / 预测**：仍禁止 / 未授权（README canonical 表、CLAUDE.md）。

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
