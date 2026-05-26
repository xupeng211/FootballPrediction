#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines -- L2V3AV keeps governance contract planning explicit for audit review. */

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AV';
const PHASE_NAME = 'recapture_runner_identity_input_contract_fix_planning';
const PLANNING_STATUS = 'completed_recapture_runner_identity_input_contract_fix_planning';
const NEXT_STEP_IMPLEMENTATION = 'Phase 5.21L2V3AW: recapture runner identity input contract fix implementation';
const NEXT_REQUIRED_STEP_IMPLEMENTATION = 'recapture_runner_identity_input_contract_fix_implementation';
const PROPOSAL_MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const AU_PREREQUISITE_PLAN_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.re_acceptance_prerequisite_plan.phase521l2v3au.json';
const AT_SUSPENSION_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_suspension_result.phase521l2v3at.json';
const AP_BLOCKER_INVESTIGATION_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_blocker_investigation.phase521l2v3ap.json';
const AO_RECAPTURE_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_result.phase521l2v3ao.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.recapture_runner_identity_input_contract_fix_plan.phase521l2v3av.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AV.md';
const NO_WRITE_RECAPTURE_HELPER_PATH = 'scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js';
const RAW_DETAIL_FETCHER_PATH = 'src/infrastructure/services/FotMobRawDetailFetcher.js';
const ROUTE_IDENTITY_RECONCILER_PATH = 'src/infrastructure/services/FotMobRouteIdentityReconciler.js';
const REQUESTED_OBSERVED_MISMATCH_EXAMPLE = '4830466->4830759';

const REVIEWED_INPUTS = Object.freeze([
    ['au_re_acceptance_prerequisite_plan', AU_PREREQUISITE_PLAN_PATH],
    ['au_re_acceptance_prerequisite_report', 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AU.md'],
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
    ['ap_blocker_investigation', AP_BLOCKER_INVESTIGATION_PATH],
    ['ap_blocker_investigation_report', 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AP.md'],
    ['ao_no_write_payload_recapture_result', AO_RECAPTURE_RESULT_PATH],
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
    ['no_write_recapture_runner_helper', NO_WRITE_RECAPTURE_HELPER_PATH],
    ['fotmob_raw_detail_fetcher_code', RAW_DETAIL_FETCHER_PATH],
    ['route_identity_reconciler_code', ROUTE_IDENTITY_RECONCILER_PATH],
    ['proposal_manifest', PROPOSAL_MANIFEST_PATH],
]);

const CONTRACT_FIELDS = Object.freeze([
    {
        id: 'schedule_external_id',
        planned_status: 'correlation_key_only_not_default_detail_route',
        description:
            'Schedule external id identifies the schedule-side target and must not be blindly used as detail route identity.',
    },
    {
        id: 'source_url_fragment_external_id',
        planned_status: 'evidence_component_not_sufficient_alone',
        description: 'Source URL fragment can support evidence but cannot independently authorize identity or retry.',
    },
    {
        id: 'source_page_url',
        planned_status: 'candidate_request_evidence_requires_reaccepted_binding',
        description:
            'Source page URL can be used only after re-accepted mapping binds it to the expected detail identity.',
    },
    {
        id: 'source_page_url_base',
        planned_status: 'insufficient_without_detail_identity_team_date_status',
        description: 'Page URL base alone is insufficient when reverse fixture or identity mismatch is unresolved.',
    },
    {
        id: 'accepted_detail_external_id',
        planned_status: 'future_reaccepted_expected_identity',
        description:
            'Accepted detail external id must come from a future re-acceptance chain, not from suspended artifacts.',
    },
    {
        id: 'observed_detail_external_id',
        planned_status: 'runtime_observation_to_reconcile_not_accept',
        description:
            'Observed detail external id is evidence to reconcile and block on mismatch, not an acceptance action.',
    },
    {
        id: 'recapture_request_identity',
        planned_status: 'must_be_explicit_and_auditable',
        description: 'Recapture request identity must state which id and URL strategy is used before any retry.',
    },
    {
        id: 'recapture_expected_identity',
        planned_status: 'must_match_reaccepted_detail_identity',
        description:
            'Recapture expected identity must be the re-accepted detail identity, not the schedule id by default.',
    },
    {
        id: 'route_identity_strategy',
        planned_status: 'block_on_unresolved_or_suspended_identity',
        description:
            'Route identity strategy must block on suspended mapping, reverse fixture, or unresolved mismatch.',
    },
    {
        id: 'canonical_identity_source',
        planned_status: 'future_reaccepted_mapping_and_evidence_chain',
        description:
            'Canonical identity source must be a fresh re-accepted mapping/baseline chain plus fresh authorization.',
    },
]);

const BLOCKING_RULES = Object.freeze([
    {
        id: 'identity_mismatch_blocks_recapture_retry',
        condition: 'identity_mismatch',
        action: 'block',
        description: 'Requested-vs-observed detail mismatch blocks retry and raw write eligibility.',
    },
    {
        id: 'reverse_fixture_detected_blocks_recapture_retry',
        condition: 'reverse_fixture_detected',
        action: 'block',
        description: 'Reverse fixture detection blocks retry until mapping and baseline are re-accepted.',
    },
    {
        id: 'page_url_base_match_alone_insufficient',
        condition: 'page_url_base_match_only',
        action: 'block',
        description: 'A matching page URL base does not override detail identity, team, date, or status mismatch.',
    },
    {
        id: 'suspended_mapping_or_baseline_blocks_retry',
        condition: 'suspended_mapping_or_baseline',
        action: 'block',
        description: 'Suspended current effective mapping/baseline cannot be used as retry input.',
    },
    {
        id: 'missing_accepted_mapping_blocks_retry',
        condition: 'missing_accepted_mapping',
        action: 'block',
        description: 'Missing accepted mapping blocks recapture retry and raw write eligibility.',
    },
    {
        id: 'missing_re_acceptance_blocks_retry',
        condition: 'missing_re_acceptance',
        action: 'block',
        description: 'Suspended mapping/baseline require future re-acceptance before retry planning can advance.',
    },
    {
        id: 'hash_mismatch_under_identity_mismatch_cannot_update_baseline',
        condition: 'hash_mismatch_with_identity_mismatch',
        action: 'block_baseline_update',
        description:
            'Hash mismatch remains secondary and cannot be used to update baseline while identity mismatch is unresolved.',
    },
]);

const INPUT_PRIORITY_ORDER = Object.freeze([
    {
        rank: 1,
        id: 'block_if_current_effective_mapping_or_baseline_suspended',
        source: 'current_effective_governance_status',
    },
    {
        rank: 2,
        id: 'require_future_reaccepted_mapping_before_retry',
        source: 'mapping_baseline_re_acceptance_chain',
    },
    {
        rank: 3,
        id: 'use_reaccepted_accepted_detail_external_id_as_expected_identity',
        source: 'accepted_detail_external_id',
    },
    {
        rank: 4,
        id: 'bind_source_page_url_and_fragment_to_expected_identity',
        source: 'source_page_url plus source_url_fragment_external_id',
    },
    {
        rank: 5,
        id: 'use_schedule_external_id_only_as_correlation_key',
        source: 'schedule_external_id',
    },
    {
        rank: 6,
        id: 'reconcile_observed_detail_external_id_after_authorized_no_write_retry',
        source: 'observed_detail_external_id',
    },
    {
        rank: 7,
        id: 'require_fresh_final_authorization_before_any_raw_write',
        source: 'fresh_final_authorization',
    },
]);

const IMPLEMENTATION_TEST_CASES = Object.freeze([
    'schedule_external_id_cannot_be_default_detail_route_identity',
    'accepted_detail_external_id_required_for_retry_after_reacceptance',
    'source_page_url_fragment_alone_does_not_authorize_retry',
    'requested_4830466_observed_4830759_blocks_retry',
    'suspended_mapping_baseline_blocks_retry',
    'hash_mismatch_secondary_under_identity_mismatch',
    'implementation_has_no_db_write_or_raw_write_mode',
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

function firstNonEmpty(...values) {
    return values.map(normalizeText).find(Boolean) || '';
}

function nullableText(...values) {
    return firstNonEmpty(...values) || null;
}

function countWhere(values = [], predicate) {
    return values.filter(predicate).length;
}

function sourceIncludes(source = '', pattern) {
    return pattern.test(String(source));
}

function allFieldsEqual(source = {}, entries = []) {
    return entries.every(([key, expectedValue]) => source[key] === expectedValue);
}

function hasExpectedAuSuspensionCounts(auPlan = {}) {
    return allFieldsEqual(auPlan, [
        ['suspended_mapping_count', 8],
        ['suspended_baseline_count', 8],
    ]);
}

function validateAuPrerequisitePlan(auPlan = {}) {
    const checks = [
        [auPlan.proposal_phase === 'Phase 5.21L2V3AU', 'L2V3AU prerequisite plan is required'],
        [
            auPlan.re_acceptance_prerequisite_planning_status === 'completed_re_acceptance_prerequisite_planning',
            'L2V3AU prerequisite planning must be completed',
        ],
        [hasExpectedAuSuspensionCounts(auPlan), 'expected 8 suspended mappings and 8 suspended baselines from AU'],
        [auPlan.blocked_pending_review_target_count === 42, 'expected 42 blocked_pending_review targets from AU'],
        [
            allFieldsEqual(auPlan, [
                ['runner_contract_fix_prerequisite_required', true],
                ['expanded_review_prerequisite_required', true],
                ['fresh_final_authorization_required', true],
            ]),
            'AU must require runner contract fix, expanded review, and fresh final authorization',
        ],
        [
            allFieldsEqual(auPlan, [
                ['raw_write_execution_ready', false],
                ['payload_recapture_retry_ready', false],
            ]),
            'AU must keep raw write execution and recapture retry blocked',
        ],
        [
            allFieldsEqual(auPlan, [
                ['re_acceptance_execution_performed', false],
                ['suspension_reversal_performed', false],
                ['rollback_execution_performed', false],
                ['db_write_performed', false],
                ['raw_match_data_insert_performed', false],
            ]),
            'AU contains a forbidden execution flag',
        ],
    ];

    return checks.filter(([passes]) => !passes).map(([, message]) => message);
}

function findMismatchExample(context = {}) {
    const suspendedTargets = context.auPlan?.suspended_targets_requiring_prerequisites || [];
    const target =
        suspendedTargets.find(
            entry =>
                normalizeText(entry.schedule_external_id) === '4830466' &&
                normalizeText(entry.observed_detail_external_id) === '4830759'
        ) || {};
    const aoTarget = (context.aoResult?.per_target_results || [])[0] || {};
    const requested = firstNonEmpty(target.schedule_external_id, aoTarget.schedule_external_id, aoTarget.external_id);
    const observed = firstNonEmpty(target.observed_detail_external_id, aoTarget.observed_detail_external_id);
    return requested && observed ? `${requested}->${observed}` : null;
}

function firstAoTarget(context = {}) {
    return (context.aoResult?.per_target_results || [])[0] || {};
}

function usesScheduleSideRoute(source = '') {
    return (
        sourceIncludes(source, /const requestUrl = buildFotMobMatchUrl\(target\.external_id\)/) &&
        sourceIncludes(source, /requestedScheduleExternalId:\s*target\.external_id/)
    );
}

function hasRequestedObservedMismatch(mismatchExample, aoTarget = {}) {
    const requestedExternalId = firstNonEmpty(aoTarget.schedule_external_id, aoTarget.external_id);
    const observedDetailExternalId = firstNonEmpty(aoTarget.observed_detail_external_id);

    return (
        mismatchExample === REQUESTED_OBSERVED_MISMATCH_EXAMPLE ||
        `${requestedExternalId}->${observedDetailExternalId}` === REQUESTED_OBSERVED_MISMATCH_EXAMPLE
    );
}

function analyzeCurrentRunnerContract(context = {}) {
    const aoTarget = firstAoTarget(context);
    const ap = context.apInvestigation || {};
    const usesScheduleRoute = usesScheduleSideRoute(context.noWriteRecaptureHelperSource);
    const mismatchExample = findMismatchExample(context);
    const mismatchConfirmed = hasRequestedObservedMismatch(mismatchExample, aoTarget);

    return {
        current_runner_schedule_side_route_issue_confirmed: usesScheduleRoute && mismatchConfirmed,
        schedule_side_route_detected_in_current_runner: usesScheduleRoute,
        runner_uses_accepted_source_page_url_as_request_contract: false,
        requested_observed_mismatch_example: mismatchExample || REQUESTED_OBSERVED_MISMATCH_EXAMPLE,
        requested_external_id: firstNonEmpty(aoTarget.schedule_external_id, aoTarget.external_id, '4830466'),
        observed_detail_external_id: firstNonEmpty(aoTarget.observed_detail_external_id, '4830759'),
        page_url_base_match_status: firstNonEmpty(aoTarget.page_url_base_match_status, ap.page_url_base_match_status),
        identity_match_status: firstNonEmpty(aoTarget.identity_match_status, 'mismatch'),
        date_compatibility_status: firstNonEmpty(
            aoTarget.date_compatibility_status,
            ap.date_compatibility_status,
            'reverse_fixture_detected'
        ),
        hash_validation_status: firstNonEmpty(aoTarget.hash_validation_status, ap.hash_validation_status),
        accepted_source_page_url: nullableText(ap.accepted_source_page_url),
        accepted_source_page_url_base: nullableText(ap.accepted_source_page_url_base),
        source_url_fragment_external_id: nullableText(
            ap.source_url_fragment_external_id,
            aoTarget.source_url_fragment_external_id
        ),
        likely_root_cause:
            firstNonEmpty(ap.likely_root_cause) ||
            'recapture request identity was not bound to a re-accepted detail identity contract',
    };
}

function buildSuspendedContractTarget(target = {}) {
    return {
        match_id: target.match_id,
        schedule_external_id: target.schedule_external_id || null,
        source_url_fragment_external_id: target.source_url_fragment_external_id || target.schedule_external_id || null,
        source_page_url: target.source_page_url || null,
        source_page_url_base: target.source_page_url_base || null,
        accepted_detail_external_id: null,
        observed_detail_external_id: target.observed_detail_external_id || null,
        recapture_request_identity: 'blocked_until_reaccepted_contract',
        recapture_expected_identity: 'blocked_until_reaccepted_contract',
        route_identity_strategy: 'block_suspended_mapping_baseline',
        canonical_identity_source: 'none_until_mapping_baseline_reaccepted',
        current_mapping_effective_status: target.current_mapping_effective_status || 'suspended',
        current_baseline_effective_status: target.current_baseline_effective_status || 'suspended',
        retry_blocked: true,
        retry_blockers: [
            'suspended_mapping_or_baseline',
            'missing_re_acceptance',
            'fresh_final_authorization_required',
        ],
    };
}

function buildArtifact(context = {}) {
    const validationErrors = validateAuPrerequisitePlan(context.auPlan);
    if (validationErrors.length > 0) {
        throw new Error(`Cannot plan L2V3AV runner contract fix: ${validationErrors.join('; ')}`);
    }

    const runnerAnalysis = analyzeCurrentRunnerContract(context);
    const suspendedTargets = (context.auPlan.suspended_targets_requiring_prerequisites || []).map(
        buildSuspendedContractTarget
    );

    return {
        artifact_type: 'recapture_runner_identity_input_contract_fix_plan',
        artifact_status: PLANNING_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        generated_at: context.generatedAt,
        runner_identity_contract_fix_planning_status: PLANNING_STATUS,
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        current_runner_schedule_side_route_issue_confirmed:
            runnerAnalysis.current_runner_schedule_side_route_issue_confirmed,
        schedule_side_route_detected_in_current_runner: runnerAnalysis.schedule_side_route_detected_in_current_runner,
        runner_uses_accepted_source_page_url_as_request_contract:
            runnerAnalysis.runner_uses_accepted_source_page_url_as_request_contract,
        requested_observed_mismatch_example: runnerAnalysis.requested_observed_mismatch_example,
        requested_external_id: runnerAnalysis.requested_external_id,
        observed_detail_external_id: runnerAnalysis.observed_detail_external_id,
        page_url_base_match_status: runnerAnalysis.page_url_base_match_status,
        page_url_base_slug_fragment_alone_insufficient: true,
        identity_match_status: runnerAnalysis.identity_match_status,
        date_compatibility_status: runnerAnalysis.date_compatibility_status,
        hash_validation_status: runnerAnalysis.hash_validation_status,
        hash_mismatch_under_identity_mismatch_secondary: true,
        accepted_source_page_url: runnerAnalysis.accepted_source_page_url,
        accepted_source_page_url_base: runnerAnalysis.accepted_source_page_url_base,
        source_url_fragment_external_id: runnerAnalysis.source_url_fragment_external_id,
        likely_root_cause: runnerAnalysis.likely_root_cause,
        suspended_mapping_count: context.auPlan.suspended_mapping_count,
        suspended_baseline_count: context.auPlan.suspended_baseline_count,
        blocked_pending_review_target_count: context.auPlan.blocked_pending_review_target_count,
        planned_contract_field_count: CONTRACT_FIELDS.length,
        planned_contract_fields: CONTRACT_FIELDS,
        planned_blocking_rule_count: BLOCKING_RULES.length,
        planned_blocking_rules: BLOCKING_RULES,
        planned_input_priority_order: INPUT_PRIORITY_ORDER,
        implementation_test_cases: IMPLEMENTATION_TEST_CASES,
        implementation_required: true,
        implementation_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        network_request_performed: false,
        recapture_retry_performed: false,
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
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
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        suspended_targets_contract_plan: suspendedTargets,
        suspended_mapping_baseline_blocks_retry: countWhere(suspendedTargets, target => target.retry_blocked) === 8,
        recommended_next_step: NEXT_STEP_IMPLEMENTATION,
        next_required_step: NEXT_REQUIRED_STEP_IMPLEMENTATION,
    };
}

function formatContractField(field = {}) {
    return `- ${field.id}: ${field.planned_status}`;
}

function formatBlockingRule(rule = {}) {
    return `- ${rule.condition} -> ${rule.action}: ${rule.id}`;
}

function formatPriority(item = {}) {
    return `${item.rank}. ${item.id}: ${item.source}`;
}

function buildReport(artifact = {}) {
    const contractFields = artifact.planned_contract_fields.map(formatContractField).join('\n');
    const blockingRules = artifact.planned_blocking_rules.map(formatBlockingRule).join('\n');
    const priorityOrder = artifact.planned_input_priority_order.map(formatPriority).join('\n');
    const implementationTests = artifact.implementation_test_cases.map(item => `- ${item}`).join('\n');

    return `# Data Entrypoint Governance - Phase 5.21 L2V3AV

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- runner_identity_contract_fix_planning_status=${artifact.runner_identity_contract_fix_planning_status}
- implementation_required=true
- implementation_performed=false
- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- recapture_retry_performed=false
- re_acceptance_execution_performed=false
- suspension_reversal_performed=false
- rollback_execution_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- raw_write_execution_performed=false
- raw_write_runner_write_mode_used=false
- full_payload_saved=false
- full_payload_printed=false

## Current Runner Schedule-Side Route Issue

- current_runner_schedule_side_route_issue_confirmed=${artifact.current_runner_schedule_side_route_issue_confirmed}
- schedule_side_route_detected_in_current_runner=${artifact.schedule_side_route_detected_in_current_runner}
- runner_uses_accepted_source_page_url_as_request_contract=${artifact.runner_uses_accepted_source_page_url_as_request_contract}
- requested_observed_mismatch_example=${artifact.requested_observed_mismatch_example}
- requested_external_id=${artifact.requested_external_id}
- observed_detail_external_id=${artifact.observed_detail_external_id}
- page_url_base_match_status=${artifact.page_url_base_match_status || 'unknown'}
- page_url_base_slug_fragment_alone_insufficient=true
- identity_match_status=${artifact.identity_match_status || 'unknown'}
- date_compatibility_status=${artifact.date_compatibility_status || 'unknown'}
- hash_validation_status=${artifact.hash_validation_status || 'unknown'}
- hash_mismatch_under_identity_mismatch_secondary=true
- likely_root_cause=${artifact.likely_root_cause}

## Planned Contract Fields

${contractFields}

## Planned Input Priority Order

${priorityOrder}

## Planned Blocking Rules

${blockingRules}

## Future Implementation Test Cases

${implementationTests}

## Readiness

- suspended_mapping_count=${artifact.suspended_mapping_count}
- suspended_baseline_count=${artifact.suspended_baseline_count}
- blocked_pending_review_target_count=${artifact.blocked_pending_review_target_count}
- suspended_mapping_baseline_blocks_retry=${artifact.suspended_mapping_baseline_blocks_retry}
- payload_recapture_retry_ready=false
- raw_write_execution_ready=false
- recommended_next_step=${artifact.recommended_next_step}
- next_required_step=${artifact.next_required_step}

## Explicit Non-Execution

- no runner implementation
- no live fetch
- no detail fetch
- no network request
- no recapture retry
- no DB writes
- no raw_match_data inserts
- no matches writes
- no matches.external_id changes
- no raw write execution
- no re-acceptance execution
- no suspension reversal
- no rollback
- no parser/features/training/prediction
- no full payload printed or saved
`;
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3av_planning_status: artifact.runner_identity_contract_fix_planning_status,
        phase_5_21_l2v3av_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3av_report_path: REPORT_OUTPUT_PATH,
        recapture_runner_identity_input_contract_fix_planning_status:
            artifact.runner_identity_contract_fix_planning_status,
        current_runner_schedule_side_route_issue_confirmed: artifact.current_runner_schedule_side_route_issue_confirmed,
        requested_observed_mismatch_example: artifact.requested_observed_mismatch_example,
        planned_contract_field_count: artifact.planned_contract_field_count,
        planned_blocking_rule_count: artifact.planned_blocking_rule_count,
        implementation_required: true,
        implementation_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        network_request_performed: false,
        recapture_retry_performed: false,
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        raw_write_execution_performed: false,
        raw_write_runner_write_mode_used: false,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        current_effective_governance_status: 'accepted_mapping_baseline_suspended_raw_write_blocked',
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function loadContext(overrides = {}) {
    const readJson = overrides.readJsonFile || readJsonFile;
    const readText = overrides.readTextFile || readTextFile;

    return {
        generatedAt: overrides.generatedAt || new Date().toISOString(),
        manifest: overrides.manifest || readJson(PROPOSAL_MANIFEST_PATH),
        auPlan: overrides.auPlan || readJson(AU_PREREQUISITE_PLAN_PATH),
        atResult: overrides.atResult || readJson(AT_SUSPENSION_RESULT_PATH),
        apInvestigation: overrides.apInvestigation || readJson(AP_BLOCKER_INVESTIGATION_PATH),
        aoResult: overrides.aoResult || readJson(AO_RECAPTURE_RESULT_PATH),
        noWriteRecaptureHelperSource:
            overrides.noWriteRecaptureHelperSource || readText(NO_WRITE_RECAPTURE_HELPER_PATH),
        rawDetailFetcherSource: overrides.rawDetailFetcherSource || readText(RAW_DETAIL_FETCHER_PATH),
        routeIdentityReconcilerSource:
            overrides.routeIdentityReconcilerSource || readText(ROUTE_IDENTITY_RECONCILER_PATH),
    };
}

function runRunnerIdentityContractFixPlan(options = {}, overrides = {}) {
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
    const result = runRunnerIdentityContractFixPlan();
    process.stdout.write(
        `${JSON.stringify(
            {
                ok: result.ok,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_OUTPUT_PATH,
                planning_status: result.artifact.runner_identity_contract_fix_planning_status,
                current_runner_schedule_side_route_issue_confirmed:
                    result.artifact.current_runner_schedule_side_route_issue_confirmed,
                requested_observed_mismatch_example: result.artifact.requested_observed_mismatch_example,
                planned_contract_field_count: result.artifact.planned_contract_field_count,
                planned_blocking_rule_count: result.artifact.planned_blocking_rule_count,
                implementation_required: true,
                implementation_performed: false,
                raw_write_execution_ready: false,
                recommended_next_step: result.artifact.recommended_next_step,
            },
            null,
            2
        )}\n`
    );
}

module.exports = {
    ARTIFACT_OUTPUT_PATH,
    AP_BLOCKER_INVESTIGATION_PATH,
    AO_RECAPTURE_RESULT_PATH,
    AU_PREREQUISITE_PLAN_PATH,
    BLOCKING_RULES,
    CONTRACT_FIELDS,
    INPUT_PRIORITY_ORDER,
    NEXT_STEP_IMPLEMENTATION,
    PHASE,
    PHASE_NAME,
    PLANNING_STATUS,
    PROPOSAL_MANIFEST_PATH,
    REPORT_OUTPUT_PATH,
    REQUESTED_OBSERVED_MISMATCH_EXAMPLE,
    analyzeCurrentRunnerContract,
    buildArtifact,
    buildReport,
    buildSuspendedContractTarget,
    loadContext,
    runCli,
    runRunnerIdentityContractFixPlan,
    updateManifestMetadata,
    validateAuPrerequisitePlan,
};

if (require.main === module) {
    runCli().catch(error => {
        process.stderr.write(`${error.stack || error.message}\n`);
        process.exitCode = 1;
    });
}
