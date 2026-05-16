#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const {
    TARGET: PREVIEW_TARGET,
    CANDIDATE_VERSION,
    HASH_STRATEGY,
    buildFotMobMatchUrl,
    fetchHtml,
    extractNextDataJsonFromHtml,
    getPageProps,
    buildPagePropsV2Candidate,
    computeStablePagePropsHash,
    listJsonPaths,
    summarizeJsonShape,
    comparePathCoverage,
    summarizeModuleCoverage,
} = require('./pageprops_v2_no_write_preview');
const { buildVersionAwareLookupSpec } = require('../../src/infrastructure/services/RawMatchDataVersionSelector');

const PHASE = 'PHASE5_21L2I_PAGEPROPS_V2_SINGLE_TARGET_WRITE_PREFLIGHT';
const PREVIOUS_PREVIEW_HASH = 'f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc';
const SOURCE = PREVIEW_TARGET.source;
const ROUTE = PREVIEW_TARGET.route;
const TARGET = Object.freeze({
    ...PREVIEW_TARGET,
    candidateVersion: CANDIDATE_VERSION,
    hashStrategy: HASH_STRATEGY,
    previousPreviewHash: PREVIOUS_PREVIEW_HASH,
});
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
const BLOCKED_TRUE_FLAGS = Object.freeze(['allowBrowserRuntime', 'allowProxyRuntime', 'bulk', 'execute', 'commit']);
const PROTECTED_TABLES = Object.freeze([
    'matches',
    'raw_match_data',
    'bookmaker_odds_history',
    'l3_features',
    'match_features_training',
    'predictions',
]);

function normalizeText(value) {
    return String(value || '').trim();
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
        matchId: null,
        externalId: null,
        homeTeam: null,
        awayTeam: null,
        candidateVersion: null,
        hashStrategy: null,
        previousPreviewHash: null,
        networkAuthorization: null,
        pagepropsV2WritePreflightAuthorization: null,
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
        bulk: false,
        execute: false,
        commit: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        route: 'route',
        'match-id': 'matchId',
        match_id: 'matchId',
        'external-id': 'externalId',
        external_id: 'externalId',
        'home-team': 'homeTeam',
        home_team: 'homeTeam',
        'away-team': 'awayTeam',
        away_team: 'awayTeam',
        'candidate-version': 'candidateVersion',
        candidate_version: 'candidateVersion',
        'hash-strategy': 'hashStrategy',
        hash_strategy: 'hashStrategy',
        'previous-preview-hash': 'previousPreviewHash',
        previous_preview_hash: 'previousPreviewHash',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'pageprops-v2-write-preflight-authorization': 'pagepropsV2WritePreflightAuthorization',
        pageprops_v2_write_preflight_authorization: 'pagepropsV2WritePreflightAuthorization',
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
        bulk: 'bulk',
        execute: 'execute',
        commit: 'commit',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'networkAuthorization',
        'pagepropsV2WritePreflightAuthorization',
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
        'bulk',
        'execute',
        'commit',
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
        errors.push(`${flagName}=yes is required in Phase 5.21L2I`);
        return;
    }
    errors.push(`missing ${flagName}=yes`);
}

function pushRequiredNo(errors, value, flagName) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.21L2I`);
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

function normalizePreflightInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        route: normalizeText(input.route),
        matchId: normalizeText(input.matchId),
        externalId: normalizeText(input.externalId),
        homeTeam: normalizeText(input.homeTeam),
        awayTeam: normalizeText(input.awayTeam),
        candidateVersion: normalizeText(input.candidateVersion),
        hashStrategy: normalizeText(input.hashStrategy),
        previousPreviewHash: normalizeText(input.previousPreviewHash).toLowerCase(),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        pagepropsV2WritePreflightAuthorization: normalizeBooleanFlag(
            input.pagepropsV2WritePreflightAuthorization,
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
        bulk: normalizeBooleanFlag(input.bulk, false),
        execute: normalizeBooleanFlag(input.execute, false),
        commit: normalizeBooleanFlag(input.commit, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validatePreflightInput(input = {}) {
    const value = normalizePreflightInput(input);
    const errors = [];
    if (value.unknown.length > 0) errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    requireExact(errors, value.source, SOURCE, 'source');
    requireExact(errors, value.route, ROUTE, 'route');
    requireExact(errors, value.matchId, TARGET.matchId, 'match-id');
    requireExact(errors, value.externalId, TARGET.externalId, 'external-id');
    requireExact(errors, value.homeTeam, TARGET.homeTeam, 'home-team');
    requireExact(errors, value.awayTeam, TARGET.awayTeam, 'away-team');
    requireExact(errors, value.candidateVersion, CANDIDATE_VERSION, 'candidate-version');
    requireExact(errors, value.hashStrategy, HASH_STRATEGY, 'hash-strategy');
    if (!value.previousPreviewHash) {
        errors.push('missing previous-preview-hash');
    } else if (!/^[a-f0-9]{64}$/.test(value.previousPreviewHash)) {
        errors.push('previous-preview-hash must be a 64-char lowercase hex string');
    }
    pushRequiredYes(errors, value.networkAuthorization, 'network-authorization');
    pushRequiredYes(errors, value.pagepropsV2WritePreflightAuthorization, 'pageprops-v2-write-preflight-authorization');
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

function buildHashComparison(stableHash, previousPreviewHash) {
    const current = normalizeText(stableHash).toLowerCase();
    const previous = normalizeText(previousPreviewHash).toLowerCase();
    return {
        stable_pageprops_hash: current,
        previous_preview_hash: previous,
        hash_matches_previous_preview: current === previous,
        hash_drift_detected: Boolean(current && previous && current !== previous),
    };
}

function summarizeExistingVersions(rows = []) {
    const versions = [
        ...new Set((Array.isArray(rows) ? rows : []).map(row => normalizeText(row.data_version)).filter(Boolean)),
    ];
    return versions.sort();
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

function buildExistingVersionDecision({ rows = [], targetHash = '' } = {}) {
    const safeRows = Array.isArray(rows) ? rows : [];
    assertNoDuplicateVersions(safeRows);
    const availableVersions = summarizeExistingVersions(safeRows);
    const v1Rows = safeRows.filter(row => normalizeText(row.data_version) === 'fotmob_html_hyd_v1');
    const v2Rows = safeRows.filter(row => normalizeText(row.data_version) === CANDIDATE_VERSION);
    const v1Exists = v1Rows.length === 1;
    const v2Exists = v2Rows.length === 1;
    const base = {
        fotmob_html_hyd_v1_exists: v1Exists,
        fotmob_pageprops_v2_exists: v2Exists,
        available_versions: availableVersions,
        existing_v1_row_id: v1Exists ? normalizeRowId(v1Rows[0]) : null,
        existing_v2_row_id: v2Exists ? normalizeRowId(v2Rows[0]) : null,
        target_version_exists: v2Exists,
    };

    if (!v1Exists) {
        return {
            existing_versions: base,
            decision: {
                would_insert_count: 0,
                would_update_count: 0,
                would_skip_count: 0,
                reason: 'required fotmob_html_hyd_v1 row missing',
                blocked_this_phase: true,
            },
        };
    }
    if (!v2Exists) {
        return {
            existing_versions: base,
            decision: {
                would_insert_count: 1,
                would_update_count: 0,
                would_skip_count: 0,
                reason: 'no existing fotmob_pageprops_v2 row for match_id',
                blocked_this_phase: false,
            },
        };
    }

    const existingHash = normalizeText(v2Rows[0].data_hash).toLowerCase();
    const candidateHash = normalizeText(targetHash).toLowerCase();
    if (existingHash === candidateHash) {
        return {
            existing_versions: {
                ...base,
                existing_v2_data_hash: existingHash,
            },
            decision: {
                would_insert_count: 0,
                would_update_count: 0,
                would_skip_count: 1,
                reason: 'existing fotmob_pageprops_v2 row already has same stable hash',
                blocked_this_phase: false,
            },
        };
    }

    return {
        existing_versions: {
            ...base,
            existing_v2_data_hash: existingHash,
        },
        decision: {
            would_insert_count: 0,
            would_update_count: 1,
            would_skip_count: 0,
            reason: 'existing fotmob_pageprops_v2 row hash differs; update requires separate authorization',
            blocked_this_phase: true,
        },
    };
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

function validateMatchMetadata(row = {}, input = {}) {
    const metadata = normalizeMatchMetadata(row);
    const errors = [];
    if (metadata.match_id !== input.matchId) errors.push('target match_id mismatch');
    if (metadata.external_id !== input.externalId) errors.push('target external_id mismatch');
    if (metadata.home_team !== input.homeTeam) errors.push('target home_team mismatch');
    if (metadata.away_team !== input.awayTeam) errors.push('target away_team mismatch');
    return errors;
}

function buildControlledFailure(input = {}, requestUrl, reason, context = {}) {
    return {
        phase: PHASE,
        ok: false,
        controlled_failure: true,
        preflight_only: true,
        source: SOURCE,
        route: ROUTE,
        match_id: input.matchId || TARGET.matchId,
        external_id: input.externalId || TARGET.externalId,
        home_team: input.homeTeam || TARGET.homeTeam,
        away_team: input.awayTeam || TARGET.awayTeam,
        candidate_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        request_url: requestUrl || buildFotMobMatchUrl(input.externalId || TARGET.externalId),
        final_url: context.final_url || null,
        http_status: context.http_status || null,
        content_type: context.content_type || null,
        body_byte_length: Number(context.body_byte_length || 0),
        body_sha256: context.body_sha256 || null,
        next_data_parse_ok: false,
        page_props_found: false,
        failure_reason: reason,
        db_write_executed: false,
        raw_match_data_write_executed: false,
        matches_write_executed: false,
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

function buildPagePropsV2SingleTargetWritePreflight({
    input = {},
    matchMetadata = {},
    existingRows = [],
    protectedTableRows = [],
    fetchResult = {},
    generatedAt = null,
} = {}) {
    const requestUrl = buildFotMobMatchUrl(input.externalId || TARGET.externalId);
    const matchErrors = validateMatchMetadata(matchMetadata, input);
    if (matchErrors.length > 0) {
        return buildControlledFailure(input, requestUrl, `TARGET_MATCH_INVALID:${matchErrors.join(',')}`);
    }
    if (!fetchResult.ok) {
        return buildControlledFailure(input, requestUrl, fetchResult.error || 'LIVE_REQUEST_FAILED', fetchResult);
    }

    let existingVersionDecision;
    try {
        existingVersionDecision = buildExistingVersionDecision({
            rows: existingRows,
            targetHash: null,
        });
    } catch (error) {
        return buildControlledFailure(input, requestUrl, error.message, fetchResult);
    }
    if (!existingVersionDecision.existing_versions.fotmob_html_hyd_v1_exists) {
        return buildControlledFailure(input, requestUrl, 'REQUIRED_V1_ROW_MISSING', fetchResult);
    }

    const extraction = extractNextDataJsonFromHtml(fetchResult.body);
    if (!extraction.ok) {
        return buildControlledFailure(input, requestUrl, extraction.error, fetchResult);
    }
    const pageProps = getPageProps(extraction.data);
    if (!pageProps) {
        return buildControlledFailure(input, requestUrl, 'PAGE_PROPS_NOT_FOUND', fetchResult);
    }

    const v1Row = existingRows.find(row => normalizeText(row.data_version) === 'fotmob_html_hyd_v1');
    const v1RawData = v1Row?.raw_data;
    if (!isPlainObject(v1RawData)) {
        return buildControlledFailure(input, requestUrl, 'STORED_V1_RAW_DATA_NOT_OBJECT', fetchResult);
    }

    const candidate = buildPagePropsV2Candidate({
        input,
        pageProps,
        fetchResult,
        generatedAt,
    });
    const stableHash = computeStablePagePropsHash(candidate);
    const hashComparison = buildHashComparison(stableHash, input.previousPreviewHash);
    let resolvedDecision;
    try {
        resolvedDecision = buildExistingVersionDecision({
            rows: existingRows,
            targetHash: stableHash,
        });
    } catch (error) {
        return buildControlledFailure(input, requestUrl, error.message, fetchResult);
    }

    const v1RawDataPaths = listJsonPaths(v1RawData);
    const v2PagePropsPaths = listJsonPaths(pageProps);
    const v1ContentPaths = listJsonPaths(objectOrEmpty(v1RawData.content));
    const v2ContentPaths = listJsonPaths(objectOrEmpty(pageProps.content));
    const pageCoverage = comparePathCoverage(v2PagePropsPaths, v1RawDataPaths);
    const contentCoverage = comparePathCoverage(v2ContentPaths, v1ContentPaths);
    const moduleCoverage = summarizeModuleCoverage(v1RawData, pageProps);
    const candidateJsonByteLength = jsonByteLength(candidate);
    const protectedTableBaseline = buildProtectedTableBaseline(protectedTableRows);
    const lookupSpec = buildVersionAwareLookupSpec();
    const payload = {
        phase: PHASE,
        ok: !resolvedDecision.decision.blocked_this_phase,
        preflight_only: true,
        source: SOURCE,
        route: ROUTE,
        match_id: input.matchId,
        external_id: input.externalId,
        home_team: input.homeTeam,
        away_team: input.awayTeam,
        match_metadata: normalizeMatchMetadata(matchMetadata),
        candidate_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        request_url: fetchResult.request_url || requestUrl,
        final_url: fetchResult.final_url || requestUrl,
        http_status: fetchResult.http_status,
        content_type: fetchResult.content_type,
        body_byte_length: Number(fetchResult.body_byte_length || 0),
        body_sha256: fetchResult.body_sha256 || null,
        next_data_parse_ok: true,
        page_props_found: true,
        candidate: {
            ...hashComparison,
            candidate_json_byte_length: candidateJsonByteLength,
            pageProps_top_level_keys: Object.keys(pageProps).sort(),
            pageProps_path_count: v2PagePropsPaths.length,
            pageProps_content_path_count: v2ContentPaths.length,
            pageProps_shape_summary: summarizeJsonShape(pageProps),
            candidate_shape_summary: summarizeJsonShape(candidate),
        },
        existing_versions: resolvedDecision.existing_versions,
        decision: resolvedDecision.decision,
        write_plan_for_next_phase: {
            insert_conflict_target: lookupSpec.conflict_target,
            insert_conflict_target_sql: lookupSpec.conflict_target_sql,
            target_table: 'raw_match_data',
            allowed_write_count: resolvedDecision.decision.would_insert_count,
            requires_final_db_write_confirmation: true,
        },
        proposed_row_metadata: {
            match_id: input.matchId,
            external_id: input.externalId,
            data_version: CANDIDATE_VERSION,
            data_hash: stableHash,
            collected_at: 'generated_at_write_time',
        },
        comparison: {
            v1_data_version: normalizeText(v1Row.data_version),
            v1_json_byte_length: jsonByteLength(v1RawData),
            v2_candidate_json_byte_length: candidateJsonByteLength,
            v1_path_count: v1RawDataPaths.length,
            v2_path_count: v2PagePropsPaths.length,
            v1_content_path_count: v1ContentPaths.length,
            v2_content_path_count: v2ContentPaths.length,
            v2_only_path_count: pageCoverage.v2_only_count,
            v1_only_path_count: pageCoverage.v1_only_count,
            content_missing_from_v2_count: contentCoverage.v1_only_count,
            content_missing_from_v1_count: contentCoverage.v2_only_count,
            content_diff_path_count: contentCoverage.v1_only_count + contentCoverage.v2_only_count,
        },
        module_coverage: moduleCoverage,
        limited_samples: {
            v2_only_paths: pageCoverage.v2_only_path_samples,
            v1_only_paths: pageCoverage.v1_only_path_samples,
            content_diff_paths: [
                ...(contentCoverage.v2_only_path_samples || []).map(path => `v2_only:${path}`),
                ...(contentCoverage.v1_only_path_samples || []).map(path => `v1_only:${path}`),
            ].slice(0, 50),
        },
        protected_table_baseline: protectedTableBaseline,
        db_write_executed: false,
        raw_match_data_write_executed: false,
        matches_write_executed: false,
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
    if (resolvedDecision.decision.blocked_this_phase) {
        payload.controlled_failure = true;
        payload.failure_reason = resolvedDecision.decision.reason;
    }
    return payload;
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
        WHERE match_id = $1 AND external_id = $2
        ORDER BY match_id
        `,
        [input.matchId, input.externalId]
    );
    const rows = result.rows || [];
    if (rows.length !== 1) throw new Error(`TARGET_MATCH_ROW_COUNT:${rows.length}`);
    return rows[0];
}

async function loadExistingRawVersions(client, input) {
    const result = await queryReadOnly(
        client,
        `
        SELECT id, match_id, external_id, data_version, data_hash, collected_at, raw_data
        FROM raw_match_data
        WHERE match_id = $1 AND external_id = $2
        ORDER BY data_version, id
        `,
        [input.matchId, input.externalId]
    );
    return result.rows || [];
}

async function loadProtectedTableBaseline(client) {
    const result = await queryReadOnly(
        client,
        `
        SELECT 'matches' AS table_name, COUNT(*) AS rows FROM matches
        UNION ALL
        SELECT 'bookmaker_odds_history', COUNT(*) FROM bookmaker_odds_history
        UNION ALL
        SELECT 'raw_match_data', COUNT(*) FROM raw_match_data
        UNION ALL
        SELECT 'l3_features', COUNT(*) FROM l3_features
        UNION ALL
        SELECT 'match_features_training', COUNT(*) FROM match_features_training
        UNION ALL
        SELECT 'predictions', COUNT(*) FROM predictions
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
        const payload = {
            phase: PHASE,
            ok: false,
            blocked: true,
            errors: validation.errors,
            preflight_only: true,
            db_write_executed: false,
            raw_match_data_write_executed: false,
            matches_write_executed: false,
            parser_features_executed: false,
            training_executed: false,
            prediction_executed: false,
            body_printed: false,
            body_saved: false,
            full_json_printed: false,
            full_json_saved: false,
            browser_used: false,
            proxy_used: false,
        };
        output(payload);
        return { status: 1, payload };
    }

    const input = validation.value;
    const requestUrl = buildFotMobMatchUrl(input.externalId);
    const pool =
        dependencies.client ||
        dependencies.matchMetadata ||
        dependencies.existingRows ||
        dependencies.protectedTableRows
            ? null
            : createDefaultPool();
    const client = dependencies.client || pool;
    try {
        const matchMetadata = dependencies.matchMetadata || (await loadTargetMatchMetadata(client, input));
        const existingRows = dependencies.existingRows || (await loadExistingRawVersions(client, input));
        const protectedTableRows = dependencies.protectedTableRows || (await loadProtectedTableBaseline(client));
        const fetchResult =
            dependencies.fetchResult ||
            (await fetchHtml(requestUrl, {
                fetchFn: dependencies.fetchFn,
            }));
        const payload = buildPagePropsV2SingleTargetWritePreflight({
            input,
            matchMetadata,
            existingRows,
            protectedTableRows,
            fetchResult,
            generatedAt: dependencies.generatedAt,
        });
        output(payload);
        return { status: payload.ok ? 0 : 1, payload };
    } catch (error) {
        const payload = buildControlledFailure(input, requestUrl, error.message);
        output(payload);
        return { status: 1, payload };
    } finally {
        if (pool && typeof pool.end === 'function') await pool.end();
    }
}

module.exports = {
    PHASE,
    TARGET,
    PREVIOUS_PREVIEW_HASH,
    parseArgs,
    normalizeBooleanFlag,
    validatePreflightInput,
    fetchHtml,
    extractNextDataJsonFromHtml,
    getPageProps,
    computeStablePagePropsHash,
    buildPagePropsV2Candidate,
    buildHashComparison,
    buildExistingVersionDecision,
    buildProtectedTableBaseline,
    buildPagePropsV2SingleTargetWritePreflight,
    queryReadOnly,
    loadTargetMatchMetadata,
    loadExistingRawVersions,
    loadProtectedTableBaseline,
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
