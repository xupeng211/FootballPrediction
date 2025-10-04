# Optimization Kanban

## TODO

## In Progress
- _None_

## Done
- [x] T1: Replace nondeterministic team/league ID mapping in `src/data/processing/football_data_cleaner.py` with deterministic database-backed logic and resilient fallback.
- [x] T2: Standardize match status usage across feature calculation, model training, and prediction services to use `MatchStatus.FINISHED` instead of the literal "completed".
- [x] T3: Implement data-driven historical averages with caching in `src/data/processing/missing_data_handler.py` to replace placeholder constants.
- [x] T4: Centralize runtime configuration (metrics toggles, service list, missing-data defaults) in `src/core/config.py` with cleaner environment parsing.
- [x] T5: Allow metrics collectors/exporters to honor configurable table whitelists and auto-disable during pytest runs to avoid unnecessary DB load.
- [x] T6: Support runtime reload and custom registration of missing-data fallback averages for hot updates without redeployments.
- [x] T7: Guard service registration with config-driven enablement to prevent duplicate instances across repeated app startups.
