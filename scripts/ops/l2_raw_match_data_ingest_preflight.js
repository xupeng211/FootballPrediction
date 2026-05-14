#!/usr/bin/env node
/* eslint-disable complexity, max-lines */
'use strict';

const crypto = require('node:crypto');
const { extractFromHtml, transformToApiFormat } = require('../../src/parsers/fotmob/NextDataParser');
const { runFotMobDetailRouteSelector, buildRouteSelectorPreviewSummary } = require('./l2_raw_detail_preview');

const PHASE = 'PHASE5_15L2_RAW_MATCH_DATA_INGEST_PREFLIGHT';
const NEXT_REQUIRED_PHASE = 'Phase 5.16L2 controlled raw_match_data write';
const TARGET = Object.freeze({
    source: 'fotmob',
    route: 'html_hydration',
    autoRoute: 'auto',
    matchId: '53_20252026_4830746',
    externalId: '4830746',
    homeTeam: 'Angers',
    awayTeam: 'Strasbourg',
    dataVersion: 'fotmob_html_hyd_v1',
});
const EXPECTED_PROTECTED_TABLE_BASELINE = Object.freeze({
    matches: 10,
    raw_match_data: 2,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const FORBIDDEN_SQL_VERBS = Object.freeze([
    'INSERT',
    'UPDATE',
    'DELETE',
    'CREATE',
    'ALTER',
    'DROP',
    'TRUNCATE',
    'UPSERT',
    'MERGE',
    'GRANT',
    'REVOKE',
    'BEGIN',
    'COMMIT',
    'ROLLBACK',
    'LOCK',
    'COPY',
]);

function normalizeText(value) {
    return String(value || '').trim();
}

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') {
        return value;
    }
    if (value === null || value === undefined || value === '') {
        return fallback;
    }

    const normalized = String(value).trim().toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) {
        return true;
    }
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) {
        return false;
    }
    return fallback;
}

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') {
        return fallback;
    }
    const normalized = String(value).trim();
    if (!/^\d+$/.test(normalized)) {
        return Number.NaN;
    }
    return Number.parseInt(normalized, 10);
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) {
        return {
            value: arg.slice(arg.indexOf('=') + 1),
            consumedNext: false,
        };
    }

    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) {
        return {
            value: nextArg,
            consumedNext: true,
        };
    }

    return {
        value: true,
        consumedNext: false,
    };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        source: null,
        route: null,
        matchId: null,
        externalId: null,
        homeTeam: null,
        awayTeam: null,
        dataVersion: null,
        networkAuthorization: null,
        livePreviewAuthorization: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowMatchesWrite: null,
        allowTraining: null,
        allowPrediction: null,
        allowBrowserRuntime: null,
        allowProxyRuntime: null,
        concurrency: null,
        retry: null,
        printBody: null,
        saveBody: null,
        commit: false,
        execute: false,
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
        'data-version': 'dataVersion',
        data_version: 'dataVersion',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'live-preview-authorization': 'livePreviewAuthorization',
        live_preview_authorization: 'livePreviewAuthorization',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        'allow-browser-runtime': 'allowBrowserRuntime',
        allow_browser_runtime: 'allowBrowserRuntime',
        'allow-proxy-runtime': 'allowProxyRuntime',
        allow_proxy_runtime: 'allowProxyRuntime',
        concurrency: 'concurrency',
        retry: 'retry',
        'print-body': 'printBody',
        print_body: 'printBody',
        'save-body': 'saveBody',
        save_body: 'saveBody',
        commit: 'commit',
        execute: 'execute',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'networkAuthorization',
        'livePreviewAuthorization',
        'allowDbWrite',
        'allowRawMatchDataWrite',
        'allowMatchesWrite',
        'allowTraining',
        'allowPrediction',
        'allowBrowserRuntime',
        'allowProxyRuntime',
        'printBody',
        'saveBody',
        'commit',
        'execute',
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
        if (consumedNext) {
            index += 1;
        }

        if (!optionKey) {
            options.unknown.push(rawKey);
            continue;
        }

        if (booleanKeys.has(optionKey)) {
            options[optionKey] = normalizeBooleanFlag(value, true);
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : value;
    }

    return options;
}

function includesText(value, expected) {
    return normalizeText(value).toLowerCase().includes(normalizeText(expected).toLowerCase());
}

function pushRequiredTrueError(errors, value, flagName) {
    if (value === true) {
        return;
    }
    if (value === false) {
        errors.push(`${flagName}=yes is required in Phase 5.15L2`);
        return;
    }
    errors.push(`missing ${flagName}=yes`);
}

function pushRequiredFalseError(errors, value, flagName) {
    if (value === false) {
        return;
    }
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.15L2`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function normalizePreflightInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        route: normalizeText(input.route).toLowerCase(),
        matchId: normalizeText(input.matchId),
        externalId: normalizeText(input.externalId),
        homeTeam: normalizeText(input.homeTeam),
        awayTeam: normalizeText(input.awayTeam),
        dataVersion: normalizeText(input.dataVersion).toLowerCase(),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        livePreviewAuthorization: normalizeBooleanFlag(input.livePreviewAuthorization, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        allowBrowserRuntime: normalizeBooleanFlag(input.allowBrowserRuntime, false),
        allowProxyRuntime: normalizeBooleanFlag(input.allowProxyRuntime, false),
        concurrency: parseInteger(input.concurrency, null),
        retry: parseInteger(input.retry, null),
        printBody: normalizeBooleanFlag(input.printBody, undefined),
        saveBody: normalizeBooleanFlag(input.saveBody, undefined),
        commit: normalizeBooleanFlag(input.commit, false),
        execute: normalizeBooleanFlag(input.execute, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validatePreflightInput(input = {}) {
    const value = normalizePreflightInput(input);
    const errors = [];

    if (value.unknown.length > 0) {
        errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    }
    if (!value.source) {
        errors.push('missing source: provide --source=fotmob');
    } else if (value.source !== TARGET.source) {
        errors.push('unsupported source: only fotmob is allowed');
    }
    if (!value.route) {
        errors.push('missing route: provide --route=html_hydration');
    } else if (![TARGET.route, TARGET.autoRoute].includes(value.route)) {
        errors.push('unsupported route: Phase 5.15L2 only allows html_hydration or auto');
    }
    if (!value.matchId) {
        errors.push('missing match-id');
    } else if (value.matchId !== TARGET.matchId) {
        errors.push(`match-id must be ${TARGET.matchId} in Phase 5.15L2`);
    }
    if (!value.externalId) {
        errors.push('missing external-id');
    } else if (value.externalId !== TARGET.externalId) {
        errors.push(`external-id must be ${TARGET.externalId} in Phase 5.15L2`);
    }
    if (!value.homeTeam) {
        errors.push('missing home-team');
    } else if (!includesText(value.homeTeam, TARGET.homeTeam)) {
        errors.push(`home-team must contain ${TARGET.homeTeam}`);
    }
    if (!value.awayTeam) {
        errors.push('missing away-team');
    } else if (!includesText(value.awayTeam, TARGET.awayTeam)) {
        errors.push(`away-team must contain ${TARGET.awayTeam}`);
    }
    if (!value.dataVersion) {
        errors.push('missing data-version');
    } else if (value.dataVersion !== TARGET.dataVersion) {
        errors.push(`data-version must be ${TARGET.dataVersion} in Phase 5.15L2`);
    }

    pushRequiredTrueError(errors, value.networkAuthorization, 'network-authorization');
    pushRequiredTrueError(errors, value.livePreviewAuthorization, 'live-preview-authorization');
    pushRequiredFalseError(errors, value.allowDbWrite, 'allow-db-write');
    pushRequiredFalseError(errors, value.allowRawMatchDataWrite, 'allow-raw-match-data-write');
    pushRequiredFalseError(errors, value.allowMatchesWrite, 'allow-matches-write');
    pushRequiredFalseError(errors, value.allowTraining, 'allow-training');
    pushRequiredFalseError(errors, value.allowPrediction, 'allow-prediction');
    pushRequiredFalseError(errors, value.printBody, 'print-body');
    pushRequiredFalseError(errors, value.saveBody, 'save-body');

    if (value.allowBrowserRuntime === true) {
        errors.push('allow-browser-runtime=yes is blocked in Phase 5.15L2');
    }
    if (value.allowProxyRuntime === true) {
        errors.push('allow-proxy-runtime=yes is blocked in Phase 5.15L2');
    }
    if (value.concurrency !== 1) {
        errors.push(value.concurrency > 1 ? 'concurrency > 1 is blocked' : 'concurrency must be 1');
    }
    if (value.retry !== 0) {
        errors.push(value.retry > 0 ? 'retry > 0 is blocked' : 'retry must be 0');
    }
    if (value.commit === true) {
        errors.push('commit=yes is blocked in Phase 5.15L2');
    }
    if (value.execute === true) {
        errors.push('execute=yes is blocked in Phase 5.15L2');
    }

    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function canonicalizeValue(value, inArray = false) {
    if (value === undefined || typeof value === 'function' || typeof value === 'symbol') {
        return inArray ? null : undefined;
    }
    if (value === null || typeof value === 'string' || typeof value === 'boolean') {
        return value;
    }
    if (typeof value === 'number') {
        return Number.isFinite(value) ? value : null;
    }
    if (Array.isArray(value)) {
        return value.map(item => {
            const normalized = canonicalizeValue(item, true);
            return normalized === undefined ? null : normalized;
        });
    }
    if (value && typeof value === 'object') {
        const normalized = {};
        for (const key of Object.keys(value).sort()) {
            const child = canonicalizeValue(value[key], false);
            if (child !== undefined) {
                normalized[key] = child;
            }
        }
        return normalized;
    }
    return null;
}

function canonicalizeJson(value) {
    return JSON.stringify(canonicalizeValue(value));
}

function sha256Text(text) {
    return crypto
        .createHash('sha256')
        .update(String(text || ''), 'utf8')
        .digest('hex');
}

function sha256CanonicalJson(value) {
    return sha256Text(canonicalizeJson(value));
}

function jsonClone(value, fallback = {}) {
    if (value === undefined || value === null) {
        return fallback;
    }
    return JSON.parse(JSON.stringify(value));
}

function buildRawDataFromPreviewPayload(payload = {}, previewSummary = {}, input = {}) {
    const value = normalizePreflightInput(input);
    const safePayload = payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {};
    const payloadMeta = safePayload._meta && typeof safePayload._meta === 'object' ? safePayload._meta : {};

    return {
        _meta: {
            source: TARGET.source,
            route: previewSummary.selected_route || TARGET.route,
            requested_route: value.route || TARGET.route,
            request_url: previewSummary.request_url || null,
            final_url: previewSummary.final_url || null,
            fetch_body_sha256: previewSummary.body_sha256 || null,
            fetch_body_byte_length: Number(previewSummary.body_byte_length || 0),
            hydration_parse_ok: previewSummary.hydration_parse_ok === true,
            looks_like_valid_match_detail: previewSummary.looks_like_valid_match_detail === true,
            parser: 'NextDataParser.transformToApiFormat',
            data_version: TARGET.dataVersion,
            collected_at_policy: 'generated_by_phase_5_16_db_write_timestamp',
            full_html_body_stored: false,
            http_response_string_stored: false,
            has_stats: payloadMeta.hasStats === true || Boolean(safePayload.content?.stats),
            has_lineup: payloadMeta.hasLineup === true || Boolean(safePayload.content?.lineup),
            has_shotmap: payloadMeta.hasShotmap === true || Boolean(safePayload.content?.shotmap),
        },
        content: jsonClone(safePayload.content || {}),
        general: jsonClone(safePayload.general || {}),
        header: jsonClone(safePayload.header || {}),
        matchId: String(safePayload.matchId || value.externalId || TARGET.externalId),
    };
}

function validateRawDataShape(rawData = {}) {
    const errors = [];
    for (const key of ['_meta', 'content', 'general', 'header', 'matchId']) {
        if (!Object.prototype.hasOwnProperty.call(rawData, key)) {
            errors.push(`raw_data missing ${key}`);
        }
    }
    if (rawData._meta?.full_html_body_stored !== false) {
        errors.push('raw_data._meta.full_html_body_stored must be false');
    }
    if (rawData._meta?.http_response_string_stored !== false) {
        errors.push('raw_data._meta.http_response_string_stored must be false');
    }
    return errors;
}

function buildAffectedPreview({ matchId, externalId, existingRows = [], rawDataHash }) {
    if (!Array.isArray(existingRows) || existingRows.length === 0) {
        return {
            match_id: matchId,
            external_id: externalId,
            decision: 'would_insert',
            reason: 'no existing raw_match_data row for match_id',
        };
    }

    const existingRow = existingRows[0];
    if (normalizeText(existingRow.data_hash) === rawDataHash) {
        return {
            match_id: matchId,
            external_id: externalId,
            decision: 'would_skip',
            reason: 'existing raw_match_data data_hash matches computed raw_data_hash',
            existing_data_hash: normalizeText(existingRow.data_hash),
            new_data_hash: rawDataHash,
        };
    }

    return {
        match_id: matchId,
        external_id: externalId,
        decision: 'would_update',
        reason: 'existing raw_match_data data_hash differs from computed raw_data_hash',
        existing_data_hash: normalizeText(existingRow.data_hash) || null,
        new_data_hash: rawDataHash,
    };
}

function buildProtectedTableBaseline(source = {}) {
    const rows = Array.isArray(source) ? source : null;
    const objectSource = rows
        ? Object.fromEntries(rows.map(row => [row.table_name, Number(row.rows)]))
        : source && typeof source === 'object'
          ? source
          : {};

    return {
        matches: Number(objectSource.matches ?? 0),
        raw_match_data: Number(objectSource.raw_match_data ?? 0),
        bookmaker_odds_history: Number(objectSource.bookmaker_odds_history ?? 0),
        l3_features: Number(objectSource.l3_features ?? 0),
        match_features_training: Number(objectSource.match_features_training ?? 0),
        predictions: Number(objectSource.predictions ?? 0),
    };
}

function validateProtectedTableBaseline(baseline = {}) {
    return Object.entries(EXPECTED_PROTECTED_TABLE_BASELINE)
        .filter(([key, expected]) => Number(baseline[key]) !== expected)
        .map(([key, expected]) => `${key} baseline expected ${expected}, got ${baseline[key]}`);
}

function assertSafeSelect(sql) {
    const text = String(sql || '').trim();
    const withoutTrailingSemicolon = text.replace(/;+\s*$/, '');
    if (!/^\s*SELECT\b/i.test(withoutTrailingSemicolon)) {
        throw new Error('Unsafe SQL blocked: query must start with SELECT');
    }
    if (withoutTrailingSemicolon.includes(';')) {
        throw new Error('Unsafe SQL blocked: multiple statements are not allowed');
    }
    if (/\bFOR\s+UPDATE\b/i.test(withoutTrailingSemicolon)) {
        throw new Error('Unsafe SQL blocked: SELECT FOR UPDATE is not allowed');
    }
    for (const verb of FORBIDDEN_SQL_VERBS) {
        if (new RegExp(`\\b${verb}\\b`, 'i').test(withoutTrailingSemicolon)) {
            throw new Error(`Unsafe SQL blocked: ${verb} is not allowed`);
        }
    }
}

async function safeSelect(pool, sql, values = []) {
    assertSafeSelect(sql);
    return pool.query(sql, values);
}

function buildDbConfig() {
    return {
        host: process.env.DB_HOST || process.env.POSTGRES_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || process.env.POSTGRES_PORT || '5432', 10),
        database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
        user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD || 'football_pass',
        application_name: 'l2_raw_match_data_ingest_preflight',
        max: 2,
        idleTimeoutMillis: 5000,
        connectionTimeoutMillis: 5000,
    };
}

function createPgPool() {
    const { Pool } = require('pg');
    return new Pool(buildDbConfig());
}

function hasCustomDbDependencies(dependencies = {}) {
    return (
        dependencies.pool ||
        dependencies.createPool ||
        Array.isArray(dependencies.targetMatchRows) ||
        Array.isArray(dependencies.existingRawMatchDataRows) ||
        dependencies.protectedTableBaseline ||
        typeof dependencies.selectTargetMatch === 'function' ||
        typeof dependencies.selectExistingRawMatchData === 'function' ||
        typeof dependencies.selectProtectedTableBaseline === 'function'
    );
}

async function selectTargetMatch(pool, value, dependencies = {}) {
    if (Array.isArray(dependencies.targetMatchRows)) {
        return dependencies.targetMatchRows;
    }
    if (typeof dependencies.selectTargetMatch === 'function') {
        return dependencies.selectTargetMatch({ input: value });
    }

    const query = `
        SELECT match_id, external_id, home_team, away_team, match_date, status
        FROM matches
        WHERE match_id = $1
           OR external_id = $2
        ORDER BY match_id
    `;
    const result = await safeSelect(pool, query, [value.matchId, value.externalId]);
    return result.rows || [];
}

async function selectExistingRawMatchData(pool, value, dependencies = {}) {
    if (Array.isArray(dependencies.existingRawMatchDataRows)) {
        return dependencies.existingRawMatchDataRows;
    }
    if (typeof dependencies.selectExistingRawMatchData === 'function') {
        return dependencies.selectExistingRawMatchData({ input: value });
    }

    const query = `
        SELECT id, match_id, external_id, collected_at, data_version, data_hash
        FROM raw_match_data
        WHERE match_id = $1
           OR external_id = $2
        ORDER BY collected_at DESC NULLS LAST, id DESC
    `;
    const result = await safeSelect(pool, query, [value.matchId, value.externalId]);
    return result.rows || [];
}

async function selectProtectedTableBaseline(pool, dependencies = {}) {
    if (dependencies.protectedTableBaseline) {
        return buildProtectedTableBaseline(dependencies.protectedTableBaseline);
    }
    if (typeof dependencies.selectProtectedTableBaseline === 'function') {
        return buildProtectedTableBaseline(await dependencies.selectProtectedTableBaseline());
    }

    const query = `
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
    `;
    const result = await safeSelect(pool, query, []);
    return buildProtectedTableBaseline(result.rows || []);
}

function shouldCreateDefaultPool(dependencies = {}) {
    if (dependencies.pool) {
        return false;
    }
    if (!hasCustomDbDependencies(dependencies)) {
        return true;
    }
    const targetNeedsPool =
        !Array.isArray(dependencies.targetMatchRows) && typeof dependencies.selectTargetMatch !== 'function';
    const existingRawNeedsPool =
        !Array.isArray(dependencies.existingRawMatchDataRows) &&
        typeof dependencies.selectExistingRawMatchData !== 'function';
    const baselineNeedsPool =
        !dependencies.protectedTableBaseline && typeof dependencies.selectProtectedTableBaseline !== 'function';
    return targetNeedsPool || existingRawNeedsPool || baselineNeedsPool;
}

async function resolveDbState(value, dependencies = {}) {
    const usePool = shouldCreateDefaultPool(dependencies);
    const pool = dependencies.pool || (usePool ? (dependencies.createPool || createPgPool)() : null);
    const shouldEndPool = Boolean(pool && !dependencies.pool);

    try {
        const targetMatchRows = await selectTargetMatch(pool, value, dependencies);
        const existingRawMatchDataRows = await selectExistingRawMatchData(pool, value, dependencies);
        const protectedTableBaseline = await selectProtectedTableBaseline(pool, dependencies);
        return {
            targetMatchRows,
            existingRawMatchDataRows,
            protectedTableBaseline,
        };
    } finally {
        if (shouldEndPool && typeof pool.end === 'function') {
            await pool.end();
        }
    }
}

function validateTargetMatchRows(rows = []) {
    const errors = [];
    if (!Array.isArray(rows) || rows.length !== 1) {
        return [`target match SELECT expected exactly 1 row, got ${Array.isArray(rows) ? rows.length : 0}`];
    }
    const row = rows[0];
    if (normalizeText(row.match_id) !== TARGET.matchId) {
        errors.push(`target match_id mismatch: ${row.match_id}`);
    }
    if (normalizeText(row.external_id) !== TARGET.externalId) {
        errors.push(`target external_id mismatch: ${row.external_id}`);
    }
    if (!includesText(row.home_team, TARGET.homeTeam)) {
        errors.push(`target home_team must contain ${TARGET.homeTeam}`);
    }
    if (!includesText(row.away_team, TARGET.awayTeam)) {
        errors.push(`target away_team must contain ${TARGET.awayTeam}`);
    }
    return errors;
}

function validateExistingRawRows(rows = []) {
    if (!Array.isArray(rows)) {
        return ['existing raw_match_data SELECT did not return an array'];
    }
    if (rows.length > 1) {
        return [`existing raw_match_data SELECT expected <= 1 row, got ${rows.length}`];
    }
    return [];
}

function createCapturingFetchImpl(fetchImpl, captures) {
    return async function capturingFetch(url, options) {
        const response = await fetchImpl(url, options);
        return {
            status: response.status,
            statusCode: response.statusCode,
            ok: response.ok,
            url: response.url || String(url),
            headers: response.headers || {},
            text: async () => {
                const body = typeof response.text === 'function' ? await response.text() : '';
                captures.push({
                    request_url: String(url),
                    final_url: response.url || String(url),
                    body,
                });
                return body;
            },
        };
    };
}

function extractPayloadFromBody(body, input = {}) {
    const bodyText = String(body || '');
    const nextData = extractFromHtml(bodyText);
    if (!nextData.success) {
        throw new Error(nextData.error || 'NEXT_DATA_PARSE_FAILED');
    }

    const transformed = transformToApiFormat(nextData.data, input.externalId || TARGET.externalId);
    if (!transformed) {
        throw new Error('NEXT_DATA_TRANSFORM_FAILED');
    }
    return transformed;
}

function buildRouteSelectorInput(value = {}) {
    return {
        source: value.source || TARGET.source,
        matchId: value.matchId || TARGET.matchId,
        externalId: value.externalId || TARGET.externalId,
        homeTeam: value.homeTeam || TARGET.homeTeam,
        awayTeam: value.awayTeam || TARGET.awayTeam,
        route: value.route || TARGET.route,
        networkAuthorization: true,
        livePreviewAuthorization: true,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        concurrency: 1,
        retry: 0,
        printBody: false,
        saveBody: false,
    };
}

async function recapturePreviewPayload(value, dependencies = {}) {
    const fetchImpl = dependencies.fetchImpl || global.fetch;
    if (typeof fetchImpl !== 'function') {
        throw new Error('FETCH_UNAVAILABLE: native fetch is not available');
    }

    const captures = [];
    const selectorInput = buildRouteSelectorInput(value);
    const selectorDependencies = {
        ...dependencies,
        fetchImpl: createCapturingFetchImpl(fetchImpl, captures),
    };
    const selectorResult = await runFotMobDetailRouteSelector(selectorInput, selectorDependencies);
    const summary = buildRouteSelectorPreviewSummary(selectorInput, selectorResult);
    const capture =
        captures.find(item => item.final_url === summary.final_url || item.request_url === summary.request_url) ||
        captures[captures.length - 1];

    if (!capture) {
        throw new Error('NO_CAPTURED_PREVIEW_BODY');
    }

    return {
        summary,
        payload: extractPayloadFromBody(capture.body, value),
    };
}

async function resolvePreviewPayload(value, dependencies = {}) {
    if (dependencies.previewPayloadResult) {
        return dependencies.previewPayloadResult;
    }
    if (typeof dependencies.resolvePreviewPayload === 'function') {
        return dependencies.resolvePreviewPayload({ input: value });
    }
    return recapturePreviewPayload(value, dependencies);
}

function validatePreviewSummary(summary = {}) {
    const errors = [];
    if (summary.ok !== true) {
        errors.push(summary.controlled_error || 'route selector did not return a valid match detail payload');
    }
    if (summary.selected_route !== TARGET.route) {
        errors.push(`selected_route must be ${TARGET.route}, got ${summary.selected_route || 'none'}`);
    }
    if (Number(summary.http_status) < 200 || Number(summary.http_status) >= 300) {
        errors.push(`http_status must be 2xx, got ${summary.http_status}`);
    }
    if (summary.hydration_parse_ok !== true) {
        errors.push('hydration_parse_ok must be true');
    }
    if (summary.looks_like_valid_match_detail !== true) {
        errors.push('looks_like_valid_match_detail must be true');
    }
    if (summary.body_printed === true) {
        errors.push('body_printed=true is blocked');
    }
    if (summary.body_saved === true) {
        errors.push('body_saved=true is blocked');
    }
    if (summary.browser_used === true) {
        errors.push('browser_used=true is blocked');
    }
    if (summary.proxy_used === true) {
        errors.push('proxy_used=true is blocked');
    }
    return errors;
}

function buildInvalidPreflight(input = {}, errors = []) {
    return {
        phase: PHASE,
        preflight_only: true,
        ok: false,
        source: input.source || null,
        route: input.route || null,
        match_id: input.matchId || null,
        external_id: input.externalId || null,
        controlled_error: `INVALID_INGEST_PREFLIGHT_INPUT:${errors.join('; ')}`,
        errors,
        raw_match_data_write_allowed_this_phase: false,
        db_write_allowed_this_phase: false,
        matches_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_write_matches: false,
        body_printed: false,
        body_saved: false,
        browser_used: false,
        proxy_used: false,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function countDecision(affectedPreview, decision) {
    return affectedPreview.decision === decision ? 1 : 0;
}

async function buildRawMatchDataIngestPreflight(input = {}, dependencies = {}) {
    const validation = validatePreflightInput(input);
    if (!validation.ok) {
        return buildInvalidPreflight(input, validation.errors);
    }

    const value = validation.value;
    const preview = await resolvePreviewPayload(value, dependencies);
    const previewSummary = preview.summary || {};
    const previewErrors = validatePreviewSummary(previewSummary);
    if (previewErrors.length > 0) {
        return buildInvalidPreflight(value, previewErrors);
    }

    const rawData = buildRawDataFromPreviewPayload(preview.payload, previewSummary, value);
    const rawDataErrors = validateRawDataShape(rawData);
    if (rawDataErrors.length > 0) {
        return buildInvalidPreflight(value, rawDataErrors);
    }

    const rawDataHash = sha256CanonicalJson(rawData);
    const dbState = await resolveDbState(value, dependencies);
    const targetErrors = validateTargetMatchRows(dbState.targetMatchRows);
    const existingRawErrors = validateExistingRawRows(dbState.existingRawMatchDataRows);
    const protectedBaseline = buildProtectedTableBaseline(dbState.protectedTableBaseline);
    const baselineErrors = validateProtectedTableBaseline(protectedBaseline);
    const dbErrors = [...targetErrors, ...existingRawErrors, ...baselineErrors];
    if (dbErrors.length > 0) {
        return buildInvalidPreflight(value, dbErrors);
    }

    const affectedPreview = buildAffectedPreview({
        matchId: TARGET.matchId,
        externalId: TARGET.externalId,
        existingRows: dbState.existingRawMatchDataRows,
        rawDataHash,
    });

    return {
        phase: PHASE,
        preflight_only: true,
        ok: true,
        source: TARGET.source,
        route: previewSummary.selected_route,
        requested_route: value.route,
        match_id: TARGET.matchId,
        external_id: TARGET.externalId,
        home_team: TARGET.homeTeam,
        away_team: TARGET.awayTeam,
        data_version: TARGET.dataVersion,
        live_preview_used: true,
        selected_route: previewSummary.selected_route,
        request_url: previewSummary.request_url,
        final_url: previewSummary.final_url,
        http_status: previewSummary.http_status,
        content_type: previewSummary.content_type,
        body_byte_length: previewSummary.body_byte_length,
        body_sha256: previewSummary.body_sha256,
        hydration_parse_ok: previewSummary.hydration_parse_ok,
        looks_like_valid_match_detail: previewSummary.looks_like_valid_match_detail,
        raw_data_canonicalized: true,
        raw_data_hash: rawDataHash,
        existing_raw_match_data_found: dbState.existingRawMatchDataRows.length > 0,
        would_insert: affectedPreview.decision === 'would_insert',
        would_update: affectedPreview.decision === 'would_update',
        would_skip: affectedPreview.decision === 'would_skip',
        would_insert_count: countDecision(affectedPreview, 'would_insert'),
        would_update_count: countDecision(affectedPreview, 'would_update'),
        would_skip_count: countDecision(affectedPreview, 'would_skip'),
        affected_preview: affectedPreview,
        protected_table_baseline: protectedBaseline,
        raw_match_data_write_allowed_this_phase: false,
        db_write_allowed_this_phase: false,
        matches_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_write_matches: false,
        body_printed: false,
        body_saved: false,
        browser_used: false,
        proxy_used: false,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_raw_match_data_ingest_preflight.js --source=fotmob --route=html_hydration --match-id=53_20252026_4830746 --external-id=4830746 --home-team=Angers --away-team=Strasbourg --data-version=fotmob_html_hyd_v1 --network-authorization=yes --live-preview-authorization=yes --allow-db-write=no --allow-raw-match-data-write=no --allow-matches-write=no --allow-training=no --allow-prediction=no --concurrency=1 --retry=0 --print-body=no --save-body=no',
        '',
        'Safety:',
        '  Phase 5.15L2 is preflight-only: one controlled live preview, SELECT-only DB reads, no raw_match_data write, no DB write, no full body print/save.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const stdout = io.stdout || process.stdout.write.bind(process.stdout);
    const args = parseArgs(argv);
    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }

    const preflight = await buildRawMatchDataIngestPreflight(args, dependencies);
    stdout(`${JSON.stringify(preflight, null, 2)}\n`);
    return preflight.ok ? 0 : 1;
}

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            process.stdout.write(
                `${JSON.stringify(
                    {
                        phase: PHASE,
                        preflight_only: true,
                        ok: false,
                        controlled_error: String(error.message || error),
                        raw_match_data_write_allowed_this_phase: false,
                        db_write_allowed_this_phase: false,
                        would_write_raw_match_data: false,
                        would_write_db: false,
                        body_printed: false,
                        body_saved: false,
                        browser_used: false,
                        proxy_used: false,
                        next_required_phase: NEXT_REQUIRED_PHASE,
                    },
                    null,
                    2
                )}\n`
            );
            process.exitCode = 1;
        });
}

module.exports = {
    parseArgs,
    normalizeBooleanFlag,
    validatePreflightInput,
    canonicalizeJson,
    sha256CanonicalJson,
    buildRawDataFromPreviewPayload,
    buildAffectedPreview,
    buildProtectedTableBaseline,
    buildRawMatchDataIngestPreflight,
    runCli,
};
