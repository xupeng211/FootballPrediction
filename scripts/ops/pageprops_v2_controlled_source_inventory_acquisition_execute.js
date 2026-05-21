#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {
    FotMobSourceInventoryAdapter,
    ROUTE_KIND: L1_SOURCE_INVENTORY_ROUTE_KIND,
} = require('../../src/infrastructure/services/FotMobSourceInventoryAdapter');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3Y';
const PHASE_NAME = 'controlled_no_write_source_inventory_acquisition_execution';
const GENERATED_AT = '2026-05-21T14:20:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3X_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_plan.phase521l2v3x.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Y.md';
const PLANNED_ENDPOINT = '/api/data/leagues?id=53&season=20252026';
const ENDPOINT_URL = `https://www.fotmob.com${PLANNED_ENDPOINT}`;
const PLANNED_SCOPE = 'ligue1_2025_2026_profile_001_current_50_candidates_metadata_only_source_inventory';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const CANDIDATE_SCOPE_COUNT = 50;
const MAX_RESPONSE_BYTES = 5 * 1024 * 1024;

const NEXT_STEPS = Object.freeze({
    regeneratedTargets: {
        recommended_next_step: 'Phase 5.21L2V3Z: enriched target regeneration planning',
        next_required_step: 'enriched_target_regeneration_planning',
    },
    candidateMatching: {
        recommended_next_step: 'Phase 5.21L2V3Z: source inventory candidate matching investigation',
        next_required_step: 'source_inventory_candidate_matching_investigation',
    },
    continuedInvestigation: {
        recommended_next_step: 'Phase 5.21L2V3Z: continued source inventory acquisition investigation',
        next_required_step: 'continued_source_inventory_acquisition_investigation',
    },
    schemaAdaptation: {
        recommended_next_step: 'Phase 5.21L2V3Z: source inventory schema adaptation planning',
        next_required_step: 'source_inventory_schema_adaptation_planning',
    },
});

const SAFE_METADATA_FIELDS = Object.freeze([
    'source_page_url',
    'source_page_url_base',
    'source_url_fragment_external_id',
    'source_slug',
    'source_route_code',
    'schedule_external_id',
    'schedule_date',
    'schedule_home_team',
    'schedule_away_team',
    'source_inventory_record_key',
    'source_inventory_generated_at',
    'identity_evidence_status',
    'source_endpoint_summary',
    'acquisition_status',
    'safe_error_summary',
]);

const PAYLOAD_SAFETY_RULES = Object.freeze([
    'do_not_save_full_api_payload',
    'do_not_print_full_api_payload',
    'do_not_save_full_pageProps',
    'do_not_print_full_pageProps',
    'do_not_save_full_raw_data',
    'do_not_print_full_raw_data',
    'do_not_save_full_html_or_source_body',
    'do_not_print_full_html_or_source_body',
    'metadata_only_safe_fields_only',
    'do_not_record_cookies_tokens_headers',
    'stop_on_block_captcha_or_abnormal_response',
]);

const STOPPING_RULES = Object.freeze([
    'http_block_or_captcha_signal',
    'rate_limit_signal',
    'parse_failure_spike',
    'widespread_non_200_response',
    'unexpected_schema_drift',
    'payload_too_large_or_suspicious_small_payload',
    'source_identity_mismatch',
    'any_attempted_write_path',
    'browser_proxy_captcha_bypass_required',
    'full_payload_persistence_attempt',
]);

const BLOCK_MARKERS = Object.freeze([
    'captcha',
    'cloudflare',
    'cf-ray',
    'access denied',
    'checking your browser',
    'just a moment',
    'unusual traffic',
    'temporarily blocked',
]);

const BLOCKED_TRUE_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowRawMatchDataWrite',
    'allowMatchesWrite',
    'allowSchemaMigration',
    'allowParserImplementation',
    'allowFeatureExtraction',
    'allowTraining',
    'allowPrediction',
    'allowBrowserRuntime',
    'allowProxyRuntime',
    'allowMatchDetailFetch',
    'allowRawWriteRetry',
    'acceptIdentityMapping',
    'acceptBaseline',
    'printFullBody',
    'saveFullBody',
    'printFullJson',
    'saveFullJson',
    'printFullPageProps',
    'saveFullPageProps',
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
        liveFetch: null,
        sourceInventoryAuthorization: null,
        retry: 0,
        help: false,
        unknown: [],
    };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
        'live-fetch': 'liveFetch',
        live_fetch: 'liveFetch',
        'source-inventory-authorization': 'sourceInventoryAuthorization',
        source_inventory_authorization: 'sourceInventoryAuthorization',
        retry: 'retry',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
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
        'allow-match-detail-fetch': 'allowMatchDetailFetch',
        allow_match_detail_fetch: 'allowMatchDetailFetch',
        'allow-raw-write-retry': 'allowRawWriteRetry',
        allow_raw_write_retry: 'allowRawWriteRetry',
        'accept-identity-mapping': 'acceptIdentityMapping',
        accept_identity_mapping: 'acceptIdentityMapping',
        'accept-baseline': 'acceptBaseline',
        accept_baseline: 'acceptBaseline',
        'print-full-body': 'printFullBody',
        print_full_body: 'printFullBody',
        'save-full-body': 'saveFullBody',
        save_full_body: 'saveFullBody',
        'print-full-json': 'printFullJson',
        print_full_json: 'printFullJson',
        'save-full-json': 'saveFullJson',
        save_full_json: 'saveFullJson',
        'print-full-pageprops': 'printFullPageProps',
        print_full_pageprops: 'printFullPageProps',
        'save-full-pageprops': 'saveFullPageProps',
        save_full_pageprops: 'saveFullPageProps',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'writeFiles',
        'liveFetch',
        'sourceInventoryAuthorization',
        'help',
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

function cliName(flagName) {
    return flagName.replace(/[A-Z]/g, match => `-${match.toLowerCase()}`);
}

function validateCliOptions(options = {}) {
    const errors = [];
    if (Array.isArray(options.unknown) && options.unknown.length > 0) {
        errors.push(`unknown arguments: ${options.unknown.join(', ')}`);
    }
    if (normalizeBooleanFlag(options.liveFetch) !== true) {
        errors.push('live-fetch=yes is required for Phase 5.21L2V3Y controlled execution');
    }
    if (normalizeBooleanFlag(options.sourceInventoryAuthorization) !== true) {
        errors.push('source-inventory-authorization=yes is required');
    }
    if (Number(options.retry || 0) !== 0) {
        errors.push('retry must be 0');
    }
    for (const flagName of BLOCKED_TRUE_FLAGS) {
        if (normalizeBooleanFlag(options[flagName], false) === true) {
            errors.push(`${cliName(flagName)}=yes is blocked`);
        }
    }
    return { ok: errors.length === 0, errors };
}

function validateInputs(manifest = {}, l2v3xArtifact = {}) {
    const errors = [];
    if (!Array.isArray(manifest.candidate_targets) || manifest.candidate_targets.length !== CANDIDATE_SCOPE_COUNT) {
        errors.push('manifest candidate_targets must contain 50 targets');
    }
    if (normalizeText(manifest.next_required_step) !== 'controlled_no_write_source_inventory_acquisition_execution') {
        errors.push('manifest next_required_step must be controlled_no_write_source_inventory_acquisition_execution');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must remain 0');
    }
    if (normalizeText(l2v3xArtifact.proposal_phase) !== 'Phase 5.21L2V3X') {
        errors.push('L2V3X artifact must be present');
    }
    if (l2v3xArtifact.live_fetch_performed !== false) {
        errors.push('L2V3X live_fetch_performed must remain false');
    }
    if (l2v3xArtifact.db_write_performed !== false) {
        errors.push('L2V3X db_write_performed must remain false');
    }
    if (normalizeText(l2v3xArtifact.planned_source_endpoint) !== PLANNED_ENDPOINT) {
        errors.push('L2V3X planned_source_endpoint must match the planned endpoint');
    }
    if (normalizeText(l2v3xArtifact.planned_acquisition_scope) !== PLANNED_SCOPE) {
        errors.push('L2V3X planned_acquisition_scope must match the planned scope');
    }
    if (Number(l2v3xArtifact.planned_candidate_scope_count || 0) !== CANDIDATE_SCOPE_COUNT) {
        errors.push('L2V3X planned_candidate_scope_count must be 50');
    }
    if (l2v3xArtifact.acquisition_execution_authorization_required !== true) {
        errors.push('L2V3X acquisition_execution_authorization_required must remain true');
    }
    if (l2v3xArtifact.baseline_acceptance_required !== true) {
        errors.push('L2V3X baseline_acceptance_required must remain true');
    }
    if (l2v3xArtifact.final_db_write_authorization_required !== true) {
        errors.push('L2V3X final_db_write_authorization_required must remain true');
    }
    if (Number(l2v3xArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3X accepted_mapping_count must remain 0');
    }
    if (l2v3xArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3X raw_write_ready_for_execution must remain false');
    }
    return { ok: errors.length === 0, errors };
}

function buildContentTypeSummary(headers) {
    if (!headers || typeof headers.get !== 'function') return null;
    return headers.get('content-type') || null;
}

function buildContentLength(headers) {
    if (!headers || typeof headers.get !== 'function') return null;
    const value = headers.get('content-length');
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}

function detectBlockedMarkers(bodyText = '') {
    const normalized = String(bodyText).toLowerCase();
    return BLOCK_MARKERS.filter(marker => normalized.includes(marker));
}

function buildStoppedFetchResult({
    statusCode = null,
    contentType = null,
    stopReason = null,
    safeErrorSummary = null,
    blockedMarkers = [],
    parsed = false,
    parseStatus = 'not_parsed',
} = {}) {
    return {
        ok: false,
        url: ENDPOINT_URL,
        endpoint_used: PLANNED_ENDPOINT,
        endpoint_http_status: statusCode,
        endpoint_parsed: parsed,
        parse_status: parseStatus,
        content_type_summary: contentType ? [contentType] : [],
        blocked_markers: blockedMarkers,
        stop_reason: stopReason,
        safe_error_summary: safeErrorSummary || stopReason || 'unknown_source_inventory_acquisition_error',
        json: null,
    };
}

async function fetchSourceInventoryJson(dependencies = {}) {
    const fetchImpl = dependencies.fetch || global.fetch;
    if (typeof fetchImpl !== 'function') {
        return buildStoppedFetchResult({
            stopReason: 'fetch_unavailable',
            safeErrorSummary: 'global_fetch_unavailable',
        });
    }

    let response;
    try {
        response = await fetchImpl(ENDPOINT_URL, { method: 'GET' });
    } catch (error) {
        return buildStoppedFetchResult({
            stopReason: 'request_failed',
            safeErrorSummary: `request_failed:${normalizeText(error.message).slice(0, 80)}`,
        });
    }

    const statusCode = Number(response?.status) || null;
    const contentType = buildContentTypeSummary(response?.headers);
    const contentLength = buildContentLength(response?.headers);
    if (contentLength && contentLength > MAX_RESPONSE_BYTES) {
        return buildStoppedFetchResult({
            statusCode,
            contentType,
            stopReason: 'payload_too_large_or_suspicious_small_payload',
            safeErrorSummary: 'content_length_exceeded_metadata_only_limit',
        });
    }

    let bodyText = '';
    try {
        bodyText = await response.text();
    } catch (error) {
        return buildStoppedFetchResult({
            statusCode,
            contentType,
            stopReason: 'response_text_read_failed',
            safeErrorSummary: `response_text_read_failed:${normalizeText(error.message).slice(0, 80)}`,
        });
    }

    const bodyByteLength = Buffer.byteLength(bodyText, 'utf8');
    if (bodyByteLength > MAX_RESPONSE_BYTES) {
        return buildStoppedFetchResult({
            statusCode,
            contentType,
            stopReason: 'payload_too_large_or_suspicious_small_payload',
            safeErrorSummary: 'response_body_exceeded_metadata_only_limit',
        });
    }

    const blockedMarkers = detectBlockedMarkers(bodyText);
    if (statusCode === 403 || blockedMarkers.length > 0) {
        return buildStoppedFetchResult({
            statusCode,
            contentType,
            stopReason: 'http_block_or_captcha_signal',
            safeErrorSummary:
                statusCode === 403 ? 'http_403_source_inventory_blocked' : 'block_or_captcha_marker_detected',
            blockedMarkers,
        });
    }
    if (statusCode === 429) {
        return buildStoppedFetchResult({
            statusCode,
            contentType,
            stopReason: 'rate_limit_signal',
            safeErrorSummary: 'http_429_rate_limited',
        });
    }
    if (statusCode < 200 || statusCode >= 300) {
        return buildStoppedFetchResult({
            statusCode,
            contentType,
            stopReason: 'widespread_non_200_response',
            safeErrorSummary: `http_${statusCode}_source_inventory_non_200`,
        });
    }

    try {
        return {
            ok: true,
            url: ENDPOINT_URL,
            endpoint_used: PLANNED_ENDPOINT,
            endpoint_http_status: statusCode,
            endpoint_parsed: true,
            parse_status: 'parsed_json',
            content_type_summary: contentType ? [contentType] : [],
            blocked_markers: [],
            stop_reason: null,
            safe_error_summary: null,
            json: JSON.parse(bodyText),
        };
    } catch {
        return buildStoppedFetchResult({
            statusCode,
            contentType,
            stopReason: 'unexpected_schema_drift',
            safeErrorSummary: 'invalid_json_source_inventory_response',
            parseStatus: 'invalid_json',
        });
    }
}

function createSourceInventoryAdapter(dependencies = {}) {
    if (dependencies.sourceInventoryAdapter) return dependencies.sourceInventoryAdapter;
    if (typeof dependencies.createSourceInventoryAdapter === 'function') {
        return dependencies.createSourceInventoryAdapter();
    }
    return new FotMobSourceInventoryAdapter({
        configManager: dependencies.configManager,
        parser: dependencies.discoveryParser,
        logger: dependencies.logger,
    });
}

function parseSourceInventoryRecords(sourceJson, dependencies = {}, generatedAt = GENERATED_AT) {
    if (Array.isArray(dependencies.sourceRecords)) return dependencies.sourceRecords;
    const adapter = createSourceInventoryAdapter(dependencies);
    return adapter.parseSourceInventory(sourceJson, {
        source: 'fotmob',
        leagueId: LEAGUE_ID,
        season: SEASON,
        sourceInventoryGeneratedAt: generatedAt,
        generatedAt,
    });
}

function evidenceStatus(record = {}, externalId = null) {
    const fragment = normalizeText(record.source_url_fragment_external_id);
    const requested = normalizeText(externalId || record.external_id);
    if (
        record.source_page_url &&
        record.source_page_url_base &&
        record.source_inventory_record_key &&
        fragment &&
        requested &&
        fragment === requested
    ) {
        return 'complete';
    }
    if (
        record.source_page_url ||
        record.source_page_url_base ||
        record.source_url_fragment_external_id ||
        record.source_inventory_record_key
    ) {
        return 'partial';
    }
    return 'missing';
}

function safeSourceRecord(record = {}, target = {}, generatedAt = GENERATED_AT, fetchResult = {}) {
    const externalId = normalizeText(target.external_id);
    const status = evidenceStatus(record, externalId);
    return {
        target_id: target.target_id || null,
        match_id: target.match_id || null,
        external_id: externalId || null,
        acquired_source_inventory_record: true,
        source_page_url: record.source_page_url || null,
        source_page_url_base: record.source_page_url_base || null,
        source_url_fragment_external_id: record.source_url_fragment_external_id || null,
        source_slug: record.source_slug || null,
        source_route_code: record.source_route_code || null,
        schedule_external_id: record.schedule_external_id || record.external_id || externalId || null,
        schedule_date: record.schedule_date || record.kickoff_time || record.match_date || target.schedule_date || null,
        schedule_home_team: record.schedule_home_team || record.home_team || target.schedule_home_team || null,
        schedule_away_team: record.schedule_away_team || record.away_team || target.schedule_away_team || null,
        source_inventory_record_key: record.source_inventory_record_key || null,
        source_inventory_generated_at: record.source_inventory_generated_at || generatedAt,
        identity_evidence_status: status,
        source_endpoint_summary: PLANNED_ENDPOINT,
        acquisition_status: 'acquired',
        safe_error_summary: null,
        endpoint_http_status: fetchResult.endpoint_http_status || null,
        parsed_status: fetchResult.parse_status || null,
        target_match_status: 'matched_current_candidate',
    };
}

function missingSourceRecord(target = {}, status, safeErrorSummary, fetchResult = {}, generatedAt = GENERATED_AT) {
    return {
        target_id: target.target_id || null,
        match_id: target.match_id || null,
        external_id: normalizeText(target.external_id) || null,
        acquired_source_inventory_record: false,
        source_page_url: null,
        source_page_url_base: null,
        source_url_fragment_external_id: null,
        source_slug: null,
        source_route_code: null,
        schedule_external_id: target.schedule_external_id || target.external_id || null,
        schedule_date: target.schedule_date || target.kickoff_time || target.match_date || null,
        schedule_home_team: target.schedule_home_team || target.home_team || null,
        schedule_away_team: target.schedule_away_team || target.away_team || null,
        source_inventory_record_key: null,
        source_inventory_generated_at: generatedAt,
        identity_evidence_status: 'missing',
        source_endpoint_summary: PLANNED_ENDPOINT,
        acquisition_status: status,
        safe_error_summary: safeErrorSummary,
        endpoint_http_status: fetchResult.endpoint_http_status || null,
        parsed_status: fetchResult.parse_status || null,
        target_match_status:
            status === 'not_found' ? 'not_found_in_source_inventory' : 'not_matched_due_to_acquisition_stop',
    };
}

function mapSourceRecordsByExternalId(sourceRecords = []) {
    const result = new Map();
    for (const record of Array.isArray(sourceRecords) ? sourceRecords : []) {
        const externalId = normalizeText(record?.external_id || record?.schedule_external_id);
        if (externalId && !result.has(externalId)) result.set(externalId, record);
    }
    return result;
}

function classifyStoppedAcquisition(fetchResult = {}) {
    if (fetchResult.stop_reason === 'http_block_or_captcha_signal' || fetchResult.stop_reason === 'rate_limit_signal') {
        return 'blocked';
    }
    return 'failed';
}

function buildSafeMetadataRecords({
    manifest = {},
    sourceRecords = [],
    fetchResult = {},
    generatedAt = GENERATED_AT,
} = {}) {
    const targets = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    if (!fetchResult.ok) {
        const stoppedStatus = classifyStoppedAcquisition(fetchResult);
        return targets.map(target =>
            missingSourceRecord(target, stoppedStatus, fetchResult.safe_error_summary, fetchResult, generatedAt)
        );
    }

    const byExternalId = mapSourceRecordsByExternalId(sourceRecords);
    return targets.map(target => {
        const externalId = normalizeText(target.external_id);
        const record = byExternalId.get(externalId);
        if (!record) {
            return missingSourceRecord(
                target,
                'not_found',
                'source_record_not_found_for_current_candidate',
                fetchResult,
                generatedAt
            );
        }
        return safeSourceRecord(record, target, generatedAt, fetchResult);
    });
}

function countWhere(records, predicate) {
    return records.filter(predicate).length;
}

function deriveArtifactStatus(records = [], fetchResult = {}) {
    if (countWhere(records, item => item.acquisition_status === 'blocked') > 0) {
        return 'blocked_metadata_only_source_inventory_acquisition_execution';
    }
    if (!fetchResult.ok && fetchResult.stop_reason === 'unexpected_schema_drift') {
        return 'failed_schema_drift_metadata_only_source_inventory_acquisition_execution';
    }
    if (!fetchResult.ok) {
        return 'failed_metadata_only_source_inventory_acquisition_execution';
    }
    return 'completed_metadata_only_source_inventory_acquisition_execution';
}

function deriveNextStep(artifact) {
    if (artifact.acquisition_blocked_count > 0) return NEXT_STEPS.continuedInvestigation;
    if (artifact.endpoint_parsed !== true || artifact.source_records_seen_count === 0) {
        return NEXT_STEPS.schemaAdaptation;
    }
    if (
        artifact.candidate_targets_matched_count === CANDIDATE_SCOPE_COUNT &&
        artifact.candidate_targets_with_source_page_url === CANDIDATE_SCOPE_COUNT &&
        artifact.candidate_targets_with_source_page_url_base === CANDIDATE_SCOPE_COUNT &&
        artifact.candidate_targets_with_source_url_fragment_external_id === CANDIDATE_SCOPE_COUNT
    ) {
        return NEXT_STEPS.regeneratedTargets;
    }
    return NEXT_STEPS.candidateMatching;
}

function buildArtifact({
    manifest = {},
    l2v3xArtifact = {},
    fetchResult = {},
    sourceRecords = [],
    generatedAt = GENERATED_AT,
} = {}) {
    const safeRecords = buildSafeMetadataRecords({ manifest, sourceRecords, fetchResult, generatedAt });
    const artifact = {
        artifact_type: 'controlled_source_inventory_acquisition_result',
        artifact_status: deriveArtifactStatus(safeRecords, fetchResult),
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3X',
        generated_at: generatedAt,
        acquisition_attempted: true,
        live_fetch_performed: true,
        live_source_check_performed: true,
        source_acquisition_execution_performed: true,
        network_request_performed: true,
        db_write_performed: false,
        raw_insert_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        browser_proxy_captcha_bypass_performed: false,
        proxy_runtime_performed: false,
        browser_runtime_performed: false,
        match_detail_fetch_performed: false,
        match_details_endpoint_fetch_performed: false,
        detail_pageprops_fetch_performed: false,
        bulk_crawl_spider_performed: false,
        retry_performed: false,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        endpoint_used: PLANNED_ENDPOINT,
        endpoint_url_summary: PLANNED_ENDPOINT,
        planned_acquisition_scope: PLANNED_SCOPE,
        planned_target_league_id: LEAGUE_ID,
        planned_target_season: SEASON,
        candidate_scope_count: Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets.length : 0,
        endpoint_http_status: fetchResult.endpoint_http_status,
        endpoint_parsed: fetchResult.endpoint_parsed === true,
        endpoint_parse_status: fetchResult.parse_status,
        endpoint_stop_reason: fetchResult.stop_reason,
        endpoint_blocked_markers_found_count: Array.isArray(fetchResult.blocked_markers)
            ? fetchResult.blocked_markers.length
            : 0,
        content_type_summary: fetchResult.content_type_summary || [],
        source_records_seen_count: fetchResult.ok ? sourceRecords.length : 0,
        candidate_targets_matched_count: countWhere(safeRecords, item => item.acquired_source_inventory_record),
        candidate_targets_with_source_page_url: countWhere(safeRecords, item => Boolean(item.source_page_url)),
        candidate_targets_with_source_page_url_base: countWhere(safeRecords, item =>
            Boolean(item.source_page_url_base)
        ),
        candidate_targets_with_source_url_fragment_external_id: countWhere(safeRecords, item =>
            Boolean(item.source_url_fragment_external_id)
        ),
        candidate_targets_with_source_inventory_record_key: countWhere(safeRecords, item =>
            Boolean(item.source_inventory_record_key)
        ),
        identity_evidence_complete_count: countWhere(safeRecords, item => item.identity_evidence_status === 'complete'),
        identity_evidence_partial_count: countWhere(safeRecords, item => item.identity_evidence_status === 'partial'),
        identity_evidence_missing_count: countWhere(safeRecords, item => item.identity_evidence_status === 'missing'),
        acquisition_blocked_count: countWhere(safeRecords, item => item.acquisition_status === 'blocked'),
        acquisition_failed_count: countWhere(safeRecords, item => item.acquisition_status === 'failed'),
        acquisition_not_found_count: countWhere(safeRecords, item => item.acquisition_status === 'not_found'),
        safe_metadata_record_count: safeRecords.length,
        safe_metadata_fields: SAFE_METADATA_FIELDS,
        payload_safety_rules: PAYLOAD_SAFETY_RULES,
        stopping_rules: STOPPING_RULES,
        payload_safety_result: {
            full_api_payload_saved: false,
            full_api_payload_printed: false,
            full_pageProps_saved: false,
            full_pageProps_printed: false,
            full_raw_data_saved: false,
            full_raw_data_printed: false,
            full_html_or_source_body_saved: false,
            full_html_or_source_body_printed: false,
            cookies_tokens_headers_recorded: false,
            metadata_only_output: true,
        },
        source_endpoint_summary: {
            endpoint_used: PLANNED_ENDPOINT,
            route_kind: L1_SOURCE_INVENTORY_ROUTE_KIND,
            request_count: 1,
            retry_count: 0,
            browser_used: false,
            proxy_used: false,
            captcha_bypass_used: false,
            detail_page_fetch_used: false,
            match_details_endpoint_fetch_used: false,
        },
        upstream_plan_context: {
            l2v3x_artifact_status: l2v3xArtifact.artifact_status || null,
            l2v3x_planned_source_endpoint: l2v3xArtifact.planned_source_endpoint || null,
            l2v3x_planned_candidate_scope_count: l2v3xArtifact.planned_candidate_scope_count || null,
            l2v3x_live_fetch_performed: l2v3xArtifact.live_fetch_performed ?? null,
        },
        safety_contract: {
            acquisition_result_is_not_accepted_mapping: true,
            acquired_source_url_evidence_is_not_raw_write_authorization: true,
            identity_evidence_status_complete_is_not_accepted_mapping: true,
            source_url_fragment_external_id_match_is_not_accepted_mapping: true,
            raw_write_ready_for_execution_remains_false: true,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        source_inventory_metadata_records: safeRecords,
    };
    const nextStep = deriveNextStep(artifact);
    return {
        ...artifact,
        recommended_next_step: nextStep.recommended_next_step,
        next_required_step: nextStep.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3y_execution_status: artifact.artifact_status,
        controlled_source_inventory_acquisition_execution_status: artifact.artifact_status,
        phase_5_21_l2v3y_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3y_report_path: REPORT_PATH,
        acquisition_attempted: true,
        live_fetch_performed: true,
        db_write_performed: false,
        phase_5_21_l2v3y_live_fetch_performed: true,
        phase_5_21_l2v3y_db_write_performed: false,
        endpoint_used: artifact.endpoint_used,
        phase_5_21_l2v3y_endpoint_used: artifact.endpoint_used,
        candidate_scope_count: artifact.candidate_scope_count,
        phase_5_21_l2v3y_candidate_scope_count: artifact.candidate_scope_count,
        candidate_targets_matched_count: artifact.candidate_targets_matched_count,
        phase_5_21_l2v3y_candidate_targets_matched_count: artifact.candidate_targets_matched_count,
        candidate_targets_with_source_page_url: artifact.candidate_targets_with_source_page_url,
        phase_5_21_l2v3y_candidate_targets_with_source_page_url: artifact.candidate_targets_with_source_page_url,
        candidate_targets_with_source_page_url_base: artifact.candidate_targets_with_source_page_url_base,
        phase_5_21_l2v3y_candidate_targets_with_source_page_url_base:
            artifact.candidate_targets_with_source_page_url_base,
        candidate_targets_with_source_url_fragment_external_id:
            artifact.candidate_targets_with_source_url_fragment_external_id,
        phase_5_21_l2v3y_candidate_targets_with_source_url_fragment_external_id:
            artifact.candidate_targets_with_source_url_fragment_external_id,
        candidate_targets_with_source_inventory_record_key: artifact.candidate_targets_with_source_inventory_record_key,
        phase_5_21_l2v3y_candidate_targets_with_source_inventory_record_key:
            artifact.candidate_targets_with_source_inventory_record_key,
        identity_evidence_complete_count: artifact.identity_evidence_complete_count,
        phase_5_21_l2v3y_identity_evidence_complete_count: artifact.identity_evidence_complete_count,
        identity_evidence_partial_count: artifact.identity_evidence_partial_count,
        phase_5_21_l2v3y_identity_evidence_partial_count: artifact.identity_evidence_partial_count,
        identity_evidence_missing_count: artifact.identity_evidence_missing_count,
        phase_5_21_l2v3y_identity_evidence_missing_count: artifact.identity_evidence_missing_count,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3y_accepted_mapping_count: 0,
        phase_5_21_l2v3y_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3y_baseline_acceptance_performed: false,
        phase_5_21_l2v3y_raw_write_retry_performed: false,
        phase_5_21_l2v3y_raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3Y

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- acquisition_attempted=true
- live_fetch_performed=true
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- browser_proxy_captcha_bypass_performed=false

## Endpoint And Scope

- endpoint_used=${artifact.endpoint_used}
- planned_acquisition_scope=${artifact.planned_acquisition_scope}
- planned_target_league_id=${artifact.planned_target_league_id}
- planned_target_season=${artifact.planned_target_season}
- candidate_scope_count=${artifact.candidate_scope_count}
- endpoint_http_status=${artifact.endpoint_http_status}
- endpoint_parsed=${artifact.endpoint_parsed}
- endpoint_parse_status=${artifact.endpoint_parse_status}
- endpoint_stop_reason=${artifact.endpoint_stop_reason || 'none'}

## Classification Output

- source_records_seen_count=${artifact.source_records_seen_count}
- candidate_targets_matched_count=${artifact.candidate_targets_matched_count}
- candidate_targets_with_source_page_url=${artifact.candidate_targets_with_source_page_url}
- candidate_targets_with_source_page_url_base=${artifact.candidate_targets_with_source_page_url_base}
- candidate_targets_with_source_url_fragment_external_id=${artifact.candidate_targets_with_source_url_fragment_external_id}
- candidate_targets_with_source_inventory_record_key=${artifact.candidate_targets_with_source_inventory_record_key}
- identity_evidence_complete_count=${artifact.identity_evidence_complete_count}
- identity_evidence_partial_count=${artifact.identity_evidence_partial_count}
- identity_evidence_missing_count=${artifact.identity_evidence_missing_count}
- acquisition_blocked_count=${artifact.acquisition_blocked_count}
- acquisition_failed_count=${artifact.acquisition_failed_count}
- acquisition_not_found_count=${artifact.acquisition_not_found_count}
- safe_metadata_record_count=${artifact.safe_metadata_record_count}
- accepted_mapping_count=0
- raw_write_ready_for_execution=false

## Metadata-Only Output

${artifact.safe_metadata_fields.map(field => `- ${field}`).join('\n')}

## Payload Safety

- full_api_payload_saved=false
- full_api_payload_printed=false
- full_pageProps_saved=false
- full_pageProps_printed=false
- full_raw_data_saved=false
- full_raw_data_printed=false
- full_html_or_source_body_saved=false
- full_html_or_source_body_printed=false
- cookies_tokens_headers_recorded=false
- metadata_only_output=true

## Stopping Rules

${artifact.stopping_rules.map(item => `- ${item}`).join('\n')}

## Safety Contract

- acquisition result is not accepted mapping.
- acquired source URL evidence is not raw write authorization.
- identity_evidence_status=complete is not accepted mapping.
- source_url_fragment_external_id match is not accepted mapping.
- raw_write_ready_for_execution remains false.
- separate identity mapping acceptance is required.
- separate baseline acceptance is required.
- separate final DB-write authorization is required.

## Next Step

${artifact.recommended_next_step}
`;
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3xArtifact: dependencies.l2v3xArtifact || readJsonFile(L2V3X_ARTIFACT_PATH),
    };
}

async function runControlledSourceInventoryAcquisitionExecution(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(loaded.manifest, loaded.l2v3xArtifact);
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const generatedAt = dependencies.generatedAt || GENERATED_AT;
    const fetchResult = dependencies.fetchResult || (await fetchSourceInventoryJson(dependencies));
    let sourceRecords = [];
    let normalizedFetchResult = fetchResult;
    if (fetchResult.ok) {
        try {
            sourceRecords = parseSourceInventoryRecords(fetchResult.json, dependencies, generatedAt);
            if (sourceRecords.length === 0) {
                normalizedFetchResult = {
                    ...fetchResult,
                    ok: false,
                    endpoint_parsed: true,
                    stop_reason: 'unexpected_schema_drift',
                    safe_error_summary: 'parsed_source_inventory_contained_no_match_records',
                };
            }
        } catch (error) {
            normalizedFetchResult = {
                ...fetchResult,
                ok: false,
                endpoint_parsed: true,
                stop_reason: 'unexpected_schema_drift',
                safe_error_summary: `source_inventory_parse_failed:${normalizeText(error.message).slice(0, 80)}`,
            };
            sourceRecords = [];
        }
    }

    const artifact = buildArtifact({
        ...loaded,
        fetchResult: normalizedFetchResult,
        sourceRecords,
        generatedAt,
    });
    const updatedManifest = updateManifestMetadata(loaded.manifest, artifact);
    const report = buildReport(artifact);

    if (dependencies.writeFiles !== false) {
        writeJsonFile(dependencies.artifactOutputPath || ARTIFACT_OUTPUT_PATH, artifact);
        writeTextFile(dependencies.reportOutputPath || REPORT_PATH, report);
        writeJsonFile(dependencies.manifestOutputPath || MANIFEST_PATH, updatedManifest);
    }

    return {
        ok: true,
        status: 0,
        artifact,
        updated_manifest: updatedManifest,
        report,
    };
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/pageprops_v2_controlled_source_inventory_acquisition_execute.js \\',
        '    --live-fetch=yes --source-inventory-authorization=yes --write-files=yes',
        '',
        'Safety:',
        '  L2V3Y performs one controlled metadata-only source inventory fetch.',
        '  It does not write DB/raw/matches, accept mappings, accept baselines, retry raw writes, or save full payloads.',
    ].join('\n');
}

function summaryForStdout(result) {
    return {
        ok: result.ok,
        phase: PHASE,
        artifact: ARTIFACT_OUTPUT_PATH,
        report: REPORT_PATH,
        acquisition_attempted: result.artifact.acquisition_attempted,
        live_fetch_performed: result.artifact.live_fetch_performed,
        db_write_performed: result.artifact.db_write_performed,
        endpoint_used: result.artifact.endpoint_used,
        candidate_scope_count: result.artifact.candidate_scope_count,
        endpoint_http_status: result.artifact.endpoint_http_status,
        endpoint_parsed: result.artifact.endpoint_parsed,
        source_records_seen_count: result.artifact.source_records_seen_count,
        candidate_targets_matched_count: result.artifact.candidate_targets_matched_count,
        candidate_targets_with_source_page_url: result.artifact.candidate_targets_with_source_page_url,
        candidate_targets_with_source_page_url_base: result.artifact.candidate_targets_with_source_page_url_base,
        candidate_targets_with_source_url_fragment_external_id:
            result.artifact.candidate_targets_with_source_url_fragment_external_id,
        candidate_targets_with_source_inventory_record_key:
            result.artifact.candidate_targets_with_source_inventory_record_key,
        identity_evidence_complete_count: result.artifact.identity_evidence_complete_count,
        identity_evidence_partial_count: result.artifact.identity_evidence_partial_count,
        identity_evidence_missing_count: result.artifact.identity_evidence_missing_count,
        acquisition_blocked_count: result.artifact.acquisition_blocked_count,
        acquisition_failed_count: result.artifact.acquisition_failed_count,
        acquisition_not_found_count: result.artifact.acquisition_not_found_count,
        safe_metadata_record_count: result.artifact.safe_metadata_record_count,
        accepted_mapping_count: result.artifact.accepted_mapping_count,
        raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
        recommended_next_step: result.artifact.recommended_next_step,
    };
}

async function runCli(argv = process.argv.slice(2), streams = {}) {
    const stdout = streams.stdout || (text => process.stdout.write(text));
    const options = parseArgs(argv);
    if (options.help) {
        stdout(`${usage()}\n`);
        return 0;
    }
    const optionGate = validateCliOptions(options);
    if (!optionGate.ok) {
        stdout(`${JSON.stringify({ ok: false, phase: PHASE, errors: optionGate.errors }, null, 2)}\n`);
        return 2;
    }
    const result = await runControlledSourceInventoryAcquisitionExecution({ writeFiles: options.writeFiles });
    if (!result.ok) {
        stdout(`${JSON.stringify({ ok: false, phase: PHASE, errors: result.errors }, null, 2)}\n`);
        return result.status;
    }
    stdout(`${JSON.stringify(summaryForStdout(result), null, 2)}\n`);
    return result.status;
}

module.exports = {
    PHASE,
    PHASE_NAME,
    MANIFEST_PATH,
    L2V3X_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    PLANNED_ENDPOINT,
    PLANNED_SCOPE,
    SAFE_METADATA_FIELDS,
    PAYLOAD_SAFETY_RULES,
    STOPPING_RULES,
    parseArgs,
    validateCliOptions,
    validateInputs,
    detectBlockedMarkers,
    fetchSourceInventoryJson,
    parseSourceInventoryRecords,
    buildSafeMetadataRecords,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runControlledSourceInventoryAcquisitionExecution,
    runCli,
};

if (require.main === module) {
    runCli().then(
        exitCode => {
            process.exitCode = exitCode;
        },
        error => {
            process.stdout.write(`${JSON.stringify({ ok: false, phase: PHASE, error: error.message }, null, 2)}\n`);
            process.exitCode = 1;
        }
    );
}
