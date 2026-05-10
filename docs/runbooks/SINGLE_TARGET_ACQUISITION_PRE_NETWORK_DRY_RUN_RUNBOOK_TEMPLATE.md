# Single-Target Acquisition Pre-Network Dry-Run Runbook Template

This document is a Phase 4.83D draft-only template for a future single-target acquisition
network dry-run runbook.

- This is a draft, not an authorization.
- `network_dry_run_authorized=false`
- `staging_write_authorized=false`
- `db_write_authorized=false`
- Even if a future operator fills `yes` in CLI fields, execution must still move to a later,
  separately authorized phase.
- Codex must not change this template to approved or authorized on its own.
- A real network dry-run requires explicit user-supplied parameters and explicit human authorization.

```yaml
phase: PHASE4.83D_SINGLE_TARGET_ACQUISITION_PRE_NETWORK_RUNBOOK_DRAFT
runbook_status: draft_only
network_dry_run_ready: false
network_dry_run_authorized: false
staging_write_authorized: false
db_write_authorized: false
training_authorized: false
prediction_authorized: false
final_human_confirmation: false

target:
    target_source:
    target_engine_family: titan_discovery
    target_scope_type:
    target_match_id:
    target_league:
    target_season:
    target_date:

source_terms:
    terms_url:
    license_url:
    allowed_use:
    terms_approval: no
    human_approval_note:

authorizations:
    network_dry_run_authorization: no
    allow_browser_runtime: no
    allow_proxy_runtime: no
    allow_external_network: no
    allow_staging_write: no
    staging_write_authorization: no
    final_human_confirmation: no

preflight_inputs:
    runtime_scaffold_required: true
    schema_validation_required: true
    writer_preflight_required: true
    staging_packet_preview_required: true
    source_manifest_candidate_required: true
    output_root_required: true

proxy_browser_network:
    proxy_required:
    proxy_provider:
    proxy_health_check_required: true
    browser_required:
    browser_provider:
    network_policy:
    rate_limit_policy:
    retry_policy:
    user_agent_policy:
    no_login_paywall_bypass: true
    no_anti_bot_bypass: true
    no_bulk_expansion: true

safety:
    would_access_network: false
    would_launch_browser: false
    would_use_proxy: false
    would_execute_engine: false
    would_write_staging: false
    would_create_staging_directory: false
    would_write_source_manifest: false
    would_write_db: false
    would_train: false
    would_predict: false
    would_bulk_harvest: false

stop_conditions:
    - missing_terms_approval
    - missing_network_authorization
    - target_scope_not_single_target
    - output_root_invalid
    - schema_validation_failed
    - packet_preview_failed
    - any_would_write_db_true
    - any_bulk_scope_detected
    - any_legacy_runtime_required

next_phase_requirements:
    - explicit_target_source
    - explicit_single_target_scope
    - reviewed_source_terms
    - explicit_network_dry_run_authorization
    - accepted_proxy_browser_network_preflight
    - accepted_staging_packet_preview
    - confirmed_no_db_write
    - confirmed_no_training
    - confirmed_no_prediction
```

## Purpose

This template captures the information that must exist before a real single-target network
dry-run can even be proposed. It does not permit:

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

The runbook draft must explicitly describe:

1. target source and single-target scope
2. source terms, license, and allowed use
3. human authorization state
4. preflight dependencies from Phases 4.79D, 4.80D, 4.81D, and 4.82D
5. proxy/browser/network policy
6. stop conditions
7. next requirements before any future real network dry-run phase

## Draft-only guardrails

- `runbook_status` must remain `draft_only`
- `network_dry_run_ready` must remain `false`
- `network_dry_run_authorized` must remain `false`
- `staging_write_authorized` must remain `false`
- `db_write_authorized` must remain `false`
- `training_authorized` must remain `false`
- `prediction_authorized` must remain `false`
- `final_human_confirmation` must remain `false`

Changing any of the above does not authorize execution inside Phase 4.83D. Future authorization
must happen in a separate phase with explicit user approval, complete parameters, reviewed terms,
and an approved follow-up runbook or authorization form.
