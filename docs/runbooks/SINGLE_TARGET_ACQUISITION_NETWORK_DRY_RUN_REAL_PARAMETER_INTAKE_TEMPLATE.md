# Single-Target Acquisition Network Dry-Run Real-Parameter Intake Template

This document is a Phase 4.90D template-only intake form for a future
single-target acquisition network dry-run.

- This is a real-parameter intake template, not an authorization document.
- `real_parameters_provided=false` by default.
- Every `provided` field is `false` by default.
- `network_dry_run_authorized=false` by default.
- `network_dry_run_execution_allowed=false` by default.
- Codex must not fill real source, target, terms, or authorization values for
  the user.
- Codex must not change any `provided` value to `true` on its own.
- Phase 4.90D does not write a real parameter intake runtime file. It only
  validates this template and produces a local stdout preview.
- A real network dry-run must move to a later, separately authorized phase
  after the user explicitly fills the real parameters.

```yaml
phase: PHASE4_90D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE
intake_status: template_only
real_parameters_provided: false
network_dry_run_authorized: false
network_dry_run_execution_allowed: false
staging_write_authorized: false
db_write_authorized: false
training_authorized: false
prediction_authorized: false
final_human_confirmation: false

real_target:
    target_source:
        required: true
        provided: false
        value:
    target_engine_family:
        required: true
        provided: false
        value: titan_discovery
    target_scope_type:
        required: true
        provided: false
        value:
        allowed_values:
            - match_id
            - league_season_date
    target_match_id:
        required_when_scope_type: match_id
        provided: false
        value:
    target_league:
        required_when_scope_type: league_season_date
        provided: false
        value:
    target_season:
        required_when_scope_type: league_season_date
        provided: false
        value:
    target_date:
        required_when_scope_type: league_season_date
        provided: false
        value:
    max_targets: 1
    bulk_scope_allowed: false

source_terms:
    source_homepage_url:
        required: true
        provided: false
        value:
    terms_url:
        required: true
        provided: false
        value:
    license_url:
        required: true
        provided: false
        value:
    allowed_use_summary:
        required: true
        provided: false
        value:
    terms_reviewed_by:
        required: true
        provided: false
        value:
    terms_approval:
        required: true
        provided: false
        value: no

network_authorization:
    network_dry_run_authorization:
        required: true
        provided: false
        value: no
    allow_external_network:
        required: true
        provided: false
        value: no
    allow_browser_runtime:
        required: true
        provided: false
        value: no
    allow_proxy_runtime:
        required: true
        provided: false
        value: no
    allow_staging_write:
        required: true
        provided: false
        value: no

proxy_browser_network_policy:
    proxy_policy:
        required: true
        provided: false
        value:
    browser_policy:
        required: true
        provided: false
        value:
    rate_limit_policy:
        required: true
        provided: false
        value:
    retry_policy:
        required: true
        provided: false
        value:
    user_agent_policy:
        required: true
        provided: false
        value:
    no_login_paywall_bypass_confirmation:
        required: true
        provided: false
        value: no
    no_anti_bot_bypass_confirmation:
        required: true
        provided: false
        value: no
    no_bulk_expansion_confirmation:
        required: true
        provided: false
        value: no

staging_policy:
    output_root:
        required: true
        provided: false
        value:
        allowed_prefix: docs/_staging_preview/acquisition/single_target
    schema_validation_required: true
    source_manifest_required: true
    staging_write_authorized:
        required: true
        provided: false
        value: no

no_db_training_prediction_policy:
    no_db_write_confirmation:
        required: true
        provided: false
        value: no
    no_training_confirmation:
        required: true
        provided: false
        value: no
    no_prediction_confirmation:
        required: true
        provided: false
        value: no
    no_model_artifact_loading_confirmation:
        required: true
        provided: false
        value: no

final_human_confirmation:
    required: true
    provided: false
    confirmed_by:
    value: no

included_blocked_preflight:
    blocked_summary: docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md
    primary_blocking_reason: missing_user_supplied_real_network_dry_run_inputs

safety:
    would_access_network: false
    would_launch_browser: false
    would_use_proxy: false
    would_execute_engine: false
    would_execute_legacy_titan_discovery: false
    would_write_staging: false
    would_create_staging_directory: false
    would_write_source_manifest: false
    would_write_packet_file: false
    would_write_approval_packet_file: false
    would_write_user_input_closure_file: false
    would_write_blocked_summary_file: false
    would_write_real_parameter_intake_file: false
    would_write_db: false
    would_train: false
    would_predict: false
    would_bulk_harvest: false
```

## Purpose

This template is the intake shape a user must fill in a later phase before a
real single-target acquisition network dry-run can even be proposed.

It collects:

- real target source
- real single-target scope
- source homepage URL, terms URL, and license URL
- allowed-use summary and terms approval
- network dry-run authorization
- external network, browser runtime, and proxy runtime policy
- staging policy
- no-DB-write confirmation
- no-training confirmation
- no-prediction confirmation
- final human confirmation

## Guardrails

This template does not permit:

- network access
- browser launch
- proxy runtime execution
- legacy `titan_discovery` runtime execution
- acquisition engine execution
- staging writes
- source manifest writes
- packet file writes
- approval packet file writes
- user input closure file writes
- blocked summary runtime file writes
- real parameter intake runtime file writes
- DB writes
- training
- prediction

The template must remain `template_only` in Phase 4.90D. Codex cannot supply or
infer real source, target, terms, license review, allowed-use review, network
authorization, staging policy, or final human confirmation for the user.

Future network dry-run execution must happen in a separate phase with explicit
user-supplied real parameters, reviewed terms, network authorization, staging
policy, no-DB/no-training/no-prediction confirmation, and final human approval.
