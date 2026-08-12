# Training No-write Report-only Guard

- lifecycle: permanent
- scope: training entrypoint safety / GOLD-AUDIT-2AE
- status: active

## Contract

Training entrypoints must not treat readiness audits as training execution.

`--report-only --no-write` is the only mode intended for filtered feature matrix
inspection. It:

- reads eligible L3 rows with SELECT-only queries;
- applies `l3_prematch_safe_contract.v0.json`;
- builds matrix statistics in memory;
- prints the report to stdout;
- does not fit, train, calibrate, or save models;
- does not write datasets, reports, metadata, scalers, or model artifacts.

## Artifact Guard

Any path that saves model artifacts must require both confirmations:

```text
ALLOW_TRAINING_WRITE=yes
FINAL_TRAINING_WRITE_CONFIRMATION=yes
```

Without both values, artifact save paths fail closed.

This guard does not authorize training. It only prevents accidental writes when
future training execution is separately authorized.

## PR-6 Candidate Boundary

The canonical PR-6 producer is a separate permanent runtime path at
`src/ml/training/canonical_training_producer.py`. It accepts only an explicit
offline pre-match feature frame, validates the exact API contract, performs a
chronological/OOS split, and writes only to an explicitly supplied
non-production candidate path. Its atomic candidate write and whole-file SHA256
are candidate-production mechanics, not activation authority.

The default `npm run train` command does not query the business database or
fetch live data, has no production/activation flag, and fails without an
explicit input and candidate output. The tracked manifest remains unchanged;
`status=active`, a real production checksum, production artifact generation,
and model loading remain separately authorized operations. Existing legacy
training write guards and their `ALLOW_TRAINING_WRITE` confirmations remain
applicable to those legacy paths; they do not make those paths canonical.
