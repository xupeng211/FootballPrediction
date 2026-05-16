#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const {
    CANDIDATE_VERSION,
    HASH_STRATEGY,
    buildFotMobMatchUrl,
    fetchHtml,
    extractNextDataJsonFromHtml,
    getPageProps,
    computeStablePagePropsHash,
    listJsonPaths,
    comparePathCoverage,
    summarizeJsonShape,
} = require('./pageprops_v2_no_write_preview');
const { buildVersionAwareLookupSpec } = require('../../src/infrastructure/services/RawMatchDataVersionSelector');

const PHASE = 'PHASE5_21L2L_REMAINING_SEEDED_PAGEPROPS_V2_ACQUISITION_PREFLIGHT';
const SOURCE = 'fotmob';
const ROUTE = 'html_hydration';
const EXPECTED_TARGETS = Object.freeze([
    { matchId: '53_20252026_4830746', externalId: '4830746' },
    { matchId: '53_20252026_4830748', externalId: '4830748' },
    { matchId: '53_20252026_4830750', externalId: '4830750' },
    { matchId: '53_20252026_4830751', externalId: '4830751' },
    { matchId: '53_20252026_4830752', externalId: '4830752' },
    { matchId: '53_20252026_4830753', externalId: '4830753' },
    { matchId: '53_20252026_4830754', externalId: '4830754' },
]);
const EXPECTED_EXTERNAL_IDS = Object.freeze(EXPECTED_TARGETS.map(target => target.externalId));
const EXPECTED_MATCH_IDS = Object.freeze(EXPECTED_TARGETS.map(target => target.matchId));
const EXCLUDED_ALREADY_WRITTEN_EXTERNAL_ID = '4830747';
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowRawMatchDataWrite',
    'allowMatchesWrite',
    'allowParserFeatures',
    'allowTraining',
    'allowPrediction',
    'printBody',
    'saveBody',
    'printFullJson',
    'saveFullJson',
]);
const BLOCKED_TRUE_FLAGS = Object.freeze([
    'allowBrowserRuntime',
    'allowProxyRuntime',
    'bulkWrite',
    'bulk',
    'execute',
    'commit',
    'include4830747',
]);
const PROTECTED_TABLES = Object.freeze([
    'matches',
    'raw_match_data',
    'bookmaker_odds_history',
    'l3_features',
    'match_features_training',
    'predictions',
]);
const EXPECTED_PROTECTED_TABLE_BASELINE = Object.freeze({
    matches: 10,
    raw_match_data: 11,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});

function normalizeText(value) {
    return String(value ?? '').trim();
}

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = String(value).trim().toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) return false;
    return fallback;
}

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = String(value).trim();
    if (!/^\d+$/.test(normalized)) return Number.NaN;
    return Number.parseInt(normalized, 10);
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        source: null,
        route: null,
        targetExternalIds: null,
        candidateVersion: null,
        hashStrategy: null,
        networkAuthorization: null,
        pagepropsV2RemainingPreflightAuthorization: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowMatchesWrite: null,
        allowParserFeatures: null,
        allowTraining: null,
        allowPrediction: null,
        concurrency: null,
        retry: null,
        printBody: null,
        saveBody: null,
        printFullJson: null,
        saveFullJson: null,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        bulkWrite: false,
        bulk: false,
        execute: false,
        commit: false,
        include4830747: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        route: 'route',
        'target-external-ids': 'targetExternalIds',
        target_external_ids: 'targetExternalIds',
        'candidate-version': 'candidateVersion',
        candidate_version: 'candidateVersion',
        'hash-strategy': 'hashStrategy',
        hash_strategy: 'hashStrategy',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'pageprops-v2-remaining-preflight-authorization': 'pagepropsV2RemainingPreflightAuthorization',
        pageprops_v2_remaining_preflight_authorization: 'pagepropsV2RemainingPreflightAuthorization',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-parser-features': 'allowParserFeatures',
        allow_parser_features: 'allowParserFeatures',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        concurrency: 'concurrency',
        retry: 'retry',
        'print-body': 'printBody',
        print_body: 'printBody',
        'save-body': 'saveBody',
        save_body: 'saveBody',
        'print-full-json': 'printFullJson',
        print_full_json: 'printFullJson',
        'save-full-json': 'saveFullJson',
        save_full_json: 'saveFullJson',
        'allow-browser-runtime': 'allowBrowserRuntime',
        allow_browser_runtime: 'allowBrowserRuntime',
        'allow-proxy-runtime': 'allowProxyRuntime',
        allow_proxy_runtime: 'allowProxyRuntime',
        'bulk-write': 'bulkWrite',
        bulk_write: 'bulkWrite',
        bulk: 'bulk',
        execute: 'execute',
        commit: 'commit',
        'include-4830747': 'include4830747',
        include_4830747: 'include4830747',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'networkAuthorization',
        'pagepropsV2RemainingPreflightAuthorization',
        'allowDbWrite',
        'allowRawMatchDataWrite',
        'allowMatchesWrite',
        'allowParserFeatures',
        'allowTraining',
        'allowPrediction',
        'printBody',
        'saveBody',
        'printFullJson',
        'saveFullJson',
        'allowBrowserRuntime',
        'allowProxyRuntime',
        'bulkWrite',
        'bulk',
        'execute',
        'commit',
        'include4830747',
        'help',
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

function pushRequiredYes(errors, value, flagName) {
    if (value === true) return;
    if (value === false) {
        errors.push(`${flagName}=yes is required in Phase 5.21L2L`);
        return;
    }
    errors.push(`missing ${flagName}=yes`);
}

function pushRequiredNo(errors, value, flagName) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.21L2L`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function requireExact(errors, actual, expected, flagName) {
    if (!normalizeText(actual)) {
        errors.push(`missing ${flagName}=${expected}`);
        return;
    }
    if (normalizeText(actual) !== expected) {
        errors.push(`${flagName} must be ${expected}`);
    }
}

function parseTargetExternalIds(value) {
    return normalizeText(value)
        .split(',')
        .map(item => item.trim())
        .filter(Boolean);
}

function hasDuplicate(values = []) {
    return new Set(values).size !== values.length;
}

function sameOrderedList(actual = [], expected = []) {
    return actual.length === expected.length && actual.every((value, index) => value === expected[index]);
}

function normalizePreflightInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        route: normalizeText(input.route),
        targetExternalIds: parseTargetExternalIds(input.targetExternalIds),
        candidateVersion: normalizeText(input.candidateVersion),
        hashStrategy: normalizeText(input.hashStrategy),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        pagepropsV2RemainingPreflightAuthorization: normalizeBooleanFlag(
            input.pagepropsV2RemainingPreflightAuthorization,
            undefined
        ),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowParserFeatures: normalizeBooleanFlag(input.allowParserFeatures, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        concurrency: parseInteger(input.concurrency, null),
        retry: parseInteger(input.retry, null),
        printBody: normalizeBooleanFlag(input.printBody, undefined),
        saveBody: normalizeBooleanFlag(input.saveBody, undefined),
        printFullJson: normalizeBooleanFlag(input.printFullJson, undefined),
        saveFullJson: normalizeBooleanFlag(input.saveFullJson, undefined),
        allowBrowserRuntime: normalizeBooleanFlag(input.allowBrowserRuntime, false),
        allowProxyRuntime: normalizeBooleanFlag(input.allowProxyRuntime, false),
        bulkWrite: normalizeBooleanFlag(input.bulkWrite, false),
        bulk: normalizeBooleanFlag(input.bulk, false),
        execute: normalizeBooleanFlag(input.execute, false),
        commit: normalizeBooleanFlag(input.commit, false),
        include4830747: normalizeBooleanFlag(input.include4830747, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validateTargetExternalIds(errors, targetExternalIds = []) {
    if (targetExternalIds.length === 0) {
        errors.push(`missing target-external-ids=${EXPECTED_EXTERNAL_IDS.join(',')}`);
        return;
    }
    if (targetExternalIds.includes(EXCLUDED_ALREADY_WRITTEN_EXTERNAL_ID)) {
        errors.push('target-external-ids must not include 4830747');
    }
    if (hasDuplicate(targetExternalIds)) {
        errors.push('target-external-ids must not contain duplicates');
    }
    if (!sameOrderedList(targetExternalIds, EXPECTED_EXTERNAL_IDS)) {
        errors.push(`target-external-ids must be exactly ${EXPECTED_EXTERNAL_IDS.join(',')}`);
    }
}

function validatePreflightInput(input = {}) {
    const value = normalizePreflightInput(input);
    const errors = [];
    if (value.unknown.length > 0) errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    requireExact(errors, value.source, SOURCE, 'source');
    requireExact(errors, value.route, ROUTE, 'route');
    validateTargetExternalIds(errors, value.targetExternalIds);
    requireExact(errors, value.candidateVersion, CANDIDATE_VERSION, 'candidate-version');
    requireExact(errors, value.hashStrategy, HASH_STRATEGY, 'hash-strategy');
    pushRequiredYes(errors, value.networkAuthorization, 'network-authorization');
    pushRequiredYes(
        errors,
        value.pagepropsV2RemainingPreflightAuthorization,
        'pageprops-v2-remaining-preflight-authorization'
    );
    for (const key of REQUIRED_NO_FLAGS) {
        pushRequiredNo(
            errors,
            value[key],
            key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)
        );
    }
    if (value.concurrency !== 1) errors.push('concurrency=1 is required');
    if (value.retry !== 0) errors.push('retry=0 is required');
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (value[key] === true) {
            errors.push(`${key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)}=yes is blocked`);
        }
    }
    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function jsonClone(value) {
    if (value === undefined) return undefined;
    return JSON.parse(JSON.stringify(value));
}

function objectOrEmpty(value) {
    return isPlainObject(value) ? value : {};
}

function jsonByteLength(value) {
    return Buffer.byteLength(JSON.stringify(value), 'utf8');
}

function normalizeRowId(row = {}) {
    if (row.id === undefined || row.id === null) return null;
    return String(row.id);
}

function normalizeMatchMetadata(row = {}) {
    return {
        match_id: normalizeText(row.match_id),
        external_id: normalizeText(row.external_id),
        home_team: normalizeText(row.home_team),
        away_team: normalizeText(row.away_team),
        match_date: normalizeText(row.match_date),
        status: normalizeText(row.status),
    };
}

function normalizeCountRow(row = {}) {
    return {
        table_name: normalizeText(row.table_name),
        rows: Number(row.rows || 0),
    };
}

function buildProtectedTableBaseline(rows = []) {
    const normalizedRows = Array.isArray(rows) ? rows.map(normalizeCountRow) : [];
    const baseline = {};
    for (const table of PROTECTED_TABLES) {
        const row = normalizedRows.find(item => item.table_name === table);
        baseline[table] = row ? row.rows : 0;
    }
    return baseline;
}

function validateProtectedTableBaseline(baseline = {}) {
    const errors = [];
    for (const [table, expectedRows] of Object.entries(EXPECTED_PROTECTED_TABLE_BASELINE)) {
        if (Number(baseline[table]) !== expectedRows) {
            errors.push(`${table} expected ${expectedRows}, got ${Number(baseline[table] || 0)}`);
        }
    }
    return errors;
}

function buildSchemaSummary(constraints = []) {
    const rows = Array.isArray(constraints) ? constraints : [];
    const uniqueMatchIdDataVersion = rows.some(row => {
        const conname = normalizeText(row.conname);
        const definition = normalizeText(row.definition);
        return (
            conname === 'raw_match_data_match_id_data_version_key' ||
            /UNIQUE\s*\(\s*match_id\s*,\s*data_version\s*\)/i.test(definition)
        );
    });
    const uniqueMatchIdOnly = rows.some(row => {
        const conname = normalizeText(row.conname);
        const definition = normalizeText(row.definition);
        return (
            conname === 'raw_match_data_match_id_key' ||
            (/UNIQUE\s*\(\s*match_id\s*\)/i.test(definition) &&
                !/UNIQUE\s*\(\s*match_id\s*,\s*data_version\s*\)/i.test(definition))
        );
    });
    return {
        unique_match_id_data_version: uniqueMatchIdDataVersion,
        unique_match_id_only: uniqueMatchIdOnly,
        raw_match_data_match_id_data_version_key_present: rows.some(
            row => normalizeText(row.conname) === 'raw_match_data_match_id_data_version_key'
        ),
        raw_match_data_match_id_key_absent: !rows.some(
            row => normalizeText(row.conname) === 'raw_match_data_match_id_key'
        ),
    };
}

function validateSchemaSummary(summary = {}) {
    const errors = [];
    if (summary.unique_match_id_data_version !== true) {
        errors.push('raw_match_data UNIQUE(match_id,data_version) missing');
    }
    if (summary.unique_match_id_only === true) {
        errors.push('legacy raw_match_data UNIQUE(match_id) must be absent');
    }
    return errors;
}

function summarizeExistingVersions(rows = []) {
    return [
        ...new Set((Array.isArray(rows) ? rows : []).map(row => normalizeText(row.data_version)).filter(Boolean)),
    ].sort();
}

function assertNoDuplicateVersions(rows = []) {
    const seen = new Set();
    for (const row of Array.isArray(rows) ? rows : []) {
        const key = `${normalizeText(row.match_id)}\u0000${normalizeText(row.data_version)}`;
        if (seen.has(key)) {
            throw new Error(
                `DUPLICATE_MATCH_ID_DATA_VERSION:${normalizeText(row.match_id)},${normalizeText(row.data_version)}`
            );
        }
        seen.add(key);
    }
}

function groupRowsByMatchId(rows = []) {
    const grouped = new Map();
    for (const row of Array.isArray(rows) ? rows : []) {
        const matchId = normalizeText(row.match_id);
        if (!grouped.has(matchId)) grouped.set(matchId, []);
        grouped.get(matchId).push(row);
    }
    return grouped;
}

function buildExistingVersionDecision(rows = []) {
    const safeRows = Array.isArray(rows) ? rows : [];
    assertNoDuplicateVersions(safeRows);
    const existingVersions = summarizeExistingVersions(safeRows);
    const v1Rows = safeRows.filter(row => normalizeText(row.data_version) === 'fotmob_html_hyd_v1');
    const v2Rows = safeRows.filter(row => normalizeText(row.data_version) === CANDIDATE_VERSION);
    const v1Exists = v1Rows.length === 1;
    const v2Exists = v2Rows.length === 1;
    const summary = {
        existing_versions: existingVersions,
        fotmob_html_hyd_v1_exists: v1Exists,
        fotmob_pageprops_v2_exists: v2Exists,
        existing_v1_row_id: v1Exists ? normalizeRowId(v1Rows[0]) : null,
        existing_v2_row_id: v2Exists ? normalizeRowId(v2Rows[0]) : null,
        target_version_exists: v2Exists,
    };
    if (!v1Exists) {
        return {
            ...summary,
            decision: 'blocked',
            would_insert_count: 0,
            would_update_count: 0,
            would_skip_count: 0,
            blocked_this_phase: true,
            reason: 'required fotmob_html_hyd_v1 row missing',
        };
    }
    if (v2Exists) {
        return {
            ...summary,
            existing_v2_data_hash: normalizeText(v2Rows[0].data_hash).toLowerCase(),
            decision: 'would_skip',
            would_insert_count: 0,
            would_update_count: 0,
            would_skip_count: 1,
            blocked_this_phase: true,
            reason: 'fotmob_pageprops_v2 row already exists for remaining target',
        };
    }
    return {
        ...summary,
        decision: 'would_insert',
        would_insert_count: 1,
        would_update_count: 0,
        would_skip_count: 0,
        blocked_this_phase: false,
        reason: 'fotmob_html_hyd_v1 exists and fotmob_pageprops_v2 is absent',
    };
}

function validateTargetMetadataRows(rows = []) {
    const metadataRows = (Array.isArray(rows) ? rows : []).map(normalizeMatchMetadata);
    if (metadataRows.length !== EXPECTED_TARGETS.length) {
        throw new Error(`TARGET_METADATA_ROW_COUNT:${metadataRows.length}`);
    }
    const byExternalId = new Map(metadataRows.map(row => [row.external_id, row]));
    for (const expected of EXPECTED_TARGETS) {
        const row = byExternalId.get(expected.externalId);
        if (!row) throw new Error(`TARGET_METADATA_MISSING:${expected.externalId}`);
        if (row.match_id !== expected.matchId) {
            throw new Error(`TARGET_MATCH_ID_MISMATCH:${expected.externalId}:${row.match_id}`);
        }
    }
    return EXPECTED_TARGETS.map(expected => byExternalId.get(expected.externalId));
}

function buildPagePropsV2Candidate({
    input = {},
    target = {},
    pageProps = {},
    fetchResult = {},
    generatedAt = null,
} = {}) {
    const safePageProps = jsonClone(pageProps) || {};
    const externalId = normalizeText(target.external_id || target.externalId);
    const matchId = normalizeText(target.match_id || target.matchId);
    const requestUrl = fetchResult.request_url || buildFotMobMatchUrl(externalId);
    const stableHash = computeStablePagePropsHash(safePageProps);
    return {
        _meta: {
            source: input.source || SOURCE,
            route: input.route || ROUTE,
            data_version: CANDIDATE_VERSION,
            hash_strategy: HASH_STRATEGY,
            match_id: matchId,
            external_id: externalId,
            request_url: requestUrl,
            final_url: fetchResult.final_url || requestUrl,
            http_status: Number(fetchResult.http_status || 0),
            content_type: fetchResult.content_type || null,
            body_byte_length: Number(fetchResult.body_byte_length || 0),
            fetch_body_sha256: fetchResult.body_sha256 || null,
            generated_at: generatedAt || new Date().toISOString(),
            full_html_body_stored: false,
            full_next_data_stored: false,
            full_json_printed: false,
            data_hash: stableHash,
        },
        matchId: Number(externalId),
        pageProps: safePageProps,
    };
}

function buildTargetContexts({ metadataRows = [], existingRows = [] } = {}) {
    const metadata = validateTargetMetadataRows(metadataRows);
    const groupedExistingRows = groupRowsByMatchId(existingRows);
    return metadata.map(row => {
        const rows = groupedExistingRows.get(row.match_id) || [];
        const versionDecision = buildExistingVersionDecision(rows);
        return {
            ...row,
            existingRows: rows,
            versionDecision,
        };
    });
}

function buildControlledTargetFailure(target = {}, requestUrl, reason, context = {}) {
    return {
        ok: false,
        controlled_failure: true,
        match_id: normalizeText(target.match_id),
        external_id: normalizeText(target.external_id),
        home_team: normalizeText(target.home_team),
        away_team: normalizeText(target.away_team),
        request_url: requestUrl || buildFotMobMatchUrl(target.external_id),
        final_url: context.final_url || null,
        http_status: context.http_status || null,
        content_type: context.content_type || null,
        body_byte_length: Number(context.body_byte_length || 0),
        body_sha256: context.body_sha256 || null,
        next_data_parse_ok: false,
        page_props_found: false,
        stable_pageprops_hash: null,
        candidate_json_byte_length: 0,
        pageProps_top_level_keys: [],
        pageProps_path_count: 0,
        pageProps_content_path_count: 0,
        existing_versions: target.versionDecision?.existing_versions || [],
        target_version_exists: target.versionDecision?.target_version_exists === true,
        decision: 'failed',
        failure_reason: reason,
    };
}

function buildTargetSummary({ input = {}, target = {}, fetchResult = {}, generatedAt = null } = {}) {
    const requestUrl = buildFotMobMatchUrl(target.external_id);
    if (!fetchResult.ok) {
        return buildControlledTargetFailure(
            target,
            requestUrl,
            fetchResult.error || 'LIVE_REQUEST_FAILED',
            fetchResult
        );
    }
    const extraction = extractNextDataJsonFromHtml(fetchResult.body);
    if (!extraction.ok) {
        return buildControlledTargetFailure(target, requestUrl, extraction.error, fetchResult);
    }
    const pageProps = getPageProps(extraction.data);
    if (!pageProps) {
        return buildControlledTargetFailure(target, requestUrl, 'PAGE_PROPS_NOT_FOUND', fetchResult);
    }
    const v1Row = target.existingRows.find(row => normalizeText(row.data_version) === 'fotmob_html_hyd_v1');
    const v1RawData = v1Row?.raw_data;
    if (!isPlainObject(v1RawData)) {
        return buildControlledTargetFailure(target, requestUrl, 'STORED_V1_RAW_DATA_NOT_OBJECT', fetchResult);
    }

    const candidate = buildPagePropsV2Candidate({
        input,
        target,
        pageProps,
        fetchResult,
        generatedAt,
    });
    const stableHash = computeStablePagePropsHash(candidate);
    const v1RawDataPaths = listJsonPaths(v1RawData);
    const v2PagePropsPaths = listJsonPaths(pageProps);
    const v1ContentPaths = listJsonPaths(objectOrEmpty(v1RawData.content));
    const v2ContentPaths = listJsonPaths(objectOrEmpty(pageProps.content));
    const pageCoverage = comparePathCoverage(v2PagePropsPaths, v1RawDataPaths);
    const contentCoverage = comparePathCoverage(v2ContentPaths, v1ContentPaths);

    return {
        ok: true,
        match_id: target.match_id,
        external_id: target.external_id,
        home_team: target.home_team,
        away_team: target.away_team,
        request_url: fetchResult.request_url || requestUrl,
        final_url: fetchResult.final_url || requestUrl,
        http_status: fetchResult.http_status,
        content_type: fetchResult.content_type,
        body_byte_length: Number(fetchResult.body_byte_length || 0),
        body_sha256: fetchResult.body_sha256 || null,
        next_data_parse_ok: true,
        page_props_found: true,
        stable_pageprops_hash: stableHash,
        candidate_json_byte_length: jsonByteLength(candidate),
        pageProps_top_level_keys: Object.keys(pageProps).sort(),
        pageProps_path_count: v2PagePropsPaths.length,
        pageProps_content_path_count: v2ContentPaths.length,
        pageProps_shape_summary: summarizeJsonShape(pageProps),
        candidate_shape_summary: summarizeJsonShape(candidate),
        v1_json_byte_length: jsonByteLength(v1RawData),
        v1_path_count: v1RawDataPaths.length,
        v1_content_path_count: v1ContentPaths.length,
        v2_only_path_count: pageCoverage.v2_only_count,
        v1_only_path_count: pageCoverage.v1_only_count,
        content_diff_path_count: contentCoverage.v1_only_count + contentCoverage.v2_only_count,
        existing_versions: target.versionDecision.existing_versions,
        target_version_exists: target.versionDecision.target_version_exists,
        decision: target.versionDecision.decision,
    };
}

function buildFailurePayload({
    input = {},
    reason,
    protectedTableBaseline = null,
    schemaSummary = null,
    targetInventory = [],
    targets = [],
    failedTargetCount = 0,
} = {}) {
    const lookupSpec = buildVersionAwareLookupSpec();
    return {
        phase: PHASE,
        ok: false,
        controlled_failure: true,
        preflight_only: true,
        source: SOURCE,
        route: ROUTE,
        candidate_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        attempted_target_count: EXPECTED_TARGETS.length,
        processed_target_count: targets.length,
        valid_payload_count: targets.filter(target => target.ok).length,
        failed_target_count: failedTargetCount || targets.filter(target => target.ok !== true).length,
        would_insert_count: targets.reduce((total, target) => total + (target.decision === 'would_insert' ? 1 : 0), 0),
        would_update_count: 0,
        would_skip_count: targets.reduce((total, target) => total + (target.decision === 'would_skip' ? 1 : 0), 0),
        target_external_ids: input.targetExternalIds || EXPECTED_EXTERNAL_IDS,
        target_inventory: targetInventory,
        targets,
        protected_table_baseline: protectedTableBaseline,
        schema_summary: schemaSummary,
        failure_reason: reason,
        write_plan_for_next_phase: {
            insert_conflict_target: lookupSpec.conflict_target,
            insert_conflict_target_sql: lookupSpec.conflict_target_sql,
            requires_final_db_write_confirmation: true,
        },
        db_write_executed: false,
        raw_match_data_write_executed: false,
        matches_write_executed: false,
        schema_migration_executed: false,
        parser_features_executed: false,
        training_executed: false,
        prediction_executed: false,
        body_printed: false,
        body_saved: false,
        full_json_printed: false,
        full_json_saved: false,
        browser_used: false,
        proxy_used: false,
        retry_count: 0,
    };
}

function summarizeTargetInventory(targetContexts = []) {
    return targetContexts.map(target => ({
        match_id: target.match_id,
        external_id: target.external_id,
        home_team: target.home_team,
        away_team: target.away_team,
        match_date: target.match_date,
        status: target.status,
        existing_versions: target.versionDecision.existing_versions,
        target_version_exists: target.versionDecision.target_version_exists,
        decision: target.versionDecision.decision,
    }));
}

function validateInventoryPreconditions(targetContexts = []) {
    const errors = [];
    for (const target of targetContexts) {
        if (target.versionDecision.blocked_this_phase) {
            errors.push(`${target.external_id}:${target.versionDecision.reason}`);
        }
    }
    return errors;
}

async function resolveFetchResultForTarget(target, index, dependencies = {}) {
    const byExternalId = dependencies.fetchResultsByExternalId || {};
    if (byExternalId[target.external_id]) return byExternalId[target.external_id];
    if (Array.isArray(dependencies.fetchResults) && dependencies.fetchResults[index]) {
        return dependencies.fetchResults[index];
    }
    const requestUrl = buildFotMobMatchUrl(target.external_id);
    const fetchHtmlFn = dependencies.fetchHtmlFn || fetchHtml;
    return fetchHtmlFn(requestUrl, { fetchFn: dependencies.fetchFn });
}

async function buildRemainingSeededPagePropsV2AcquisitionPreflight({
    input = {},
    metadataRows = [],
    existingRows = [],
    protectedTableRows = [],
    schemaConstraintRows = [],
    generatedAt = null,
    dependencies = {},
} = {}) {
    const protectedTableBaseline = buildProtectedTableBaseline(protectedTableRows);
    const baselineErrors = validateProtectedTableBaseline(protectedTableBaseline);
    const schemaSummary = buildSchemaSummary(schemaConstraintRows);
    const schemaErrors = validateSchemaSummary(schemaSummary);
    if (baselineErrors.length > 0 || schemaErrors.length > 0) {
        return buildFailurePayload({
            input,
            reason: `BASELINE_INVALID:${[...baselineErrors, ...schemaErrors].join(';')}`,
            protectedTableBaseline,
            schemaSummary,
        });
    }

    let targetContexts;
    try {
        targetContexts = buildTargetContexts({ metadataRows, existingRows });
    } catch (error) {
        return buildFailurePayload({
            input,
            reason: error.message,
            protectedTableBaseline,
            schemaSummary,
        });
    }

    const targetInventory = summarizeTargetInventory(targetContexts);
    const inventoryErrors = validateInventoryPreconditions(targetContexts);
    if (inventoryErrors.length > 0) {
        return buildFailurePayload({
            input,
            reason: `TARGET_VERSION_PRECONDITION_FAILED:${inventoryErrors.join(';')}`,
            protectedTableBaseline,
            schemaSummary,
            targetInventory,
            targets: targetInventory,
            failedTargetCount: inventoryErrors.length,
        });
    }

    const targetSummaries = [];
    for (let index = 0; index < targetContexts.length; index += 1) {
        const target = targetContexts[index];
        const fetchResult = await resolveFetchResultForTarget(target, index, dependencies);
        const summary = buildTargetSummary({
            input,
            target,
            fetchResult,
            generatedAt,
        });
        targetSummaries.push(summary);
        if (!summary.ok) {
            return buildFailurePayload({
                input,
                reason: `${target.external_id}:${summary.failure_reason}`,
                protectedTableBaseline,
                schemaSummary,
                targetInventory,
                targets: targetSummaries,
                failedTargetCount: 1,
            });
        }
    }

    const lookupSpec = buildVersionAwareLookupSpec();
    return {
        phase: PHASE,
        ok: true,
        preflight_only: true,
        source: SOURCE,
        route: ROUTE,
        candidate_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        attempted_target_count: EXPECTED_TARGETS.length,
        processed_target_count: targetSummaries.length,
        valid_payload_count: targetSummaries.length,
        failed_target_count: 0,
        would_insert_count: targetSummaries.filter(target => target.decision === 'would_insert').length,
        would_update_count: 0,
        would_skip_count: targetSummaries.filter(target => target.decision === 'would_skip').length,
        target_external_ids: input.targetExternalIds,
        target_inventory: targetInventory,
        targets: targetSummaries,
        baseline_hashes_for_next_phase: Object.fromEntries(
            targetSummaries.map(target => [target.external_id, target.stable_pageprops_hash])
        ),
        protected_table_baseline: protectedTableBaseline,
        schema_summary: schemaSummary,
        write_plan_for_next_phase: {
            insert_conflict_target: lookupSpec.conflict_target,
            insert_conflict_target_sql: lookupSpec.conflict_target_sql,
            expected_raw_match_data_after_future_write: '11 -> 18',
            requires_final_db_write_confirmation: true,
            any_hash_drift_blocks_whole_write: true,
        },
        db_write_executed: false,
        raw_match_data_write_executed: false,
        matches_write_executed: false,
        schema_migration_executed: false,
        parser_features_executed: false,
        training_executed: false,
        prediction_executed: false,
        body_printed: false,
        body_saved: false,
        full_json_printed: false,
        full_json_saved: false,
        browser_used: false,
        proxy_used: false,
        retry_count: 0,
    };
}

async function queryReadOnly(client, sql, params = []) {
    const normalized = normalizeText(sql).replace(/\s+/g, ' ').toLowerCase();
    if (!normalized.startsWith('select ')) throw new Error('NON_SELECT_SQL_BLOCKED');
    if (/\b(insert|update|delete|truncate|alter|drop|create|grant|revoke|copy|for update|lock)\b/i.test(normalized)) {
        throw new Error('SQL_WRITE_OR_LOCK_BLOCKED');
    }
    return client.query(sql, params);
}

async function loadTargetMatchMetadata(client, input) {
    const result = await queryReadOnly(
        client,
        `
        SELECT match_id, external_id, home_team, away_team, match_date, status
        FROM matches
        WHERE external_id = ANY($1::text[])
        ORDER BY external_id
        `,
        [input.targetExternalIds]
    );
    return result.rows || [];
}

async function loadExistingRawVersions(client) {
    const result = await queryReadOnly(
        client,
        `
        SELECT id, match_id, external_id, data_version, data_hash, collected_at, raw_data
        FROM raw_match_data
        WHERE match_id = ANY($1::text[])
        ORDER BY match_id, data_version, id
        `,
        [EXPECTED_MATCH_IDS]
    );
    return result.rows || [];
}

async function loadProtectedTableBaselineRows(client) {
    const result = await queryReadOnly(
        client,
        `
        SELECT 'matches' AS table_name, COUNT(*)::int AS rows FROM matches
        UNION ALL
        SELECT 'bookmaker_odds_history', COUNT(*)::int FROM bookmaker_odds_history
        UNION ALL
        SELECT 'raw_match_data', COUNT(*)::int FROM raw_match_data
        UNION ALL
        SELECT 'l3_features', COUNT(*)::int FROM l3_features
        UNION ALL
        SELECT 'match_features_training', COUNT(*)::int FROM match_features_training
        UNION ALL
        SELECT 'predictions', COUNT(*)::int FROM predictions
        `,
        []
    );
    return result.rows || [];
}

async function loadSchemaConstraints(client) {
    const result = await queryReadOnly(
        client,
        `
        SELECT
          conname,
          contype,
          pg_get_constraintdef(c.oid) AS definition
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = 'raw_match_data'
        ORDER BY conname
        `,
        []
    );
    return result.rows || [];
}

function createDefaultPool() {
    const { Pool } = require('pg');
    const { buildDbConnectionConfig } = require('./helpers/dbBlueprint');
    return new Pool(buildDbConnectionConfig());
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsed = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validatePreflightInput(parsed);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));
    if (!validation.ok) {
        const payload = buildFailurePayload({
            input: normalizePreflightInput(parsed),
            reason: `INPUT_INVALID:${validation.errors.join(';')}`,
        });
        payload.blocked = true;
        payload.errors = validation.errors;
        output(payload);
        return { status: 1, payload };
    }

    const input = validation.value;
    const pool =
        dependencies.client ||
        dependencies.metadataRows ||
        dependencies.existingRows ||
        dependencies.protectedTableRows ||
        dependencies.schemaConstraintRows
            ? null
            : createDefaultPool();
    const client = dependencies.client || pool;
    try {
        const metadataRows = dependencies.metadataRows || (await loadTargetMatchMetadata(client, input));
        const existingRows = dependencies.existingRows || (await loadExistingRawVersions(client));
        const protectedTableRows = dependencies.protectedTableRows || (await loadProtectedTableBaselineRows(client));
        const schemaConstraintRows = dependencies.schemaConstraintRows || (await loadSchemaConstraints(client));
        const payload = await buildRemainingSeededPagePropsV2AcquisitionPreflight({
            input,
            metadataRows,
            existingRows,
            protectedTableRows,
            schemaConstraintRows,
            generatedAt: dependencies.generatedAt,
            dependencies,
        });
        output(payload);
        return { status: payload.ok ? 0 : 1, payload };
    } catch (error) {
        const payload = buildFailurePayload({
            input,
            reason: error.message,
        });
        output(payload);
        return { status: 1, payload };
    } finally {
        if (pool && typeof pool.end === 'function') await pool.end();
    }
}

module.exports = {
    PHASE,
    SOURCE,
    ROUTE,
    EXPECTED_TARGETS,
    EXPECTED_EXTERNAL_IDS,
    EXPECTED_PROTECTED_TABLE_BASELINE,
    parseArgs,
    normalizeBooleanFlag,
    validatePreflightInput,
    extractNextDataJsonFromHtml,
    getPageProps,
    computeStablePagePropsHash,
    buildProtectedTableBaseline,
    buildSchemaSummary,
    buildExistingVersionDecision,
    validateTargetMetadataRows,
    buildPagePropsV2Candidate,
    buildTargetContexts,
    buildTargetSummary,
    buildRemainingSeededPagePropsV2AcquisitionPreflight,
    queryReadOnly,
    loadTargetMatchMetadata,
    loadExistingRawVersions,
    loadProtectedTableBaselineRows,
    loadSchemaConstraints,
    runCli,
};

if (require.main === module) {
    runCli()
        .then(result => {
            process.exitCode = result.status;
        })
        .catch(error => {
            process.stderr.write(`${error.stack || error.message}\n`);
            process.exitCode = 1;
        });
}
