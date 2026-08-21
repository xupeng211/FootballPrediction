## Summary

<!-- What changed and why? Keep this outcome-focused. -->

## Scope

| Field | Value |
| --- | --- |
| Task type | `source-code`, `workflow-governance`, or another matrix task type |
| Workflow class | `NORMAL` or `STRICT` |
| Changed paths | `path/to/file` |
| Authorized paths | `path/to/file` or `none` |
| Runtime behavior changed | `yes` / `no` |
| Business progress | one concise sentence |

<!-- For a strict or workflow-governance change, state the risk boundary and authorized paths. -->

## Tests

<!-- List the actual commands, exit codes, and any intentionally unrun checks. -->

## Risk

<!-- State side effects explicitly: live fetch, DB write, raw write, training, model activation, migration, and rollback risk. -->

## Rollback

<!-- Explain the smallest safe rollback or why reverting this PR is sufficient. -->

<!--
For high-risk files, add the minimum authorization evidence required by the repository gate:

## Dangerous File Authorization
List the exact authorized paths and the owner/issue authorization.

## PR Authorization Matrix
State the task type, authorized paths, and why the change is in scope.

-->

## Strict Review Evidence

<!-- Required when Workflow class is STRICT. NORMAL PRs may leave these placeholders. -->

| Field | Value |
| --- | --- |
| Version | `1` |
| Task type | `STRICT` |
| Provider | approved independent reviewer |
| Reviewed full SHA | 40-character SHA |
| Result | `PASS` or `FINDINGS_RESOLVED` |
| Timestamp | ISO-8601 timestamp with timezone |

Do not use the PR body as a runtime database, workflow state database, SHA database, or review registry. The only exception is the narrow, machine-checked `Strict Review Evidence` contract above; it records one provider-neutral result and its exact reviewed HEAD, and does not replace the reviewer's durable result.
If the task is not complete, say so and identify the blocker. The next task must either be explicitly authorized
or say that no further task is authorized; do not automatically start another phase.
