# Phase 4.55C Acquisition Engine Rationalization

Date: 2026-05-05

## 1. Current Head / Branch

- Starting HEAD: `059248f7eff0ddbf8c597de4feff78ad620d411a`
- Working branch: `docs/acquisition-engine-rationalization-phase455c`
- Base branch: `main`

## 2. Why This Review Was Needed

The repo now has a registry and a scaffold-only network gate, but the acquisition surface is still operationally noisy:

- multiple legacy engines still exist
- some names hide risk
- some dry-run claims are low-trust
- some scripts mix discovery, acquisition, normalization, DB writes, and downstream orchestration
- Codex needs a canonical route instead of a pile of historical entrypoints

Phase 4.55C therefore treats the current engine set as an architecture map problem, not an implementation problem.

## 3. Current 13-Engine Overview

The Phase 4.54 registry currently tracks 13 engines:

1. `real_finished_csv_staging_dry_run`
2. `raw_match_data_local_ingest`
3. `finished_match_backfill_preflight`
4. `csv_bulk_loader`
5. `local_dom_ingestor`
6. `run_production`
7. `titan_discovery`
8. `recon_scanner`
9. `batch_historical_backfill`
10. `fetch_and_adapt_euro_leagues`
11. `odds_harvest_pipeline`
12. `total_war_pipeline`
13. `titan_marathon`

High-level split:

- local read-only / preflight gates: 3
- local loaders / ingestors with commit paths: 2
- legacy or high-risk network / bulk engines: 8

## 4. Layered Architecture

Recommended future layering:

- Layer 0: registry / policy / gate
- Layer 1: source manifest / provenance
- Layer 2: discovery only
- Layer 3: single-target acquisition only
- Layer 4: local staging normalization
- Layer 5: local staging dry-run
- Layer 6: small DB write with `pg_dump`
- Layer 7: raw / L3 / training feature dry-run
- Layer 8: training / prediction

## 5. Engine Placement and Recommendation

### Keep canonical

- `real_finished_csv_staging_dry_run`
    - Layer 1 / 5
    - canonical local staging + manifest dry-run
    - keep

- `raw_match_data_local_ingest`
    - Layer 5 / 6 / 7
    - canonical raw fixture preview
    - keep, but commit remains blocked

- `finished_match_backfill_preflight`
    - Layer 5 / 7
    - canonical chain readiness preview
    - keep

### Keep behind gate

- `csv_bulk_loader`
    - Layer 4 / 6
    - useful as a local loader, but only behind explicit commit gate
    - keep behind gate

- `local_dom_ingestor`
    - Layer 4 / 6
    - useful as local normalization from captured HTML, but not a default acquisition route
    - keep behind gate

### Discovery candidate

- `titan_discovery`
    - Layer 2 candidate
    - potentially reusable as discovery-only entrypoint
    - first fix dry-run trust and CLI flag propagation
    - no AI default execution until proven

### Single-target adapter candidates

- `fetch_and_adapt_euro_leagues`
    - Layer 3 / 4 candidate
    - can become a source-specific adapter if rewritten around manifest + no-network tests
    - current form is blocked

- `odds_harvest_pipeline`
    - Layer 3 candidate for odds acquisition
    - only after single-target isolation, manifest binding, and no-db dry-run mode
    - current form is blocked

### Gate-only / quarantine / deprecate

- `run_production`
    - legacy production path
    - mixes network harvest, DB writes, file writes, and production runtime assumptions
    - gate-only, not canonical

- `recon_scanner`
    - high-risk browser / proxy / Redis / DB coupled path
    - quarantine until browser, source probing, and persistence boundaries are isolated

- `batch_historical_backfill`
    - legacy bulk orchestrator
    - not suitable for early real-data single-target route
    - keep blocked

- `total_war_pipeline`
    - legacy bulk super-orchestrator
    - quarantine / deprecate

- `titan_marathon`
    - legacy bulk harvester
    - quarantine / deprecate

## 6. Canonical Mainline Route

Recommended future mainline:

1. source registry / source manifest
2. target selection
3. single-target discovery, optional
4. single-target acquisition network dry-run
5. local staging artifact
6. source manifest hash / provenance confirmation
7. local staging dry-run
8. manual approval
9. `pg_dump`
10. small DB write
11. DB validation
12. downstream feature dry-run

Recommended command family:

- `make data-acquisition-engines`
- `make data-acquisition-engine-audit`
- `make data-single-target-network-dry-run ...`
- `make data-real-source-audit ...`
- `make data-real-finished-csv-dry-run ...`
- `make data-raw-fixture-dry-run ...`

Codex should not be pointed at legacy network or bulk entrypoints directly.

## 7. Legacy / Quarantine / Deprecation Route

Recommended strangler-style migration:

1. keep registry as the entrypoint inventory
2. force all future acquisition planning through gate + manifest
3. isolate discovery-only behavior from bulk runtime behavior
4. extract source-specific adapters from legacy scripts only when needed
5. leave legacy bulk runners blocked while the new mainline matures
6. move old engines to quarantine / deprecated status in registry metadata

Concrete route classification:

- keep canonical:
  `real_finished_csv_staging_dry_run`, `raw_match_data_local_ingest`, `finished_match_backfill_preflight`
- keep behind gate:
  `csv_bulk_loader`, `local_dom_ingestor`
- quarantine:
  `recon_scanner`, `run_production`, `total_war_pipeline`, `titan_marathon`
- deprecate:
  `total_war_pipeline`, `titan_marathon` once equivalent single-target paths exist
- candidate for rewrite:
  `titan_discovery`, `fetch_and_adapt_euro_leagues`, `odds_harvest_pipeline`
- candidate for adapter extraction:
  `run_production`, `fetch_and_adapt_euro_leagues`, `odds_harvest_pipeline`

## 8. What the Registry Still Cannot Express

Phase 4.54 registry is good enough for risk gating, but not yet for architecture governance.

Missing metadata that would help in Phase 4.56C:

- `owner`
- `status`
- `intended_layer`
- `replacement_plan`
- `deprecation_status`
- `canonical_entrypoint`
- `allowed_next_phase`
- `test_coverage`

Recommendation: add those fields in a small registry-extension phase rather than changing Phase 4.54 semantics ad hoc.

## 9. AGENTS.md Update Summary

AGENTS now explicitly states:

- Codex should not directly execute legacy / high-risk acquisition engines
- canonical path is `source -> staging -> manifest -> dry-run -> approval -> pg_dump -> small DB write`
- bulk pipelines stay gate-only / quarantine until the real-data chain matures
- every new acquisition engine must enter the registry first
- any engine allowed as read-only must first have no-network / no-db tests

## 10. Next Step Recommendation

Two clean next steps exist:

1. Phase 4.56C: extend the registry with governance fields such as owner / layer / replacement / deprecation / test coverage.
2. Phase 4.56A: only after the user provides a real target source, target engine, target match, source manifest, terms approval, and network dry-run authorization, prepare a runbook for a future single-target network dry-run.

## 11. Explicit Non-Execution

Not executed in Phase 4.55C:

- DB writes
- external download
- `curl` / `wget` / `git clone`
- external football data access
- scraping / browser automation
- harvest / ingest
- batch backfill
- real network dry-run execution
- bulk harvest
- model training
- real prediction execution
- model artifact loading
- Docker volume cleanup
- force push
- `git fetch --all`
- `git pull`
- file deletion
