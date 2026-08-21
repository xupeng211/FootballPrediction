# Codex Workflow — Historical Index

> 本文件不再是 workflow authority。当前操作规则唯一来自 [AGENTS.md](../AGENTS.md)，详细说明来自
> [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md)。本页保留旧链接名称，避免外部书签失效。

## Core Rules

请遵守 `AGENTS.md` 的安全、branch/worktree、副作用和 DONE 规则。

## Task Types

任务只分为 `NORMAL` 和 `STRICT`，分类规则在 `AGENTS.md`。

## Mandatory PR Body Sections

默认 PR 模板只有 `Summary`、`Scope`、`Tests`、`Risk`、`Rollback`。高风险路径才补充授权字段。

## Documentation Creation Decision Tree

先更新现有 canonical 文档；不要用新 report、manifest 或 phase snapshot 代替 runtime 实现。只有明确授权且确有长期用途时才新增文档。

## Prohibited Habits

不要在 `main` 开发，不要覆盖 dirty change，不要吞掉 required failure，不要把文档声明、advisory review 或短 SHA 当作机器事实。

## Migration note

本页中的旧段落、旧命令和旧 PR 状态不再定义当前流程；需要核对历史时可查 Git history，但 current truth 来自 Git/GitHub/Actions 和上述 canonical documents。
