#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines -- L2V3AR execution keeps contradiction evidence explicit for governance review. */

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AR';
const PHASE_NAME = 'accepted_mapping_baseline_contradiction_review_execution';
const EXECUTION_STATUS = 'completed_accepted_mapping_baseline_contradiction_review_execution';
const NEXT_STEP_SUSPENSION_PLANNING = 'Phase 5.21L2V3AS: accepted mapping and baseline suspension planning';
const NEXT_STEP_RUNNER_FIX = 'Phase 5.21L2V3AS: recapture runner identity input contract fix planning';
const NEXT_STEP_EXPANDED_REVIEW = 'Phase 5.21L2V3AS: expanded accepted mapping/baseline contradiction review planning';
const NEXT_STEP_CONTINUED_REVIEW = 'Phase 5.21L2V3AS: continued contradiction review planning';
const NEXT_REQUIRED_STEP_SUSPENSION_PLANNING = 'accepted_mapping_and_baseline_suspension_planning';
const NEXT_REQUIRED_STEP_RUNNER_FIX = 'recapture_runner_identity_input_contract_fix_planning';
const NEXT_REQUIRED_STEP_EXPANDED_REVIEW = 'expanded_accepted_mapping_baseline_contradiction_review_planning';
const NEXT_REQUIRED_STEP_CONTINUED_REVIEW = 'continued_contradiction_review_planning';
const PROPOSAL_MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const AQ_PLAN_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_contradiction_review_plan.phase521l2v3aq.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_contradiction_review_result.phase521l2v3ar.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AR.md';

const REVIEW_STATUS_CATALOG = Object.freeze([
    'contradiction_confirmed',
    'contradiction_not_confirmed',
    'contradiction_blocked_pending_evidence',
    'mapping_suspension_required',
    'baseline_suspension_required',
    're_acceptance_required',
    'runner_contract_fix_required',
    'expanded_review_required',
]);

const REVIEWED_INPUTS = Object.freeze([
    ['aq_contradiction_review_plan', AQ_PLAN_PATH],
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
    ['fotmob_raw_detail_fetcher_code', 'src/infrastructure/services/FotMobRawDetailFetcher.js'],
    ['route_identity_reconciler_code', 'src/infrastructure/services/FotMobRouteIdentityReconciler.js'],
    ['raw_write_runner_input_contract_code', 'scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js'],
    [
        'aq_contradiction_review_plan_test',
        'tests/unit/pageprops_v2_accepted_mapping_baseline_contradiction_review_plan_aq.test.js',
    ],
    ['ap_blocker_investigation_test', 'tests/unit/pageprops_v2_no_write_recapture_blocker_investigation_ap.test.js'],
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

function normalizeText(value) {
    return String(value ?? '').trim();
}

function isReverseFixtureReady(target = {}) {
    return (
        target.reverse_fixture_detected === true &&
        normalizeText(target.reverse_fixture_evidence_status) === 'reverse_fixture_detected' &&
        normalizeText(target.contradiction_review_planned_status) === 'contradiction_review_ready'
    );
}

// eslint-disable-next-line complexity -- 矛盾状态映射需要显式保留所有治理标记。
function buildExecutionTarget(planTarget = {}) {
    const reverseFixtureReady = isReverseFixtureReady(planTarget);
    const mappingConfirmed = reverseFixtureReady && planTarget.accepted_mapping_contradiction === true;
    const baselineConfirmed = reverseFixtureReady && planTarget.baseline_acceptance_contradiction === true;
    const contradictionConfirmed = mappingConfirmed || baselineConfirmed;
    const blockedPendingEvidence = !contradictionConfirmed;

    return {
        match_id: planTarget.match_id,
        schedule_external_id: planTarget.schedule_external_id || null,
        observed_detail_external_id: planTarget.observed_detail_external_id || null,
        accepted_mapping_review_status: planTarget.ae_review_status || null,
        baseline_acceptance_review_status: planTarget.ag_baseline_acceptance_status || null,
        source_page_url_base: planTarget.source_page_url_base || null,
        reverse_fixture_evidence_status: planTarget.reverse_fixture_evidence_status || 'unknown',
        contradiction_review_status: contradictionConfirmed
            ? 'contradiction_confirmed'
            : 'contradiction_blocked_pending_evidence',
        accepted_mapping_contradiction_confirmed: mappingConfirmed,
        baseline_acceptance_contradiction_confirmed: baselineConfirmed,
        contradiction_not_confirmed: false,
        contradiction_blocked_pending_evidence: blockedPendingEvidence,
        mapping_suspension_required: mappingConfirmed,
        baseline_suspension_required: baselineConfirmed,
        re_acceptance_required: contradictionConfirmed,
        page_url_base_slug_fragment_evidence_sufficient_for_acceptance: false,
        page_url_base_slug_fragment_evidence_review_result: contradictionConfirmed
            ? 'insufficient_against_reverse_fixture_evidence'
            : 'insufficient_without_reverse_fixture_evidence',
        hash_mismatch_classification: contradictionConfirmed
            ? 'secondary_to_identity_mismatch_reverse_fixture'
            : 'not_reviewable_without_reverse_fixture_evidence',
        hash_mismatch_baseline_update_allowed: false,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        review_blocker_status: blockedPendingEvidence
            ? 'insufficient_reverse_fixture_evidence_blocked_pending_review'
            : 'reverse_fixture_contradiction_confirmed',
        recommended_follow_up: contradictionConfirmed
            ? 'accepted_mapping_and_baseline_suspension_planning'
            : 'requires_future_reverse_fixture_evidence_review',
        contradiction_safe_error_summary:
            planTarget.contradiction_safe_error_summary ||
            'reverse fixture evidence is unavailable from source-controlled artifacts',
    };
}

function chooseNextStep(counts = {}) {
    if (counts.mappingSuspensionRequiredCount > 0 || counts.baselineSuspensionRequiredCount > 0) {
        return {
            recommended_next_step: NEXT_STEP_SUSPENSION_PLANNING,
            next_required_step: NEXT_REQUIRED_STEP_SUSPENSION_PLANNING,
        };
    }
    if (counts.runnerContractFixRequired) {
        return {
            recommended_next_step: NEXT_STEP_RUNNER_FIX,
            next_required_step: NEXT_REQUIRED_STEP_RUNNER_FIX,
        };
    }
    if (counts.expandedReviewRequired) {
        return {
            recommended_next_step: NEXT_STEP_EXPANDED_REVIEW,
            next_required_step: NEXT_REQUIRED_STEP_EXPANDED_REVIEW,
        };
    }
    return {
        recommended_next_step: NEXT_STEP_CONTINUED_REVIEW,
        next_required_step: NEXT_REQUIRED_STEP_CONTINUED_REVIEW,
    };
}

function buildCounts(reviewTargets = [], aqPlan = {}) {
    const contradictionConfirmedCount = reviewTargets.filter(
        target => target.contradiction_review_status === 'contradiction_confirmed'
    ).length;
    const contradictionBlockedPendingEvidenceCount = reviewTargets.filter(
        target => target.contradiction_review_status === 'contradiction_blocked_pending_evidence'
    ).length;
    const acceptedMappingContradictionConfirmedCount = reviewTargets.filter(
        target => target.accepted_mapping_contradiction_confirmed
    ).length;
    const baselineAcceptanceContradictionConfirmedCount = reviewTargets.filter(
        target => target.baseline_acceptance_contradiction_confirmed
    ).length;
    const mappingSuspensionRequiredCount = reviewTargets.filter(target => target.mapping_suspension_required).length;
    const baselineSuspensionRequiredCount = reviewTargets.filter(target => target.baseline_suspension_required).length;
    const reAcceptanceRequiredCount = reviewTargets.filter(target => target.re_acceptance_required).length;
    const runnerContractFixRequired = aqPlan.runner_contract_fix_planning_required === true;
    const expandedReviewRequired = contradictionBlockedPendingEvidenceCount > 0;

    return {
        contradictionReviewCandidateCount: reviewTargets.length,
        contradictionReviewedCount: reviewTargets.length,
        contradictionConfirmedCount,
        contradictionNotConfirmedCount: 0,
        contradictionBlockedPendingEvidenceCount,
        acceptedMappingContradictionConfirmedCount,
        baselineAcceptanceContradictionConfirmedCount,
        mappingSuspensionRequiredCount,
        baselineSuspensionRequiredCount,
        reAcceptanceRequiredCount,
        runnerContractFixRequired,
        expandedReviewRequired,
    };
}

function buildArtifact(context = {}) {
    const reviewTargets = (Array.isArray(context.aqPlan.review_targets) ? context.aqPlan.review_targets : []).map(
        buildExecutionTarget
    );
    const counts = buildCounts(reviewTargets, context.aqPlan);
    const nextStep = chooseNextStep(counts);

    return {
        artifact_type: 'accepted_mapping_baseline_contradiction_review_result',
        artifact_status: EXECUTION_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        generated_at: context.generatedAt,
        execution_status: EXECUTION_STATUS,
        contradiction_review_execution_performed: true,
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
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
        re_acceptance_execution_performed: false,
        mapping_rollback_execution_performed: false,
        baseline_rollback_execution_performed: false,
        accepted_artifact_mutation_performed: false,
        baseline_artifact_mutation_performed: false,
        full_payload_saved: false,
        full_payload_printed: false,
        full_source_body_saved: false,
        full_source_body_printed: false,
        contradiction_review_status_catalog: REVIEW_STATUS_CATALOG,
        contradiction_review_candidate_count: counts.contradictionReviewCandidateCount,
        contradiction_reviewed_count: counts.contradictionReviewedCount,
        contradiction_confirmed_count: counts.contradictionConfirmedCount,
        contradiction_not_confirmed_count: counts.contradictionNotConfirmedCount,
        contradiction_blocked_pending_evidence_count: counts.contradictionBlockedPendingEvidenceCount,
        accepted_mapping_contradiction_confirmed_count: counts.acceptedMappingContradictionConfirmedCount,
        baseline_acceptance_contradiction_confirmed_count: counts.baselineAcceptanceContradictionConfirmedCount,
        mapping_suspension_required_count: counts.mappingSuspensionRequiredCount,
        baseline_suspension_required_count: counts.baselineSuspensionRequiredCount,
        re_acceptance_required_count: counts.reAcceptanceRequiredCount,
        runner_contract_fix_required: counts.runnerContractFixRequired,
        expanded_review_required: counts.expandedReviewRequired,
        hash_mismatch_classification: 'secondary_to_identity_mismatch_reverse_fixture_for_confirmed_targets',
        hash_mismatch_baseline_update_allowed: false,
        page_url_base_slug_fragment_evidence_alone_sufficient: false,
        reverse_fixture_evidence_remains_blocking: true,
        payload_recapture_retry_ready: false,
        raw_write_execution_ready: false,
        accepted_artifacts_rewritten: false,
        baseline_artifacts_rewritten: false,
        review_targets: reviewTargets,
        confirmed_contradiction_targets: reviewTargets.filter(
            target => target.contradiction_review_status === 'contradiction_confirmed'
        ),
        blocked_pending_evidence_targets: reviewTargets.filter(
            target => target.contradiction_review_status === 'contradiction_blocked_pending_evidence'
        ),
        recommended_next_step: nextStep.recommended_next_step,
        next_required_step: nextStep.next_required_step,
    };
}

function formatTargetLine(target = {}) {
    return `- ${target.match_id}: requested=${target.schedule_external_id || 'unknown'} observed=${
        target.observed_detail_external_id || 'unknown'
    } review_status=${target.contradiction_review_status} mapping_suspension_required=${
        target.mapping_suspension_required
    } baseline_suspension_required=${target.baseline_suspension_required}`;
}

function buildReport(artifact = {}) {
    const confirmedLines = artifact.confirmed_contradiction_targets.map(formatTargetLine).join('\n');

    return `# Data Entrypoint Governance - Phase 5.21 L2V3AR

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- execution_status=${artifact.execution_status}
- contradiction_review_execution_performed=${artifact.contradiction_review_execution_performed}
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
- re_acceptance_execution_performed=false
- accepted_artifact_mutation_performed=false
- baseline_artifact_mutation_performed=false

## Counts

- reviewed_input_artifact_count=${artifact.reviewed_input_artifact_count}
- contradiction_review_candidate_count=${artifact.contradiction_review_candidate_count}
- contradiction_reviewed_count=${artifact.contradiction_reviewed_count}
- contradiction_confirmed_count=${artifact.contradiction_confirmed_count}
- contradiction_not_confirmed_count=${artifact.contradiction_not_confirmed_count}
- contradiction_blocked_pending_evidence_count=${artifact.contradiction_blocked_pending_evidence_count}
- accepted_mapping_contradiction_confirmed_count=${artifact.accepted_mapping_contradiction_confirmed_count}
- baseline_acceptance_contradiction_confirmed_count=${artifact.baseline_acceptance_contradiction_confirmed_count}
- mapping_suspension_required_count=${artifact.mapping_suspension_required_count}
- baseline_suspension_required_count=${artifact.baseline_suspension_required_count}
- re_acceptance_required_count=${artifact.re_acceptance_required_count}

## Review Result

- page_url_base_slug_fragment_evidence_alone_sufficient=${artifact.page_url_base_slug_fragment_evidence_alone_sufficient}
- hash_mismatch_classification=${artifact.hash_mismatch_classification}
- hash_mismatch_baseline_update_allowed=${artifact.hash_mismatch_baseline_update_allowed}
- runner_contract_fix_required=${artifact.runner_contract_fix_required}
- expanded_review_required=${artifact.expanded_review_required}
- payload_recapture_retry_ready=${artifact.payload_recapture_retry_ready}
- raw_write_execution_ready=${artifact.raw_write_execution_ready}
- recommended_next_step=${artifact.recommended_next_step}
- next_required_step=${artifact.next_required_step}

## Confirmed Accepted Mapping/Baseline Contradictions

${confirmedLines || '- none'}

## Remaining Targets

- blocked_pending_evidence_count=${artifact.contradiction_blocked_pending_evidence_count}
- status=insufficient_reverse_fixture_evidence_blocked_pending_review
- these targets are not accepted clean and are not raw-write ready

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
        phase_5_21_l2v3ar_execution_status: artifact.execution_status,
        phase_5_21_l2v3ar_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ar_report_path: REPORT_OUTPUT_PATH,
        accepted_mapping_baseline_contradiction_review_execution_status: artifact.execution_status,
        contradiction_review_execution_performed: true,
        contradiction_review_candidate_count: artifact.contradiction_review_candidate_count,
        contradiction_reviewed_count: artifact.contradiction_reviewed_count,
        contradiction_confirmed_count: artifact.contradiction_confirmed_count,
        contradiction_not_confirmed_count: artifact.contradiction_not_confirmed_count,
        contradiction_blocked_pending_evidence_count: artifact.contradiction_blocked_pending_evidence_count,
        accepted_mapping_contradiction_confirmed_count: artifact.accepted_mapping_contradiction_confirmed_count,
        baseline_acceptance_contradiction_confirmed_count: artifact.baseline_acceptance_contradiction_confirmed_count,
        mapping_suspension_required_count: artifact.mapping_suspension_required_count,
        baseline_suspension_required_count: artifact.baseline_suspension_required_count,
        re_acceptance_required_count: artifact.re_acceptance_required_count,
        runner_contract_fix_required: artifact.runner_contract_fix_required,
        expanded_review_required: artifact.expanded_review_required,
        payload_recapture_retry_ready: false,
        raw_write_execution_ready: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        mapping_suspension_execution_performed: false,
        baseline_suspension_execution_performed: false,
        re_acceptance_execution_performed: false,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function loadContext(overrides = {}) {
    const readJson = overrides.readJsonFile || readJsonFile;

    return {
        generatedAt: overrides.generatedAt || new Date().toISOString(),
        aqPlan: overrides.aqPlan || readJson(AQ_PLAN_PATH),
        manifest: overrides.manifest || readJson(PROPOSAL_MANIFEST_PATH),
    };
}

function runAcceptedMappingBaselineContradictionReviewExecute(options = {}, overrides = {}) {
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
    const result = runAcceptedMappingBaselineContradictionReviewExecute();
    process.stdout.write(
        `${JSON.stringify(
            {
                ok: result.ok,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_OUTPUT_PATH,
                execution_status: result.artifact.execution_status,
                contradiction_review_candidate_count: result.artifact.contradiction_review_candidate_count,
                contradiction_reviewed_count: result.artifact.contradiction_reviewed_count,
                contradiction_confirmed_count: result.artifact.contradiction_confirmed_count,
                contradiction_blocked_pending_evidence_count:
                    result.artifact.contradiction_blocked_pending_evidence_count,
                accepted_mapping_contradiction_confirmed_count:
                    result.artifact.accepted_mapping_contradiction_confirmed_count,
                baseline_acceptance_contradiction_confirmed_count:
                    result.artifact.baseline_acceptance_contradiction_confirmed_count,
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
    EXECUTION_STATUS,
    AQ_PLAN_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    PROPOSAL_MANIFEST_PATH,
    REVIEW_STATUS_CATALOG,
    buildArtifact,
    buildExecutionTarget,
    buildReport,
    loadContext,
    runAcceptedMappingBaselineContradictionReviewExecute,
    runCli,
    updateManifestMetadata,
};

if (require.main === module) {
    runCli().catch(error => {
        process.stderr.write(`${error.stack || error.message}\n`);
        process.exitCode = 1;
    });
}
