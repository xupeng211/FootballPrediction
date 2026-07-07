# Claude Code Project Instructions

- lifecycle: permanent / agent-entrypoint

## Read order

Before working on this repository, treat the following files as the authoritative workflow sources:

1. AGENTS.md
2. docs/AGENT_WORKFLOW.md
3. docs/engineering/AI_AGENT_WORKFLOW.md
4. .github/pull_request_template.md
5. docs/data/FOTMOB_CURRENT_STATE.md

Do not rely on historical ADG reports as the primary current truth. Use docs/data/FOTMOB_CURRENT_STATE.md for the latest FotMob ingestion state.

## Container-first

All Node.js / Python commands run inside the dev container: `docker compose -f docker-compose.dev.yml exec dev <command>`. Never run business logic directly on the host. Use `make dev-up` / `make dev-shell` for environment setup. See AGENTS.md §4 for details.

## Core rules

- Implementation PRs must include real runtime behavior change.
- Planning / governance PRs must not pretend to be implementation.
- Data / ingestion work is no-write by default.
- Do not perform live fetch, network request, DB write, raw write, re-acceptance, suspension reversal, source inventory production mutation, or candidate production mutation unless explicitly authorized.
- Do not save or print full HTML, pageProps, raw_data, or source body.
- Every PR must include Repository Hygiene / Debt Impact.
- Every new file must have a lifecycle.
- One-shot helpers are cleanup candidates unless future reuse is documented.
- Prefer current-state updates over creating long historical reports.
- Keep reports and manifests minimal.

## FotMob current state

Read docs/data/FOTMOB_CURRENT_STATE.md before any FotMob ingestion task.

Current high-level status:

- raw_write_ready_count is 0.
- Existing source-controlled artifacts cannot generate corrected Ligue 1 source inventory records.
- The next data step is bounded corrected-source discovery, only after workflow hygiene is merged and explicitly authorized.

## Local PR Gate Preflight

- **Push 前必须运行 local PR Gate preflight.** Use `make pr-gate-local PR_BODY=<file>` to simulate Production Gate checks locally.
- **开 PR 前必须准备 PR body 并用 preflight 检查.** The preflight validates all required sections, forbidden claims, changed-files hardening, and enforcement phases.
- **远程 CI 失败前应先本地复现.** Do not use GitHub Actions as trial-and-error. Run the preflight first.
- **如果 local preflight 和 remote CI 不一致，要修 parity，不要绕过.** Report discrepancies; do not work around them.
- **Fast mode** (default): `make pr-gate-local PR_BODY=/tmp/pr_body.md` — static analysis, PR body validation, enforcement checks.
- **Full mode**: `make pr-gate-local PR_BODY=/tmp/pr_body.md FULL=1` — adds ruff, mypy, pytest, npm test:coverage.
- **JSON output**: `make pr-gate-local PR_BODY=/tmp/pr_body.md JSON=1` — machine-readable results.
- See `scripts/ops/local_pr_gate_preflight.py` for the full implementation.

## CI Watch Command

- **禁止自定义 while true / sleep loop / Monitor 包装器监控 GitHub Actions CI。**
- **统一使用** `make watch-pr PR=<number>` 等待 PR checks 完成。
- 备选单次查询：`gh pr checks <number>`（不循环）。
- 如果 `gh pr checks --watch` 在当前 gh 版本不可用，`make watch-pr` 会给出清晰提示并退出。
- **不要因为 CI 监控命令失败而修改业务代码。**
- **不要在 PR body / docs / scripts 中嵌入自定义 while true + gh pr checks + sleep loop 来监控 CI。**
- 详细 CI 监控规则和完整治理文档见 `docs/AI_AGENT_WORKFLOW_HARDENING.md`。

## Final Report Rule

每个任务的 Final Report 必须包含以下全部字段，缺字段 = 任务未完成：

- **PR number / URL**
- **head SHA**（完整 40 位优先）
- **merge commit SHA**（完整 40 位优先）
- **PR Gate run id**
- **PR Gate result**（success / failure / cancelled）
- **post-merge main Gate run id**（或明确说明"could not be independently verified"）
- **post-merge main Gate result**（success / failure / cancelled / not verified）
- **remote branch deleted**（yes / no）
- **main green**（yes / no / not verified）
- **independently verified**（yes = 有 run id + `gh run view` 确认 / no = 仅 reported）
- **是否有未核验项**
- **SC-002 status**
- **training / data expansion / real DB write remain blocked**
- **next recommended task**
- **Do not start automatically**

## Main Gate Evidence Rule

- **没有 post-merge main Gate run id，不得写 "main green yes"。**
- 如果 merge commit 查询不到 workflow run，必须写：
  `"main Gate could not be independently verified by merge commit; needs explicit run id"`。
- **不得把 Claude 自己的口头 success 当成独立核验。**
- Final report 中必须区分：
  - **reported success** — CI dashboard 显示绿色，但 agent 未独立确认。
  - **independently verified success** — agent 执行了 `gh run view <run-id>` 或 `gh run watch` 并得到 `"conclusion":"success"`。
- 如果查到的 run 来自附近 commit 而非 exact merge commit，必须在报告中注明替代关系。

## Branch Safety Rule

- **每个任务开始前必须执行：**
  ```
  git branch --show-current
  git status --short
  ```
- 如果当前分支不是预期分支：先说明原因，获得确认后再切换。
- 如果存在未提交修改：**立即停止**，列出修改文件，等待用户确认 stash/discard/commit。
- 禁止在 main 上直接作业。唯一的 main 操作：checkout / pull / 创建分支。
- 如果上一个任务留有分支且未合并：
  - **干净分支（无本地 commit）：** 切回 main，删除本地分支。
  - **有本地 commit 或未提交修改：** 停止并报告，请用户确认如何处理。
- 禁止在不相关分支上混用任务 scope。

## Scope Drift Rule

- 当前任务是 X 时，**不得继续上一个会话未完成的 Y 任务。**
- 如果当前任务是 workflow hardening，不得继续 staging deployment。
- 如果当前任务是 docs/tests，不得修改 runtime business logic。
- 如果当前任务无 DB scope，不得连接 DB。
- **任何 scope drift 必须停止并报告。**
- 检测到跨越 scope 边界时：立即停止越界动作，报告边界冲突，返回授权 scope。

## Completion Definition Rule

"任务完成"必须同时满足以下 **全部** 条件：

- PR merged
- PR Gate success（有 run id）
- post-merge main Gate success（有 run id）
- post-merge main Gate run id 已记录在 final report 中
- remote branch deleted
- working tree clean
- final report complete（全部必填字段）

如果缺一项，只能说 "PR merged but completion not fully verified"。

不构成完成的常见错误：
- "PR merged" ≠ 完成（还需要 main Gate 验证）
- "CI passed on PR" ≠ main Gate 通过
- "main 之前是绿的" ≠ post-merge main 是绿的
- "web dashboard 看起来绿的" = reported success，不是 independent verification

## MCP permissions

| Server | Permission | Allowed |
|--------|-----------|---------|
| postgres | READ-ONLY | SELECT / DESCRIBE / EXPLAIN |
| filesystem | PROJECT ROOT | read / diff / controlled write |
| git | READ-ONLY | commit history / diff / blame |
| pytest | RESTRICTED | run pytest / list tests |

MCP does not own production control. No irreversible or high-risk automation via MCP.

## Claude Skills

Project has 12+ dedicated Skills (see `.claude/README.md`). Use Skill tool for specialized tasks (football-prediction, data-collection, code-quality, etc.).

## Agent Workflow Hardening

These rules are non-negotiable. They exist so AI agents working in this repo do not need repeated long-form prompts to enforce basic discipline. Detailed reference: `AGENTS.md`.

### 1. Branch discipline

- **Never work directly on main.** Always create a feature branch from clean latest `origin/main`.
- Always start from clean latest `origin/main`. Verify `HEAD == origin/main` before branching.
- **If main is red** (Production Gate failure), stop all feature work and fix main first. Do not start new branches from a red main.
- Delete remote branch after merge.

### 2. Scope discipline

- **Prefer minimal diffs.** Do not expand scope without explicit user instruction.
- Do not rewrite existing modules unless explicitly requested.
- **Do not create V2 / FINAL / rewritten / replacement / backup duplicates** to replace old code. This applies to file naming patterns: `*_v2.py`, `*_v2.js`, `*_new.py`, `*_new.js`, `*_final.py`, `*_final.js`, `*_rewritten.py`, `*_rewritten.js`, `*_replacement.py`, `*_replacement.js`, `*_backup.py`, `*_backup.js`.
- Do not delete or move historical code without an explicit cleanup task with declared scope.
- Do not perform mass refactoring or large-scale code movement without explicit authorization.

### 3. Safety discipline

- **Do not run DB write scripts.** Do not execute INSERT/UPDATE/DELETE/TRUNCATE/CREATE/DROP/ALTER.
- **Do not run SQL / migrations.** No `ALTER TABLE`, no `flyway`, no `alembic upgrade`, no schema changes.
- **Do not connect to DB** for write operations. SELECT-only MCP access is permitted for auditing.
- **Do not run scraper / browser / Playwright.** No live HTTP fetch, no headless browser, no network data collection.
- **Do not train or expand data.** No model training, no data expansion, no raw data acquisition.
- Do not execute `DRY_RUN=false` or `FINAL_DB_WRITE_CONFIRMATION=yes` target scripts unless explicitly authorized by the user with clear scope and confirmation.

### 4. SC-002 discipline

- **SC-002 is enforcement complete** (see `docs/SC002_FINAL_CLOSURE_CHECK.md`). Training / data expansion / real DB write remain blocked (require separate authorization).
- **Do not claim SC-002 is partial mitigation only** without acknowledging enforcement infrastructure is complete.
- **Do not claim training / data expansion / real DB write are unblocked.** They remain blocked even with SC-002 enforcement complete.
- **Allowlist is historical baseline, not safety approval.** Being in an allowlist does not authorize execution.
- **Guarded means gated, not authorized to execute.** A guard script blocks by default; it does not grant permission.
- All Python write paths (20/20) are classified and resolved per `docs/SC002_CLOSURE_PLAN.md`.

### 5. PR discipline

- Every PR must include these sections in the body:
  - `## Summary`
  - `## Scope`
  - `## Files Changed`
  - `## Safety Impact`
  - `## Validation`
  - `## CI Gate Scope`
  - `## No deletion / no move / no rename confirmation`
  - `## SC-002 status`
  - `## Remaining risks`
  - `## Next Recommended Task`
- Every PR must state whether DB / migration / scraper / browser / training was executed.
- `## Next Recommended Task` must contain: "Do not start automatically." and "Recommended next task only after user confirmation:".
- **Post-merge main Production Gate must be green** before the task is considered complete.
- If post-merge main Gate fails, open a minimal hotfix immediately. Do not start new feature work until main is green.

### 6. Task type discipline

| Task type | Allowed | Forbidden |
|---|---|---|
| **design phase** | planning, static analysis, docs, SELECT-only audit | runtime code change, DB write, training, live fetch |
| **scanner phase** | static scanning, allowlist management, CI enforcement | runtime guard implementation, DB write, live fetch |
| **guard phase** | guard integration, test updates, allowlist updates | new feature code, schema migration, training, data expansion |
| **hotfix phase** | minimal fix for gate/test failure | scope expansion, new features, refactoring |
| **cleanup phase** | explicit delete/move/rename within declared scope only | mass delete without explicit authorization, expanding beyond declared targets |
| **documentation-only phase** | docs, templates, manifests, governance files | runtime code, DB, scraper, browser, training, data |

### 7. Post-merge discipline

- Verify post-merge main Production Gate is green.
- If main Gate is red, open minimal hotfix immediately.
- Do not start new feature work until main is green again.
- Delete remote branch after merge is confirmed.

## Validation expectations

Before proposing completion:

- run relevant targeted tests;
- run lint / formatting checks when reasonable;
- run hidden/bidi and payload marker checks if touched files require them;
- report failures honestly;
- do not fake passing tests.
