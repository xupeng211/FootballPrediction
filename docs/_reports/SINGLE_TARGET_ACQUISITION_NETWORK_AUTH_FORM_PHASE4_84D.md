# Phase 4.84D: Single-Target Acquisition Network Dry-Run Authorization Form

**Date**: 2026-05-10
**Status**: Complete (template-only, local-only)
**Previous phases**: 4.79D, 4.80D, 4.81D, 4.82D, 4.83D
**Recommended next phase**: Phase 4.85D or Phase 4.56A

---

## 1. Executive Summary

Phase 4.84D adds a network dry-run authorization form template and a local
validator for the future first single-target acquisition network dry-run.

This phase did not:

- access network
- perform acquisition
- write DB
- write staging
- write packet files

The goal is to define the authorization form that humans must complete before a
future real single-target network dry-run can even be proposed.

---

## 2. Implemented Files

- `docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_FORM_TEMPLATE.md`
- `scripts/ops/single_target_acquisition_network_auth_form_validate.js`
- `tests/unit/single_target_acquisition_network_auth_form_validate.test.js`
- `Makefile` targets
- `AGENTS.md` update
- `docs/_reports/SINGLE_TARGET_ACQUISITION_NETWORK_AUTH_FORM_PHASE4_84D.md`

---

## 3. Authorization Form Sections

The authorization form template includes these sections:

- `request`
- `source_terms`
- `network_authorization`
- `proxy_browser_network_preflight`
- `required_inputs`
- `safety`
- `approvals`

The YAML block remains machine-readable and enforces template-only status.

---

## 4. Validation Behavior

The validator is:

- local-only
- read-only
- in-process

It verifies that:

- the form remains `template_only`
- all authorization fields remain false / no in the template
- single-target / no-bulk constraints remain in force
- no network execution occurs
- no runtime writes occur

It also keeps the commit path blocked in Phase 4.84D.

---

## 5. Relationship to Previous Phases

- 4.79D handles runtime parameter scaffold
- 4.80D handles artifact / manifest schema validation
- 4.81D handles writer path / authorization preflight
- 4.82D handles staging packet preview
- 4.83D handles pre-network runbook draft
- 4.84D handles authorization form template

All six phases remain non-executing. None equals a real network dry-run.

---

## 6. Recommended Next Phase

Recommended:

`Phase 4.85D: single-target acquisition network dry-run final readiness checklist`

Goals:

- still no network
- consolidate runbook + auth form + packet preview

Alternative:

`Phase 4.56A: 用户给齐真实 network dry-run 参数后才做 runbook`

---

## 7. Explicit Non-Execution

The following were not executed:

- DB writes
- non-SELECT DB SQL
- external download
- `curl`
- `wget`
- `git clone`
- external football data access
- external odds data access
- scraping
- browser automation
- proxy runtime
- harvest
- ingest
- batch backfill
- network dry-run
- bulk harvest
- runtime staging artifact write
- runtime staging directory creation
- runtime source manifest write
- packet file write
- `pg_dump`
- `pg_restore`
- model training
- real prediction
- model artifact loading
- Docker volume cleanup
- force push
- `git fetch --all`
- `git pull`
- file deletion
