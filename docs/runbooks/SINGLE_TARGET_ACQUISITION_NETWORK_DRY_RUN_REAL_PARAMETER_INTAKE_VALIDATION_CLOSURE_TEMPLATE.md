# Single-Target Acquisition Network Dry-Run Real-Parameter Intake Validation Closure Template

This document is a Phase 4.91D template-only validation closure for a future
user-filled real-parameter intake.

- This is a real-parameter intake validation closure template, not proof that
  validation has passed.
- This is not a network dry-run authorization document.
- `real_parameter_intake_validation_ready=false` by default.
- `real_parameter_intake_validated=false` by default.
- `real_parameters_provided=false` by default.
- Every `validation_passed` field is `false` by default.
- Codex must not fill real source, target, terms, or authorization values for
  the user.
- Codex must not change any `validation_passed` value to `true` on its own.
- Codex must not authorize network dry-run execution.
- Phase 4.91D does not write a real parameter validation closure runtime file.
  It only validates this template and produces a local stdout preview.
- A real network dry-run must move to a later, separately authorized phase
  after the user explicitly fills the real parameters and that filled intake is
  independently reviewed.

```yaml
phase: PHASE4_91D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE
validation_closure_status: template_only
real_parameter_intake_validation_ready: false
real_parameter_intake_validated: false
real_parameters_provided: false
network_dry_run_authorized: false
network_dry_run_execution_allowed: false
staging_write_authorized: false
db_write_authorized: false
training_authorized: false
prediction_authorized: false
final_human_confirmation: false

validation_rule_groups:
    real_target_validation:
        required: true
        rule_complete: true
        validation_passed: false
        requires_target_source: true
        requires_engine_family_titan_discovery: true
        requires_single_target_scope: true
        allows_match_id_scope: true
        allows_league_season_date_scope: true
        max_targets: 1
        bulk_scope_allowed: false
    source_terms_validation:
        required: true
        rule_complete: true
        validation_passed: false
        requires_source_homepage_url: true
        requires_terms_url: true
        requires_license_url: true
        requires_allowed_use_summary: true
        requires_terms_reviewed_by: true
        requires_terms_approval_yes: true
    network_authorization_validation:
        required: true
        rule_complete: true
        validation_passed: false
        requires_network_dry_run_authorization_yes: true
        requires_allow_external_network_yes_or_explicit_no: true
        requires_browser_runtime_policy: true
        requires_proxy_runtime_policy: true
        requires_no_bulk_expansion_confirmation: true
    staging_policy_validation:
        required: true
        rule_complete: true
        validation_passed: false
        requires_output_root_policy: true
        requires_schema_validation: true
        requires_source_manifest_policy: true
        requires_staging_write_authorization_decision: true
    no_db_training_prediction_validation:
        required: true
        rule_complete: true
        validation_passed: false
        requires_no_db_write_confirmation: true
        requires_no_training_confirmation: true
        requires_no_prediction_confirmation: true
        requires_no_model_artifact_loading_confirmation: true
    final_human_confirmation_validation:
        required: true
        rule_complete: true
        validation_passed: false
        requires_confirmed_by: true
        requires_final_confirmation_yes: true

validation_blocking_reasons:
    - real_parameters_not_provided
    - real_target_not_validated
    - source_terms_not_validated
    - network_authorization_not_validated
    - staging_policy_not_validated
    - no_db_training_prediction_policy_not_validated
    - final_human_confirmation_not_validated
    - future_separate_phase_required

included_artifacts:
    real_parameter_intake: docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md
    blocked_summary: docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md

codex_constraints:
    codex_may_not_self_fill_real_parameters: true
    codex_may_not_mark_validation_passed: true
    codex_may_not_authorize_network: true
    codex_may_not_enable_execution: true
    codex_may_not_write_runtime_files: true

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
    would_write_real_parameter_validation_closure_file: false
    would_write_db: false
    would_train: false
    would_predict: false
    would_bulk_harvest: false

next_phase_requirements:
    - user_fills_real_parameter_intake
    - separate_phase_validates_filled_intake
    - separate_phase_reviews_terms_and_authorization
    - separate_phase_confirms_single_target_scope
    - separate_phase_confirms_no_db_write
    - separate_phase_confirms_no_training
    - separate_phase_confirms_no_prediction
```

## Purpose

This template defines how a later phase should evaluate a user-filled
real-parameter intake before any single-target acquisition network dry-run can
be proposed.

It defines validation rules for:

- real target completeness
- single-target scope validity
- source terms, license, and allowed-use fields
- explicit network authorization
- browser, proxy, and external network policy
- staging policy
- no-DB-write confirmation
- no-training confirmation
- no-prediction confirmation
- final human confirmation
- absence of bulk scope
- absence of Codex self-filled real parameters

## Guardrails

Even if a future intake is complete, Phase 4.91D does not execute a network
dry-run. A filled intake must still move through a later, separately authorized
review phase that checks the filled parameters, terms approval, network
authorization, staging policy, no-DB/no-training/no-prediction confirmations,
and final human approval.

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
- real parameter validation closure runtime file writes
- DB writes
- training
- prediction

The template must remain `template_only` in Phase 4.91D. Codex cannot supply or
infer real source, target, terms, license review, allowed-use review, network
authorization, staging policy, validation pass status, or final human
confirmation for the user.
