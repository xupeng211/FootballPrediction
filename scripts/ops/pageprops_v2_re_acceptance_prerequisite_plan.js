#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines -- L2V3AU keeps prerequisite governance evidence explicit for review. */

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AU';
const PHASE_NAME = 're_acceptance_prerequisite_planning';
const PLANNING_STATUS = 'completed_re_acceptance_prerequisite_planning';
const NEXT_STEP_RUNNER_CONTRACT_FIX = 'Phase 5.21L2V3AV: recapture runner identity input contract fix planning';
const NEXT_REQUIRED_STEP_RUNNER_CONTRACT_FIX = 'recapture_runner_identity_input_contract_fix_planning';
const FINAL_AUTHORIZATION_EFFECTIVE_STATUS = 'blocked_or_superseded';
const PROPOSAL_MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const AT_SUSPENSION_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_suspension_result.phase521l2v3at.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.re_acceptance_prerequisite_plan.phase521l2v3au.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AU.md';

const REVIEWED_INPUTS = Object.freeze([
    ['at_suspension_result', AT_SUSPENSION_RESULT_PATH],
    ['at_suspension_report', 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AT.md'],
    [
        'as_suspension_plan',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_suspension_plan.phase521l2v3as.json',
    ],
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

const MAPPING_RE_ACCEPTANCE_PREREQUISITES = Object.freeze([
    {
        id: 'reverse_fixture_evidence_resolved',
        required: true,
        status: 'required_before_mapping_re_acceptance',
        description: 'Reverse-fixture evidence must be resolved for every suspended mapping.',
    },
    {
        id: 'schedule_detail_identity_contract_clarified',
        required: true,
        status: 'required_before_mapping_re_acceptance',
        description: 'Schedule-side identity and detail-page identity contract must be explicit.',
    },
    {
        id: 'accepted_detail_identity_supported_by_sufficient_evidence',
        required: true,
        status: 'required_before_mapping_re_acceptance',
        description: 'Accepted detail identity must be backed by sufficient source evidence.',
    },
    {
        id: 'page_url_base_slug_fragment_insufficient',
        required: true,
        status: 'required_before_mapping_re_acceptance',
        description: 'Page URL base, slug, or fragment alone is not sufficient identity evidence.',
    },
    {
        id: 'source_url_detail_identity_date_team_status_consistency_required',
        required: true,
        status: 'required_before_mapping_re_acceptance',
        description: 'Source URL, detail identity, date, team, and status evidence must be consistent.',
    },
    {
        id: 'no_unresolved_identity_mismatch',
        required: true,
        status: 'required_before_mapping_re_acceptance',
        description: 'No unresolved identity_mismatch can remain on a re-accepted mapping.',
    },
    {
        id: 'no_unresolved_reverse_fixture_detected',
        required: true,
        status: 'required_before_mapping_re_acceptance',
        description: 'No unresolved reverse_fixture_detected state can remain on a re-accepted mapping.',
    },
    {
        id: 'human_review_required',
        required: true,
        status: 'required_before_mapping_re_acceptance',
        description: 'Human review is required before any suspended mapping can be re-accepted.',
    },
]);

const BASELINE_RE_ACCEPTANCE_PREREQUISITES = Object.freeze([
    {
        id: 'identity_mismatch_resolved_first',
        required: true,
        status: 'required_before_baseline_re_acceptance',
        description: 'Identity mismatch must be resolved before any baseline hash can be considered.',
    },
    {
        id: 'hash_mismatch_secondary_until_identity_corrected',
        required: true,
        status: 'required_before_baseline_re_acceptance',
        description: 'Hash mismatch remains secondary while identity is unresolved.',
    },
    {
        id: 'baseline_hash_update_cannot_bypass_identity_mismatch',
        required: true,
        status: 'required_before_baseline_re_acceptance',
        description: 'A baseline hash must not be updated to bypass an identity mismatch.',
    },
    {
        id: 'baseline_evidence_binds_to_correct_accepted_identity',
        required: true,
        status: 'required_before_baseline_re_acceptance',
        description: 'Baseline evidence must bind to the correct accepted identity.',
    },
    {
        id: 'baseline_re_acceptance_requires_separate_review',
        required: true,
        status: 'required_before_baseline_re_acceptance',
        description: 'Baseline re-acceptance requires a separate review from mapping re-acceptance.',
    },
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

function countWhere(targets = [], predicate) {
    return targets.filter(predicate).length;
}

function validateSuspensionResult(result = {}) {
    const errors = [];
    if (result.proposal_phase !== 'Phase 5.21L2V3AT') {
        errors.push('L2V3AT suspension result is required');
    }
    if (result.execution_status !== 'completed_accepted_mapping_baseline_suspension_execution') {
        errors.push('L2V3AT suspension execution must be completed');
    }
    if (result.suspension_execution_performed !== true) {
        errors.push('L2V3AT suspension execution must be performed before AU planning');
    }
    if (result.mapping_suspended_count !== 8 || result.baseline_suspended_count !== 8) {
        errors.push('expected 8 suspended mappings and 8 suspended baselines');
    }
    if (result.blocked_pending_review_target_count !== 42) {
        errors.push('expected 42 blocked_pending_review targets');
    }
    if (result.final_db_write_authorization_effective_status !== FINAL_AUTHORIZATION_EFFECTIVE_STATUS) {
        errors.push('final DB-write authorization must be blocked or superseded');
    }
    if (result.raw_write_execution_ready !== false || result.payload_recapture_retry_ready !== false) {
        errors.push('raw write execution and payload recapture retry must remain blocked');
    }
    if (
        result.re_acceptance_execution_performed !== false ||
        result.rollback_execution_performed !== false ||
        result.db_write_performed !== false ||
        result.raw_match_data_insert_performed !== false ||
        result.raw_write_execution_performed !== false
    ) {
        errors.push('L2V3AT result contains a forbidden execution flag');
    }
    return errors;
}

function buildSuspendedPrerequisiteTarget(target = {}) {
    return {
        match_id: target.match_id,
        schedule_external_id: target.schedule_external_id || null,
        observed_detail_external_id: target.observed_detail_external_id || null,
        source_page_url_base: target.source_page_url_base || null,
        current_mapping_effective_status: target.current_mapping_effective_status || 'suspended',
        current_baseline_effective_status: target.current_baseline_effective_status || 'suspended',
        current_raw_write_status: 'raw_write_blocked',
        mapping_re_acceptance_prerequisite_status: 'prerequisites_required',
        baseline_re_acceptance_prerequisite_status: 'prerequisites_required',
        identity_mismatch_resolution_required: true,
        reverse_fixture_resolution_required: true,
        human_review_required: true,
        baseline_hash_update_allowed_before_identity_resolution: false,
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
    };
}

function buildBlockedReviewTarget(target = {}) {
    return {
        match_id: target.match_id,
        schedule_external_id: target.schedule_external_id || null,
        observed_detail_external_id: target.observed_detail_external_id || null,
        source_page_url_base: target.source_page_url_base || null,
        current_effective_status: 'blocked_pending_review',
        current_raw_write_status: 'raw_write_blocked',
        expanded_review_required: true,
        clean_acceptance_inferred: false,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
    };
}

function buildArtifact(context = {}) {
    const validationErrors = validateSuspensionResult(context.atResult);
    if (validationErrors.length > 0) {
        throw new Error(`Cannot plan L2V3AU prerequisites: ${validationErrors.join('; ')}`);
    }

    const suspendedTargets = (context.atResult.suspended_targets || []).map(buildSuspendedPrerequisiteTarget);
    const blockedTargets = (context.atResult.blocked_pending_review_targets || []).map(buildBlockedReviewTarget);

    return {
        artifact_type: 're_acceptance_prerequisite_plan',
        artifact_status: PLANNING_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        generated_at: context.generatedAt,
        re_acceptance_prerequisite_planning_status: PLANNING_STATUS,
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        suspended_mapping_count: countWhere(
            suspendedTargets,
            target => target.current_mapping_effective_status === 'suspended'
        ),
        suspended_baseline_count: countWhere(
            suspendedTargets,
            target => target.current_baseline_effective_status === 'suspended'
        ),
        blocked_pending_review_target_count: blockedTargets.length,
        re_acceptance_required_count: suspendedTargets.length,
        mapping_re_acceptance_prerequisite_count: MAPPING_RE_ACCEPTANCE_PREREQUISITES.length,
        baseline_re_acceptance_prerequisite_count: BASELINE_RE_ACCEPTANCE_PREREQUISITES.length,
        mapping_re_acceptance_prerequisites: MAPPING_RE_ACCEPTANCE_PREREQUISITES,
        baseline_re_acceptance_prerequisites: BASELINE_RE_ACCEPTANCE_PREREQUISITES,
        runner_contract_fix_prerequisite_required: true,
        runner_contract_prerequisite_status: 'fix_planning_required_before_recapture_retry',
        recapture_runner_must_use_accepted_mapping_source_url_detail_identity: true,
        schedule_side_route_alone_allowed_for_recapture_retry: false,
        runner_contract_fix_implementation_performed: false,
        expanded_review_prerequisite_required: true,
        expanded_review_target_count: blockedTargets.length,
        blocked_targets_clean_acceptance_inferred: false,
        fresh_final_authorization_required: true,
        prior_final_db_write_authorization_effective_status: FINAL_AUTHORIZATION_EFFECTIVE_STATUS,
        direct_path_from_suspended_state_to_raw_write_allowed: false,
        payload_recapture_retry_ready: false,
        raw_write_execution_ready: false,
        re_acceptance_execution_performed: false,
        mapping_re_acceptance_execution_performed: false,
        baseline_re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
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
        suspended_targets_requiring_prerequisites: suspendedTargets,
        blocked_pending_review_targets: blockedTargets,
        recommended_next_step: NEXT_STEP_RUNNER_CONTRACT_FIX,
        next_required_step: NEXT_REQUIRED_STEP_RUNNER_CONTRACT_FIX,
    };
}

function formatPrerequisiteLine(item = {}) {
    return `- ${item.id}: ${item.status}`;
}

function formatTargetLine(target = {}) {
    return `- ${target.match_id}: mapping=${target.current_mapping_effective_status} baseline=${target.current_baseline_effective_status} raw_write=${target.current_raw_write_status}`;
}

function buildReport(artifact = {}) {
    const mappingPrerequisites = artifact.mapping_re_acceptance_prerequisites.map(formatPrerequisiteLine).join('\n');
    const baselinePrerequisites = artifact.baseline_re_acceptance_prerequisites.map(formatPrerequisiteLine).join('\n');
    const suspendedLines = artifact.suspended_targets_requiring_prerequisites.map(formatTargetLine).join('\n');

    return `# Data Entrypoint Governance - Phase 5.21 L2V3AU

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- re_acceptance_prerequisite_planning_status=${artifact.re_acceptance_prerequisite_planning_status}
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
- suspension_reversal_performed=false
- re_acceptance_execution_performed=false
- rollback_execution_performed=false
- runner_contract_fix_implementation_performed=false
- full_payload_saved=false
- full_payload_printed=false

## Counts

- suspended_mapping_count=${artifact.suspended_mapping_count}
- suspended_baseline_count=${artifact.suspended_baseline_count}
- blocked_pending_review_target_count=${artifact.blocked_pending_review_target_count}
- mapping_re_acceptance_prerequisite_count=${artifact.mapping_re_acceptance_prerequisite_count}
- baseline_re_acceptance_prerequisite_count=${artifact.baseline_re_acceptance_prerequisite_count}
- runner_contract_fix_prerequisite_required=${artifact.runner_contract_fix_prerequisite_required}
- expanded_review_prerequisite_required=${artifact.expanded_review_prerequisite_required}
- fresh_final_authorization_required=${artifact.fresh_final_authorization_required}
- raw_write_execution_ready=${artifact.raw_write_execution_ready}
- payload_recapture_retry_ready=${artifact.payload_recapture_retry_ready}

## Mapping Re-Acceptance Prerequisites

${mappingPrerequisites}

## Baseline Re-Acceptance Prerequisites

${baselinePrerequisites}

## Suspended Targets Requiring Prerequisites

${suspendedLines || '- none'}

## Runner Contract / Expanded Review / Authorization

- runner_contract_prerequisite_status=${artifact.runner_contract_prerequisite_status}
- recapture_runner_must_use_accepted_mapping_source_url_detail_identity=true
- schedule_side_route_alone_allowed_for_recapture_retry=false
- expanded_review_target_count=${artifact.expanded_review_target_count}
- blocked_targets_clean_acceptance_inferred=false
- prior_final_db_write_authorization_effective_status=${artifact.prior_final_db_write_authorization_effective_status}
- direct_path_from_suspended_state_to_raw_write_allowed=false

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
- no suspension reversal
- no re-acceptance execution
- no rollback
- no runner contract implementation
- no full payload printed or saved
`;
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3au_planning_status: artifact.re_acceptance_prerequisite_planning_status,
        phase_5_21_l2v3au_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3au_report_path: REPORT_OUTPUT_PATH,
        re_acceptance_prerequisite_planning_status: artifact.re_acceptance_prerequisite_planning_status,
        suspended_mapping_count: artifact.suspended_mapping_count,
        suspended_baseline_count: artifact.suspended_baseline_count,
        blocked_pending_review_target_count: artifact.blocked_pending_review_target_count,
        mapping_re_acceptance_prerequisite_count: artifact.mapping_re_acceptance_prerequisite_count,
        baseline_re_acceptance_prerequisite_count: artifact.baseline_re_acceptance_prerequisite_count,
        runner_contract_fix_prerequisite_required: true,
        expanded_review_prerequisite_required: true,
        fresh_final_authorization_required: true,
        payload_recapture_retry_ready: false,
        raw_write_execution_ready: false,
        re_acceptance_execution_performed: false,
        mapping_re_acceptance_execution_performed: false,
        baseline_re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        raw_write_execution_performed: false,
        runner_contract_fix_implementation_performed: false,
        current_effective_governance_status: 'accepted_mapping_baseline_suspended_raw_write_blocked',
        prior_final_db_write_authorization_effective_status: FINAL_AUTHORIZATION_EFFECTIVE_STATUS,
        direct_path_from_suspended_state_to_raw_write_allowed: false,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function loadContext(overrides = {}) {
    const readJson = overrides.readJsonFile || readJsonFile;

    return {
        generatedAt: overrides.generatedAt || new Date().toISOString(),
        atResult: overrides.atResult || readJson(AT_SUSPENSION_RESULT_PATH),
        manifest: overrides.manifest || readJson(PROPOSAL_MANIFEST_PATH),
    };
}

function runReAcceptancePrerequisitePlan(options = {}, overrides = {}) {
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
    const result = runReAcceptancePrerequisitePlan();
    process.stdout.write(
        `${JSON.stringify(
            {
                ok: result.ok,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_OUTPUT_PATH,
                planning_status: result.artifact.re_acceptance_prerequisite_planning_status,
                suspended_mapping_count: result.artifact.suspended_mapping_count,
                suspended_baseline_count: result.artifact.suspended_baseline_count,
                blocked_pending_review_target_count: result.artifact.blocked_pending_review_target_count,
                mapping_re_acceptance_prerequisite_count: result.artifact.mapping_re_acceptance_prerequisite_count,
                baseline_re_acceptance_prerequisite_count: result.artifact.baseline_re_acceptance_prerequisite_count,
                runner_contract_fix_prerequisite_required: result.artifact.runner_contract_fix_prerequisite_required,
                fresh_final_authorization_required: result.artifact.fresh_final_authorization_required,
                raw_write_execution_ready: false,
                payload_recapture_retry_ready: false,
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
    NEXT_STEP_RUNNER_CONTRACT_FIX,
    AT_SUSPENSION_RESULT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    PROPOSAL_MANIFEST_PATH,
    BASELINE_RE_ACCEPTANCE_PREREQUISITES,
    MAPPING_RE_ACCEPTANCE_PREREQUISITES,
    buildArtifact,
    buildBlockedReviewTarget,
    buildReport,
    buildSuspendedPrerequisiteTarget,
    loadContext,
    runCli,
    runReAcceptancePrerequisitePlan,
    updateManifestMetadata,
    validateSuspensionResult,
};

if (require.main === module) {
    runCli().catch(error => {
        process.stderr.write(`${error.stack || error.message}\n`);
        process.exitCode = 1;
    });
}
