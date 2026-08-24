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

`settings*.json` 中的 permission allowlist 只是 Claude host 的工具权限，不是项目授权，也不能绕过 `AGENTS.md` 对 DB、写入、网络、MCP 或其他副作用的逐项授权。配置文件中存在 MCP entry 也不证明该 entry 已被当前宿主加载、项目当前支持或任务已获授权；本仓库没有对应的 MCP loader。跟踪的 MCP 配置不得包含 inline credential；环境本地 secret/setup 必须由宿主侧另行提供。

`mcp-config.json` 中的绝对路径属于 host-local setup，不能作为可移植的 repository path 或项目能力声明；当前机器是否能使用这些路径必须单独确认。该文件的历史配置说明不改变 `AGENTS.md`、README 和 current-state 文档的 authority。

## Claude-specific differences

Claude 只在权限、工具调用和 skill 可用性上有 agent-specific 差异。任务分类、测试、CI、STRICT review freshness、owner merge decision 和 DONE 定义全部以 `AGENTS.md` 为准。
