# Claude Code Project Instructions

- lifecycle: permanent / agent-entrypoint

## Read order

Before working on this repository, treat the following files as the authoritative workflow sources:

1. AGENTS.md
2. docs/AGENT_WORKFLOW.md
3. .github/pull_request_template.md
4. docs/data/FOTMOB_CURRENT_STATE.md

Do not rely on historical ADG reports as the primary current truth. Use docs/data/FOTMOB_CURRENT_STATE.md for the latest FotMob ingestion state.

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

## Validation expectations

Before proposing completion:

- run relevant targeted tests;
- run lint / formatting checks when reasonable;
- run hidden/bidi and payload marker checks if touched files require them;
- report failures honestly;
- do not fake passing tests.
