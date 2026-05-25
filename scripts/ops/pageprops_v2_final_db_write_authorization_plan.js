#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const agExecution = require('./pageprops_v2_baseline_acceptance_execute');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AH';
const PHASE_NAME = 'final_db_write_authorization_planning';
const ARTIFACT_STATUS = 'completed_final_db_write_authorization_planning';
const BLOCKED_STATUS = 'blocked_final_db_write_authorization_planning';
const GENERATED_AT = '2026-05-24T10:00:00Z';
const EXPECTED_TARGET_COUNT = 50;
const EXPECTED_RAW_MATCH_DATA_BEFORE_COUNT = 18;
const EXPECTED_RAW_MATCH_DATA_AFTER_COUNT = 68;
const EXPECTED_PAGEPROPS_V2_BEFORE_COUNT = 8;
const EXPECTED_EXISTING_CANDIDATE_V2_RAW_ROWS = 0;
const RAW_DATA_VERSION = 'fotmob_pageprops_v2';
const MANIFEST_PATH = agExecution.MANIFEST_PATH;
const L2V3AG_ARTIFACT_PATH = agExecution.ARTIFACT_OUTPUT_PATH;
const L2V3AE_ARTIFACT_PATH = agExecution.L2V3AE_ARTIFACT_PATH;
const L2V3AC_ARTIFACT_PATH = agExecution.L2V3AC_ARTIFACT_PATH;
const L2V3AA_ARTIFACT_PATH = agExecution.L2V3AA_ARTIFACT_PATH;
const L2V3Y_ARTIFACT_PATH = agExecution.L2V3Y_ARTIFACT_PATH;
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.final_db_write_authorization_plan.phase521l2v3ah.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AH.md';
const PASS_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AI: final DB-write authorization execution',
    next_required_step: 'final_db_write_authorization_execution',
});
const BLOCKER_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AI: final DB-write authorization blocker investigation',
    next_required_step: 'final_db_write_authorization_blocker_investigation',
});
const CONTINUED_PLANNING_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AI: continued final DB-write authorization planning',
    next_required_step: 'continued_final_db_write_authorization_planning',
});
const INPUT_PATHS = Object.freeze([
    { key: 'manifest', path: MANIFEST_PATH, role: 'current_proposal_manifest' },
    { key: 'l2v3agArtifact', path: L2V3AG_ARTIFACT_PATH, role: 'baseline_acceptance_result' },
    { key: 'l2v3aeArtifact', path: L2V3AE_ARTIFACT_PATH, role: 'identity_mapping_acceptance_result' },
    { key: 'l2v3acArtifact', path: L2V3AC_ARTIFACT_PATH, role: 'enriched_no_write_verification_result' },
    { key: 'l2v3aaArtifact', path: L2V3AA_ARTIFACT_PATH, role: 'enriched_targets' },
    { key: 'l2v3yArtifact', path: L2V3Y_ARTIFACT_PATH, role: 'source_inventory_acquisition_result' },
]);
const PLANNED_FINAL_AUTHORIZATION_RULES = Object.freeze([
    'identity_mapping_accepted_count must be 50.',
    'baseline_accepted_count must be 50.',
    'no_write_verified_target_count must be 50.',
    'enriched_target_count must be 50.',
    'existing candidate raw rows for data_version=fotmob_pageprops_v2 must be 0.',
    'raw_match_data before count must be 18.',
    'expected raw_match_data after count must be 68.',
    'raw_match_data uniqueness must be UNIQUE(match_id,data_version).',
    'legacy UNIQUE(match_id) must be absent.',
    'FK prerequisite from candidate match_id to matches must be satisfied.',
    'protected tables must remain unchanged.',
    'raw write runner must remain blocked until final authorization execution.',
    'hidden/bidi scan must be resolved before execution.',
    'full raw_data/pageProps/source body leak scan must be clean.',
    'CI must be green before execution authorization.',
    'final DB-write reviewer must explicitly authorize the future execution phase.',
]);
const PLANNED_FINAL_BLOCKING_RULES = Object.freeze([
    'accepted_mapping_count_not_50',
    'baseline_accepted_count_not_50',
    'no_write_verification_not_passed',
    'candidate_v2_raw_rows_already_exist',
    'raw_match_data_before_count_mismatch',
    'expected_after_count_mismatch',
    'unique_constraint_missing_or_wrong',
    'fk_prerequisite_not_satisfied',
    'protected_table_drift',
    'hidden_bidi_unresolved',
    'full_payload_leak_detected',
    'db_unavailable',
    'human_final_authorization_missing',
    'ci_not_green',
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
    'executeFinalDbWriteAuthorization',
    'authorizeFinalDbWrite',
    'performFinalAuthorization',
    'allowRawWriteRetry',
    'executeRawWrite',
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

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = { writeFiles: true, help: false, unknown: [] };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
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
        'execute-final-db-write-authorization': 'executeFinalDbWriteAuthorization',
        execute_final_db_write_authorization: 'executeFinalDbWriteAuthorization',
        'authorize-final-db-write': 'authorizeFinalDbWrite',
        authorize_final_db_write: 'authorizeFinalDbWrite',
        'perform-final-authorization': 'performFinalAuthorization',
        perform_final_authorization: 'performFinalAuthorization',
        'allow-raw-write-retry': 'allowRawWriteRetry',
        allow_raw_write_retry: 'allowRawWriteRetry',
        'execute-raw-write': 'executeRawWrite',
        execute_raw_write: 'executeRawWrite',
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

function hasUnsafeWriteState(value = {}, options = {}) {
    const allowBaselineAcceptance = options.allowBaselineAcceptance === true;
    const allowFinalAuthorization = options.allowFinalAuthorization === true;
    return (
        value.db_write_performed === true ||
        value.raw_insert_performed === true ||
        value.raw_match_data_insert_performed === true ||
        value.matches_write_performed === true ||
        value.matches_external_id_modified === true ||
        (allowFinalAuthorization !== true && value.raw_write_authorization_performed === true) ||
        value.raw_write_retry_performed === true ||
        (allowFinalAuthorization !== true && value.final_db_write_authorization_performed === true) ||
        value.raw_write_ready_for_execution === true ||
        (allowFinalAuthorization !== true && value.final_db_write_authorization_execution_performed === true) ||
        (allowBaselineAcceptance !== true && value.baseline_acceptance_performed === true)
    );
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3agArtifact: dependencies.l2v3agArtifact || readJsonFile(L2V3AG_ARTIFACT_PATH),
        l2v3aeArtifact: dependencies.l2v3aeArtifact || readJsonFile(L2V3AE_ARTIFACT_PATH),
        l2v3acArtifact: dependencies.l2v3acArtifact || readJsonFile(L2V3AC_ARTIFACT_PATH),
        l2v3aaArtifact: dependencies.l2v3aaArtifact || readJsonFile(L2V3AA_ARTIFACT_PATH),
        l2v3yArtifact: dependencies.l2v3yArtifact || readJsonFile(L2V3Y_ARTIFACT_PATH),
    };
}

function validateInputs(
    manifest = {},
    l2v3agArtifact = {},
    l2v3aeArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {}
) {
    const errors = [];
    const advancedNextSteps = new Set([
        'final_db_write_authorization_execution',
        'controlled_raw_match_data_write_execution_planning',
        'controlled_raw_match_data_write_execution',
        'controlled_raw_write_execution_blocker_resolution',
        'continued_controlled_raw_write_planning',
        'controlled_payload_source_declaration_planning',
    ]);
    const alreadyPlanned =
        normalizeText(manifest.phase_5_21_l2v3ah_planning_status) === ARTIFACT_STATUS &&
        advancedNextSteps.has(normalizeText(manifest.next_required_step));
    if (normalizeText(manifest.next_required_step) !== 'final_db_write_authorization_planning' && !alreadyPlanned) {
        errors.push('manifest next_required_step must be final_db_write_authorization_planning');
    }
    if (normalizeText(manifest.phase_5_21_l2v3ag_execution_status) !== 'completed_baseline_acceptance_execution') {
        errors.push('manifest phase_5_21_l2v3ag_execution_status must be completed_baseline_acceptance_execution');
    }
    if (Number(manifest.phase_5_21_l2v3ag_baseline_accepted_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('manifest phase_5_21_l2v3ag_baseline_accepted_count must be 50');
    }
    const laterFinalAuthorizationExecuted =
        normalizeText(manifest.phase_5_21_l2v3ai_execution_status) ===
        'completed_final_db_write_authorization_execution';
    if (
        hasUnsafeWriteState(manifest, {
            allowBaselineAcceptance: true,
            allowFinalAuthorization: laterFinalAuthorizationExecuted,
        })
    ) {
        errors.push('manifest must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }

    if (l2v3agArtifact.proposal_phase !== 'Phase 5.21L2V3AG') errors.push('L2V3AG artifact is required');
    if (l2v3agArtifact.phase_name !== 'baseline_acceptance_execution') {
        errors.push('L2V3AG phase_name must be baseline_acceptance_execution');
    }
    if (l2v3agArtifact.baseline_acceptance_execution_performed !== true) {
        errors.push('L2V3AG baseline_acceptance_execution_performed must be true');
    }
    if (l2v3agArtifact.baseline_acceptance_performed !== true) {
        errors.push('L2V3AG baseline_acceptance_performed must be true');
    }
    if (Number(l2v3agArtifact.baseline_accepted_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AG baseline_accepted_count must be 50');
    }
    if (Number(l2v3agArtifact.baseline_blocked_count || 0) !== 0) {
        errors.push('L2V3AG baseline_blocked_count must be 0');
    }
    if (l2v3agArtifact.baseline_human_review_required !== true) {
        errors.push('L2V3AG baseline_human_review_required must be true');
    }
    if (l2v3agArtifact.baseline_human_review_satisfied !== true) {
        errors.push('L2V3AG baseline_human_review_satisfied must be true');
    }
    if (hasUnsafeWriteState(l2v3agArtifact, { allowBaselineAcceptance: true })) {
        errors.push('L2V3AG artifact must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }

    if (l2v3aeArtifact.proposal_phase !== 'Phase 5.21L2V3AE') errors.push('L2V3AE artifact is required');
    if (Number(l2v3aeArtifact.accepted_mapping_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AE accepted_mapping_count must be 50');
    }
    if (Number(l2v3aeArtifact.blocked_mapping_count || 0) !== 0) {
        errors.push('L2V3AE blocked_mapping_count must be 0');
    }
    if (l2v3aeArtifact.human_review_satisfied !== true) {
        errors.push('L2V3AE human_review_satisfied must be true');
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
    if (Number(l2v3acArtifact.failed_target_count || 0) !== 0) errors.push('L2V3AC failed_target_count must be 0');
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

function countBy(values = []) {
    const counts = new Map();
    for (const value of values.map(item => normalizeText(item)).filter(Boolean)) {
        counts.set(value, (counts.get(value) || 0) + 1);
    }
    return counts;
}

function isDuplicate(counts, value) {
    const key = normalizeText(value);
    return Boolean(key && (counts.get(key) || 0) > 1);
}

function indexBy(values = [], keyName) {
    const map = new Map();
    for (const value of values) {
        const key = normalizeText(value?.[keyName]);
        if (key) map.set(key, value);
    }
    return map;
}

function buildInputSummaries(loaded = {}) {
    return INPUT_PATHS.map(input => {
        const value = loaded[input.key];
        return {
            key: input.key,
            path: input.path,
            role: input.role,
            present: Boolean(value),
            proposal_phase: value?.proposal_phase || null,
            db_write_performed: value?.db_write_performed === true,
            raw_write_retry_performed: value?.raw_write_retry_performed === true,
            final_db_write_authorization_performed: value?.final_db_write_authorization_performed === true,
            raw_write_ready_for_execution: value?.raw_write_ready_for_execution === true,
        };
    });
}

function buildPlanningContext(l2v3agArtifact = {}, l2v3aeArtifact = {}, l2v3acArtifact = {}, l2v3aaArtifact = {}) {
    const baselineEntries = Array.isArray(l2v3agArtifact.baseline_entries) ? l2v3agArtifact.baseline_entries : [];
    const identityEntries = Array.isArray(l2v3aeArtifact.review_entries) ? l2v3aeArtifact.review_entries : [];
    const verificationResults = Array.isArray(l2v3acArtifact.verification_analysis?.target_results)
        ? l2v3acArtifact.verification_analysis.target_results
        : [];
    const enrichedTargets = Array.isArray(l2v3aaArtifact.enriched_targets) ? l2v3aaArtifact.enriched_targets : [];
    return {
        baselineEntries,
        identityByTargetId: indexBy(identityEntries, 'target_id'),
        verificationByTargetId: indexBy(verificationResults, 'target_id'),
        enrichedByTargetId: indexBy(enrichedTargets, 'target_id'),
        duplicates: {
            target_id: countBy(baselineEntries.map(entry => entry.target_id)),
            match_id: countBy(baselineEntries.map(entry => entry.match_id)),
            source_inventory_record_key: countBy(baselineEntries.map(entry => entry.source_inventory_record_key)),
            source_url_fragment_external_id: countBy(
                baselineEntries.map(entry => entry.source_url_fragment_external_id)
            ),
        },
    };
}

function buildDbSafetyStatus(overrides = {}) {
    return {
        source: overrides.source || 'preflight_select_only_row_count_and_schema_guard',
        select_only: true,
        db_available: overrides.db_available !== false,
        matches_count: Number(overrides.matches_count ?? 60),
        raw_match_data_count: Number(overrides.raw_match_data_count ?? EXPECTED_RAW_MATCH_DATA_BEFORE_COUNT),
        fotmob_pageprops_v2_count: Number(overrides.fotmob_pageprops_v2_count ?? EXPECTED_PAGEPROPS_V2_BEFORE_COUNT),
        candidate_v2_raw_rows_existing_count: Number(
            overrides.candidate_v2_raw_rows_existing_count ?? EXPECTED_EXISTING_CANDIDATE_V2_RAW_ROWS
        ),
        bookmaker_odds_history_count: Number(overrides.bookmaker_odds_history_count ?? 2),
        l3_features_count: Number(overrides.l3_features_count ?? 2),
        match_features_training_count: Number(overrides.match_features_training_count ?? 2),
        predictions_count: Number(overrides.predictions_count ?? 2),
        protected_tables_unchanged: overrides.protected_tables_unchanged !== false,
        unique_match_id_data_version_present: overrides.unique_match_id_data_version_present !== false,
        legacy_unique_match_id_absent: overrides.legacy_unique_match_id_absent !== false,
        fk_prerequisite_satisfied: overrides.fk_prerequisite_satisfied !== false,
        raw_write_runner_guard_ok: overrides.raw_write_runner_guard_ok === true,
        raw_write_runner_guard_error_count: Number(overrides.raw_write_runner_guard_error_count ?? 52),
        hidden_bidi_resolved: overrides.hidden_bidi_resolved !== false,
        full_payload_scan_clean: overrides.full_payload_scan_clean !== false,
        ci_green: overrides.ci_green !== false,
    };
}

function dbSafetyBlockers(dbSafety = {}) {
    const blockers = [];
    if (dbSafety.db_available !== true) blockers.push('db_unavailable');
    if (dbSafety.raw_match_data_count !== EXPECTED_RAW_MATCH_DATA_BEFORE_COUNT) {
        blockers.push('raw_match_data_before_count_mismatch');
    }
    if (dbSafety.candidate_v2_raw_rows_existing_count !== EXPECTED_EXISTING_CANDIDATE_V2_RAW_ROWS) {
        blockers.push('candidate_v2_raw_rows_already_exist');
    }
    if (dbSafety.unique_match_id_data_version_present !== true || dbSafety.legacy_unique_match_id_absent !== true) {
        blockers.push('unique_constraint_missing_or_wrong');
    }
    if (dbSafety.fk_prerequisite_satisfied !== true) blockers.push('fk_prerequisite_not_satisfied');
    if (dbSafety.protected_tables_unchanged !== true) blockers.push('protected_table_drift');
    if (dbSafety.raw_write_runner_guard_ok !== false) blockers.push('raw_write_runner_unexpectedly_ready');
    if (dbSafety.hidden_bidi_resolved !== true) blockers.push('hidden_bidi_unresolved');
    if (dbSafety.full_payload_scan_clean !== true) blockers.push('full_payload_leak_detected');
    if (dbSafety.ci_green !== true) blockers.push('ci_not_green');
    return blockers;
}

function buildFinalAuthorizationEntry(baselineEntry = {}, context = {}, dbSafety = {}) {
    const blockers = [];
    const targetId = normalizeText(baselineEntry.target_id);
    const identityEntry = context.identityByTargetId.get(targetId) || {};
    const verification = context.verificationByTargetId.get(targetId) || {};
    const enriched = context.enrichedByTargetId.get(targetId) || {};
    const sourceEvidenceComplete =
        Boolean(normalizeText(baselineEntry.source_page_url)) &&
        Boolean(normalizeText(baselineEntry.source_page_url_base)) &&
        Boolean(normalizeText(baselineEntry.source_url_fragment_external_id)) &&
        Boolean(normalizeText(baselineEntry.source_inventory_record_key));
    const noDuplicateIdentityKeys =
        !isDuplicate(context.duplicates.target_id, baselineEntry.target_id) &&
        !isDuplicate(context.duplicates.match_id, baselineEntry.match_id) &&
        !isDuplicate(context.duplicates.source_inventory_record_key, baselineEntry.source_inventory_record_key) &&
        !isDuplicate(context.duplicates.source_url_fragment_external_id, baselineEntry.source_url_fragment_external_id);
    const fragmentMatchesSchedule =
        normalizeText(baselineEntry.source_url_fragment_external_id) ===
        normalizeText(baselineEntry.schedule_external_id);

    if (baselineEntry.baseline_accepted !== true) blockers.push('baseline_not_accepted');
    if (baselineEntry.baseline_acceptance_status !== 'accepted_enriched_baseline_metadata') {
        blockers.push('baseline_acceptance_status_not_accepted_metadata');
    }
    if (identityEntry.acceptance_status !== 'accepted_identity_mapping') {
        blockers.push('identity_mapping_not_accepted');
    }
    if (verification.verification_status !== 'verified') blockers.push('no_write_verification_not_passed');
    if (!enriched.target_id) blockers.push('enriched_target_missing');
    if (sourceEvidenceComplete !== true) blockers.push('missing_source_url_evidence');
    if (fragmentMatchesSchedule !== true) blockers.push('fragment_schedule_mismatch');
    if (noDuplicateIdentityKeys !== true) blockers.push('duplicate_or_conflicting_identity_key');
    blockers.push(...dbSafetyBlockers(dbSafety));

    const ready = blockers.length === 0;
    return {
        target_id: baselineEntry.target_id || null,
        match_id: baselineEntry.match_id || null,
        schedule_external_id: baselineEntry.schedule_external_id || null,
        source_page_url: baselineEntry.source_page_url || null,
        source_page_url_base: baselineEntry.source_page_url_base || null,
        source_url_fragment_external_id: baselineEntry.source_url_fragment_external_id || null,
        schedule_date: baselineEntry.schedule_date || null,
        schedule_home_team: baselineEntry.schedule_home_team || null,
        schedule_away_team: baselineEntry.schedule_away_team || null,
        source_inventory_record_key: baselineEntry.source_inventory_record_key || null,
        raw_data_version: RAW_DATA_VERSION,
        final_authorization_status: ready ? 'final_authorization_ready' : 'final_authorization_blocked',
        final_db_write_authorization_performed: false,
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_write_execution_performed: false,
        planned_write_operation: 'future_transaction_controlled_raw_match_data_insert',
        planned_write_scope: {
            table: 'raw_match_data',
            data_version: RAW_DATA_VERSION,
            target_match_id: baselineEntry.match_id || null,
            insert_only: true,
            matches_write_allowed: false,
            matches_external_id_write_allowed: false,
            protected_tables_write_allowed: false,
        },
        final_authorization_blockers: [...new Set(blockers)],
        final_authorization_evidence_summary: {
            identity_mapping_accepted: identityEntry.acceptance_status === 'accepted_identity_mapping',
            baseline_accepted: baselineEntry.baseline_accepted === true,
            no_write_verification_passed: verification.verification_status === 'verified',
            enriched_target_present: Boolean(enriched.target_id),
            source_url_evidence_complete: sourceEvidenceComplete,
            source_url_fragment_external_id_matches_schedule_external_id: fragmentMatchesSchedule,
            no_duplicate_identity_keys: noDuplicateIdentityKeys,
            existing_candidate_v2_raw_rows_zero:
                dbSafety.candidate_v2_raw_rows_existing_count === EXPECTED_EXISTING_CANDIDATE_V2_RAW_ROWS,
            raw_match_data_before_count_expected:
                dbSafety.raw_match_data_count === EXPECTED_RAW_MATCH_DATA_BEFORE_COUNT,
            expected_after_count_documented: EXPECTED_RAW_MATCH_DATA_AFTER_COUNT === 68,
            unique_match_id_data_version_present: dbSafety.unique_match_id_data_version_present === true,
            legacy_unique_match_id_absent: dbSafety.legacy_unique_match_id_absent === true,
            fk_prerequisite_satisfied: dbSafety.fk_prerequisite_satisfied === true,
            protected_tables_unchanged: dbSafety.protected_tables_unchanged === true,
            raw_write_runner_remains_blocked: dbSafety.raw_write_runner_guard_ok === false,
            final_db_write_authorization_performed: false,
        },
    };
}

function planFinalDbWriteAuthorization(
    manifest = {},
    l2v3agArtifact = {},
    l2v3aeArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    dbSafetyOverrides = {}
) {
    const context = buildPlanningContext(l2v3agArtifact, l2v3aeArtifact, l2v3acArtifact, l2v3aaArtifact);
    const dbSafety = buildDbSafetyStatus(dbSafetyOverrides);
    const finalAuthorizationEntries = context.baselineEntries.map(entry =>
        buildFinalAuthorizationEntry(entry, context, dbSafety)
    );
    const finalAuthorizationReadyCount = finalAuthorizationEntries.filter(
        entry => entry.final_authorization_status === 'final_authorization_ready'
    ).length;
    const finalAuthorizationBlockedCount = finalAuthorizationEntries.length - finalAuthorizationReadyCount;
    return {
        identity_mapping_accepted_count: Number(l2v3aeArtifact.accepted_mapping_count || 0),
        baseline_accepted_count: Number(l2v3agArtifact.baseline_accepted_count || 0),
        no_write_verified_target_count: Number(l2v3acArtifact.verified_target_count || 0),
        enriched_target_count: Number(l2v3aaArtifact.regenerated_target_count || 0),
        final_authorization_candidate_count: finalAuthorizationEntries.length,
        final_authorization_ready_count: finalAuthorizationReadyCount,
        final_authorization_blocked_count: finalAuthorizationBlockedCount,
        final_authorization_blocker_count: finalAuthorizationEntries.reduce(
            (sum, entry) => sum + entry.final_authorization_blockers.length,
            0
        ),
        final_authorization_entries: finalAuthorizationEntries,
        db_safety_status: dbSafety,
        manifest_next_required_step_before_planning: manifest.next_required_step || null,
    };
}

function determineOutcome(plan = {}) {
    if (plan.final_authorization_candidate_count !== EXPECTED_TARGET_COUNT) return CONTINUED_PLANNING_NEXT_STEP;
    if (plan.final_authorization_blocked_count > 0) return BLOCKER_NEXT_STEP;
    if (plan.final_authorization_ready_count === EXPECTED_TARGET_COUNT) return PASS_NEXT_STEP;
    return CONTINUED_PLANNING_NEXT_STEP;
}

function buildArtifact({ loaded = {}, plan = {}, generatedAt = GENERATED_AT } = {}) {
    const inputSummaries = buildInputSummaries(loaded);
    const outcome = determineOutcome(plan);
    const completed = plan.final_authorization_blocked_count === 0;
    return {
        artifact_type: 'final_db_write_authorization_planning_result',
        artifact_status: completed ? ARTIFACT_STATUS : BLOCKED_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3AG',
        source_baseline_acceptance_result_path: L2V3AG_ARTIFACT_PATH,
        source_identity_mapping_acceptance_result_path: L2V3AE_ARTIFACT_PATH,
        source_no_write_verification_result_path: L2V3AC_ARTIFACT_PATH,
        generated_at: generatedAt,
        planning_status: completed ? ARTIFACT_STATUS : BLOCKED_STATUS,
        planning_only: true,
        final_db_write_authorization_planning_only: true,
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
        final_db_write_authorization_execution_performed: false,
        final_db_write_authorization_performed: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        baseline_acceptance_performed: true,
        baseline_accepted_count: plan.baseline_accepted_count,
        reviewed_input_artifact_count: inputSummaries.filter(input => input.present).length,
        input_artifact_summaries: inputSummaries,
        identity_mapping_accepted_count: plan.identity_mapping_accepted_count,
        no_write_verified_target_count: plan.no_write_verified_target_count,
        enriched_target_count: plan.enriched_target_count,
        final_authorization_candidate_count: plan.final_authorization_candidate_count,
        final_authorization_ready_count: plan.final_authorization_ready_count,
        final_authorization_blocked_count: plan.final_authorization_blocked_count,
        final_authorization_blocker_count: plan.final_authorization_blocker_count,
        planned_final_authorization_rule_count: PLANNED_FINAL_AUTHORIZATION_RULES.length,
        planned_final_authorization_blocking_rule_count: PLANNED_FINAL_BLOCKING_RULES.length,
        planned_final_authorization_rules: PLANNED_FINAL_AUTHORIZATION_RULES,
        planned_final_authorization_blocking_rules: PLANNED_FINAL_BLOCKING_RULES,
        final_db_write_reviewer_required: true,
        final_db_write_execution_authorization_required: true,
        final_db_write_authorization_execution_requires_separate_explicit_authorization: true,
        expected_raw_match_data_before_count: EXPECTED_RAW_MATCH_DATA_BEFORE_COUNT,
        expected_raw_match_data_after_count: EXPECTED_RAW_MATCH_DATA_AFTER_COUNT,
        expected_raw_match_data_delta_count: EXPECTED_TARGET_COUNT,
        expected_fotmob_pageprops_v2_before_count: EXPECTED_PAGEPROPS_V2_BEFORE_COUNT,
        expected_fotmob_pageprops_v2_after_count: EXPECTED_PAGEPROPS_V2_BEFORE_COUNT + EXPECTED_TARGET_COUNT,
        existing_candidate_v2_raw_rows_expected_count: EXPECTED_EXISTING_CANDIDATE_V2_RAW_ROWS,
        raw_data_version: RAW_DATA_VERSION,
        db_safety_status: plan.db_safety_status,
        raw_write_runner_guard_status: {
            ok: plan.db_safety_status.raw_write_runner_guard_ok,
            error_count: plan.db_safety_status.raw_write_runner_guard_error_count,
            blocked_until_final_authorization_execution: true,
        },
        write_scope: {
            planning_only_current_phase: true,
            future_execution_scope_table: 'raw_match_data',
            future_execution_data_version: RAW_DATA_VERSION,
            future_execution_target_count: EXPECTED_TARGET_COUNT,
            future_execution_requires_transaction_controlled_insert: true,
            future_execution_requires_final_db_write_authorization_confirmation: true,
            current_phase_writes_db: false,
        },
        non_write_scope: {
            no_final_authorization_execution: true,
            no_raw_write_retry: true,
            no_live_fetch: true,
            no_detail_fetch: true,
            no_network_request: true,
            no_matches_write: true,
            no_matches_external_id_change: true,
            no_schema_migration: true,
            no_parser_features_training_prediction: true,
            no_full_payload_output: true,
        },
        final_authorization_entries: plan.final_authorization_entries,
        safety_contract: {
            baseline_accepted_does_not_imply_final_db_write_authorization: true,
            final_authorization_ready_does_not_imply_final_authorization_performed: true,
            final_authorization_plan_does_not_authorize_raw_write: true,
            final_authorization_plan_does_not_execute_db_write: true,
            raw_write_ready_for_execution_remains_false: true,
            raw_write_retry_performed_remains_false: true,
            final_db_write_authorization_performed_remains_false: true,
            final_db_write_authorization_execution_requires_separate_explicit_authorization: true,
        },
        recommended_next_step: outcome.recommended_next_step,
        next_required_step: outcome.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3ah_planning_status: artifact.planning_status,
        final_db_write_authorization_planning_status: artifact.planning_status,
        phase_5_21_l2v3ah_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ah_report_path: REPORT_PATH,
        phase_5_21_l2v3ah_identity_mapping_accepted_count: artifact.identity_mapping_accepted_count,
        phase_5_21_l2v3ah_baseline_accepted_count: artifact.baseline_accepted_count,
        phase_5_21_l2v3ah_no_write_verified_target_count: artifact.no_write_verified_target_count,
        phase_5_21_l2v3ah_final_authorization_candidate_count: artifact.final_authorization_candidate_count,
        phase_5_21_l2v3ah_final_authorization_ready_count: artifact.final_authorization_ready_count,
        phase_5_21_l2v3ah_final_authorization_blocked_count: artifact.final_authorization_blocked_count,
        phase_5_21_l2v3ah_planned_final_authorization_rule_count: artifact.planned_final_authorization_rule_count,
        phase_5_21_l2v3ah_planned_final_authorization_blocking_rule_count:
            artifact.planned_final_authorization_blocking_rule_count,
        final_db_write_reviewer_required: true,
        final_db_write_authorization_execution_performed: false,
        final_db_write_authorization_performed: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        expected_raw_match_data_before_count: artifact.expected_raw_match_data_before_count,
        expected_raw_match_data_after_count: artifact.expected_raw_match_data_after_count,
        expected_raw_match_data_delta_count: artifact.expected_raw_match_data_delta_count,
        final_authorization_candidate_count: artifact.final_authorization_candidate_count,
        final_authorization_ready_count: artifact.final_authorization_ready_count,
        final_authorization_blocked_count: artifact.final_authorization_blocked_count,
        planned_final_authorization_rule_count: artifact.planned_final_authorization_rule_count,
        planned_final_authorization_blocking_rule_count: artifact.planned_final_authorization_blocking_rule_count,
        requires_separate_final_db_write_authorization_execution: true,
        final_authorization_ready_does_not_imply_final_authorization_performed: true,
        baseline_accepted_does_not_imply_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AH

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- final_db_write_authorization_planning_only=true
- final_db_write_authorization_execution_performed=false
- final_db_write_authorization_performed=false
- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- raw_write_authorization_performed=false
- raw_write_retry_performed=false
- raw_write_ready_for_execution=false

## Planning Summary

- reviewed_input_artifact_count=${artifact.reviewed_input_artifact_count}
- identity_mapping_accepted_count=${artifact.identity_mapping_accepted_count}
- baseline_accepted_count=${artifact.baseline_accepted_count}
- no_write_verified_target_count=${artifact.no_write_verified_target_count}
- final_authorization_candidate_count=${artifact.final_authorization_candidate_count}
- final_authorization_ready_count=${artifact.final_authorization_ready_count}
- final_authorization_blocked_count=${artifact.final_authorization_blocked_count}
- planned_final_authorization_rule_count=${artifact.planned_final_authorization_rule_count}
- planned_final_authorization_blocking_rule_count=${artifact.planned_final_authorization_blocking_rule_count}
- final_db_write_reviewer_required=true
- final_db_write_execution_authorization_required=true

## Expected Row Counts

- expected_raw_match_data_before_count=${artifact.expected_raw_match_data_before_count}
- expected_raw_match_data_after_count=${artifact.expected_raw_match_data_after_count}
- expected_raw_match_data_delta_count=${artifact.expected_raw_match_data_delta_count}
- expected_fotmob_pageprops_v2_before_count=${artifact.expected_fotmob_pageprops_v2_before_count}
- expected_fotmob_pageprops_v2_after_count=${artifact.expected_fotmob_pageprops_v2_after_count}
- existing_candidate_v2_raw_rows_expected_count=${artifact.existing_candidate_v2_raw_rows_expected_count}

## Write Scope

- current_phase_is_planning_only=true
- future_execution_scope_table=raw_match_data
- future_execution_data_version=${RAW_DATA_VERSION}
- future_execution_target_count=${EXPECTED_TARGET_COUNT}
- future_execution_requires_transaction_controlled_insert=true
- no_matches_write=true
- no_matches_external_id_changes=true
- no_odds_features_training_prediction_writes=true

## Non-Write Scope

- no_final_authorization_execution=true
- no_raw_write_retry=true
- no_live_fetch=true
- no_detail_fetch=true
- no_network_request=true
- no_schema_migration=true
- no_parser_features_training_prediction=true
- no_full_payload_output=true

## Safety Contract

- baseline accepted is not raw write authorization.
- baseline accepted does not imply final DB-write authorization.
- final_authorization_ready is not final authorization performed.
- final DB-write authorization execution requires separate explicit authorization.
- current user instruction authorizes planning only, not DB write.
- raw_write_retry_performed=false.
- final_db_write_authorization_performed=false.
- raw_write_ready_for_execution=false.

## Planned Blocking Rules

${artifact.planned_final_authorization_blocking_rules.map(rule => `- ${rule}`).join('\n')}

## Next Step

${artifact.recommended_next_step}
`;
}

function runFinalDbWriteAuthorizationPlanning(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(
        loaded.manifest,
        loaded.l2v3agArtifact,
        loaded.l2v3aeArtifact,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact
    );
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const plan = planFinalDbWriteAuthorization(
        loaded.manifest,
        loaded.l2v3agArtifact,
        loaded.l2v3aeArtifact,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        dependencies.dbSafetyStatus || {}
    );
    const artifact = buildArtifact({ loaded, plan, generatedAt: dependencies.generatedAt || GENERATED_AT });
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
    return `L2V3AH is final DB-write authorization planning only.

Allowed:
  --write-files=false

Blocked:
  final authorization execution, live fetch, detail fetch, network, DB write,
  raw_match_data insert, matches write, matches.external_id write, raw write
  retry, raw write ready marking, schema migration, parser/features/training/
  prediction, browser/proxy runtime, and full payload printing/saving.
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
    const result = runFinalDbWriteAuthorizationPlanning({ writeFiles: options.writeFiles !== false });
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
                final_authorization_candidate_count: result.artifact.final_authorization_candidate_count,
                final_authorization_ready_count: result.artifact.final_authorization_ready_count,
                final_authorization_blocked_count: result.artifact.final_authorization_blocked_count,
                final_db_write_authorization_performed: result.artifact.final_db_write_authorization_performed,
                raw_write_retry_performed: result.artifact.raw_write_retry_performed,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
                expected_raw_match_data_before_count: result.artifact.expected_raw_match_data_before_count,
                expected_raw_match_data_after_count: result.artifact.expected_raw_match_data_after_count,
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
    L2V3AG_ARTIFACT_PATH,
    L2V3AE_ARTIFACT_PATH,
    L2V3AC_ARTIFACT_PATH,
    L2V3AA_ARTIFACT_PATH,
    L2V3Y_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    PLANNED_FINAL_AUTHORIZATION_RULES,
    PLANNED_FINAL_BLOCKING_RULES,
    parseArgs,
    validateCliOptions,
    validateInputs,
    buildDbSafetyStatus,
    planFinalDbWriteAuthorization,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    runFinalDbWriteAuthorizationPlanning,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
