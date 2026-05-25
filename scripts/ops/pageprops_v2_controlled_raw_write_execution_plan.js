#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const aiExecute = require('./pageprops_v2_final_db_write_authorization_execute');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AJ';
const PHASE_NAME = 'controlled_raw_match_data_write_execution_planning';
const ARTIFACT_STATUS = 'completed_controlled_raw_match_data_write_execution_planning';
const BLOCKED_STATUS = 'blocked_controlled_raw_write_execution_planning';
const CONTINUED_STATUS = 'continued_controlled_raw_write_planning_required';
const READY_STATUS = 'ready_for_separate_raw_write_execution_authorization';
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
const MANIFEST_PATH = aiExecute.MANIFEST_PATH;
const L2V3AI_ARTIFACT_PATH = aiExecute.ARTIFACT_OUTPUT_PATH;
const L2V3AG_ARTIFACT_PATH = aiExecute.L2V3AG_ARTIFACT_PATH;
const L2V3AE_ARTIFACT_PATH = aiExecute.L2V3AE_ARTIFACT_PATH;
const L2V3AC_ARTIFACT_PATH = aiExecute.L2V3AC_ARTIFACT_PATH;
const L2V3AA_ARTIFACT_PATH = aiExecute.L2V3AA_ARTIFACT_PATH;
const L2V3Y_ARTIFACT_PATH = aiExecute.L2V3Y_ARTIFACT_PATH;
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_raw_match_data_write_execution_plan.phase521l2v3aj.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AJ.md';
const RAW_WRITE_RUNNER_REFERENCE_PATH = 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js';
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
    'writeMode',
    'printFullBody',
    'saveFullBody',
    'printFullJson',
    'saveFullJson',
    'printFullPageprops',
    'saveFullPageprops',
]);
const PAYLOAD_SOURCE_KEY_PATTERN = /(payload|raw_data|source_body).*path/i;
const READY_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AK: controlled raw_match_data write execution',
    next_required_step: 'controlled_raw_match_data_write_execution',
});
const BLOCKED_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AK: controlled raw write execution blocker resolution',
    next_required_step: 'controlled_raw_write_execution_blocker_resolution',
});
const CONTINUED_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AK: continued controlled raw write planning',
    next_required_step: 'continued_controlled_raw_write_planning',
});

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
        dbSafetyStatusFile: null,
        help: false,
        unknown: [],
    };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
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
        'write-mode': 'writeMode',
        write_mode: 'writeMode',
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

function hasProhibitedWriteState(value = {}) {
    return (
        value.db_write_performed === true ||
        value.raw_insert_performed === true ||
        value.raw_match_data_insert_performed === true ||
        value.matches_write_performed === true ||
        value.matches_external_id_modified === true ||
        value.raw_write_retry_performed === true ||
        value.raw_write_ready_for_execution === true ||
        value.raw_write_execution_performed === true
    );
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3aiArtifact: dependencies.l2v3aiArtifact || readJsonFile(L2V3AI_ARTIFACT_PATH),
        l2v3agArtifact: dependencies.l2v3agArtifact || readJsonFile(L2V3AG_ARTIFACT_PATH),
        l2v3aeArtifact: dependencies.l2v3aeArtifact || readJsonFile(L2V3AE_ARTIFACT_PATH),
        l2v3acArtifact: dependencies.l2v3acArtifact || readJsonFile(L2V3AC_ARTIFACT_PATH),
        l2v3aaArtifact: dependencies.l2v3aaArtifact || readJsonFile(L2V3AA_ARTIFACT_PATH),
        l2v3yArtifact: dependencies.l2v3yArtifact || readJsonFile(L2V3Y_ARTIFACT_PATH),
    };
}

function validateInputs(
    manifest = {},
    l2v3aiArtifact = {},
    l2v3agArtifact = {},
    l2v3aeArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {}
) {
    const errors = [];
    const advancedNextSteps = new Set([
        'controlled_raw_match_data_write_execution',
        'controlled_raw_write_execution_blocker_resolution',
        'continued_controlled_raw_write_planning',
        'controlled_payload_source_declaration_planning',
        'controlled_payload_source_declaration_execution',
        'controlled_no_write_payload_recapture_planning',
        'controlled_no_write_payload_recapture_execution',
        'no_write_payload_recapture_blocker_investigation',
        'partial_recapture_review_planning',
        'controlled_recapture_result_verification_planning',
    ]);
    const alreadyPlanned =
        normalizeText(manifest.phase_5_21_l2v3aj_planning_status) === ARTIFACT_STATUS &&
        advancedNextSteps.has(normalizeText(manifest.next_required_step));
    if (
        normalizeText(manifest.next_required_step) !== 'controlled_raw_match_data_write_execution_planning' &&
        !alreadyPlanned
    ) {
        errors.push('manifest next_required_step must be controlled_raw_match_data_write_execution_planning');
    }

    if (l2v3aiArtifact.proposal_phase !== 'Phase 5.21L2V3AI') errors.push('L2V3AI artifact is required');
    if (l2v3aiArtifact.phase_name !== 'final_db_write_authorization_execution') {
        errors.push('L2V3AI phase_name must be final_db_write_authorization_execution');
    }
    if (l2v3aiArtifact.final_db_write_authorization_execution_performed !== true) {
        errors.push('L2V3AI final_db_write_authorization_execution_performed must be true');
    }
    if (l2v3aiArtifact.final_db_write_authorization_performed !== true) {
        errors.push('L2V3AI final_db_write_authorization_performed must be true');
    }
    if (l2v3aiArtifact.final_db_write_human_review_required !== true) {
        errors.push('L2V3AI final_db_write_human_review_required must be true');
    }
    if (l2v3aiArtifact.final_db_write_human_review_satisfied !== true) {
        errors.push('L2V3AI final_db_write_human_review_satisfied must be true');
    }
    if (Number(l2v3aiArtifact.identity_mapping_accepted_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AI identity_mapping_accepted_count must be 50');
    }
    if (Number(l2v3aiArtifact.baseline_accepted_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AI baseline_accepted_count must be 50');
    }
    if (Number(l2v3aiArtifact.no_write_verified_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AI no_write_verified_target_count must be 50');
    }
    if (Number(l2v3aiArtifact.final_authorization_candidate_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AI final_authorization_candidate_count must be 50');
    }
    if (Number(l2v3aiArtifact.final_authorization_reviewed_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AI final_authorization_reviewed_count must be 50');
    }
    if (Number(l2v3aiArtifact.final_authorization_accepted_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AI final_authorization_accepted_count must be 50');
    }
    if (Number(l2v3aiArtifact.final_authorization_blocked_count || 0) !== 0) {
        errors.push('L2V3AI final_authorization_blocked_count must be 0');
    }
    if (l2v3aiArtifact.requires_separate_raw_write_execution !== true) {
        errors.push('L2V3AI requires_separate_raw_write_execution must be true');
    }
    if (l2v3aiArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3AI raw_write_ready_for_execution must be false');
    }
    if (
        Number(l2v3aiArtifact.expected_raw_match_data_after_future_write || 0) !== EXPECTED_RAW_MATCH_DATA_AFTER_COUNT
    ) {
        errors.push('L2V3AI expected_raw_match_data_after_future_write must be 68');
    }
    if (Number(l2v3aiArtifact.candidate_v2_existing_rows || 0) !== EXPECTED_EXISTING_CANDIDATE_V2_RAW_ROWS) {
        errors.push('L2V3AI candidate_v2_existing_rows must be 0');
    }
    if (l2v3aiArtifact.network_request_performed !== false) {
        errors.push('L2V3AI network_request_performed must be false');
    }
    if (l2v3aiArtifact.live_fetch_performed !== false) {
        errors.push('L2V3AI live_fetch_performed must be false');
    }
    if (l2v3aiArtifact.detail_fetch_performed !== false) {
        errors.push('L2V3AI detail_fetch_performed must be false');
    }
    if (l2v3aiArtifact.schema_migration_performed !== false) {
        errors.push('L2V3AI schema_migration_performed must be false');
    }
    if (l2v3aiArtifact.parser_features_training_prediction_performed !== false) {
        errors.push('L2V3AI parser_features_training_prediction_performed must be false');
    }
    if (hasProhibitedWriteState(l2v3aiArtifact)) {
        errors.push('L2V3AI artifact must not contain DB-write, raw-write, network, or schema-migration state');
    }

    if (l2v3agArtifact.proposal_phase !== 'Phase 5.21L2V3AG') errors.push('L2V3AG artifact is required');
    if (l2v3agArtifact.baseline_acceptance_performed !== true) {
        errors.push('L2V3AG baseline_acceptance_performed must be true');
    }
    if (Number(l2v3agArtifact.baseline_accepted_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AG baseline_accepted_count must be 50');
    }
    if (hasProhibitedWriteState(l2v3agArtifact)) {
        errors.push('L2V3AG artifact must not contain DB-write, raw-write, network, or schema-migration state');
    }

    if (l2v3aeArtifact.proposal_phase !== 'Phase 5.21L2V3AE') errors.push('L2V3AE artifact is required');
    if (Number(l2v3aeArtifact.accepted_mapping_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AE accepted_mapping_count must be 50');
    }
    if (hasProhibitedWriteState(l2v3aeArtifact)) {
        errors.push('L2V3AE artifact must not contain DB-write, raw-write, network, or schema-migration state');
    }

    if (l2v3acArtifact.proposal_phase !== 'Phase 5.21L2V3AC') errors.push('L2V3AC artifact is required');
    if (l2v3acArtifact.verification_status !== 'passed_no_write_source_controlled') {
        errors.push('L2V3AC verification_status must be passed_no_write_source_controlled');
    }
    if (Number(l2v3acArtifact.verified_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AC verified_target_count must be 50');
    }
    if (l2v3acArtifact.raw_write_runner_blocked !== true) {
        errors.push('L2V3AC raw_write_runner_blocked must be true');
    }
    if (hasProhibitedWriteState(l2v3acArtifact)) {
        errors.push('L2V3AC artifact must not contain DB-write, raw-write, network, or schema-migration state');
    }

    if (Number(l2v3aaArtifact.regenerated_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AA regenerated_target_count must be 50');
    }
    if (hasProhibitedWriteState(l2v3aaArtifact)) {
        errors.push('L2V3AA artifact must not contain DB-write, raw-write, network, or schema-migration state');
    }

    if (Number(l2v3yArtifact.candidate_scope_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3Y candidate_scope_count must be 50');
    }
    if (hasProhibitedWriteState(l2v3yArtifact)) {
        errors.push('L2V3Y artifact must not contain DB-write, raw-write, network, or schema-migration state');
    }

    if (manifest.final_db_write_authorization_performed !== true) {
        errors.push('manifest final_db_write_authorization_performed must be true');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must be false');
    }
    if (manifest.requires_separate_raw_write_execution !== true) {
        errors.push('manifest requires_separate_raw_write_execution must be true');
    }
    if (hasProhibitedWriteState(manifest)) {
        errors.push('manifest must not contain DB-write, raw-write, network, or schema-migration state');
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
        source: overrides.source || 'select_only_db_safety_snapshot_for_controlled_raw_write_planning',
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

function pushPayloadSourcePath(collection, key, value, sourceLabel) {
    if (!PAYLOAD_SOURCE_KEY_PATTERN.test(key) || !normalizeText(value)) return;
    collection.push({
        source: sourceLabel,
        key,
        value: normalizeText(value),
    });
}

function collectPayloadSourcePaths(value, sourceLabel, collection = []) {
    if (!value || typeof value !== 'object') return collection;
    if (Array.isArray(value)) {
        for (const entry of value) collectPayloadSourcePaths(entry, sourceLabel, collection);
        return collection;
    }
    for (const [key, entryValue] of Object.entries(value)) {
        if (typeof entryValue === 'string') pushPayloadSourcePath(collection, key, entryValue, sourceLabel);
        if (entryValue && typeof entryValue === 'object') {
            collectPayloadSourcePaths(entryValue, sourceLabel, collection);
        }
    }
    return collection;
}

function uniquePayloadSourcePaths(records = []) {
    const seen = new Set();
    return records.filter(record => {
        const id = `${record.source}:${record.key}:${record.value}`;
        if (seen.has(id)) return false;
        seen.add(id);
        return true;
    });
}

function detectPayloadSource(loaded = {}) {
    const candidates = [];
    collectPayloadSourcePaths(loaded.manifest, 'manifest', candidates);
    collectPayloadSourcePaths(loaded.l2v3aiArtifact, 'l2v3ai', candidates);
    collectPayloadSourcePaths(loaded.l2v3agArtifact, 'l2v3ag', candidates);
    collectPayloadSourcePaths(loaded.l2v3aeArtifact, 'l2v3ae', candidates);
    collectPayloadSourcePaths(loaded.l2v3acArtifact, 'l2v3ac', candidates);
    collectPayloadSourcePaths(loaded.l2v3aaArtifact, 'l2v3aa', candidates);
    collectPayloadSourcePaths(loaded.l2v3yArtifact, 'l2v3y', candidates);
    const paths = uniquePayloadSourcePaths(candidates);
    return {
        status:
            paths.length > 0
                ? 'declared_safe_payload_source_paths_present'
                : 'unknown_no_safe_payload_source_path_declared',
        clear: paths.length > 0,
        followup_needed: paths.length === 0,
        paths,
    };
}

function reviewedInputArtifactCount() {
    return 7;
}

function determineOutcome(blockers = [], payloadSource = {}) {
    if (blockers.length > 0) {
        return {
            artifact_status: BLOCKED_STATUS,
            controlled_raw_write_execution_planning_status: BLOCKED_STATUS,
            ...BLOCKED_NEXT_STEP,
        };
    }
    if (payloadSource.clear !== true) {
        return {
            artifact_status: ARTIFACT_STATUS,
            controlled_raw_write_execution_planning_status: CONTINUED_STATUS,
            ...CONTINUED_NEXT_STEP,
        };
    }
    return {
        artifact_status: ARTIFACT_STATUS,
        controlled_raw_write_execution_planning_status: READY_STATUS,
        ...READY_NEXT_STEP,
    };
}

function buildTransactionPlan() {
    return {
        begin_transaction_required: true,
        insert_exactly_target_count_rows: true,
        planned_insert_count: EXPECTED_TARGET_COUNT,
        insert_only: true,
        data_version: RAW_DATA_VERSION,
        verify_inserted_count_equals_target_count: true,
        verify_raw_match_data_after_count_equals_expected: true,
        verify_protected_tables_unchanged: true,
        commit_only_if_all_checks_pass: true,
        rollback_on_any_mismatch: true,
        no_partial_commit: true,
        non_raw_table_writes_allowed: false,
    };
}

function buildArtifact({ loaded = {}, dbSafetyStatus = {} } = {}) {
    const blockers = dbSafetyBlockers(dbSafetyStatus);
    const payloadSource = detectPayloadSource(loaded);
    const runnerReferenceExists = fs.existsSync(absolutePath(RAW_WRITE_RUNNER_REFERENCE_PATH));
    const outcome = determineOutcome(blockers, payloadSource);
    const writeInputSourceUnknown = payloadSource.clear !== true;
    const executionPreconditions = {
        final_db_write_authorization_performed: loaded.l2v3aiArtifact.final_db_write_authorization_performed === true,
        requires_separate_raw_write_execution: loaded.l2v3aiArtifact.requires_separate_raw_write_execution === true,
        requires_separate_raw_write_execution_authorization: true,
        user_must_provide_separate_explicit_raw_write_execution_authorization: true,
        candidate_v2_existing_rows_zero: dbSafetyStatus.candidate_v2_existing_rows === 0,
        fk_prerequisite_satisfied: dbSafetyStatus.fk_prerequisite_satisfied === true,
        unique_match_id_data_version_present: dbSafetyStatus.unique_match_id_data_version_present === true,
        legacy_unique_match_id_absent: dbSafetyStatus.legacy_unique_match_id_absent === true,
        protected_tables_unchanged: dbSafetyStatus.protected_tables_unchanged === true,
        raw_match_data_before_count_is_18: dbSafetyStatus.raw_match_data_count === EXPECTED_RAW_MATCH_DATA_BEFORE_COUNT,
        expected_raw_match_data_after_count_is_68: true,
        hidden_bidi_resolved: dbSafetyStatus.hidden_bidi_resolved === true,
        full_payload_scan_clean: dbSafetyStatus.full_payload_scan_clean === true,
        ci_green: dbSafetyStatus.ci_green === true,
    };
    return {
        artifact_type: 'controlled_raw_match_data_write_execution_plan',
        artifact_status: outcome.artifact_status,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        planning_only: true,
        controlled_raw_write_execution_planning_only: true,
        generated_at: currentTimestamp(),
        reviewed_input_artifact_count: reviewedInputArtifactCount(),
        reviewed_input_artifact_paths: {
            final_db_write_authorization_result_path: L2V3AI_ARTIFACT_PATH,
            baseline_acceptance_result_path: L2V3AG_ARTIFACT_PATH,
            identity_mapping_acceptance_result_path: L2V3AE_ARTIFACT_PATH,
            enriched_no_write_verification_result_path: L2V3AC_ARTIFACT_PATH,
            enriched_targets_path: L2V3AA_ARTIFACT_PATH,
            source_inventory_acquisition_result_path: L2V3Y_ARTIFACT_PATH,
            proposal_manifest_path: MANIFEST_PATH,
        },
        planning_status: ARTIFACT_STATUS,
        controlled_raw_write_execution_planning_status: outcome.controlled_raw_write_execution_planning_status,
        final_db_write_authorization_performed: loaded.l2v3aiArtifact.final_db_write_authorization_performed === true,
        final_db_write_authorization_execution_performed:
            loaded.l2v3aiArtifact.final_db_write_authorization_execution_performed === true,
        planned_write_table: 'raw_match_data',
        planned_data_version: RAW_DATA_VERSION,
        planned_target_count: EXPECTED_TARGET_COUNT,
        planned_insert_mode: 'insert_only',
        planned_transaction_control: true,
        expected_raw_match_data_before_count: EXPECTED_RAW_MATCH_DATA_BEFORE_COUNT,
        expected_insert_count: EXPECTED_TARGET_COUNT,
        expected_raw_match_data_after_count: EXPECTED_RAW_MATCH_DATA_AFTER_COUNT,
        protected_table_write_scope: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        requires_separate_raw_write_execution_authorization: true,
        write_input_source_status: payloadSource.status,
        write_input_source_unknown: writeInputSourceUnknown,
        write_input_source_followup_needed: payloadSource.followup_needed,
        write_input_source_paths_found: payloadSource.paths,
        write_runner_reference_path: RAW_WRITE_RUNNER_REFERENCE_PATH,
        write_runner_reference_exists: runnerReferenceExists,
        write_runner_write_mode_invoked: false,
        execution_preconditions: executionPreconditions,
        execution_blocking_rules: [
            'no explicit user raw write execution authorization',
            'final authorization missing',
            'candidate v2 existing rows != 0',
            'raw_match_data count != 18',
            'expected after count != 68',
            'FK prerequisite not satisfied',
            'UNIQUE constraint mismatch',
            'protected table drift',
            'hidden/bidi unresolved',
            'payload leak detected',
            'DB unavailable',
            'CI not green',
            'any attempt to write non-raw_match_data table',
        ],
        blocking_reasons_detected: blockers,
        transaction_plan: buildTransactionPlan(),
        payload_policy: {
            do_not_print_full_raw_data: true,
            do_not_print_full_pageprops: true,
            do_not_print_full_source_body: true,
            do_not_save_full_source_body: true,
            safe_metadata_and_counts_only: true,
            current_safe_payload_source_path_identified: payloadSource.clear === true,
        },
        db_safety_status: dbSafetyStatus,
        recommended_next_step: outcome.recommended_next_step,
        next_required_step: outcome.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3aj_planning_status: artifact.artifact_status,
        controlled_raw_match_data_write_execution_planning_status:
            artifact.controlled_raw_write_execution_planning_status,
        phase_5_21_l2v3aj_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3aj_report_path: REPORT_PATH,
        final_db_write_authorization_performed: true,
        planned_write_table: artifact.planned_write_table,
        planned_data_version: artifact.planned_data_version,
        planned_target_count: artifact.planned_target_count,
        expected_raw_match_data_before_count: artifact.expected_raw_match_data_before_count,
        expected_insert_count: artifact.expected_insert_count,
        expected_raw_match_data_after_count: artifact.expected_raw_match_data_after_count,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        requires_separate_raw_write_execution_authorization: true,
        phase_5_21_l2v3aj_payload_source_status: artifact.write_input_source_status,
        phase_5_21_l2v3aj_write_input_source_unknown: artifact.write_input_source_unknown,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AJ

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- planning_only=true
- raw_write_execution_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- requires_separate_raw_write_execution_authorization=true

## Reviewed Inputs

- reviewed_input_artifact_count=${artifact.reviewed_input_artifact_count}
- final_db_write_authorization_performed=${artifact.final_db_write_authorization_performed}
- planned_write_table=${artifact.planned_write_table}
- planned_data_version=${artifact.planned_data_version}
- planned_target_count=${artifact.planned_target_count}

## Planned Counts

- expected_raw_match_data_before_count=${artifact.expected_raw_match_data_before_count}
- expected_insert_count=${artifact.expected_insert_count}
- expected_raw_match_data_after_count=${artifact.expected_raw_match_data_after_count}
- protected_table_write_scope=${artifact.protected_table_write_scope}

## Transaction Plan

- begin_transaction_required=${artifact.transaction_plan.begin_transaction_required}
- insert_exactly_target_count_rows=${artifact.transaction_plan.insert_exactly_target_count_rows}
- verify_inserted_count_equals_target_count=${artifact.transaction_plan.verify_inserted_count_equals_target_count}
- verify_raw_match_data_after_count_equals_expected=${artifact.transaction_plan.verify_raw_match_data_after_count_equals_expected}
- verify_protected_tables_unchanged=${artifact.transaction_plan.verify_protected_tables_unchanged}
- commit_only_if_all_checks_pass=${artifact.transaction_plan.commit_only_if_all_checks_pass}
- rollback_on_any_mismatch=${artifact.transaction_plan.rollback_on_any_mismatch}
- no_partial_commit=${artifact.transaction_plan.no_partial_commit}

## Preconditions

- final_db_write_authorization_performed=${artifact.execution_preconditions.final_db_write_authorization_performed}
- requires_separate_raw_write_execution=${artifact.execution_preconditions.requires_separate_raw_write_execution}
- candidate_v2_existing_rows_zero=${artifact.execution_preconditions.candidate_v2_existing_rows_zero}
- fk_prerequisite_satisfied=${artifact.execution_preconditions.fk_prerequisite_satisfied}
- unique_match_id_data_version_present=${artifact.execution_preconditions.unique_match_id_data_version_present}
- legacy_unique_match_id_absent=${artifact.execution_preconditions.legacy_unique_match_id_absent}
- raw_match_data_before_count_is_18=${artifact.execution_preconditions.raw_match_data_before_count_is_18}
- expected_raw_match_data_after_count_is_68=${artifact.execution_preconditions.expected_raw_match_data_after_count_is_68}
- ci_green=${artifact.execution_preconditions.ci_green}

## Payload Safety

- write_input_source_status=${artifact.write_input_source_status}
- write_input_source_unknown=${artifact.write_input_source_unknown}
- do_not_print_full_raw_data=${artifact.payload_policy.do_not_print_full_raw_data}
- do_not_print_full_pageprops=${artifact.payload_policy.do_not_print_full_pageprops}
- do_not_print_full_source_body=${artifact.payload_policy.do_not_print_full_source_body}
- safe_metadata_and_counts_only=${artifact.payload_policy.safe_metadata_and_counts_only}

## Blocking Rules

- no explicit user raw write execution authorization
- final authorization missing
- candidate v2 existing rows != 0
- raw_match_data count != 18
- expected after count != 68
- FK prerequisite not satisfied
- UNIQUE constraint mismatch
- protected table drift
- hidden/bidi unresolved
- payload leak detected
- DB unavailable
- CI not green
- any attempt to write non-raw_match_data table

## Next Step

${artifact.recommended_next_step}
`;
}

function runControlledRawWriteExecutionPlanning(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(
        loaded.manifest,
        loaded.l2v3aiArtifact,
        loaded.l2v3agArtifact,
        loaded.l2v3aeArtifact,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact
    );
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const dbSafetyStatus =
        dependencies.dbSafetyStatus ||
        (normalizeText(dependencies.dbSafetyStatusFile) ? readJsonFile(dependencies.dbSafetyStatusFile) : {});
    const artifact = buildArtifact({
        loaded,
        dbSafetyStatus: buildDbSafetyStatus(dbSafetyStatus),
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
    return `L2V3AJ is controlled raw_match_data write execution planning only.

Allowed:
  --db-safety-status-file=<json path>
  --write-files=false

Blocked:
  raw write execution, DB writes, raw_match_data inserts, matches writes,
  live fetch, detail fetch, network, write mode, parser/features/training/prediction,
  schema migration, browser/proxy runtime, and full payload printing/saving.
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
    const result = runControlledRawWriteExecutionPlanning({
        writeFiles: options.writeFiles !== false,
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
                planning_status: result.artifact.planning_status,
                final_db_write_authorization_performed: result.artifact.final_db_write_authorization_performed,
                controlled_raw_write_execution_planning_status:
                    result.artifact.controlled_raw_write_execution_planning_status,
                planned_write_table: result.artifact.planned_write_table,
                planned_data_version: result.artifact.planned_data_version,
                planned_target_count: result.artifact.planned_target_count,
                expected_raw_match_data_after_count: result.artifact.expected_raw_match_data_after_count,
                raw_write_execution_performed: result.artifact.raw_write_execution_performed,
                db_write_performed: result.artifact.db_write_performed,
                raw_match_data_insert_performed: result.artifact.raw_match_data_insert_performed,
                requires_separate_raw_write_execution_authorization:
                    result.artifact.requires_separate_raw_write_execution_authorization,
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
    BLOCKED_STATUS,
    CONTINUED_STATUS,
    READY_STATUS,
    MANIFEST_PATH,
    L2V3AI_ARTIFACT_PATH,
    L2V3AG_ARTIFACT_PATH,
    L2V3AE_ARTIFACT_PATH,
    L2V3AC_ARTIFACT_PATH,
    L2V3AA_ARTIFACT_PATH,
    L2V3Y_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    RAW_WRITE_RUNNER_REFERENCE_PATH,
    parseArgs,
    validateCliOptions,
    validateInputs,
    buildDbSafetyStatus,
    detectPayloadSource,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    runControlledRawWriteExecutionPlanning,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
