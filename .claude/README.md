# Claude tooling and skills index

本目录只承载 Claude 的 tooling、skills 和本地配置，不是项目工作流 authority。

## Project workflow

- 唯一 operational workflow authority：[`/AGENTS.md`](../AGENTS.md)
- 唯一详细 workflow 文档：[`/docs/AGENT_WORKFLOW.md`](../docs/AGENT_WORKFLOW.md)
- `.claude`、`CLAUDE.md`、`GEMINI.md` 和 skill 文档不得定义与上述文件平行的 branch、test、review、PR 或 merge 规则。

## Skill inventory

Inventory task `STALE_AGENT_KNOWLEDGE_RETIREMENT` retired the 17 audited
legacy Claude skill manifests and READMEs that previously occupied the current
`.claude/skills/` surface. The audit found no unique current contract,
incident, or governance evidence in those generic examples; their historical
commits remain recoverable for background use. They are not a current
capability, workflow, or execution authority.

Any remaining files under `.claude/skills/` are optional tooling/domain
references and must be inspected manually. They are not automatically loaded,
do not form a project gate, and must still obey `AGENTS.md` and the canonical
validation profiles.

当前仓库 `.claude/settings.json` 明确 `skills.enabled=false`，因此不能把自动加载或自动执行技能当作已实现的机器强制行为。`settings.local.json` 和 `mcp-config.json` 是环境相关配置，不得保存 workflow state、review state 或 SHA authority；其中绝对路径是否仍由宿主 runtime 使用，需要单独确认。

## Claude-specific differences

Claude 只在权限、工具调用和 skill 可用性上有 agent-specific 差异。任务分类、测试、CI、STRICT review freshness、owner merge decision 和 DONE 定义全部以 `AGENTS.md` 为准。
