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
    summarizeJsonShape,
} = require('./pageprops_v2_no_write_preview');
const { buildVersionAwareLookupSpec } = require('../../src/infrastructure/services/RawMatchDataVersionSelector');

const PHASE = 'PHASE5_21L2M_REMAINING_SEEDED_PAGEPROPS_V2_CONTROLLED_WRITE';
const SOURCE = 'fotmob';
const ROUTE = 'html_hydration';
const EXCLUDED_ALREADY_WRITTEN_TARGET = Object.freeze({
    matchId: '53_20252026_4830747',
    externalId: '4830747',
});
const EXPECTED_TARGETS = Object.freeze([
    {
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        baselineHash: '7953562593a2ab57ed59741667ccf2fa628adf22eff76fdc7a499f559b3ac440',
    },
    {
        matchId: '53_20252026_4830748',
        externalId: '4830748',
        baselineHash: 'fe664ebe76d4e0e9fda088d4d642fe98fe25c03b920f4f3d83531e6ea4c4ad04',
    },
    {
        matchId: '53_20252026_4830750',
        externalId: '4830750',
        baselineHash: 'e5cada280a0b8d351181defd5605ded7ced091e86be3039439559aed1247b762',
    },
    {
        matchId: '53_20252026_4830751',
        externalId: '4830751',
        baselineHash: 'de78dc67d69ffc22739e4cf648788fd6f50a6dfccae8518a9c1fa8def0eb16a5',
    },
    {
        matchId: '53_20252026_4830752',
        externalId: '4830752',
        baselineHash: '65564219fcb25c6369822a0082f43e96f59675f434208d45cb16ef6395f08c32',
    },
    {
        matchId: '53_20252026_4830753',
        externalId: '4830753',
        baselineHash: '4ab9fcb73465d00cc8bab7a6cb1a61b1b3370d466b15c2ace0092c8357ead413',
    },
    {
        matchId: '53_20252026_4830754',
        externalId: '4830754',
        baselineHash: '29be450e84a55fb56a8db4f1bf7a672adcd6c85e34a8cf06c98e99ac179532c6',
    },
]);
const EXPECTED_EXTERNAL_IDS = Object.freeze(EXPECTED_TARGETS.map(target => target.externalId));
const EXPECTED_MATCH_IDS = Object.freeze(EXPECTED_TARGETS.map(target => target.matchId));
const SEEDED_EIGHT_MATCH_IDS = Object.freeze([EXCLUDED_ALREADY_WRITTEN_TARGET.matchId, ...EXPECTED_MATCH_IDS].sort());
const BASELINE_HASHES = Object.freeze(
    Object.fromEntries(EXPECTED_TARGETS.map(target => [target.externalId, target.baselineHash]))
);
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
    'bulkUnbounded',
    'bulk',
    'execute',
    'commit',
    'include4830747',
    'rewriteExisting',
    'dropV1',
    'allowSchemaMigration',
    'alterTable',
    'partialWrite',
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
    raw_match_data: 11,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const EXPECTED_ROW_COUNTS_AFTER = Object.freeze({
    ...EXPECTED_ROW_COUNTS_BEFORE,
    raw_match_data: 18,
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
        baselineHashes: null,
        candidateVersion: null,
        hashStrategy: null,
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
        bulkUnbounded: false,
        bulk: false,
        execute: false,
        commit: false,
        include4830747: false,
        rewriteExisting: false,
        dropV1: false,
        allowSchemaMigration: false,
        alterTable: false,
        partialWrite: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        route: 'route',
        'baseline-hashes': 'baselineHashes',
        baseline_hashes: 'baselineHashes',
        'candidate-version': 'candidateVersion',
        candidate_version: 'candidateVersion',
        'hash-strategy': 'hashStrategy',
        hash_strategy: 'hashStrategy',
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
        'bulk-unbounded': 'bulkUnbounded',
        bulk_unbounded: 'bulkUnbounded',
        bulk: 'bulk',
        execute: 'execute',
        commit: 'commit',
        'include-4830747': 'include4830747',
        include_4830747: 'include4830747',
        'rewrite-existing': 'rewriteExisting',
        rewrite_existing: 'rewriteExisting',
        'drop-v1': 'dropV1',
        drop_v1: 'dropV1',
        'allow-schema-migration': 'allowSchemaMigration',
        allow_schema_migration: 'allowSchemaMigration',
        'alter-table': 'alterTable',
        alter_table: 'alterTable',
        'partial-write': 'partialWrite',
        partial_write: 'partialWrite',
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
        'bulkUnbounded',
        'bulk',
        'execute',
        'commit',
        'include4830747',
        'rewriteExisting',
        'dropV1',
        'allowSchemaMigration',
        'alterTable',
        'partialWrite',
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
        errors.push(`${flagName}=yes is required in Phase 5.21L2M`);
        return;
    }
    errors.push(`missing ${flagName}=yes`);
}

function pushRequiredNo(errors, value, flagName) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.21L2M`);
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

function parseBaselineHashes(rawValue) {
    const rawText = normalizeText(rawValue);
    const errors = [];
    if (!rawText) {
        return {
            ok: false,
            errors: ['missing baseline-hashes'],
            hashes: {},
        };
    }

    const keyOccurrences = {};
    const keyPattern = /"((?:[^"\\]|\\.)+)"\s*:/g;
    let match;
    while ((match = keyPattern.exec(rawText)) !== null) {
        const key = match[1].replace(/\\"/g, '"');
        keyOccurrences[key] = (keyOccurrences[key] || 0) + 1;
    }
    for (const [key, count] of Object.entries(keyOccurrences)) {
        if (count > 1) errors.push(`baseline-hashes contains duplicate target ${key}`);
    }

    let parsed;
    try {
        parsed = JSON.parse(rawText);
    } catch (error) {
        return {
            ok: false,
            errors: [`baseline-hashes must be valid JSON: ${error.message}`],
            hashes: {},
        };
    }
    if (!isPlainObject(parsed)) {
        errors.push('baseline-hashes must be a JSON object');
        parsed = {};
    }

    const hashes = Object.fromEntries(
        Object.entries(parsed).map(([key, value]) => [normalizeText(key), normalizeText(value)])
    );
    const keys = Object.keys(hashes).sort();
    if (keys.includes(EXCLUDED_ALREADY_WRITTEN_TARGET.externalId)) {
        errors.push('baseline-hashes must not contain 4830747');
    }
    for (const externalId of EXPECTED_EXTERNAL_IDS) {
        if (!Object.prototype.hasOwnProperty.call(hashes, externalId)) {
            errors.push(`baseline-hashes missing ${externalId}`);
            continue;
        }
        const hash = normalizeText(hashes[externalId]).toLowerCase();
        if (!/^[a-f0-9]{64}$/.test(hash)) {
            errors.push(`baseline-hashes ${externalId} must be a 64-char lowercase hex string`);
        } else if (hash !== BASELINE_HASHES[externalId]) {
            errors.push(`baseline-hashes ${externalId} must be ${BASELINE_HASHES[externalId]}`);
        }
        hashes[externalId] = hash;
    }
    for (const key of keys) {
        if (!EXPECTED_EXTERNAL_IDS.includes(key)) {
            errors.push(`baseline-hashes contains unexpected target ${key}`);
        }
    }
    if (keys.length !== EXPECTED_EXTERNAL_IDS.length) {
        errors.push(`baseline-hashes must contain exactly ${EXPECTED_EXTERNAL_IDS.length} targets`);
    }

    return {
        ok: errors.length === 0,
        errors,
        hashes,
    };
}

function normalizeWriteInput(input = {}) {
    const parsedBaselines = parseBaselineHashes(input.baselineHashes);
    return {
        source: normalizeText(input.source).toLowerCase(),
        route: normalizeText(input.route),
        baselineHashesRaw: normalizeText(input.baselineHashes),
        baselineHashes: parsedBaselines.hashes,
        baselineHashErrors: parsedBaselines.errors,
        candidateVersion: normalizeText(input.candidateVersion),
        hashStrategy: normalizeText(input.hashStrategy),
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
        bulkUnbounded: normalizeBooleanFlag(input.bulkUnbounded, false),
        bulk: normalizeBooleanFlag(input.bulk, false),
        execute: normalizeBooleanFlag(input.execute, false),
        commit: normalizeBooleanFlag(input.commit, false),
        include4830747: normalizeBooleanFlag(input.include4830747, false),
        rewriteExisting: normalizeBooleanFlag(input.rewriteExisting, false),
        dropV1: normalizeBooleanFlag(input.dropV1, false),
        allowSchemaMigration: normalizeBooleanFlag(input.allowSchemaMigration, false),
        alterTable: normalizeBooleanFlag(input.alterTable, false),
        partialWrite: normalizeBooleanFlag(input.partialWrite, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validateWriteInput(input = {}) {
    const value = normalizeWriteInput(input);
    const errors = [];
    if (value.unknown.length > 0) errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    requireExact(errors, value.source, SOURCE, 'source');
    requireExact(errors, value.route, ROUTE, 'route');
    errors.push(...value.baselineHashErrors);
    requireExact(errors, value.candidateVersion, CANDIDATE_VERSION, 'candidate-version');
    requireExact(errors, value.hashStrategy, HASH_STRATEGY, 'hash-strategy');
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

function validateSchemaConstraints(rows = []) {
    const constraintRows = Array.isArray(rows) ? rows : [];
    const byName = new Map(constraintRows.map(row => [normalizeText(row.conname), normalizeText(row.definition)]));
    const errors = [];
    const versionedUnique = byName.get('raw_match_data_match_id_data_version_key');
    const anyVersionedUnique = constraintRows.some(row =>
        /UNIQUE\s*\(\s*match_id\s*,\s*data_version\s*\)/i.test(normalizeText(row.definition))
    );
    if (!versionedUnique && !anyVersionedUnique) {
        errors.push('raw_match_data_match_id_data_version_key UNIQUE(match_id,data_version) missing');
    }
    if (versionedUnique && !/UNIQUE\s*\(\s*match_id\s*,\s*data_version\s*\)/i.test(versionedUnique)) {
        errors.push('raw_match_data_match_id_data_version_key must be UNIQUE(match_id,data_version)');
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
    const availableVersions = summarizeExistingVersions(safeRows);
    const v1Rows = safeRows.filter(row => normalizeText(row.data_version) === 'fotmob_html_hyd_v1');
    const v2Rows = safeRows.filter(row => normalizeText(row.data_version) === CANDIDATE_VERSION);
    const v1Exists = v1Rows.length === 1;
    const v2Exists = v2Rows.length === 1;
    const summary = {
        available_versions: availableVersions,
        fotmob_html_hyd_v1_exists: v1Exists,
        fotmob_pageprops_v2_exists: v2Exists,
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
            reason: 'fotmob_pageprops_v2 row already exists for remaining target',
        };
    }
    return {
        ok_to_insert: true,
        existing_versions: summary,
        reason: 'v1 exists and v2 is absent',
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
    if (byExternalId.has(EXCLUDED_ALREADY_WRITTEN_TARGET.externalId)) {
        throw new Error('TARGET_METADATA_INCLUDES_4830747');
    }
    return EXPECTED_TARGETS.map(expected => byExternalId.get(expected.externalId));
}

function buildTargetContexts({ metadataRows = [], existingRows = [] } = {}) {
    const metadata = validateTargetMetadataRows(metadataRows);
    const groupedExistingRows = groupRowsByMatchId(existingRows);
    return metadata.map(row => {
        const rows = groupedExistingRows.get(row.match_id) || [];
        const versionDecision = buildExistingVersionDecision(rows);
        return {
            ...row,
            baseline_hash: BASELINE_HASHES[row.external_id],
            existingRows: rows,
            versionDecision,
        };
    });
}

function summarizeTargetInventory(targetContexts = []) {
    return targetContexts.map(target => ({
        match_id: target.match_id,
        external_id: target.external_id,
        home_team: target.home_team,
        away_team: target.away_team,
        match_date: target.match_date,
        status: target.status,
        baseline_hash: target.baseline_hash,
        existing_versions: target.versionDecision.existing_versions.available_versions,
        target_version_exists: target.versionDecision.existing_versions.target_version_exists,
        decision: target.versionDecision.ok_to_insert ? 'would_insert' : 'blocked',
        reason: target.versionDecision.reason,
    }));
}

function validateTargetInventory(targetContexts = []) {
    const errors = [];
    for (const target of targetContexts) {
        if (!target.versionDecision.ok_to_insert) {
            errors.push(`${target.external_id}:${target.versionDecision.reason}`);
        }
    }
    return errors;
}

function buildPagePropsV2RawData({
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

function validateRawDataShape(rawData = {}) {
    const errors = [];
    if (!isPlainObject(rawData)) errors.push('raw_data must be object');
    if (!isPlainObject(rawData._meta)) errors.push('raw_data._meta missing');
    if (!Object.prototype.hasOwnProperty.call(rawData, 'matchId')) errors.push('raw_data top-level matchId missing');
    if (!isPlainObject(rawData.pageProps)) errors.push('raw_data.pageProps missing');
    return errors;
}

function buildTargetFailure(target = {}, requestUrl, reason, context = {}) {
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
        next_data_parse_ok: context.next_data_parse_ok === true,
        page_props_found: context.page_props_found === true,
        baseline_hash: target.baseline_hash || BASELINE_HASHES[target.external_id],
        recaptured_hash: context.recaptured_hash || null,
        hash_matches_baseline: context.hash_matches_baseline === true,
        existing_versions: target.versionDecision?.existing_versions?.available_versions || [],
        decision: 'blocked',
        failure_reason: reason,
    };
}

function buildRecapturedTarget({
    input = {},
    target = {},
    fetchResult = {},
    generatedAt = null,
    recapturedHashOverride = undefined,
} = {}) {
    const requestUrl = buildFotMobMatchUrl(target.external_id);
    if (!fetchResult.ok) {
        return buildTargetFailure(target, requestUrl, fetchResult.error || 'LIVE_REQUEST_FAILED', fetchResult);
    }
    const extraction = extractNextDataJsonFromHtml(fetchResult.body);
    if (!extraction.ok) {
        return buildTargetFailure(target, requestUrl, extraction.error, fetchResult);
    }
    const pageProps = getPageProps(extraction.data);
    if (!pageProps) {
        return buildTargetFailure(target, requestUrl, 'PAGE_PROPS_NOT_FOUND', {
            ...fetchResult,
            next_data_parse_ok: true,
        });
    }
    const rawData = buildPagePropsV2RawData({
        input,
        target,
        pageProps,
        fetchResult,
        generatedAt,
    });
    const rawDataErrors = validateRawDataShape(rawData);
    if (rawDataErrors.length > 0) {
        return buildTargetFailure(target, requestUrl, `INVALID_RAW_DATA_SHAPE:${rawDataErrors.join('; ')}`, {
            ...fetchResult,
            next_data_parse_ok: true,
            page_props_found: true,
        });
    }
    const recapturedHash =
        recapturedHashOverride === undefined
            ? computeStablePagePropsHash(rawData)
            : normalizeText(recapturedHashOverride);
    rawData._meta.data_hash = recapturedHash;
    const pagePropsPaths = listJsonPaths(pageProps);
    const pagePropsContentPaths = listJsonPaths(isPlainObject(pageProps.content) ? pageProps.content : {});
    const hashMatchesBaseline = recapturedHash === target.baseline_hash;
    const safeSummary = {
        ok: hashMatchesBaseline,
        controlled_failure: !hashMatchesBaseline,
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
        baseline_hash: target.baseline_hash,
        recaptured_hash: recapturedHash,
        hash_matches_baseline: hashMatchesBaseline,
        candidate_json_byte_length: jsonByteLength(rawData),
        pageProps_top_level_keys: Object.keys(pageProps).sort(),
        pageProps_path_count: pagePropsPaths.length,
        pageProps_content_path_count: pagePropsContentPaths.length,
        pageProps_shape_summary: summarizeJsonShape(pageProps),
        candidate_shape_summary: summarizeJsonShape(rawData),
        existing_versions: target.versionDecision.existing_versions.available_versions,
        decision: hashMatchesBaseline ? 'insert_allowed' : 'blocked',
        failure_reason: hashMatchesBaseline
            ? null
            : `HASH_DRIFT: recaptured ${recapturedHash} differs from baseline ${target.baseline_hash}`,
        rawData,
        pageProps,
    };
    return safeSummary;
}

function publicTargetSummary(summary = {}) {
    const {
        rawData: _rawData,
        pageProps: _pageProps,
        candidate_shape_summary: _candidateShapeSummary,
        pageProps_shape_summary: _pagePropsShapeSummary,
        ...publicFields
    } = summary;
    return publicFields;
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

function nowUtcIso(dependencies = {}) {
    if (typeof dependencies.now === 'function') return dependencies.now();
    if (dependencies.now) return dependencies.now;
    return new Date().toISOString();
}

function buildInsertRawMatchDataSql({ recapturedTargets = [], collectedAt } = {}) {
    const values = [];
    const placeholders = [];
    recapturedTargets.forEach((target, index) => {
        const base = index * 6;
        placeholders.push(
            `($${base + 1}, $${base + 2}, $${base + 3}::jsonb, $${base + 4}::timestamptz, $${base + 5}, $${base + 6})`
        );
        values.push(
            target.match_id,
            target.external_id,
            JSON.stringify(target.rawData),
            collectedAt,
            CANDIDATE_VERSION,
            target.recaptured_hash
        );
    });
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
            VALUES ${placeholders.join(',\n')}
            ON CONFLICT (match_id, data_version) DO NOTHING
            RETURNING id, match_id, external_id, data_version, data_hash, collected_at
        `,
        values,
    };
}

function buildFailurePayload({
    input = {},
    reason,
    protectedTableBaseline = null,
    schemaErrors = [],
    targetInventory = [],
    targets = [],
    rowCountsAfter = null,
    transaction = {},
    insertedCount = 0,
} = {}) {
    const lookupSpec = buildVersionAwareLookupSpec();
    const publicTargets = targets.map(publicTargetSummary);
    const validPayloadCount = publicTargets.filter(
        target => target.next_data_parse_ok && target.page_props_found
    ).length;
    const hashMatchCount = publicTargets.filter(target => target.hash_matches_baseline === true).length;
    return {
        phase: PHASE,
        ok: false,
        controlled_failure: true,
        source: SOURCE,
        route: ROUTE,
        candidate_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        attempted_target_count: EXPECTED_TARGETS.length,
        processed_target_count: publicTargets.length,
        valid_payload_count: validPayloadCount,
        failed_target_count: Math.max(0, EXPECTED_TARGETS.length - validPayloadCount),
        hash_match_count: hashMatchCount,
        hash_drift_count: publicTargets.filter(target => target.recaptured_hash && !target.hash_matches_baseline)
            .length,
        inserted_count: insertedCount,
        updated_count: 0,
        skipped_count: 0,
        target_external_ids: EXPECTED_EXTERNAL_IDS,
        baseline_hashes: input.baselineHashes || BASELINE_HASHES,
        target_inventory: targetInventory,
        targets: publicTargets,
        protected_table_baseline: protectedTableBaseline,
        row_counts_after: rowCountsAfter,
        schema_errors: schemaErrors,
        failure_reason: reason,
        insert_conflict_target: lookupSpec.conflict_target,
        insert_conflict_target_sql: lookupSpec.conflict_target_sql,
        transaction: {
            began: transaction.began === true,
            committed: transaction.committed === true,
            rolled_back: transaction.rolled_back === true,
        },
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
    input = {},
    targetInventory = [],
    recapturedTargets = [],
    insertedRows = [],
    rowCountsBefore = {},
    rowCountsAfter = {},
    postWriteRows = [],
    excludedBeforeRows = [],
    excludedAfterRows = [],
    duplicateRowsAfter = [],
    transaction = {},
} = {}) {
    const lookupSpec = buildVersionAwareLookupSpec();
    const insertedByExternalId = new Map((insertedRows || []).map(row => [normalizeText(row.external_id), row]));
    const postRowsByMatchId = groupRowsByMatchId(postWriteRows);
    const publicTargets = recapturedTargets.map(target => {
        const insertedRow = insertedByExternalId.get(target.external_id) || {};
        const rowsAfter = postRowsByMatchId.get(target.match_id) || [];
        const v2Row = rowsAfter.find(row => normalizeText(row.data_version) === CANDIDATE_VERSION) || {};
        return {
            ...publicTargetSummary(target),
            inserted_row_id: insertedRow.id ?? v2Row.id ?? null,
            data_version: CANDIDATE_VERSION,
            data_hash: insertedRow.data_hash ?? v2Row.data_hash ?? target.recaptured_hash,
            inserted_row_metadata: {
                id: insertedRow.id ?? v2Row.id ?? null,
                match_id: insertedRow.match_id ?? target.match_id,
                external_id: insertedRow.external_id ?? target.external_id,
                data_version: insertedRow.data_version ?? CANDIDATE_VERSION,
                data_hash: insertedRow.data_hash ?? target.recaptured_hash,
                collected_at: insertedRow.collected_at ?? v2Row.collected_at ?? null,
            },
            raw_data_shape_verification: {
                has_meta: v2Row.has_meta === true,
                has_matchId: v2Row.has_match_id === true,
                has_pageProps: v2Row.has_pageprops === true,
            },
        };
    });
    return {
        phase: PHASE,
        ok: true,
        source: SOURCE,
        route: ROUTE,
        candidate_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        attempted_target_count: EXPECTED_TARGETS.length,
        processed_target_count: publicTargets.length,
        valid_payload_count: publicTargets.length,
        failed_target_count: 0,
        hash_match_count: publicTargets.filter(target => target.hash_matches_baseline === true).length,
        hash_drift_count: 0,
        inserted_count: insertedRows.length,
        updated_count: 0,
        skipped_count: 0,
        target_external_ids: EXPECTED_EXTERNAL_IDS,
        baseline_hashes: input.baselineHashes || BASELINE_HASHES,
        target_inventory: targetInventory,
        targets: publicTargets,
        row_counts_before: rowCountsBefore,
        row_counts_after: rowCountsAfter,
        insert_conflict_target: lookupSpec.conflict_target,
        insert_conflict_target_sql: lookupSpec.conflict_target_sql,
        transaction: {
            began: transaction.began === true,
            committed: transaction.committed === true,
            rolled_back: transaction.rolled_back === true,
        },
        post_write_verification: {
            raw_match_data_before: rowCountsBefore.raw_match_data,
            raw_match_data_after: rowCountsAfter.raw_match_data,
            all_remaining_targets_have_v1_v2: publicTargets.every(target =>
                ['fotmob_html_hyd_v1', CANDIDATE_VERSION].every(version =>
                    (postRowsByMatchId.get(target.match_id) || []).some(row => row.data_version === version)
                )
            ),
            all_v2_hashes_match_baseline: publicTargets.every(
                target => target.data_hash === BASELINE_HASHES[target.external_id]
            ),
            excluded_4830747_unchanged: rawRowSummariesEqual(excludedBeforeRows, excludedAfterRows),
            duplicate_match_id_data_version_count: duplicateRowsAfter.length,
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

function rawRowSummariesEqual(leftRows = [], rightRows = []) {
    const normalize = rows =>
        (Array.isArray(rows) ? rows : [])
            .map(normalizeRawRowSummary)
            .sort((left, right) =>
                `${left.match_id}:${left.data_version}`.localeCompare(`${right.match_id}:${right.data_version}`)
            );
    return JSON.stringify(normalize(leftRows)) === JSON.stringify(normalize(rightRows));
}

function buildExcludedTargetVerificationErrors(rows = [], label = 'excluded 4830747') {
    const errors = [];
    let safeRows = [];
    try {
        safeRows = Array.isArray(rows) ? rows : [];
        assertNoDuplicateVersions(safeRows);
    } catch (error) {
        errors.push(`${label}:${error.message}`);
    }
    const versions = summarizeExistingVersions(safeRows);
    if (!versions.includes('fotmob_html_hyd_v1')) errors.push(`${label}:fotmob_html_hyd_v1 missing`);
    if (!versions.includes(CANDIDATE_VERSION)) errors.push(`${label}:fotmob_pageprops_v2 missing`);
    return errors;
}

function buildPostWriteVerificationErrors({
    rowCountsAfter = {},
    beforeTargetRows = [],
    afterTargetRows = [],
    excludedBeforeRows = [],
    excludedAfterRows = [],
    duplicateRowsAfter = [],
} = {}) {
    const errors = [];
    errors.push(...validateExactRowCounts(rowCountsAfter, EXPECTED_ROW_COUNTS_AFTER));
    if (duplicateRowsAfter.length > 0) {
        errors.push(`duplicate match_id,data_version rows: ${duplicateRowsAfter.length}`);
    }
    if (!rawRowSummariesEqual(excludedBeforeRows, excludedAfterRows)) errors.push('4830747 rows changed');
    errors.push(...buildExcludedTargetVerificationErrors(excludedAfterRows));

    const beforeGrouped = groupRowsByMatchId(beforeTargetRows);
    const afterGrouped = groupRowsByMatchId(afterTargetRows);
    for (const expected of EXPECTED_TARGETS) {
        const beforeRows = beforeGrouped.get(expected.matchId) || [];
        const afterRows = afterGrouped.get(expected.matchId) || [];
        const beforeVersions = summarizeExistingVersions(beforeRows);
        const afterVersions = summarizeExistingVersions(afterRows);
        if (!beforeVersions.includes('fotmob_html_hyd_v1')) errors.push(`${expected.externalId}:pre-write v1 missing`);
        if (!afterVersions.includes('fotmob_html_hyd_v1')) errors.push(`${expected.externalId}:post-write v1 missing`);
        if (!afterVersions.includes(CANDIDATE_VERSION)) errors.push(`${expected.externalId}:post-write v2 missing`);
        const beforeV1 = beforeRows.find(row => row.data_version === 'fotmob_html_hyd_v1');
        const afterV1 = afterRows.find(row => row.data_version === 'fotmob_html_hyd_v1');
        if (beforeV1 && afterV1) {
            for (const key of ['id', 'match_id', 'external_id', 'data_version', 'data_hash', 'collected_at']) {
                if (normalizeText(beforeV1[key]) !== normalizeText(afterV1[key])) {
                    errors.push(`${expected.externalId}:v1 row changed field ${key}`);
                }
            }
        }
        const afterV2 = afterRows.find(row => row.data_version === CANDIDATE_VERSION);
        if (afterV2) {
            if (normalizeText(afterV2.data_hash).toLowerCase() !== expected.baselineHash) {
                errors.push(`${expected.externalId}:v2 data_hash does not equal baseline`);
            }
            if (afterV2.has_meta !== true) errors.push(`${expected.externalId}:v2 raw_data missing _meta`);
            if (afterV2.has_match_id !== true) {
                errors.push(`${expected.externalId}:v2 raw_data missing top-level matchId`);
            }
            if (afterV2.has_pageprops !== true) errors.push(`${expected.externalId}:v2 raw_data missing pageProps`);
        }
    }
    return errors;
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

async function loadTargetMatchMetadata(client) {
    const result = await querySelectOnly(
        client,
        `
        SELECT match_id, external_id, home_team, away_team, match_date, status
        FROM matches
        WHERE external_id = ANY($1::text[])
        ORDER BY external_id
        `,
        [EXPECTED_EXTERNAL_IDS]
    );
    return result.rows || [];
}

async function loadExistingRawVersions(client, matchIds = EXPECTED_MATCH_IDS) {
    const result = await querySelectOnly(
        client,
        `
        SELECT id, match_id, external_id, data_version, data_hash, collected_at
        FROM raw_match_data
        WHERE match_id = ANY($1::text[])
        ORDER BY match_id, data_version, id
        `,
        [matchIds]
    );
    return result.rows || [];
}

async function loadRawVersionSummaries(client, matchIds = EXPECTED_MATCH_IDS) {
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
        WHERE match_id = ANY($1::text[])
        ORDER BY match_id, data_version, id
        `,
        [matchIds]
    );
    return (result.rows || []).map(normalizeRawRowSummary);
}

async function loadDuplicateMatchVersionRows(client) {
    const result = await querySelectOnly(
        client,
        `
        SELECT match_id, data_version, COUNT(*)::int AS rows
        FROM raw_match_data
        GROUP BY match_id, data_version
        HAVING COUNT(*) > 1
        ORDER BY match_id, data_version
        `,
        []
    );
    return result.rows || [];
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

async function recaptureAllTargets({ input = {}, targetContexts = [], dependencies = {}, generatedAt = null } = {}) {
    const recapturedTargets = [];
    for (let index = 0; index < targetContexts.length; index += 1) {
        const target = targetContexts[index];
        const fetchResult = await resolveFetchResultForTarget(target, index, dependencies);
        const overrideMap = dependencies.recapturedHashesByExternalId || {};
        const recapturedHashOverride =
            typeof dependencies.recapturedHashForTarget === 'function'
                ? dependencies.recapturedHashForTarget(target, index)
                : overrideMap[target.external_id];
        const recaptured = buildRecapturedTarget({
            input,
            target,
            fetchResult,
            generatedAt,
            recapturedHashOverride,
        });
        recapturedTargets.push(recaptured);
        if (!recaptured.ok) {
            return {
                ok: false,
                recapturedTargets,
                failureReason: `${target.external_id}:${recaptured.failure_reason}`,
            };
        }
    }
    return {
        ok: true,
        recapturedTargets,
        failureReason: null,
    };
}

async function executeControlledWrite(input = {}, dependencies = {}) {
    const validation = dependencies.skipValidation
        ? { ok: true, errors: [], value: normalizeWriteInput(input) }
        : validateWriteInput(input);
    if (!validation.ok) {
        return buildFailurePayload({
            input: normalizeWriteInput(input),
            reason: `INPUT_INVALID:${validation.errors.join(';')}`,
        });
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
    let targetContexts = [];
    let targetInventory = [];
    let existingRowsBefore = [];
    let excludedBeforeRows = [];
    let recapturedTargets = [];
    let insertedCount = 0;
    try {
        connection = await acquireDbConnection(dependencies);
        const schemaRows = await loadSchemaConstraints(connection.client);
        const schemaErrors = validateSchemaConstraints(schemaRows);
        if (schemaErrors.length > 0) {
            return buildFailurePayload({
                input: value,
                reason: `SCHEMA_CONSTRAINT_INVALID:${schemaErrors.join('; ')}`,
                schemaErrors,
            });
        }

        const duplicateRowsBefore = await loadDuplicateMatchVersionRows(connection.client);
        if (duplicateRowsBefore.length > 0) {
            return buildFailurePayload({
                input: value,
                reason: `DUPLICATE_MATCH_ID_DATA_VERSION:${duplicateRowsBefore.length}`,
            });
        }

        rowCountsBefore = await loadProtectedTableBaseline(connection.client);
        const beforeCountErrors = validateExactRowCounts(rowCountsBefore, EXPECTED_ROW_COUNTS_BEFORE);
        if (beforeCountErrors.length > 0) {
            return buildFailurePayload({
                input: value,
                reason: `PRE_WRITE_BASELINE_MISMATCH:${beforeCountErrors.join('; ')}`,
                protectedTableBaseline: rowCountsBefore,
            });
        }

        const metadataRows = await loadTargetMatchMetadata(connection.client);
        existingRowsBefore = await loadExistingRawVersions(connection.client, EXPECTED_MATCH_IDS);
        excludedBeforeRows = await loadRawVersionSummaries(connection.client, [
            EXCLUDED_ALREADY_WRITTEN_TARGET.matchId,
        ]);
        const excludedErrors = buildExcludedTargetVerificationErrors(excludedBeforeRows);
        if (excludedErrors.length > 0) {
            return buildFailurePayload({
                input: value,
                reason: `EXCLUDED_4830747_INVALID:${excludedErrors.join('; ')}`,
                protectedTableBaseline: rowCountsBefore,
            });
        }
        try {
            targetContexts = buildTargetContexts({
                metadataRows,
                existingRows: existingRowsBefore,
            });
            targetInventory = summarizeTargetInventory(targetContexts);
        } catch (error) {
            return buildFailurePayload({
                input: value,
                reason: error.message,
                protectedTableBaseline: rowCountsBefore,
            });
        }
        const inventoryErrors = validateTargetInventory(targetContexts);
        if (inventoryErrors.length > 0) {
            return buildFailurePayload({
                input: value,
                reason: `PRE_WRITE_VERSION_BLOCKED:${inventoryErrors.join('; ')}`,
                protectedTableBaseline: rowCountsBefore,
                targetInventory,
            });
        }

        const recapture = await recaptureAllTargets({
            input: value,
            targetContexts,
            dependencies,
            generatedAt: dependencies.generatedAt,
        });
        recapturedTargets = recapture.recapturedTargets;
        if (!recapture.ok) {
            return buildFailurePayload({
                input: value,
                reason: recapture.failureReason,
                protectedTableBaseline: rowCountsBefore,
                targetInventory,
                targets: recapturedTargets,
            });
        }

        await connection.client.query('BEGIN');
        transaction.began = true;

        const txExistingRows = await loadExistingRawVersions(connection.client, EXPECTED_MATCH_IDS);
        let txContexts;
        try {
            txContexts = buildTargetContexts({
                metadataRows,
                existingRows: txExistingRows,
            });
        } catch (error) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildFailurePayload({
                input: value,
                reason: `TX_TARGET_CONTEXT_INVALID:${error.message}`,
                protectedTableBaseline: rowCountsBefore,
                targetInventory,
                targets: recapturedTargets,
                transaction,
            });
        }
        const txInventoryErrors = validateTargetInventory(txContexts);
        if (txInventoryErrors.length > 0) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildFailurePayload({
                input: value,
                reason: `TX_VERSION_BLOCKED:${txInventoryErrors.join('; ')}`,
                protectedTableBaseline: rowCountsBefore,
                targetInventory,
                targets: recapturedTargets,
                transaction,
            });
        }

        const collectedAt = nowUtcIso(dependencies);
        const insertSql = buildInsertRawMatchDataSql({
            recapturedTargets,
            collectedAt,
        });
        const insertResult = await connection.client.query(insertSql.text, insertSql.values);
        insertedCount =
            typeof insertResult.rowCount === 'number' ? insertResult.rowCount : (insertResult.rows || []).length;
        if (insertedCount !== EXPECTED_TARGETS.length) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildFailurePayload({
                input: value,
                reason: `INSERTED_COUNT_INVALID:${insertedCount}`,
                protectedTableBaseline: rowCountsBefore,
                targetInventory,
                targets: recapturedTargets,
                transaction,
                insertedCount,
            });
        }

        rowCountsAfter = await loadProtectedTableBaseline(connection.client);
        const postWriteRows = await loadRawVersionSummaries(connection.client, EXPECTED_MATCH_IDS);
        const excludedAfterRows = await loadRawVersionSummaries(connection.client, [
            EXCLUDED_ALREADY_WRITTEN_TARGET.matchId,
        ]);
        const duplicateRowsAfter = await loadDuplicateMatchVersionRows(connection.client);
        const verificationErrors = buildPostWriteVerificationErrors({
            rowCountsAfter,
            beforeTargetRows: existingRowsBefore,
            afterTargetRows: postWriteRows,
            excludedBeforeRows,
            excludedAfterRows,
            duplicateRowsAfter,
        });
        if (verificationErrors.length > 0) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildFailurePayload({
                input: value,
                reason: `POST_WRITE_VERIFICATION_FAILED:${verificationErrors.join('; ')}`,
                protectedTableBaseline: rowCountsBefore,
                rowCountsAfter,
                targetInventory,
                targets: recapturedTargets,
                transaction,
                insertedCount,
            });
        }

        await connection.client.query('COMMIT');
        transaction.committed = true;

        return buildSuccessPayload({
            input: value,
            targetInventory,
            recapturedTargets,
            insertedRows: insertResult.rows || [],
            rowCountsBefore,
            rowCountsAfter,
            postWriteRows,
            excludedBeforeRows,
            excludedAfterRows,
            duplicateRowsAfter,
            transaction,
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
        return buildFailurePayload({
            input: value || input,
            reason: String(error.message || error),
            protectedTableBaseline: rowCountsBefore,
            rowCountsAfter,
            targetInventory,
            targets: recapturedTargets,
            transaction,
            insertedCount,
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
    SOURCE,
    ROUTE,
    EXPECTED_TARGETS,
    EXPECTED_EXTERNAL_IDS,
    EXPECTED_MATCH_IDS,
    SEEDED_EIGHT_MATCH_IDS,
    EXCLUDED_ALREADY_WRITTEN_TARGET,
    BASELINE_HASHES,
    EXPECTED_ROW_COUNTS_BEFORE,
    EXPECTED_ROW_COUNTS_AFTER,
    parseArgs,
    parseBaselineHashes,
    normalizeBooleanFlag,
    validateWriteInput,
    buildProtectedTableBaseline,
    validateExactRowCounts,
    validateSchemaConstraints,
    buildExistingVersionDecision,
    validateTargetMetadataRows,
    buildTargetContexts,
    buildPagePropsV2RawData,
    validateRawDataShape,
    buildRecapturedTarget,
    computeStablePagePropsHash,
    buildInsertRawMatchDataSql,
    buildPostWriteVerificationErrors,
    querySelectOnly,
    loadSchemaConstraints,
    loadTargetMatchMetadata,
    loadExistingRawVersions,
    loadRawVersionSummaries,
    loadDuplicateMatchVersionRows,
    loadProtectedTableBaseline,
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
