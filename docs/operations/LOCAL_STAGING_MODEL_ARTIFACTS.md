# Local Staging Model Artifacts

## Purpose

This document defines the local staging model artifact governance boundary.

It exists because local staging can run the API stack before any model artifact has been deployed. In that bootstrap state, the model health check reports that no model file is found. That state is expected until a separately authorized model artifact deployment task is completed.

This document does not train, generate, copy, upload, or deploy any model artifact.

## Current Status

Local staging currently has no deployed model artifact.

This is intentional for the current bootstrap phase. The local staging API, database, and Redis services can be live while model-specific health remains unavailable.

The following status is expected in empty staging:

- API container can be healthy.
- `/health` can return HTTP 200.
- The model sub-check can report unhealthy or `model file not found`.
- `/predict` must not be called unless a separate model deployment task has explicitly authorized it.

## Expected Empty-Staging Health Behavior

An empty local staging environment should not be treated as a failed model deployment.

Until a model artifact is deployed, model health failures should be interpreted as:

- expected bootstrap state
- not evidence of DB failure
- not evidence of API startup failure
- not authorization to train, copy, or deploy a model

The runtime model path is defined by `src/config/ml_settings.py` (`model_path` field, with `get_model_path()`). The actual path can be configured via environment variable or config. When no artifact exists at that path, the model health sub-check reports unhealthy.

## Artifact Location Contract

This document does not create directories, mounts, or configuration.

For reference, the recommended host-side local staging model artifact root is:

```text
/home/xupeng/local-staging/artifacts/models/
```

A recommended future container-visible mount point is:

```text
/app/artifacts/models/
```

Neither directory is created by this document. No Docker Compose mount is added by this PR. No runtime configuration is changed.

If a future task deploys a model artifact, the deployer must align the actual artifact path with the runtime `model_path` configuration and document the resolution.

## Deployment Preconditions

A model artifact may only be deployed to local staging after a separate task explicitly authorizes it.

Before deployment, the following must be true:

- The artifact source and provenance are known.
- The artifact checksum is recorded.
- The artifact version is recorded.
- The expected runtime path is documented and aligned with `model_path`.
- A rollback artifact or version is available.
- No secrets are embedded in the artifact or its metadata.
- No production database connection is required for deployment or validation.
- Training or data expansion has been separately authorized if the artifact depends on it.
- SC-002 staging DB role deployment (#1637) is complete if artifact deployment depends on governed DB writes.
- Staging schema and migration planning (#1636) is complete if validation depends on DB-backed features.

## Deployment Procedure Placeholder

The future deployment procedure should be handled in a separate authorized task. This document does not authorize execution.

Expected high-level steps for a future authorized deployment:

1. Select an approved model artifact.
1. Record provenance, version, and checksum.
1. Copy the artifact to the approved local staging artifact root.
1. Align the runtime `model_path` configuration with the artifact location.
1. Add or update any required Compose or config mounts only via a separate PR.
1. Restart or reload services only after explicit approval.
1. Validate model health only after explicit approval.
1. Call `/predict` only after explicit approval.

## Validation Checklist

Before treating a local staging model artifact as deployed, verify:

- [ ] Artifact exists at the approved and configured path.
- [ ] Checksum matches the recorded value.
- [ ] Artifact provenance and version are recorded.
- [ ] No secrets are present in artifact metadata.
- [ ] Runtime configuration points to the expected path.
- [ ] A rollback artifact or version is available.
- [ ] `/health` model sub-check status is interpreted according to the current deployment phase.
- [ ] `/predict` is not called unless explicitly authorized.
- [ ] `/health/quick` is not called unless explicitly authorized.

## Rollback Plan

A future model artifact deployment must define rollback before deployment.

Minimum rollback requirements for a future authorized task:

- Keep the previous artifact version available.
- Record the previous checksum.
- Document how to switch back to the previous artifact.
- Do not delete the previous artifact until the new artifact is validated.
- Do not use rollback to bypass SC-002, migration, or DB safety requirements.

## Explicit Non-Goals

This document does not do any of the following:

- Train a model.
- Generate a model artifact.
- Copy or upload a model artifact.
- Create model directories on disk.
- Add Docker, Compose, or environment configuration.
- Restart or reload staging services.
- Execute SQL or run migrations.
- Deploy SC-002 database roles.
- Connect to production database.
- Call `/predict`.
- Call `/health/quick`.
- Start scraper, training, or data expansion pipelines.

## Relationship to SC-002 and Migration Work

Model artifact deployment is separate from SC-002 staging DB role deployment and schema/migration planning.

Related issues and work:

- #1636 — staging schema and migration planning (pending)
- #1637 — SC-002 staging DB role deployment (pending)
- #1632 — DB name validation behavior (pending)
- #1633 — DB SSL mode configuration behavior (pending)

This document only defines the model artifact governance boundary for local staging. It does not execute or authorize any of the related work.

## Related Issues

Closes #1635.
