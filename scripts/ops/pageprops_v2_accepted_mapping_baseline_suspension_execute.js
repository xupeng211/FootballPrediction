#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines -- L2V3AT keeps suspension execution evidence explicit for governance review. */

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AT';
const PHASE_NAME = 'accepted_mapping_baseline_suspension_execution';
const EXECUTION_STATUS = 'completed_accepted_mapping_baseline_suspension_execution';
const FINAL_AUTHORIZATION_EFFECTIVE_STATUS = 'blocked_or_superseded';
const NEXT_STEP_RE_ACCEPTANCE_PREREQ = 'Phase 5.21L2V3AU: re-acceptance prerequisite planning';
const NEXT_REQUIRED_STEP_RE_ACCEPTANCE_PREREQ = 're_acceptance_prerequisite_planning';
const PROPOSAL_MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const AS_PLAN_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_suspension_plan.phase521l2v3as.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_suspension_result.phase521l2v3at.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AT.md';

const REVIEWED_INPUTS = Object.freeze([
    ['as_suspension_plan', AS_PLAN_PATH],
    ['as_suspension_report', 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AS.md'],
    [
        'ar_contradiction_review_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_contradiction_review_result.phase521l2v3ar.json',
    ],
    ['ar_contradiction_review_report', 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AR.md'],
    [
        'aq_contradiction_review_plan',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_contradiction_review_plan.phase521l2v3aq.json',
    ],
    ['aq_contradiction_review_report', 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AQ.md'],
    [
        'ap_blocker_investigation_artifact',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_blocker_investigation.phase521l2v3ap.json',
    ],
    ['ap_blocker_investigation_report', 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AP.md'],
    [
        'ao_no_write_payload_recapture_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_result.phase521l2v3ao.json',
    ],
    [
        'an_no_write_payload_recapture_plan',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_plan.phase521l2v3an.json',
    ],
    [
        'am_payload_source_declaration_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_result.phase521l2v3am.json',
    ],
    [
        'al_payload_source_declaration_plan',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_plan.phase521l2v3al.json',
    ],
    [
        'ak_raw_write_input_source_investigation',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.raw_write_input_source_investigation.phase521l2v3ak.json',
    ],
    [
        'aj_controlled_raw_write_execution_plan',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_raw_match_data_write_execution_plan.phase521l2v3aj.json',
    ],
    [
        'ai_final_db_write_authorization_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.final_db_write_authorization_result.phase521l2v3ai.json',
    ],
    [
        'ag_baseline_acceptance_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.baseline_acceptance_result.phase521l2v3ag.json',
    ],
    [
        'ae_identity_mapping_acceptance_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_result.phase521l2v3ae.json',
    ],
    [
        'ac_enriched_no_write_verification_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_result.phase521l2v3ac.json',
    ],
    [
        'aa_enriched_targets',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json',
    ],
    [
        'y_source_inventory_acquisition_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json',
    ],
    [
        'm_reverse_fixture_rule_artifact',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json',
    ],
    [
        'n_expanded_reverse_fixture_verification',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json',
    ],
    ['proposal_manifest', PROPOSAL_MANIFEST_PATH],
]);

function absolutePath(filePath) {
    return path.isAbsolute(filePath) ? filePath : path.join(PROJECT_ROOT, filePath);
}

function readTextFile(filePath) {
    return fs.readFileSync(absolutePath(filePath), 'utf8');
}

function readJsonFile(filePath) {
    return JSON.parse(readTextFile(filePath));
}

function writeJsonFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), `${JSON.stringify(value, null, 4)}\n`, 'utf8');
}

function writeTextFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), value, 'utf8');
}

function buildSuspendedTarget(planTarget = {}) {
    return {
        match_id: planTarget.match_id,
        schedule_external_id: planTarget.schedule_external_id || null,
        observed_detail_external_id: planTarget.observed_detail_external_id || null,
        source_page_url_base: planTarget.source_page_url_base || null,
        suspension_reason: planTarget.suspension_reason || 'reverse_fixture_contradiction_confirmed',
        previous_mapping_effective_status: planTarget.current_mapping_state || 'accepted_active',
        previous_baseline_effective_status: planTarget.current_baseline_state || 'accepted_active',
        current_mapping_effective_status: 'suspended',
        current_baseline_effective_status: 'suspended',
        current_effective_status: 'suspended',
        current_raw_write_status: 'raw_write_blocked',
        mapping_suspension_execution_performed: true,
        baseline_suspension_execution_performed: true,
        historical_accepted_artifacts_mutated: false,
        accepted_artifact_mutation_performed: false,
        baseline_artifact_mutation_performed: false,
        rollback_execution_performed: false,
        re_acceptance_execution_performed: false,
        re_acceptance_required: true,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        final_db_write_authorization_effective_status: FINAL_AUTHORIZATION_EFFECTIVE_STATUS,
    };
}

function buildBlockedTarget(planTarget = {}) {
    return {
        match_id: planTarget.match_id,
        schedule_external_id: planTarget.schedule_external_id || null,
        observed_detail_external_id: planTarget.observed_detail_external_id || null,
        source_page_url_base: planTarget.source_page_url_base || null,
        current_effective_status: 'blocked_pending_review',
        current_raw_write_status: 'raw_write_blocked',
        blocked_pending_review: true,
        suspension_execution_performed: false,
        re_acceptance_required: false,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        blocker_status: planTarget.required_future_review || 'insufficient_reverse_fixture_evidence',
    };
}

function countWhere(targets = [], predicate) {
    return targets.filter(predicate).length;
}

function validateSuspensionPlan(plan = {}) {
    const errors = [];
    if (plan.proposal_phase !== 'Phase 5.21L2V3AS') {
        errors.push('L2V3AS suspension plan is required');
    }
    if (plan.suspension_planning_status !== 'completed_accepted_mapping_baseline_suspension_planning') {
        errors.push('L2V3AS suspension planning status is not completed');
    }
    if (plan.mapping_suspension_planned_count !== 8 || plan.baseline_suspension_planned_count !== 8) {
        errors.push('expected 8 mapping and 8 baseline planned suspensions');
    }
    if (plan.blocked_pending_review_target_count !== 42) {
        errors.push('expected 42 blocked_pending_review targets');
    }
    if (plan.raw_write_execution_ready !== false || plan.payload_recapture_retry_ready !== false) {
        errors.push('L2V3AS plan must keep raw write and recapture retry blocked');
    }
    return errors;
}

function buildArtifact(context = {}) {
    const validationErrors = validateSuspensionPlan(context.asPlan);
    if (validationErrors.length > 0) {
        throw new Error(`Cannot execute L2V3AT suspension: ${validationErrors.join('; ')}`);
    }

    const suspendedTargets = (context.asPlan.suspension_targets || []).map(buildSuspendedTarget);
    const blockedTargets = (context.asPlan.blocked_pending_review_targets || []).map(buildBlockedTarget);
    const mappingSuspendedCount = countWhere(
        suspendedTargets,
        target => target.current_mapping_effective_status === 'suspended'
    );
    const baselineSuspendedCount = countWhere(
        suspendedTargets,
        target => target.current_baseline_effective_status === 'suspended'
    );

    return {
        artifact_type: 'accepted_mapping_baseline_suspension_result',
        artifact_status: EXECUTION_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        generated_at: context.generatedAt,
        execution_status: EXECUTION_STATUS,
        accepted_mapping_baseline_suspension_execution_status: EXECUTION_STATUS,
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        suspension_execution_performed: true,
        mapping_suspension_execution_performed: true,
        baseline_suspension_execution_performed: true,
        mapping_suspended_count: mappingSuspendedCount,
        baseline_suspended_count: baselineSuspendedCount,
        blocked_pending_review_target_count: blockedTargets.length,
        re_acceptance_required_count: countWhere(suspendedTargets, target => target.re_acceptance_required),
        runner_contract_fix_planning_required: true,
        expanded_review_required: true,
        historical_accepted_artifacts_mutated: false,
        accepted_artifact_mutation_performed: false,
        baseline_artifact_mutation_performed: false,
        accepted_artifacts_rewritten: false,
        baseline_artifacts_rewritten: false,
        rollback_execution_performed: false,
        mapping_rollback_execution_performed: false,
        baseline_rollback_execution_performed: false,
        re_acceptance_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        raw_write_execution_performed: false,
        raw_write_runner_write_mode_used: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        network_request_performed: false,
        recapture_retry_performed: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        full_payload_saved: false,
        full_payload_printed: false,
        full_source_body_saved: false,
        full_source_body_printed: false,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        final_db_write_authorization_historical_artifact_retained: true,
        final_db_write_authorization_effective_status: FINAL_AUTHORIZATION_EFFECTIVE_STATUS,
        final_db_write_authorization_usable_for_raw_write: false,
        raw_write_reauthorization_required_after_re_acceptance: true,
        current_effective_governance_status: 'accepted_mapping_baseline_suspended_raw_write_blocked',
        suspended_targets: suspendedTargets,
        blocked_pending_review_targets: blockedTargets,
        recommended_next_step: NEXT_STEP_RE_ACCEPTANCE_PREREQ,
        next_required_step: NEXT_REQUIRED_STEP_RE_ACCEPTANCE_PREREQ,
    };
}

function formatSuspendedLine(target = {}) {
    return `- ${target.match_id}: requested=${target.schedule_external_id || 'unknown'} observed=${
        target.observed_detail_external_id || 'unknown'
    } mapping=${target.previous_mapping_effective_status}->${target.current_mapping_effective_status} baseline=${
        target.previous_baseline_effective_status
    }->${target.current_baseline_effective_status} raw_write=${target.current_raw_write_status}`;
}

function buildReport(artifact = {}) {
    const suspendedLines = artifact.suspended_targets.map(formatSuspendedLine).join('\n');

    return `# Data Entrypoint Governance - Phase 5.21 L2V3AT

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- execution_status=${artifact.execution_status}
- suspension_execution_performed=true
- mapping_suspension_execution_performed=true
- baseline_suspension_execution_performed=true
- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- recapture_retry_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- raw_write_execution_performed=false
- raw_write_runner_write_mode_used=false
- rollback_execution_performed=false
- re_acceptance_execution_performed=false
- historical_accepted_artifacts_mutated=false
- full_payload_saved=false
- full_payload_printed=false

## Counts

- mapping_suspended_count=${artifact.mapping_suspended_count}
- baseline_suspended_count=${artifact.baseline_suspended_count}
- blocked_pending_review_target_count=${artifact.blocked_pending_review_target_count}
- re_acceptance_required_count=${artifact.re_acceptance_required_count}
- runner_contract_fix_planning_required=${artifact.runner_contract_fix_planning_required}
- expanded_review_required=${artifact.expanded_review_required}
- raw_write_execution_ready=${artifact.raw_write_execution_ready}
- payload_recapture_retry_ready=${artifact.payload_recapture_retry_ready}

## Suspension Result

${suspendedLines || '- none'}

## Remaining Targets

- blocked_pending_review_target_count=${artifact.blocked_pending_review_target_count}
- status=blocked_pending_review / insufficient_reverse_fixture_evidence
- these targets are not clean, not accepted safe, and not raw-write eligible

## Final Authorization Status

- final_db_write_authorization_historical_artifact_retained=true
- final_db_write_authorization_effective_status=${artifact.final_db_write_authorization_effective_status}
- final_db_write_authorization_usable_for_raw_write=false
- raw_write_reauthorization_required_after_re_acceptance=true

## Next Step

- recommended_next_step=${artifact.recommended_next_step}
- next_required_step=${artifact.next_required_step}

## Explicit Non-Execution

- no live fetch
- no detail fetch
- no network request
- no recapture retry
- no DB writes
- no raw_match_data inserts
- no matches writes
- no matches.external_id changes
- no raw write execution
- no rollback
- no re-acceptance
- no historical accepted artifact mutation
- no full payload printed or saved
`;
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3at_execution_status: artifact.execution_status,
        phase_5_21_l2v3at_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3at_report_path: REPORT_OUTPUT_PATH,
        accepted_mapping_baseline_suspension_execution_status:
            artifact.accepted_mapping_baseline_suspension_execution_status,
        suspension_execution_performed: true,
        mapping_suspension_execution_performed: true,
        baseline_suspension_execution_performed: true,
        mapping_suspended_count: artifact.mapping_suspended_count,
        baseline_suspended_count: artifact.baseline_suspended_count,
        blocked_pending_review_target_count: artifact.blocked_pending_review_target_count,
        re_acceptance_required_count: artifact.re_acceptance_required_count,
        runner_contract_fix_planning_required: true,
        expanded_review_required: true,
        historical_accepted_artifacts_mutated: false,
        rollback_execution_performed: false,
        re_acceptance_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        raw_write_execution_performed: false,
        raw_write_execution_ready: false,
        final_db_write_authorization_effective_status: FINAL_AUTHORIZATION_EFFECTIVE_STATUS,
        final_db_write_authorization_usable_for_raw_write: false,
        payload_recapture_retry_ready: false,
        current_effective_governance_status: artifact.current_effective_governance_status,
        current_effective_suspended_mapping_match_ids: artifact.suspended_targets.map(target => target.match_id),
        current_effective_blocked_pending_review_target_count: artifact.blocked_pending_review_target_count,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function loadContext(overrides = {}) {
    const readJson = overrides.readJsonFile || readJsonFile;

    return {
        generatedAt: overrides.generatedAt || new Date().toISOString(),
        asPlan: overrides.asPlan || readJson(AS_PLAN_PATH),
        manifest: overrides.manifest || readJson(PROPOSAL_MANIFEST_PATH),
    };
}

function runAcceptedMappingBaselineSuspensionExecute(options = {}, overrides = {}) {
    const context = loadContext(overrides);
    const artifact = buildArtifact(context);
    const report = buildReport(artifact);
    const updatedManifest = updateManifestMetadata(context.manifest, artifact);
    const writeFiles = options.writeFiles !== false;

    if (writeFiles) {
        const writeJson = overrides.writeJsonFile || writeJsonFile;
        const writeText = overrides.writeTextFile || writeTextFile;
        writeJson(ARTIFACT_OUTPUT_PATH, artifact);
        writeText(REPORT_OUTPUT_PATH, report);
        writeJson(PROPOSAL_MANIFEST_PATH, updatedManifest);
    }

    return {
        ok: true,
        artifact,
        report,
        updated_manifest: updatedManifest,
    };
}

async function runCli() {
    const result = runAcceptedMappingBaselineSuspensionExecute();
    process.stdout.write(
        `${JSON.stringify(
            {
                ok: result.ok,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_OUTPUT_PATH,
                execution_status: result.artifact.execution_status,
                mapping_suspended_count: result.artifact.mapping_suspended_count,
                baseline_suspended_count: result.artifact.baseline_suspended_count,
                blocked_pending_review_target_count: result.artifact.blocked_pending_review_target_count,
                re_acceptance_required_count: result.artifact.re_acceptance_required_count,
                raw_write_execution_ready: false,
                final_db_write_authorization_effective_status:
                    result.artifact.final_db_write_authorization_effective_status,
                recommended_next_step: result.artifact.recommended_next_step,
            },
            null,
            2
        )}\n`
    );
}

module.exports = {
    PHASE,
    PHASE_NAME,
    EXECUTION_STATUS,
    FINAL_AUTHORIZATION_EFFECTIVE_STATUS,
    AS_PLAN_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    PROPOSAL_MANIFEST_PATH,
    buildArtifact,
    buildReport,
    buildSuspendedTarget,
    buildBlockedTarget,
    loadContext,
    runAcceptedMappingBaselineSuspensionExecute,
    runCli,
    updateManifestMetadata,
    validateSuspensionPlan,
};

if (require.main === module) {
    runCli().catch(error => {
        process.stderr.write(`${error.stack || error.message}\n`);
        process.exitCode = 1;
    });
}
