# Agent Workflow Hardening

本文件约束 Codex / AI agent 在本仓库中的工程作业方式。目标是防止 implementation phase 退化为文档堆叠，防止 report / manifest 失控膨胀，并让每个 PR 都能明确回答：解决了什么系统问题、代码行为是否变化、还剩什么 blocker。

## 1. 核心原则

- 代码解决问题，测试证明问题，文档解释问题。
- implementation phase 必须推动 runtime 行为变化。
- docs、reports、manifests、proposal metadata 不能替代 implementation。
- 每个 PR 必须声明 PR type、business progress、安全边界和剩余 blocker。
- 变更范围必须可 review；禁止把大型 phase snapshot 当作默认推进方式。

## 2. PR 类型

每个 PR 必须选择且只选择一个主类型：

- `runtime-code-change`: 修改 runtime code path，并改变可执行系统行为。
- `governance-only`: 只调整规则、流程、runbook、模板或作业约束。
- `docs-only`: 只更新说明性文档，不改变流程规则和系统行为。
- `test-only`: 只新增或修正测试，不改变 runtime 代码。
- `ci-fix`: 只修复 CI、lint、format、dependency gate 或构建配置。
- `data-artifact`: 只更新已授权的数据 artifact、manifest delta 或 source-controlled metadata。

辅助类型可以在 PR body 说明，但不能掩盖主类型。例如 implementation phase 如果没有 runtime code behavior change，不能标成 `runtime-code-change`。

## 3. Implementation PR 验收标准

implementation PR 必须同时满足：

- 修改 runtime code path，例如 `src/`、`scripts/ops/`、配置加载、门禁入口或真实执行路径。
- PR body 明确列出改动的 runtime code paths。
- 行为变化可以被 reviewer 从 diff 中验证。
- 测试优先覆盖行为结果、阻断条件、边界输入和失败路径。
- docs / reports / manifests 只作为结果说明或必要 metadata，不作为主要交付物。

以下情况默认 No-Go：

- 只修改 `docs/_reports`、`docs/_manifests`、tests 或 proposal metadata。
- 只新增 phase report，没有改变实际执行路径。
- 只把字段名加入文档或测试 allowlist，没有修复导致 blocker 的代码。
- 无法安全实现 runtime change，却用 report 宣称 implementation 完成。

如果确实不能安全改 runtime code，必须停止并输出 No-Go 报告，说明 blocker、风险、需要的授权或设计决策。

## 4. Governance-only PR 限制

governance-only PR 允许建立规则、模板、runbook 或安全边界，但必须满足：

- PR body 明确写 `no runtime code changed`。
- 不声称解除业务 blocker。
- 不把 recommended next step 推进成 implementation done。
- 不创建大型 phase snapshot。
- 不把 governance artifact 写成事实执行结果。

连续 governance-only PR 超过 1 个时，必须人工确认是否继续治理路线。没有人工确认时，应停止并做 architecture review 或转入真正的 runtime implementation。

## 5. Docs / Report / Manifest 体积规则

新增或修改 artifact 必须最小化：

- report 只记录本阶段 delta、关键结论、验证命令和剩余 blocker。
- manifest 优先记录 current effective state，不复制完整历史状态。
- phase artifact 只记录该 phase 的输入、输出和 delta。
- 不得为每个微小状态变化复制整份大型 manifest。
- 大型 raw body、完整 pageProps、完整 source body 不得提交到 git。
- 大型诊断输出应优先作为 CI artifact、本地临时文件或 archive 方案，并单独说明保留策略。

PR 模板必须披露：

- 新增/修改 report 行数。
- 新增/修改 manifest 行数。
- 是否复制完整历史状态。
- 是否包含 large artifact。
- 如果包含 large artifact，必须说明为什么不能最小化。

## 6. Current State Manifest 原则

source-controlled manifest 应表达当前有效状态，而不是无限增长的阶段日志。

推荐结构：

- 顶层保存当前 batch、source、route、data_version、hash_strategy 和 next required action。
- per-target 保存当前有效 identity、baseline、blocker 和安全状态。
- 历史 phase 只保存必要引用、hash 或短摘要。
- 已废弃字段保留时必须标记 deprecated，并说明 reader 是否仍使用。

禁止结构：

- 每个 phase 都把全部 targets、历史状态和所有字段完整复制一遍。
- 为了通过测试而保留无实际 reader 的冗余字段。
- 在 manifest 中保存 full payload、full body、full pageProps 或敏感来源内容。

## 7. Large Artifact 归档原则

大型 artifact 不应默认进入 `main`。如必须保留：

- 先判断是否可以只保留 hash、row count、schema summary、sample path 或 CI artifact link。
- 如果必须 source-control，必须使用 archive 路径或明确的 retention policy。
- archive 变更不得和 runtime implementation 混在同一个 PR，除非它是该实现的必要输入。
- 不做大规模历史清理，除非用户明确要求并单独开 PR。

## 8. Testing 原则

测试应优先证明系统行为：

- 对 runtime-code-change，至少覆盖成功路径、阻断路径和关键安全边界。
- 对 data gate，覆盖 no-write、no-network、no-full-payload-print/save、hash gate、identity gate。
- 对 DB 相关变更，写入前必须有 SELECT-only preflight；写入必须单独授权。
- 对 docs-only / governance-only，可以做 markdown、link、template 或 policy lint，但不得声称业务逻辑被验证。

文档字段测试从严：

- 只允许验证对系统 reader、gate 或 reviewer 有实际意义的字段。
- 不得用 allowlist 扩张掩盖真实 blocker。
- 不得把 recommended next step 字段变化当作业务推进证明。

## 9. Stopping Rules

出现以下任一情况必须停止，输出 No-Go 或 architecture review：

- implementation phase 没有 runtime behavior change。
- 连续 planning / governance 阶段没有移除 blocker。
- report / manifest 行数增长明显超过代码改动，且无法证明必要性。
- 测试主要验证文档字段，而不是 runtime behavior。
- PR body 无法说明 business progress 或 blocker removed。
- 下一步需要 live fetch、detail fetch、network request、DB write、raw write、re-acceptance、rollback 或 schema migration，但缺少明确授权。

## 10. Safety Disclosure

所有相关 PR 必须明确声明：

- no live fetch / detail fetch / network request 状态。
- no DB write / no raw_match_data insert / no matches write 状态。
- no raw write execution 状态。
- no re-acceptance / suspension reversal / rollback 状态。
- no parser / features / training / prediction 状态。
- 是否保存或打印 full body、full JSON、full raw_data、full pageProps。

如果某项被执行，必须列出授权来源、命令、范围、写入表、row count 和回滚/验证结果。

## 11. Review Expectations

reviewer 应能在 PR 中快速看到：

- PR type。
- runtime behavior 是否变化。
- 改了哪些 runtime code paths。
- business progress 是什么。
- blocker removed 是什么。
- blocker remaining 是什么。
- artifact 是否最小化。
- 测试是否证明行为。
- 安全边界是否保持。

如果这些信息缺失，PR 默认不应合并。

## 12. Workflow Sequence

默认顺序：

1. 读现有代码、规则、manifest 和相关测试。
2. 确认 PR type 与授权边界。
3. 对 implementation，先改 runtime 行为，再补行为测试。
4. 只写必要 docs / manifest delta。
5. 运行范围匹配的验证。
6. 填写 PR 模板，明确 business progress 和剩余 blocker。
7. CI green 后再合并。

这套顺序不能绕过既有 L1/L2/L3、DB、raw write、network、schema migration 授权规则。
