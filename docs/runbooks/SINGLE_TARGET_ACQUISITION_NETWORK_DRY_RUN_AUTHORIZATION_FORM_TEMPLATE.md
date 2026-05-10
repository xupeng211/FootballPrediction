# Single-Target Acquisition Network Dry-Run Authorization Form Template

This document is a Phase 4.84D template-only authorization form for a future
single-target acquisition network dry-run.

- This is an authorization form template, not an actual authorization.
- `network_dry_run_authorized=false`
- `staging_write_authorized=false`
- `db_write_authorized=false`
- `training_authorized=false`
- `prediction_authorized=false`
- Codex must not change this template to authorized on its own.
- A real network dry-run requires explicit user-supplied source, target, terms,
  and authorization details.
- Even if a future operator fills `yes` in the form or CLI, execution must still
  move to a later, separately authorized phase. Phase 4.84D does not permit
  network execution.

```yaml
phase: PHASE4.84D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_FORM
authorization_form_status: template_only
network_dry_run_authorized: false
staging_write_authorized: false
db_write_authorized: false
training_authorized: false
prediction_authorized: false
final_human_confirmation: false

request:
    requested_by:
    requested_at:
    target_source:
    target_engine_family: titan_discovery
    target_scope_type:
    target_match_id:
    target_league:
    target_season:
    target_date:

source_terms:
    source_url:
    terms_url:
    license_url:
    allowed_use:
    terms_reviewed_by:
    terms_approval: no
    human_approval_note:

network_authorization:
    network_dry_run_authorization: no
    allow_external_network: no
    allow_browser_runtime: no
    allow_proxy_runtime: no
    allow_staging_write: no
    max_targets: 1
    bulk_scope_allowed: false
    allowed_runtime: scaffolded_single_target_only
    allowed_engine_family: titan_discovery
    forbidden_legacy_runtime: true

proxy_browser_network_preflight:
    proxy_required:
    proxy_provider:
    proxy_health_check_required:
    browser_required:
    browser_provider:
    rate_limit_policy:
    retry_policy:
    user_agent_policy:
    no_login_paywall_bypass: true
    no_anti_bot_bypass: true
    no_bulk_expansion: true

required_inputs:
    pre_network_runbook_required: true
    staging_packet_preview_required: true
    artifact_schema_required: true
    manifest_schema_required: true
    output_root_policy_required: true
    stop_conditions_required: true

safety:
    would_access_network: false
    would_launch_browser: false
    would_use_proxy: false
    would_execute_engine: false
    would_write_staging: false
    would_create_staging_directory: false
    would_write_source_manifest: false
    would_write_packet_file: false
    would_write_db: false
    would_train: false
    would_predict: false
    would_bulk_harvest: false

approvals:
    source_terms_approved_by:
    network_dry_run_approved_by:
    staging_policy_approved_by:
    final_human_confirmation_by:
```

## Purpose

This template defines what a human must provide and approve before a future
single-target acquisition network dry-run can even be proposed.

It does not permit:

- network access
- browser launch
- proxy runtime execution
- acquisition engine execution
- staging writes
- source manifest writes
- packet file writes
- DB writes
- training
- prediction

## Required sections

The authorization form template must explicitly describe:

1. request metadata and single-target scope
2. source URL, terms, license, and allowed use
3. network authorization and allowed runtime constraints
4. proxy/browser/network preflight requirements
5. pre-network runbook and packet preview prerequisites
6. safety flags that remain false in this phase
7. human approval roles for any future phase

## Template-only guardrails

- `authorization_form_status` must remain `template_only`
- `network_dry_run_authorized` must remain `false`
- `staging_write_authorized` must remain `false`
- `db_write_authorized` must remain `false`
- `training_authorized` must remain `false`
- `prediction_authorized` must remain `false`
- `final_human_confirmation` must remain `false`

Changing any of the above does not authorize execution inside Phase 4.84D.
Future network dry-run authorization must happen in a separate phase with
explicit user approval, complete parameters, reviewed terms, and an approved
follow-up readiness process.
