#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const {
    RAW_MATCH_DATA_VERSIONS,
    selectCanonicalRawMatchData,
    isSyntheticOrUnknownVersion,
} = require('../../src/infrastructure/services/RawMatchDataVersionSelector');

const PHASE = 'PHASE5_21L2K_PAGEPROPS_V2_POST_WRITE_CANONICAL_READ_VERIFICATION';
const SOURCE = 'fotmob';
const TABLE = 'raw_match_data';
const TARGET_MATCH_ID = '53_20252026_4830747';
const TARGET_EXTERNAL_ID = '4830747';
const EXPECTED_TARGET_VERSION = RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2;
const FALLBACK_VERSION = RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1;
const EXPECTED_TARGET_HASH = 'f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc';
const SEEDED_MATCH_IDS = Object.freeze([
    '53_20252026_4830746',
    TARGET_MATCH_ID,
    '53_20252026_4830748',
    '53_20252026_4830750',
    '53_20252026_4830751',
    '53_20252026_4830752',
    '53_20252026_4830753',
    '53_20252026_4830754',
]);
const REMAINING_SEEDED_MATCH_IDS = Object.freeze(SEEDED_MATCH_IDS.filter(matchId => matchId !== TARGET_MATCH_ID));
const EXPECTED_ROW_COUNTS = Object.freeze({
    matches: 10,
    raw_match_data: 11,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const EXPECTED_DISTRIBUTION = Object.freeze({
    [RAW_MATCH_DATA_VERSIONS.PHASE4_23]: 1,
    [RAW_MATCH_DATA_VERSIONS.PHASE4_43_SYNTHETIC]: 1,
    [RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1]: 8,
    [RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2]: 1,
});
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowNetwork',
    'allowParserFeatures',
    'allowTraining',
    'allowPrediction',
]);
const BLOCKED_TRUE_FLAGS = Object.freeze([
    'execute',
    'commit',
    'touchFotmob',
    'liveRequest',
    'allowRawMatchDataWrite',
    'allowSchemaMigration',
    'allowMatchesWrite',
]);

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

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        source: null,
        table: null,
        targetMatchId: null,
        targetExternalId: null,
        expectedTargetVersion: null,
        fallbackVersion: null,
        expectedTargetHash: null,
        allowDbWrite: null,
        allowNetwork: null,
        allowParserFeatures: null,
        allowTraining: null,
        allowPrediction: null,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowRawMatchDataWrite: false,
        allowSchemaMigration: false,
        allowMatchesWrite: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        table: 'table',
        'target-match-id': 'targetMatchId',
        target_match_id: 'targetMatchId',
        'target-external-id': 'targetExternalId',
        target_external_id: 'targetExternalId',
        'expected-target-version': 'expectedTargetVersion',
        expected_target_version: 'expectedTargetVersion',
        'fallback-version': 'fallbackVersion',
        fallback_version: 'fallbackVersion',
        'expected-target-hash': 'expectedTargetHash',
        expected_target_hash: 'expectedTargetHash',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-network': 'allowNetwork',
        allow_network: 'allowNetwork',
        'allow-parser-features': 'allowParserFeatures',
        allow_parser_features: 'allowParserFeatures',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        execute: 'execute',
        commit: 'commit',
        'touch-fotmob': 'touchFotmob',
        touch_fotmob: 'touchFotmob',
        'live-request': 'liveRequest',
        live_request: 'liveRequest',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-schema-migration': 'allowSchemaMigration',
        allow_schema_migration: 'allowSchemaMigration',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'allowDbWrite',
        'allowNetwork',
        'allowParserFeatures',
        'allowTraining',
        'allowPrediction',
        'execute',
        'commit',
        'touchFotmob',
        'liveRequest',
        'allowRawMatchDataWrite',
        'allowSchemaMigration',
        'allowMatchesWrite',
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

function pushRequiredNo(errors, value, flagName) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.21L2K`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function normalizeVerificationInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        table: normalizeText(input.table),
        targetMatchId: normalizeText(input.targetMatchId),
        targetExternalId: normalizeText(input.targetExternalId),
        expectedTargetVersion: normalizeText(input.expectedTargetVersion),
        fallbackVersion: normalizeText(input.fallbackVersion),
        expectedTargetHash: normalizeText(input.expectedTargetHash),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowNetwork: normalizeBooleanFlag(input.allowNetwork, undefined),
        allowParserFeatures: normalizeBooleanFlag(input.allowParserFeatures, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        execute: normalizeBooleanFlag(input.execute, false),
        commit: normalizeBooleanFlag(input.commit, false),
        touchFotmob: normalizeBooleanFlag(input.touchFotmob, false),
        liveRequest: normalizeBooleanFlag(input.liveRequest, false),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, false),
        allowSchemaMigration: normalizeBooleanFlag(input.allowSchemaMigration, false),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validateVerificationInput(input = {}) {
    const value = normalizeVerificationInput(input);
    const errors = [];
    if (value.unknown.length > 0) errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    if (!value.source) errors.push(`missing source=${SOURCE}`);
    else if (value.source !== SOURCE) errors.push(`source must be ${SOURCE}`);
    if (!value.table) errors.push(`missing table=${TABLE}`);
    else if (value.table !== TABLE) errors.push(`table must be ${TABLE}`);
    if (value.targetMatchId !== TARGET_MATCH_ID) errors.push(`target-match-id must be ${TARGET_MATCH_ID}`);
    if (value.targetExternalId !== TARGET_EXTERNAL_ID) errors.push(`target-external-id must be ${TARGET_EXTERNAL_ID}`);
    if (value.expectedTargetVersion !== EXPECTED_TARGET_VERSION) {
        errors.push(`expected-target-version must be ${EXPECTED_TARGET_VERSION}`);
    }
    if (value.fallbackVersion !== FALLBACK_VERSION) errors.push(`fallback-version must be ${FALLBACK_VERSION}`);
    if (!value.expectedTargetHash) errors.push('missing expected-target-hash');
    else if (!/^[a-f0-9]{64}$/.test(value.expectedTargetHash)) {
        errors.push('expected-target-hash must be a 64-char lowercase hex string');
    } else if (value.expectedTargetHash !== EXPECTED_TARGET_HASH) {
        errors.push(`expected-target-hash must equal ${EXPECTED_TARGET_HASH}`);
    }
    for (const flag of REQUIRED_NO_FLAGS) {
        pushRequiredNo(
            errors,
            value[flag],
            flag.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)
        );
    }
    for (const flag of BLOCKED_TRUE_FLAGS) {
        if (value[flag] === true) {
            errors.push(`${flag.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)}=yes is blocked in Phase 5.21L2K`);
        }
    }

    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function assertSelectOnly(sql) {
    const normalized = normalizeText(sql);
    if (!/^SELECT\b/i.test(normalized)) {
        throw new Error(`NON_SELECT_SQL_BLOCKED: ${normalized.slice(0, 80)}`);
    }
    if (/\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|MERGE|COPY|BEGIN|COMMIT|ROLLBACK)\b/i.test(normalized)) {
        throw new Error(`NON_SELECT_SQL_BLOCKED: ${normalized.slice(0, 80)}`);
    }
}

async function safeSelect(db, sql, values = []) {
    assertSelectOnly(sql);
    const result = await db.query(sql, values);
    return result.rows || [];
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

function rowsToCountObject(rows = []) {
    const counts = {};
    for (const row of Array.isArray(rows) ? rows : []) {
        counts[normalizeText(row.table_name)] = Number(row.rows || 0);
    }
    return counts;
}

function buildDistributionObject(rows = []) {
    const distribution = {};
    for (const row of Array.isArray(rows) ? rows : []) {
        distribution[normalizeText(row.data_version)] = Number(row.rows || 0);
    }
    return distribution;
}

function uniqueVersions(rows = []) {
    return [
        ...new Set((Array.isArray(rows) ? rows : []).map(row => normalizeText(row.data_version)).filter(Boolean)),
    ].sort();
}

function groupByMatchId(rows = []) {
    const grouped = new Map();
    for (const row of Array.isArray(rows) ? rows : []) {
        const matchId = normalizeText(row.match_id);
        if (!grouped.has(matchId)) grouped.set(matchId, []);
        grouped.get(matchId).push(row);
    }
    return grouped;
}

function buildDuplicateSummary(rows = []) {
    const duplicates = (Array.isArray(rows) ? rows : []).map(row => ({
        match_id: row.match_id,
        data_version: row.data_version,
        rows: Number(row.rows || 0),
    }));
    return {
        duplicate_match_id_data_version_count: duplicates.length,
        rows: duplicates,
    };
}

function hasVersion(rows, version) {
    return (Array.isArray(rows) ? rows : []).some(row => normalizeText(row.data_version) === version);
}

function selectCanonical(rows, value) {
    return selectCanonicalRawMatchData({
        rows,
        allowedVersions: [value.expectedTargetVersion, value.fallbackVersion],
        versionPriority: [value.expectedTargetVersion, value.fallbackVersion],
        excludeSyntheticUnknown: true,
    });
}

function verifyExpectedCounts(actual, expected, errors, label) {
    for (const [key, expectedValue] of Object.entries(expected)) {
        if (Number(actual[key] || 0) !== expectedValue) {
            errors.push(`${label} ${key} expected ${expectedValue}, got ${Number(actual[key] || 0)}`);
        }
    }
}

function buildTargetVerification(rows, value, errors, warnings) {
    const targetRows = (Array.isArray(rows) ? rows : []).filter(
        row =>
            normalizeText(row.match_id) === value.targetMatchId &&
            normalizeText(row.external_id) === value.targetExternalId
    );
    let selected = null;
    try {
        selected = selectCanonical(targetRows, value);
    } catch (error) {
        errors.push(`target canonical selection failed: ${String(error.message || error)}`);
    }
    const v1Exists = hasVersion(targetRows, value.fallbackVersion);
    const v2Exists = hasVersion(targetRows, value.expectedTargetVersion);
    if (!v1Exists) warnings.push('target fotmob_html_hyd_v1 row is missing');
    if (!v2Exists) errors.push('target fotmob_pageprops_v2 row is missing');
    if (!selected) {
        errors.push('target canonical selection returned null');
    } else {
        if (normalizeText(selected.data_version) !== value.expectedTargetVersion) {
            errors.push(`target canonical selected ${selected.data_version}, expected ${value.expectedTargetVersion}`);
        }
        if (normalizeText(selected.data_hash) !== value.expectedTargetHash) {
            errors.push(`target selected hash mismatch: ${selected.data_hash}`);
        }
        if (selected.has_meta !== true) errors.push('target selected v2 row missing _meta key');
        if (selected.has_match_id !== true) errors.push('target selected v2 row missing matchId key');
        if (selected.has_pageprops !== true) errors.push('target selected v2 row missing pageProps key');
    }

    return {
        match_id: value.targetMatchId,
        external_id: value.targetExternalId,
        available_versions: uniqueVersions(targetRows),
        canonical_selected_version: selected?.data_version || null,
        canonical_selected_hash: selected?.data_hash || null,
        hash_matches_expected: normalizeText(selected?.data_hash) === value.expectedTargetHash,
        has_meta: selected?.has_meta === true,
        has_matchId: selected?.has_match_id === true,
        has_pageProps: selected?.has_pageprops === true,
        v1_exists: v1Exists,
        v2_exists: v2Exists,
        warnings,
    };
}

function buildFallbackVerification(rows, value, errors) {
    const grouped = groupByMatchId(rows);
    const perMatch = [];
    let fallbackToV1Count = 0;
    let unexpectedMissingCount = 0;
    let unexpectedV2Count = 0;

    for (const matchId of REMAINING_SEEDED_MATCH_IDS) {
        const matchRows = grouped.get(matchId) || [];
        let selected = null;
        try {
            selected = selectCanonical(matchRows, value);
        } catch (error) {
            errors.push(`${matchId} canonical selection failed: ${String(error.message || error)}`);
        }
        const hasV1 = hasVersion(matchRows, value.fallbackVersion);
        const hasV2 = hasVersion(matchRows, value.expectedTargetVersion);
        if (!hasV1) {
            unexpectedMissingCount += 1;
            errors.push(`${matchId} missing ${value.fallbackVersion}`);
        }
        if (hasV2) {
            unexpectedV2Count += 1;
            errors.push(`${matchId} unexpectedly has ${value.expectedTargetVersion}`);
        }
        if (selected?.data_version === value.fallbackVersion) {
            fallbackToV1Count += 1;
        } else {
            errors.push(`${matchId} selected ${selected?.data_version || 'null'}, expected ${value.fallbackVersion}`);
        }
        perMatch.push({
            match_id: matchId,
            external_id: matchRows[0]?.external_id || null,
            available_versions: uniqueVersions(matchRows),
            canonical_selected_version: selected?.data_version || null,
            canonical_selected_hash: selected?.data_hash || null,
            has_v1: hasV1,
            has_v2: hasV2,
        });
    }

    return {
        seeded_matches_checked: REMAINING_SEEDED_MATCH_IDS.length,
        fallback_to_v1_count: fallbackToV1Count,
        unexpected_missing_count: unexpectedMissingCount,
        unexpected_v2_count: unexpectedV2Count,
        per_match: perMatch,
    };
}

function buildExcludedVersionsVerification(rows, value, errors) {
    const legacyRows = Array.isArray(rows) ? rows : [];
    const phase443Rows = legacyRows.filter(
        row => normalizeText(row.data_version) === RAW_MATCH_DATA_VERSIONS.PHASE4_43_SYNTHETIC
    );
    const phase423Rows = legacyRows.filter(
        row => normalizeText(row.data_version) === RAW_MATCH_DATA_VERSIONS.PHASE4_23
    );
    const unknownRows = legacyRows.filter(row => {
        const version = normalizeText(row.data_version);
        return (
            isSyntheticOrUnknownVersion(version) &&
            version !== RAW_MATCH_DATA_VERSIONS.PHASE4_43_SYNTHETIC &&
            version !== RAW_MATCH_DATA_VERSIONS.PHASE4_23
        );
    });
    const selectionRows = legacyRows.map(row => {
        let selected = null;
        try {
            selected = selectCanonical([row], value);
        } catch (error) {
            errors.push(`legacy row ${row.id} canonical selection failed: ${String(error.message || error)}`);
        }
        if (selected) {
            errors.push(`legacy row ${row.id} with version ${row.data_version} was selected unexpectedly`);
        }
        return {
            id: row.id,
            match_id: row.match_id,
            external_id: row.external_id,
            data_version: row.data_version,
            canonical_selected_version: selected?.data_version || null,
            excluded: selected === null,
        };
    });
    const syntheticExcluded =
        phase443Rows.length > 0 && phase443Rows.every(row => selectionRows.find(item => item.id === row.id)?.excluded);
    const phase423Excluded =
        phase423Rows.length > 0 && phase423Rows.every(row => selectionRows.find(item => item.id === row.id)?.excluded);
    const unknownExcluded = unknownRows.every(row => selectionRows.find(item => item.id === row.id)?.excluded);
    if (!syntheticExcluded) errors.push('PHASE4.43_SYNTHETIC was not verified as excluded');
    if (!phase423Excluded) errors.push('PHASE4.23 was not verified as excluded');
    if (!unknownExcluded) errors.push('unknown versions were not verified as excluded');

    return {
        synthetic_excluded: syntheticExcluded,
        phase4_23_excluded: phase423Excluded,
        unknown_excluded: unknownExcluded,
        legacy_rows_checked: legacyRows.length,
        excluded_rows: selectionRows,
    };
}

function buildVerificationResult(input, rows) {
    const value = normalizeVerificationInput(input);
    const errors = [];
    const warnings = [];
    const schema = buildSchemaSummary(rows.constraints);
    const rowCounts = rowsToCountObject(rows.rowCounts);
    const distribution = buildDistributionObject(rows.distribution);
    const duplicates = buildDuplicateSummary(rows.duplicates);

    if (!schema.unique_match_id_data_version) errors.push('raw_match_data UNIQUE(match_id,data_version) is missing');
    if (schema.unique_match_id_only) errors.push('legacy UNIQUE(match_id) is still present');
    verifyExpectedCounts(rowCounts, EXPECTED_ROW_COUNTS, errors, 'row count');
    verifyExpectedCounts(distribution, EXPECTED_DISTRIBUTION, errors, 'data_version distribution');
    if (duplicates.duplicate_match_id_data_version_count !== 0) {
        errors.push(`duplicate match_id,data_version rows found: ${duplicates.duplicate_match_id_data_version_count}`);
    }

    const targetWarnings = [];
    const targetVerification = buildTargetVerification(rows.seededRows, value, errors, targetWarnings);
    warnings.push(...targetWarnings);
    const fallbackVerification = buildFallbackVerification(rows.seededRows, value, errors);
    const excludedVersionsVerification = buildExcludedVersionsVerification(rows.legacyRows, value, errors);

    return {
        phase: PHASE,
        verification_only: true,
        ok: errors.length === 0,
        source: value.source,
        table: value.table,
        schema,
        row_counts: rowCounts,
        data_version_distribution: distribution,
        target_verification: targetVerification,
        fallback_verification: fallbackVerification,
        excluded_versions_verification: excludedVersionsVerification,
        duplicates,
        warnings,
        errors,
        controlled_error: errors.length > 0 ? `CANONICAL_READ_VERIFICATION_FAILED:${errors.join('; ')}` : null,
        db_write_executed: false,
        raw_match_data_write_executed: false,
        network_executed: false,
        parser_features_executed: false,
        training_executed: false,
        prediction_executed: false,
    };
}

async function readVerificationRows(db) {
    const rowCounts = await safeSelect(
        db,
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
        `
    );
    const constraints = await safeSelect(
        db,
        `
            SELECT
              conname,
              contype,
              pg_get_constraintdef(c.oid) AS definition
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'raw_match_data'
            ORDER BY conname
        `
    );
    const seededRows = await safeSelect(
        db,
        `
            SELECT
              r.id,
              r.match_id,
              r.external_id,
              r.data_version,
              r.data_hash,
              r.collected_at,
              r.raw_data ? '_meta' AS has_meta,
              r.raw_data ? 'matchId' AS has_match_id,
              r.raw_data ? 'content' AS has_content,
              r.raw_data ? 'pageProps' AS has_pageprops
            FROM raw_match_data r
            WHERE r.match_id = ANY($1::text[])
            ORDER BY r.match_id, r.data_version, r.id
        `,
        [SEEDED_MATCH_IDS]
    );
    const legacyRows = await safeSelect(
        db,
        `
            SELECT id, match_id, external_id, data_version, data_hash, collected_at
            FROM raw_match_data
            WHERE data_version <> ALL($1::text[])
            ORDER BY data_version, match_id, id
        `,
        [[EXPECTED_TARGET_VERSION, FALLBACK_VERSION]]
    );
    const distribution = await safeSelect(
        db,
        `
            SELECT data_version, COUNT(*)::int AS rows
            FROM raw_match_data
            GROUP BY data_version
            ORDER BY data_version
        `
    );
    const duplicates = await safeSelect(
        db,
        `
            SELECT match_id, data_version, COUNT(*)::int AS rows
            FROM raw_match_data
            GROUP BY match_id, data_version
            HAVING COUNT(*) > 1
            ORDER BY match_id, data_version
        `
    );
    return {
        rowCounts,
        constraints,
        seededRows,
        legacyRows,
        distribution,
        duplicates,
    };
}

async function buildPostWriteCanonicalReadVerification(input = {}, dependencies = {}) {
    const validation = validateVerificationInput(input);
    if (!validation.ok) {
        return {
            phase: PHASE,
            verification_only: true,
            ok: false,
            controlled_error: `INVALID_CANONICAL_READ_VERIFICATION_INPUT:${validation.errors.join('; ')}`,
            errors: validation.errors,
            db_write_executed: false,
            raw_match_data_write_executed: false,
            network_executed: false,
            parser_features_executed: false,
            training_executed: false,
            prediction_executed: false,
        };
    }

    if (dependencies.verificationRows) {
        return buildVerificationResult(validation.value, dependencies.verificationRows);
    }

    const pool = dependencies.pool || (dependencies.getPool ? dependencies.getPool() : createDefaultPool());
    const shouldClose = !dependencies.pool && !dependencies.getPool;
    try {
        const rows = await readVerificationRows(pool);
        return buildVerificationResult(validation.value, rows);
    } finally {
        if (shouldClose) {
            await closeDefaultPool();
        }
    }
}

function createDefaultPool() {
    return require('../../config/database').getPool();
}

async function closeDefaultPool() {
    await require('../../config/database').closePool();
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/pageprops_v2_post_write_canonical_read_verification.js --source=fotmob --table=raw_match_data --target-match-id=53_20252026_4830747 --target-external-id=4830747 --expected-target-version=fotmob_pageprops_v2 --fallback-version=fotmob_html_hyd_v1 --expected-target-hash=f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc --allow-db-write=no --allow-network=no --allow-parser-features=no --allow-training=no --allow-prediction=no',
        '',
        'Safety:',
        '  Phase 5.21L2K is SELECT-only: no DB write, raw_match_data write, network/FotMob access, parser/features, training, or prediction.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const stdout = io.stdout || process.stdout.write.bind(process.stdout);
    const args = parseArgs(argv);
    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }
    const result = await buildPostWriteCanonicalReadVerification(args, dependencies);
    stdout(`${JSON.stringify(result, null, 2)}\n`);
    return result.ok ? 0 : 1;
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
                        verification_only: true,
                        ok: false,
                        controlled_error: String(error.message || error),
                        db_write_executed: false,
                        raw_match_data_write_executed: false,
                        network_executed: false,
                        parser_features_executed: false,
                        training_executed: false,
                        prediction_executed: false,
                    },
                    null,
                    2
                )}\n`
            );
            process.exitCode = 1;
        });
}

module.exports = {
    PHASE,
    SOURCE,
    TABLE,
    TARGET_MATCH_ID,
    TARGET_EXTERNAL_ID,
    EXPECTED_TARGET_VERSION,
    FALLBACK_VERSION,
    EXPECTED_TARGET_HASH,
    SEEDED_MATCH_IDS,
    REMAINING_SEEDED_MATCH_IDS,
    parseArgs,
    normalizeBooleanFlag,
    validateVerificationInput,
    assertSelectOnly,
    buildSchemaSummary,
    rowsToCountObject,
    buildDistributionObject,
    buildDuplicateSummary,
    buildTargetVerification,
    buildFallbackVerification,
    buildExcludedVersionsVerification,
    buildVerificationResult,
    buildPostWriteCanonicalReadVerification,
    runCli,
};
