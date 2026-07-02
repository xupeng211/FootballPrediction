# L3A Legacy Entrypoint Inventory Report

## Snapshot

- Lifecycle: phase-artifact.
- Main head: `df66bd97200a20887fe0c4aa44a5db7da4df7f42`.
- Main CI run: `28585411409`.
- Main CI conclusion: success.
- Scan date: 2026-07-02.
- Branch: `techdebt/l3a-legacy-entrypoint-isolation-inventory-plan`.

## Scan methods

- Grep scan for Python entrypoint patterns: `__main__`, `FastAPI`,
  `APIRouter`, `argparse`, `Typer`, `Celery`, route decorators, and `uvicorn`.
- Grep scan for JS/TS CLI/server patterns: `process.argv`, `commander`,
  `yargs`, `listen`, `node`, package exports, and command references.
- Grep scan for workflow, Docker, Makefile, and package command references.
- Temporary AST inventory for Python files using `/tmp` script output only.

## Inventory summary

- Total AST candidates: 417.
- Python grep candidates: 259 matched lines.
- JS/TS grep candidates: 1163 matched lines.
- Workflow/Docker/Make/package reference scan: 1859 matched lines.
- Likely active entrypoints: 7 representative surfaces.
- Likely legacy/high-risk entrypoints: 12 representative surfaces.
- Unknown / needs owner decision: 47 AST-category unknown candidates plus
  unclassified script references.

## Important findings

1. `src/main.py` is the only high-confidence active API app entrypoint.
2. `Dockerfile` and `docker-compose.yml` both point to `uvicorn src.main:app`.
3. `src/main.py` mounts health, monitoring, model management, and optional admin routers.
4. `src/api/predictions/predict_router.py` is an alternate prediction router candidate, not the current `/predict` owner.
5. `AGENTS.md` already marks `titan_discovery.js`, `run_production.js`, `batch_historical_backfill.js`, and `total_war_pipeline.js` as deprecated/admin-only for agents.
6. `odds_harvest_pipeline.js` is explicitly blocked for agents without future authorization.
7. Package scripts still expose training, prediction, harvest, odds, smelt, and L3 commands that can look active to agents.
8. Many maintenance scripts have `__main__` or `argparse`; they should remain task-scoped, not opportunistically fixed.
9. Archive and legacy test trees contain runnable-looking files but should be treated as historical or test-only.
10. L3B should confirm a whitelist before adding labels or guard wording.

## Risk map

| Risk | Paths | Reason |
|---|---|---|
| High | `scripts/ops/run_production.js`, `scripts/ops/titan_discovery.js`, `scripts/ops/total_war_pipeline.js`, `scripts/ops/batch_historical_backfill.js`, `scripts/ops/odds_harvest_pipeline.js` | Can trigger harvest, network, raw ingest, orchestration, or odds flows. |
| Medium | `scripts/ops/train_model.py`, `scripts/ops/predict_pipeline.py`, `scripts/ops/smelt_all.js`, `scripts/ops/l3_stitch_pipeline.js`, `scripts/maintenance/**` | Training, prediction, feature, or maintenance semantics require explicit scope. |
| Medium | `src/api/predictions/predict_router.py` | Looks like a prediction API owner but current runtime is `src/main.py`. |
| Low | `tests/**`, `scripts/devops/**`, `.github/**`, `archive_vault_2026/**` | Test/governance/archive surfaces, but names can still confuse static scans. |

## Recommended next step

Do not start automatically.

Recommended: L3B active entrypoint whitelist confirmation.

## Raw artifacts

Raw scan outputs remain in `/tmp` only:

- `/tmp/techdebt_l3a_python_entrypoint_candidates.txt`
- `/tmp/techdebt_l3a_js_ts_entrypoint_candidates.txt`
- `/tmp/techdebt_l3a_runtime_references.txt`
- `/tmp/techdebt_l3a_entrypoint_inventory.json`
- `/tmp/techdebt_l3a_entrypoint_inventory_summary.json`
