# Clone Guide

## Recommended Daily Clone

Use a shallow, single-branch, no-tags clone for normal development:

```bash
git clone \
  --single-branch \
  --branch main \
  --depth 1 \
  --no-tags \
  git@github.com:xupeng211/FootballPrediction.git
```

For this repository, do not add:

```bash
--filter=blob:none
```

## Why `--filter=blob:none` Is Not Recommended

Local timing after the history rewrite showed that `--filter=blob:none` is slower for this repository.

Observed results:

- SSH shallow clone without blob filtering was faster than blobless shallow clone.
- `.git` size was nearly unchanged with blob filtering.
- Checkout was not the bottleneck.
- The current `HEAD` tree is approximately 14 MiB.
- The current tracked file count is approximately 992.
- Remaining clone latency appears more related to GitHub Git transfer, pack generation, or the local network path than to working tree size.

## After The History Rewrite

The repository history has been rewritten to remove large generated, model, data, and environment artifacts from the main history.

Important rules:

- Old clones should not be used for normal development or push workflows.
- Collaborators should create a fresh clone.
- `models/` and `model_zoo/` are no longer tracked by Git.
- A fresh clone does not include model artifacts.
- Missing artifacts should be handled through the model artifact manifest and checker workflow.

## Fresh Clone Setup

After cloning, create a local environment file from the committed template:

```bash
cp .env.example .env
docker compose config
```

`.env` is a local machine configuration file and must not be committed.

`.env.example` is the committed template that keeps safe local defaults for Docker Compose and development setup.

Model artifacts are not distributed through Git. If model files are missing, use the artifact documentation and checker paths:

- Manifest template: `config/model_artifacts.example.json`
- Artifact guide: `docs/MODEL_ARTIFACTS.md`
- Checker script: `scripts/model_artifacts/check_model_artifacts.py`

For a fresh clone that does not have local model artifacts yet, use the checker in allow-missing mode when validating artifact wiring:

```bash
python3 scripts/model_artifacts/check_model_artifacts.py --allow-missing
```

## Recommended Local Development Directory

The recommended local development clone on this machine is:

```text
/home/xupeng/FootballPrediction.clean-dev
```

Keep the older `/home/xupeng/FootballPrediction` directory only as a local reference unless it is intentionally migrated.
