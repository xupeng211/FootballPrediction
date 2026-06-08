# Agent Workflow Hardening

本文件约束 Codex / AI agent 在本仓库中的工程作业方式。目标是防止 implementation phase 退化为文档堆叠，
防止 report / manifest 失控膨胀，并让每个 PR 都能明确回答：
解决了什么系统问题、代码行为是否变化、还剩什么 blocker。

## 1. 核心原则

- 代码解决问题，测试证明问题，文档解释问题。
- implementation phase 必须推动 runtime 行为变化。
- docs、reports、manifests、proposal metadata 不能替代 implementation。
- 每个 PR 必须声明 PR type、business progress、安全边界和剩余 blocker。
- 变更范围必须可 review；禁止把大型 phase snapshot 当作默认推进方式。

## 2. PR 类型

每个 PR 必须选择且只选择一个主类型：

- `runtime-code-change`: 修改 runtime code path，并改变可执行系统行为。
- `governance-only`: 只调整规则、流程、runbook、模板或作业约束。
- `docs-only`: 只更新说明性文档，不改变流程规则和系统行为。
- `test-only`: 只新增或修正测试，不改变 runtime 代码。
- `ci-fix`: 只修复 CI、lint、format、dependency gate 或构建配置。
- `data-artifact`: 只更新已授权的数据 artifact、manifest delta 或 source-controlled metadata。

辅助类型可以在 PR body 说明，但不能掩盖主类型。例如 implementation phase 如果没有 runtime code behavior change，不能标成 `runtime-code-change`。

## 3. Implementation PR 验收标准

implementation PR 必须同时满足：

- 修改 runtime code path，例如 `src/`、`scripts/ops/`、配置加载、门禁入口或真实执行路径。
- PR body 明确列出改动的 runtime code paths。
- 行为变化可以被 reviewer 从 diff 中验证。
- 测试优先覆盖行为结果、阻断条件、边界输入和失败路径。
- docs / reports / manifests 只作为结果说明或必要 metadata，不作为主要交付物。

以下情况默认 No-Go：

- 只修改 `docs/_reports`、`docs/_manifests`、tests 或 proposal metadata。
- 只新增 phase report，没有改变实际执行路径。
- 只把字段名加入文档或测试 allowlist，没有修复导致 blocker 的代码。
- 无法安全实现 runtime change，却用 report 宣称 implementation 完成。

如果确实不能安全改 runtime code，必须停止并输出 No-Go 报告，说明 blocker、风险、需要的授权或设计决策。

## 4. Governance-only PR 限制

governance-only PR 允许建立规则、模板、runbook 或安全边界，但必须满足：

- PR body 明确写 `no runtime code changed`。
- 不声称解除业务 blocker。
- 不把 recommended next step 推进成 implementation done。
- 不创建大型 phase snapshot。
- 不把 governance artifact 写成事实执行结果。

连续 governance-only PR 超过 1 个时，必须人工确认是否继续治理路线。没有人工确认时，应停止并做 architecture review 或转入真正的 runtime implementation。

## 5. Docs / Report / Manifest 体积规则

新增或修改 artifact 必须最小化：

- report 只记录本阶段 delta、关键结论、验证命令和剩余 blocker。
- manifest 优先记录 current effective state，不复制完整历史状态。
- phase artifact 只记录该 phase 的输入、输出和 delta。
- 不得为每个微小状态变化复制整份大型 manifest。
- 大型 raw body、完整 pageProps、完整 source body 不得提交到 git。
- 大型诊断输出应优先作为 CI artifact、本地临时文件或 archive 方案，并单独说明保留策略。

PR 模板必须披露：

- 新增/修改 report 行数。
- 新增/修改 manifest 行数。
- 是否复制完整历史状态。
- 是否包含 large artifact。
- 如果包含 large artifact，必须说明为什么不能最小化。

## 6. Current State Manifest 原则

source-controlled manifest 应表达当前有效状态，而不是无限增长的阶段日志。

推荐结构：

- 顶层保存当前 batch、source、route、data_version、hash_strategy 和 next required action。
- per-target 保存当前有效 identity、baseline、blocker 和安全状态。
- 历史 phase 只保存必要引用、hash 或短摘要。
- 已废弃字段保留时必须标记 deprecated，并说明 reader 是否仍使用。

禁止结构：

- 每个 phase 都把全部 targets、历史状态和所有字段完整复制一遍。
- 为了通过测试而保留无实际 reader 的冗余字段。
- 在 manifest 中保存 full payload、full body、full pageProps 或敏感来源内容。

## 7. Large Artifact 归档原则

大型 artifact 不应默认进入 `main`。如必须保留：

- 先判断是否可以只保留 hash、row count、schema summary、sample path 或 CI artifact link。
- 如果必须 source-control，必须使用 archive 路径或明确的 retention policy。
- archive 变更不得和 runtime implementation 混在同一个 PR，除非它是该实现的必要输入。
- 不做大规模历史清理，除非用户明确要求并单独开 PR。

## 8. Testing 原则

测试应优先证明系统行为：

- 对 runtime-code-change，至少覆盖成功路径、阻断路径和关键安全边界。
- 对 data gate，覆盖 no-write、no-network、no-full-payload-print/save、hash gate、identity gate。
- 对 DB 相关变更，写入前必须有 SELECT-only preflight；写入必须单独授权。
- 对 docs-only / governance-only，可以做 markdown、link、template 或 policy lint，但不得声称业务逻辑被验证。

文档字段测试从严：

- 只允许验证对系统 reader、gate 或 reviewer 有实际意义的字段。
- 不得用 allowlist 扩张掩盖真实 blocker。
- 不得把 recommended next step 字段变化当作业务推进证明。

## 9. Ingestion Convergence Gate

数据入库链路的 planning、review、execution 和 governance PR 必须证明业务收敛，而不是只证明流程合规。详细规则见
`docs/INGESTION_CONVERGENCE_GATE.md`。默认要求：

- 每个 ingestion PR 必须声明要解除的 blocker、目标 target 集合和 `target_state_delta`。
- `target_state_delta` 必须说明 target 是否进入 `clean_candidate`、`rejected_mapping`、
  `superseded_mapping`、`eligible_for_re_acceptance_review`、`needs_new_evidence`、
  `remain_suspended`、`blocked_pending_review` 或 `abandon_current_batch_candidate`。
- 如果所有 target 都是 `no_progress`，PR 必须给出 no-progress justification，并声明是否触发 architecture decision gate。
- 连续 2 个 ingestion governance / review / planning / execution PR 没有解除 blocker
  或没有 target 状态实质变化时，必须停止自动开下一轮 planning / review。
- expanded review planning / execution 必须 bounded，至少声明 target 上限、证据范围、完成条件和失败后的 stop condition。
- bounded review 后仍没有 clean / reject / supersede / re-acceptance candidate 时，
  下一步必须是 architecture decision gate，而不是继续 phase 化。
- raw write 仍需 fresh authorization；review 结果不得自动放行 DB write、
  `raw_match_data` write、re-acceptance、suspension reversal 或 rollback。

Architecture decision gate 必须在以下方向中明确选择或请求人工决策：

- abandon current batch
- rebuild canonical identity pipeline
- redo source inventory strategy
- switch data source / compare alternative source
- redesign FotMob identity mapping strategy

## 10. Stopping Rules

出现以下任一情况必须停止，输出 No-Go 或 architecture review：

- implementation phase 没有 runtime behavior change。
- 连续 planning / governance 阶段没有移除 blocker。
- 连续 2 个 ingestion governance / review / planning / execution PR 没有解除 blocker 或 target 状态实质变化。
- bounded ingestion review 后仍没有 clean / reject / supersede / re-acceptance candidate，却只建议继续 planning。
- report / manifest 行数增长明显超过代码改动，且无法证明必要性。
- 测试主要验证文档字段，而不是 runtime behavior。
- PR body 无法说明 business progress 或 blocker removed。
- 下一步需要 live fetch、detail fetch、network request、DB write、raw write、re-acceptance、rollback 或 schema migration，但缺少明确授权。

## 11. Safety Disclosure

所有相关 PR 必须明确声明：

- no live fetch / detail fetch / network request 状态。
- no DB write / no raw_match_data insert / no matches write 状态。
- no raw write execution 状态。
- no re-acceptance / suspension reversal / rollback 状态。
- no parser / features / training / prediction 状态。
- 是否保存或打印 full body、full JSON、full raw_data、full pageProps。

如果某项被执行，必须列出授权来源、命令、范围、写入表、row count 和回滚/验证结果。

## 12. Review Expectations

reviewer 应能在 PR 中快速看到：

- PR type。
- runtime behavior 是否变化。
- 改了哪些 runtime code paths。
- business progress 是什么。
- blocker removed 是什么。
- blocker remaining 是什么。
- artifact 是否最小化。
- 测试是否证明行为。
- 安全边界是否保持。

如果这些信息缺失，PR 默认不应合并。

## 13. Workflow Sequence

默认顺序：

1. 读现有代码、规则、manifest 和相关测试。
2. 确认 PR type 与授权边界。
3. 对 implementation，先改 runtime 行为，再补行为测试。
4. 只写必要 docs / manifest delta。
5. 运行范围匹配的验证。
6. 填写 PR 模板，明确 business progress 和剩余 blocker。
7. CI green 后再合并。

这套顺序不能绕过既有 L1/L2/L3、DB、raw write、network、schema migration 授权规则。

## 14. Repository Hygiene Gate

每个 PR 在完成前必须做 hygiene check：

**File lifecycle**：每个新增文件必须在 PR body 声明 lifecycle（见 AGENTS.md 2.5 节）。PR 不得留下无 lifecycle 的新文件。

**Phase artifact limits**：
- Report 默认 <= 120 行；如需更长，必须在 PR body 说明原因
- Manifest 只保留机器需要的最小字段；不得复制完整历史
- Implementation PR 不得顺手新增无 lifecycle artifact
- Evidence/acquisition/regression PR 只能保留安全摘要，不保存 full payload

**One-shot helpers**：
- 每个新增 helper/script 必须说明是否长期保留
- 若 helper 只服务一次，默认成为 cleanup candidate
- 若 helper 被 Makefile/npm script/CI 引用，标注 permanent

**Tests**：
- 优先新增 runtime behavior tests
- 只验证 report wording / manifest metadata 的测试不得替代 behavior coverage
- Planning-only PR 不要求强 behavior tests

**Current truth first**：
- 维护 current-state 入口（如 docs/ 中的状态文件）
- 历史 ADG report 不能作为 current truth 的替代
- 后续状态变更应优先更新 current-state，不是继续堆 phase report

**Cleanup cadence**：
- 每 3-5 个 data/ingestion PR 后必须考虑是否需要一个 hygiene PR
- 若连续多个 PR 只新加 phase artifacts 不作清理，应在最终回复里建议 cleanup / archive

**Debt Impact**：
- 每个 PR 最终回复必须包含 Debt Impact（new files、permanent、phase-only、temporary、superseded、deleted、cleanup needed、noise increased、next trigger）
- 详见 `.github/pull_request_template.md` Repository Hygiene / Debt Impact 段落

**Hygiene PR scope**：
- 只建规则，不做大规模批量清理
- 文件满足当前生命周期声明的继续保留
- 只有明确标注 delete-after-use / archive-candidate 的文件才在后续 hygiene PR 中删除或归档

**Cross-agent rule**：Codex and Claude Code must follow the same workflow defined here. `CLAUDE.md` is an entrypoint that points to the same authoritative sources — it is not a separate rule set.

## 15. Local CI before push

Before pushing a PR branch, run:

```bash
make ci-local-pr
```

This invokes `scripts/devops/gatekeeper.sh` in local CI direct mode. It runs
static checks (no-verify guard, proxy config, leak check, contract check,
ruff, mypy, repo hygiene, etc.) directly in the current environment.

If the command reports partial validation, remote GitHub CI remains the final
authority. Do not claim full local CI passed unless gatekeeper completed
without any skipped checks.

## 16. PR Body Gate Local Check

PR body must pass `scripts/ops/ai_workflow_gate.py` before push. Missing required
sections or stop phrases will cause remote CI failure.

### Before creating a PR

Write the draft PR body to a temp file and validate:

```bash
cat > /tmp/pr_body.md <<'EOF'
## Summary
...
## Next Recommended Task
Do not start automatically.
Recommended next task only after user confirmation.
EOF

python3 scripts/ops/ai_workflow_gate.py --pr-body-file /tmp/pr_body.md
```

Gate must report `PASS` before `git push`.

### After creating a PR

Fetch the real PR body and re-validate:

```bash
gh pr view <PR_NUMBER> --json body --jq .body > /tmp/pr_body.md
python3 scripts/ops/ai_workflow_gate.py --pr-body-file /tmp/pr_body.md
```

### Required PR body sections (9)

```text
## Summary
## Scope
## Documentation Impact
## Safety Impact
## Validation
## CI Gate Scope
## No deletion / no move / no rename confirmation
## Rollback Plan
## Next Recommended Task
```

### Mandatory stop phrases in `## Next Recommended Task`

```text
Do not start automatically.
Recommended next task only after user confirmation.
```

### If the local gate fails

- Update only the PR body (via `gh pr edit` or `gh api PATCH`).
- Do **not** change code, tests, scripts, CI, or docs to satisfy the gate.
- Do **not** merge with a failing body check.
- Do **not** start another task until the gate passes.

## 17. CI Failure Handling and CI Retrigger Rules

### PR body edits do not trigger new CI

When you edit a PR body via `gh pr edit` or `gh api PATCH`, GitHub does **not**
fire a new `pull_request` event. The existing CI run still holds the old body.

### Do not rerun old workflow runs for body validation

`gh run rerun --failed` replays the **original** event payload. A rerun will
**not** see the updated PR body. The gate will fail again.

### Trigger a fresh CI run after a body-only fix

If you need to validate a PR body update and no code changes are required, push
an empty commit to create a new `pull_request` `synchronize` event:

```bash
git commit --allow-empty -m "ci: retrigger PR gate after body update"
git push
```

Before using an empty commit, confirm:

- Working tree is clean (`git status --short` produces no output).
- PR body passes local gate check (`python3 scripts/ops/ai_workflow_gate.py --pr-body-file /tmp/pr_body.md`).
- User has explicitly authorized the empty-commit push.
- No files are modified — `git diff --stat` shows zero changes.

## 18. P0 Engineering Design Constraints

These constraints apply to all implementation tasks.

### Separation of concerns

- **Fetch ≠ Parse ≠ Validate ≠ Write**. These four responsibilities must live
  in separate modules.
- One module = one responsibility. Do not create catch-all `Manager`,
  `Processor`, `Handler`, or `Utils` classes that absorb unrelated logic.
- Fetchers may retrieve data but must not write to DB.
- Parsers must be pure functions: no network, no DB, no file writes.
- Validators must only validate — they must not fetch or write.
- Writers may write to DB or files but must not scrape or parse raw payloads.
- Pipeline / Service modules orchestrate steps; they do not inline business
  details.

### Scope discipline

- One PR = one concern. Do not mix runtime, DB, docs, CI, and schema changes
  in a single PR unless the user explicitly authorizes it.
- If a single file or function is already too large, do not add more
  responsibilities. Stop and report that the module needs decomposition first.

### File placement

- New files go into the directory that matches their responsibility
  (`src/parsers/`, `src/infrastructure/network/`, `tests/unit/`, etc.).
- If file placement is unclear, **stop and ask the user** before creating it.
- Do not create new top-level directories without explicit authorization.
- Temporary reports, scripts, outputs, screenshots, raw payloads, dumps, and
  coverage artifacts must never be committed.

## 19. Code / Test / Docs Sync Rules

When making changes, check the following synchronization requirements:

| Change type | Check needed |
|---|---|
| Runtime behavior change | Test coverage (success + failure paths) |
| User-facing behavior change | Documentation update |
| Data structure / schema change | Schema docs and migration plan |
| Safety boundary change | PR body Safety Impact section |
| Test-only enhancement | Document in PR body; docs update optional |
| Governance / workflow rule change | Update `docs/AGENT_WORKFLOW.md` |

Do **not** use temporary reports under `docs/_reports/` or `docs/_manifests/`
as substitutes for permanent documentation. These directories accumulate
historical evidence; new files require explicit user authorization.

## 20. AI Agent Default Behaviors

These defaults apply unless a specific task overrides them with explicit
authorization.

### Read-only by default

- Audit, inspect, and review before modifying.
- Do not create branches, PRs, or Issues without explicit user instruction.
- Do not merge, auto-merge, or delete branches without explicit authorization.

### Stop-and-ask

Stop and ask the user before:

- Destructive or irreversible operations.
- Creating files in directories whose responsibility is unclear.
- Creating new top-level directories.
- Running `git add -A` or committing files beyond the authorized scope.
- Installing new dependencies.
- Starting any next task that was not explicitly authorized.

### Auto-start prohibition

Every PR body, Issue comment, and terminal report must include:

```text
Do not start automatically.
Recommended next task only after user confirmation.
```

## 21. PR Merge Preflight Evidence Check

Before merging a PR, run the read-only evidence check to produce an auditable
PASS/FAIL verdict. The check does **not** merge, delete branches, or modify
anything — it only reads via ``gh`` CLI.

```bash
make pr-merge-preflight PR=<PR_NUMBER>
```

Or run the script directly:

```bash
python scripts/devops/pr_merge_preflight.py --pr <PR_NUMBER>
python scripts/devops/pr_merge_preflight.py --pr <PR_NUMBER> --json  # machine-readable
```

### Evidence emitted

- PR number, title, state, draft status
- base branch, head branch, head SHA
- mergeable status
- changed files, additions/deletions
- CI workflow name (Production Gate)
- CI run id, status, conclusion
- Final PASS / FAIL verdict

### PASS conditions (all must be true)

- PR is open
- PR is **not** a draft
- base ref is ``main``
- mergeable is ``MERGEABLE``
- a Production Gate CI run exists for the head SHA
- Production Gate status is ``completed``
- Production Gate conclusion is ``success``

### FAIL conditions

- PR closed / merged
- PR is a draft
- base branch is not ``main``
- mergeable unknown / conflicting
- head SHA empty or too short
- Production Gate CI run not found for head SHA
- CI status is not ``completed``
- CI conclusion is not ``success`` (includes ``failure``, ``cancelled``, ``skipped``)

This is enforced by CI through `scripts/ops/ai_workflow_gate.py`.

## 22. Workflow PR Local Validation

Every workflow-only PR (governance-only, test-only, ci-fix) must pass local
validation before pushing. The ``make workflow-pr-check`` target is the fixed
entry point.

### Usage

```bash
make workflow-pr-check \
  FILES="scripts/devops/foo.py tests/unit/test_foo.py" \
  TESTS="tests/unit/test_foo.py"
```

### What it runs

```
ruff check $FILES
ruff format --check $FILES
pytest $TESTS -v
```

### Rules

- ``FILES`` must not be empty.
- ``TESTS`` must not be empty.
- If either parameter is missing, the target fails immediately with a clear
  usage message.
- The target does **not** guess files, does **not** default to whole-repo
  tests, and does **not** modify files (it is a check command, not a fix
  command).
- All three checks must pass for the target to report PASS.

### Workflow PR requirement

A workflow PR must run **all three** checks — ruff check, ruff format --check,
and pytest. Running only pytest is **not** sufficient.

### Typical call for this PR

```bash
make workflow-pr-check \
  FILES="scripts/devops/pr_post_merge_check.py tests/unit/test_pr_post_merge_check.py" \
  TESTS="tests/unit/test_pr_post_merge_check.py tests/unit/test_pr_merge_preflight.py"
```

## 23. Post-Merge Check / Cleanup Gate

After a PR is merged, a read-only post-merge safety check must pass before
any branch cleanup. The ``make pr-post-merge-check`` target is the fixed
entry point.

### Usage

```bash
# Read-only check (default — safe, no deletion)
make pr-post-merge-check PR=1475 MERGE_COMMIT=<sha> BRANCH=<branch>

# With branch cleanup (explicit opt-in required)
make pr-post-merge-check PR=1475 MERGE_COMMIT=<sha> BRANCH=<branch> CONFIRM_CLEANUP=1
```

### Checks performed

1. PR state is ``MERGED``.
2. Merge commit SHA is valid (>= 7 characters).
3. Merge commit is reachable from ``origin/main``.
4. Production Gate CI workflow exists for the merge commit.
5. Production Gate CI status is ``completed`` and conclusion is ``success``.
   This implies Run Gatekeeper, AI Workflow Gate (P0), and Docker Build
   Validation all passed (they are jobs/steps within the same workflow).
6. Local ``main`` can fast-forward sync to ``origin/main``.
7. Working tree is clean (no uncommitted changes).

### Safety rules

- Default mode is **read-only**. No branch deletion without explicit opt-in.
- Set ``CONFIRM_CLEANUP=1`` to delete the remote branch and local branch.
- Without ``CONFIRM_CLEANUP=1``, remote and local branches are **never**
  deleted.
- If the Production Gate CI run cannot be found, the check **fails** — no
  guessing, no fallback.
- If the Production Gate CI conclusion is anything other than ``success``
  (including ``failure``, ``cancelled``, ``skipped``, ``in_progress``), the
  check **fails** — branch cleanup is blocked.
- Any uncertain situation must cause a failure and stop. No automatic
  recovery, no automatic branch deletion.

### Post-merge cleanup timing rule

Post-merge cleanup must **not** be performed before main CI success is
confirmed. If the Production Gate on the merge commit has not completed or
has failed, the branch must not be deleted.

### No auto-start

After post-merge check passes (and optional cleanup completes):

- Do **not** start the next task automatically.
- Recommended next task only after user confirmation.

### Script

The underlying script is ``scripts/devops/pr_post_merge_check.py``:

```bash
python scripts/devops/pr_post_merge_check.py \
  --pr <PR_NUMBER> \
  --merge-commit <SHA> \
  --branch <BRANCH> \
  [--confirm-cleanup] \
  [--json]
```
