# Optimization Kanban

## TODO

## In Progress
- _None_

## Done
- [x] T1: Replace nondeterministic team/league ID mapping in `src/data/processing/football_data_cleaner.py` with deterministic database-backed logic and resilient fallback.
- [x] T2: Standardize match status usage across feature calculation, model training, and prediction services to use `MatchStatus.FINISHED` instead of the literal "completed".
- [x] T3: Implement data-driven historical averages with caching in `src/data/processing/missing_data_handler.py` to replace placeholder constants.
