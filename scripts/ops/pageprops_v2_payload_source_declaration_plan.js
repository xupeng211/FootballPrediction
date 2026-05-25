#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AL';
const PHASE_NAME = 'controlled_payload_source_declaration_planning';
const ARTIFACT_STATUS = 'completed_controlled_payload_source_declaration_planning';
const SELECTED_PLANNED_SOURCE_TYPE = 'controlled_live_recapture_in_memory';
const PAYLOAD_SOURCE_DECLARATION_STATUS = 'planned_not_executed';
const NEXT_REQUIRED_STEP = 'controlled_payload_source_declaration_execution';
const RECOMMENDED_NEXT_STEP = 'Phase 5.21L2V3AM: controlled payload source declaration execution';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3Y_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
const L2V3AA_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const L2V3AC_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_result.phase521l2v3ac.json';
const L2V3AE_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_result.phase521l2v3ae.json';
const L2V3AG_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.baseline_acceptance_result.phase521l2v3ag.json';
const L2V3AI_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.final_db_write_authorization_result.phase521l2v3ai.json';
const L2V3AJ_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_raw_match_data_write_execution_plan.phase521l2v3aj.json';
const L2V3AK_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.raw_write_input_source_investigation.phase521l2v3ak.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_plan.phase521l2v3al.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AL.md';
const RAW_WRITE_RUNNER_PATH = 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js';
const RAW_WRITE_BASE_HELPER_PATH = 'scripts/ops/single_league_pageprops_v2_controlled_write_execute.js';
const AK_ARTIFACT_STATUS = 'completed_controlled_raw_write_input_source_investigation';
const AK_INPUT_CONTRACT_STATUS = 'requires_manifest_metadata_plus_live_recapture_to_construct_raw_data';
const REVIEWED_INPUTS = Object.freeze([
    ['proposal_manifest', MANIFEST_PATH],
    ['source_inventory_acquisition_result', L2V3Y_ARTIFACT_PATH],
    ['enriched_targets', L2V3AA_ARTIFACT_PATH],
    ['enriched_no_write_verification_result', L2V3AC_ARTIFACT_PATH],
    ['identity_mapping_acceptance_result', L2V3AE_ARTIFACT_PATH],
    ['baseline_acceptance_result', L2V3AG_ARTIFACT_PATH],
    ['final_db_write_authorization_result', L2V3AI_ARTIFACT_PATH],
    ['controlled_raw_match_data_write_execution_plan', L2V3AJ_ARTIFACT_PATH],
    ['raw_write_input_source_investigation', L2V3AK_ARTIFACT_PATH],
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
    'allowPayloadSourceDeclarationExecution',
    'allowLiveRecaptureExecution',
    'executePayloadSourceDeclaration',
    'commitPayloadSourceDeclaration',
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
        'allow-payload-source-declaration-execution': 'allowPayloadSourceDeclarationExecution',
        allow_payload_source_declaration_execution: 'allowPayloadSourceDeclarationExecution',
        'allow-live-recapture-execution': 'allowLiveRecaptureExecution',
        allow_live_recapture_execution: 'allowLiveRecaptureExecution',
        'execute-payload-source-declaration': 'executePayloadSourceDeclaration',
        execute_payload_source_declaration: 'executePayloadSourceDeclaration',
        'commit-payload-source-declaration': 'commitPayloadSourceDeclaration',
        commit_payload_source_declaration: 'commitPayloadSourceDeclaration',
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

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3yArtifact: dependencies.l2v3yArtifact || readJsonFile(L2V3Y_ARTIFACT_PATH),
        l2v3aaArtifact: dependencies.l2v3aaArtifact || readJsonFile(L2V3AA_ARTIFACT_PATH),
        l2v3acArtifact: dependencies.l2v3acArtifact || readJsonFile(L2V3AC_ARTIFACT_PATH),
        l2v3aeArtifact: dependencies.l2v3aeArtifact || readJsonFile(L2V3AE_ARTIFACT_PATH),
        l2v3agArtifact: dependencies.l2v3agArtifact || readJsonFile(L2V3AG_ARTIFACT_PATH),
        l2v3aiArtifact: dependencies.l2v3aiArtifact || readJsonFile(L2V3AI_ARTIFACT_PATH),
        l2v3ajArtifact: dependencies.l2v3ajArtifact || readJsonFile(L2V3AJ_ARTIFACT_PATH),
        l2v3akArtifact: dependencies.l2v3akArtifact || readJsonFile(L2V3AK_ARTIFACT_PATH),
        rawWriteRunnerSource: dependencies.rawWriteRunnerSource || readTextFile(RAW_WRITE_RUNNER_PATH),
        rawWriteBaseHelperSource: dependencies.rawWriteBaseHelperSource || readTextFile(RAW_WRITE_BASE_HELPER_PATH),
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
        value.schema_migration_performed === true ||
        value.parser_features_training_prediction_performed === true
    );
}

function validateInputs(loaded = {}) {
    const errors = [];
    const manifest = loaded.manifest || {};
    const ak = loaded.l2v3akArtifact || {};
    const advancedNextSteps = new Set([
        NEXT_REQUIRED_STEP,
        'controlled_no_write_payload_recapture_planning',
        'controlled_no_write_payload_recapture_execution',
        'no_write_payload_recapture_blocker_investigation',
        'partial_recapture_review_planning',
        'controlled_recapture_result_verification_planning',
        'raw_write_runner_input_contract_declaration_planning',
        'continued_payload_source_declaration_planning',
    ]);
    const alreadyPlanned =
        normalizeText(manifest.phase_5_21_l2v3al_planning_status) === ARTIFACT_STATUS &&
        advancedNextSteps.has(normalizeText(manifest.next_required_step));

    if (
        normalizeText(manifest.next_required_step) !== 'controlled_payload_source_declaration_planning' &&
        !alreadyPlanned
    ) {
        errors.push('manifest next_required_step must be controlled_payload_source_declaration_planning');
    }
    if (normalizeText(manifest.phase_5_21_l2v3ak_planning_status) !== AK_ARTIFACT_STATUS) {
        errors.push('manifest L2V3AK planning status must be completed');
    }
    if (normalizeText(ak.proposal_phase) !== 'Phase 5.21L2V3AK') errors.push('L2V3AK artifact is required');
    if (normalizeText(ak.safe_payload_source_path_status) !== 'unknown_or_missing') {
        errors.push('L2V3AK safe_payload_source_path_status must remain unknown_or_missing');
    }
    if (ak.safe_payload_source_path !== null) errors.push('L2V3AK safe_payload_source_path must remain null');
    if (ak.full_payload_artifact_found !== false) errors.push('L2V3AK full_payload_artifact_found must be false');
    if (ak.live_recapture_required !== true) errors.push('L2V3AK live_recapture_required must be true');
    if (ak.raw_write_execution_ready !== false) errors.push('L2V3AK raw_write_execution_ready must be false');
    if (ak.raw_write_execution_performed !== false) errors.push('L2V3AK raw_write_execution_performed must be false');
    if (ak.db_write_performed !== false) errors.push('L2V3AK db_write_performed must be false');
    if (ak.raw_match_data_insert_performed !== false) {
        errors.push('L2V3AK raw_match_data_insert_performed must be false');
    }
    if (ak.metadata_only_artifacts_cannot_be_used_as_raw_payload !== true) {
        errors.push('L2V3AK must reject metadata-only artifacts as raw payload');
    }
    if (ak.source_url_evidence_cannot_be_treated_as_raw_payload !== true) {
        errors.push('L2V3AK must reject source URL evidence as raw payload');
    }
    if (ak.baseline_accepted_cannot_be_treated_as_raw_payload !== true) {
        errors.push('L2V3AK must reject baseline acceptance as raw payload');
    }
    if (normalizeText(ak.raw_write_runner_input_contract_status) !== AK_INPUT_CONTRACT_STATUS) {
        errors.push('L2V3AK runner input contract status is not the expected live recapture contract');
    }
    if (ak.raw_write_runner_input_contract?.accepts_payload_file_path !== false) {
        errors.push('L2V3AK runner contract must not accept a payload file path');
    }
    if (ak.raw_write_runner_input_contract?.constructs_raw_data_in_memory_from_pageprops !== true) {
        errors.push('L2V3AK runner contract must construct raw_data in memory');
    }
    for (const [label] of REVIEWED_INPUTS) {
        const key =
            label === 'proposal_manifest'
                ? 'manifest'
                : label === 'source_inventory_acquisition_result'
                  ? 'l2v3yArtifact'
                  : label === 'enriched_targets'
                    ? 'l2v3aaArtifact'
                    : label === 'enriched_no_write_verification_result'
                      ? 'l2v3acArtifact'
                      : label === 'identity_mapping_acceptance_result'
                        ? 'l2v3aeArtifact'
                        : label === 'baseline_acceptance_result'
                          ? 'l2v3agArtifact'
                          : label === 'final_db_write_authorization_result'
                            ? 'l2v3aiArtifact'
                            : label === 'controlled_raw_match_data_write_execution_plan'
                              ? 'l2v3ajArtifact'
                              : 'l2v3akArtifact';
        if (hasProhibitedWriteState(loaded[key] || {})) {
            errors.push(`${label} contains prohibited write/execution state`);
        }
    }
    return { ok: errors.length === 0, errors };
}

function inspectRawWriteRunnerContract(rawWriteRunnerSource = '', rawWriteBaseHelperSource = '') {
    const combined = `${rawWriteRunnerSource}\n${rawWriteBaseHelperSource}`;
    return {
        status: AK_INPUT_CONTRACT_STATUS,
        runner_reference_path: RAW_WRITE_RUNNER_PATH,
        base_helper_reference_path: RAW_WRITE_BASE_HELPER_PATH,
        requires_manifest_metadata:
            /MANIFEST_PATH/.test(rawWriteRunnerSource) && /readManifestFile/.test(rawWriteRunnerSource),
        requires_live_recapture:
            /recaptureTargetsSequential/.test(rawWriteRunnerSource) &&
            /base\.recaptureTarget/.test(rawWriteRunnerSource) &&
            /fetchHtml/.test(rawWriteBaseHelperSource),
        requires_full_pageprops_payload: /function buildRawDataForTarget/.test(rawWriteBaseHelperSource),
        constructs_raw_data_in_memory_from_pageprops:
            /function buildRawDataForTarget/.test(rawWriteBaseHelperSource) &&
            /pageProps: safePageProps/.test(rawWriteBaseHelperSource),
        accepts_payload_file_path:
            /payloadSourcePath|safePayloadSourcePath|payload-source-path|raw-data-source-path/.test(combined),
        write_mode_invoked: false,
        inspected_by_source_read_only: true,
    };
}

function targetCountFrom(loaded = {}) {
    if (Array.isArray(loaded.manifest?.candidate_targets)) return loaded.manifest.candidate_targets.length;
    return Number(loaded.l2v3agArtifact?.baseline_accepted_count || loaded.manifest?.baseline_accepted_count || 0);
}

function buildSourceTypeCandidates(loaded = {}) {
    const targetCount = targetCountFrom(loaded);
    return [
        {
            source_type: 'source_controlled_payload_artifact',
            selected_for_planning: false,
            payload_source_accepted: false,
            source_status: 'unavailable_missing',
            source_path: null,
            target_count: targetCount,
            source_controlled_payload_artifact_available: false,
            raw_write_runner_contract_change_required_if_selected: true,
            reason: 'L2V3AK found no full payload artifact and the current runner does not accept a payload file path',
            required_future_safety_gates: [
                'artifact_must_exist',
                'artifact_must_be_complete',
                'artifact_must_match_all_targets',
                'artifact_hash_metadata_must_be_verified',
                'full_payload_must_not_be_printed_to_logs_or_reports',
            ],
        },
        {
            source_type: SELECTED_PLANNED_SOURCE_TYPE,
            selected_for_planning: true,
            payload_source_accepted: false,
            source_status: PAYLOAD_SOURCE_DECLARATION_STATUS,
            source_path: null,
            target_count: targetCount,
            in_memory_only: true,
            source_endpoint_or_fetcher:
                'existing pageProps v2 HTML hydration fetcher path; future authorization required',
            live_recapture_required: true,
            live_recapture_authorization_required: true,
            payload_persistence_policy: 'in_memory_only_no_full_payload_storage_no_full_payload_print',
            raw_write_runner_contract_change_required_if_selected: false,
            reason: 'AK confirmed the current runner uses manifest metadata plus controlled live recapture and constructs raw_data in memory',
            required_future_safety_gates: [
                'separate_live_recapture_authorization_required',
                'no_browser_proxy_captcha_bypass',
                'no_full_payload_print_or_save',
                'no_uncontrolled_retries',
                'http_403_block_or_captcha_stops',
                'recaptured_identity_must_match_accepted_mapping_baseline_and_targets',
                'transaction_write_only_in_later_raw_write_execution_phase',
                'live_recapture_success_does_not_authorize_raw_write',
            ],
        },
        {
            source_type: 'raw_write_runner_in_memory_fetch_output',
            selected_for_planning: false,
            payload_source_accepted: false,
            source_status: 'execution_internal_output_only',
            source_path: null,
            target_count: targetCount,
            in_memory_only: true,
            compatible_with_selected_planned_source_type: true,
            reason: 'runner output can materialize payload only during a future authorized recapture/write path and is not a source-controlled declaration artifact',
        },
        {
            source_type: 'unsupported_metadata_only_artifact',
            selected_for_planning: false,
            payload_source_accepted: false,
            source_status: 'rejected',
            source_path: null,
            target_count: targetCount,
            reason: 'metadata-only artifacts, source URL evidence, and accepted baseline hashes cannot be treated as raw payload',
        },
    ];
}

function buildDeclarationSchema(targetCount) {
    return {
        required_fields: [
            'source_type',
            'source_status',
            'source_path',
            'source_endpoint_or_fetcher',
            'live_recapture_required',
            'live_recapture_authorization_required',
            'payload_persistence_policy',
            'full_payload_storage_allowed',
            'full_payload_print_allowed',
            'in_memory_only',
            'target_count',
            'manifest_source',
            'fetcher_contract',
            'validation_rules',
            'blockers',
            'raw_write_execution_ready',
            'requires_separate_raw_write_execution_authorization',
        ],
        planned_values: {
            source_type: SELECTED_PLANNED_SOURCE_TYPE,
            source_status: PAYLOAD_SOURCE_DECLARATION_STATUS,
            source_path: null,
            source_endpoint_or_fetcher:
                'existing pageProps v2 HTML hydration fetcher path; future authorization required',
            live_recapture_required: true,
            live_recapture_authorization_required: true,
            payload_persistence_policy: 'in_memory_only_no_full_payload_storage_no_full_payload_print',
            full_payload_storage_allowed: false,
            full_payload_print_allowed: false,
            in_memory_only: true,
            target_count: targetCount,
            manifest_source: MANIFEST_PATH,
            fetcher_contract: AK_INPUT_CONTRACT_STATUS,
            raw_write_execution_ready: false,
            requires_separate_raw_write_execution_authorization: true,
        },
    };
}

function buildValidationRules() {
    return [
        'payload_source_declaration_execution_must_be_separate_phase',
        'controlled_live_recapture_requires_separate_authorization',
        'live_recapture_required_does_not_allow_live_fetch_in_L2V3AL',
        'no_db_write',
        'no_raw_match_data_insert',
        'no_matches_write',
        'no_matches_external_id_change',
        'no_live_fetch',
        'no_detail_fetch',
        'no_network_request',
        'no_browser_proxy_captcha_bypass',
        'no_schema_migration',
        'no_parser_features_training_prediction',
        'no_full_payload_print_or_save',
        'metadata_only_artifacts_cannot_be_payload',
        'source_url_evidence_cannot_be_payload',
        'baseline_hashes_cannot_be_payload',
        'planned_source_type_does_not_imply_payload_source_accepted',
        'planned_source_type_does_not_imply_raw_write_execution_ready',
        'raw_write_execution_still_requires_separate_explicit_authorization',
    ];
}

function buildArtifact({ loaded = {} } = {}) {
    const runnerContract = inspectRawWriteRunnerContract(loaded.rawWriteRunnerSource, loaded.rawWriteBaseHelperSource);
    const sourceTypeCandidates = buildSourceTypeCandidates(loaded);
    const targetCount = targetCountFrom(loaded);
    return {
        artifact_type: 'payload_source_declaration_plan',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        planning_only: true,
        payload_source_declaration_execution_performed: false,
        live_recapture_execution_performed: false,
        generated_at: currentTimestamp(),
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        planning_status: ARTIFACT_STATUS,
        controlled_payload_source_declaration_planning_status: PAYLOAD_SOURCE_DECLARATION_STATUS,
        source_type_candidate_count: sourceTypeCandidates.length,
        source_type_candidates: sourceTypeCandidates,
        selected_planned_source_type: SELECTED_PLANNED_SOURCE_TYPE,
        payload_source_declaration_status: PAYLOAD_SOURCE_DECLARATION_STATUS,
        payload_source_accepted: false,
        source_controlled_payload_artifact_available: false,
        controlled_live_recapture_in_memory_required: true,
        raw_write_runner_contract_change_required: false,
        payload_source_declaration_execution_required: true,
        live_recapture_authorization_required: true,
        full_payload_storage_allowed: false,
        full_payload_print_allowed: false,
        metadata_only_artifacts_accepted_as_payload: false,
        raw_write_runner_input_contract_status: runnerContract.status,
        raw_write_runner_input_contract: runnerContract,
        declaration_schema: buildDeclarationSchema(targetCount),
        validation_rules: buildValidationRules(),
        blockers: [
            'payload_source_declaration_not_executed',
            'live_recapture_not_authorized_or_executed_in_L2V3AL',
            'raw_write_execution_requires_later_separate_authorization',
        ],
        target_count: targetCount,
        manifest_source: MANIFEST_PATH,
        raw_write_execution_ready: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        network_request_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        raw_write_runner_write_mode_invoked: false,
        requires_separate_raw_write_execution_authorization: true,
        planned_source_type_is_not_payload_source_accepted: true,
        planned_source_type_is_not_raw_write_execution_ready: true,
        live_recapture_required_does_not_authorize_live_fetch: true,
        recommended_next_step: RECOMMENDED_NEXT_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3al_planning_status: artifact.planning_status,
        phase_5_21_l2v3al_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3al_report_path: REPORT_PATH,
        controlled_payload_source_declaration_planning_status:
            artifact.controlled_payload_source_declaration_planning_status,
        source_type_candidate_count: artifact.source_type_candidate_count,
        selected_planned_source_type: artifact.selected_planned_source_type,
        payload_source_declaration_status: artifact.payload_source_declaration_status,
        source_controlled_payload_artifact_available: artifact.source_controlled_payload_artifact_available,
        controlled_live_recapture_in_memory_required: artifact.controlled_live_recapture_in_memory_required,
        raw_write_runner_contract_change_required: artifact.raw_write_runner_contract_change_required,
        payload_source_declaration_execution_required: artifact.payload_source_declaration_execution_required,
        live_recapture_authorization_required: artifact.live_recapture_authorization_required,
        full_payload_storage_allowed: false,
        full_payload_print_allowed: false,
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
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AL

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- planning_only=true
- payload_source_declaration_execution_performed=false
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

## Reviewed Inputs

- reviewed_input_artifact_count=${artifact.reviewed_input_artifact_count}
- l2v3ak_safe_payload_source_path_status=unknown_or_missing
- l2v3ak_full_payload_artifact_found=false
- l2v3ak_live_recapture_required=true

## Source Type Candidates

- source_type_candidate_count=${artifact.source_type_candidate_count}
- selected_planned_source_type=${artifact.selected_planned_source_type}
- payload_source_declaration_status=${artifact.payload_source_declaration_status}
- source_controlled_payload_artifact_available=${artifact.source_controlled_payload_artifact_available}
- controlled_live_recapture_in_memory_required=${artifact.controlled_live_recapture_in_memory_required}
- raw_write_runner_contract_change_required=${artifact.raw_write_runner_contract_change_required}
- payload_source_declaration_execution_required=${artifact.payload_source_declaration_execution_required}
- live_recapture_authorization_required=${artifact.live_recapture_authorization_required}

## Payload Safety

- full_payload_storage_allowed=false
- full_payload_print_allowed=false
- metadata_only_artifacts_accepted_as_payload=false
- planned_source_type_is_not_payload_source_accepted=true
- planned_source_type_is_not_raw_write_execution_ready=true
- live_recapture_required_does_not_authorize_live_fetch=true

## Runner Contract

- raw_write_runner_input_contract_status=${artifact.raw_write_runner_input_contract_status}
- requires_manifest_metadata=${artifact.raw_write_runner_input_contract.requires_manifest_metadata}
- requires_live_recapture=${artifact.raw_write_runner_input_contract.requires_live_recapture}
- requires_full_pageprops_payload=${artifact.raw_write_runner_input_contract.requires_full_pageprops_payload}
- constructs_raw_data_in_memory_from_pageprops=${artifact.raw_write_runner_input_contract.constructs_raw_data_in_memory_from_pageprops}
- accepts_payload_file_path=${artifact.raw_write_runner_input_contract.accepts_payload_file_path}
- write_mode_invoked=false

## Next Step

${artifact.recommended_next_step}
`;
}

function runPayloadSourceDeclarationPlan(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(loaded);
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };
    const artifact = buildArtifact({ loaded });
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
    return `L2V3AL is controlled payload source declaration planning only.

Allowed:
  --write-files=false

Blocked:
  payload source declaration execution, live recapture execution, raw write
  execution, DB writes, raw_match_data inserts, matches writes,
  matches.external_id changes, live fetch, detail fetch, network, write mode,
  parser/features/training/prediction, schema migration, browser/proxy runtime,
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
    const result = runPayloadSourceDeclarationPlan({
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
                planning_status: result.artifact.planning_status,
                selected_planned_source_type: result.artifact.selected_planned_source_type,
                payload_source_declaration_status: result.artifact.payload_source_declaration_status,
                live_recapture_authorization_required: result.artifact.live_recapture_authorization_required,
                full_payload_storage_allowed: result.artifact.full_payload_storage_allowed,
                full_payload_print_allowed: result.artifact.full_payload_print_allowed,
                metadata_only_artifacts_accepted_as_payload:
                    result.artifact.metadata_only_artifacts_accepted_as_payload,
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
    SELECTED_PLANNED_SOURCE_TYPE,
    PAYLOAD_SOURCE_DECLARATION_STATUS,
    NEXT_REQUIRED_STEP,
    RECOMMENDED_NEXT_STEP,
    MANIFEST_PATH,
    L2V3Y_ARTIFACT_PATH,
    L2V3AA_ARTIFACT_PATH,
    L2V3AC_ARTIFACT_PATH,
    L2V3AE_ARTIFACT_PATH,
    L2V3AG_ARTIFACT_PATH,
    L2V3AI_ARTIFACT_PATH,
    L2V3AJ_ARTIFACT_PATH,
    L2V3AK_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    RAW_WRITE_RUNNER_PATH,
    RAW_WRITE_BASE_HELPER_PATH,
    parseArgs,
    validateCliOptions,
    validateInputs,
    inspectRawWriteRunnerContract,
    buildSourceTypeCandidates,
    buildDeclarationSchema,
    buildValidationRules,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    runPayloadSourceDeclarationPlan,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
