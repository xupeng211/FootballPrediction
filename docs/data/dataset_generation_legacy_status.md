# Dataset Generation Legacy Status

Status: legacy / non-production

## Current finding

- `src/ml/dataset/dataset_generator.py` is not the production training dataset builder.
- It uses mock/random historical data.
- It has a known mismatch between `ClassificationDatasetGenerator` and `MatchFeatureExtractor` call shape.
- It should not be used for real training, training dry-run, or production backtest.

## Production path

The current prematch-safe production path is:

- `l3_features`
- `config/features/l3_prematch_safe_contract.v0.json`
- `src/ml/features/l3_prematch_contract.py`
- `scripts/model_training/train_baseline_v1.py`
- `scripts/ops/train_model.py`
- `src/database/repositories/prediction_repo.py`

## Safety status

- Production training path: protected by #1721.
- Production prediction path: protected by #1722.
- `dataset_generator.py`: legacy / non-production.

## Blocked usage

Do not use `dataset_generator.py` for:

- real training;
- training dry-run;
- production backtest;
- evidence that production dataset generation is ready.

## Allowed future work

Future work may:

- add cutoff-safety tests for `MatchFeatureExtractor`;
- retire `dataset_generator.py`;
- rewrite it as a real cutoff-safe dataset builder.
