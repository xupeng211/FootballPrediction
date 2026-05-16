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
    computeStablePagePropsHash,
    listJsonPaths,
    summarizeJsonShape,
} = require('./pageprops_v2_no_write_preview');
const { buildVersionAwareLookupSpec } = require('../../src/infrastructure/services/RawMatchDataVersionSelector');

const PHASE = 'PHASE5_21L2J_PAGEPROPS_V2_SINGLE_TARGET_CONTROLLED_WRITE';
const BASELINE_PAGEPROPS_HASH = 'f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc';
const SOURCE = PREVIEW_TARGET.source;
const ROUTE = PREVIEW_TARGET.route;
const TARGET = Object.freeze({
    ...PREVIEW_TARGET,
    candidateVersion: CANDIDATE_VERSION,
    hashStrategy: HASH_STRATEGY,
    baselinePagepropsHash: BASELINE_PAGEPROPS_HASH,
});
const REQUIRED_YES_FLAGS = Object.freeze([
    'networkAuthorization',
    'finalDbWriteConfirmation',
    'allowDbWrite',
    'allowRawMatchDataWrite',
]);
const REQUIRED_NO_FLAGS = Object.freeze([
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
    'bulk',
    'execute',
    'commit',
    'executeMultiple',
    'rewriteExisting',
    'dropV1',
    'allowSchemaMigration',
    'alterTable',
]);
const PROTECTED_TABLES = Object.freeze([
    'matches',
    'raw_match_data',
    'bookmaker_odds_history',
    'l3_features',
    'match_features_training',
    'predictions',
]);
const EXPECTED_ROW_COUNTS_BEFORE = Object.freeze({
    matches: 10,
    raw_match_data: 10,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const EXPECTED_ROW_COUNTS_AFTER = Object.freeze({
    ...EXPECTED_ROW_COUNTS_BEFORE,
    raw_match_data: 11,
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
        matchId: null,
        externalId: null,
        homeTeam: null,
        awayTeam: null,
        candidateVersion: null,
        hashStrategy: null,
        baselinePagepropsHash: null,
        networkAuthorization: null,
        finalDbWriteConfirmation: null,
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
        executeMultiple: false,
        rewriteExisting: false,
        dropV1: false,
        allowSchemaMigration: false,
        alterTable: false,
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
        'baseline-pageprops-hash': 'baselinePagepropsHash',
        baseline_pageprops_hash: 'baselinePagepropsHash',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'final-db-write-confirmation': 'finalDbWriteConfirmation',
        final_db_write_confirmation: 'finalDbWriteConfirmation',
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
        'execute-multiple': 'executeMultiple',
        execute_multiple: 'executeMultiple',
        'rewrite-existing': 'rewriteExisting',
        rewrite_existing: 'rewriteExisting',
        'drop-v1': 'dropV1',
        drop_v1: 'dropV1',
        'allow-schema-migration': 'allowSchemaMigration',
        allow_schema_migration: 'allowSchemaMigration',
        'alter-table': 'alterTable',
        alter_table: 'alterTable',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'networkAuthorization',
        'finalDbWriteConfirmation',
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
        'executeMultiple',
        'rewriteExisting',
        'dropV1',
        'allowSchemaMigration',
        'alterTable',
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
        errors.push(`${flagName}=yes is required in Phase 5.21L2J`);
        return;
    }
    errors.push(`missing ${flagName}=yes`);
}

function pushRequiredNo(errors, value, flagName) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.21L2J`);
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

function normalizeWriteInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        route: normalizeText(input.route),
        matchId: normalizeText(input.matchId),
        externalId: normalizeText(input.externalId),
        homeTeam: normalizeText(input.homeTeam),
        awayTeam: normalizeText(input.awayTeam),
        candidateVersion: normalizeText(input.candidateVersion),
        hashStrategy: normalizeText(input.hashStrategy),
        baselinePagepropsHash: normalizeText(input.baselinePagepropsHash).toLowerCase(),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        finalDbWriteConfirmation: normalizeBooleanFlag(input.finalDbWriteConfirmation, undefined),
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
        executeMultiple: normalizeBooleanFlag(input.executeMultiple, false),
        rewriteExisting: normalizeBooleanFlag(input.rewriteExisting, false),
        dropV1: normalizeBooleanFlag(input.dropV1, false),
        allowSchemaMigration: normalizeBooleanFlag(input.allowSchemaMigration, false),
        alterTable: normalizeBooleanFlag(input.alterTable, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validateWriteInput(input = {}) {
    const value = normalizeWriteInput(input);
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
    if (!value.baselinePagepropsHash) {
        errors.push('missing baseline-pageprops-hash');
    } else if (!/^[a-f0-9]{64}$/.test(value.baselinePagepropsHash)) {
        errors.push('baseline-pageprops-hash must be a 64-char lowercase hex string');
    } else if (value.baselinePagepropsHash !== BASELINE_PAGEPROPS_HASH) {
        errors.push(`baseline-pageprops-hash must be ${BASELINE_PAGEPROPS_HASH}`);
    }
    for (const key of REQUIRED_YES_FLAGS) {
        pushRequiredYes(
            errors,
            value[key],
            key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)
        );
    }
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

function jsonByteLength(value) {
    return Buffer.byteLength(JSON.stringify(value), 'utf8');
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

function validateExactRowCounts(actual = {}, expected = {}) {
    const errors = [];
    for (const table of PROTECTED_TABLES) {
        if (Number(actual[table]) !== Number(expected[table])) {
            errors.push(`${table} expected ${expected[table]} got ${actual[table]}`);
        }
    }
    return errors;
}

function normalizeRowId(row = {}) {
    if (row.id === undefined || row.id === null) return null;
    return String(row.id);
}

function normalizeRawRowSummary(row = {}) {
    return {
        id: normalizeRowId(row),
        match_id: normalizeText(row.match_id),
        external_id: normalizeText(row.external_id),
        data_version: normalizeText(row.data_version),
        data_hash: normalizeText(row.data_hash).toLowerCase(),
        collected_at: normalizeText(row.collected_at),
        raw_data_type: normalizeText(row.raw_data_type),
        has_meta: row.has_meta === true,
        has_match_id: row.has_match_id === true,
        has_pageprops: row.has_pageprops === true,
    };
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

function buildExistingVersionDecision(rows = []) {
    const safeRows = Array.isArray(rows) ? rows : [];
    assertNoDuplicateVersions(safeRows);
    const availableVersions = summarizeExistingVersions(safeRows);
    const v1Rows = safeRows.filter(row => normalizeText(row.data_version) === 'fotmob_html_hyd_v1');
    const v2Rows = safeRows.filter(row => normalizeText(row.data_version) === CANDIDATE_VERSION);
    const v1Exists = v1Rows.length === 1;
    const v2Exists = v2Rows.length === 1;
    const summary = {
        fotmob_html_hyd_v1_exists: v1Exists,
        fotmob_pageprops_v2_exists: v2Exists,
        available_versions: availableVersions,
        existing_v1_row_id: v1Exists ? normalizeRowId(v1Rows[0]) : null,
        existing_v2_row_id: v2Exists ? normalizeRowId(v2Rows[0]) : null,
        target_version_exists: v2Exists,
    };
    if (!v1Exists) {
        return {
            ok_to_insert: false,
            existing_versions: summary,
            reason: 'required fotmob_html_hyd_v1 row missing',
        };
    }
    if (v2Exists) {
        return {
            ok_to_insert: false,
            existing_versions: {
                ...summary,
                existing_v2_data_hash: normalizeText(v2Rows[0].data_hash).toLowerCase(),
            },
            reason: 'fotmob_pageprops_v2 row already exists; this phase only inserts a missing v2 row',
        };
    }
    return {
        ok_to_insert: true,
        existing_versions: summary,
        reason: 'v1 exists and v2 is absent',
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

function validateSchemaConstraints(rows = []) {
    const constraintRows = Array.isArray(rows) ? rows : [];
    const byName = new Map(constraintRows.map(row => [normalizeText(row.conname), normalizeText(row.definition)]));
    const errors = [];
    const versionedUnique = byName.get('raw_match_data_match_id_data_version_key');
    if (!versionedUnique || !/UNIQUE\s*\(\s*match_id\s*,\s*data_version\s*\)/i.test(versionedUnique)) {
        errors.push('raw_match_data_match_id_data_version_key UNIQUE(match_id,data_version) missing');
    }
    if (byName.has('raw_match_data_match_id_key')) {
        errors.push('legacy raw_match_data_match_id_key must be absent');
    }
    if (!byName.has('raw_data_has_match_id')) {
        errors.push('raw_data_has_match_id check missing');
    }
    if (!byName.has('raw_data_not_empty')) {
        errors.push('raw_data_not_empty check missing');
    }
    return errors;
}

function buildPagePropsV2RawData({ input = {}, pageProps = {}, fetchResult = {}, generatedAt = null } = {}) {
    const safePageProps = jsonClone(pageProps) || {};
    const stableHash = computeStablePagePropsHash(safePageProps);
    return {
        _meta: {
            source: SOURCE,
            route: ROUTE,
            data_version: CANDIDATE_VERSION,
            hash_strategy: HASH_STRATEGY,
            match_id: input.matchId || TARGET.matchId,
            external_id: input.externalId || TARGET.externalId,
            request_url: fetchResult.request_url || buildFotMobMatchUrl(input.externalId || TARGET.externalId),
            final_url:
                fetchResult.final_url ||
                fetchResult.request_url ||
                buildFotMobMatchUrl(input.externalId || TARGET.externalId),
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
        matchId: Number(input.externalId || TARGET.externalId),
        pageProps: safePageProps,
    };
}

function validateRawDataShape(rawData = {}) {
    const errors = [];
    if (!isPlainObject(rawData)) errors.push('raw_data must be object');
    if (!isPlainObject(rawData._meta)) errors.push('raw_data._meta missing');
    if (!Object.prototype.hasOwnProperty.call(rawData, 'matchId')) errors.push('raw_data top-level matchId missing');
    if (!isPlainObject(rawData.pageProps)) errors.push('raw_data.pageProps missing');
    return errors;
}

function buildInsertRawMatchDataSql({ input, rawData, collectedAt, dataHash }) {
    return {
        text: `
            INSERT INTO raw_match_data (
                match_id,
                external_id,
                raw_data,
                collected_at,
                data_version,
                data_hash
            )
            VALUES ($1, $2, $3::jsonb, $4::timestamptz, $5, $6)
            ON CONFLICT (match_id, data_version) DO NOTHING
            RETURNING id, match_id, external_id, data_version, data_hash, collected_at
        `,
        values: [input.matchId, input.externalId, JSON.stringify(rawData), collectedAt, CANDIDATE_VERSION, dataHash],
    };
}

function nowUtcIso(dependencies = {}) {
    if (typeof dependencies.now === 'function') return dependencies.now();
    if (dependencies.now) return dependencies.now;
    return new Date().toISOString();
}

function buildControlledFailure(input = {}, requestUrl, reason, context = {}) {
    return {
        phase: PHASE,
        ok: false,
        controlled_failure: true,
        source: SOURCE,
        route: ROUTE,
        match_id: input.matchId || TARGET.matchId,
        external_id: input.externalId || TARGET.externalId,
        home_team: input.homeTeam || TARGET.homeTeam,
        away_team: input.awayTeam || TARGET.awayTeam,
        candidate_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        baseline_pageprops_hash: input.baselinePagepropsHash || BASELINE_PAGEPROPS_HASH,
        recaptured_pageprops_hash: context.recaptured_pageprops_hash || null,
        hash_matches_baseline:
            context.hash_matches_baseline === undefined ? null : context.hash_matches_baseline === true,
        request_url: requestUrl || buildFotMobMatchUrl(input.externalId || TARGET.externalId),
        final_url: context.final_url || null,
        http_status: context.http_status || null,
        content_type: context.content_type || null,
        body_byte_length: Number(context.body_byte_length || 0),
        body_sha256: context.body_sha256 || null,
        next_data_parse_ok: context.next_data_parse_ok === true,
        page_props_found: context.page_props_found === true,
        inserted_count: 0,
        updated_count: 0,
        skipped_count: 0,
        transaction: {
            began: context.transaction?.began === true,
            committed: context.transaction?.committed === true,
            rolled_back: context.transaction?.rolled_back === true,
        },
        failure_reason: reason,
        row_counts_before: context.row_counts_before || null,
        row_counts_after: context.row_counts_after || null,
        existing_versions_before: context.existing_versions_before || [],
        existing_versions_after: context.existing_versions_after || [],
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

function buildSuccessPayload({
    input,
    matchMetadata,
    fetchResult,
    pageProps,
    rawData,
    rowCountsBefore,
    rowCountsAfter,
    existingRowsBefore,
    versionRowsAfter,
    insertedRow,
    transaction,
    collectedAt,
    recapturedHash,
} = {}) {
    const v2Paths = listJsonPaths(pageProps);
    const v2ContentPaths = listJsonPaths(isPlainObject(pageProps.content) ? pageProps.content : {});
    const v2Row = versionRowsAfter.find(row => normalizeText(row.data_version) === CANDIDATE_VERSION) || {};
    const v1Row = versionRowsAfter.find(row => normalizeText(row.data_version) === 'fotmob_html_hyd_v1') || {};
    const lookupSpec = buildVersionAwareLookupSpec();
    return {
        phase: PHASE,
        ok: true,
        source: SOURCE,
        route: ROUTE,
        match_id: input.matchId,
        external_id: input.externalId,
        home_team: input.homeTeam,
        away_team: input.awayTeam,
        match_metadata: normalizeMatchMetadata(matchMetadata),
        candidate_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        baseline_pageprops_hash: input.baselinePagepropsHash,
        recaptured_pageprops_hash: recapturedHash,
        hash_matches_baseline: recapturedHash === input.baselinePagepropsHash,
        request_url: fetchResult.request_url || buildFotMobMatchUrl(input.externalId),
        final_url: fetchResult.final_url || fetchResult.request_url || buildFotMobMatchUrl(input.externalId),
        http_status: fetchResult.http_status,
        content_type: fetchResult.content_type,
        body_byte_length: Number(fetchResult.body_byte_length || 0),
        body_sha256: fetchResult.body_sha256 || null,
        next_data_parse_ok: true,
        page_props_found: true,
        candidate_summary: {
            raw_data_shape: Object.keys(rawData).sort(),
            candidate_json_byte_length: jsonByteLength(rawData),
            pageProps_path_count: v2Paths.length,
            pageProps_content_path_count: v2ContentPaths.length,
            pageProps_shape_summary: summarizeJsonShape(pageProps),
            raw_data_shape_summary: summarizeJsonShape(rawData),
        },
        existing_versions_before: summarizeExistingVersions(existingRowsBefore),
        existing_versions_after: summarizeExistingVersions(versionRowsAfter),
        inserted_count: 1,
        updated_count: 0,
        skipped_count: 0,
        transaction: {
            began: transaction.began === true,
            committed: transaction.committed === true,
            rolled_back: transaction.rolled_back === true,
        },
        row_counts_before: rowCountsBefore,
        row_counts_after: rowCountsAfter,
        insert_conflict_target: lookupSpec.conflict_target,
        insert_conflict_target_sql: lookupSpec.conflict_target_sql,
        inserted_row_metadata: {
            id: insertedRow?.id ?? v2Row.id ?? null,
            match_id: insertedRow?.match_id ?? input.matchId,
            external_id: insertedRow?.external_id ?? input.externalId,
            data_version: insertedRow?.data_version ?? CANDIDATE_VERSION,
            data_hash: insertedRow?.data_hash ?? recapturedHash,
            collected_at: insertedRow?.collected_at ?? collectedAt,
        },
        v1_row_verification: {
            id: v1Row.id ?? null,
            data_version: v1Row.data_version || 'fotmob_html_hyd_v1',
            retained: true,
        },
        v2_row_verification: {
            id: v2Row.id ?? null,
            data_version: v2Row.data_version || CANDIDATE_VERSION,
            data_hash: v2Row.data_hash || recapturedHash,
            has_meta: v2Row.has_meta === true,
            has_matchId: v2Row.has_match_id === true,
            has_pageProps: v2Row.has_pageprops === true,
        },
        raw_match_data_write_executed: true,
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

async function querySelectOnly(client, sql, params = []) {
    const normalized = normalizeText(sql).replace(/\s+/g, ' ').toLowerCase();
    if (!normalized.startsWith('select ')) throw new Error('NON_SELECT_SQL_BLOCKED');
    if (/\b(insert|update|delete|truncate|alter|drop|create|grant|revoke|copy|for update|lock)\b/i.test(normalized)) {
        throw new Error('SQL_WRITE_OR_LOCK_BLOCKED');
    }
    return client.query(sql, params);
}

async function loadSchemaConstraints(client) {
    const result = await querySelectOnly(
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

async function loadTargetMatchMetadata(client, input) {
    const result = await querySelectOnly(
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
    const result = await querySelectOnly(
        client,
        `
        SELECT id, match_id, external_id, data_version, data_hash, collected_at
        FROM raw_match_data
        WHERE match_id = $1 AND external_id = $2
        ORDER BY data_version, id
        `,
        [input.matchId, input.externalId]
    );
    return result.rows || [];
}

async function loadTargetRawVersionSummaries(client, input) {
    const result = await querySelectOnly(
        client,
        `
        SELECT
          id,
          match_id,
          external_id,
          data_version,
          data_hash,
          collected_at,
          jsonb_typeof(raw_data) AS raw_data_type,
          raw_data ? '_meta' AS has_meta,
          raw_data ? 'matchId' AS has_match_id,
          raw_data ? 'pageProps' AS has_pageprops
        FROM raw_match_data
        WHERE match_id = $1 AND external_id = $2
        ORDER BY data_version, id
        `,
        [input.matchId, input.externalId]
    );
    return (result.rows || []).map(normalizeRawRowSummary);
}

async function loadProtectedTableBaseline(client) {
    const result = await querySelectOnly(
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
    return buildProtectedTableBaseline(result.rows || []);
}

function createDefaultPool() {
    const { Pool } = require('pg');
    const { buildDbConnectionConfig } = require('./helpers/dbBlueprint');
    return new Pool(buildDbConnectionConfig());
}

async function acquireDbConnection(dependencies = {}) {
    if (dependencies.client) {
        return {
            client: dependencies.client,
            release: async () => {},
            cleanupPool: async () => {},
        };
    }
    const pool = dependencies.pool || (dependencies.createPool || createDefaultPool)();
    if (pool && typeof pool.connect === 'function') {
        const client = await pool.connect();
        return {
            client,
            release: async () => {
                if (typeof client.release === 'function') client.release();
            },
            cleanupPool: async () => {
                if (!dependencies.pool && typeof pool.end === 'function') await pool.end();
            },
        };
    }
    return {
        client: pool,
        release: async () => {},
        cleanupPool: async () => {
            if (!dependencies.pool && pool && typeof pool.end === 'function') await pool.end();
        },
    };
}

function buildPostWriteVerificationErrors({ beforeRows = [], afterRows = [], rowCountsAfter = {} } = {}) {
    const errors = [];
    const countErrors = validateExactRowCounts(rowCountsAfter, EXPECTED_ROW_COUNTS_AFTER);
    errors.push(...countErrors);
    let beforeDecision;
    let afterDecision;
    try {
        beforeDecision = buildExistingVersionDecision(beforeRows);
        afterDecision = {
            existing_versions: {
                available_versions: summarizeExistingVersions(afterRows),
                fotmob_html_hyd_v1_exists: afterRows.some(row => row.data_version === 'fotmob_html_hyd_v1'),
                fotmob_pageprops_v2_exists: afterRows.some(row => row.data_version === CANDIDATE_VERSION),
            },
        };
        assertNoDuplicateVersions(afterRows);
    } catch (error) {
        errors.push(error.message);
    }
    if (beforeDecision && !beforeDecision.existing_versions.fotmob_html_hyd_v1_exists) {
        errors.push('pre-write v1 row missing');
    }
    if (!afterDecision?.existing_versions?.fotmob_html_hyd_v1_exists) {
        errors.push('post-write v1 row missing');
    }
    if (!afterDecision?.existing_versions?.fotmob_pageprops_v2_exists) {
        errors.push('post-write v2 row missing');
    }

    const beforeV1 = beforeRows.find(row => normalizeText(row.data_version) === 'fotmob_html_hyd_v1');
    const afterV1 = afterRows.find(row => normalizeText(row.data_version) === 'fotmob_html_hyd_v1');
    const afterV2 = afterRows.find(row => normalizeText(row.data_version) === CANDIDATE_VERSION);
    if (beforeV1 && afterV1) {
        for (const key of ['id', 'match_id', 'external_id', 'data_version', 'data_hash', 'collected_at']) {
            if (normalizeText(beforeV1[key]) !== normalizeText(afterV1[key])) {
                errors.push(`v1 row changed field ${key}`);
            }
        }
    }
    if (afterV2) {
        if (normalizeText(afterV2.data_hash).toLowerCase() !== BASELINE_PAGEPROPS_HASH) {
            errors.push('v2 data_hash does not equal baseline');
        }
        if (afterV2.has_meta !== true) errors.push('v2 raw_data missing _meta');
        if (afterV2.has_match_id !== true) errors.push('v2 raw_data missing top-level matchId');
        if (afterV2.has_pageprops !== true) errors.push('v2 raw_data missing pageProps');
    }
    return errors;
}

async function executeControlledWrite(input = {}, dependencies = {}) {
    const validation = dependencies.skipValidation
        ? { ok: true, errors: [], value: normalizeWriteInput(input) }
        : validateWriteInput(input);
    const requestUrl = buildFotMobMatchUrl(input.externalId || TARGET.externalId);
    if (!validation.ok) {
        return buildControlledFailure(normalizeWriteInput(input), requestUrl, validation.errors.join('; '));
    }

    const value = validation.value;
    let connection = null;
    const transaction = {
        began: false,
        committed: false,
        rolled_back: false,
    };
    let rowCountsBefore = null;
    let rowCountsAfter = null;
    let existingRowsBefore = [];
    let fetchResult = null;
    let recapturedHash = null;
    try {
        connection = await acquireDbConnection(dependencies);
        const schemaRows = await loadSchemaConstraints(connection.client);
        const schemaErrors = validateSchemaConstraints(schemaRows);
        if (schemaErrors.length > 0) {
            return buildControlledFailure(value, requestUrl, `SCHEMA_CONSTRAINT_INVALID:${schemaErrors.join('; ')}`);
        }

        const matchMetadata = await loadTargetMatchMetadata(connection.client, value);
        const matchErrors = validateMatchMetadata(matchMetadata, value);
        if (matchErrors.length > 0) {
            return buildControlledFailure(value, requestUrl, `TARGET_MATCH_INVALID:${matchErrors.join('; ')}`);
        }

        existingRowsBefore = await loadExistingRawVersions(connection.client, value);
        const beforeDecision = buildExistingVersionDecision(existingRowsBefore);
        if (!beforeDecision.ok_to_insert) {
            return buildControlledFailure(value, requestUrl, `PRE_WRITE_VERSION_BLOCKED:${beforeDecision.reason}`, {
                existing_versions_before: beforeDecision.existing_versions.available_versions,
            });
        }

        rowCountsBefore = await loadProtectedTableBaseline(connection.client);
        const beforeCountErrors = validateExactRowCounts(rowCountsBefore, EXPECTED_ROW_COUNTS_BEFORE);
        if (beforeCountErrors.length > 0) {
            return buildControlledFailure(
                value,
                requestUrl,
                `PRE_WRITE_BASELINE_MISMATCH:${beforeCountErrors.join('; ')}`,
                {
                    row_counts_before: rowCountsBefore,
                    existing_versions_before: beforeDecision.existing_versions.available_versions,
                }
            );
        }

        fetchResult =
            dependencies.fetchResult ||
            (await fetchHtml(requestUrl, {
                fetchFn: dependencies.fetchFn,
            }));
        if (!fetchResult.ok) {
            return buildControlledFailure(value, requestUrl, fetchResult.error || 'LIVE_REQUEST_FAILED', {
                ...fetchResult,
                row_counts_before: rowCountsBefore,
                existing_versions_before: beforeDecision.existing_versions.available_versions,
            });
        }

        const extraction = extractNextDataJsonFromHtml(fetchResult.body);
        if (!extraction.ok) {
            return buildControlledFailure(value, requestUrl, extraction.error, {
                ...fetchResult,
                row_counts_before: rowCountsBefore,
                existing_versions_before: beforeDecision.existing_versions.available_versions,
            });
        }
        const pageProps = getPageProps(extraction.data);
        if (!pageProps) {
            return buildControlledFailure(value, requestUrl, 'PAGE_PROPS_NOT_FOUND', {
                ...fetchResult,
                next_data_parse_ok: true,
                row_counts_before: rowCountsBefore,
                existing_versions_before: beforeDecision.existing_versions.available_versions,
            });
        }

        const rawData = buildPagePropsV2RawData({
            input: value,
            pageProps,
            fetchResult,
            generatedAt: dependencies.generatedAt,
        });
        const rawDataErrors = validateRawDataShape(rawData);
        if (rawDataErrors.length > 0) {
            return buildControlledFailure(value, requestUrl, `INVALID_RAW_DATA_SHAPE:${rawDataErrors.join('; ')}`, {
                ...fetchResult,
                next_data_parse_ok: true,
                page_props_found: true,
                row_counts_before: rowCountsBefore,
                existing_versions_before: beforeDecision.existing_versions.available_versions,
            });
        }
        recapturedHash = dependencies.recapturedHashOverride || computeStablePagePropsHash(rawData);
        rawData._meta.data_hash = recapturedHash;
        if (recapturedHash !== value.baselinePagepropsHash) {
            return buildControlledFailure(
                value,
                requestUrl,
                `HASH_DRIFT: recaptured ${recapturedHash} differs from baseline ${value.baselinePagepropsHash}`,
                {
                    ...fetchResult,
                    next_data_parse_ok: true,
                    page_props_found: true,
                    recaptured_pageprops_hash: recapturedHash,
                    hash_matches_baseline: false,
                    row_counts_before: rowCountsBefore,
                    existing_versions_before: beforeDecision.existing_versions.available_versions,
                }
            );
        }

        await connection.client.query('BEGIN');
        transaction.began = true;

        const txRowsBefore = await loadExistingRawVersions(connection.client, value);
        const txDecision = buildExistingVersionDecision(txRowsBefore);
        if (!txDecision.ok_to_insert) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildControlledFailure(value, requestUrl, `TX_VERSION_BLOCKED:${txDecision.reason}`, {
                ...fetchResult,
                next_data_parse_ok: true,
                page_props_found: true,
                recaptured_pageprops_hash: recapturedHash,
                hash_matches_baseline: true,
                transaction,
                row_counts_before: rowCountsBefore,
                existing_versions_before: beforeDecision.existing_versions.available_versions,
            });
        }

        const collectedAt = nowUtcIso(dependencies);
        const insertSql = buildInsertRawMatchDataSql({
            input: value,
            rawData,
            collectedAt,
            dataHash: recapturedHash,
        });
        const insertResult = await connection.client.query(insertSql.text, insertSql.values);
        const insertedCount =
            typeof insertResult.rowCount === 'number' ? insertResult.rowCount : (insertResult.rows || []).length;
        if (insertedCount !== 1) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildControlledFailure(value, requestUrl, `INSERTED_COUNT_INVALID:${insertedCount}`, {
                ...fetchResult,
                next_data_parse_ok: true,
                page_props_found: true,
                recaptured_pageprops_hash: recapturedHash,
                hash_matches_baseline: true,
                transaction,
                row_counts_before: rowCountsBefore,
                existing_versions_before: beforeDecision.existing_versions.available_versions,
            });
        }

        rowCountsAfter = await loadProtectedTableBaseline(connection.client);
        const versionRowsAfter = await loadTargetRawVersionSummaries(connection.client, value);
        const verificationErrors = buildPostWriteVerificationErrors({
            beforeRows: existingRowsBefore,
            afterRows: versionRowsAfter,
            rowCountsAfter,
        });
        if (verificationErrors.length > 0) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildControlledFailure(
                value,
                requestUrl,
                `POST_WRITE_VERIFICATION_FAILED:${verificationErrors.join('; ')}`,
                {
                    ...fetchResult,
                    next_data_parse_ok: true,
                    page_props_found: true,
                    recaptured_pageprops_hash: recapturedHash,
                    hash_matches_baseline: true,
                    transaction,
                    row_counts_before: rowCountsBefore,
                    row_counts_after: rowCountsAfter,
                    existing_versions_before: beforeDecision.existing_versions.available_versions,
                    existing_versions_after: summarizeExistingVersions(versionRowsAfter),
                }
            );
        }

        await connection.client.query('COMMIT');
        transaction.committed = true;

        return buildSuccessPayload({
            input: value,
            matchMetadata,
            fetchResult,
            pageProps,
            rawData,
            rowCountsBefore,
            rowCountsAfter,
            existingRowsBefore,
            versionRowsAfter,
            insertedRow: (insertResult.rows || [])[0],
            transaction,
            collectedAt,
            recapturedHash,
        });
    } catch (error) {
        if (transaction.began && transaction.committed !== true && transaction.rolled_back !== true && connection) {
            try {
                await connection.client.query('ROLLBACK');
                transaction.rolled_back = true;
            } catch (rollbackError) {
                error.rollback_error = rollbackError.message;
            }
        }
        return buildControlledFailure(value || input, requestUrl, String(error.message || error), {
            ...(fetchResult || {}),
            transaction,
            row_counts_before: rowCountsBefore,
            row_counts_after: rowCountsAfter,
            recaptured_pageprops_hash: recapturedHash,
            hash_matches_baseline:
                recapturedHash && value?.baselinePagepropsHash ? recapturedHash === value.baselinePagepropsHash : null,
            existing_versions_before: summarizeExistingVersions(existingRowsBefore),
        });
    } finally {
        if (connection) {
            await connection.release();
            await connection.cleanupPool();
        }
    }
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsed = Array.isArray(argv) ? parseArgs(argv) : argv;
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));
    const payload = await executeControlledWrite(parsed, dependencies);
    output(payload);
    return { status: payload.ok ? 0 : 1, payload };
}

module.exports = {
    PHASE,
    TARGET,
    BASELINE_PAGEPROPS_HASH,
    parseArgs,
    normalizeBooleanFlag,
    validateWriteInput,
    buildExistingVersionDecision,
    buildPagePropsV2RawData,
    computeStablePagePropsHash,
    buildInsertRawMatchDataSql,
    buildProtectedTableBaseline,
    validateSchemaConstraints,
    validateRawDataShape,
    buildPostWriteVerificationErrors,
    querySelectOnly,
    loadSchemaConstraints,
    loadTargetMatchMetadata,
    loadExistingRawVersions,
    loadProtectedTableBaseline,
    loadTargetRawVersionSummaries,
    executeControlledWrite,
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
