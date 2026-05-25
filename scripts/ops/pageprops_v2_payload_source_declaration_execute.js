#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AM';
const PHASE_NAME = 'controlled_payload_source_declaration_execution';
const ARTIFACT_STATUS = 'completed_controlled_payload_source_declaration_execution';
const SELECTED_SOURCE_TYPE = 'controlled_live_recapture_in_memory';
const PAYLOAD_SOURCE_STATUS = 'declared';
const NEXT_REQUIRED_STEP = 'controlled_no_write_payload_recapture_planning';
const RECOMMENDED_NEXT_STEP = 'Phase 5.21L2V3AN: controlled no-write payload recapture planning';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3AK_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.raw_write_input_source_investigation.phase521l2v3ak.json';
const L2V3AL_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_plan.phase521l2v3al.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_result.phase521l2v3am.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AM.md';
const AL_ARTIFACT_STATUS = 'completed_controlled_payload_source_declaration_planning';
const AK_ARTIFACT_STATUS = 'completed_controlled_raw_write_input_source_investigation';
const REVIEWED_INPUTS = Object.freeze([
    ['proposal_manifest', MANIFEST_PATH],
    ['raw_write_input_source_investigation', L2V3AK_ARTIFACT_PATH],
    ['payload_source_declaration_plan', L2V3AL_ARTIFACT_PATH],
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
    'allowRawWriteRetry',
    'allowLiveRecaptureExecution',
    'executeLiveRecapture',
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
        allowPayloadSourceDeclarationExecution: true,
        executePayloadSourceDeclaration: true,
        help: false,
        unknown: [],
    };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
        'allow-payload-source-declaration-execution': 'allowPayloadSourceDeclarationExecution',
        allow_payload_source_declaration_execution: 'allowPayloadSourceDeclarationExecution',
        'execute-payload-source-declaration': 'executePayloadSourceDeclaration',
        execute_payload_source_declaration: 'executePayloadSourceDeclaration',
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
        'allow-live-recapture-execution': 'allowLiveRecaptureExecution',
        allow_live_recapture_execution: 'allowLiveRecaptureExecution',
        'execute-live-recapture': 'executeLiveRecapture',
        execute_live_recapture: 'executeLiveRecapture',
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
    const booleanKeys = new Set([
        'writeFiles',
        'help',
        'allowPayloadSourceDeclarationExecution',
        'executePayloadSourceDeclaration',
        ...BLOCKED_TRUE_FLAGS,
    ]);

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
    if (normalizeBooleanFlag(options.allowPayloadSourceDeclarationExecution, true) !== true) {
        errors.push('payload source declaration execution must be explicitly allowed for L2V3AM');
    }
    if (normalizeBooleanFlag(options.executePayloadSourceDeclaration, true) !== true) {
        errors.push('payload source declaration execution must remain enabled for L2V3AM');
    }
    for (const flagName of BLOCKED_TRUE_FLAGS) {
        if (normalizeBooleanFlag(options[flagName], false) === true) {
            errors.push(`${cliName(flagName)}=yes is blocked`);
        }
    }
    return { ok: errors.length === 0, errors };
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3akArtifact: dependencies.l2v3akArtifact || readJsonFile(L2V3AK_ARTIFACT_PATH),
        l2v3alArtifact: dependencies.l2v3alArtifact || readJsonFile(L2V3AL_ARTIFACT_PATH),
    };
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
        value.raw_write_execution_ready === true ||
        value.raw_write_execution_performed === true ||
        value.network_request_performed === true ||
        value.live_fetch_performed === true ||
        value.detail_fetch_performed === true ||
        value.live_recapture_execution_performed === true ||
        value.schema_migration_performed === true ||
        value.parser_features_training_prediction_performed === true
    );
}

function validateInputs(loaded = {}) {
    const errors = [];
    const manifest = loaded.manifest || {};
    const ak = loaded.l2v3akArtifact || {};
    const al = loaded.l2v3alArtifact || {};
    const advancedNextSteps = new Set([
        NEXT_REQUIRED_STEP,
        'raw_write_runner_input_contract_declaration_planning',
        'payload_source_declaration_blocker_resolution',
    ]);
    const alreadyExecuted =
        normalizeText(manifest.phase_5_21_l2v3am_execution_status) === ARTIFACT_STATUS &&
        advancedNextSteps.has(normalizeText(manifest.next_required_step));

    if (
        normalizeText(manifest.next_required_step) !== 'controlled_payload_source_declaration_execution' &&
        !alreadyExecuted
    ) {
        errors.push('manifest next_required_step must be controlled_payload_source_declaration_execution');
    }
    if (normalizeText(manifest.phase_5_21_l2v3al_planning_status) !== AL_ARTIFACT_STATUS) {
        errors.push('manifest L2V3AL planning status must be completed');
    }
    if (normalizeText(ak.artifact_status) !== AK_ARTIFACT_STATUS) {
        errors.push('L2V3AK artifact status must be completed');
    }
    if (normalizeText(al.artifact_status) !== AL_ARTIFACT_STATUS) {
        errors.push('L2V3AL artifact status must be completed');
    }
    if (normalizeText(al.selected_planned_source_type) !== SELECTED_SOURCE_TYPE) {
        errors.push('L2V3AL selected planned source type must be controlled_live_recapture_in_memory');
    }
    if (normalizeText(al.payload_source_declaration_status) !== 'planned_not_executed') {
        errors.push('L2V3AL payload source declaration status must be planned_not_executed');
    }
    if (al.payload_source_declaration_execution_required !== true) {
        errors.push('L2V3AL must require payload source declaration execution');
    }
    if (al.source_controlled_payload_artifact_available !== false || ak.full_payload_artifact_found !== false) {
        errors.push('source-controlled full payload artifact must remain unavailable');
    }
    if (
        ak.safe_payload_source_path !== null ||
        normalizeText(ak.safe_payload_source_path_status) !== 'unknown_or_missing'
    ) {
        errors.push('L2V3AK safe payload source path must remain unknown_or_missing/null');
    }
    if (al.controlled_live_recapture_in_memory_required !== true || al.live_recapture_authorization_required !== true) {
        errors.push('L2V3AL must require controlled live recapture in memory and separate authorization');
    }
    if (al.full_payload_storage_allowed !== false || al.full_payload_print_allowed !== false) {
        errors.push('L2V3AL must disallow full payload storage and printing');
    }
    if (al.metadata_only_artifacts_accepted_as_payload !== false) {
        errors.push('metadata-only artifacts must not be accepted as payload');
    }
    for (const [label] of REVIEWED_INPUTS) {
        const key =
            label === 'proposal_manifest'
                ? 'manifest'
                : label === 'raw_write_input_source_investigation'
                  ? 'l2v3akArtifact'
                  : 'l2v3alArtifact';
        if (hasProhibitedWriteState(loaded[key] || {})) {
            errors.push(`${label} contains prohibited write/fetch/execution state`);
        }
    }
    return { ok: errors.length === 0, errors };
}

function targetCountFrom(loaded = {}) {
    return Number(
        loaded.l2v3alArtifact?.target_count ||
            loaded.l2v3alArtifact?.declaration_schema?.planned_values?.target_count ||
            loaded.manifest?.candidate_targets?.length ||
            0
    );
}

function buildDeclarationResult({ loaded = {} } = {}) {
    const targetCount = targetCountFrom(loaded);
    return {
        artifact_type: 'payload_source_declaration_result',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        payload_source_declaration_execution_performed: true,
        payload_source_declaration_performed: true,
        generated_at: currentTimestamp(),
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        selected_source_type: SELECTED_SOURCE_TYPE,
        payload_source_status: PAYLOAD_SOURCE_STATUS,
        source_controlled_payload_artifact_available: false,
        full_payload_artifact_found: false,
        source_path: null,
        source_endpoint_or_fetcher: 'existing pageProps v2 HTML hydration fetcher path; future authorization required',
        current_raw_write_runner_constructs_raw_data_in_memory: true,
        current_runner_accepts_source_controlled_payload_file_path: false,
        controlled_live_recapture_in_memory_required: true,
        live_recapture_required: true,
        live_recapture_authorization_required: true,
        no_browser_proxy_captcha_bypass: true,
        no_uncontrolled_retry: true,
        stop_conditions: [
            'http_403',
            'block',
            'captcha',
            'parse_failure',
            'identity_mismatch',
            'hash_or_baseline_mismatch',
        ],
        payload_persistence_policy: 'in_memory_only_no_full_payload_storage_no_full_payload_print',
        full_payload_storage_allowed: false,
        full_payload_print_allowed: false,
        in_memory_only: true,
        target_count: targetCount,
        manifest_source: MANIFEST_PATH,
        declaration_source_plan: L2V3AL_ARTIFACT_PATH,
        metadata_only_artifacts_accepted_as_payload: false,
        source_url_evidence_accepted_as_payload: false,
        baseline_hashes_accepted_as_payload: false,
        payload_source_declaration_is_not_raw_write_execution: true,
        payload_source_declaration_does_not_make_raw_write_execution_ready: true,
        future_live_recapture_success_does_not_authorize_raw_write_by_itself: true,
        raw_write_execution_ready: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        network_request_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        live_recapture_execution_performed: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        raw_write_runner_write_mode_invoked: false,
        full_raw_data_printed_or_saved: false,
        full_pageprops_printed_or_saved: false,
        full_source_body_printed_or_saved: false,
        cookies_tokens_headers_saved: false,
        local_validation_incident_review: {
            broad_node_test_accidental_e2e_db_insert_attempt_observed: true,
            insert_attempt_succeeded: false,
            insert_attempt_blocked_by_db_constraint: true,
            cleanup_ran: true,
            followup_select_only_row_count_unchanged: true,
            protected_tables_unchanged: true,
            raw_match_data_rows_added: 0,
            matches_rows_added_or_modified: 0,
            matches_external_id_modified: false,
            later_explicit_file_list_validation_passed: true,
            not_successful_db_write: true,
            not_raw_write_execution: true,
            not_regular_safety_validation_entrypoint: true,
            l2v3am_db_write_performed: false,
        },
        requires_separate_raw_write_execution_authorization: true,
        recommended_next_step: RECOMMENDED_NEXT_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3am_execution_status: ARTIFACT_STATUS,
        phase_5_21_l2v3am_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3am_report_path: REPORT_PATH,
        controlled_payload_source_declaration_execution_status: ARTIFACT_STATUS,
        payload_source_declaration_execution_performed: true,
        payload_source_declaration_performed: artifact.payload_source_declaration_performed,
        selected_source_type: artifact.selected_source_type,
        payload_source_status: artifact.payload_source_status,
        source_controlled_payload_artifact_available: false,
        controlled_live_recapture_in_memory_required: true,
        live_recapture_required: true,
        live_recapture_authorization_required: true,
        full_payload_storage_allowed: false,
        full_payload_print_allowed: false,
        in_memory_only: true,
        metadata_only_artifacts_accepted_as_payload: false,
        raw_write_execution_ready: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        requires_separate_raw_write_execution_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AM

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- payload_source_declaration_execution_performed=true
- payload_source_declaration_performed=${artifact.payload_source_declaration_performed}
- selected_source_type=${artifact.selected_source_type}
- payload_source_status=${artifact.payload_source_status}
- live_recapture_execution_performed=false
- raw_write_execution_ready=false
- raw_write_execution_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- network_request_performed=false
- live_fetch_performed=false
- detail_fetch_performed=false
- parser_features_training_prediction_performed=false
- requires_separate_raw_write_execution_authorization=true

## Declaration Result

- source_controlled_payload_artifact_available=false
- full_payload_artifact_found=false
- current_raw_write_runner_constructs_raw_data_in_memory=true
- current_runner_accepts_source_controlled_payload_file_path=false
- metadata_only_artifacts_accepted_as_payload=false
- source_url_evidence_accepted_as_payload=false
- baseline_hashes_accepted_as_payload=false

## Future Live Recapture Requirements

- controlled_live_recapture_in_memory_required=true
- live_recapture_required=true
- live_recapture_authorization_required=true
- no_browser_proxy_captcha_bypass=true
- no_uncontrolled_retry=true
- stop_conditions=${artifact.stop_conditions.join(',')}
- full_payload_storage_allowed=false
- full_payload_print_allowed=false
- in_memory_only=true

## Raw Write Relationship

- payload_source_declaration_is_not_raw_write_execution=true
- payload_source_declaration_does_not_make_raw_write_execution_ready=true
- future_live_recapture_success_does_not_authorize_raw_write_by_itself=true
- raw_write_execution_ready=false
- raw_write_execution_performed=false
- raw_match_data_insert_performed=false

## Artifact Safety

- full_raw_data_printed_or_saved=false
- full_pageprops_printed_or_saved=false
- full_source_body_printed_or_saved=false
- cookies_tokens_headers_saved=false

## Local Validation Incident Review

- broad_node_test_accidental_e2e_db_insert_attempt_observed=true
- insert_attempt_succeeded=false
- insert_attempt_blocked_by_db_constraint=true
- cleanup_ran=true
- followup_select_only_row_count_unchanged=true
- protected_tables_unchanged=true
- raw_match_data_rows_added=0
- matches_rows_added_or_modified=0
- matches_external_id_modified=false
- later_explicit_file_list_validation_passed=true
- not_successful_db_write=true
- not_raw_write_execution=true
- not_regular_safety_validation_entrypoint=true
- l2v3am_db_write_performed=false

## Next Step

${artifact.recommended_next_step}
`;
}

function runPayloadSourceDeclarationExecute(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(loaded);
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };
    const artifact = buildDeclarationResult({ loaded });
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
    return `L2V3AM executes controlled payload source declaration only.

Allowed:
  --write-files=false
  --allow-payload-source-declaration-execution=yes
  --execute-payload-source-declaration=yes

Blocked:
  live recapture execution, raw write execution, DB writes, raw_match_data
  inserts, matches writes, matches.external_id changes, live fetch, detail
  fetch, network, write mode, parser/features/training/prediction, schema
  migration, browser/proxy runtime, and full payload printing/saving.
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
    const result = runPayloadSourceDeclarationExecute({
        writeFiles: options.writeFiles !== false,
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
                payload_source_declaration_execution_performed:
                    result.artifact.payload_source_declaration_execution_performed,
                payload_source_declaration_performed: result.artifact.payload_source_declaration_performed,
                selected_source_type: result.artifact.selected_source_type,
                payload_source_status: result.artifact.payload_source_status,
                live_recapture_authorization_required: result.artifact.live_recapture_authorization_required,
                full_payload_storage_allowed: result.artifact.full_payload_storage_allowed,
                full_payload_print_allowed: result.artifact.full_payload_print_allowed,
                in_memory_only: result.artifact.in_memory_only,
                raw_write_execution_ready: result.artifact.raw_write_execution_ready,
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
    SELECTED_SOURCE_TYPE,
    PAYLOAD_SOURCE_STATUS,
    NEXT_REQUIRED_STEP,
    RECOMMENDED_NEXT_STEP,
    MANIFEST_PATH,
    L2V3AK_ARTIFACT_PATH,
    L2V3AL_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    parseArgs,
    validateCliOptions,
    validateInputs,
    buildDeclarationResult,
    buildReport,
    updateManifestMetadata,
    runPayloadSourceDeclarationExecute,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
