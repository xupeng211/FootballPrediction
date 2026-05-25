#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AP';
const PHASE_NAME = 'no_write_payload_recapture_blocker_investigation';
const ARTIFACT_STATUS = 'completed_no_write_payload_recapture_blocker_investigation';
const NEXT_STEP_CONTRADICTION = 'Phase 5.21L2V3AQ: accepted mapping and baseline contradiction review planning';
const NEXT_STEP_CONTRACT = 'Phase 5.21L2V3AQ: recapture runner identity input contract fix planning';
const NEXT_STEP_CONTINUED = 'Phase 5.21L2V3AQ: continued no-write recapture blocker investigation';
const NEXT_REQUIRED_STEP_CONTRADICTION = 'accepted_mapping_and_baseline_contradiction_review_planning';
const NEXT_REQUIRED_STEP_CONTRACT = 'recapture_runner_identity_input_contract_fix_planning';
const NEXT_REQUIRED_STEP_CONTINUED = 'continued_no_write_recapture_blocker_investigation';
const PROPOSAL_MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_blocker_investigation.phase521l2v3ap.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AP.md';

const REVIEWED_INPUTS = Object.freeze([
    [
        'no_write_payload_recapture_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_result.phase521l2v3ao.json',
    ],
    [
        'no_write_payload_recapture_plan',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_plan.phase521l2v3an.json',
    ],
    [
        'payload_source_declaration_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_result.phase521l2v3am.json',
    ],
    [
        'payload_source_declaration_plan',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_plan.phase521l2v3al.json',
    ],
    [
        'raw_write_input_source_investigation',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.raw_write_input_source_investigation.phase521l2v3ak.json',
    ],
    [
        'controlled_raw_write_execution_plan',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_raw_match_data_write_execution_plan.phase521l2v3aj.json',
    ],
    [
        'final_db_write_authorization_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.final_db_write_authorization_result.phase521l2v3ai.json',
    ],
    [
        'baseline_acceptance_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.baseline_acceptance_result.phase521l2v3ag.json',
    ],
    [
        'identity_mapping_acceptance_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_result.phase521l2v3ae.json',
    ],
    [
        'enriched_no_write_verification_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_result.phase521l2v3ac.json',
    ],
    [
        'enriched_targets',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json',
    ],
    [
        'source_inventory_acquisition_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json',
    ],
    [
        'date_mismatch_rule_artifact',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json',
    ],
    [
        'expanded_date_rule_verification',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json',
    ],
    ['proposal_manifest', PROPOSAL_MANIFEST_PATH],
    ['no_write_payload_recapture_execute_helper', 'scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js'],
    ['fotmob_raw_detail_fetcher_code', 'src/infrastructure/services/FotMobRawDetailFetcher.js'],
    ['route_identity_reconciler_code', 'src/infrastructure/services/FotMobRouteIdentityReconciler.js'],
    [
        'no_write_payload_recapture_execute_test',
        'tests/unit/pageprops_v2_no_write_payload_recapture_execute_ao.test.js',
    ],
    [
        'identity_mapping_acceptance_execute_test',
        'tests/unit/pageprops_v2_identity_mapping_acceptance_review_execute_ae.test.js',
    ],
    ['baseline_acceptance_execute_test', 'tests/unit/pageprops_v2_baseline_acceptance_execute_ag.test.js'],
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

function buildFotMobMatchUrl(externalId) {
    const id = normalizeText(externalId);
    if (!/^\d+$/.test(id)) throw new Error(`INVALID_EXTERNAL_ID:${externalId}`);
    return `https://www.fotmob.com/match/${id}`;
}

function urlPath(value) {
    const text = normalizeText(value);
    if (!text) return null;
    try {
        return new URL(text, 'https://www.fotmob.com').pathname.replace(/\/+$/, '') || '/';
    } catch {
        return text.split('#')[0].split('?')[0].replace(/\/+$/, '') || null;
    }
}

function findEntryByMatchId(entries = [], matchId) {
    return (
        (Array.isArray(entries) ? entries : []).find(
            entry => normalizeText(entry.match_id) === normalizeText(matchId)
        ) || null
    );
}

function findTargetByMatchId(manifest = {}, matchId) {
    return findEntryByMatchId(manifest.candidate_targets, matchId);
}

function findKnownMapping(l2v3m = {}, scheduleExternalId) {
    return (
        (Array.isArray(l2v3m.known_mappings) ? l2v3m.known_mappings : []).find(
            entry => normalizeText(entry.schedule_external_id) === normalizeText(scheduleExternalId)
        ) || null
    );
}

function findDateRuleEntry(l2v3n = {}, matchId) {
    return findEntryByMatchId(l2v3n.target_summaries, matchId);
}

function chooseText(...values) {
    for (const value of values) {
        const text = normalizeText(value);
        if (text) return text;
    }
    return null;
}

function inferRunnerUsesScheduleRoute(aoHelperSource = '') {
    return /buildFotMobMatchUrl\(target\.external_id\)/.test(aoHelperSource);
}

function inferRunnerUsesAcceptedSourcePageUrlForRequest(aoHelperSource = '') {
    return (
        /fetchHtmlFn\(target\.source_page_url/.test(aoHelperSource) ||
        /fetchHtml\(target\.source_page_url/.test(aoHelperSource)
    );
}

function inferAoTestUsesSimplifiedMatchRoute(testSource = '') {
    return testSource.includes('source_page_url: `/match/${item.external_id}#${item.external_id}`');
}

function buildLikelyRootCause(context = {}) {
    if (context.accepted_mapping_contradiction || context.baseline_acceptance_contradiction) {
        return 'accepted mapping and baseline accepted schedule-side slug/fragment evidence without resolved detail identity, while L2V3M/L2V3N already recorded the same schedule id as a reverse fixture';
    }
    if (context.runner_input_contract_issue) {
        return 'recapture runner rebuilt /match/{schedule_external_id} and did not use accepted source URL evidence as the request contract';
    }
    return 'blocker remains unresolved from source-controlled artifacts alone';
}

function chooseNextStep(context = {}) {
    if (context.accepted_mapping_contradiction || context.baseline_acceptance_contradiction) {
        return {
            recommended_next_step: NEXT_STEP_CONTRADICTION,
            next_required_step: NEXT_REQUIRED_STEP_CONTRADICTION,
        };
    }
    if (context.runner_input_contract_issue) {
        return {
            recommended_next_step: NEXT_STEP_CONTRACT,
            next_required_step: NEXT_REQUIRED_STEP_CONTRACT,
        };
    }
    return {
        recommended_next_step: NEXT_STEP_CONTINUED,
        next_required_step: NEXT_REQUIRED_STEP_CONTINUED,
    };
}

function buildArtifact(context = {}) {
    const aoArtifact = context.aoArtifact || {};
    const blockedResults = Array.isArray(aoArtifact.per_target_results) ? aoArtifact.per_target_results : [];
    const blockerTarget = blockedResults[0] || {};
    const matchId = normalizeText(blockerTarget.match_id);
    const requestedExternalId = normalizeText(blockerTarget.external_id);
    const observedDetailExternalId = chooseText(
        blockerTarget.observed_detail_external_id,
        context.l2v3nEntry?.observed_detail_external_id,
        context.l2v3mKnownMapping?.detail_external_id
    );
    const requestedRouteUrl = buildFotMobMatchUrl(requestedExternalId);
    const acceptedSourcePageUrl = chooseText(
        context.l2v3aeEntry?.source_page_url,
        context.l2v3agEntry?.source_page_url,
        context.enrichedTarget?.source_page_url
    );
    const acceptedSourcePageUrlBase = chooseText(
        context.l2v3aeEntry?.source_page_url_base,
        context.l2v3agEntry?.source_page_url_base,
        context.enrichedTarget?.source_page_url_base
    );
    const sourceUrlFragmentExternalId = chooseText(
        context.l2v3aeEntry?.source_url_fragment_external_id,
        context.l2v3agEntry?.source_url_fragment_external_id,
        context.enrichedTarget?.source_url_fragment_external_id
    );
    const hashMismatchClassification = context.identityMismatchConfirmed
        ? 'secondary_to_identity_mismatch_reverse_fixture'
        : 'identity_status_unresolved';
    const pageUrlBaseIdentityEvidenceSufficient = false;
    const hashMismatchAcceptanceAllowed = false;
    const nextStep = chooseNextStep(context);
    const likelyRootCause = buildLikelyRootCause(context);

    return {
        artifact_type: 'no_write_payload_recapture_blocker_investigation',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        generated_at: context.generatedAt,
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        investigation_status: ARTIFACT_STATUS,
        no_write_payload_recapture_blocker_investigation_performed: true,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        network_request_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        raw_write_execution_performed: false,
        raw_write_runner_write_mode_used: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        full_payload_saved: false,
        full_payload_printed: false,
        full_source_body_saved: false,
        full_source_body_printed: false,
        blocker_target_count: context.blockerTargetCount,
        blocker_target_match_id: matchId,
        requested_external_id: requestedExternalId,
        observed_detail_external_id: observedDetailExternalId,
        requested_route_url: requestedRouteUrl,
        accepted_source_page_url: acceptedSourcePageUrl,
        accepted_source_page_url_base: acceptedSourcePageUrlBase,
        source_url_fragment_external_id: sourceUrlFragmentExternalId,
        source_url_fragment_external_id_matches_schedule_external_id:
            normalizeText(sourceUrlFragmentExternalId) === requestedExternalId,
        page_url_base_match_status: chooseText(
            blockerTarget.page_url_base_match_status,
            context.l2v3nEntry?.page_url_base_match_status
        ),
        page_url_base_identity_evidence_sufficient: pageUrlBaseIdentityEvidenceSufficient,
        team_date_status_match_status: chooseText(
            blockerTarget.team_date_status_match_status,
            context.l2v3nEntry?.team_pair_match_status
        ),
        date_compatibility_status: chooseText(
            blockerTarget.date_compatibility_status,
            context.l2v3nEntry?.date_rule_status,
            context.l2v3mKnownMapping?.classification
        ),
        hash_validation_status: chooseText(blockerTarget.hash_validation_status, 'not_evaluated'),
        hash_mismatch_classification: hashMismatchClassification,
        hash_mismatch_acceptance_allowed: hashMismatchAcceptanceAllowed,
        stable_pageprops_payload_v1_hash: blockerTarget.stable_pageprops_payload_v1_hash || null,
        baseline_hash: chooseText(context.proposalTarget?.baseline_hash),
        identity_mismatch_confirmed: context.identityMismatchConfirmed,
        reverse_fixture_confirmed: context.reverseFixtureConfirmed,
        date_route_mismatch_confirmed: context.dateRouteMismatchConfirmed,
        runner_input_contract_issue: context.runner_input_contract_issue,
        accepted_mapping_contradiction: context.accepted_mapping_contradiction,
        baseline_acceptance_contradiction: context.baseline_acceptance_contradiction,
        source_url_route_issue: context.source_url_route_issue,
        accepted_mapping_entry_has_observed_detail_external_id: Boolean(
            normalizeText(context.l2v3aeEntry?.observed_detail_external_id)
        ),
        baseline_entry_has_observed_detail_external_id: Boolean(
            normalizeText(context.l2v3agEntry?.observed_detail_external_id)
        ),
        ao_runner_uses_schedule_match_route: context.ao_runner_uses_schedule_match_route,
        ao_runner_uses_accepted_source_page_url_for_request:
            context.ao_runner_uses_accepted_source_page_url_for_request,
        ao_test_uses_simplified_match_route_fixture: context.ao_test_uses_simplified_match_route_fixture,
        l2v3m_known_mapping_present: Boolean(context.l2v3mKnownMapping),
        l2v3n_blocker_entry_present: Boolean(context.l2v3nEntry),
        l2v3m_known_mapping: context.l2v3mKnownMapping || null,
        l2v3n_blocker_entry: context.l2v3nEntry || null,
        l2v3ae_review_status: chooseText(context.l2v3aeEntry?.review_status),
        l2v3ag_baseline_acceptance_status: chooseText(context.l2v3agEntry?.baseline_acceptance_status),
        likely_root_cause: likelyRootCause,
        payload_recapture_retry_ready: false,
        raw_write_execution_ready: false,
        recapture_retry_requires_separate_future_authorization: true,
        raw_write_execution_requires_separate_future_authorization: true,
        blocker_list: blockerTarget.blocker_list || [],
        safe_error_summary: chooseText(
            context.l2v3nEntry?.safe_error_summary,
            'local artifact investigation only; reverse fixture blocker remains unresolved'
        ),
        recommended_next_step: nextStep.recommended_next_step,
        next_required_step: nextStep.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AP

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- investigation_status=${artifact.investigation_status}
- no_write_payload_recapture_blocker_investigation_performed=true
- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- raw_write_execution_performed=false
- raw_write_runner_write_mode_used=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false

## Blocker Target

- blocker_target_count=${artifact.blocker_target_count}
- blocker_target_match_id=${artifact.blocker_target_match_id}
- requested_external_id=${artifact.requested_external_id}
- observed_detail_external_id=${artifact.observed_detail_external_id}
- requested_route_url=${artifact.requested_route_url}
- accepted_source_page_url=${artifact.accepted_source_page_url || 'none'}
- accepted_source_page_url_base=${artifact.accepted_source_page_url_base || 'none'}
- source_url_fragment_external_id=${artifact.source_url_fragment_external_id || 'none'}

## Classification

- identity_mismatch_confirmed=${artifact.identity_mismatch_confirmed}
- reverse_fixture_confirmed=${artifact.reverse_fixture_confirmed}
- date_route_mismatch_confirmed=${artifact.date_route_mismatch_confirmed}
- page_url_base_match_status=${artifact.page_url_base_match_status || 'unknown'}
- page_url_base_identity_evidence_sufficient=${artifact.page_url_base_identity_evidence_sufficient}
- team_date_status_match_status=${artifact.team_date_status_match_status || 'unknown'}
- date_compatibility_status=${artifact.date_compatibility_status || 'unknown'}
- hash_validation_status=${artifact.hash_validation_status || 'unknown'}
- hash_mismatch_classification=${artifact.hash_mismatch_classification}
- hash_mismatch_acceptance_allowed=${artifact.hash_mismatch_acceptance_allowed}

## Consistency Analysis

- runner_input_contract_issue=${artifact.runner_input_contract_issue}
- source_url_route_issue=${artifact.source_url_route_issue}
- ao_runner_uses_schedule_match_route=${artifact.ao_runner_uses_schedule_match_route}
- ao_runner_uses_accepted_source_page_url_for_request=${artifact.ao_runner_uses_accepted_source_page_url_for_request}
- ao_test_uses_simplified_match_route_fixture=${artifact.ao_test_uses_simplified_match_route_fixture}
- accepted_mapping_contradiction=${artifact.accepted_mapping_contradiction}
- baseline_acceptance_contradiction=${artifact.baseline_acceptance_contradiction}
- accepted_mapping_entry_has_observed_detail_external_id=${artifact.accepted_mapping_entry_has_observed_detail_external_id}
- baseline_entry_has_observed_detail_external_id=${artifact.baseline_entry_has_observed_detail_external_id}
- l2v3ae_review_status=${artifact.l2v3ae_review_status || 'unknown'}
- l2v3ag_baseline_acceptance_status=${artifact.l2v3ag_baseline_acceptance_status || 'unknown'}

## Root Cause

- likely_root_cause=${artifact.likely_root_cause}
- safe_error_summary=${artifact.safe_error_summary}

## Readiness

- payload_recapture_retry_ready=false
- raw_write_execution_ready=false
- recapture_retry_requires_separate_future_authorization=true
- raw_write_execution_requires_separate_future_authorization=true
- recommended_next_step=${artifact.recommended_next_step}

## Explicit Non-Execution

- no live fetch
- no detail fetch
- no network request
- no DB writes
- no raw_match_data inserts
- no matches writes
- no matches.external_id changes
- no raw write execution
- no raw write runner write mode
- no full payload printed or saved
`;
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3ap_investigation_status: artifact.investigation_status,
        phase_5_21_l2v3ap_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ap_report_path: REPORT_OUTPUT_PATH,
        no_write_payload_recapture_blocker_investigation_status: artifact.investigation_status,
        blocker_target_count: artifact.blocker_target_count,
        requested_external_id: artifact.requested_external_id,
        observed_detail_external_id: artifact.observed_detail_external_id,
        identity_mismatch_confirmed: artifact.identity_mismatch_confirmed,
        reverse_fixture_confirmed: artifact.reverse_fixture_confirmed,
        date_route_mismatch_confirmed: artifact.date_route_mismatch_confirmed,
        hash_mismatch_classification: artifact.hash_mismatch_classification,
        likely_root_cause: artifact.likely_root_cause,
        runner_input_contract_issue: artifact.runner_input_contract_issue,
        accepted_mapping_contradiction: artifact.accepted_mapping_contradiction,
        baseline_acceptance_contradiction: artifact.baseline_acceptance_contradiction,
        source_url_route_issue: artifact.source_url_route_issue,
        payload_recapture_retry_ready: false,
        raw_write_execution_ready: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        raw_write_execution_performed: false,
        raw_write_runner_write_mode_used: false,
        full_payload_saved: false,
        full_payload_printed: false,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

// eslint-disable-next-line complexity -- Governance phase input aggregation stays explicit for auditability.
function loadContext(overrides = {}) {
    const readJson = overrides.readJsonFile || readJsonFile;
    const readText = overrides.readTextFile || readTextFile;
    const manifest = overrides.manifest || readJson(PROPOSAL_MANIFEST_PATH);
    const aoArtifact =
        overrides.aoArtifact ||
        readJson(
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_result.phase521l2v3ao.json'
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
    const aoHelperSource =
        overrides.aoHelperSource || readText('scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js');
    const aoHelperTestSource =
        overrides.aoHelperTestSource ||
        readText('tests/unit/pageprops_v2_no_write_payload_recapture_execute_ao.test.js');
    const blockerTarget = (Array.isArray(aoArtifact.per_target_results) ? aoArtifact.per_target_results : [])[0] || {};
    const matchId = normalizeText(blockerTarget.match_id);
    const scheduleExternalId = normalizeText(blockerTarget.external_id);
    const proposalTarget = findTargetByMatchId(manifest, matchId);
    const enrichedTarget = findEntryByMatchId(l2v3aa.enriched_targets, matchId);
    const l2v3aeEntry = findEntryByMatchId(l2v3ae.review_entries, matchId);
    const l2v3agEntry = findEntryByMatchId(l2v3ag.baseline_entries, matchId);
    const l2v3nEntry = findDateRuleEntry(l2v3n, matchId);
    const l2v3mKnownMapping = findKnownMapping(l2v3m, scheduleExternalId);
    const aoRunnerRoutePath = urlPath(buildFotMobMatchUrl(scheduleExternalId));
    const acceptedSourcePageUrlBase = chooseText(
        l2v3aeEntry?.source_page_url_base,
        l2v3agEntry?.source_page_url_base,
        enrichedTarget?.source_page_url_base
    );
    const sourceUrlRouteIssue =
        Boolean(acceptedSourcePageUrlBase) &&
        normalizeText(acceptedSourcePageUrlBase) !== normalizeText(aoRunnerRoutePath);
    const identityMismatchConfirmed =
        normalizeText(blockerTarget.identity_match_status) === 'mismatch' &&
        chooseText(blockerTarget.observed_detail_external_id, l2v3nEntry?.observed_detail_external_id) !==
            scheduleExternalId;
    const reverseFixtureConfirmed =
        normalizeText(blockerTarget.date_compatibility_status) === 'reverse_fixture_detected' &&
        (normalizeText(l2v3nEntry?.date_rule_status) === 'reverse_fixture_detected' ||
            normalizeText(l2v3mKnownMapping?.classification) === 'reverse_fixture_detected');
    const dateRouteMismatchConfirmed =
        normalizeText(blockerTarget.date_route_status) === 'mismatch' && reverseFixtureConfirmed;
    const contradictionEvidence =
        normalizeText(l2v3nEntry?.date_rule_status) === 'reverse_fixture_detected' ||
        normalizeText(l2v3mKnownMapping?.classification) === 'reverse_fixture_detected';
    const acceptedMappingContradiction =
        normalizeText(l2v3aeEntry?.review_status) === 'accepted' &&
        contradictionEvidence &&
        normalizeText(l2v3nEntry?.accepted_mapping) !== 'true';
    const baselineAcceptanceContradiction =
        normalizeText(l2v3agEntry?.baseline_acceptance_status) === 'accepted_enriched_baseline_metadata' &&
        contradictionEvidence &&
        normalizeText(l2v3nEntry?.accepted_mapping) !== 'true';

    return {
        generatedAt: overrides.generatedAt || new Date().toISOString(),
        manifest,
        aoArtifact,
        l2v3aa,
        l2v3ac,
        l2v3ae,
        l2v3ag,
        l2v3m,
        l2v3n,
        proposalTarget,
        enrichedTarget,
        l2v3aeEntry,
        l2v3agEntry,
        l2v3nEntry,
        l2v3mKnownMapping,
        blockerTargetCount: Array.isArray(aoArtifact.per_target_results) ? aoArtifact.per_target_results.length : 0,
        identityMismatchConfirmed,
        reverseFixtureConfirmed,
        dateRouteMismatchConfirmed,
        ao_runner_uses_schedule_match_route: inferRunnerUsesScheduleRoute(aoHelperSource),
        ao_runner_uses_accepted_source_page_url_for_request:
            inferRunnerUsesAcceptedSourcePageUrlForRequest(aoHelperSource),
        ao_test_uses_simplified_match_route_fixture: inferAoTestUsesSimplifiedMatchRoute(aoHelperTestSource),
        runner_input_contract_issue:
            inferRunnerUsesScheduleRoute(aoHelperSource) &&
            !inferRunnerUsesAcceptedSourcePageUrlForRequest(aoHelperSource) &&
            sourceUrlRouteIssue,
        accepted_mapping_contradiction: acceptedMappingContradiction,
        baseline_acceptance_contradiction: baselineAcceptanceContradiction,
        source_url_route_issue: sourceUrlRouteIssue,
    };
}

function runNoWriteRecaptureBlockerInvestigation(options = {}, overrides = {}) {
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
    const result = runNoWriteRecaptureBlockerInvestigation();
    process.stdout.write(
        `${JSON.stringify(
            {
                ok: result.ok,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_OUTPUT_PATH,
                investigation_status: result.artifact.investigation_status,
                blocker_target_match_id: result.artifact.blocker_target_match_id,
                requested_external_id: result.artifact.requested_external_id,
                observed_detail_external_id: result.artifact.observed_detail_external_id,
                accepted_mapping_contradiction: result.artifact.accepted_mapping_contradiction,
                baseline_acceptance_contradiction: result.artifact.baseline_acceptance_contradiction,
                runner_input_contract_issue: result.artifact.runner_input_contract_issue,
                payload_recapture_retry_ready: false,
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
    ARTIFACT_STATUS,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    PROPOSAL_MANIFEST_PATH,
    buildFotMobMatchUrl,
    urlPath,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    loadContext,
    runNoWriteRecaptureBlockerInvestigation,
    runCli,
};

if (require.main === module) {
    runCli().catch(error => {
        process.stderr.write(`${error.stack || error.message}\n`);
        process.exitCode = 1;
    });
}
