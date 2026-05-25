#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AN';
const PHASE_NAME = 'controlled_no_write_payload_recapture_planning';
const ARTIFACT_STATUS = 'completed_controlled_no_write_payload_recapture_planning';
const PLANNED_SOURCE_TYPE = 'controlled_live_recapture_in_memory';
const NEXT_REQUIRED_STEP = 'controlled_no_write_payload_recapture_execution';
const RECOMMENDED_NEXT_STEP = 'Phase 5.21L2V3AO: controlled no-write payload recapture execution';
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
const L2V3AL_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_plan.phase521l2v3al.json';
const L2V3AM_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_result.phase521l2v3am.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_plan.phase521l2v3an.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AN.md';
const RAW_WRITE_RUNNER_PATH = 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js';
const RAW_WRITE_BASE_HELPER_PATH = 'scripts/ops/single_league_pageprops_v2_controlled_write_execute.js';
const RAW_FETCHER_PATH = 'src/infrastructure/fetchers/FotMobRawDetailFetcher.js';
const ROUTE_RECONCILER_PATH = 'src/infrastructure/recon/FotMobRouteIdentityReconciler.js';

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
    ['payload_source_declaration_plan', L2V3AL_ARTIFACT_PATH],
    ['payload_source_declaration_result', L2V3AM_ARTIFACT_PATH],
    ['raw_write_runner_code', RAW_WRITE_RUNNER_PATH],
    ['raw_write_base_helper_code', RAW_WRITE_BASE_HELPER_PATH],
    ['fotmob_raw_detail_fetcher_code', RAW_FETCHER_PATH],
    ['route_identity_reconciler_code', ROUTE_RECONCILER_PATH],
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
    'allowNoWriteRecaptureExecution',
    'executeNoWriteRecapture',
    'executeLiveFetch',
    'executeDetailFetch',
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

const PLANNED_SAFE_OUTPUT_FIELDS = Object.freeze([
    'target_count',
    'per_target_status',
    'external_id',
    'match_id',
    'stable_pageprops_payload_v1_hash',
    'identity_validation_status',
    'route_validation_status',
    'hash_validation_status',
    'structural_summary',
    'blockers',
    'stopping_rule_triggered',
]);

const PLANNED_STOPPING_RULES = Object.freeze([
    'http_403',
    'captcha_or_block_marker',
    'parse_failure',
    'identity_mismatch',
    'date_or_route_mismatch',
    'hash_mismatch_unexplained',
    'duplicate_target',
    'unexpected_schema_drift',
    'network_instability_above_planned_threshold',
    'db_write_path_attempt',
    'full_payload_leak_attempt',
]);

const PLANNED_IDENTITY_VALIDATION_RULES = Object.freeze([
    'requested_schedule_external_id_must_match_accepted_mapping_baseline_and_enriched_targets',
    'observed_detail_identity_must_match_accepted_mapping_where_available',
    'source_url_fragment_external_id_must_match_schedule_external_id',
    'reverse_fixture_must_not_be_accepted',
    'unresolved_date_or_route_blockers_must_stop_recapture',
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
        allowPlanning: true,
        help: false,
        unknown: [],
    };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
        'allow-planning': 'allowPlanning',
        allow_planning: 'allowPlanning',
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
        'allow-no-write-recapture-execution': 'allowNoWriteRecaptureExecution',
        allow_no_write_recapture_execution: 'allowNoWriteRecaptureExecution',
        'execute-no-write-recapture': 'executeNoWriteRecapture',
        execute_no_write_recapture: 'executeNoWriteRecapture',
        'execute-live-fetch': 'executeLiveFetch',
        execute_live_fetch: 'executeLiveFetch',
        'execute-detail-fetch': 'executeDetailFetch',
        execute_detail_fetch: 'executeDetailFetch',
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
    const booleanKeys = new Set(['writeFiles', 'allowPlanning', 'help', ...BLOCKED_TRUE_FLAGS]);

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
    if (normalizeBooleanFlag(options.allowPlanning, true) !== true) {
        errors.push('L2V3AN planning must remain explicitly allowed');
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
        l2v3amArtifact: dependencies.l2v3amArtifact || readJsonFile(L2V3AM_ARTIFACT_PATH),
    };
}

function hasProhibitedExecutionState(value = {}, options = {}) {
    const allowLaterNoWriteRecapture = options.allowLaterNoWriteRecapture === true;
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
        (!allowLaterNoWriteRecapture && value.network_request_performed === true) ||
        value.live_fetch_performed === true ||
        (!allowLaterNoWriteRecapture && value.detail_fetch_performed === true) ||
        (!allowLaterNoWriteRecapture && value.live_recapture_execution_performed === true) ||
        (!allowLaterNoWriteRecapture && value.no_write_payload_recapture_execution_performed === true) ||
        value.schema_migration_performed === true ||
        value.parser_features_training_prediction_performed === true
    );
}

function validateInputs(loaded = {}) {
    const errors = [];
    const manifest = loaded.manifest || {};
    const ak = loaded.l2v3akArtifact || {};
    const al = loaded.l2v3alArtifact || {};
    const am = loaded.l2v3amArtifact || {};
    const advancedNextSteps = new Set([
        NEXT_REQUIRED_STEP,
        'no_write_payload_recapture_contract_clarification',
        'continued_no_write_payload_recapture_planning',
        'no_write_payload_recapture_blocker_investigation',
        'partial_recapture_review_planning',
        'controlled_recapture_result_verification_planning',
    ]);
    const alreadyPlanned =
        normalizeText(manifest.phase_5_21_l2v3an_planning_status) === ARTIFACT_STATUS &&
        advancedNextSteps.has(normalizeText(manifest.next_required_step));

    if (
        normalizeText(manifest.next_required_step) !== 'controlled_no_write_payload_recapture_planning' &&
        !alreadyPlanned
    ) {
        errors.push('manifest next_required_step must be controlled_no_write_payload_recapture_planning');
    }
    if (normalizeText(am.artifact_status) !== 'completed_controlled_payload_source_declaration_execution') {
        errors.push('L2V3AM payload source declaration result must be completed');
    }
    if (am.payload_source_declaration_performed !== true || am.payload_source_status !== 'declared') {
        errors.push('L2V3AM must declare payload source before L2V3AN planning');
    }
    if (normalizeText(am.selected_source_type) !== PLANNED_SOURCE_TYPE) {
        errors.push('L2V3AM selected source type must be controlled_live_recapture_in_memory');
    }
    if (am.live_recapture_required !== true || am.live_recapture_authorization_required !== true) {
        errors.push('L2V3AM must require separately authorized live recapture');
    }
    if (
        am.full_payload_storage_allowed !== false ||
        am.full_payload_print_allowed !== false ||
        am.in_memory_only !== true
    ) {
        errors.push('L2V3AM payload safety flags must remain in-memory only with no full payload storage/print');
    }
    if (am.raw_write_execution_ready !== false || am.raw_write_execution_performed !== false) {
        errors.push('L2V3AM must not be raw write ready or executed');
    }
    if (am.db_write_performed !== false || am.raw_match_data_insert_performed !== false) {
        errors.push('L2V3AM must not have DB writes or raw_match_data inserts');
    }
    if (normalizeText(al.selected_planned_source_type) !== PLANNED_SOURCE_TYPE) {
        errors.push('L2V3AL selected planned source type must match AM declaration');
    }
    if (ak.full_payload_artifact_found !== false || ak.safe_payload_source_path !== null) {
        errors.push('L2V3AK must still have no source-controlled full payload path');
    }
    if (ak.live_recapture_required !== true) errors.push('L2V3AK must identify live recapture as required');
    for (const [label, value] of [
        ['proposal_manifest', loaded.manifest],
        ['raw_write_input_source_investigation', ak],
        ['payload_source_declaration_plan', al],
        ['payload_source_declaration_result', am],
    ]) {
        const allowLaterNoWriteRecapture =
            label === 'proposal_manifest' &&
            normalizeText(value?.phase_5_21_l2v3ao_execution_status) !== '' &&
            value?.db_write_performed === false &&
            value?.raw_match_data_insert_performed === false &&
            value?.raw_write_execution_performed === false;
        if (hasProhibitedExecutionState(value || {}, { allowLaterNoWriteRecapture })) {
            errors.push(`${label} contains prohibited write/fetch/recapture execution state`);
        }
    }
    return { ok: errors.length === 0, errors };
}

function plannedTargetCountFrom(loaded = {}) {
    return Number(
        loaded.l2v3amArtifact?.target_count ||
            loaded.l2v3alArtifact?.target_count ||
            loaded.l2v3alArtifact?.declaration_schema?.planned_values?.target_count ||
            50
    );
}

function buildPlanArtifact({ loaded = {} } = {}) {
    const plannedTargetCount = plannedTargetCountFrom(loaded);
    return {
        artifact_type: 'no_write_payload_recapture_plan',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        planning_status: ARTIFACT_STATUS,
        recapture_planning_status: 'planned_not_executed',
        generated_at: currentTimestamp(),
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        planned_source_type: PLANNED_SOURCE_TYPE,
        planned_target_count: plannedTargetCount,
        recapture_scope: {
            target_count: plannedTargetCount,
            source_type: PLANNED_SOURCE_TYPE,
            source_endpoint_or_fetcher:
                'existing pageProps v2 HTML hydration fetcher path; future authorization required',
            no_browser_proxy_captcha_bypass: true,
            no_raw_write: true,
            no_db_write: true,
        },
        current_user_instruction_authorizes_planning_only: true,
        no_write_payload_recapture_execution_performed: false,
        live_recapture_execution_performed: false,
        live_recapture_authorization_required: true,
        no_write_recapture_authorization_required: true,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        raw_write_execution_performed: false,
        network_request_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        raw_write_runner_write_mode_invoked: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        in_memory_only: true,
        full_payload_storage_allowed: false,
        full_payload_print_allowed: false,
        cookies_tokens_headers_persisted: false,
        metadata_only_artifacts_accepted_as_payload: false,
        source_url_evidence_accepted_as_payload: false,
        baseline_hashes_accepted_as_payload: false,
        planned_safe_output_fields: [...PLANNED_SAFE_OUTPUT_FIELDS],
        planned_stopping_rules: [...PLANNED_STOPPING_RULES],
        planned_stopping_rule_count: PLANNED_STOPPING_RULES.length,
        planned_identity_validation_rules: [...PLANNED_IDENTITY_VALIDATION_RULES],
        planned_identity_validation_rule_count: PLANNED_IDENTITY_VALIDATION_RULES.length,
        planned_hash_validation_policy:
            'future no-write recapture may compute stable_pageprops_payload_v1 hashes in memory, but must not print or save full payloads; hash mismatch stops or blocks and must not auto-update baseline',
        recapture_execution_ready: false,
        raw_write_execution_ready: false,
        recapture_plan_is_not_recapture_execution: true,
        recapture_plan_is_not_raw_write_readiness: true,
        future_recapture_success_does_not_authorize_raw_write_by_itself: true,
        requires_separate_raw_write_execution_authorization: true,
        recommended_next_step: RECOMMENDED_NEXT_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3an_planning_status: ARTIFACT_STATUS,
        phase_5_21_l2v3an_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3an_report_path: REPORT_PATH,
        no_write_payload_recapture_planning_status: artifact.recapture_planning_status,
        planned_source_type: artifact.planned_source_type,
        planned_target_count: artifact.planned_target_count,
        live_recapture_execution_performed: false,
        live_recapture_authorization_required: true,
        no_write_recapture_authorization_required: true,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        raw_write_execution_performed: false,
        in_memory_only: true,
        full_payload_storage_allowed: false,
        full_payload_print_allowed: false,
        planned_stopping_rule_count: artifact.planned_stopping_rule_count,
        planned_identity_validation_rule_count: artifact.planned_identity_validation_rule_count,
        recapture_execution_ready: false,
        raw_write_execution_ready: false,
        requires_separate_raw_write_execution_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AN

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- planning_status=${artifact.planning_status}
- recapture_planning_status=${artifact.recapture_planning_status}
- planned_source_type=${artifact.planned_source_type}
- planned_target_count=${artifact.planned_target_count}
- no_write_payload_recapture_execution_performed=false
- live_recapture_execution_performed=false
- network_request_performed=false
- live_fetch_performed=false
- detail_fetch_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- raw_write_execution_performed=false
- raw_write_runner_write_mode_invoked=false
- parser_features_training_prediction_performed=false

## Authorization

- current_user_instruction_authorizes_planning_only=true
- live_recapture_authorization_required=true
- no_write_recapture_authorization_required=true
- recapture_execution_ready=false
- raw_write_execution_ready=false
- requires_separate_raw_write_execution_authorization=true

## Payload Safety

- in_memory_only=true
- full_payload_storage_allowed=false
- full_payload_print_allowed=false
- cookies_tokens_headers_persisted=false
- metadata_only_artifacts_accepted_as_payload=false
- source_url_evidence_accepted_as_payload=false
- baseline_hashes_accepted_as_payload=false

## Planned Safe Output Fields

${artifact.planned_safe_output_fields.map(field => `- ${field}`).join('\n')}

## Planned Identity Validation

- planned_identity_validation_rule_count=${artifact.planned_identity_validation_rule_count}
${artifact.planned_identity_validation_rules.map(rule => `- ${rule}`).join('\n')}

## Planned Hash Validation Policy

${artifact.planned_hash_validation_policy}

## Planned Stopping Rules

- planned_stopping_rule_count=${artifact.planned_stopping_rule_count}
${artifact.planned_stopping_rules.map(rule => `- ${rule}`).join('\n')}

## Raw Write Relationship

- recapture_plan_is_not_recapture_execution=true
- recapture_plan_is_not_raw_write_readiness=true
- future_recapture_success_does_not_authorize_raw_write_by_itself=true
- raw_write_execution_ready=false
- raw_write_execution_performed=false

## Next Step

${artifact.recommended_next_step}

This next step requires a new, separate, explicit no-write live recapture authorization.
`;
}

function runNoWritePayloadRecapturePlan(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(loaded);
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };
    const artifact = buildPlanArtifact({ loaded });
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
    return `L2V3AN plans controlled no-write payload recapture only.

Allowed:
  --write-files=false
  --allow-planning=yes

Blocked:
  no-write recapture execution, live fetch, detail fetch, network, DB writes,
  raw_match_data inserts, matches writes, matches.external_id changes, raw write
  execution, write mode, parser/features/training/prediction, schema migration,
  browser/proxy runtime, and full payload printing/saving.
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
    const result = runNoWritePayloadRecapturePlan({
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
                planned_source_type: result.artifact.planned_source_type,
                planned_target_count: result.artifact.planned_target_count,
                live_recapture_execution_performed: result.artifact.live_recapture_execution_performed,
                no_write_recapture_authorization_required: result.artifact.no_write_recapture_authorization_required,
                raw_write_execution_ready: result.artifact.raw_write_execution_ready,
                db_write_performed: result.artifact.db_write_performed,
                raw_match_data_insert_performed: result.artifact.raw_match_data_insert_performed,
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
    PLANNED_SOURCE_TYPE,
    NEXT_REQUIRED_STEP,
    RECOMMENDED_NEXT_STEP,
    MANIFEST_PATH,
    L2V3AK_ARTIFACT_PATH,
    L2V3AL_ARTIFACT_PATH,
    L2V3AM_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    PLANNED_SAFE_OUTPUT_FIELDS,
    PLANNED_STOPPING_RULES,
    PLANNED_IDENTITY_VALIDATION_RULES,
    parseArgs,
    validateCliOptions,
    validateInputs,
    buildPlanArtifact,
    buildReport,
    updateManifestMetadata,
    runNoWritePayloadRecapturePlan,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
