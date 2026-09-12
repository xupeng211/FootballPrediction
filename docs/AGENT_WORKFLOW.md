# Agent Workflow — Detailed Reference

> 状态：current / permanent。`AGENTS.md` 是唯一 operational authority；本文件只解释其规则、示例和异常处理，不创建第二套 policy。

## 1. 设计边界

工作流只有四种 authority：

| Authority | 责任 | 不负责 |
| --- | --- | --- |
| TEST | 证明代码行为正确 | 决定是否合并 |
| CI | 在可重复环境执行验证 | 替代 review 或 owner |
| REVIEW | STRICT 任务判断语义、边界和失败场景 | 运行全部测试或决定合并 |
| OWNER | 接受风险并决定 merge | 伪造测试、review 或 HEAD 证据 |

脚本可以编排这些步骤，但不能成为第五种 correctness authority。Git/GitHub/Actions 是状态事实来源；Markdown 只描述规则，不保存 workflow state、SHA、review state 或 CI state。

## 2. 任务分类

NORMAL 适合局部、低风险变更。STRICT 适合 DB/schema/write、ingestion、identity/auth/security、生产 runtime、training/model activation、关键架构和高影响破坏性行为。无法由现有 path/task classifier 安全分类时按 STRICT 处理，并在 PR `Risk` 说明原因。

NORMAL：

```text
branch/worktree → implementation → make verify-targeted → commit/push
→ PR → required CI → owner decision → squash/approved merge policy
→ main Production Gate exact merge SHA → DONE
```

STRICT：

```text
branch/worktree → base/head snapshot → implementation
→ make verify-strict → PR → required CI
→ one exact-head independent adversarial review
→ fix findings and revalidate current HEAD (CI + new review)
→ owner decision → main Production Gate exact merge SHA → DONE
```

NORMAL 不默认运行本地 Codex review、DeepSeek、codex-loop、manifest/audit package 或 GitHub Codex Review。STRICT 只要求一个 primary independent reviewer；额外意见只能是 advisory，并且不能改变 owner 的 merge authority。
STRICT PR 使用一个最小、provider-neutral 的 `Strict Review Evidence` contract 绑定 review target 与当前完整 PR HEAD。V1 的本地 pre-review 阶段可暂时声明 `Result=PENDING`；它永远不能让 PR merge-ready，也不能通过最终 required remote governance CI。真正的独立 Codex receipt 产生后，Builder 将其更新为 `PASS` 或 `FINDINGS_RESOLVED`。现有 required governance path 同时复用 task/path classifier，拒绝高风险变更用 NORMAL 声明绕过 review；evidence 字段重复或多列也 fail-closed。它不运行 reviewer、不生成 manifest、不决定 merge；GitHub Codex Review 仍是 advisory。

## 3. 验证 profile

WF02 目标是把公开入口收敛为：

```bash
make verify-targeted
make verify-pr
make verify-strict
```

profile 的边界：

- `verify-targeted`：受影响测试、必要 static check 和最小 targeted regression；快反馈，不宣称完整 CI。
- `verify-pr`：通过 `scripts/devops/validation_profiles.py pr` 调用现有 PR gatekeeper；GitHub PR 的
  `Run Gatekeeper` 步骤调用同一个 profile implementation，required failure 必须返回非零。

### Pre-push ref 删除

本地 pre-push Gatekeeper 按 Git 提供的 ref-update 输入分类事务。仅当至少一条更新存在且全部
使用全零 local object ID 表示删除时，才进入纯 ref 删除维护路径并跳过不适用的源代码质量检查。
空输入、解析失败以及删除与更新混合的事务均按完整源代码 push 门禁处理；不存在通用 bypass。
- `verify-strict`：通过同一 dispatcher 调用现有 push/full gate（覆盖率、完整性、安全和 runtime
  smoke）；只用于 STRICT，不把昂贵检查默认施加给 NORMAL。

`ci-local`、`ci-local-pr` 和 `workflow-pr-check` 只是兼容别名，委托 `verify-pr`，不再吞掉失败或维护另一套测试矩阵。旧的 `test` / `test-unit` 是底层测试入口，不是新的 workflow authority；Agent 默认只选择上述三个 profile。

旧 `npm`/`make` 入口可以作为 alias 或 internal implementation，但不得各自维护另一套 test semantics。弃用入口在没有 caller inventory 前只标记，不直接删除。

## 4. PR 模板和内容

唯一默认模板是 `.github/pull_request_template.md`，正文五个部分：

```markdown
## Summary
## Scope
## Tests
## Risk
## Rollback
```

内容必须是实际事实：命令、exit code、覆盖范围、runtime 影响和回滚办法。`Scope` 必须包含 `Workflow class = NORMAL` 或 `STRICT`。STRICT 的 evidence 只包含 version、task type、provider、reviewed full SHA、result 和带时区 timestamp；完整 SHA 必须等于当前 PR HEAD。普通 PR 不生成空 finding、manifest、snapshot 或 phase report。高风险路径需要的授权信息只在该 PR 的 `Risk` 之外按模板提示增加，不为 NORMAL 增加状态机式正文。

### 4.1 Current-state documentation backflow

`AGENTS.md` 的 2.1 是操作要求；具体文档映射由
`docs/DOCUMENTATION_GOVERNANCE.md` 维护，二者不创建新的 authority。涉及长期能力或状态的任务开始前要声明
`EXISTING_CAPABILITIES_REVIEWED=YES` 和 `CURRENT_MILESTONE_REVIEWED=YES`；结束前要判断
`CAPABILITY_INDEX_UPDATE_REQUIRED`、`ACTIVE_MILESTONE_UPDATE_REQUIRED`、
`PROJECT_STATUS_UPDATE_REQUIRED`、`README_ENTRYPOINT_UPDATE_REQUIRED` 和
`PROJECT_MAP_UPDATE_REQUIRED`。涉及长期能力或目标架构时，还要先阅读
`docs/PROJECT_VISION.md` 并确认 `VISION_ALIGNMENT_REVIEWED=YES`：说明能力对应的目标层、
可复用资产、当前缺口和是否偏离 North Star。结束时同时判断
`PROJECT_VISION_UPDATE_REQUIRED`。普通 bugfix 若不改变长期语义，不要求修改 vision。
PR 的 `Documentation Impact` 以 yes/no 字段表达这些判断。

现有 `AI Workflow Gate` 会根据少量稳定 changed-path 分类检查：能力变化是否回写
`docs/CAPABILITY_INDEX.md`，里程碑变化是否回写 `docs/ACTIVE_MILESTONE.md`，canonical
入口变化是否同时回写 `README.md` 与能力索引，blocker 变化是否回写
`docs/PROJECT_STATUS.md`，以及仓库结构/authority navigation 变化是否回写
`docs/PROJECT_MAP.md`。如果 PR 改变 North Star、target architecture 或将 vision 中的能力
推进到新的 maturity 状态，必须回写 `docs/PROJECT_VISION.md`；vision 的正向声明不能用
no-update reason 绕过。没有改变长期语义的 bugfix（包括 vision=no）可以填写具体 no-update
reason；空泛理由会失败。

## 5. Review freshness

review 记录必须绑定完整 PR HEAD。有效性不依赖 reviewer 口头说 PASS，而依赖：

```text
reviewed_full_sha == current_pr_head_full_sha
```

source change、rebase、amend 或 force-push 后，旧 review 自动视为 stale；必须重新 review 或明确降级为 advisory。现有 `ai_workflow_gate.py --block-matrix` 路径在 STRICT PR 上拒绝缺失、格式错误、重复字段、声明绕过或 stale evidence，不新增第三个 required check。GitHub Codex Review 当前是可选 second opinion，不是 required check，也不等于 approval。

## 6. CI 和 merge freshness

当前 GitHub ruleset 观察到的 required checks 是：

```text
Environment / Proxy / Static / Unit Gate
Docker Build Validation
```

规则可能由 owner 在 GitHub 上改变；报告时以 ruleset API 和实际 run 为准。PR source change 必须产生验证新 HEAD 的 run，不能复用历史 green run。merge 后必须记录实际 merge SHA，并确认 main push Production Gate 验证同一完整 SHA；仅有 PR green 或“已 merged”不算 DONE。

完整 SHA 的共享实现是 `scripts/devops/exact_head.py`。`pr_ready_check.py`、CI event
ref helper 和 post-merge evidence check 必须通过这个 primitive 做 freshness/authority
比较；任何同前 7 位但完整 SHA 不同的值都必须判为 stale 或不匹配。

## 7. `pr-ready` 的职责

唯一的 merge-readiness 状态预检是：

```bash
make pr-ready PR=<number>
make pr-ready PR=<number> JSON=1
```

其 canonical implementation 是 `scripts/devops/pr_ready_check.py`。它只读 Git/GitHub 当前状态并失败关闭，检查：

- PR 为 open、非 draft、目标为 default branch，且有基本 title/body；
- 当前 worktree 在 feature branch、branch 与 PR head branch 相同、无 dirty path；
- 本地 HEAD 与 PR HEAD 是相同的完整 40 字符 SHA；
- active ruleset 为 default branch 声明的每一个 required status check，都以相同完整 SHA 成功完成。

它不重跑测试、不重跑 review、不生成 audit package/manifest、不把 SHA/run ID 写入 PR body、不修改 PR、不 merge、不清理 branch。它是 `GOVERNANCE CHECK`，不是 TEST、CI 或 REVIEW。

历史 `pr-body-check`、`pr-merge-preflight` 和 `pr-ready-check` 路径只委托该实现；不能再维护自己的判断逻辑。`pr-gate-local` 是本地 PR gate parity helper，负责静态/安全扫描，不是 merge readiness，也不替代 GitHub required CI。`ai_workflow_gate.py` 仍由 CI 调用，负责 PR 内容和危险变更治理检查，但不是 reviewer。

## 8. 异常处理

- Docker 不可用：报告环境 blocker，不绕过容器限制运行业务命令。
- required test 失败：保留非零 exit，修复或停止；不得把 advisory 命令命名为 `ci`/`verify`。
- PR HEAD 改变：重新计算 exact-head 状态并使旧 review/CI 结果失效。
- GitHub API 无权限：标记 `UNKNOWN`，不把缺失数据当作 green 或 approval。
- 文档与机器状态冲突：以 Git/GitHub/Actions 为准，修正文档时保留证据，不创建新的平行规则。
- 不能安全完成 runtime change：No-Go；不得用 report、manifest、test-only 或 phase metadata 伪装进展。

## 9. 证据格式

每个阶段至少记录 branch、base SHA、head SHA、changed files、命令和 exit code、GitHub PR/run、验证 SHA、remaining risks 和 deferred items。判断使用三种标签：

- `CONFIRMED`：机器输出、文件引用或 GitHub API 直接证明。
- `INFERRED`：由多个证据推断，但没有单一强制点。
- `UNKNOWN`：证据不足或权限不可用。

最终报告必须把 TEST、STATIC CHECK、REVIEW、CI、GOVERNANCE CHECK 分开，不能统称“验证”。

## 10. 变更与回滚

workflow 收敛按 WF01–WF06 分阶段完成。每阶段独立 branch/commit/PR，先通过本阶段 acceptance 再进入下一阶段；前四阶段不大规模重写 `scripts/devops/gatekeeper.sh`。任何阶段发现真实 caller、远端规则或生产风险与旧假设不符，应记录 `AUDIT_ASSUMPTION_CHANGED`，停止危险 cleanup，保留 UNKNOWN 项。

## 11. Agentic Engineering Workflow V1（当前 canonical contract）

本节把 Builder、reviewer 和 controller 的职责固化为可执行合同。它服务于
“一次 bounded mission 内自主闭环，merge 前停止”的工程目标；不改变 Stage D
业务合同、provider 配额、request accounting、identity、transaction authority 或生产授权。

### 11.1 角色与权限边界

| Role | 必须做 | 明确不能做 |
| --- | --- | --- |
| `EXECUTION_CONTROLLER` | 定义 bounded mission、protected invariants、审阅 `MERGE_READY` 证据并作最终 merge/gate 判断 | 不把 Builder 的自证当作 Chief Engineer Gate；不要求每个窄修复逐步确认 |
| `BUILDER` | 实现、测试、维护同一 PR；自主修复当前 mission 内 CI/preflight/reviewer finding；在每次 HEAD 变化后重跑验证 | 不自授予 independent review；不 merge；不跨 mission/gate/provider/production 边界 |
| `INDEPENDENT_REVIEWER` | 新 Codex process/session/context，在 exact HEAD 的 detached read-only worktree 做 adversarial review，输出 receipt | 不修改 Builder tree、commit、push、merge 或静默修复 finding；不把 Builder reasoning 当证据 |
| `CHIEF_ENGINEER` | 独立接受/拒绝重大项目 Gate | 不被 merge-level code review 或 PR green 替代 |

### 11.2 Builder 自主修复决策模型

共享机器合同是 `scripts/ops/helpers/agent_workflow_contract.py`；未知类别默认
`ESCALATE`。以下类别在当前 mission 内可以 `AUTO_REMEDIATE`：

- compile/syntax、lint、format、当前 patch 引起的 test/integration failure 和 CI failure；
- Task type、Workflow class、Documentation Impact、PR body schema；
- report/script lifecycle、governance preflight、growth-freeze 触发的窄修复；
- 当前 mission 直接归因的 reviewer 窄 defect、缺失 negative test、准确描述当前变更所需的文档修正。

以下类别必须 `ESCALATE`：scope expansion、新产品要求或架构决定、Chief Engineer Gate、protected invariant 语义、显式排除 blocker、quota/request-accounting/identity/transaction-authority 语义、provider/production mutation、真实请求、destructive action、secret、security broad design、CI bypass、STRICT weakening 或 self-merge。

Builder 的动作循环为：

```text
bounded mission
  → local preflight (`make agent-preflight`)
  → target validation (`make verify-targeted` / `make verify-pr` / `make verify-strict`)
  → commit/push/update PR
  → current-head required CI
  → fresh independent Codex review
  → blocking in-scope finding? Builder 修复并使旧 receipt/CI freshness 失效
  → new exact HEAD: local validation + CI + fresh review
  → CI terminal green AND clean exact-head review
  → `make agent-merge-ready`
  → STOP AT MERGE GATE，交回 Execution Controller
```

`make agent-preflight PR_BODY=<path> MISSION_SCOPE_FILE=<path>` 的静态结果与 CI 的
`AI Workflow Gate` 共用 `validate_pr_metadata()`、现有 `pr_authorization_matrix.py`、
`strict_review_evidence.py`、`governance_growth_gate.py` 和 lifecycle helpers。路径
授权不属于永久 workflow policy；它来自当前 bounded mission 提供的、已纳入候选
HEAD 的 `schemas/agentic/mission_scope.schema.json` 合同（通常放在
`docs/agentic/missions/<mission-id>.json`）。合同必须明确 mission ID、task/workflow、
authorized/excluded paths or prefixes、protected invariants 和 forbidden side effects；
缺失、无效或空授权一律 fail-closed，exclude 优先且匹配按目录边界执行。当前 mission
的 preflight 会验证这个文件的字节与待审 exact HEAD 一致；不会把另一个 mission 的
路径列表当作默认值。远端永久 PR gate 只启用可复用的 metadata/lifecycle 合同，不
自动启用任何 bootstrap mission scope；只有显式提供 scope context 的受控调用才做
mission-scope check。merge readiness 和 reviewer 会再次读取同一 scope contract。
PR context、GitHub ruleset 和 required check runs 仍只能由 `make pr-ready PR=<number>`
读取。

### 11.3 Codex independent reviewer 与 receipt

canonical runner 是 `scripts/devops/codex_independent_review.py run`（receipt 证据读取与内部
一致性证明在 `scripts/devops/codex_review_receipt.py`，三态分类在
`scripts/devops/codex_review_classification.py`），入口为
`make agent-review BASE_SHA=<full SHA> HEAD_SHA=<full SHA> MISSION_ID=<id> MISSION_SCOPE_FILE=<path> EVIDENCE_DIR=<external dir>`。
它必须：

1. 在 exact reviewed commit 创建 detached worktree；
2. 用新的通用 `codex exec` 子进程，通过 stdin 传入审查合同，带 `--sandbox read-only`、
   `--ignore-user-config`、`--ephemeral`、显式 pinned `-m <REVIEW_MODEL>`、显式
   `-c model_reasoning_effort="<REVIEW_REASONING_EFFORT>"`、`--json`、
   `--output-schema` 和独立 `--output-last-message`；review prompt 自带 exact base/head，
   不依赖 Builder 上下文，也不复用 persisted Builder session；
3. 把 raw JSONL、final normal-review JSON 和 receipt 写到 source tree 之外的 owner-only evidence directory；
4. 只从 Codex `thread.started`、唯一成功的 `turn.completed`、唯一已完成的
   `agent_message`、final schema、当前 Git diff 和文件 hash 派生 receipt；raw
   completed message 必须与 `--output-last-message` 字节内容一致，且 exit code 为 0；
   不接受 Builder 传入的 PASS/count/invocation 结论；
5. review 结束检查 detached worktree 仍 clean；任何缺失、非零退出、非 JSON、写入或 context collision 都 fail-closed。

receipt schema 是 `schemas/agentic/codex_review_receipt.schema.json`，至少绑定：schema/contract version、
`assurance_model=engineering_independent_review`、明确的 same-uid residual-risk 标记、Codex engine/role、
base SHA、reviewed full HEAD、完整 diff SHA-256、mission、开始/结束时间、P0–P3 counts、blocking count、
result、finding summaries、Builder/reviewer context IDs、fresh/separate context、read-only isolation、
clean-before/after、raw/final output hashes 和 receipt payload integrity hash。

**Reviewer model provenance（v1.1）。** 当前审批 policy 是 `REVIEW_MODEL=gpt-6-astra`、
`REVIEW_REASONING_EFFORT=medium`。两者必须出现在 canonical invocation 的 argv 中：`-m gpt-6-astra` 和
`-c model_reasoning_effort="medium"`。不允许依赖 user config default、account default、catalog priority、
implicit CLI default 或 environment-selected default；`--ignore-user-config` 必须保持有效。builder 若无法从
command 中解析出这两个 selector，runner 直接 fail-closed，不做任何 fallback。

receipt v2 因此在 `provenance.reviewer_command` 记录完整 executed argv（由 `command_sha256` 绑定），并新增
`model_provenance` 块：`review_model`、`review_reasoning_effort`、`codex_cli_version`，三者都从实际执行的
argv 或从同一 resolved Codex binary 的 `--version` 观察派生（`model_source=codex_exec_model_flag`、
`reasoning_effort_source=codex_config_override`、`cli_version_source=observed_codex_version_stdout`、
`derived_from_recorded_command=true`）。Builder 自报的 JSON 字段不构成证据：validation 重新解析 command、
重新观察 CLI version，并要求 `command_sha256` 与记录 argv 重算一致——model 或 effort 一旦被改写，
command hash 必然改变，receipt 立刻失效。v1 legacy receipt 无法记录 argv，因此它的 `command_sha256`
仍会按冻结的 v1 invocation 形状（不含 model selector 的旧 argv）从 receipt 自己记录的执行路径重算：
旧证据的内部一致性检查不因 model pinning 而消失，伪造的 64 位十六进制 hash 仍算 tamper，而非历史漂移。
v2 还会把记录 argv 与 receipt 其余 evidence 绑定：`--output-schema`、`--output-last-message` 的取值必须等于
receipt 记录的对应路径，argv[0] 必须等于 `codex_binary`。一个自身 hash 自洽、却指向别处的 argv 是与
evidence 矛盾的 tamper，而不是可以由 `REVIEW_POLICY_DRIFT` 解释掉的合法 policy 变化。

**三态 classification。** `validate` / `classify` 输出正交的两个轴：`classification` 与 `integrity`。

- `VALID_CURRENT`：receipt 内部一致、绑定当前 exact base/head/diff/scope/challenge，且当前 toolchain
  （wrapper blob、Codex binary、CLI version、pinned model/effort、canonical command）与实际一致。这是唯一
  可以作为当前 exact-head approval 的状态；`make agent-merge-ready` 只接受它。
- `STALE_TOOLING`：receipt 内部一致且 `INTEGRITY=INTACT`，但被记录的工具链或 policy 之后发生了合法变化
  （wrapper 升级、Codex CLI/binary 升级，或 v1 legacy receipt 早于 model pinning），或者 review worktree
  已不可用。canonical invocation 的 `--output-schema` 指向该临时 worktree，因此 worktree 被正常清理后，
  历史 schema 改为核对 reviewed exact commit 中的 blob，而不是已消失的文件；receipt 仍是合法历史证据，
  但**绝不能**满足 `MERGE_READY=YES`、当前 STRICT approval 或当前 PR merge authorization。schema 因
  其他原因缺失、或存在但与 reviewed commit 不一致，仍然是 `INVALID` / `TAMPERED`。worktree 不可用只
  免除对实际 Git HEAD 的现场核对：receipt 自己记录的 `worktree_head_sha` 与 `reviewed_head_sha` 必须
  始终一致，与 worktree 是否存在无关，两者矛盾仍是 `INVALID` / `TAMPERED`。
- `INVALID`：证据对它自称的 target 不成立——文件或 hash 被改动、base/head/diff/scope/mission 不匹配、
  receipt 声称的 model 或 effort 与 command 矛盾、记录的 CLI version 与 invocation 证据不同。

`validate` 仍会重新计算 exact HEAD/diff、重新解析 raw/final output、核对 invocation/completion 事件、确认
review worktree 仍是 exact-head 且 clean，并检查 receipt/evidence 不在 source tree 且为 owner-only。
`classify --historical-audit` 只做只读分类并总是 exit 0，用于回看旧 receipt，不产生 approval：它有意跳过
current-HEAD freshness 比较，因此即使 receipt 的每个字段仍与已安装 toolchain 一致，也只会得到
`STALE_TOOLING` 与 `HISTORICAL_AUDIT_NO_CURRENT_APPROVAL`，`current_approval_eligible` 恒为 false。
`VALID_CURRENT` 只能由真正执行过 exact-head 比较的路径产生。

这里的 hash 是可审计的 integrity check，不是 cryptographic reviewer identity；同一 OS uid 的恶意 Builder
理论上仍可能改写本地 evidence，这是 Owner 选择的 residual risk。简单缺失/错误/自相矛盾的 PASS JSON 仍会
fail-closed，但本工作流不声称抵抗恶意同 UID 伪造。

P0/P1/P2 均阻塞，P3 不阻塞；这比当前 STRICT provider-neutral evidence 更具体但不削弱 STRICT。reviewer 只写适合普通 code review 的 finding，不写隐藏推理。

### 11.4 Exact-head 与 merge readiness

所有 freshness 使用 `scripts/devops/exact_head.py` 的完整 40 位 SHA primitive：

```text
CURRENT_PR_HEAD != REVIEWED_HEAD_SHA  →  REVIEW_VALID=NO
CURRENT_PR_HEAD != CI_HEAD_SHA        →  CI_VALID=NO
```

`scripts/devops/agent_workflow.py merge-ready` / `make agent-merge-ready` 只读地要求：

```text
MISSION_SCOPE_VALID=YES
LOCAL_REQUIRED_CHECKS=PASS
REMOTE_REQUIRED_CI_TERMINAL_GREEN=YES（有 PR context 时）
INDEPENDENT_REVIEW_PRESENT=YES
INDEPENDENT_REVIEW_RESULT=PASS
RECEIPT_CLASSIFICATION=VALID_CURRENT
RECEIPT_INTEGRITY=INTACT
MODEL_PROVENANCE_VALID=YES
BLOCKING_FINDINGS=0
REVIEWED_HEAD_SHA=CURRENT_PR_HEAD_SHA
PROTECTED_INVARIANTS=PASS
FORBIDDEN_SIDE_EFFECTS=NO
REQUIRED_PR_GOVERNANCE=PASS
```

`MISSION_SCOPE_VALID=YES` 只表示当前 changed paths 通过实际 mission contract；它不从
mission ID、PR title 或 Builder prose 推断授权。`PROTECTED_INVARIANTS=PASS` 与
`FORBIDDEN_SIDE_EFFECTS=NO` 既是必需声明，也必须与当前 exact-head、mission-scope 和
已验证 local preflight 推导出的机器状态一致；调用者单独自报 PASS/NO 不能覆盖缺失或
失败的机器证据。任何 `UNKNOWN`、failed/stale receipt、
PENDING review、缺少 PR context 或缺少 protected-invariant evidence 都返回
`MERGE_READY=NO`。review receipt 必须被分类为 `VALID_CURRENT`：`STALE_TOOLING` 只在历史审计中
有意义，`CURRENT_PR_REVIEW + STALE_TOOLING` 永远得到 `MERGE_READY=NO`，不得把旧证据转换成当前 PASS。命令没有 merge API、push、commit
或 cleanup 分支；`MERGE_READY=YES` 只产生
`READY_FOR_EXECUTION_CONTROLLER_MERGE_REVIEW=YES`，随后必须停止。

### 11.5 CI enforcement 与 staged review

GitHub `Production Gate` 的 PR AI Workflow Gate 开启
`--enforce-agent-workflow-contract`，所以 required remote CI 始终要求有效的最终
STRICT review evidence，并验证 Task type / Workflow class / Documentation Impact / lifecycle；它不
加载或执行某一个 PR 的 mission scope，因而不会把 #1904 的 bootstrap 路径列表当成
所有 PR 的全局限制。需要 scope 的本地/受控 gate 必须显式提供当前合同；不能把
mission ID、PR title 或 PENDING 当作授权。review 完成后 PR body 的 strict evidence 必须改为 Codex、PASS/FINDINGS_RESOLVED
和当前 exact HEAD；`agent-merge-ready --pr` 会再次以 `allow_pending=false` 校验当前
PR body。source change 自动使旧 evidence stale，新 HEAD 必须重新 CI + review。远端
required checks 仍由 GitHub ruleset/API 产生，`pr-ready` 不替代 TEST、CI 或 REVIEW。
