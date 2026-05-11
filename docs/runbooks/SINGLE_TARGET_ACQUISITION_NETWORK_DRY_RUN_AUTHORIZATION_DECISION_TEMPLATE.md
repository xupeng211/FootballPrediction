# Single-Target Acquisition Network Dry-Run Authorization Decision Template

This document is a Phase 4.95D template-only network authorization decision
record.

- This is a network authorization decision template, not authorization itself.
- `authorization_decision_status=template_only` by default.
- `authorization_decision=not_authorized` by default.
- `network_authorization_decision_ready=false` by default.
- `network_authorization_decision_recorded=false` by default.
- `network_dry_run_authorized=false` by default.
- `network_dry_run_execution_allowed=false` by default.
- Every `decision_sections.*.reviewed` field is `false` by default.
- Every `decision_sections.*.decision` field is `not_authorized` by default.
- Codex must not change `authorization_decision` to `authorized` or
  `conditionally_authorized_for_future_preparation`.
- Codex must not change `network_dry_run_authorized` to `true`.
- Codex must not change `network_dry_run_execution_allowed` to `true`.
- Phase 4.95D does not write a network authorization decision runtime file.
  It only validates this template and produces a local stdout preview.
- A real network dry-run must enter a separate execution preparation and final
  confirmation phase.

```yaml
phase: PHASE4_95D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_DECISION
authorization_decision_status: template_only
network_authorization_decision_ready: false
network_authorization_decision_recorded: false
network_dry_run_authorized: false
network_dry_run_execution_allowed: false
authorization_decision: not_authorized
authorization_decision_allowed_values:
    - not_authorized
    - denied
    - needs_revision
    - conditionally_authorized_for_future_preparation
filled_intake_reviewed: false
filled_intake_accepted: false
authorization_handoff_ready: false
authorization_handoff_completed: false
can_proceed_to_network_dry_run_preparation: false
staging_write_authorized: false
db_write_authorized: false
training_authorized: false
prediction_authorized: false
final_human_confirmation: false

included_artifacts:
    authorization_handoff_checklist: docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_HANDOFF_CHECKLIST_TEMPLATE.md
    filled_intake_review_result: docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_RESULT_TEMPLATE.md
    filled_intake_review_plan: docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_PLAN_TEMPLATE.md
    real_parameter_intake: docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md
    validation_closure: docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE_TEMPLATE.md
    blocked_summary: docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md

decision_metadata:
    decision_maker:
    decision_made_at:
    decision_notes:
    source_of_authorization:
    authorization_decision_id:
    template_only: true

decision_sections:
    scope_decision:
        reviewed: false
        decision: not_authorized
        single_target_confirmed: false
        bulk_scope_allowed: false
        max_targets: 1
        blocking_reason: scope_not_authorized
    source_terms_decision:
        reviewed: false
        decision: not_authorized
        terms_approved: false
        allowed_use_approved: false
        blocking_reason: source_terms_not_authorized
    network_runtime_decision:
        reviewed: false
        decision: not_authorized
        external_network_allowed: false
        browser_runtime_allowed: false
        proxy_runtime_allowed: false
        blocking_reason: network_runtime_not_authorized
    staging_decision:
        reviewed: false
        decision: not_authorized
        staging_write_allowed: false
        source_manifest_write_allowed: false
        blocking_reason: staging_not_authorized
    db_training_prediction_decision:
        reviewed: false
        decision: not_authorized
        db_write_allowed: false
        training_allowed: false
        prediction_allowed: false
        model_artifact_loading_allowed: false
        blocking_reason: db_training_prediction_not_authorized
    final_human_decision:
        reviewed: false
        decision: not_authorized
        final_confirmation: false
        confirmed_by:
        blocking_reason: final_human_confirmation_missing

authorization_boundaries:
    authorization_decision_is_not_execution: true
    future_execution_preparation_phase_required: true
    future_final_confirmation_required: true
    codex_may_not_authorize_network: true
    codex_may_not_enable_execution: true
    codex_may_not_self_approve_terms: true
    codex_may_not_self_accept_handoff: true
    codex_may_not_convert_decision_to_execution: true

decision_blocking_reasons:
    - authorization_decision_template_only
    - authorization_handoff_not_completed
    - filled_intake_review_result_not_accepted
    - source_terms_not_authorized
    - network_runtime_not_authorized
    - staging_not_authorized
    - db_training_prediction_not_authorized
    - final_human_confirmation_missing
    - future_execution_preparation_phase_required

codex_constraints:
    codex_may_not_self_fill_real_parameters: true
    codex_may_not_mark_decision_recorded: true
    codex_may_not_authorize_network: true
    codex_may_not_set_execution_allowed: true
    codex_may_not_mark_reviewed: true
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
    would_write_filled_intake_review_file: false
    would_write_filled_intake_review_result_file: false
    would_write_authorization_handoff_checklist_file: false
    would_write_network_authorization_decision_file: false
    would_write_db: false
    would_train: false
    would_predict: false
    would_bulk_harvest: false
    would_spawn_child_process: false

next_phase_requirements:
    - user_supplies_filled_real_parameter_intake
    - separate_phase_reviews_filled_intake
    - separate_phase_records_review_result
    - separate_phase_checks_authorization_handoff
    - separate_phase_records_authorization_decision
    - separate_phase_prepares_network_dry_run_execution
    - separate_phase_still_requires_final_human_confirmation
    - separate_phase_confirms_no_db_write
    - separate_phase_confirms_no_training
    - separate_phase_confirms_no_prediction
```

## Purpose

This template defines how a future phase should record the final decision about
whether a single-target network dry-run may proceed to preparation. It answers
which fields are required, which decision states are valid, why the default is
`not_authorized`, and which prior artifacts must be referenced before any
future decision can be considered.

The only allowed decision values are:

- `not_authorized`
- `denied`
- `needs_revision`
- `conditionally_authorized_for_future_preparation`

The default must remain `not_authorized` because Phase 4.95D has no real filled
intake, no accepted review result, no completed handoff, no human decision, and
no authorization to access external sources or execute runtime code.

## Required Prior Materials

A future decision record must reference the authorization handoff checklist,
filled-intake review result, filled-intake review plan, real-parameter intake,
validation closure, and blocked final preflight summary. The references in this
template point to templates only, not runtime approvals.

## Scope And Runtime Policy

The `scope_decision` section keeps the future scope single-target by requiring
`bulk_scope_allowed=false` and `max_targets=1`. The
`network_runtime_decision` section records whether external network, browser,
and proxy runtime would be allowed in a future phase. Phase 4.95D keeps all of
those runtime allowances `false`.

## Prohibited Actions

This template records that DB writes, training, prediction, model artifact
loading, staging writes, source manifest writes, packet writes, bulk harvest,
browser automation, proxy runtime, and engine execution are not authorized.

## Authorization Boundaries

An authorization decision template is not authorization. An authorization
decision is not execution. Even if a future human decision conditionally
authorizes preparation, a separate execution preparation phase and a separate
final human confirmation remain required before any network dry-run can occur.

Codex must not self-fill real source, target, terms, authorization, decision
maker, or confirmation fields. Codex must not convert `not_authorized` to an
authorized decision, must not set network authorization to `true`, and must not
enable execution.
