# AI Agent Workflow Hardening — Phase 1

- lifecycle: permanent
- owner: project governance
- created: 2026-06-25
- task: agent_workflow_hardening_phase1
- hardening_type: CI discipline / PR lifecycle / final report / main Gate evidence
- sc002_status: enforcement infrastructure complete

## Purpose

This document codifies the rules AI agents (Claude Code and similar) MUST follow when
executing PR workflows in this repository. These rules exist because agents have
repeatedly:

- Used custom `while true` / `until` / `sleep` / `Monitor` loops to watch CI
- Skipped `make watch-pr PR=<number>` for CI observation
- Produced final reports claiming "main green" without a post-merge main Gate run id
- Claimed independent verification while only forwarding CI-reported results
- Worked directly on `main` without creating branches
- Omitted remote branch deletion after merge
- Treated "reported success" as equivalent to "independently verified success"
- Continued an unrelated unfinished task (e.g., staging deployment) during a new task

These rules are **non-negotiable** and enforced by:
- `CLAUDE.md` resident rules
- `scripts/ops/ai_workflow_gate.py` CI enforcement
- `scripts/ops/helpers/agent_workflow_hardening_checks.py` check functions
- `tests/unit/test_agent_workflow_hardening.py` static tests
- `.github/pull_request_template.md` PR checklist

## Standard PR Lifecycle

1. **Branch creation:** From clean latest `origin/main`. Verify `HEAD == origin/main`.
2. **Implementation:** Work on feature branch only. Never on `main`.
3. **Pre-push validation:** `make pr-gate-local PR_BODY=/tmp/pr_body.md` (fast mode).
4. **PR creation:** Push branch, open PR with complete PR body.
5. **CI observation:** `make watch-pr PR=<number>` — the **only** allowed command.
6. **Merge:** Only after PR Gate is green. Use squash or merge commit.
7. **Post-merge main Gate:** `gh run list --branch main --limit 3` then `gh run view <run-id> --json status,conclusion`. Record the run id.
8. **Branch cleanup:** `git push origin --delete <branch>` after merge.
9. **Final report:** Complete report with all evidence fields.
10. **Completion:** Only when PR merged + PR Gate green + main Gate green (with run id) + branch deleted + working tree clean + final report complete.

## Forbidden CI Watch Patterns

The following patterns are **ABSOLUTELY FORBIDDEN** for watching CI:

| Forbidden Pattern | Example |
|---|---|
| `while true` loop | `while true; do gh pr checks $PR; sleep 30; done` |
| `until` loop | `until gh pr checks $PR --json state --jq '.[] | select(.state=="SUCCESS")'; do ...` |
| `sleep`-based polling | `sleep 60; gh run list ...; sleep 60; ...` |
| `Monitor` tool wrapper | Monitor tool with `while true; do gh pr checks ...; sleep 30; done` |
| `grep`-based CI wait | `gh pr checks $PR \| grep -v "pending"` in a loop |
| Custom `watch` loop | Any shell loop combining `gh` + `sleep`/`while`/`until` |
| `gh run watch --exit-status` in a loop | Single invocation only; not wrapped in a polling loop |
| Cron-based CI polling via CronCreate | `CronCreate` with `*/5 * * * *` + `gh pr checks` |

## Required CI Watch Commands

### PR Gate (before merge)

**Only allowed command:**
```bash
make watch-pr PR=<number>
```

**Single-shot fallback (if `make watch-pr` fails due to gh version):**
```bash
gh pr checks <number>
```

**What is NOT allowed:**
- Wrapping `make watch-pr` in any loop
- Running `make watch-pr` repeatedly in a `while`/`until`/`sleep`/`Monitor` loop
- Using Monitor tool to stream `gh pr checks` output

### Main Gate (post-merge)

**Only allowed commands:**
```bash
# Step 1: Find the run
gh run list --branch main --limit 3

# Step 2: View a specific run's conclusion
gh run view <run-id> --json status,conclusion

# Step 3 (optional): Watch a specific run complete
gh run watch <run-id> --exit-status
```

**What is NOT allowed:**
- Any custom loop wrapping these commands
- Claiming "main green" without a specific run id
- Using `make watch-pr` (this is for PR checks, not main branch runs)

### Rationale

Custom CI watch loops cause:
- **Unnecessary API load:** Polling every few seconds = hundreds of redundant requests
- **Observability gaps:** Custom loops swallow failures that standard tooling reports
- **Drift across agents:** Every agent invents its own pattern; no standardization
- **Cache waste:** Token cache is ~5 min; short polling burns it with no benefit

`make watch-pr` uses `gh pr checks --watch --interval 15` which is the standard,
well-tested `gh` mechanism. If it fails, agents should fall back to a single-shot
`gh pr checks <number>` and report the result to the user.

## Final Report Template

Every task completion MUST include a final report with ALL of the following fields.
Omission of any field means the task is NOT complete.

```markdown
## Final Report

| Field | Value |
|---|---|
| PR number / URL | `<number>` / `<url>` |
| head SHA (full 40-char) | `<sha>` |
| merge commit SHA (full 40-char) | `<sha>` |
| PR Gate run id | `<run-id>` |
| PR Gate result | `success` / `failure` / `cancelled` |
| post-merge main Gate run id | `<run-id>` (or "could not be independently verified") |
| post-merge main Gate result | `success` / `failure` / `cancelled` / `not verified` |
| remote branch deleted | `yes` / `no` |
| main green | `yes` / `no` / `not verified` |
| independently verified | `yes` (run id present) / `no` (reported only) |
| DB connected | `yes` / `no` |
| SQL executed | `yes` / `no` |
| training executed | `yes` / `no` |
| data expansion executed | `yes` / `no` |
| real DB write executed | `yes` / `no` |
| SC-002 status | `enforcement complete` |
| training / data expansion / real DB write remain blocked | `yes` / `no` |
| next recommended task | `<description>` |
| Do not start automatically | `confirmed` |
```

## Main Gate Evidence Rules

### Rule: No run id → No "main green"

- If a post-merge main Gate run id is NOT available, the agent MUST write:
  `"main Gate could not be independently verified by merge commit; needs explicit run id"`
- The agent MUST NOT write "main green yes" without a concrete run id.

### Rule: Report what you verified, not what you were told

- CI-reported success is `reported success`. It is NOT `independently verified success`.
- The agent's own `gh run view <run-id> --json status,conclusion` output IS independent verification.
- The final report MUST distinguish between these two categories:
  - **Reported success:** CI dashboard shows "green". The agent has not independently confirmed.
  - **Independently verified success:** Agent ran `gh run view` or `gh run watch` and saw `"conclusion":"success"`.

### Rule: Merge-commit run lookup may fail

- If `gh run list --branch main --limit 3` does NOT show a run for the merge commit, the agent MUST:
  1. Note that the run could not be found by merge commit
  2. Check if a run exists for a nearby commit/same push
  3. If found, report that run id with the caveat that it's a nearby commit, not the exact merge commit
  4. If not found, report `"main Gate could not be independently verified"`
- Do NOT silently substitute a run from a different branch or an earlier push without noting the substitution.

### Rule: Gate result ≠ task complete

- A green CI run proves the CI checks passed. It does NOT prove:
  - The task's intended outcome was achieved
  - All manual verification steps were performed
  - The branch was deleted
  - The working tree is clean
- "Task complete" requires ALL completion criteria, not just CI green.

## Branch Safety Rules

### Pre-task mandatory check

Before starting ANY task, the agent MUST:

```bash
git branch --show-current
git status --short
```

If the current branch is **not** the expected branch:
1. State what branch we are on and why
2. Explain what the current branch was for
3. Get user confirmation before switching

If there are **uncommitted modifications**:
1. Stop immediately
2. List the modified files
3. Ask the user whether to stash, discard, or commit
4. Do NOT proceed without explicit user instruction

### Main-branch work prohibition

- Working directly on `main` is **NEVER** allowed
- If accidentally on `main`, create a feature branch immediately before any changes
- The only allowed `main` operations are: `git checkout`, `git pull`, branch creation

### Stale branch handling

- If a previous task left a branch (e.g., `chore/sc002-staging-db-role-deployment`),
  the agent MUST handle it before creating a new branch:
  - **Clean branch (no local commits):** Checkout main, delete local branch
  - **Branch with local commits:** Stop, report the commits, ask user how to proceed
  - **Branch with uncommitted changes:** Stop, report the changes, ask user

## Scope Drift Rules

### Same-task continuity prohibition

- If the current task is X, the agent MUST NOT continue an unfinished task Y from a
  previous conversation/session unless the user explicitly authorizes it.
- Example: If the previous task was `sc002_staging_db_role_deployment` (staging DB
  deployment) and it was correctly stopped due to missing staging env vars, the agent
  MUST NOT continue staging deployment during a new workflow hardening task.

### Cross-scope prohibition

| Current task scope | Must not also do |
|---|---|
| workflow/governance | runtime business logic, DB writes, migrations |
| docs/tests only | runtime code changes, scraper/browser, training |
| static analysis | DB connections, SQL execution, network access |
| SC-002 audit | training, data expansion, production DB access |
| staging DB deployment | production DB deployment, training, data expansion |

### Drift detection

If the agent detects it is drifting into a forbidden scope:
1. Stop the drifting action immediately
2. Report the scope boundary violation
3. Do NOT complete the drifting action "just this once"
4. Return to the authorized task scope

## Completion Definition

### What counts as "task complete"

ALL of the following must be true:

| Criterion | Verification |
|---|---|
| PR merged | `gh pr view <number> --json state --jq '.state'` returns `MERGED` |
| PR Gate green | `gh pr checks <number>` shows all checks passing |
| post-merge main Gate green | `gh run view <run-id> --json conclusion` returns `"success"` |
| main Gate run id recorded | Specific run id is in the final report |
| remote branch deleted | `git push origin --delete <branch>` succeeded or branch does not exist |
| working tree clean | `git status --short` returns empty |
| final report complete | All 20+ fields present |

### What does NOT count as "task complete"

| Claim | Why insufficient |
|---|---|
| "PR merged" | Merge is not completion; post-merge main Gate must be verified |
| "CI passed on PR" | PR Gate ≠ main Gate; main may fail after merge |
| "main was green before merge" | Pre-merge main green does not guarantee post-merge main green |
| "main looks green in the dashboard" | Web dashboard is reported success, not independently verified |
| "the merge commit should trigger a run" | Expectation is not evidence; must have actual run id |
| "branch deleted on GitHub" | Local branch may also need cleanup |
| "the agent reported CI passed" | Agent report ≠ independent verification |

## Examples

### ACCEPTABLE CI watch commands

```bash
# Standard PR Gate watch
make watch-pr PR=1607

# Single-shot fallback (one invocation, no loop)
gh pr checks 1607

# Post-merge main Gate discovery
gh run list --branch main --limit 3

# Verify a specific run
gh run view 1234567890 --json status,conclusion

# Watch a specific main Gate run (single invocation)
gh run watch 1234567890 --exit-status
```

### UNACCEPTABLE CI watch commands

```bash
# FORBIDDEN: while-true-sleep loop
while true; do gh pr checks 1607; sleep 30; done

# FORBIDDEN: until loop
until gh run list --branch main --status completed | grep -q "push"; do sleep 30; done

# FORBIDDEN: Monitor-based polling
Monitor --command "while true; do gh pr checks 1607 | grep -v pending; sleep 30; done"

# FORBIDDEN: for loop polling
for i in {1..20}; do gh pr checks 1607; sleep 15; done

# FORBIDDEN: Cron-based CI polling
CronCreate --cron "*/5 * * * *" --prompt "Check CI status and notify me"

# FORBIDDEN: Wrapping make watch-pr in a loop
while ! make watch-pr PR=1607; do sleep 30; done

# FORBIDDEN: Custom sleep in a one-liner
gh pr checks 1607 && sleep 60 && gh pr checks 1607
```

## Relationship to Other Governance

| Document | Relationship |
|---|---|
| `CLAUDE.md` | Resident rules — the canonical source for agent behavior |
| `AGENTS.md` | General agent workflow — read first for project conventions |
| `docs/AGENT_WORKFLOW.md` | Detailed agent workflow reference |
| `docs/SC002_CLOSURE_PLAN.md` | SC-002 closure criteria and status |
| `.github/pull_request_template.md` | PR structure and checklist |
| `scripts/ops/ai_workflow_gate.py` | CI-enforced gate checks |
| `scripts/ops/helpers/agent_workflow_hardening_checks.py` | Check functions extracted from gate |

## What This Document Does NOT Do

- Modify runtime business logic
- Change DB connection, migration, or write behavior
- Authorize training, data expansion, or real DB write
- Change SC-002 guard coverage or enforcement
- Deploy to staging or production
- Connect to any database
- Execute any SQL

## Next Steps After Phase 1

1. Observe agent compliance over multiple PRs
2. If agents still use custom CI loops, escalate to CI-level enforcement
3. If final reports still lack run ids, add bot-comment validation on PR merge
4. Phase 2 candidate: automated post-merge verification bot that checks run id existence

Do not start automatically. Each step requires explicit authorization.
