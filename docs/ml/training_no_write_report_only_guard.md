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
