# Ingestion Convergence Gate

本文件定义数据入库链路的业务收敛门槛。目标是防止 agent 在 no-write、
planning、review、execution 或 governance 阶段持续产出“小而合规”的 PR，
却没有解除 blocker、没有改变 target 状态、也没有迫使架构决策。

本 gate 不授权 live fetch、detail fetch、network request、DB write、
`raw_match_data` write、re-acceptance、suspension reversal、rollback 或 schema migration。
这些动作仍必须按阶段单独授权。

## 1. 适用范围

以下 PR 属于 ingestion convergence gate 范围：

- data ingestion planning
- source inventory planning / review
- target identity review
- accepted mapping / baseline review
- suspended target review
- blocked target review
- raw write readiness audit
- raw acquisition authorization / preflight / execution
- ingestion governance-only guardrail

以下 PR 不因本 gate 自动获得例外：

- implementation phase
- live source compare
- controlled raw write
- matches seed write
- schema migration
- parser / features / training / prediction

implementation phase 仍必须包含 runtime behavior change。governance-only PR 只能建立规则，
不得声明业务 blocker 已解除。

## 2. Blocker Transition Requirements

每个 ingestion PR 必须在 PR body 中回答：

- 解除哪个 blocker？
- blocker transition 目标是什么？
- 哪些 target 状态发生实质变化？
- 是否有 target 进入 clean / reject / supersede / re-acceptance / new-evidence 路径？
- 如果没有状态变化，为什么仍值得合并？
- 下一步是否 bounded？
- 是否已经是连续第 2 个 no-progress ingestion PR？

PR 必须输出 `target_state_delta`。最小格式：

```text
target_state_delta:
- total_targets:
- moved_to_clean_candidate:
- moved_to_rejected_mapping:
- moved_to_superseded_mapping:
- moved_to_eligible_for_re_acceptance_review:
- moved_to_needs_new_evidence:
- remain_suspended:
- still_blocked_pending_review:
- abandon_current_batch_candidate:
- no_progress_count:
```

`recommended_next_step` 不能替代 `target_state_delta`。只写“下一步继续 planning”
不构成业务进展。

## 3. Target State Taxonomy

`clean_candidate`
: identity、source、baseline 或 hash evidence 已足以进入下一阶段候选池。
它不等于 raw-write authorization。

`remain_suspended`
: 证据仍支持暂停；不得 re-accept、不得 reversal、不得 raw write。

`rejected_mapping`
: 当前 mapping 被判定不可用，后续不得继续把它作为 accepted / baseline / raw-write 输入。

`superseded_mapping`
: 当前 mapping 被新 canonical identity 或新 source evidence 替代。

`eligible_for_re_acceptance_review`
: 可以进入后续 re-acceptance review；不等于 re-acceptance execution。

`needs_new_evidence`
: 现有 source-controlled evidence 不足，必须补充 bounded evidence。
补证可能需要独立 network authorization。

`blocked_pending_review`
: 仍被 blocker 阻断；不得视为 clean，不得 raw write。

`abandon_current_batch_candidate`
: 当前 batch 已无法通过局部 review 收敛，应进入 architecture decision gate。

## 4. Bounded Review Rule

expanded review planning / execution 必须 bounded。PR 必须声明：

- target 上限和具体 target scope
- evidence source scope
- 允许的 review decisions
- 禁止的 decisions
- 完成条件
- stop condition
- no-write / no-network / no-DB 边界

bounded review 不得无限接下一轮 bounded review。一次 bounded review 后如果仍没有任何
clean、reject、supersede 或 re-acceptance candidate，下一步必须是 architecture decision gate。

## 5. No-Progress Stop Rule

no-progress 定义：

- 没有解除 blocker
- 没有 target 状态实质变化
- 所有 target 仍是 remain_suspended 或 blocked_pending_review
- 只新增 planning / review / report / manifest metadata
- 下一步仍建议继续 planning / review

连续 2 个 ingestion governance / review / planning / execution PR 满足 no-progress 时：

- 必须停止自动开下一轮 phase
- 不得继续 expanded review planning
- 不得把 no-progress report 当作 business progress
- 必须输出 architecture decision gate

如果用户明确要求继续 no-progress 路线，PR 必须记录人工确认和理由。

## 6. Architecture Decision Gate

architecture decision gate 必须明确选择或请求人工选择以下方向之一：

- abandon current batch
- rebuild canonical identity pipeline
- redo source inventory strategy
- switch data source / compare alternative source
- redesign FotMob identity mapping strategy

decision gate 输出必须说明：

- 当前 blocker 为什么无法靠下一轮 review 消除
- 已尝试的 bounded evidence 范围
- 受影响 target 数量
- 推荐方向
- 被拒绝的方向和原因
- 进入下一阶段需要的授权

decision gate 可以是 governance / architecture PR，但不得把它包装成 execution result。

## 7. Raw Write Boundary

review / planning / execution 结果不得自动放行 raw write。

raw write 仍必须重新确认：

- final DB-write authorization
- exact target scope
- baseline hash gate
- no hash drift
- FK / matches prerequisite
- no partial write policy
- no parser / features / training / prediction
- no full body / full pageProps save or print

`clean_candidate`、`eligible_for_re_acceptance_review` 或 `needs_new_evidence`
都不是 raw-write authorization。

## 8. Reviewer Checklist

reviewer 应拒绝缺少以下信息的 ingestion PR：

- PR type
- blocker removed
- blocker remaining
- target_state_delta
- no-progress justification, if applicable
- bounded review scope, if applicable
- architecture decision gate trigger status
- next step bounded status
- safety status
- artifact size
- no full snapshot / no large artifact statement

如果 PR 只增加 report、manifest 或 proposal tail，却无法说明状态迁移，默认视为 no-progress。
