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
4. **阶段A 三项（出处：PR #1813 Debt Impact，P3-1 / P3-2）**：
   - malformed `reason.short` fail closed（P3-1）
   - started=true + postponed 矛盾组合 fail closed（P3-1）
   - canonical-v2 核心层强制 40-hex（40 位小写十六进制）Git SHA（当前仅在 CLI 层强制，P3-2）
   注意：P3-3（v1 paired-write 弱点）**不属于**阶段A（PR #1813 Debt Impact 第 3 项，
   标注 unchanged scope）。阶段A 的出处仅为 PR #1813 正文 Debt Impact，不是既有文档决策。
5. **FotMob 公共条款 / 使用边界审查**：属 FOTMOB_REAL_CAPTURE_READINESS 范围，
   后续独立研究，未授权。
6. **单页面 shape probe**：必须单独授权（Issue #1793 评论明确 "requires a separate
   user authorization"）。
7. **三赛季真实采集**（2022/2023–2024/2025 范围的网络抓取）：未授权。
8. **生产 import schema 与真实写入**：需后续单独授权（须先满足 status-complete
   artifact、FotMob endpoint/capture/licence provenance、disposable proof、
   dedicated sandbox/ACL/backup-restore 等 Gate，见 Issue #1793 评论）。
9. **训练 / 回测 / 预测**：仍禁止 / 未授权（README canonical 表、CLAUDE.md）。

## 当前授权下一步

- 只读审计与阅读（无需另行授权）：docs/data/FOTMOB_CURRENT_STATE.md、docs/PROJECT_STATUS.md、
  PR #1813 证据、Issue #1793 记录。
- 文档维护（不自动执行：需用户明确确认后方可发起，且连续 governance/docs-only PR 须人工确认）：
  本文档与 docs/CAPABILITY_INDEX.md、docs/PROJECT_MAP.md 的 current-state 更新。
- 等待主会话 / 用户对下一授权步骤的明确指令（如阶段A 实现、writer implementation review）。

## 明确停止边界（不得越界）

- 不执行任何真实网络抓取、浏览器自动化、DB 写入、migration、artifact 写盘、
  训练、预测或生产操作。
- 不把 FOTMOB_REAL_CAPTURE_READINESS 写成已授权里程碑或已有独立 Issue/tag。
- 不重建 M3 staging 已完成的任何模块（防重复开发，AGENTS.md §2.1）。
- 不新增 Phase/ADG 编号脚本、report、manifest（M2 增长冻结，AGENTS.md）。
- 不修改本任务授权文件集合之外的任何文件。

## 链接

- 仓库结构：docs/PROJECT_MAP.md
- 能力索引：docs/CAPABILITY_INDEX.md
- FotMob 当前状态：docs/data/FOTMOB_CURRENT_STATE.md
- 总体状态与 blocker：docs/PROJECT_STATUS.md
- 业务命令入口：README "Canonical Business Entrypoints"
