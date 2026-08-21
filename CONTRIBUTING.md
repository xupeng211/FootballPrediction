# Contributing

仓库开发规则唯一以 [AGENTS.md](AGENTS.md) 为准，详细 workflow 见
[docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md)。本文件只保留 GitHub 协作约定。

## Branch and PR

- 从当前确认的 base SHA 创建 feature branch；不要直接在 `main` 开发或提交。
- 保留并检查自己的 dirty changes；不要用 reset、clean、覆盖式 checkout 或 force-push 处理工作区。
- 变更完成后运行与任务风险匹配的 canonical validation profile，提交清晰 commit，push feature branch 并创建 PR。
- PR 必须说明 Summary、Scope、Tests、Risk 和 Rollback；Scope 还要声明 `Workflow class = NORMAL` 或 `STRICT`，高风险文件按模板补充授权信息。
- source change 后，旧 review 和旧 CI 结果不能替代当前完整 PR HEAD 的验证。

## Review and merge

- NORMAL 任务不默认需要独立 AI reviewer。
- STRICT 任务需要一个绑定当前完整 HEAD 的 independent adversarial review；GitHub Codex Review 只是可选 advisory second opinion。
- STRICT PR 必须提供最小 `Strict Review Evidence`，由现有 required governance path 验证 reviewed full SHA 等于当前 PR HEAD；NORMAL 不需要该 evidence。
- 当前 ruleset 的 required checks 以 GitHub 实际配置为准；截至 2026-08-21 观察到 `Environment / Proxy / Static / Unit Gate` 和 `Docker Build Validation`。
- owner 负责最终 merge decision。目标 policy 是 Squash Merge；远端若仍允许其他 merge method，不由仓库文档假装已经收紧，需 owner 单独调整 GitHub 设置。
- merge 后必须确认 main Production Gate 验证实际 merge SHA，才算 DONE。

## Commands

公开验证入口目标为：

```bash
make verify-targeted
make verify-pr
make verify-strict
```

旧 `make`/`npm` 入口在收敛期间只作为兼容 alias 或 internal implementation；它们不能吞掉 required failure，也不能单独代表 GitHub hard gate。
