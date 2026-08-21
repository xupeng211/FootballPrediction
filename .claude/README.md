# Claude tooling and skills index

本目录只承载 Claude 的 tooling、skills 和本地配置，不是项目工作流 authority。

## Project workflow

- 唯一 operational workflow authority：[`/AGENTS.md`](../AGENTS.md)
- 唯一详细 workflow 文档：[`/docs/AGENT_WORKFLOW.md`](../docs/AGENT_WORKFLOW.md)
- `.claude`、`CLAUDE.md`、`GEMINI.md` 和 skill 文档不得定义与上述文件平行的 branch、test、review、PR 或 merge 规则。

## Skill inventory

`.claude/skills/` 下的内容按需手动使用，具体能力是否可用取决于宿主工具配置；skill 文件本身不构成项目强制 gate。

- `codex-review`：STRICT 任务可用的 approved independent reviewer capability；review 必须绑定当前完整 PR HEAD。
- `codex-loop`：异常情况下的 bounded helper，不是默认流程，也不是独立 authority。
- 其他目录技能：tooling / domain helper；使用前仍须遵守 `AGENTS.md` 的安全边界和 canonical validation profiles。

当前仓库 `.claude/settings.json` 明确 `skills.enabled=false`，因此不能把自动加载或自动执行技能当作已实现的机器强制行为。`settings.local.json` 和 `mcp-config.json` 是环境相关配置，不得保存 workflow state、review state 或 SHA authority；其中绝对路径是否仍由宿主 runtime 使用，需要单独确认。

## Claude-specific differences

Claude 只在权限、工具调用和 skill 可用性上有 agent-specific 差异。任务分类、测试、CI、STRICT review freshness、owner merge decision 和 DONE 定义全部以 `AGENTS.md` 为准。
