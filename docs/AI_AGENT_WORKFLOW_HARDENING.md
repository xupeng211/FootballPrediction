# AI Agent Workflow Hardening — Historical Index

> 本文件保留历史阶段的索引，不是 current workflow authority。操作规则请读
> [AGENTS.md](../AGENTS.md)，详细说明请读 [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md)。

过去的 hardening 文档曾描述 `PR Lifecycle`、`Branch Safety`、`Scope Drift`、staging、Final Report、PR Gate run id、main Gate run id、reported 与 independently verified evidence，以及 `no run id / could not verify` 的失败表达。这些概念现在统一由 canonical documents 解释，不再由本页单独维护流程。

## What This Document Does NOT Do

本页不定义额外 gate、review、loop、manifest、状态机或自动 cleanup；不授权 training、data expansion、DB write、live fetch、raw write、migration、model activation 或生产变更。

## Historical compatibility terms

旧审计中出现的 `Forbidden CI Watch`、`while true`、`Monitor`、`ACCEPTABLE`、`UNACCEPTABLE`、`What counts as` 和 `What does NOT count as` 只是历史检索词。当前证据必须来自实际命令、exit code、完整 SHA、GitHub run 和 ruleset。

## Current replacement

NORMAL 使用 targeted validation；STRICT 使用 relevant/full validation 和一个 exact-head independent review。TEST、CI、REVIEW、OWNER 是仅有的 authority；merge 后 main Production Gate 验证 exact merge SHA 才算 DONE。
