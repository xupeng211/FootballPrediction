# FootballPrediction — AI 开发工作流权威

> 本文件是本仓库唯一的 operational workflow authority。最后复核：2026-08-21。
> 业务入口以 [README.md](README.md) 的 `Canonical Business Entrypoints` 为准；详细工作流见
> [docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md)。其他工作流文档只能解释背景或指向这两处，不能另行定义规则。

## 1. 安全边界

- 所有回复、注释和日志优先使用中文。
- 不直接修改 `main`，不在 `main` 上开发或提交。先确认 branch、worktree 和 dirty state。
- 保护用户已有修改；不得使用 `reset --hard`、`clean`、覆盖式 checkout、force-push 或删除未知工作。
- 先读后改、最小修改、只做当前任务范围内的变更。
- 默认在 `dev` 容器中运行 Node/Python 业务命令；数据库、网络抓取、raw 写入、训练、预测、backtest、模型激活和 migration apply 均需单独授权。
- 不使用模拟数据替代真实链路；不保存或打印完整 HTML、`raw_data` 或 `pageProps`。
- 数据入口使用 README 和 `docs/data/FOTMOB_CURRENT_STATE.md` 指定的 `make data-*` 安全门禁；不要直接运行 legacy production、harvest、backfill 或 discovery 入口。
- 新增模块、脚本、writer、mapping、migration 或数据合同前，先阅读 `docs/CAPABILITY_INDEX.md`，搜索既有 symbol 和调用者，并说明不能复用的原因。

## 2. 开始任务

开始任何写操作前，记录：

```text
PROJECT_ROOT=
CURRENT_BRANCH=
CURRENT_HEAD=
CURRENT_DIRTY_STATE=
BASE_SHA=
```

确认当前不是 `main`。若在 `main`，先创建 feature branch；若已有未提交修改，原样保护，不能为了切 branch 而覆盖它。优先使用现有 worktree；需要新 worktree 时先确认目标路径不含用户工作。

## 3. 任务分类

### NORMAL

小 bug、局部业务逻辑、UI、文档、低风险 refactor 和不改变 DB/write/runtime 安全边界的普通功能。默认流程：

```text
feature branch/worktree → 实现 → make verify-targeted → commit/push → PR
→ required CI → owner merge decision → main Production Gate → DONE
```

NORMAL 默认不要求本地 Codex review、DeepSeek audit、codex-loop、manifest package 或 GitHub Codex review。

### STRICT

DB/schema/write boundary、data ingestion、identity/auth/security、生产 runtime 语义、训练/模型激活、关键架构变化和高影响破坏性行为。流程在 NORMAL 基础上增加：

```text
relevant/full validation → 一个 exact-head independent adversarial review → PR
```

一个 STRICT 任务默认只有一个 primary independent reviewer。GitHub Codex Review 可以作为 advisory second opinion，但不是 approval 或 required status。

## 4. Canonical validation profiles

最终公开给 agent 的验证接口只有三种：

```bash
make verify-targeted   # NORMAL 的受影响测试和必要静态检查
make verify-pr         # 与 GitHub PR Production Gate 共享实现
make verify-strict     # STRICT 的 relevant/full、安全和完整性验证
```

`make verify-targeted`、`make verify-pr`、`make verify-strict` 是唯一公开的 validation profiles。
仓库已有的 `make test-unit`、`make test`、`make ci-local-pr`、`make workflow-pr-check` 等入口只保留兼容用途；其中 CI/PR 兼容入口委托 canonical profile，不得自行定义另一套失败语义。

验证分类必须保持清楚：

- `TEST`：证明代码行为正确。
- `STATIC CHECK`：证明格式、lint、类型或静态约束。
- `CI`：在可重复环境中执行 canonical PR 验证。
- `REVIEW`：STRICT 时判断语义、边界和失败场景。
- `GOVERNANCE CHECK`：只检查 branch/PR/HEAD/权限等流程状态，不替代测试或 review。

## 5. PR、review 和 merge

PR 使用唯一模板 [.github/pull_request_template.md](.github/pull_request_template.md)，正文至少包含：

```text
Summary / Scope / Tests / Risk / Rollback
```

`Scope` 必须说明 task type、变更路径和 runtime behavior 是否变化；`Tests` 必须写实际命令及结果；`Risk` 必须说明副作用边界；高风险路径另加模板中要求的授权字段。

PR 生命周期：

1. 在 feature branch/worktree 实现并运行匹配的 canonical profile。
2. commit 前检查 `git diff`、`git status` 和完整 HEAD；不要提交用户已有 dirty change。
3. push feature branch，创建或更新 PR；source change 后重新验证当前 PR HEAD。
4. GitHub `Environment / Proxy / Static / Unit Gate` 和 `Docker Build Validation` 是当前 ruleset 的 required checks；它们必须验证当前 PR HEAD。
5. owner 判断是否接受风险并合并。仓库目标 merge policy 是 Squash Merge；远端 ruleset 当前仍允许 merge、squash、rebase，若需收紧必须由 owner 修改 GitHub 设置。
6. merge 不等于完成。必须找到实际 merge SHA，并确认 main push 的 Production Gate 对该完整 SHA 成功。

合并前只使用一个状态预检入口：

```bash
make pr-ready PR=<number>          # 只读 Git/GitHub 状态检查
make pr-ready PR=<number> JSON=1   # 机器可读证据
```

`pr-ready` 的 canonical implementation 是 `scripts/devops/pr_ready_check.py`。它只检查当前
feature worktree、PR 当前完整 HEAD、active ruleset 的 required checks 和该 HEAD 的 check runs；
它不跑测试、不执行 review、不生成 manifest/report、不修改 PR、不 merge、不清理 branch。
`pr-ready-check`、`pr-body-check` 和 `pr-merge-preflight` 仅是兼容别名，不能形成第二套 authority。
`pr-gate-local` 仍是本地静态 parity helper，不是 merge readiness 或 code review。

## 6. Exact-head 原则

- freshness、授权、review、CI 和 DONE 判断使用完整 40 字符 SHA；短 SHA 只能用于人类展示。
- repository / PR / review / CI / merge 的共享完整 SHA primitive 是 `scripts/devops/exact_head.py`；新增 freshness 判断时先复用它，不得另写前缀比较。
- review 只有在 `review_head == current_pr_head` 时有效；source change 自动使旧 review stale。
- required CI 只有在验证 SHA 等于当前 PR HEAD 时有效；历史 green run 不能授权新 HEAD。
- `PR merged + merge SHA identified + main Production Gate for exact merge SHA succeeds` 才能标记 `DONE`。

## 7. 明确禁止的副作用

未经逐项授权，不得执行 live fetch/detail fetch、浏览器采集、DB write、`raw_match_data` write、re-acceptance、rollback、schema migration apply、训练、预测、backtest 或模型激活。治理任务也不得用新增 report、manifest、phase snapshot、test-only 或 metadata-only 变更伪装 runtime 进展。

## 8. 真实入口和文档优先级

1. 本文件：唯一 operational workflow authority。
2. `docs/AGENT_WORKFLOW.md`：唯一 detailed workflow documentation，不得与本文件冲突。
3. `README.md`：业务 canonical entrypoints 和运行说明。
4. Git/GitHub/Actions：branch、HEAD、required checks 和 merge 的机器事实。
5. 其他文档、历史 report、handover、archive：仅作背景，不能当作 current truth。

Claude Code 只保留 Claude-specific 的权限/工具差异；其他 agent 应直接阅读本文件。

## 9. DONE 定义

未完成以下任一项，不得声称任务完成：

- 当前 branch/worktree 和 dirty state 已核对，用户修改未被覆盖。
- 目标验证已按 NORMAL/STRICT 分类实际执行，并报告命令与 exit code。
- PR 的 required checks 对当前完整 HEAD 成功。
- STRICT 任务的 review 对当前 HEAD 有效，或明确记录不需要 review 的理由。
- owner 已作出 merge decision。
- merge 后 main Production Gate 对实际 merge SHA 成功。
- 最终报告区分 `CONFIRMED`、`INFERRED` 和 `UNKNOWN`，没有把文档声明冒充机器强制。

若安全边界、授权或证据不足，停止在 `MERGE_READY`，明确 blocker，不用新的治理 artifact 掩盖它。
