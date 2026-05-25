#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AK';
const PHASE_NAME = 'continued_controlled_raw_write_planning';
const ARTIFACT_STATUS = 'completed_controlled_raw_write_input_source_investigation';
const INPUT_CONTRACT_STATUS = 'requires_manifest_metadata_plus_live_recapture_to_construct_raw_data';
const SAFE_PAYLOAD_SOURCE_PATH_STATUS = 'unknown_or_missing';
const NEXT_REQUIRED_STEP = 'controlled_payload_source_declaration_planning';
const RECOMMENDED_NEXT_STEP = 'Phase 5.21L2V3AL: controlled payload source declaration planning';
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
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.raw_write_input_source_investigation.phase521l2v3ak.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AK.md';
const RAW_WRITE_RUNNER_PATH = 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js';
const RAW_WRITE_BASE_HELPER_PATH = 'scripts/ops/single_league_pageprops_v2_controlled_write_execute.js';
const REVIEWED_INPUTS = Object.freeze([
    ['proposal_manifest', MANIFEST_PATH],
    ['source_inventory_acquisition_result', L2V3Y_ARTIFACT_PATH],
    ['enriched_targets', L2V3AA_ARTIFACT_PATH],
    ['enriched_no_write_verification_result', L2V3AC_ARTIFACT_PATH],
    ['identity_mapping_acceptance_result', L2V3AE_ARTIFACT_PATH],
    ['baseline_acceptance_result', L2V3AG_ARTIFACT_PATH],
    ['final_db_write_authorization_result', L2V3AI_ARTIFACT_PATH],
    ['controlled_raw_match_data_write_execution_plan', L2V3AJ_ARTIFACT_PATH],
]);
const FULL_PAYLOAD_KEYS = Object.freeze([
    'raw_data',
    'rawData',
    'pageProps',
    'source_body',
    'sourceBody',
    'full_body',
    'fullBody',
    'html_body',
    'htmlBody',
    '__NEXT_DATA__',
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
    fs.writeFileSync(absolutePath(filePath), `${JSON.stringify(value, null, 2)}\n`, 'utf8');
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
        value.raw_write_execution_performed === true ||
        value.schema_migration_performed === true ||
        value.parser_features_training_prediction_performed === true
    );
}

function validateInputs(loaded = {}) {
    const errors = [];
    const manifest = loaded.manifest || {};
    const l2v3aj = loaded.l2v3ajArtifact || {};
    const advancedNextSteps = new Set([
        NEXT_REQUIRED_STEP,
        'controlled_payload_source_declaration_execution',
        'controlled_no_write_payload_recapture_planning',
        'controlled_no_write_payload_recapture_execution',
        'no_write_payload_recapture_blocker_investigation',
        'partial_recapture_review_planning',
        'controlled_recapture_result_verification_planning',
        'continued_controlled_raw_write_planning',
    ]);
    const alreadyInvestigated =
        normalizeText(manifest.phase_5_21_l2v3ak_planning_status) === ARTIFACT_STATUS &&
        advancedNextSteps.has(normalizeText(manifest.next_required_step));
    if (
        normalizeText(manifest.next_required_step) !== 'continued_controlled_raw_write_planning' &&
        !alreadyInvestigated
    ) {
        errors.push('manifest next_required_step must be continued_controlled_raw_write_planning');
    }
    if (
        normalizeText(manifest.phase_5_21_l2v3aj_planning_status) !==
        'completed_controlled_raw_match_data_write_execution_planning'
    ) {
        errors.push('manifest L2V3AJ planning status must be completed');
    }
    if (l2v3aj.proposal_phase !== 'Phase 5.21L2V3AJ') errors.push('L2V3AJ artifact is required');
    if (l2v3aj.write_input_source_status !== 'unknown_no_safe_payload_source_path_declared') {
        errors.push('L2V3AJ write_input_source_status must remain unknown_no_safe_payload_source_path_declared');
    }
    if (l2v3aj.raw_write_execution_performed !== false) {
        errors.push('L2V3AJ raw_write_execution_performed must be false');
    }
    if (l2v3aj.db_write_performed !== false) errors.push('L2V3AJ db_write_performed must be false');
    if (l2v3aj.raw_match_data_insert_performed !== false) {
        errors.push('L2V3AJ raw_match_data_insert_performed must be false');
    }
    if (l2v3aj.requires_separate_raw_write_execution_authorization !== true) {
        errors.push('L2V3AJ requires separate raw write execution authorization');
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
                            : 'l2v3ajArtifact';
        if (hasProhibitedWriteState(loaded[key] || {})) {
            errors.push(`${label} contains prohibited write/network/execution state`);
        }
    }
    return { ok: errors.length === 0, errors };
}

function walk(value, visitor, pathParts = []) {
    if (!value || typeof value !== 'object') return;
    if (Array.isArray(value)) {
        value.forEach((entry, index) => walk(entry, visitor, [...pathParts, String(index)]));
        return;
    }
    for (const [key, entryValue] of Object.entries(value)) {
        const nextPath = [...pathParts, key];
        visitor(key, entryValue, nextPath);
        if (entryValue && typeof entryValue === 'object') walk(entryValue, visitor, nextPath);
    }
}

function collectExactKeyPaths(value, keyNames = []) {
    const keySet = new Set(keyNames);
    const paths = [];
    walk(value, (key, entryValue, pathParts) => {
        if (keySet.has(key) && entryValue !== false && entryValue !== null && entryValue !== undefined) {
            paths.push(pathParts.join('.'));
        }
    });
    return paths;
}

function collectScalarPathMatches(value, pattern) {
    const matches = [];
    walk(value, (_key, entryValue, pathParts) => {
        if (entryValue && typeof entryValue === 'object') return;
        const pathText = pathParts.join('.');
        if (pattern.test(pathText)) {
            matches.push({ path: pathText, value: entryValue });
        }
    });
    return matches;
}

function countDistinctScalar(value, pathPattern) {
    const values = new Set();
    for (const match of collectScalarPathMatches(value, pathPattern)) {
        if (normalizeText(match.value)) values.add(normalizeText(match.value));
    }
    return values.size;
}

function inspectArtifacts(loaded = {}) {
    const artifactObjects = [
        ['proposal_manifest', loaded.manifest],
        ['source_inventory_acquisition_result', loaded.l2v3yArtifact],
        ['enriched_targets', loaded.l2v3aaArtifact],
        ['enriched_no_write_verification_result', loaded.l2v3acArtifact],
        ['identity_mapping_acceptance_result', loaded.l2v3aeArtifact],
        ['baseline_acceptance_result', loaded.l2v3agArtifact],
        ['final_db_write_authorization_result', loaded.l2v3aiArtifact],
        ['controlled_raw_match_data_write_execution_plan', loaded.l2v3ajArtifact],
    ];
    return artifactObjects.map(([label, value]) => {
        const fullPayloadKeyPaths = collectExactKeyPaths(value, FULL_PAYLOAD_KEYS);
        const payloadPathCandidates = collectScalarPathMatches(
            value,
            /(^|\.)(safe_)?(payload|raw_data|source_body|pageprops|pageProps).*path$/i
        );
        return {
            label,
            full_payload_key_count: fullPayloadKeyPaths.length,
            full_payload_key_paths: fullPayloadKeyPaths.slice(0, 20),
            payload_path_candidate_count: payloadPathCandidates.length,
            metadata_only: fullPayloadKeyPaths.length === 0,
        };
    });
}

function declaredPayloadPathRecords(loaded = {}) {
    const records = [];
    const sources = [
        ['manifest', loaded.manifest],
        ['l2v3aj', loaded.l2v3ajArtifact],
    ];
    for (const [source, value] of sources) {
        for (const match of collectScalarPathMatches(
            value,
            /(^|\.)(safe_)?(payload|raw_data|source_body|pageprops|pageProps).*path$/i
        )) {
            if (!normalizeText(match.value)) continue;
            records.push({
                candidate_type: 'declared_payload_source_path',
                source,
                path: match.path,
                value: normalizeText(match.value),
                source_controlled_path_exists: fs.existsSync(absolutePath(normalizeText(match.value))),
            });
        }
    }
    return records;
}

function buildPayloadSourceCandidates(loaded = {}) {
    const manifest = loaded.manifest || {};
    const l2v3ag = loaded.l2v3agArtifact || {};
    const l2v3aj = loaded.l2v3ajArtifact || {};
    const declaredPaths = declaredPayloadPathRecords(loaded);
    const candidates = [
        {
            candidate_type: 'declared_payload_source_path',
            candidate_count: declaredPaths.length,
            accepted: false,
            status: declaredPaths.length > 0 ? 'rejected' : 'blocked',
            reason:
                declaredPaths.length > 0
                    ? 'declared path needs a separate validation phase before raw write'
                    : 'no safe payload source path declared',
            evidence: declaredPaths,
        },
        {
            candidate_type: 'manifest_candidate_targets_source_path',
            candidate_count: countDistinctScalar(manifest, /(^|\.)candidate_targets\.\d+\.source_path$/),
            accepted: false,
            status: 'rejected',
            reason: 'source_path points to schedule/source-inventory provenance, not full pageProps or raw_data payload',
        },
        {
            candidate_type: 'source_url_identity_evidence',
            candidate_count: countDistinctScalar(
                manifest,
                /source_(page_url|url_fragment_external_id|inventory_record_key)$/
            ),
            accepted: false,
            status: 'rejected',
            reason: 'source URL evidence verifies identity only and cannot be treated as raw payload',
        },
        {
            candidate_type: 'accepted_baseline_hash_metadata',
            candidate_count: Number(l2v3ag.baseline_accepted_count || manifest.baseline_accepted_count || 0),
            accepted: false,
            status: 'rejected',
            reason: 'accepted baseline hashes are hash gates and not raw_data/pageProps payloads',
        },
        {
            candidate_type: 'pageprops_summary_metadata',
            candidate_count: countDistinctScalar(
                manifest,
                /(^|\.)candidate_targets\.\d+\.pageprops_summary\.parse_status$/
            ),
            accepted: false,
            status: 'rejected',
            reason: 'pageprops_summary contains counts/status metadata only and no pageProps object',
        },
        {
            candidate_type: 'l2v3aj_write_input_source_paths_found',
            candidate_count: Array.isArray(l2v3aj.write_input_source_paths_found)
                ? l2v3aj.write_input_source_paths_found.length
                : 0,
            accepted: false,
            status: 'blocked',
            reason: 'L2V3AJ explicitly recorded no safe payload source paths',
        },
    ];
    return candidates;
}

function inspectRawWriteRunnerContract(rawWriteRunnerSource = '', rawWriteBaseHelperSource = '') {
    const combined = `${rawWriteRunnerSource}\n${rawWriteBaseHelperSource}`;
    const requiresManifest =
        /MANIFEST_PATH/.test(rawWriteRunnerSource) && /readManifestFile/.test(rawWriteRunnerSource);
    const requiresLiveRecapture =
        /recaptureTargetsSequential/.test(rawWriteRunnerSource) &&
        /base\.recaptureTarget/.test(rawWriteRunnerSource) &&
        /fetchHtml/.test(rawWriteBaseHelperSource);
    const buildsRawDataFromPageProps =
        /function buildRawDataForTarget/.test(rawWriteBaseHelperSource) &&
        /pageProps: safePageProps/.test(rawWriteBaseHelperSource);
    const insertsFromRecaptureGate =
        /buildInsertRawMatchDataSql\(recaptureGate\.targets/.test(rawWriteRunnerSource) &&
        /INSERT INTO raw_match_data/.test(rawWriteBaseHelperSource);
    const acceptsPayloadFilePath =
        /payloadSourcePath|safePayloadSourcePath|payload-source-path|raw-data-source-path/.test(combined);
    return {
        status: INPUT_CONTRACT_STATUS,
        runner_reference_path: RAW_WRITE_RUNNER_PATH,
        base_helper_reference_path: RAW_WRITE_BASE_HELPER_PATH,
        requires_manifest_metadata: requiresManifest,
        requires_live_recapture: requiresLiveRecapture,
        requires_full_pageprops_payload: buildsRawDataFromPageProps,
        constructs_raw_data_in_memory_from_pageprops: buildsRawDataFromPageProps,
        inserts_raw_match_data_from_recapture_gate_targets: insertsFromRecaptureGate,
        accepts_payload_file_path: acceptsPayloadFilePath,
        manifest_embeds_payload: false,
        write_mode_invoked: false,
        inspected_by_source_read_only: true,
    };
}

function summarizeCandidateCounts(candidates = []) {
    return {
        payload_source_candidate_count: candidates.length,
        payload_source_accepted_count: candidates.filter(candidate => candidate.accepted === true).length,
        payload_source_rejected_count: candidates.filter(candidate => candidate.status === 'rejected').length,
        payload_source_blocked_count: candidates.filter(candidate => candidate.status === 'blocked').length,
    };
}

function buildArtifact({ loaded = {} } = {}) {
    const artifactSummaries = inspectArtifacts(loaded);
    const payloadCandidates = buildPayloadSourceCandidates(loaded);
    const candidateCounts = summarizeCandidateCounts(payloadCandidates);
    const runnerContract = inspectRawWriteRunnerContract(loaded.rawWriteRunnerSource, loaded.rawWriteBaseHelperSource);
    const fullPayloadArtifactFound = artifactSummaries.some(summary => summary.full_payload_key_count > 0);
    return {
        artifact_type: 'raw_write_input_source_investigation',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        planning_only: true,
        continued_controlled_raw_write_planning: true,
        generated_at: currentTimestamp(),
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        planning_status: ARTIFACT_STATUS,
        controlled_raw_write_input_source_planning_status: SAFE_PAYLOAD_SOURCE_PATH_STATUS,
        raw_write_runner_input_contract_status: runnerContract.status,
        raw_write_runner_input_contract: runnerContract,
        safe_payload_source_path_status: SAFE_PAYLOAD_SOURCE_PATH_STATUS,
        safe_payload_source_path: null,
        ...candidateCounts,
        metadata_only_artifacts_count: artifactSummaries.filter(summary => summary.metadata_only).length,
        reviewed_artifact_summaries: artifactSummaries,
        full_payload_artifact_found: fullPayloadArtifactFound,
        live_recapture_required: runnerContract.requires_live_recapture === true,
        controlled_payload_source_planning_required: true,
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
        metadata_only_artifacts_cannot_be_used_as_raw_payload: true,
        nonexistent_payload_path_cannot_be_accepted: true,
        source_url_evidence_cannot_be_treated_as_raw_payload: true,
        baseline_accepted_cannot_be_treated_as_raw_payload: true,
        full_payload_printed_or_saved: false,
        payload_source_candidates: payloadCandidates,
        blocker: 'write_input_source_status=unknown_no_safe_payload_source_path_declared',
        recommended_next_step: RECOMMENDED_NEXT_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3ak_planning_status: artifact.planning_status,
        phase_5_21_l2v3ak_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ak_report_path: REPORT_PATH,
        controlled_raw_write_input_source_planning_status: artifact.controlled_raw_write_input_source_planning_status,
        raw_write_runner_input_contract_status: artifact.raw_write_runner_input_contract_status,
        safe_payload_source_path_status: artifact.safe_payload_source_path_status,
        safe_payload_source_path: artifact.safe_payload_source_path,
        payload_source_candidate_count: artifact.payload_source_candidate_count,
        payload_source_accepted_count: artifact.payload_source_accepted_count,
        payload_source_rejected_count: artifact.payload_source_rejected_count,
        payload_source_blocked_count: artifact.payload_source_blocked_count,
        metadata_only_artifacts_count: artifact.metadata_only_artifacts_count,
        full_payload_artifact_found: artifact.full_payload_artifact_found,
        live_recapture_required: artifact.live_recapture_required,
        controlled_payload_source_planning_required: artifact.controlled_payload_source_planning_required,
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
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AK

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- planning_only=true
- continued_controlled_raw_write_planning=true
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
- metadata_only_artifacts_count=${artifact.metadata_only_artifacts_count}
- full_payload_artifact_found=${artifact.full_payload_artifact_found}

## Raw Write Runner Input Contract

- raw_write_runner_input_contract_status=${artifact.raw_write_runner_input_contract_status}
- runner_reference_path=${artifact.raw_write_runner_input_contract.runner_reference_path}
- base_helper_reference_path=${artifact.raw_write_runner_input_contract.base_helper_reference_path}
- requires_manifest_metadata=${artifact.raw_write_runner_input_contract.requires_manifest_metadata}
- requires_live_recapture=${artifact.raw_write_runner_input_contract.requires_live_recapture}
- requires_full_pageprops_payload=${artifact.raw_write_runner_input_contract.requires_full_pageprops_payload}
- constructs_raw_data_in_memory_from_pageprops=${artifact.raw_write_runner_input_contract.constructs_raw_data_in_memory_from_pageprops}
- inserts_raw_match_data_from_recapture_gate_targets=${artifact.raw_write_runner_input_contract.inserts_raw_match_data_from_recapture_gate_targets}
- accepts_payload_file_path=${artifact.raw_write_runner_input_contract.accepts_payload_file_path}
- write_mode_invoked=false

## Payload Source Result

- safe_payload_source_path_status=${artifact.safe_payload_source_path_status}
- safe_payload_source_path=${artifact.safe_payload_source_path || 'null'}
- payload_source_candidate_count=${artifact.payload_source_candidate_count}
- payload_source_accepted_count=${artifact.payload_source_accepted_count}
- payload_source_rejected_count=${artifact.payload_source_rejected_count}
- payload_source_blocked_count=${artifact.payload_source_blocked_count}
- live_recapture_required=${artifact.live_recapture_required}
- controlled_payload_source_planning_required=${artifact.controlled_payload_source_planning_required}

## Safety Conclusions

- metadata_only_artifacts_cannot_be_used_as_raw_payload=true
- nonexistent_payload_path_cannot_be_accepted=true
- source_url_evidence_cannot_be_treated_as_raw_payload=true
- baseline_accepted_cannot_be_treated_as_raw_payload=true
- full_payload_printed_or_saved=false
- raw_write_execution_ready=false

## Next Step

${artifact.recommended_next_step}
`;
}

function runRawWriteInputSourceInvestigation(dependencies = {}) {
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
    return `L2V3AK is controlled raw write input source investigation only.

Allowed:
  --write-files=false

Blocked:
  raw write execution, DB writes, raw_match_data inserts, matches writes,
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
    const result = runRawWriteInputSourceInvestigation({
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
                raw_write_runner_input_contract_status: result.artifact.raw_write_runner_input_contract_status,
                safe_payload_source_path_status: result.artifact.safe_payload_source_path_status,
                payload_source_accepted_count: result.artifact.payload_source_accepted_count,
                full_payload_artifact_found: result.artifact.full_payload_artifact_found,
                live_recapture_required: result.artifact.live_recapture_required,
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
    INPUT_CONTRACT_STATUS,
    SAFE_PAYLOAD_SOURCE_PATH_STATUS,
    MANIFEST_PATH,
    L2V3Y_ARTIFACT_PATH,
    L2V3AA_ARTIFACT_PATH,
    L2V3AC_ARTIFACT_PATH,
    L2V3AE_ARTIFACT_PATH,
    L2V3AG_ARTIFACT_PATH,
    L2V3AI_ARTIFACT_PATH,
    L2V3AJ_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    RAW_WRITE_RUNNER_PATH,
    RAW_WRITE_BASE_HELPER_PATH,
    RECOMMENDED_NEXT_STEP,
    NEXT_REQUIRED_STEP,
    parseArgs,
    validateCliOptions,
    validateInputs,
    inspectArtifacts,
    inspectRawWriteRunnerContract,
    buildPayloadSourceCandidates,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    runRawWriteInputSourceInvestigation,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
