#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ahPlan = require('./pageprops_v2_final_db_write_authorization_plan');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AI';
const PHASE_NAME = 'final_db_write_authorization_execution';
const ARTIFACT_STATUS = 'completed_final_db_write_authorization_execution';
const BLOCKED_STATUS = 'blocked_final_db_write_authorization_execution';
const DEFAULT_AUTHORIZED_BY = 'codex_automation_on_user_authorization';
const EXPECTED_TARGET_COUNT = 50;
const EXPECTED_MATCHES_COUNT = 60;
const EXPECTED_RAW_MATCH_DATA_BEFORE_COUNT = 18;
const EXPECTED_RAW_MATCH_DATA_AFTER_COUNT = 68;
const EXPECTED_PAGEPROPS_V2_BEFORE_COUNT = 8;
const EXPECTED_EXISTING_CANDIDATE_V2_RAW_ROWS = 0;
const EXPECTED_BOOKMAKER_ODDS_HISTORY_COUNT = 2;
const EXPECTED_L3_FEATURES_COUNT = 2;
const EXPECTED_MATCH_FEATURES_TRAINING_COUNT = 2;
const EXPECTED_PREDICTIONS_COUNT = 2;
const RAW_DATA_VERSION = 'fotmob_pageprops_v2';
const MANIFEST_PATH = ahPlan.MANIFEST_PATH;
const L2V3AH_PLAN_PATH = ahPlan.ARTIFACT_OUTPUT_PATH;
const L2V3AG_ARTIFACT_PATH = ahPlan.L2V3AG_ARTIFACT_PATH;
const L2V3AE_ARTIFACT_PATH = ahPlan.L2V3AE_ARTIFACT_PATH;
const L2V3AC_ARTIFACT_PATH = ahPlan.L2V3AC_ARTIFACT_PATH;
const L2V3AA_ARTIFACT_PATH = ahPlan.L2V3AA_ARTIFACT_PATH;
const L2V3Y_ARTIFACT_PATH = ahPlan.L2V3Y_ARTIFACT_PATH;
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.final_db_write_authorization_result.phase521l2v3ai.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AI.md';
const AUTHORIZED_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AJ: controlled raw_match_data write execution planning',
    next_required_step: 'controlled_raw_match_data_write_execution_planning',
});
const BLOCKED_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AJ: final DB-write authorization blocker resolution',
    next_required_step: 'final_db_write_authorization_blocker_resolution',
});
const CONTINUED_PLANNING_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AJ: continued final DB-write authorization planning',
    next_required_step: 'continued_final_db_write_authorization_planning',
});
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
    'allowRawWriteRetry',
    'executeRawWrite',
    'commitRawWrite',
    'markRawWriteReady',
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

function currentTimestamp() {
    return new Date().toISOString();
}

function numericOrNaN(value) {
    if (value === null || value === undefined || value === '') return Number.NaN;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
    return { value: true, consumedNext: false };
}

function cliName(flagName) {
    return flagName.replace(/[A-Z]/g, character => `-${character.toLowerCase()}`);
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        writeFiles: true,
        finalDbWriteHumanReviewSatisfied: false,
        authorizedBy: DEFAULT_AUTHORIZED_BY,
        authorizedAt: null,
        dbSafetyStatusFile: null,
        help: false,
        unknown: [],
    };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
        'final-db-write-human-review-satisfied': 'finalDbWriteHumanReviewSatisfied',
        final_db_write_human_review_satisfied: 'finalDbWriteHumanReviewSatisfied',
        'human-review-satisfied': 'finalDbWriteHumanReviewSatisfied',
        human_review_satisfied: 'finalDbWriteHumanReviewSatisfied',
        'authorized-by': 'authorizedBy',
        authorized_by: 'authorizedBy',
        'authorized-at': 'authorizedAt',
        authorized_at: 'authorizedAt',
        'db-safety-status-file': 'dbSafetyStatusFile',
        db_safety_status_file: 'dbSafetyStatusFile',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-network': 'allowNetwork',
        allow_network: 'allowNetwork',
        'allow-live-fetch': 'allowLiveFetch',
        allow_live_fetch: 'allowLiveFetch',
        'allow-detail-fetch': 'allowDetailFetch',
        allow_detail_fetch: 'allowDetailFetch',
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
        'allow-raw-write-retry': 'allowRawWriteRetry',
        allow_raw_write_retry: 'allowRawWriteRetry',
        'execute-raw-write': 'executeRawWrite',
        execute_raw_write: 'executeRawWrite',
        'commit-raw-write': 'commitRawWrite',
        commit_raw_write: 'commitRawWrite',
        'mark-raw-write-ready': 'markRawWriteReady',
        mark_raw_write_ready: 'markRawWriteReady',
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
    const booleanKeys = new Set(['writeFiles', 'finalDbWriteHumanReviewSatisfied', 'help', ...BLOCKED_TRUE_FLAGS]);

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
    if (normalizeBooleanFlag(options.finalDbWriteHumanReviewSatisfied, false) === true) {
        if (!normalizeText(options.authorizedBy)) errors.push('authorized-by is required');
    }
    return { ok: errors.length === 0, errors };
}

function hasUnsafeWriteState(value = {}, options = {}) {
    const allowBaselineAcceptance = options.allowBaselineAcceptance === true;
    const allowFinalAuthorization = options.allowFinalAuthorization === true;
    return (
        value.db_write_performed === true ||
        value.raw_insert_performed === true ||
        value.raw_match_data_insert_performed === true ||
        value.matches_write_performed === true ||
        value.matches_external_id_modified === true ||
        value.raw_write_retry_performed === true ||
        value.raw_write_ready_for_execution === true ||
        (allowFinalAuthorization !== true && value.final_db_write_authorization_performed === true) ||
        (allowFinalAuthorization !== true && value.raw_write_authorization_performed === true) ||
        (allowBaselineAcceptance !== true && value.baseline_acceptance_performed === true)
    );
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3ahPlan: dependencies.l2v3ahPlan || readJsonFile(L2V3AH_PLAN_PATH),
        l2v3agArtifact: dependencies.l2v3agArtifact || readJsonFile(L2V3AG_ARTIFACT_PATH),
        l2v3aeArtifact: dependencies.l2v3aeArtifact || readJsonFile(L2V3AE_ARTIFACT_PATH),
        l2v3acArtifact: dependencies.l2v3acArtifact || readJsonFile(L2V3AC_ARTIFACT_PATH),
        l2v3aaArtifact: dependencies.l2v3aaArtifact || readJsonFile(L2V3AA_ARTIFACT_PATH),
        l2v3yArtifact: dependencies.l2v3yArtifact || readJsonFile(L2V3Y_ARTIFACT_PATH),
    };
}

function validateInputs(
    manifest = {},
    l2v3ahPlan = {},
    l2v3agArtifact = {},
    l2v3aeArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {}
) {
    const errors = [];
    const advancedNextSteps = new Set([
        'controlled_raw_match_data_write_execution_planning',
        'controlled_raw_match_data_write_execution',
        'controlled_raw_write_execution_blocker_resolution',
        'continued_controlled_raw_write_planning',
        'controlled_payload_source_declaration_planning',
        'controlled_payload_source_declaration_execution',
        'controlled_no_write_payload_recapture_planning',
    ]);
    const alreadyExecuted =
        normalizeText(manifest.phase_5_21_l2v3ai_execution_status) === ARTIFACT_STATUS &&
        advancedNextSteps.has(normalizeText(manifest.next_required_step));
    if (normalizeText(manifest.next_required_step) !== 'final_db_write_authorization_execution' && !alreadyExecuted) {
        errors.push('manifest next_required_step must be final_db_write_authorization_execution');
    }
    if (normalizeText(manifest.phase_5_21_l2v3ah_planning_status) !== ahPlan.ARTIFACT_STATUS) {
        errors.push(
            'manifest phase_5_21_l2v3ah_planning_status must be completed_final_db_write_authorization_planning'
        );
    }
    if (Number(manifest.phase_5_21_l2v3ah_final_authorization_ready_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('manifest phase_5_21_l2v3ah_final_authorization_ready_count must be 50');
    }
    if (hasUnsafeWriteState(manifest, { allowBaselineAcceptance: true, allowFinalAuthorization: alreadyExecuted })) {
        errors.push('manifest must not contain DB-write, raw-write, raw-ready, or premature final authorization state');
    }

    if (l2v3ahPlan.proposal_phase !== 'Phase 5.21L2V3AH') errors.push('L2V3AH plan artifact is required');
    if (l2v3ahPlan.phase_name !== 'final_db_write_authorization_planning') {
        errors.push('L2V3AH phase_name must be final_db_write_authorization_planning');
    }
    if (Number(l2v3ahPlan.identity_mapping_accepted_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AH identity_mapping_accepted_count must be 50');
    }
    if (Number(l2v3ahPlan.baseline_accepted_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AH baseline_accepted_count must be 50');
    }
    if (Number(l2v3ahPlan.no_write_verified_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AH no_write_verified_target_count must be 50');
    }
    if (Number(l2v3ahPlan.final_authorization_ready_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AH final_authorization_ready_count must be 50');
    }
    if (Number(l2v3ahPlan.final_authorization_blocked_count || 0) !== 0) {
        errors.push('L2V3AH final_authorization_blocked_count must be 0');
    }
    if (l2v3ahPlan.final_db_write_reviewer_required !== true) {
        errors.push('L2V3AH final_db_write_reviewer_required must be true');
    }
    if (l2v3ahPlan.final_db_write_authorization_execution_performed !== false) {
        errors.push('L2V3AH final_db_write_authorization_execution_performed must be false');
    }
    if (hasUnsafeWriteState(l2v3ahPlan, { allowBaselineAcceptance: true })) {
        errors.push('L2V3AH plan must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }

    if (l2v3agArtifact.proposal_phase !== 'Phase 5.21L2V3AG') errors.push('L2V3AG artifact is required');
    if (l2v3agArtifact.baseline_acceptance_performed !== true) {
        errors.push('L2V3AG baseline_acceptance_performed must be true');
    }
    if (Number(l2v3agArtifact.baseline_accepted_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AG baseline_accepted_count must be 50');
    }
    if (hasUnsafeWriteState(l2v3agArtifact, { allowBaselineAcceptance: true })) {
        errors.push('L2V3AG artifact must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }

    if (l2v3aeArtifact.proposal_phase !== 'Phase 5.21L2V3AE') errors.push('L2V3AE artifact is required');
    if (Number(l2v3aeArtifact.accepted_mapping_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AE accepted_mapping_count must be 50');
    }
    if (hasUnsafeWriteState(l2v3aeArtifact)) {
        errors.push('L2V3AE artifact must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }

    if (l2v3acArtifact.proposal_phase !== 'Phase 5.21L2V3AC') errors.push('L2V3AC artifact is required');
    if (l2v3acArtifact.verification_status !== 'passed_no_write_source_controlled') {
        errors.push('L2V3AC verification_status must be passed_no_write_source_controlled');
    }
    if (Number(l2v3acArtifact.verified_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AC verified_target_count must be 50');
    }
    if (l2v3acArtifact.raw_write_runner_blocked !== true) errors.push('L2V3AC raw_write_runner_blocked must be true');
    if (hasUnsafeWriteState(l2v3acArtifact)) {
        errors.push('L2V3AC artifact must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }

    if (Number(l2v3aaArtifact.regenerated_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AA regenerated_target_count must be 50');
    }
    if (hasUnsafeWriteState(l2v3aaArtifact)) {
        errors.push('L2V3AA artifact must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }
    if (Number(l2v3yArtifact.candidate_scope_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3Y candidate_scope_count must be 50');
    }
    if (hasUnsafeWriteState(l2v3yArtifact)) {
        errors.push('L2V3Y artifact must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }
    return { ok: errors.length === 0, errors };
}

function buildDbSafetyStatus(overrides = {}) {
    const matchesCount = numericOrNaN(overrides.matches_count);
    const rawMatchDataCount = numericOrNaN(overrides.raw_match_data_count);
    const fotmobPagepropsV2Count = numericOrNaN(overrides.fotmob_pageprops_v2_count);
    const candidateV2ExistingRows = numericOrNaN(
        overrides.candidate_v2_existing_rows ?? overrides.candidate_v2_raw_rows_existing_count
    );
    const candidateMatchesMissingFkCount = numericOrNaN(
        overrides.candidate_matches_missing_fk_count ?? overrides.candidate_matches_missing_fk
    );
    const bookmakerOddsHistoryCount = numericOrNaN(overrides.bookmaker_odds_history_count);
    const l3FeaturesCount = numericOrNaN(overrides.l3_features_count);
    const matchFeaturesTrainingCount = numericOrNaN(overrides.match_features_training_count);
    const predictionsCount = numericOrNaN(overrides.predictions_count);
    const derivedProtectedTablesUnchanged =
        matchesCount === EXPECTED_MATCHES_COUNT &&
        bookmakerOddsHistoryCount === EXPECTED_BOOKMAKER_ODDS_HISTORY_COUNT &&
        l3FeaturesCount === EXPECTED_L3_FEATURES_COUNT &&
        matchFeaturesTrainingCount === EXPECTED_MATCH_FEATURES_TRAINING_COUNT &&
        predictionsCount === EXPECTED_PREDICTIONS_COUNT;
    return {
        source: overrides.source || 'preflight_select_only_row_count_and_schema_guard',
        checked_at: normalizeText(overrides.checked_at) || null,
        select_only: true,
        db_available: overrides.db_available === true,
        matches_count: matchesCount,
        raw_match_data_count: rawMatchDataCount,
        fotmob_pageprops_v2_count: fotmobPagepropsV2Count,
        candidate_v2_existing_rows: candidateV2ExistingRows,
        candidate_matches_missing_fk_count: candidateMatchesMissingFkCount,
        bookmaker_odds_history_count: bookmakerOddsHistoryCount,
        l3_features_count: l3FeaturesCount,
        match_features_training_count: matchFeaturesTrainingCount,
        predictions_count: predictionsCount,
        protected_tables_unchanged:
            typeof overrides.protected_tables_unchanged === 'boolean'
                ? overrides.protected_tables_unchanged
                : derivedProtectedTablesUnchanged,
        unique_match_id_data_version_present: overrides.unique_match_id_data_version_present === true,
        legacy_unique_match_id_absent: overrides.legacy_unique_match_id_absent === true,
        fk_prerequisite_satisfied:
            typeof overrides.fk_prerequisite_satisfied === 'boolean'
                ? overrides.fk_prerequisite_satisfied
                : candidateMatchesMissingFkCount === 0,
        hidden_bidi_resolved: overrides.hidden_bidi_resolved === true,
        full_payload_scan_clean: overrides.full_payload_scan_clean === true,
        ci_green: overrides.ci_green === true,
        raw_write_runner_guard_ok: overrides.raw_write_runner_guard_ok,
        raw_write_runner_guard_error_count: numericOrNaN(overrides.raw_write_runner_guard_error_count),
    };
}

function dbSafetyBlockers(dbSafety = {}) {
    const blockers = [];
    if (dbSafety.db_available !== true) blockers.push('db_unavailable');
    if (dbSafety.matches_count !== EXPECTED_MATCHES_COUNT) blockers.push('matches_count_mismatch');
    if (dbSafety.raw_match_data_count !== EXPECTED_RAW_MATCH_DATA_BEFORE_COUNT) {
        blockers.push('raw_match_data_before_count_mismatch');
    }
    if (dbSafety.fotmob_pageprops_v2_count !== EXPECTED_PAGEPROPS_V2_BEFORE_COUNT) {
        blockers.push('fotmob_pageprops_v2_count_mismatch');
    }
    if (dbSafety.candidate_v2_existing_rows !== EXPECTED_EXISTING_CANDIDATE_V2_RAW_ROWS) {
        blockers.push('candidate_v2_raw_rows_already_exist');
    }
    if (
        dbSafety.bookmaker_odds_history_count !== EXPECTED_BOOKMAKER_ODDS_HISTORY_COUNT ||
        dbSafety.l3_features_count !== EXPECTED_L3_FEATURES_COUNT ||
        dbSafety.match_features_training_count !== EXPECTED_MATCH_FEATURES_TRAINING_COUNT ||
        dbSafety.predictions_count !== EXPECTED_PREDICTIONS_COUNT
    ) {
        blockers.push('protected_table_drift');
    }
    if (dbSafety.unique_match_id_data_version_present !== true || dbSafety.legacy_unique_match_id_absent !== true) {
        blockers.push('unique_constraint_missing_or_wrong');
    }
    if (dbSafety.fk_prerequisite_satisfied !== true) blockers.push('fk_prerequisite_not_satisfied');
    if (dbSafety.protected_tables_unchanged !== true) blockers.push('protected_table_drift');
    if (dbSafety.hidden_bidi_resolved !== true) blockers.push('hidden_bidi_unresolved');
    if (dbSafety.full_payload_scan_clean !== true) blockers.push('full_payload_leak_detected');
    if (dbSafety.ci_green !== true) blockers.push('ci_not_green');
    if (dbSafety.raw_write_runner_guard_ok !== false) blockers.push('raw_write_runner_unexpectedly_ready');
    return blockers;
}

function buildExecutionEntry(planEntry = {}, globalBlockers = [], options = {}) {
    const blockers = [...globalBlockers];
    if (planEntry.final_authorization_status !== 'final_authorization_ready') {
        blockers.push('plan_entry_not_final_authorization_ready');
    }
    if (planEntry.final_db_write_authorization_performed === true) {
        blockers.push('final_authorization_already_performed_in_plan_entry');
    }
    if (planEntry.raw_write_ready_for_execution === true) blockers.push('plan_entry_raw_write_ready_unexpectedly_true');
    if (planEntry.raw_write_retry_performed === true) blockers.push('plan_entry_raw_write_retry_already_performed');
    if (Array.isArray(planEntry.final_authorization_blockers) && planEntry.final_authorization_blockers.length > 0) {
        blockers.push('unresolved_planning_blocker');
    }
    if (options.finalDbWriteHumanReviewSatisfied !== true) blockers.push('human_final_authorization_missing');

    const uniqueBlockers = [...new Set(blockers)];
    const accepted = uniqueBlockers.length === 0;
    return {
        target_id: planEntry.target_id || null,
        match_id: planEntry.match_id || null,
        schedule_external_id: planEntry.schedule_external_id || null,
        source_page_url: planEntry.source_page_url || null,
        source_page_url_base: planEntry.source_page_url_base || null,
        source_url_fragment_external_id: planEntry.source_url_fragment_external_id || null,
        source_inventory_record_key: planEntry.source_inventory_record_key || null,
        raw_data_version: RAW_DATA_VERSION,
        final_authorization_status: accepted ? 'final_authorization_accepted' : 'final_authorization_blocked',
        final_db_write_authorization_execution_performed: true,
        final_db_write_authorization_performed: accepted,
        final_db_write_authorized: accepted,
        authorized_by: accepted ? options.authorizedBy : null,
        authorized_at: accepted ? options.authorizedAt : null,
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        requires_separate_raw_write_execution: true,
        final_authorization_blockers: uniqueBlockers,
        authorized_write_scope: {
            table: 'raw_match_data',
            data_version: RAW_DATA_VERSION,
            target_match_id: planEntry.match_id || null,
            insert_only: true,
            matches_write_allowed: false,
            matches_external_id_write_allowed: false,
            odds_features_training_prediction_write_allowed: false,
            schema_migration_allowed: false,
            raw_write_execution_allowed_in_this_phase: false,
        },
        authorization_evidence_summary: {
            planning_entry_ready: planEntry.final_authorization_status === 'final_authorization_ready',
            identity_mapping_accepted:
                planEntry.final_authorization_evidence_summary?.identity_mapping_accepted === true,
            baseline_accepted: planEntry.final_authorization_evidence_summary?.baseline_accepted === true,
            no_write_verification_passed:
                planEntry.final_authorization_evidence_summary?.no_write_verification_passed === true,
            existing_candidate_v2_raw_rows_zero:
                planEntry.final_authorization_evidence_summary?.existing_candidate_v2_raw_rows_zero === true,
            raw_match_data_before_count_expected:
                planEntry.final_authorization_evidence_summary?.raw_match_data_before_count_expected === true,
            unique_match_id_data_version_present:
                planEntry.final_authorization_evidence_summary?.unique_match_id_data_version_present === true,
            legacy_unique_match_id_absent:
                planEntry.final_authorization_evidence_summary?.legacy_unique_match_id_absent === true,
            fk_prerequisite_satisfied:
                planEntry.final_authorization_evidence_summary?.fk_prerequisite_satisfied === true,
            protected_tables_unchanged:
                planEntry.final_authorization_evidence_summary?.protected_tables_unchanged === true,
            final_db_write_human_review_satisfied: options.finalDbWriteHumanReviewSatisfied === true,
            user_authorized_final_db_write_authorization_execution: options.finalDbWriteHumanReviewSatisfied === true,
            user_did_not_authorize_raw_write_execution_in_this_phase: true,
            db_write_attempted: false,
            raw_write_retry_attempted: false,
        },
    };
}

function executeFinalDbWriteAuthorization(l2v3ahPlan = {}, dbSafetyOverrides = {}, options = {}) {
    const dbSafetyStatus = buildDbSafetyStatus(dbSafetyOverrides);
    const globalBlockers = dbSafetyBlockers(dbSafetyStatus);
    const entries = (
        Array.isArray(l2v3ahPlan.final_authorization_entries) ? l2v3ahPlan.final_authorization_entries : []
    ).map(entry => buildExecutionEntry(entry, globalBlockers, options));
    const acceptedCount = entries.filter(entry => entry.final_db_write_authorization_performed === true).length;
    const blockedCount = entries.filter(
        entry => entry.final_authorization_status === 'final_authorization_blocked'
    ).length;
    return {
        db_safety_status: dbSafetyStatus,
        final_authorization_candidate_count: entries.length,
        final_authorization_reviewed_count: entries.length,
        final_authorization_accepted_count: acceptedCount,
        final_authorization_rejected_count: 0,
        final_authorization_blocked_count: blockedCount,
        final_authorization_blocker_count: entries.reduce(
            (sum, entry) => sum + entry.final_authorization_blockers.length,
            0
        ),
        authorization_evidence_summary_present_count: entries.filter(entry => entry.authorization_evidence_summary)
            .length,
        final_authorization_entries: entries,
    };
}

function determineOutcome(execution = {}, humanReviewSatisfied = false) {
    if (execution.final_authorization_candidate_count !== EXPECTED_TARGET_COUNT) return CONTINUED_PLANNING_NEXT_STEP;
    if (humanReviewSatisfied !== true || execution.final_authorization_blocked_count > 0) return BLOCKED_NEXT_STEP;
    if (execution.final_authorization_accepted_count === EXPECTED_TARGET_COUNT) return AUTHORIZED_NEXT_STEP;
    return BLOCKED_NEXT_STEP;
}

function buildArtifact({
    loaded = {},
    execution = {},
    finalDbWriteHumanReviewSatisfied = false,
    authorizedBy = DEFAULT_AUTHORIZED_BY,
    authorizedAt = null,
    generatedAt = null,
} = {}) {
    const outcome = determineOutcome(execution, finalDbWriteHumanReviewSatisfied);
    const authorizationPerformed =
        finalDbWriteHumanReviewSatisfied === true &&
        execution.final_authorization_accepted_count === EXPECTED_TARGET_COUNT &&
        execution.final_authorization_blocked_count === 0;
    return {
        artifact_type: 'final_db_write_authorization_execution_result',
        artifact_status: authorizationPerformed ? ARTIFACT_STATUS : BLOCKED_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3AH',
        source_plan_artifact_path: L2V3AH_PLAN_PATH,
        source_baseline_acceptance_result_path: L2V3AG_ARTIFACT_PATH,
        source_identity_mapping_acceptance_result_path: L2V3AE_ARTIFACT_PATH,
        source_no_write_verification_result_path: L2V3AC_ARTIFACT_PATH,
        generated_at: generatedAt,
        final_db_write_authorization_execution_only: true,
        no_write: true,
        source_controlled_artifacts_only: true,
        final_db_write_authorization_execution_performed: true,
        final_db_write_authorization_performed: authorizationPerformed,
        raw_write_authorization_performed: false,
        raw_write_execution_authorization_performed: false,
        final_db_write_human_review_required: true,
        final_db_write_human_review_satisfied: finalDbWriteHumanReviewSatisfied === true,
        authorized_by: authorizationPerformed ? authorizedBy : null,
        authorized_at: authorizationPerformed ? authorizedAt : null,
        authorization_evidence_summary_present: authorizationPerformed,
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
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        raw_write_ready_for_execution_semantics_decision:
            'kept_false_because_raw_write_execution_requires_separate_phase_and_runner_must_not_be_directly_unblocked',
        requires_separate_raw_write_execution: true,
        identity_mapping_accepted_count: Number(loaded.l2v3ahPlan?.identity_mapping_accepted_count || 0),
        baseline_accepted_count: Number(loaded.l2v3ahPlan?.baseline_accepted_count || 0),
        no_write_verified_target_count: Number(loaded.l2v3ahPlan?.no_write_verified_target_count || 0),
        final_authorization_candidate_count: execution.final_authorization_candidate_count,
        final_authorization_reviewed_count: execution.final_authorization_reviewed_count,
        final_authorization_accepted_count: execution.final_authorization_accepted_count,
        final_authorization_rejected_count: execution.final_authorization_rejected_count,
        final_authorization_blocked_count: execution.final_authorization_blocked_count,
        final_authorization_blocker_count: execution.final_authorization_blocker_count,
        baseline_acceptance_performed: true,
        expected_raw_match_data_before_count: EXPECTED_RAW_MATCH_DATA_BEFORE_COUNT,
        raw_match_data_before_count: execution.db_safety_status.raw_match_data_count,
        expected_raw_match_data_after_future_write: EXPECTED_RAW_MATCH_DATA_AFTER_COUNT,
        expected_raw_match_data_delta_count: EXPECTED_TARGET_COUNT,
        expected_fotmob_pageprops_v2_before_count: EXPECTED_PAGEPROPS_V2_BEFORE_COUNT,
        expected_fotmob_pageprops_v2_after_future_write: EXPECTED_PAGEPROPS_V2_BEFORE_COUNT + EXPECTED_TARGET_COUNT,
        candidate_v2_existing_rows: execution.db_safety_status.candidate_v2_existing_rows,
        raw_data_version: RAW_DATA_VERSION,
        db_safety_status: execution.db_safety_status,
        raw_write_runner_guard_status: {
            ok: execution.db_safety_status.raw_write_runner_guard_ok,
            error_count: execution.db_safety_status.raw_write_runner_guard_error_count,
            not_invoked_in_write_mode: true,
            remains_blocked_until_separate_raw_write_execution_authorization: true,
        },
        authorization_scope: {
            future_execution_scope_table: 'raw_match_data',
            future_execution_data_version: RAW_DATA_VERSION,
            future_execution_target_count: EXPECTED_TARGET_COUNT,
            future_execution_insert_only: true,
            future_execution_requires_transaction_controlled_insert: true,
            raw_write_execution_allowed_in_this_phase: false,
        },
        prohibited_execution_scope: {
            no_raw_match_data_insert: true,
            no_matches_write: true,
            no_matches_external_id_change: true,
            no_raw_write_retry: true,
            no_live_fetch: true,
            no_detail_fetch: true,
            no_network_request: true,
            no_schema_migration: true,
            no_parser_features_training_prediction: true,
            no_full_payload_output: true,
        },
        final_authorization_entries: execution.final_authorization_entries,
        authorization_evidence_summary: {
            user_authorized_final_db_write_authorization_execution: finalDbWriteHumanReviewSatisfied === true,
            user_did_not_authorize_raw_write_execution_in_this_phase: true,
            identity_mapping_accepted_count_is_50:
                Number(loaded.l2v3ahPlan?.identity_mapping_accepted_count || 0) === 50,
            baseline_accepted_count_is_50: Number(loaded.l2v3ahPlan?.baseline_accepted_count || 0) === 50,
            no_write_verified_target_count_is_50: Number(loaded.l2v3ahPlan?.no_write_verified_target_count || 0) === 50,
            candidate_v2_existing_rows_zero: execution.db_safety_status.candidate_v2_existing_rows === 0,
            raw_match_data_before_count_is_18: execution.db_safety_status.raw_match_data_count === 18,
            expected_future_after_count_is_68: EXPECTED_RAW_MATCH_DATA_AFTER_COUNT === 68,
            db_write_attempted: false,
            raw_write_retry_attempted: false,
        },
        safety_contract: {
            final_authorization_is_not_raw_write_execution: true,
            final_authorization_is_not_raw_write_execution_authorization_bypass: true,
            final_authorization_does_not_insert_raw_match_data: true,
            final_authorization_does_not_modify_matches: true,
            raw_write_retry_performed_remains_false: true,
            db_write_performed_remains_false: true,
            raw_match_data_insert_performed_remains_false: true,
            raw_write_ready_for_execution_remains_false: true,
            requires_separate_raw_write_execution: true,
        },
        recommended_next_step: outcome.recommended_next_step,
        next_required_step: outcome.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3ai_execution_status: artifact.artifact_status,
        final_db_write_authorization_execution_status: artifact.artifact_status,
        phase_5_21_l2v3ai_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ai_report_path: REPORT_PATH,
        final_db_write_authorization_execution_performed: true,
        final_db_write_authorization_performed: artifact.final_db_write_authorization_performed,
        raw_write_authorization_performed: false,
        raw_write_execution_authorization_performed: false,
        final_db_write_human_review_required: true,
        final_db_write_human_review_satisfied: artifact.final_db_write_human_review_satisfied,
        authorized_by: artifact.authorized_by,
        authorized_at: artifact.authorized_at,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        network_request_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3ai_identity_mapping_accepted_count: artifact.identity_mapping_accepted_count,
        phase_5_21_l2v3ai_baseline_accepted_count: artifact.baseline_accepted_count,
        phase_5_21_l2v3ai_no_write_verified_target_count: artifact.no_write_verified_target_count,
        phase_5_21_l2v3ai_final_authorization_candidate_count: artifact.final_authorization_candidate_count,
        phase_5_21_l2v3ai_final_authorization_reviewed_count: artifact.final_authorization_reviewed_count,
        phase_5_21_l2v3ai_final_authorization_accepted_count: artifact.final_authorization_accepted_count,
        phase_5_21_l2v3ai_final_authorization_rejected_count: artifact.final_authorization_rejected_count,
        phase_5_21_l2v3ai_final_authorization_blocked_count: artifact.final_authorization_blocked_count,
        candidate_v2_existing_rows: artifact.candidate_v2_existing_rows,
        raw_match_data_before_count: artifact.raw_match_data_before_count,
        expected_raw_match_data_after_future_write: artifact.expected_raw_match_data_after_future_write,
        requires_separate_raw_write_execution: true,
        final_authorization_is_not_raw_write_execution: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AI

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- final_db_write_authorization_execution_performed=true
- final_db_write_authorization_performed=${artifact.final_db_write_authorization_performed}
- final authorization, if performed, is not raw write execution.
- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- raw_write_retry_performed=false
- raw_write_ready_for_execution=false
- requires_separate_raw_write_execution=true

## Human Review

- final_db_write_human_review_required=true
- final_db_write_human_review_satisfied=${artifact.final_db_write_human_review_satisfied}
- authorized_by=${artifact.authorized_by || 'null'}
- authorized_at=${artifact.authorized_at || 'null'}
- user authorized final DB-write authorization execution.
- user did not authorize raw write retry or raw_match_data insert in this phase.

## Authorization Summary

- identity_mapping_accepted_count=${artifact.identity_mapping_accepted_count}
- baseline_accepted_count=${artifact.baseline_accepted_count}
- no_write_verified_target_count=${artifact.no_write_verified_target_count}
- final_authorization_candidate_count=${artifact.final_authorization_candidate_count}
- final_authorization_reviewed_count=${artifact.final_authorization_reviewed_count}
- final_authorization_accepted_count=${artifact.final_authorization_accepted_count}
- final_authorization_rejected_count=${artifact.final_authorization_rejected_count}
- final_authorization_blocked_count=${artifact.final_authorization_blocked_count}
- authorization_evidence_summary_present=${artifact.authorization_evidence_summary_present}

## DB Safety Snapshot

- candidate_v2_existing_rows=${artifact.candidate_v2_existing_rows}
- raw_match_data_before_count=${artifact.raw_match_data_before_count}
- expected_raw_match_data_after_future_write=${artifact.expected_raw_match_data_after_future_write}
- expected_fotmob_pageprops_v2_after_future_write=${artifact.expected_fotmob_pageprops_v2_after_future_write}
- UNIQUE(match_id,data_version)_present=${artifact.db_safety_status.unique_match_id_data_version_present}
- old_UNIQUE(match_id)_absent=${artifact.db_safety_status.legacy_unique_match_id_absent}
- fk_prerequisite_satisfied=${artifact.db_safety_status.fk_prerequisite_satisfied}
- protected_tables_unchanged=${artifact.db_safety_status.protected_tables_unchanged}

## Write Authorization Scope

- future_execution_scope_table=raw_match_data
- future_execution_data_version=${RAW_DATA_VERSION}
- future_execution_target_count=${EXPECTED_TARGET_COUNT}
- future_execution_insert_only=true
- future_execution_requires_transaction_controlled_insert=true

## Prohibited Execution Scope

- no_raw_match_data_insert=true
- no_matches_write=true
- no_matches_external_id_change=true
- no_raw_write_retry=true
- no_live_fetch=true
- no_detail_fetch=true
- no_network_request=true
- no_schema_migration=true
- no_parser_features_training_prediction=true
- no_full_payload_output=true

## Safety Contract

- final authorization is not raw write execution.
- raw_match_data write still requires a separate controlled raw write execution phase.
- expected raw_match_data count 18 -> 68 only in a future controlled write execution.
- raw_write_ready_for_execution remains false to avoid directly unblocking the runner.
- requires_separate_raw_write_execution=true.

## Next Step

${artifact.recommended_next_step}
`;
}

function runFinalDbWriteAuthorizationExecution(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(
        loaded.manifest,
        loaded.l2v3ahPlan,
        loaded.l2v3agArtifact,
        loaded.l2v3aeArtifact,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact
    );
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const options = {
        finalDbWriteHumanReviewSatisfied: dependencies.finalDbWriteHumanReviewSatisfied === true,
        authorizedBy: normalizeText(dependencies.authorizedBy) || DEFAULT_AUTHORIZED_BY,
        authorizedAt: normalizeText(dependencies.authorizedAt) || currentTimestamp(),
    };
    const dbSafetyStatus =
        dependencies.dbSafetyStatus ||
        (normalizeText(dependencies.dbSafetyStatusFile) ? readJsonFile(dependencies.dbSafetyStatusFile) : {});
    const execution = executeFinalDbWriteAuthorization(loaded.l2v3ahPlan, dbSafetyStatus, options);
    const artifact = buildArtifact({
        loaded,
        execution,
        finalDbWriteHumanReviewSatisfied: options.finalDbWriteHumanReviewSatisfied,
        authorizedBy: options.authorizedBy,
        authorizedAt: options.authorizedAt,
        generatedAt: dependencies.generatedAt || currentTimestamp(),
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
    return `L2V3AI is final DB-write authorization execution only.

Allowed:
  --final-db-write-human-review-satisfied=yes
  --authorized-by=<reviewer>
  --authorized-at=<iso timestamp>
  --db-safety-status-file=<json path>
  --write-files=false

Blocked:
  live fetch, detail fetch, network, DB write, raw_match_data insert, matches
  write, matches.external_id write, raw write retry, raw write ready marking,
  schema migration, parser/features/training/prediction, browser/proxy runtime,
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
    const result = runFinalDbWriteAuthorizationExecution({
        writeFiles: options.writeFiles !== false,
        finalDbWriteHumanReviewSatisfied: options.finalDbWriteHumanReviewSatisfied === true,
        authorizedBy: options.authorizedBy,
        authorizedAt: options.authorizedAt,
        dbSafetyStatusFile: options.dbSafetyStatusFile,
    });
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
                final_db_write_authorization_performed: result.artifact.final_db_write_authorization_performed,
                final_authorization_accepted_count: result.artifact.final_authorization_accepted_count,
                final_authorization_blocked_count: result.artifact.final_authorization_blocked_count,
                db_write_performed: result.artifact.db_write_performed,
                raw_match_data_insert_performed: result.artifact.raw_match_data_insert_performed,
                raw_write_retry_performed: result.artifact.raw_write_retry_performed,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
                requires_separate_raw_write_execution: result.artifact.requires_separate_raw_write_execution,
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
    L2V3AH_PLAN_PATH,
    L2V3AG_ARTIFACT_PATH,
    L2V3AE_ARTIFACT_PATH,
    L2V3AC_ARTIFACT_PATH,
    L2V3AA_ARTIFACT_PATH,
    L2V3Y_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    parseArgs,
    validateCliOptions,
    validateInputs,
    buildDbSafetyStatus,
    executeFinalDbWriteAuthorization,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    runFinalDbWriteAuthorizationExecution,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
