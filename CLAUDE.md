# Claude Code 项目入口

> Claude-specific 说明。仓库工作流唯一权威是 [AGENTS.md](AGENTS.md)，详细说明是
> [docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md)。本文件不复制 branch、test、review、CI 或 merge policy。

## Claude-specific safety

- 遵守 `AGENTS.md` 的 branch/worktree、最小修改、容器优先和副作用授权规则。
- 不直接修改 `main`，不覆盖用户 dirty change；开始写操作前先报告 branch、HEAD 和 dirty state。
- 不直接执行 live fetch、DB write、raw write、训练、预测、backtest、模型激活或 migration apply。
- Claude 的 skills、MCP、权限和工具差异不改变仓库的 TEST、CI、REVIEW、OWNER 四种 authority。

## Current entrypoints

- 业务入口：README 的 `Canonical Business Entrypoints`。
- 工作流：`AGENTS.md`；详细解释：`docs/AGENT_WORKFLOW.md`。
- 最终验证目标：`make verify-targeted`、`make verify-pr`、`make verify-strict`。
- 当前 GitHub hard gate 以 ruleset/API 为准；文档不能把本地 helper 或 advisory review 说成 required check。

## Claude handoff

报告必须区分 `CONFIRMED`、`INFERRED`、`UNKNOWN`，并给出实际命令、exit code、完整 SHA 和未验证事项。只有当前 PR HEAD 的 required CI、必要的 exact-head review、owner merge decision，以及 merge SHA 对应的 main Production Gate 都有证据，才可称 `DONE`。

旧的 `docs/AI_AGENT_WORKFLOW_HARDENING.md`、`docs/CODEX_WORKFLOW.md`、`docs/engineering/AI_AGENT_WORKFLOW.md` 和 `docs/WORKFLOW_TOOLCHAIN_INVENTORY.md` 仅作历史/迁移索引，不是 Claude 的额外必读 workflow authority。
