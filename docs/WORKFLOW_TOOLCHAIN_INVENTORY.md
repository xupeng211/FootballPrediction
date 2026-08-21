# Workflow Toolchain Inventory — Non-authoritative Index

> This page is not the current workflow authority；本页只用于迁移期间查找旧入口。规则见
> [AGENTS.md](../AGENTS.md)，详细说明见 [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md)。

## Current target

公开给 agent 的验证 profile 是：

```text
make verify-targeted
make verify-pr
make verify-strict
```

`gatekeeper.sh`、`ai_workflow_gate.py`、各种 preflight、loop 和 local wrapper 仍可能被兼容入口或 GitHub workflow 调用，但它们是 implementation/helper，不是额外 authority。请用 `rg`、Makefile、package.json 和 `.github/workflows` 追踪真实 caller；不要因为此索引列出名称就认为它们仍在运行。

## Migration rule

旧入口先标记为 canonical、alias、internal、legacy 或 dead；只有证明没有 current caller、GitHub caller、supported documentation entry 或外部配置依赖，并且存在替代物后，才可删除。历史 inventory 不得作为当前状态证明。
