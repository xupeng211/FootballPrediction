#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines -- L2V3AS keeps suspension planning evidence explicit for governance review. */

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AS';
const PHASE_NAME = 'accepted_mapping_baseline_suspension_planning';
const PLANNING_STATUS = 'completed_accepted_mapping_baseline_suspension_planning';
const NEXT_STEP_SUSPENSION_EXECUTION = 'Phase 5.21L2V3AT: accepted mapping and baseline suspension execution';
const NEXT_REQUIRED_STEP_SUSPENSION_EXECUTION = 'accepted_mapping_and_baseline_suspension_execution';
const PROPOSAL_MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const AR_REVIEW_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_contradiction_review_result.phase521l2v3ar.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_suspension_plan.phase521l2v3as.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AS.md';

const SUSPENSION_STATE_MODEL = Object.freeze([
    'accepted_active',
    'suspension_required',
    'suspension_planned',
    'suspended',
    're_acceptance_required',
    'blocked_pending_evidence',
    'superseded',
    'rejected',
]);

const REVIEWED_INPUTS = Object.freeze([
    ['ar_contradiction_review_result', AR_REVIEW_RESULT_PATH],
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

function isConfirmedSuspensionCandidate(target = {}) {
    return (
        target.contradiction_review_status === 'contradiction_confirmed' &&
        target.accepted_mapping_contradiction_confirmed === true &&
        target.baseline_acceptance_contradiction_confirmed === true &&
        target.mapping_suspension_required === true &&
        target.baseline_suspension_required === true
    );
}

function buildSuspensionTarget(target = {}) {
    const confirmed = isConfirmedSuspensionCandidate(target);

    if (!confirmed) {
        return {
            match_id: target.match_id,
            schedule_external_id: target.schedule_external_id || null,
            observed_detail_external_id: target.observed_detail_external_id || null,
            source_page_url_base: target.source_page_url_base || null,
            suspension_planning_status: 'blocked_pending_evidence',
            blocked_pending_review: true,
            mapping_suspension_candidate: false,
            baseline_suspension_candidate: false,
            mapping_suspension_planned: false,
            baseline_suspension_planned: false,
            re_acceptance_required: false,
            current_mapping_state: 'accepted_active',
            planned_mapping_state: 'blocked_pending_evidence',
            current_baseline_state: 'accepted_active',
            planned_baseline_state: 'blocked_pending_evidence',
            raw_write_eligibility_state: 'blocked_pending_reverse_fixture_evidence',
            required_future_review: 'expanded_reverse_fixture_evidence_review_required',
            suspension_execution_performed: false,
            accepted_artifact_mutation_performed: false,
        };
    }

    return {
        match_id: target.match_id,
        schedule_external_id: target.schedule_external_id || null,
        observed_detail_external_id: target.observed_detail_external_id || null,
        source_page_url_base: target.source_page_url_base || null,
        suspension_planning_status: 'suspension_planned',
        suspension_reason: 'reverse_fixture_contradiction_confirmed',
        blocked_pending_review: false,
        mapping_suspension_candidate: true,
        baseline_suspension_candidate: true,
        mapping_suspension_planned: true,
        baseline_suspension_planned: true,
        re_acceptance_required: true,
        current_mapping_state: 'accepted_active',
        planned_mapping_state: 'suspension_planned',
        future_mapping_state_after_execution: 'suspended',
        current_baseline_state: 'accepted_active',
        planned_baseline_state: 'suspension_planned',
        future_baseline_state_after_execution: 'suspended',
        raw_write_eligibility_state: 'blocked_by_confirmed_identity_mismatch',
        final_db_write_authorization_dependency_action:
            'future_authorization_dependency_must_be_replanned_if_it_assumes_all_50_targets_accepted_clean',
        re_acceptance_prerequisite_status: 're_acceptance_required_after_identity_and_runner_contract_resolution',
        suspension_execution_performed: false,
        accepted_artifact_mutation_performed: false,
    };
}

function countWhere(targets = [], predicate) {
    return targets.filter(predicate).length;
}

function buildCounts(plannedTargets = []) {
    return {
        mappingSuspensionCandidateCount: countWhere(plannedTargets, target => target.mapping_suspension_candidate),
        baselineSuspensionCandidateCount: countWhere(plannedTargets, target => target.baseline_suspension_candidate),
        blockedPendingReviewTargetCount: countWhere(plannedTargets, target => target.blocked_pending_review),
        mappingSuspensionPlannedCount: countWhere(plannedTargets, target => target.mapping_suspension_planned),
        baselineSuspensionPlannedCount: countWhere(plannedTargets, target => target.baseline_suspension_planned),
        reAcceptanceRequiredCount: countWhere(plannedTargets, target => target.re_acceptance_required),
    };
}

function buildArtifact(context = {}) {
    const reviewTargets = Array.isArray(context.arResult.review_targets) ? context.arResult.review_targets : [];
    const plannedTargets = reviewTargets.map(buildSuspensionTarget);
    const counts = buildCounts(plannedTargets);
    const suspensionTargets = plannedTargets.filter(target => target.mapping_suspension_planned);
    const blockedTargets = plannedTargets.filter(target => target.blocked_pending_review);

    return {
        artifact_type: 'accepted_mapping_baseline_suspension_plan',
        artifact_status: PLANNING_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        generated_at: context.generatedAt,
        suspension_planning_status: PLANNING_STATUS,
        accepted_mapping_baseline_suspension_planning_status: PLANNING_STATUS,
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        suspension_state_model: SUSPENSION_STATE_MODEL,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        network_request_performed: false,
        recapture_retry_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        raw_write_execution_performed: false,
        raw_write_runner_write_mode_used: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        mapping_suspension_execution_performed: false,
        baseline_suspension_execution_performed: false,
        suspension_execution_performed: false,
        rollback_execution_performed: false,
        mapping_rollback_execution_performed: false,
        baseline_rollback_execution_performed: false,
        re_acceptance_execution_performed: false,
        accepted_artifact_mutation_performed: false,
        baseline_artifact_mutation_performed: false,
        accepted_artifacts_rewritten: false,
        baseline_artifacts_rewritten: false,
        full_payload_saved: false,
        full_payload_printed: false,
        full_source_body_saved: false,
        full_source_body_printed: false,
        mapping_suspension_candidate_count: counts.mappingSuspensionCandidateCount,
        baseline_suspension_candidate_count: counts.baselineSuspensionCandidateCount,
        blocked_pending_review_target_count: counts.blockedPendingReviewTargetCount,
        mapping_suspension_planned_count: counts.mappingSuspensionPlannedCount,
        baseline_suspension_planned_count: counts.baselineSuspensionPlannedCount,
        re_acceptance_required_count: counts.reAcceptanceRequiredCount,
        runner_contract_fix_planning_required: true,
        expanded_review_required: true,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        what_to_suspend: [
            'identity_mapping_acceptance_for_8_confirmed_contradictions',
            'baseline_acceptance_for_8_confirmed_contradictions',
            'raw_write_eligibility_derived_from_confirmed_bad_acceptances',
            'final_db_write_authorization_dependency_if_it_assumes_all_50_targets_accepted_clean',
        ],
        what_not_to_suspend_in_this_phase: [
            'do_not_modify_l2v3ae_identity_mapping_acceptance_result',
            'do_not_modify_l2v3ag_baseline_acceptance_result',
            'do_not_modify_accepted_by_or_accepted_at',
            'do_not_write_database',
            'do_not_delete_history',
            'do_not_fabricate_corrected_mapping',
        ],
        re_acceptance_prerequisites: [
            'runner_input_contract_fixed_or_clarified',
            'reverse_fixture_evidence_resolved',
            'source_url_and_detail_identity_evidence_sufficient',
            'hash_mismatch_reclassified_after_identity_resolution',
            'no_write_recapture_replanned_and_reauthorized_if_needed',
            'human_review_required',
            'fresh_raw_write_authorization_chain_required_after_re_acceptance',
        ],
        suspension_and_runner_contract_ordering:
            'plan suspension first for confirmed bad acceptances; plan runner contract fix before any future recapture or re-acceptance',
        suspension_targets: suspensionTargets,
        blocked_pending_review_targets: blockedTargets,
        all_planning_targets: plannedTargets,
        recommended_next_step: NEXT_STEP_SUSPENSION_EXECUTION,
        next_required_step: NEXT_REQUIRED_STEP_SUSPENSION_EXECUTION,
    };
}

function formatSuspensionLine(target = {}) {
    return `- ${target.match_id}: requested=${target.schedule_external_id || 'unknown'} observed=${
        target.observed_detail_external_id || 'unknown'
    } mapping=${target.current_mapping_state}->${target.planned_mapping_state} baseline=${
        target.current_baseline_state
    }->${target.planned_baseline_state} re_acceptance_required=${target.re_acceptance_required}`;
}

function buildReport(artifact = {}) {
    const suspensionLines = artifact.suspension_targets.map(formatSuspensionLine).join('\n');

    return `# Data Entrypoint Governance - Phase 5.21 L2V3AS

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- suspension_planning_status=${artifact.suspension_planning_status}
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
- mapping_suspension_execution_performed=false
- baseline_suspension_execution_performed=false
- rollback_execution_performed=false
- re_acceptance_execution_performed=false
- accepted_artifact_mutation_performed=false
- baseline_artifact_mutation_performed=false

## Counts

- reviewed_input_artifact_count=${artifact.reviewed_input_artifact_count}
- mapping_suspension_candidate_count=${artifact.mapping_suspension_candidate_count}
- baseline_suspension_candidate_count=${artifact.baseline_suspension_candidate_count}
- blocked_pending_review_target_count=${artifact.blocked_pending_review_target_count}
- mapping_suspension_planned_count=${artifact.mapping_suspension_planned_count}
- baseline_suspension_planned_count=${artifact.baseline_suspension_planned_count}
- re_acceptance_required_count=${artifact.re_acceptance_required_count}
- runner_contract_fix_planning_required=${artifact.runner_contract_fix_planning_required}
- expanded_review_required=${artifact.expanded_review_required}
- raw_write_execution_ready=${artifact.raw_write_execution_ready}
- payload_recapture_retry_ready=${artifact.payload_recapture_retry_ready}

## Suspension State Model

- accepted_active
- suspension_required
- suspension_planned
- suspended
- re_acceptance_required
- blocked_pending_evidence
- superseded
- rejected

## Planned Suspension Targets

${suspensionLines || '- none'}

## Remaining Targets

- blocked_pending_review_target_count=${artifact.blocked_pending_review_target_count}
- status=blocked_pending_review / insufficient_reverse_fixture_evidence
- these targets are not accepted clean and are not raw-write ready

## Re-Acceptance And Runner Contract Follow-Up

- re_acceptance_prerequisites=${artifact.re_acceptance_prerequisites.join(', ')}
- suspension_and_runner_contract_ordering=${artifact.suspension_and_runner_contract_ordering}
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
- no mapping suspension execution
- no baseline suspension execution
- no rollback
- no accepted artifact mutation
- no full payload printed or saved
`;
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3as_planning_status: artifact.suspension_planning_status,
        phase_5_21_l2v3as_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3as_report_path: REPORT_OUTPUT_PATH,
        accepted_mapping_baseline_suspension_planning_status:
            artifact.accepted_mapping_baseline_suspension_planning_status,
        mapping_suspension_candidate_count: artifact.mapping_suspension_candidate_count,
        baseline_suspension_candidate_count: artifact.baseline_suspension_candidate_count,
        blocked_pending_review_target_count: artifact.blocked_pending_review_target_count,
        mapping_suspension_planned_count: artifact.mapping_suspension_planned_count,
        baseline_suspension_planned_count: artifact.baseline_suspension_planned_count,
        re_acceptance_required_count: artifact.re_acceptance_required_count,
        runner_contract_fix_planning_required: artifact.runner_contract_fix_planning_required,
        expanded_review_required: artifact.expanded_review_required,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        mapping_suspension_execution_performed: false,
        baseline_suspension_execution_performed: false,
        rollback_execution_performed: false,
        re_acceptance_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function loadContext(overrides = {}) {
    const readJson = overrides.readJsonFile || readJsonFile;

    return {
        generatedAt: overrides.generatedAt || new Date().toISOString(),
        arResult: overrides.arResult || readJson(AR_REVIEW_RESULT_PATH),
        manifest: overrides.manifest || readJson(PROPOSAL_MANIFEST_PATH),
    };
}

function runAcceptedMappingBaselineSuspensionPlan(options = {}, overrides = {}) {
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
    const result = runAcceptedMappingBaselineSuspensionPlan();
    process.stdout.write(
        `${JSON.stringify(
            {
                ok: result.ok,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_OUTPUT_PATH,
                suspension_planning_status: result.artifact.suspension_planning_status,
                mapping_suspension_candidate_count: result.artifact.mapping_suspension_candidate_count,
                baseline_suspension_candidate_count: result.artifact.baseline_suspension_candidate_count,
                blocked_pending_review_target_count: result.artifact.blocked_pending_review_target_count,
                mapping_suspension_planned_count: result.artifact.mapping_suspension_planned_count,
                baseline_suspension_planned_count: result.artifact.baseline_suspension_planned_count,
                re_acceptance_required_count: result.artifact.re_acceptance_required_count,
                raw_write_execution_ready: false,
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
    PLANNING_STATUS,
    AR_REVIEW_RESULT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    PROPOSAL_MANIFEST_PATH,
    SUSPENSION_STATE_MODEL,
    buildArtifact,
    buildReport,
    buildSuspensionTarget,
    loadContext,
    runAcceptedMappingBaselineSuspensionPlan,
    runCli,
    updateManifestMetadata,
};

if (require.main === module) {
    runCli().catch(error => {
        process.stderr.write(`${error.stack || error.message}\n`);
        process.exitCode = 1;
    });
}
