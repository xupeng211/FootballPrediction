#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines -- L2V3AQ planning keeps source-controlled governance evidence explicit. */

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AQ';
const PHASE_NAME = 'accepted_mapping_baseline_contradiction_review_planning';
const PLANNING_STATUS = 'completed_accepted_mapping_baseline_contradiction_review_planning';
const NEXT_STEP_REVIEW_EXECUTION = 'Phase 5.21L2V3AR: accepted mapping and baseline contradiction review execution';
const NEXT_STEP_SUSPENSION_PLANNING = 'Phase 5.21L2V3AR: accepted mapping and baseline suspension planning';
const NEXT_STEP_EXPANDED_REVIEW_PLANNING =
    'Phase 5.21L2V3AR: expanded accepted mapping/baseline contradiction review planning';
const NEXT_STEP_RUNNER_FIX = 'Phase 5.21L2V3AR: recapture runner identity input contract fix planning';
const NEXT_REQUIRED_STEP_REVIEW_EXECUTION = 'accepted_mapping_and_baseline_contradiction_review_execution';
const NEXT_REQUIRED_STEP_SUSPENSION_PLANNING = 'accepted_mapping_and_baseline_suspension_planning';
const NEXT_REQUIRED_STEP_EXPANDED_REVIEW_PLANNING = 'expanded_accepted_mapping_baseline_contradiction_review_planning';
const NEXT_REQUIRED_STEP_RUNNER_FIX = 'recapture_runner_identity_input_contract_fix_planning';
const PROPOSAL_MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_contradiction_review_plan.phase521l2v3aq.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AQ.md';

const REVIEW_STATUS_CATALOG = Object.freeze([
    'contradiction_not_reviewed',
    'contradiction_review_ready',
    'contradiction_confirmed',
    'contradiction_rejected',
    'suspend_mapping_required',
    'suspend_baseline_required',
    'supersede_required',
    're_acceptance_required',
    'blocker_investigation_required',
]);

const REVIEWED_INPUTS = Object.freeze([
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
    ['ap_blocker_investigation_test', 'tests/unit/pageprops_v2_no_write_recapture_blocker_investigation_ap.test.js'],
    [
        'ae_identity_mapping_acceptance_execute_test',
        'tests/unit/pageprops_v2_identity_mapping_acceptance_review_execute_ae.test.js',
    ],
    ['ag_baseline_acceptance_execute_test', 'tests/unit/pageprops_v2_baseline_acceptance_execute_ag.test.js'],
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

function chooseText(...values) {
    for (const value of values) {
        const text = normalizeText(value);
        if (text) return text;
    }
    return null;
}

function findEntryByMatchId(entries = [], matchId) {
    return (
        (Array.isArray(entries) ? entries : []).find(
            entry => normalizeText(entry.match_id) === normalizeText(matchId)
        ) || null
    );
}

function findKnownMapping(artifact = {}, scheduleExternalId) {
    return (
        (Array.isArray(artifact.known_mappings) ? artifact.known_mappings : []).find(
            entry => normalizeText(entry.schedule_external_id) === normalizeText(scheduleExternalId)
        ) || null
    );
}

function findTargetByMatchId(manifest = {}, matchId) {
    return findEntryByMatchId(manifest.candidate_targets, matchId);
}

function inferRunnerUsesScheduleRoute(helperSource = '') {
    return /buildFotMobMatchUrl\(target\.external_id\)/.test(helperSource);
}

function inferRunnerUsesAcceptedSourcePageUrlForRequest(helperSource = '') {
    return (
        /fetchHtmlFn\(target\.source_page_url/.test(helperSource) ||
        /fetchHtml\(target\.source_page_url/.test(helperSource)
    );
}

function indexAcceptedEntries(entries = [], acceptedStatusField, acceptedStatusValue) {
    return new Map(
        (Array.isArray(entries) ? entries : [])
            .filter(entry => normalizeText(entry[acceptedStatusField]) === acceptedStatusValue)
            .map(entry => [normalizeText(entry.match_id), entry])
    );
}

function collectCandidateMatchIds(acceptedAeByMatch, acceptedAgByMatch, manifest = {}) {
    const ids = new Set([...acceptedAeByMatch.keys(), ...acceptedAgByMatch.keys()]);
    for (const target of Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : []) {
        if (ids.has(normalizeText(target.match_id))) continue;
        if (acceptedAeByMatch.size === 0 && acceptedAgByMatch.size === 0) ids.add(normalizeText(target.match_id));
    }
    return [...ids].filter(Boolean).sort();
}

function buildReviewTarget(context = {}, matchId) {
    const proposalTarget = findTargetByMatchId(context.manifest, matchId);
    const aeEntry = context.acceptedAeByMatch.get(matchId) || null;
    const agEntry = context.acceptedAgByMatch.get(matchId) || null;
    const nEntry = findEntryByMatchId(context.l2v3n.target_summaries, matchId);
    const scheduleExternalId = chooseText(
        aeEntry?.source_url_fragment_external_id,
        agEntry?.source_url_fragment_external_id,
        proposalTarget?.external_id
    );
    const mEntry = findKnownMapping(context.l2v3m, scheduleExternalId);
    const reverseFixtureDetected =
        normalizeText(nEntry?.date_rule_status) === 'reverse_fixture_detected' ||
        normalizeText(mEntry?.classification) === 'reverse_fixture_detected';
    const acceptedMappingContradiction = Boolean(aeEntry) && reverseFixtureDetected;
    const baselineAcceptanceContradiction = Boolean(agEntry) && reverseFixtureDetected;
    const reviewReady = reverseFixtureDetected;

    return {
        match_id: matchId,
        schedule_external_id: scheduleExternalId || null,
        observed_detail_external_id: chooseText(nEntry?.observed_detail_external_id, mEntry?.detail_external_id),
        ae_review_status: chooseText(aeEntry?.review_status),
        ag_baseline_acceptance_status: chooseText(agEntry?.baseline_acceptance_status),
        source_page_url_base: chooseText(aeEntry?.source_page_url_base, agEntry?.source_page_url_base),
        accepted_mapping_has_observed_detail_external_id: Boolean(normalizeText(aeEntry?.observed_detail_external_id)),
        baseline_has_observed_detail_external_id: Boolean(normalizeText(agEntry?.observed_detail_external_id)),
        reverse_fixture_detected: reverseFixtureDetected,
        reverse_fixture_evidence_status: chooseText(nEntry?.date_rule_status, mEntry?.classification, 'unknown'),
        contradiction_review_planned_status: reviewReady
            ? 'contradiction_review_ready'
            : 'blocker_investigation_required',
        accepted_mapping_contradiction: acceptedMappingContradiction,
        baseline_acceptance_contradiction: baselineAcceptanceContradiction,
        mapping_follow_up_status: acceptedMappingContradiction
            ? 'suspend_mapping_required'
            : 'contradiction_not_reviewed',
        baseline_follow_up_status: baselineAcceptanceContradiction
            ? 'suspend_baseline_required'
            : 'contradiction_not_reviewed',
        re_acceptance_follow_up_status:
            acceptedMappingContradiction || baselineAcceptanceContradiction
                ? 're_acceptance_required'
                : 'blocker_investigation_required',
        contradiction_safe_error_summary: chooseText(
            nEntry?.safe_error_summary,
            'reverse fixture evidence unavailable from source-controlled artifacts'
        ),
    };
}

function chooseNextStep(context = {}) {
    if (context.acceptedMappingContradictionCount > 0 || context.baselineAcceptanceContradictionCount > 0) {
        return {
            recommended_next_step: NEXT_STEP_REVIEW_EXECUTION,
            next_required_step: NEXT_REQUIRED_STEP_REVIEW_EXECUTION,
        };
    }
    if (context.runnerContractFixPlanningRequired) {
        return {
            recommended_next_step: NEXT_STEP_RUNNER_FIX,
            next_required_step: NEXT_REQUIRED_STEP_RUNNER_FIX,
        };
    }
    if (context.mappingSuspensionPlanningRequired || context.baselineSuspensionPlanningRequired) {
        return {
            recommended_next_step: NEXT_STEP_SUSPENSION_PLANNING,
            next_required_step: NEXT_REQUIRED_STEP_SUSPENSION_PLANNING,
        };
    }
    return {
        recommended_next_step: NEXT_STEP_EXPANDED_REVIEW_PLANNING,
        next_required_step: NEXT_REQUIRED_STEP_EXPANDED_REVIEW_PLANNING,
    };
}

function buildLikelyRootCause(context = {}) {
    if (context.acceptedMappingContradictionCount > 0 || context.baselineAcceptanceContradictionCount > 0) {
        return 'accepted mapping and accepted baseline currently rely on schedule-side slug/fragment/page_url_base evidence even when reverse fixture evidence and missing observed detail identity already block safe acceptance';
    }
    if (context.runnerContractFixPlanningRequired) {
        return 'runner route contract still needs a later identity-input fix plan, but no contradiction-ready target could be confirmed from current source-controlled artifacts alone';
    }
    return 'accepted mapping and baseline require broader contradiction review because most targets still have unknown reverse-fixture evidence';
}

function buildArtifact(context = {}) {
    const nextStep = chooseNextStep(context);
    const blockerTarget = context.apArtifact || {};

    return {
        artifact_type: 'accepted_mapping_baseline_contradiction_review_plan',
        artifact_status: PLANNING_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        generated_at: context.generatedAt,
        planning_status: PLANNING_STATUS,
        contradiction_review_planning_status: PLANNING_STATUS,
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        accepted_mapping_baseline_contradiction_review_planning_performed: true,
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
        mapping_suspension_executed: false,
        baseline_suspension_executed: false,
        mapping_rollback_executed: false,
        baseline_rollback_executed: false,
        accepted_artifact_mutation_performed: false,
        baseline_artifact_mutation_performed: false,
        full_payload_saved: false,
        full_payload_printed: false,
        full_source_body_saved: false,
        full_source_body_printed: false,
        blocker_target_count: context.blockerTargetCount,
        blocker_target_match_id: blockerTarget.blocker_target_match_id || null,
        requested_external_id: blockerTarget.requested_external_id || null,
        observed_detail_external_id: blockerTarget.observed_detail_external_id || null,
        known_reverse_fixture_target_count: context.knownReverseFixtureTargetCount,
        accepted_mapping_count: context.acceptedMappingCount,
        baseline_accepted_count: context.baselineAcceptedCount,
        accepted_mapping_contradiction_count: context.acceptedMappingContradictionCount,
        baseline_acceptance_contradiction_count: context.baselineAcceptanceContradictionCount,
        contradiction_review_candidate_count: context.reviewCandidateCount,
        contradiction_review_ready_count: context.reviewReadyCount,
        contradiction_review_blocked_count: context.reviewBlockedCount,
        mapping_suspension_planning_required: context.mappingSuspensionPlanningRequired,
        baseline_suspension_planning_required: context.baselineSuspensionPlanningRequired,
        re_acceptance_planning_required: context.reAcceptancePlanningRequired,
        runner_contract_fix_planning_required: context.runnerContractFixPlanningRequired,
        hash_mismatch_classification: blockerTarget.hash_mismatch_classification || 'identity_status_unresolved',
        hash_mismatch_baseline_update_allowed: false,
        reverse_fixture_evidence_blocks_raw_write_readiness: true,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        contradiction_review_status_catalog: REVIEW_STATUS_CATALOG,
        review_scope_counts: {
            reverse_fixture_detected_count: context.knownReverseFixtureTargetCount,
            reverse_fixture_unknown_count: context.reviewBlockedCount,
            accepted_mapping_under_review_count: context.acceptedMappingCount,
            baseline_under_review_count: context.baselineAcceptedCount,
        },
        review_targets: context.reviewTargets,
        likely_root_cause: buildLikelyRootCause(context),
        recommended_next_step: nextStep.recommended_next_step,
        next_required_step: nextStep.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AQ

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- planning_status=${artifact.planning_status}
- accepted_mapping_baseline_contradiction_review_planning_performed=true
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
- mapping_suspension_executed=false
- baseline_suspension_executed=false
- mapping_rollback_executed=false
- baseline_rollback_executed=false
- accepted_artifact_mutation_performed=false
- baseline_artifact_mutation_performed=false

## Counts

- blocker_target_count=${artifact.blocker_target_count}
- blocker_target_match_id=${artifact.blocker_target_match_id || 'none'}
- requested_external_id=${artifact.requested_external_id || 'none'}
- observed_detail_external_id=${artifact.observed_detail_external_id || 'none'}
- known_reverse_fixture_target_count=${artifact.known_reverse_fixture_target_count}
- accepted_mapping_count=${artifact.accepted_mapping_count}
- baseline_accepted_count=${artifact.baseline_accepted_count}
- accepted_mapping_contradiction_count=${artifact.accepted_mapping_contradiction_count}
- baseline_acceptance_contradiction_count=${artifact.baseline_acceptance_contradiction_count}
- contradiction_review_candidate_count=${artifact.contradiction_review_candidate_count}
- contradiction_review_ready_count=${artifact.contradiction_review_ready_count}
- contradiction_review_blocked_count=${artifact.contradiction_review_blocked_count}

## Planning

- mapping_suspension_planning_required=${artifact.mapping_suspension_planning_required}
- baseline_suspension_planning_required=${artifact.baseline_suspension_planning_required}
- re_acceptance_planning_required=${artifact.re_acceptance_planning_required}
- runner_contract_fix_planning_required=${artifact.runner_contract_fix_planning_required}
- hash_mismatch_classification=${artifact.hash_mismatch_classification}
- hash_mismatch_baseline_update_allowed=${artifact.hash_mismatch_baseline_update_allowed}
- reverse_fixture_evidence_blocks_raw_write_readiness=${artifact.reverse_fixture_evidence_blocks_raw_write_readiness}
- raw_write_execution_ready=${artifact.raw_write_execution_ready}
- payload_recapture_retry_ready=${artifact.payload_recapture_retry_ready}

## Root Cause

- likely_root_cause=${artifact.likely_root_cause}
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
- no mapping rollback
- no baseline rollback
- no accepted artifact mutation
- no full payload printed or saved
`;
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3aq_planning_status: artifact.planning_status,
        phase_5_21_l2v3aq_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3aq_report_path: REPORT_OUTPUT_PATH,
        accepted_mapping_baseline_contradiction_review_planning_status: artifact.contradiction_review_planning_status,
        accepted_mapping_contradiction_count: artifact.accepted_mapping_contradiction_count,
        baseline_acceptance_contradiction_count: artifact.baseline_acceptance_contradiction_count,
        contradiction_review_candidate_count: artifact.contradiction_review_candidate_count,
        contradiction_review_ready_count: artifact.contradiction_review_ready_count,
        contradiction_review_blocked_count: artifact.contradiction_review_blocked_count,
        mapping_suspension_planning_required: artifact.mapping_suspension_planning_required,
        baseline_suspension_planning_required: artifact.baseline_suspension_planning_required,
        re_acceptance_planning_required: artifact.re_acceptance_planning_required,
        runner_contract_fix_planning_required: artifact.runner_contract_fix_planning_required,
        raw_write_execution_ready: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

// eslint-disable-next-line complexity -- Governance phase input aggregation stays explicit for auditability.
function loadContext(overrides = {}) {
    const readJson = overrides.readJsonFile || readJsonFile;
    const readText = overrides.readTextFile || readTextFile;
    const manifest = overrides.manifest || readJson(PROPOSAL_MANIFEST_PATH);
    const apArtifact =
        overrides.apArtifact ||
        readJson(
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_blocker_investigation.phase521l2v3ap.json'
        );
    const aoArtifact =
        overrides.aoArtifact ||
        readJson(
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_result.phase521l2v3ao.json'
        );
    const l2v3ae =
        overrides.l2v3ae ||
        readJson(
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_result.phase521l2v3ae.json'
        );
    const l2v3ag =
        overrides.l2v3ag ||
        readJson(
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.baseline_acceptance_result.phase521l2v3ag.json'
        );
    const l2v3aa =
        overrides.l2v3aa ||
        readJson(
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json'
        );
    const l2v3ac =
        overrides.l2v3ac ||
        readJson(
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_result.phase521l2v3ac.json'
        );
    const l2v3m =
        overrides.l2v3m ||
        readJson(
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json'
        );
    const l2v3n =
        overrides.l2v3n ||
        readJson(
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json'
        );
    const runnerContractSource =
        overrides.runnerContractSource || readText('scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js');

    const acceptedAeByMatch = indexAcceptedEntries(l2v3ae.review_entries, 'review_status', 'accepted');
    const acceptedAgByMatch = indexAcceptedEntries(
        l2v3ag.baseline_entries,
        'baseline_acceptance_status',
        'accepted_enriched_baseline_metadata'
    );
    const reviewCandidateMatchIds = collectCandidateMatchIds(acceptedAeByMatch, acceptedAgByMatch, manifest);
    const reviewTargets = reviewCandidateMatchIds.map(matchId =>
        buildReviewTarget(
            {
                manifest,
                acceptedAeByMatch,
                acceptedAgByMatch,
                l2v3m,
                l2v3n,
            },
            matchId
        )
    );

    const acceptedMappingContradictionCount = reviewTargets.filter(
        target => target.accepted_mapping_contradiction
    ).length;
    const baselineAcceptanceContradictionCount = reviewTargets.filter(
        target => target.baseline_acceptance_contradiction
    ).length;
    const reviewReadyCount = reviewTargets.filter(
        target => target.contradiction_review_planned_status === 'contradiction_review_ready'
    ).length;
    const reviewBlockedCount = reviewTargets.filter(
        target => target.contradiction_review_planned_status === 'blocker_investigation_required'
    ).length;

    return {
        generatedAt: overrides.generatedAt || new Date().toISOString(),
        manifest,
        apArtifact,
        aoArtifact,
        l2v3ae,
        l2v3ag,
        l2v3aa,
        l2v3ac,
        l2v3m,
        l2v3n,
        acceptedAeByMatch,
        acceptedAgByMatch,
        reviewTargets,
        blockerTargetCount: apArtifact.blocker_target_count || 0,
        knownReverseFixtureTargetCount: (Array.isArray(l2v3n.target_summaries) ? l2v3n.target_summaries : []).filter(
            entry => normalizeText(entry.date_rule_status) === 'reverse_fixture_detected'
        ).length,
        acceptedMappingCount: acceptedAeByMatch.size,
        baselineAcceptedCount: acceptedAgByMatch.size,
        acceptedMappingContradictionCount,
        baselineAcceptanceContradictionCount,
        reviewCandidateCount: reviewTargets.length,
        reviewReadyCount,
        reviewBlockedCount,
        mappingSuspensionPlanningRequired: acceptedMappingContradictionCount > 0,
        baselineSuspensionPlanningRequired: baselineAcceptanceContradictionCount > 0,
        reAcceptancePlanningRequired: acceptedMappingContradictionCount > 0 || baselineAcceptanceContradictionCount > 0,
        runnerContractFixPlanningRequired:
            apArtifact.runner_input_contract_issue === true ||
            (inferRunnerUsesScheduleRoute(runnerContractSource) &&
                !inferRunnerUsesAcceptedSourcePageUrlForRequest(runnerContractSource)),
    };
}

function runAcceptedMappingBaselineContradictionReviewPlan(options = {}, overrides = {}) {
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
    const result = runAcceptedMappingBaselineContradictionReviewPlan();
    process.stdout.write(
        `${JSON.stringify(
            {
                ok: result.ok,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_OUTPUT_PATH,
                planning_status: result.artifact.planning_status,
                accepted_mapping_contradiction_count: result.artifact.accepted_mapping_contradiction_count,
                baseline_acceptance_contradiction_count: result.artifact.baseline_acceptance_contradiction_count,
                contradiction_review_candidate_count: result.artifact.contradiction_review_candidate_count,
                contradiction_review_ready_count: result.artifact.contradiction_review_ready_count,
                contradiction_review_blocked_count: result.artifact.contradiction_review_blocked_count,
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
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    PROPOSAL_MANIFEST_PATH,
    REVIEW_STATUS_CATALOG,
    buildArtifact,
    buildReport,
    loadContext,
    runAcceptedMappingBaselineContradictionReviewPlan,
    runCli,
    updateManifestMetadata,
};

if (require.main === module) {
    runCli().catch(error => {
        process.stderr.write(`${error.stack || error.message}\n`);
        process.exitCode = 1;
    });
}
