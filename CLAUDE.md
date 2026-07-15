# Claude Code Project Instructions

- lifecycle: permanent / agent-entrypoint

## Read order

1. **AGENTS.md** — authoritative for repository-wide safety and workflow rules.
2. **README "Canonical Business Entrypoints"** — authoritative for business commands.
3. `docs/AGENT_WORKFLOW.md` and `docs/engineering/AI_AGENT_WORKFLOW.md` — detailed workflow docs.
4. `docs/AI_AGENT_WORKFLOW_HARDENING.md` — CI monitoring, branch safety, and completion evidence rules.
5. `docs/data/FOTMOB_CURRENT_STATE.md` — latest FotMob ingestion state.

## Container-first

All Node.js / Python commands run inside the dev container:
`docker compose -f docker-compose.dev.yml exec dev <command>`.
Never run business logic directly on the host.
Use `make dev-up` / `make dev-shell` for environment setup.

## Core rules

- Implementation PRs must include real runtime behavior change.
- Planning / governance PRs must not pretend to be implementation.
- Data / ingestion work is no-write by default.
- Do not perform live fetch, network request, DB write, raw write, re-acceptance,
  suspension reversal, source inventory production mutation, or candidate production
  mutation unless explicitly authorized.
- Do not save or print full HTML, pageProps, raw_data, or source body.
- Every PR must include Repository Hygiene / Debt Impact.
- Every new file must have a lifecycle.
- Prefer current-state updates over creating long historical reports.

## Branch Safety Rule

- **Never work directly on main.** Always create a feature branch from clean latest `origin/main`.
- Before every task: `git branch --show-current` and `git status --short`.
- If current branch is unexpected: explain, get confirmation before switching.
- If uncommitted changes exist: **stop**, list them, wait for user decision.
- **Never force push.** Do not rebase, amend, or force-push shared branches.

## Scope Drift Rule

- Current task is X → do NOT continue unfinished Y from a previous session.
- Do not cross scope boundaries without explicit user authorization.
- Do not expand into DB, training, scraping, or odds import unless explicitly authorized.
- **Prefer minimal diffs.** Do not expand scope without explicit user instruction.
- **Do not create V2 / FINAL / rewritten / replacement / backup file-name patterns.**

## Authorization discipline

- **Do not run DB write scripts, SQL, migrations, schema changes.** SELECT-only is
  permitted for auditing when explicitly authorized.
- **Do not run scraper / browser / Playwright** or live HTTP fetch unless explicitly
  authorized with clear scope and confirmation.
- **Do not train or expand data.** Model training, data expansion, and raw data
  acquisition remain blocked (require separate authorization).
- **Do not execute `DRY_RUN=false` or `FINAL_DB_WRITE_CONFIRMATION=yes`** targets
  unless explicitly authorized.

## SC-002 and growth freeze

- SC-002 is partial mitigation only.
- SC-002 enforcement is complete. Training / data expansion / real DB write remain blocked.
- M2 governance growth freeze is active (PR1 #1790). New Phase/ADG-numbered scripts,
  reports, manifests, and `src → scripts/ops` reverse dependencies are blocked.
- Allowlists are historical baselines, not safety approvals.

## CI Watch Command

- **禁止自定义 while true / sleep loop / Monitor 包装器监控 GitHub Actions CI。**
- **统一使用** `make watch-pr PR=<number>` 等待 PR checks 完成。
- 备选单次查询：`gh pr checks <number>`（不循环）。
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

- **Post-merge main Production Gate must be green** before the task is considered complete.
- **没有 post-merge main Gate run id，不得写 "main green yes"。**
- 如果 merge commit 查询不到 workflow run，必须写：
  `"main Gate could not be independently verified by merge commit; needs explicit run id"`。
- **不得把 Claude 自己的口头 success 当成独立核验。**
- Final report 中必须区分：
  - **reported success** — CI dashboard 显示绿色，但 agent 未独立确认。
  - **independently verified success** — agent 执行了 `gh run view <run-id>` 或 `gh run watch` 并得到 `"conclusion":"success"`。
- 如果查到的 run 来自附近 commit 而非 exact merge commit，必须在报告中注明替代关系。

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

## Canonical business entrypoints

- **README "Canonical Business Entrypoints"** is the single source of truth.
- Claude must not invent or promote legacy scripts as canonical entrypoints.
- Claude must not claim FotMob or backtest have established canonical entrypoints.
- Side-effectful canonical commands (training, odds harvest) still require
  explicit authorization — canonical does not mean auto-authorized.

## Stop conditions

Stop immediately and report when:
- Remote state changes unexpectedly (new commits, parallel PRs, branch divergence).
- A required authorization is missing.
- CI is red and the fix is outside the declared task scope.
- The original workspace has been modified unintentionally.
- A task would cross into blocked territory (DB write, training, scraping, odds import).

## Claude Skills

Project has 12+ dedicated Skills (see `.claude/README.md`). Use Skill tool for
specialized tasks (football-prediction, data-collection, code-quality, etc.).
