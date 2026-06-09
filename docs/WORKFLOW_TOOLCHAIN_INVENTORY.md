# Workflow Toolchain Inventory

`lifecycle: current-state`

最后更新：`2026-06-09`

## 1. 当前已有 workflow 工具链清单

- `make workflow-pr-check`
- `make pr-body-check`
- `make pr-merge-preflight`
- `make pr-ready-check`
- `make pr-post-merge-check`
- `make ci-local-pr`
- `scripts/ops/ai_workflow_gate.py`
- `scripts/devops/pr_merge_preflight.py`
- `scripts/devops/pr_body_check.py`
- `scripts/devops/pr_post_merge_check.py`

## 2. 工具说明

### Make targets

| 工具 | 解决什么问题 | 什么时候运行 | 是否只读 | 是否会改仓库 | 是否会清理分支 | 输入参数 | 输出 / 通过条件 | 失败时怎么处理 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `make workflow-pr-check` | 给 workflow-only PR 提供固定的本地 lint + format-check + pytest 校验入口 | workflow/governance/test-only PR 在 push 前 | 是 | 否，默认只做检查 | 否 | `FILES`, `TESTS` | `ruff check`、`ruff format --check`、`pytest -v` 全部通过才 PASS | 修正被检查的文件或测试；不要跳过任一步，不要只跑 pytest |
| `make pr-body-check` | 防止 PR body 滞后，强制把真实 PR body 与当前 head SHA 的 CI 证据绑定 | PR 创建后、更新 PR body 后、合并前 | 是 | 否 | 否 | `PR=<N>` | PR 存在且 open；body 可实时拉取；`ai_workflow_gate` 通过；body 包含当前 short SHA、changed files、最新 Production Gate run id；CI 对应当前 head 且 `completed/success` | 先修 PR body 或等当前 head CI 完成；如果 body 只更新了文字，需要 fresh CI，而不是迷信旧绿灯 |
| `make pr-merge-preflight` | 在 merge 前输出可审计的 PR + CI 证据，阻止错误 head / draft / 非 main / 失败 CI 被 merge | 合并前最后一步 | 是 | 否 | 否 | `PR=<N>` | PR open、非 draft、base=`main`、mergeable、head SHA 存在、Production Gate 对应当前 head 且 `completed/success` | 不修复脚本外的东西；先解决 PR 状态、head SHA、CI 或 mergeability，再重跑 |
| `make pr-ready-check` | 串联 `pr-body-check` + `pr-merge-preflight`，减少合并前手工漏跑风险 | 合并前，替代手工两步 | 是 | 否 | 否 | `PR=<N>` | 两者都 PASS 才 PASS；任一步失败则停止 | 按失败的子步骤修；不要跳过任一步 |
| `make pr-post-merge-check` | 在 merge 后验证 merge commit、main CI、工作区和 cleanup 条件 | PR merge 之后 | 默认是；`CONFIRM_CLEANUP=1` 时不是 | 默认不改；`CONFIRM_CLEANUP=1` 会删分支 | 默认否；显式确认后会删远程/本地分支 | `PR=<N> MERGE_COMMIT=<sha> BRANCH=<name> [CONFIRM_CLEANUP=1]` | 默认模式：所有 post-merge gate 通过则 PASS；带 `CONFIRM_CLEANUP=1` 时，在 PASS 后继续执行 cleanup | 如果 merge commit CI 未成功、main 未同步、工作区不干净或分支受保护，立即停止；不要先删分支 |
| `make ci-local-pr` | 提供本地 gatekeeper 入口，提醒“本地部分验证 != 远程 CI 权威” | PR push 前 | 否 | 可能。可能重建本地依赖树或缓存，例如 `npm ci`、本地工具缓存 | 否 | 无 | 目标本身总是把结果解释为“部分验证”；真正结论仍看远程 GitHub Actions | 报告具体本地环境失败原因；不要把本地 PASS/0 退出码当成远程 CI PASS |

### Underlying scripts

| 工具 | 解决什么问题 | 什么时候运行 | 是否只读 | 是否会改仓库 | 是否会清理分支 | 输入参数 | 输出 / 通过条件 | 失败时怎么处理 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `scripts/ops/ai_workflow_gate.py` | 做 P0 级 PR body + git diff 风险门禁，覆盖 required sections、stop phrase、mixed governance、doc sprawl、blind-spot dangerous keywords、safety declaration consistency | PR body 起草后、本地自检、CI 中的 AI workflow gate | 是 | 否 | 否 | `--pr-body-file` 或 `--pr-body-stdin`，可选 `--base-ref`、`--skip-body-checks` | PR body section 完整，包含 stop phrase，git diff 不触发 mixed-governance / doc-sprawl / blind-spot / safety inconsistency | 修 PR body 或改动范围，不要靠修改测试/CI/文档绕过 |
| `scripts/devops/pr_merge_preflight.py` | 只读拉取 PR 元数据和 head CI，输出 merge 前证据 | `make pr-merge-preflight` 背后或直接脚本调用 | 是 | 否 | 否 | `--pr <N>`，可选 `--json` | 输出 PR/CI 证据；所有 merge gate 满足则 exit 0 | 根据失败项修 PR 状态、CI、base 分支或 mergeable 条件；不要猜 |
| `scripts/devops/pr_body_check.py` | 只读拉取 live PR body，调用 `ai_workflow_gate.py`，并校验 body 与当前 head CI 证据一致 | `make pr-body-check` 背后或直接脚本调用 | 是 | 否 | 否 | `--pr <N>` | 输出 PR number、title、head SHA、changed files、Production Gate run id/status/conclusion、AI gate result、PASS/FAIL | 修 PR body 或等待正确的当前 head CI；不要把旧 run id 或旧 head 绿灯继续写在 body 里 |
| `scripts/devops/pr_post_merge_check.py` | 在 merge 后校验 merge commit 是否在 `origin/main`，merge commit 的 Production Gate 是否成功，本地 main 是否可 ff-sync，工作区是否干净，并在显式确认后清理分支 | `make pr-post-merge-check` 背后或直接脚本调用 | 默认是；`--confirm-cleanup` 时会执行删除 | 默认否；cleanup 模式会删远程/本地分支 | 仅 `--confirm-cleanup` 时是 | `--pr <N> --merge-commit <sha> --branch <name>`，可选 `--confirm-cleanup`、`--json` | 默认模式 PASS 只报告；cleanup 模式 PASS 后删除分支 | 先让 merge commit 的 main CI 成功，再同步本地 main，再重跑；不要在不确定状态下删分支 |

## 3. 最近 PR 教训归纳

- `#1475`：`pr-merge-preflight` 工具化，补上 merge 前 head SHA / Production Gate 证据检查。
- `#1476`：`workflow-pr-check` 与 `pr-post-merge-check` 工具化，补上 workflow-only PR 的固定本地验证入口，以及 merge 后的 safety / cleanup gate。
- `#1477`：`pr-body-check` 工具化，补上 live PR body、AI workflow gate 和当前 head CI 绑定检查。
- `#1478`：统一 `pr-post-merge-check` 使用 `python3`，暴露出工具入口的运行时环境依赖也必须统一。

当前已经暴露出来的问题：

- AI 报告不能直接信，必须让工具重新拉真实 PR / CI 状态。
- PR body 很容易滞后，尤其在 body-only 编辑、rerun failed jobs、fresh CI 之间。
- GitHub 页面上的绿灯必须绑定当前 head SHA，不能只看“有一个 success”。
- 本地验证不等于远程 CI；`ci-local-pr` 本质上只是 partial validation。
- Makefile 里 `python` / `python3` 不统一会直接让工具不可用。
- merge 后也必须做 post-merge check 和 cleanup，不能 merge 成功就算收尾。

## 4. 当前推荐标准流程

1. 创建 PR 前：
   workflow-only 改动先跑 `make workflow-pr-check ...`；随后跑 `make ci-local-pr`；PR body 草稿先用 `python3 scripts/ops/ai_workflow_gate.py --pr-body-file <tmp>` 过本地 gate。
2. 创建 PR 后：
   跑 `make pr-body-check PR=<N>`，确认 live PR body、当前 head SHA、changed files、Production Gate run id 和 AI gate 一致。
3. 合并前：
   跑 `make pr-ready-check PR=<N>`（串联 `pr-body-check` + `pr-merge-preflight`）；PASS 才能 merge。
4. 合并后：
   先等 merge commit 在 `main` 上的 Production Gate `completed / success`，再同步本地 `main`，然后跑 `make pr-post-merge-check PR=<N> MERGE_COMMIT=<sha> BRANCH=<branch>`。
5. cleanup 后：
   再用 `make pr-post-merge-check PR=<N> MERGE_COMMIT=<sha> BRANCH=<branch> CONFIRM_CLEANUP=1` 做统一 cleanup；清完后停止，不自动开始下一任务。

## 5. 剩余待工具化清单

| 项目 | 优先级 | 要解决的问题 |
| --- | --- | --- |
| `make pr-ready-check PR=<N>` | `P0` — **已实现** | 把 `pr-body-check + pr-merge-preflight` 串起来，减少合并前的手工两步和漏跑风险 |
| `make changed-files-policy-check PR=<N>` | `P1` | 对 governance-only / docs-only / runtime-code-change 做更显式的 changed-files policy 检查，避免“声明安全、实际越界” |
| `docs/REPOSITORY_STRUCTURE.md` | `P1` | 明确文件应该放哪里，减少 AI 乱建目录、乱放报告、乱放 helper 的概率 |
| `make repo-structure-check` | `P1` | 把目录放置规则工具化，防止新增文件落在错误位置 |
| `make pr-post-merge-ready PR=<N>` | `P1` | 把 merge commit 的 main CI 检查、post-merge check、cleanup readiness 串成一个统一入口 |
| `AGENTS.md / skills 拆分` | `P2` | 降低每次给 AI 的长提示词依赖，把稳定规则和专项流程拆到更小、更专注的入口 |

## 6. 优先级建议

- `P0`：`make pr-ready-check PR=<N>`。这是最直接减少人工漏步的缺口。
- `P1`：`make changed-files-policy-check PR=<N>`、`docs/REPOSITORY_STRUCTURE.md`、`make repo-structure-check`、`make pr-post-merge-ready PR=<N>`。这些都是近期应该补齐的流程边界和仓库边界。
- `P2`：`AGENTS.md / skills 拆分`。重要，但属于流程负载优化，不是当前最直接的 merge 风险点。

## 7. 推荐下一步

`make pr-ready-check PR=<N>` 已实现。下一步推荐 `P1`：`make changed-files-policy-check PR=<N>` 或 `docs/REPOSITORY_STRUCTURE.md`。

Do not start automatically.
Recommended next task only after user confirmation.
