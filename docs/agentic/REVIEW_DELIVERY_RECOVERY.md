# 审核交付恢复候选 — 未启用

- lifecycle: permanent
- owner: engineering workflow governance
- status: PROPOSED / BLOCKED_PENDING_QUALIFICATION_AND_OWNER_ADOPTION
- authority: 仅解释候选；正式 authority 仍为 `AGENTS.md`、`review_policy.py` 和既有 Gate。

## 问题与最小边界

NORMAL/STRICT/CRITICAL 风险分级合理。当前 CRITICAL 固定绑定两个 backend，把服务可用性变成永久交付依赖；NO_VERDICT 无法证明代码质量。本候选复用成熟 Official Codex 的独立会话、工作区和 receipt 合同，不导入 PR1938 的复杂 DeepSeek CLI 专用传输。它不注册新 active backend、不改现行 receipt 或 AI Workflow Gate、不放行自身或 PR1937。

`review_recovery.py` 是已实现的确定性资格/替代/独立性预览器，不是 provider runner。输入必须来自未来 backend validator 的真实观察事实；CLI 输入事实只能用于 preview，不能作为 receipt。输出 `dispatch_authorized=false`、`merge_ready=false`、`manual_approval_required=true` 恒定，无启用参数，CLI 永不返回 approval exit 0。`PROPOSED_EVIDENCE_COMPLETE` 也不是 SATISFIED。

## 推荐策略与资格

| 风险 | 推荐选择（资格通过并单独批准后） | 审核次数 |
| --- | --- | --- |
| NORMAL | 优先合格 Official OpenAI；合格经济 reviewer 可预先指定 | 1 |
| STRICT | 高可靠 Official OpenAI profile；替代需同风险资格 | 1 |
| CRITICAL | Official OpenAI 主审 + 合格跨厂商第二审优先；第二审服务失败可使用合格不同模型的 Official GPT 第二 profile | 2 真正独立的成功审核 |

同厂商必须标记 SAME_PROVIDER；不同模型、独立会话、不同只读工作区、不看其他 reviewer 结论、同 base/head/diff/mission/scope。两份同模型报告不在本候选的双审资格范围内。授权、认证、资金、恢复与审核治理变更还要求独立的人工风险验收；AI 双审不能代替 Owner 的治理采用及业务合并两次批准。

资格必须绑定 profile 的确切 provider/model/mode/prompt-harness-transport recipe hash、风险 eligibility、原始证据 hash、独立性和完整性合同，不能只用厂商名字或一次 PASS。模型/模式/工具链变更需重新资格验证。质量语料应包含真实良性改动、可验证 P0/P1/P2 历史缺陷、跨文件与删除任务，不给 reviewer 提供 ground truth 或其他 reviewer 结论。需验证缺陷检出、误报、重复性、终止行为和总交付成本。

目前资格状态：

| Profile | 现有证据 | 本候选资格 |
| --- | --- | --- |
| canonical codex-cli / gpt-5.6-terra medium | 正式 active reviewer，官方登录恢复，历史真实审核 | 现行能力保留；新四次物理上界 recipe 未证明，不能在本任务调用 |
| Direct DeepSeek non-thinking | 一次真实有界单块 verdict | FEASIBLE，不是 QUALIFIED |
| 第二 Official GPT profile | 尚未选择/验证不同模型及双会话 recipe | NOT_QUALIFIED |

没有把这些 profile 虚构为新的 QUALIFIED registry。输入 qualified fixture 只验证状态机行为，不提供模型质量证明。

## 故障与预算合同

每个 slot 预先固定至多两个 profile，最多一次替代，同一 profile 不重复。CRITICAL 两个 slot 的总物理上界最多4，每个 invocation 必须证明最多1次物理请求；输出不超过16384 tokens，输入保守上界不超过1048576，wall不超过900秒。实际 profile 可更低。替代只能因完整可验证的 TIMEOUT / OUTPUT_EXHAUSTED / SERVICE_UNAVAILABLE / AUTH_FAILURE / NO_VERDICT；不能因有效 FAIL、P0/P1/P2、证据损坏、覆盖缺失、身份不符或未知状态触发。

任何有效 P0/P1/P2 均先阻断，包括最终未使用的 reviewer；修复后新 HEAD 重新审核。P3记录不阻断。UNKNOWN传输或 usage 保留每次完整reservation并停止。预览输出保留每次 evidence hash、物理尝试和 input/output reservation；它不结算、不改 ledger，也不发 provider 请求。未来 runner 的实际单次传输约束和 backend validator 的 provenance 证明仍是启用前必要条件。

## 完整性及删除内容

`python3 -m scripts.devops.review_coverage` 导出 source tree 外 owner-only 材料；包含现行 receipt 使用的完整 binary three-dot diff、真实 effective merge-base、全部变更路径和全部前后 blob 原始字节，逐个记录 Git OID、长度、SHA256、external artifact。`--verify` 重新从 Git 核对全部字节、manifest、文件集合和权限；删除/截断/替换 blob、漏路径、额外摘要、身份不符皆拒绝。

这是材料完整性证明，不是模型语义审核证明。所有 reviewer 必须实际取得完整 diff 和必要上下文；不允许用 inventory/摘要当作完整审核。不引入 compact representation。大型删除可以从精确只读 Git/外部材料按需读取，仍需已资格的 reviewer 完整性合同；目前没有新原生 API receipt 验证器来证明这种动态读取，不据此授权业务 PR。

PR1937 的外部材料已可对齐当前 base/head；相关静态/动态加载、构建、恢复与功能回归仍须未来正式验收。其现有 mission invariant 明确要求 Official OpenAI 与 Direct DeepSeek；新通用 policy 本身不能覆盖这个 mission-specific 限制。若未来要采用 SAME_PROVIDER，Owner 还必须明确批准对应 mission 的纯治理元数据迁移；不能改变瘦身内容或风险级别。

## 安全治理迁移

1. 本 Draft 仅交付 preview、完整材料工具及接入现有 canonical Python Gate 的负面测试；旧政策和合并门禁仍生效，PENDING不得改成PASS。
2. 在独立限额内取得候选 recipe 的真实质量/独立性/完整性/执行上界证据。不能把 unbounded canonical CLI invocation 当成一个物理请求。本任务最多4次；不能证明上界的 reviewer 不调用。
3. 治理候选自身需要旧规则的 exact-head 双 receipt、Hosted CI及构建。若旧规则与实验上界不能兼容，停止在 Owner bootstrap 决策关口，不编造“全绿”。Owner 可以另行授权有限资格预算及明确、精确 HEAD 的迁移验收方案；这不是自动免审或当前合并许可。
4. 只有 qualification 和 Owner明确采用完成，才可另行进行最小生产接线：复用现有 validators，将 profile/runtime/覆盖身份纳入 receipt，公开替代日志和 SAME_PROVIDER，按现行 classifier 校验风险。不能让候选改规则后批准自己。
5. Owner单独合并合格治理 PR后，才启动PR1937正式审核、真实回归、Hosted Production Gate、完整生产Docker build；再单独申请业务合并批准。

## PR1938 成本收益

建议暂停进一步扩张 PR1938，保留 Draft 与诊断证据，不关闭/删除。本候选替代其交付恢复方向；不要求为2.51MB瘦身长期维护特定厂商 CLI/分片/推理调优体系。跨厂商盲点分散有价值，但服务绑定并不是质量证据；SAME_PROVIDER具有模型家族共同盲点，需不同模型、负面语料和人工敏感风险验收，不能伪称等价跨厂商。
