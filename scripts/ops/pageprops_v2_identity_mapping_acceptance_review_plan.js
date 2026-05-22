#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AD';
const PHASE_NAME = 'identity_mapping_acceptance_review_planning';
const ARTIFACT_STATUS = 'completed_identity_mapping_acceptance_review_planning';
const GENERATED_AT = '2026-05-22T08:00:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3AC_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_result.phase521l2v3ac.json';
const L2V3AA_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const L2V3Y_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
const L2V3M_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json';
const L2V3I_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_artifact_design.phase521l2v3i.json';
const L2V3J_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_plan.phase521l2v3j.json';
const L2V3K_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_result.phase521l2v3k.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_plan.phase521l2v3ad.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AD.md';
const EXPECTED_TARGET_COUNT = 50;
const PASS_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AE: identity mapping acceptance review execution',
    next_required_step: 'identity_mapping_acceptance_review_execution',
});
const BLOCKER_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AE: identity mapping acceptance blocker investigation',
    next_required_step: 'identity_mapping_acceptance_blocker_investigation',
});
const CONTINUE_PLANNING_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AE: continued identity mapping acceptance review planning',
    next_required_step: 'continued_identity_mapping_acceptance_review_planning',
});
const INPUT_PATHS = Object.freeze([
    { key: 'manifest', path: MANIFEST_PATH, role: 'current_proposal_manifest', countAsArtifact: true },
    { key: 'l2v3ac_artifact', path: L2V3AC_ARTIFACT_PATH, role: 'no_write_verification_result', countAsArtifact: true },
    { key: 'l2v3aa_artifact', path: L2V3AA_ARTIFACT_PATH, role: 'enriched_targets_artifact', countAsArtifact: true },
    {
        key: 'l2v3y_artifact',
        path: L2V3Y_ARTIFACT_PATH,
        role: 'source_inventory_acquisition_result',
        countAsArtifact: true,
    },
    { key: 'l2v3m_artifact', path: L2V3M_ARTIFACT_PATH, role: 'date_rule_implementation', countAsArtifact: true },
    {
        key: 'l2v3i_artifact',
        path: L2V3I_ARTIFACT_PATH,
        role: 'prior_acceptance_artifact_design',
        countAsArtifact: true,
    },
    { key: 'l2v3j_artifact', path: L2V3J_ARTIFACT_PATH, role: 'prior_acceptance_review_plan', countAsArtifact: true },
    { key: 'l2v3k_artifact', path: L2V3K_ARTIFACT_PATH, role: 'prior_acceptance_review_result', countAsArtifact: true },
]);
const ACCEPTANCE_REVIEW_STATUSES = Object.freeze([
    'review_not_started',
    'review_ready',
    'review_blocked',
    'accepted',
    'rejected',
    'superseded',
]);
const PLANNED_ACCEPTANCE_RULES = Object.freeze([
    'candidate must come from L2V3AC verification passed target set.',
    'source_page_url and source_page_url_base evidence must be present.',
    'source_url_fragment_external_id must equal schedule_external_id.',
    'target_id, match_id, source_inventory_record_key, and source_url_fragment_external_id must be unique.',
    'schedule date, home team, and away team metadata must be present.',
    'source inventory acquisition evidence must be available for the target.',
    'L2V3M route/date rule status must be reviewed before any acceptance execution.',
    'raw write runner must remain blocked before and after review planning.',
    'reviewer_required must remain true until a future execution phase.',
    'accepted_by and accepted_at must remain null in planning.',
    'review_ready must not imply accepted mapping.',
    'identity acceptance must not imply baseline acceptance or final DB-write authorization.',
]);
const PLANNED_BLOCKING_RULES = Object.freeze([
    'verification_not_passed',
    'missing_source_url_evidence',
    'fragment_schedule_mismatch',
    'duplicate_target_or_match_id',
    'duplicate_source_key',
    'duplicate_fragment_external_id',
    'schedule_team_date_mismatch',
    'unresolved_reverse_fixture_evidence',
    'date_rule_blocked_status',
    'raw_write_runner_unexpectedly_ready',
    'human_review_missing',
    'incomplete_audit_trail',
]);
const BLOCKED_TRUE_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowNetwork',
    'allowLiveFetch',
    'allowDetailFetch',
    'allowRawMatchDataWrite',
    'allowMatchesWrite',
    'allowMatchesExternalIdWrite',
    'allowSchemaMigration',
    'allowParserImplementation',
    'allowFeatureExtraction',
    'allowTraining',
    'allowPrediction',
    'allowBrowserRuntime',
    'allowProxyRuntime',
    'executeAcceptance',
    'acceptIdentityMapping',
    'acceptBaseline',
    'allowRawWriteRetry',
    'executeRawWrite',
    'printFullBody',
    'saveFullBody',
    'printFullJson',
    'saveFullJson',
    'printFullPageprops',
    'saveFullPageprops',
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

function normalizeBooleanFlag(value, fallback = false) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = normalizeText(value).toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) return false;
    return fallback;
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        writeFiles: true,
        help: false,
        unknown: [],
    };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-network': 'allowNetwork',
        allow_network: 'allowNetwork',
        'allow-live-fetch': 'allowLiveFetch',
        allow_live_fetch: 'allowLiveFetch',
        'live-fetch': 'allowLiveFetch',
        live_fetch: 'allowLiveFetch',
        'allow-detail-fetch': 'allowDetailFetch',
        allow_detail_fetch: 'allowDetailFetch',
        'detail-fetch': 'allowDetailFetch',
        detail_fetch: 'allowDetailFetch',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-matches-external-id-write': 'allowMatchesExternalIdWrite',
        allow_matches_external_id_write: 'allowMatchesExternalIdWrite',
        'allow-schema-migration': 'allowSchemaMigration',
        allow_schema_migration: 'allowSchemaMigration',
        'allow-parser-implementation': 'allowParserImplementation',
        allow_parser_implementation: 'allowParserImplementation',
        'allow-feature-extraction': 'allowFeatureExtraction',
        allow_feature_extraction: 'allowFeatureExtraction',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        'allow-browser-runtime': 'allowBrowserRuntime',
        allow_browser_runtime: 'allowBrowserRuntime',
        'allow-proxy-runtime': 'allowProxyRuntime',
        allow_proxy_runtime: 'allowProxyRuntime',
        'execute-acceptance': 'executeAcceptance',
        execute_acceptance: 'executeAcceptance',
        'accept-identity-mapping': 'acceptIdentityMapping',
        accept_identity_mapping: 'acceptIdentityMapping',
        'accept-baseline': 'acceptBaseline',
        accept_baseline: 'acceptBaseline',
        'allow-raw-write-retry': 'allowRawWriteRetry',
        allow_raw_write_retry: 'allowRawWriteRetry',
        'execute-raw-write': 'executeRawWrite',
        execute_raw_write: 'executeRawWrite',
        'print-full-body': 'printFullBody',
        print_full_body: 'printFullBody',
        'save-full-body': 'saveFullBody',
        save_full_body: 'saveFullBody',
        'print-full-json': 'printFullJson',
        print_full_json: 'printFullJson',
        'save-full-json': 'saveFullJson',
        save_full_json: 'saveFullJson',
        'print-full-pageprops': 'printFullPageprops',
        print_full_pageprops: 'printFullPageprops',
        'save-full-pageprops': 'saveFullPageprops',
        save_full_pageprops: 'saveFullPageprops',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set(['writeFiles', 'help', ...BLOCKED_TRUE_FLAGS]);

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) index += 1;
        if (!optionKey) {
            options.unknown.push(rawKey);
            continue;
        }
        options[optionKey] = booleanKeys.has(optionKey) ? normalizeBooleanFlag(value, true) : value;
    }
    return options;
}

function cliName(flagName) {
    return flagName.replace(/[A-Z]/g, character => `-${character.toLowerCase()}`);
}

function validateCliOptions(options = {}) {
    const errors = [];
    if (Array.isArray(options.unknown) && options.unknown.length > 0) {
        errors.push(`unknown arguments: ${options.unknown.join(', ')}`);
    }
    for (const flagName of BLOCKED_TRUE_FLAGS) {
        if (normalizeBooleanFlag(options[flagName], false) === true) {
            errors.push(`${cliName(flagName)}=yes is blocked`);
        }
    }
    return { ok: errors.length === 0, errors };
}

function countBy(values = []) {
    const counts = new Map();
    for (const value of values.map(item => normalizeText(item)).filter(Boolean)) {
        counts.set(value, (counts.get(value) || 0) + 1);
    }
    return counts;
}

function indexBy(values = [], keyName) {
    const map = new Map();
    for (const value of values) {
        const key = normalizeText(value?.[keyName]);
        if (key) map.set(key, value);
    }
    return map;
}

function analyzeInputPaths(inputPaths = INPUT_PATHS, dependencies = {}) {
    return inputPaths.map(item => {
        const exists = dependencies.sourceTextByPath
            ? Object.prototype.hasOwnProperty.call(dependencies.sourceTextByPath, item.path)
            : fs.existsSync(absolutePath(item.path));
        return {
            key: item.key,
            path: item.path,
            role: item.role,
            count_as_artifact: item.countAsArtifact === true,
            exists,
        };
    });
}

function hasAcceptedMapping(value = {}) {
    return (
        value.identity_mapping_acceptance_performed === true ||
        Number(value.accepted_mapping_count || 0) !== 0 ||
        value.raw_write_ready_for_execution === true
    );
}

function validateInputs(
    manifest = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {},
    l2v3mArtifact = {},
    priorArtifacts = {}
) {
    const errors = [];
    const allowedNextSteps = new Set([
        'identity_mapping_acceptance_review_planning',
        PASS_NEXT_STEP.next_required_step,
    ]);
    if (!allowedNextSteps.has(normalizeText(manifest.next_required_step))) {
        errors.push('manifest next_required_step must be identity_mapping_acceptance_review_planning');
    }
    if (manifest.raw_write_ready_for_execution === true) {
        errors.push('manifest raw_write_ready_for_execution must be false');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must be 0');
    }
    if (manifest.identity_mapping_acceptance_performed === true) {
        errors.push('manifest identity_mapping_acceptance_performed must be false');
    }
    if (manifest.baseline_acceptance_performed === true) {
        errors.push('manifest baseline_acceptance_performed must be false');
    }
    if (manifest.raw_write_retry_performed === true) {
        errors.push('manifest raw_write_retry_performed must be false');
    }

    if (l2v3acArtifact.proposal_phase !== 'Phase 5.21L2V3AC') {
        errors.push('L2V3AC artifact is required');
    }
    if (l2v3acArtifact.verification_execution_performed !== true) {
        errors.push('L2V3AC verification_execution_performed must be true');
    }
    if (l2v3acArtifact.live_fetch_performed !== false) {
        errors.push('L2V3AC live_fetch_performed must be false');
    }
    if (l2v3acArtifact.detail_fetch_performed !== false) {
        errors.push('L2V3AC detail_fetch_performed must be false');
    }
    if (l2v3acArtifact.db_write_performed !== false) {
        errors.push('L2V3AC db_write_performed must be false');
    }
    if (l2v3acArtifact.verification_status !== 'passed_no_write_source_controlled') {
        errors.push('L2V3AC verification_status must be passed_no_write_source_controlled');
    }
    if (Number(l2v3acArtifact.verified_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AC verified_target_count must be 50');
    }
    if (Number(l2v3acArtifact.failed_target_count || 0) !== 0) {
        errors.push('L2V3AC failed_target_count must be 0');
    }
    if (Number(l2v3acArtifact.blocked_target_count || 0) !== 0) {
        errors.push('L2V3AC blocked_target_count must be 0');
    }
    if (Number(l2v3acArtifact.raw_write_ready_target_count || 0) !== 0) {
        errors.push('L2V3AC raw_write_ready_target_count must be 0');
    }
    if (l2v3acArtifact.raw_write_runner_blocked !== true) {
        errors.push('L2V3AC raw_write_runner_blocked must be true');
    }
    if (hasAcceptedMapping(l2v3acArtifact)) {
        errors.push('L2V3AC must not contain accepted mapping or raw-write-ready state');
    }

    if (Number(l2v3aaArtifact.regenerated_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AA regenerated_target_count must be 50');
    }
    if (hasAcceptedMapping(l2v3aaArtifact)) {
        errors.push('L2V3AA must not contain accepted mapping or raw-write-ready state');
    }
    if (Number(l2v3yArtifact.candidate_scope_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3Y candidate_scope_count must be 50');
    }
    if (hasAcceptedMapping(l2v3yArtifact)) {
        errors.push('L2V3Y must not contain accepted mapping or raw-write-ready state');
    }
    if (l2v3mArtifact.integrated_with_raw_write_guard !== true) {
        errors.push('L2V3M integrated_with_raw_write_guard must remain true');
    }
    if (hasAcceptedMapping(l2v3mArtifact)) {
        errors.push('L2V3M must not contain accepted mapping or raw-write-ready state');
    }

    for (const [key, artifact] of Object.entries(priorArtifacts || {})) {
        if (artifact && hasAcceptedMapping(artifact)) {
            errors.push(`${key} must not contain accepted mapping or raw-write-ready state`);
        }
    }

    return { ok: errors.length === 0, errors };
}

function buildDuplicateContext(targets = []) {
    return {
        target_id: countBy(targets.map(target => target.target_id)),
        match_id: countBy(targets.map(target => target.match_id)),
        source_inventory_record_key: countBy(targets.map(target => target.source_inventory_record_key)),
        source_url_fragment_external_id: countBy(targets.map(target => target.source_url_fragment_external_id)),
    };
}

function isDuplicate(counts, keyName, value) {
    const key = normalizeText(value);
    return Boolean(key && (counts[keyName].get(key) || 0) > 1);
}

function buildTargetReviewEntry(
    target = {},
    verificationResult = {},
    duplicates = {},
    sourceRecord = null,
    context = {}
) {
    const blockers = [];
    const missingUrlEvidence =
        !normalizeText(target.source_page_url) ||
        !normalizeText(target.source_page_url_base) ||
        !normalizeText(target.source_url_fragment_external_id) ||
        !normalizeText(target.source_inventory_record_key);
    const missingScheduleMetadata =
        !normalizeText(target.schedule_date) ||
        !normalizeText(target.schedule_home_team) ||
        !normalizeText(target.schedule_away_team);

    if (verificationResult.verification_status !== 'verified') blockers.push('verification_not_passed');
    if (missingUrlEvidence) blockers.push('missing_source_url_evidence');
    if (normalizeText(target.source_url_fragment_external_id) !== normalizeText(target.schedule_external_id)) {
        blockers.push('fragment_schedule_mismatch');
    }
    if (
        isDuplicate(duplicates, 'target_id', target.target_id) ||
        isDuplicate(duplicates, 'match_id', target.match_id)
    ) {
        blockers.push('duplicate_target_or_match_id');
    }
    if (isDuplicate(duplicates, 'source_inventory_record_key', target.source_inventory_record_key)) {
        blockers.push('duplicate_source_key');
    }
    if (isDuplicate(duplicates, 'source_url_fragment_external_id', target.source_url_fragment_external_id)) {
        blockers.push('duplicate_fragment_external_id');
    }
    if (missingScheduleMetadata) blockers.push('schedule_team_date_mismatch');
    if (target.regeneration_status !== 'regenerated_no_write') blockers.push('regeneration_status_not_clean');
    if (Array.isArray(target.regeneration_blockers) && target.regeneration_blockers.length > 0) {
        blockers.push('regeneration_blockers_present');
    }
    if (target.raw_write_ready_for_execution === true) blockers.push('raw_write_target_unexpectedly_ready');
    if (!sourceRecord) blockers.push('source_inventory_record_missing');
    if (context.rawWriteRunnerBlocked !== true) blockers.push('raw_write_runner_unexpectedly_ready');

    const reviewStatus = blockers.length === 0 ? 'review_ready' : 'review_blocked';
    return {
        target_id: target.target_id || null,
        match_id: target.match_id || null,
        schedule_external_id: target.schedule_external_id || null,
        source_page_url: target.source_page_url || null,
        source_page_url_base: target.source_page_url_base || null,
        source_url_fragment_external_id: target.source_url_fragment_external_id || null,
        schedule_date: target.schedule_date || null,
        schedule_home_team: target.schedule_home_team || null,
        schedule_away_team: target.schedule_away_team || null,
        source_inventory_record_key: target.source_inventory_record_key || null,
        verification_status: verificationResult.verification_status || 'unknown',
        review_status: reviewStatus,
        acceptance_status: 'not_accepted_planning_only',
        reviewer_required: true,
        accepted_by: null,
        accepted_at: null,
        acceptance_blockers: blockers,
        future_acceptance_requirements: [
            'human_review_execution_required',
            'accepted_by_required_in_future_execution',
            'accepted_at_required_in_future_execution',
            'acceptance_evidence_summary_required_in_future_execution',
        ],
        acceptance_evidence_summary: {
            source_url_evidence_complete: missingUrlEvidence === false,
            source_url_fragment_external_id_matches_schedule_external_id:
                normalizeText(target.source_url_fragment_external_id) === normalizeText(target.schedule_external_id),
            source_inventory_record_present: Boolean(sourceRecord),
            schedule_metadata_present: missingScheduleMetadata === false,
            verification_passed: verificationResult.verification_status === 'verified',
            raw_write_runner_blocked: context.rawWriteRunnerBlocked === true,
            human_review_executed: false,
        },
        raw_write_eligible_after_acceptance: false,
    };
}

function analyzeAcceptanceReviewCandidates(l2v3acArtifact = {}, l2v3aaArtifact = {}, l2v3yArtifact = {}) {
    const targets = Array.isArray(l2v3aaArtifact.enriched_targets) ? l2v3aaArtifact.enriched_targets : [];
    const verificationResults = Array.isArray(l2v3acArtifact.verification_analysis?.target_results)
        ? l2v3acArtifact.verification_analysis.target_results
        : [];
    const sourceRecords = Array.isArray(l2v3yArtifact.source_inventory_metadata_records)
        ? l2v3yArtifact.source_inventory_metadata_records
        : [];
    const verificationByTargetId = indexBy(verificationResults, 'target_id');
    const sourceByTargetId = indexBy(sourceRecords, 'target_id');
    const duplicates = buildDuplicateContext(targets);
    const context = { rawWriteRunnerBlocked: l2v3acArtifact.raw_write_runner_blocked === true };
    const reviewPlanEntries = targets.map(target =>
        buildTargetReviewEntry(
            target,
            verificationByTargetId.get(normalizeText(target.target_id)) || {},
            duplicates,
            sourceByTargetId.get(normalizeText(target.target_id)) || null,
            context
        )
    );
    const reviewReadyCount = reviewPlanEntries.filter(entry => entry.review_status === 'review_ready').length;
    const reviewBlockedCount = reviewPlanEntries.filter(entry => entry.review_status === 'review_blocked').length;
    return {
        verification_passed_target_count: Number(l2v3acArtifact.verified_target_count || 0),
        acceptance_review_candidate_count: reviewPlanEntries.length,
        review_ready_count: reviewReadyCount,
        review_blocked_count: reviewBlockedCount,
        review_plan_entries: reviewPlanEntries,
    };
}

function determineOutcome(candidateAnalysis = {}) {
    if (candidateAnalysis.acceptance_review_candidate_count !== EXPECTED_TARGET_COUNT) {
        return CONTINUE_PLANNING_NEXT_STEP;
    }
    if (candidateAnalysis.review_blocked_count > 0) {
        return BLOCKER_NEXT_STEP;
    }
    return PASS_NEXT_STEP;
}

function buildArtifact({
    manifest = {},
    l2v3acArtifact = {},
    l2v3mArtifact = {},
    inputAnalysis = [],
    candidateAnalysis = {},
    generatedAt = GENERATED_AT,
} = {}) {
    const outcome = determineOutcome(candidateAnalysis);
    return {
        artifact_type: 'identity_mapping_acceptance_review_plan',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3AC',
        generated_at: generatedAt,
        planning_only: true,
        no_write: true,
        source_controlled_artifacts_only: true,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        network_request_performed: false,
        db_write_performed: false,
        raw_insert_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        browser_proxy_captcha_bypass_performed: false,
        acceptance_execution_performed: false,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        human_review_required: true,
        planning_status: ARTIFACT_STATUS,
        reviewed_input_artifact_count: inputAnalysis.filter(item => item.count_as_artifact && item.exists).length,
        verification_passed_target_count: candidateAnalysis.verification_passed_target_count,
        acceptance_review_candidate_count: candidateAnalysis.acceptance_review_candidate_count,
        review_ready_count: candidateAnalysis.review_ready_count,
        review_blocked_count: candidateAnalysis.review_blocked_count,
        planned_acceptance_rule_count: PLANNED_ACCEPTANCE_RULES.length,
        planned_blocking_rule_count: PLANNED_BLOCKING_RULES.length,
        review_statuses: ACCEPTANCE_REVIEW_STATUSES,
        planned_acceptance_rules: PLANNED_ACCEPTANCE_RULES,
        planned_blocking_rules: PLANNED_BLOCKING_RULES,
        review_plan_entries: candidateAnalysis.review_plan_entries,
        input_analysis: inputAnalysis,
        upstream_context: {
            current_manifest_next_required_step: manifest.next_required_step || null,
            l2v3ac_verification_status: l2v3acArtifact.verification_status || null,
            l2v3ac_raw_write_runner_blocked: l2v3acArtifact.raw_write_runner_blocked === true,
            l2v3m_integrated_with_raw_write_guard: l2v3mArtifact.integrated_with_raw_write_guard === true,
            l2v3m_blocking_statuses: Array.isArray(l2v3mArtifact.blocking_statuses)
                ? l2v3mArtifact.blocking_statuses
                : [],
        },
        safety_contract: {
            planning_result_is_not_accepted_mapping: true,
            review_ready_is_not_accepted: true,
            verification_passed_is_not_accepted_mapping: true,
            source_url_fragment_external_id_match_is_not_accepted_mapping: true,
            identity_evidence_complete_does_not_imply_raw_write_ready_for_execution: true,
            identity_mapping_acceptance_execution_requires_separate_authorization: true,
            baseline_acceptance_requires_separate_authorization: true,
            final_db_write_authorization_required: true,
        },
        recommended_next_step: outcome.recommended_next_step,
        next_required_step: outcome.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3ad_planning_status: artifact.planning_status,
        identity_mapping_acceptance_review_planning_status: artifact.planning_status,
        phase_5_21_l2v3ad_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ad_report_path: REPORT_PATH,
        verification_passed_target_count: artifact.verification_passed_target_count,
        acceptance_review_candidate_count: artifact.acceptance_review_candidate_count,
        review_ready_count: artifact.review_ready_count,
        review_blocked_count: artifact.review_blocked_count,
        planned_acceptance_rule_count: artifact.planned_acceptance_rule_count,
        human_review_required: true,
        acceptance_execution_performed: false,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance_execution: true,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AD

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- planning_only=true
- source_controlled_artifacts_only=true
- live_fetch_performed=false
- detail_fetch_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- acceptance_execution_performed=false
- identity_mapping_acceptance_performed=false
- baseline_acceptance_performed=false
- raw_write_retry_performed=false

## Planning Summary

- planning_status=${artifact.planning_status}
- reviewed_input_artifact_count=${artifact.reviewed_input_artifact_count}
- verification_passed_target_count=${artifact.verification_passed_target_count}
- acceptance_review_candidate_count=${artifact.acceptance_review_candidate_count}
- review_ready_count=${artifact.review_ready_count}
- review_blocked_count=${artifact.review_blocked_count}
- planned_acceptance_rule_count=${artifact.planned_acceptance_rule_count}
- planned_blocking_rule_count=${artifact.planned_blocking_rule_count}
- human_review_required=true
- accepted_mapping_count=0
- raw_write_ready_for_execution=false

## Review Statuses

${artifact.review_statuses.map(status => `- ${status}`).join('\n')}

## Planned Acceptance Rules

${artifact.planned_acceptance_rules.map((rule, index) => `- ${index + 1}. ${rule}`).join('\n')}

## Planned Blocking Rules

${artifact.planned_blocking_rules.map(rule => `- ${rule}`).join('\n')}

## Candidate Summary

- review_ready_count=${artifact.review_ready_count}
- review_blocked_count=${artifact.review_blocked_count}
- review_ready_is_not_accepted=true
- raw_write_eligible_after_acceptance=false
- acceptance_execution_performed=false

## Input Artifacts

${artifact.input_analysis
    .map(
        item =>
            `- ${item.role}: ${item.path} (exists=${item.exists === true}, artifact=${item.count_as_artifact === true})`
    )
    .join('\n')}

## Safety Contract

- identity mapping acceptance review planning is not acceptance execution.
- review_ready is not accepted mapping.
- verification passed is not accepted mapping.
- source URL fragment match is not accepted mapping.
- identity evidence completeness does not imply raw_write_ready_for_execution.
- accepted_mapping_count remains 0.
- raw_write_ready_for_execution remains false.
- baseline acceptance remains false.
- raw write retry remains false.
- separate identity mapping acceptance execution is required.
- separate baseline acceptance is required.
- separate final DB-write authorization is required.

## Next Step

${artifact.recommended_next_step}
`;
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3acArtifact: dependencies.l2v3acArtifact || readJsonFile(L2V3AC_ARTIFACT_PATH),
        l2v3aaArtifact: dependencies.l2v3aaArtifact || readJsonFile(L2V3AA_ARTIFACT_PATH),
        l2v3yArtifact: dependencies.l2v3yArtifact || readJsonFile(L2V3Y_ARTIFACT_PATH),
        l2v3mArtifact: dependencies.l2v3mArtifact || readJsonFile(L2V3M_ARTIFACT_PATH),
        priorArtifacts: dependencies.priorArtifacts || {
            l2v3iArtifact: readJsonFile(L2V3I_ARTIFACT_PATH),
            l2v3jArtifact: readJsonFile(L2V3J_ARTIFACT_PATH),
            l2v3kArtifact: readJsonFile(L2V3K_ARTIFACT_PATH),
        },
    };
}

function runIdentityMappingAcceptanceReviewPlan(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(
        loaded.manifest,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact,
        loaded.l2v3mArtifact,
        loaded.priorArtifacts
    );
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const inputAnalysis = analyzeInputPaths(INPUT_PATHS, dependencies);
    const candidateAnalysis = analyzeAcceptanceReviewCandidates(
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact
    );
    const artifact = buildArtifact({
        manifest: loaded.manifest,
        l2v3acArtifact: loaded.l2v3acArtifact,
        l2v3mArtifact: loaded.l2v3mArtifact,
        inputAnalysis,
        candidateAnalysis,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
    });
    const report = buildReport(artifact);
    const updatedManifest = updateManifestMetadata(loaded.manifest, artifact);

    if (dependencies.writeFiles !== false) {
        const writeJson = dependencies.writeJsonFile || writeJsonFile;
        const writeText = dependencies.writeTextFile || writeTextFile;
        writeJson(dependencies.artifactOutputPath || ARTIFACT_OUTPUT_PATH, artifact);
        writeText(dependencies.reportOutputPath || REPORT_PATH, report);
        writeJson(dependencies.manifestOutputPath || MANIFEST_PATH, updatedManifest);
    }

    return { ok: true, status: 0, artifact, report, updated_manifest: updatedManifest };
}

function helpText() {
    return `L2V3AD is an identity mapping acceptance review planning-only phase.

Allowed:
  --write-files=false

Blocked:
  live fetch, detail fetch, network, DB write, raw write, matches write,
  matches.external_id write, identity mapping acceptance, baseline acceptance,
  raw write retry, parser/features/training/prediction, browser/proxy runtime,
  and full payload printing/saving.
`;
}

function runCli(argv = process.argv.slice(2), io = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    const options = parseArgs(argv);
    if (options.help) {
        stdout(helpText());
        return 0;
    }
    const cliGate = validateCliOptions(options);
    if (!cliGate.ok) {
        stdout(`${JSON.stringify({ ok: false, errors: cliGate.errors }, null, 2)}\n`);
        return 2;
    }
    const result = runIdentityMappingAcceptanceReviewPlan({ writeFiles: options.writeFiles !== false });
    if (!result.ok) {
        stdout(`${JSON.stringify({ ok: false, errors: result.errors }, null, 2)}\n`);
        return result.status || 1;
    }
    stdout(
        `${JSON.stringify(
            {
                ok: true,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_PATH,
                planning_status: result.artifact.planning_status,
                verification_passed_target_count: result.artifact.verification_passed_target_count,
                acceptance_review_candidate_count: result.artifact.acceptance_review_candidate_count,
                review_ready_count: result.artifact.review_ready_count,
                review_blocked_count: result.artifact.review_blocked_count,
                accepted_mapping_count: result.artifact.accepted_mapping_count,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
                recommended_next_step: result.artifact.recommended_next_step,
            },
            null,
            2
        )}\n`
    );
    return 0;
}

module.exports = {
    PHASE,
    PHASE_NAME,
    ARTIFACT_STATUS,
    MANIFEST_PATH,
    L2V3AC_ARTIFACT_PATH,
    L2V3AA_ARTIFACT_PATH,
    L2V3Y_ARTIFACT_PATH,
    L2V3M_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    ACCEPTANCE_REVIEW_STATUSES,
    PLANNED_ACCEPTANCE_RULES,
    PLANNED_BLOCKING_RULES,
    parseArgs,
    validateCliOptions,
    validateInputs,
    analyzeAcceptanceReviewCandidates,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    runIdentityMappingAcceptanceReviewPlan,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
