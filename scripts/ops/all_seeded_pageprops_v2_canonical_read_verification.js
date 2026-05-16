#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const {
    RAW_MATCH_DATA_VERSIONS,
    selectCanonicalRawMatchData,
    isSyntheticOrUnknownVersion,
} = require('../../src/infrastructure/services/RawMatchDataVersionSelector');

const PHASE = 'PHASE5_21L2N_ALL_SEEDED_PAGEPROPS_V2_CANONICAL_READ_VERIFICATION';
const SOURCE = 'fotmob';
const TABLE = 'raw_match_data';
const EXPECTED_TARGET_VERSION = RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2;
const FALLBACK_VERSION = RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1;
const SEEDED_TARGETS = Object.freeze([
    {
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        expectedHash: '7953562593a2ab57ed59741667ccf2fa628adf22eff76fdc7a499f559b3ac440',
    },
    {
        matchId: '53_20252026_4830747',
        externalId: '4830747',
        expectedHash: 'f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc',
    },
    {
        matchId: '53_20252026_4830748',
        externalId: '4830748',
        expectedHash: 'fe664ebe76d4e0e9fda088d4d642fe98fe25c03b920f4f3d83531e6ea4c4ad04',
    },
    {
        matchId: '53_20252026_4830750',
        externalId: '4830750',
        expectedHash: 'e5cada280a0b8d351181defd5605ded7ced091e86be3039439559aed1247b762',
    },
    {
        matchId: '53_20252026_4830751',
        externalId: '4830751',
        expectedHash: 'de78dc67d69ffc22739e4cf648788fd6f50a6dfccae8518a9c1fa8def0eb16a5',
    },
    {
        matchId: '53_20252026_4830752',
        externalId: '4830752',
        expectedHash: '65564219fcb25c6369822a0082f43e96f59675f434208d45cb16ef6395f08c32',
    },
    {
        matchId: '53_20252026_4830753',
        externalId: '4830753',
        expectedHash: '4ab9fcb73465d00cc8bab7a6cb1a61b1b3370d466b15c2ace0092c8357ead413',
    },
    {
        matchId: '53_20252026_4830754',
        externalId: '4830754',
        expectedHash: '29be450e84a55fb56a8db4f1bf7a672adcd6c85e34a8cf06c98e99ac179532c6',
    },
]);
const EXPECTED_TARGET_EXTERNAL_IDS = Object.freeze(SEEDED_TARGETS.map(target => target.externalId));
const EXPECTED_MATCH_IDS = Object.freeze(SEEDED_TARGETS.map(target => target.matchId));
const EXPECTED_HASHES = Object.freeze(
    Object.fromEntries(SEEDED_TARGETS.map(target => [target.externalId, target.expectedHash]))
);
const EXPECTED_ROW_COUNTS = Object.freeze({
    matches: 10,
    raw_match_data: 18,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const EXPECTED_DISTRIBUTION = Object.freeze({
    [RAW_MATCH_DATA_VERSIONS.PHASE4_23]: 1,
    [RAW_MATCH_DATA_VERSIONS.PHASE4_43_SYNTHETIC]: 1,
    [RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1]: 8,
    [RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2]: 8,
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

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
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
        targetExternalIds: null,
        expectedTargetVersion: null,
        fallbackVersion: null,
        expectedHashes: null,
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
        'target-external-ids': 'targetExternalIds',
        target_external_ids: 'targetExternalIds',
        'expected-target-version': 'expectedTargetVersion',
        expected_target_version: 'expectedTargetVersion',
        'fallback-version': 'fallbackVersion',
        fallback_version: 'fallbackVersion',
        'expected-hashes': 'expectedHashes',
        expected_hashes: 'expectedHashes',
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

function arraysEqual(left = [], right = []) {
    if (left.length !== right.length) return false;
    return left.every((value, index) => value === right[index]);
}

function parseTargetExternalIds(rawValue) {
    if (Array.isArray(rawValue)) {
        const ids = rawValue.map(item => normalizeText(item)).filter(Boolean);
        const errors = [];
        if (!arraysEqual(ids, EXPECTED_TARGET_EXTERNAL_IDS)) {
            errors.push(`target-external-ids must be exactly ${EXPECTED_TARGET_EXTERNAL_IDS.join(',')}`);
        }
        return {
            ok: errors.length === 0,
            errors,
            ids,
        };
    }
    const rawText = normalizeText(rawValue);
    if (!rawText) {
        return {
            ok: false,
            errors: ['missing target-external-ids'],
            ids: [],
        };
    }
    const ids = rawText
        .split(',')
        .map(item => normalizeText(item))
        .filter(Boolean);
    const errors = [];
    if (!arraysEqual(ids, EXPECTED_TARGET_EXTERNAL_IDS)) {
        errors.push(`target-external-ids must be exactly ${EXPECTED_TARGET_EXTERNAL_IDS.join(',')}`);
    }
    return {
        ok: errors.length === 0,
        errors,
        ids,
    };
}

function parseExpectedHashes(rawValue) {
    if (isPlainObject(rawValue)) {
        const hashes = Object.fromEntries(
            Object.entries(rawValue).map(([key, value]) => [normalizeText(key), normalizeText(value).toLowerCase()])
        );
        const errors = [];
        for (const externalId of EXPECTED_TARGET_EXTERNAL_IDS) {
            if (!Object.prototype.hasOwnProperty.call(hashes, externalId)) {
                errors.push(`expected-hashes missing ${externalId}`);
                continue;
            }
            if (!/^[a-f0-9]{64}$/.test(hashes[externalId])) {
                errors.push(`expected-hashes ${externalId} must be a 64-char lowercase hex string`);
            } else if (hashes[externalId] !== EXPECTED_HASHES[externalId]) {
                errors.push(`expected-hashes ${externalId} must equal ${EXPECTED_HASHES[externalId]}`);
            }
        }
        for (const externalId of Object.keys(hashes).sort()) {
            if (!EXPECTED_TARGET_EXTERNAL_IDS.includes(externalId)) {
                errors.push(`expected-hashes contains unexpected target ${externalId}`);
            }
        }
        if (Object.keys(hashes).length !== EXPECTED_TARGET_EXTERNAL_IDS.length) {
            errors.push(`expected-hashes must contain exactly ${EXPECTED_TARGET_EXTERNAL_IDS.length} targets`);
        }
        return {
            ok: errors.length === 0,
            errors,
            hashes,
        };
    }
    const rawText = normalizeText(rawValue);
    const errors = [];
    if (!rawText) {
        return {
            ok: false,
            errors: ['missing expected-hashes'],
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
        if (count > 1) errors.push(`expected-hashes contains duplicate target ${key}`);
    }

    let parsed;
    try {
        parsed = JSON.parse(rawText);
    } catch (error) {
        return {
            ok: false,
            errors: [`expected-hashes must be valid JSON: ${error.message}`],
            hashes: {},
        };
    }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        return {
            ok: false,
            errors: ['expected-hashes must be a JSON object'],
            hashes: {},
        };
    }

    const hashes = Object.fromEntries(
        Object.entries(parsed).map(([key, value]) => [normalizeText(key), normalizeText(value)])
    );
    for (const externalId of EXPECTED_TARGET_EXTERNAL_IDS) {
        if (!Object.prototype.hasOwnProperty.call(hashes, externalId)) {
            errors.push(`expected-hashes missing ${externalId}`);
            continue;
        }
        const hash = normalizeText(hashes[externalId]).toLowerCase();
        if (!/^[a-f0-9]{64}$/.test(hash)) {
            errors.push(`expected-hashes ${externalId} must be a 64-char lowercase hex string`);
        } else if (hash !== EXPECTED_HASHES[externalId]) {
            errors.push(`expected-hashes ${externalId} must equal ${EXPECTED_HASHES[externalId]}`);
        }
        hashes[externalId] = hash;
    }
    for (const externalId of Object.keys(hashes).sort()) {
        if (!EXPECTED_TARGET_EXTERNAL_IDS.includes(externalId)) {
            errors.push(`expected-hashes contains unexpected target ${externalId}`);
        }
    }
    if (Object.keys(hashes).length !== EXPECTED_TARGET_EXTERNAL_IDS.length) {
        errors.push(`expected-hashes must contain exactly ${EXPECTED_TARGET_EXTERNAL_IDS.length} targets`);
    }

    return {
        ok: errors.length === 0,
        errors,
        hashes,
    };
}

function pushRequiredNo(errors, value, flagName) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.21L2N`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function normalizeVerificationInput(input = {}) {
    const parsedTargetExternalIds = parseTargetExternalIds(input.targetExternalIds);
    const parsedExpectedHashes = parseExpectedHashes(input.expectedHashes);
    return {
        source: normalizeText(input.source).toLowerCase(),
        table: normalizeText(input.table),
        targetExternalIdsRaw: normalizeText(input.targetExternalIds),
        targetExternalIds: parsedTargetExternalIds.ids,
        targetExternalIdsErrors: parsedTargetExternalIds.errors,
        expectedTargetVersion: normalizeText(input.expectedTargetVersion),
        fallbackVersion: normalizeText(input.fallbackVersion),
        expectedHashesRaw: normalizeText(input.expectedHashes),
        expectedHashes: parsedExpectedHashes.hashes,
        expectedHashesErrors: parsedExpectedHashes.errors,
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
    errors.push(...value.targetExternalIdsErrors);
    if (value.expectedTargetVersion !== EXPECTED_TARGET_VERSION) {
        errors.push(`expected-target-version must be ${EXPECTED_TARGET_VERSION}`);
    }
    if (value.fallbackVersion !== FALLBACK_VERSION) {
        errors.push(`fallback-version must be ${FALLBACK_VERSION}`);
    }
    errors.push(...value.expectedHashesErrors);
    for (const flag of REQUIRED_NO_FLAGS) {
        pushRequiredNo(
            errors,
            value[flag],
            flag.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)
        );
    }
    for (const flag of BLOCKED_TRUE_FLAGS) {
        if (value[flag] === true) {
            errors.push(`${flag.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)}=yes is blocked in Phase 5.21L2N`);
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
        match_id: normalizeText(row.match_id),
        data_version: normalizeText(row.data_version),
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

function buildSeededVerification(rows = [], value = {}, errors = []) {
    const grouped = groupByMatchId(rows);
    const perTarget = [];
    let canonicalV2Count = 0;
    let hashMatchCount = 0;
    let missingV2Count = 0;
    let missingV1Count = 0;
    let fallbackToV1Count = 0;
    let unexpectedVersionCount = 0;

    for (const target of SEEDED_TARGETS) {
        const targetRows = grouped.get(target.matchId) || [];
        const availableVersions = uniqueVersions(targetRows);
        const unexpectedVersions = availableVersions.filter(
            version => version !== value.expectedTargetVersion && version !== value.fallbackVersion
        );
        const hasV1 = hasVersion(targetRows, value.fallbackVersion);
        const hasV2 = hasVersion(targetRows, value.expectedTargetVersion);
        let selected = null;
        try {
            selected = selectCanonical(targetRows, value);
        } catch (error) {
            errors.push(`${target.externalId} canonical selection failed: ${String(error.message || error)}`);
        }

        if (!hasV1) {
            missingV1Count += 1;
            errors.push(`${target.externalId} missing ${value.fallbackVersion}`);
        }
        if (!hasV2) {
            missingV2Count += 1;
            errors.push(`${target.externalId} missing ${value.expectedTargetVersion}`);
        }
        if (unexpectedVersions.length > 0) {
            unexpectedVersionCount += 1;
            errors.push(`${target.externalId} has unexpected versions: ${unexpectedVersions.join(', ')}`);
        }
        if (!selected) {
            errors.push(`${target.externalId} canonical selection returned null`);
        } else {
            if (normalizeText(selected.data_version) === value.expectedTargetVersion) {
                canonicalV2Count += 1;
            }
            if (normalizeText(selected.data_version) === value.fallbackVersion) {
                fallbackToV1Count += 1;
                errors.push(`${target.externalId} unexpectedly fell back to ${value.fallbackVersion}`);
            }
            if (normalizeText(selected.data_version) !== value.expectedTargetVersion) {
                errors.push(
                    `${target.externalId} canonical selected ${normalizeText(selected.data_version) || 'null'}, expected ${value.expectedTargetVersion}`
                );
            }
            if (normalizeText(selected.data_hash) === value.expectedHashes[target.externalId]) {
                hashMatchCount += 1;
            } else {
                errors.push(
                    `${target.externalId} selected hash mismatch: ${normalizeText(selected.data_hash)} expected ${value.expectedHashes[target.externalId]}`
                );
            }
            if (selected.has_meta !== true) errors.push(`${target.externalId} selected v2 row missing _meta key`);
            if (selected.has_match_id !== true) errors.push(`${target.externalId} selected v2 row missing matchId key`);
            if (selected.has_pageprops !== true) {
                errors.push(`${target.externalId} selected v2 row missing pageProps key`);
            }
        }

        perTarget.push({
            match_id: target.matchId,
            external_id: target.externalId,
            available_versions: availableVersions,
            canonical_selected_version: selected?.data_version || null,
            selected_data_hash: selected?.data_hash || null,
            expected_data_hash: value.expectedHashes[target.externalId],
            hash_matches_expected: normalizeText(selected?.data_hash) === value.expectedHashes[target.externalId],
            has_meta: selected?.has_meta === true,
            has_matchId: selected?.has_match_id === true,
            has_pageProps: selected?.has_pageprops === true,
        });
    }

    return {
        seeded_matches_checked: SEEDED_TARGETS.length,
        canonical_v2_count: canonicalV2Count,
        hash_match_count: hashMatchCount,
        missing_v2_count: missingV2Count,
        missing_v1_count: missingV1Count,
        fallback_to_v1_count: fallbackToV1Count,
        unexpected_version_count: unexpectedVersionCount,
        per_target: perTarget,
    };
}

function buildExcludedVersionsVerification(rows = [], value = {}, errors = []) {
    const grouped = groupByMatchId(rows);
    const excludedGroups = [];
    const phase443Rows = [];
    const phase423Rows = [];
    const unknownRows = [];

    for (const row of Array.isArray(rows) ? rows : []) {
        const version = normalizeText(row.data_version);
        if (version === RAW_MATCH_DATA_VERSIONS.PHASE4_43_SYNTHETIC) phase443Rows.push(row);
        else if (version === RAW_MATCH_DATA_VERSIONS.PHASE4_23) phase423Rows.push(row);
        else if (isSyntheticOrUnknownVersion(version)) unknownRows.push(row);
    }

    for (const [matchId, matchRows] of grouped.entries()) {
        let selected = null;
        try {
            selected = selectCanonical(matchRows, value);
        } catch (error) {
            errors.push(`excluded group ${matchId} canonical selection failed: ${String(error.message || error)}`);
        }
        if (selected) {
            errors.push(`excluded group ${matchId} selected ${normalizeText(selected.data_version)} unexpectedly`);
        }
        excludedGroups.push({
            match_id: matchId,
            external_ids: [...new Set(matchRows.map(row => normalizeText(row.external_id)).filter(Boolean))].sort(),
            available_versions: uniqueVersions(matchRows),
            canonical_selected_version: selected?.data_version || null,
            excluded: selected === null,
        });
    }

    const syntheticExcluded =
        phase443Rows.length === 0 ||
        phase443Rows.every(row => {
            const group = excludedGroups.find(item => item.match_id === normalizeText(row.match_id));
            return group?.excluded === true;
        });
    const phase423Excluded =
        phase423Rows.length === 0 ||
        phase423Rows.every(row => {
            const group = excludedGroups.find(item => item.match_id === normalizeText(row.match_id));
            return group?.excluded === true;
        });
    const unknownExcluded =
        unknownRows.length === 0 ||
        unknownRows.every(row => {
            const group = excludedGroups.find(item => item.match_id === normalizeText(row.match_id));
            return group?.excluded === true;
        });
    if (!syntheticExcluded) errors.push('PHASE4.43_SYNTHETIC was not excluded');
    if (!phase423Excluded) errors.push('PHASE4.23 was not excluded');
    if (!unknownExcluded) errors.push('unknown versions were not excluded');

    return {
        synthetic_excluded: syntheticExcluded,
        phase4_23_excluded: phase423Excluded,
        unknown_excluded: unknownExcluded,
        synthetic_rows_checked: phase443Rows.length,
        phase4_23_rows_checked: phase423Rows.length,
        unknown_rows_checked: unknownRows.length,
        excluded_groups: excludedGroups,
    };
}

function buildVerificationResult(input = {}, rows = {}) {
    const value = normalizeVerificationInput(input);
    const errors = [];
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

    const seededVerification = buildSeededVerification(rows.seededRows, value, errors);
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
        seeded_verification: seededVerification,
        per_target: seededVerification.per_target,
        excluded_versions_verification: excludedVersionsVerification,
        duplicates,
        errors,
        controlled_error:
            errors.length > 0 ? `ALL_SEEDED_CANONICAL_READ_VERIFICATION_FAILED:${errors.join('; ')}` : null,
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
              id,
              match_id,
              external_id,
              data_version,
              data_hash,
              collected_at,
              raw_data ? '_meta' AS has_meta,
              raw_data ? 'matchId' AS has_match_id,
              raw_data ? 'pageProps' AS has_pageprops
            FROM raw_match_data
            WHERE match_id = ANY($1::text[])
            ORDER BY match_id, data_version, id
        `,
        [EXPECTED_MATCH_IDS]
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

async function buildAllSeededCanonicalReadVerification(input = {}, dependencies = {}) {
    const validation = validateVerificationInput(input);
    if (!validation.ok) {
        return {
            phase: PHASE,
            verification_only: true,
            ok: false,
            controlled_error: `INVALID_ALL_SEEDED_CANONICAL_READ_VERIFICATION_INPUT:${validation.errors.join('; ')}`,
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
        `  node scripts/ops/all_seeded_pageprops_v2_canonical_read_verification.js --source=${SOURCE} --table=${TABLE} --target-external-ids=${EXPECTED_TARGET_EXTERNAL_IDS.join(',')} --expected-target-version=${EXPECTED_TARGET_VERSION} --fallback-version=${FALLBACK_VERSION} --expected-hashes='<json>' --allow-db-write=no --allow-network=no --allow-parser-features=no --allow-training=no --allow-prediction=no`,
        '',
        'Safety:',
        '  Phase 5.21L2N is SELECT-only: no DB write, raw_match_data write, network/FotMob access, parser/features, training, or prediction.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const stdout = io.stdout || process.stdout.write.bind(process.stdout);
    const args = parseArgs(argv);
    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }
    const result = await buildAllSeededCanonicalReadVerification(args, dependencies);
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
    EXPECTED_TARGET_VERSION,
    FALLBACK_VERSION,
    SEEDED_TARGETS,
    EXPECTED_TARGET_EXTERNAL_IDS,
    EXPECTED_MATCH_IDS,
    EXPECTED_HASHES,
    EXPECTED_ROW_COUNTS,
    EXPECTED_DISTRIBUTION,
    parseArgs,
    parseTargetExternalIds,
    parseExpectedHashes,
    normalizeBooleanFlag,
    validateVerificationInput,
    assertSelectOnly,
    buildSchemaSummary,
    rowsToCountObject,
    buildDistributionObject,
    buildDuplicateSummary,
    buildSeededVerification,
    buildExcludedVersionsVerification,
    buildVerificationResult,
    readVerificationRows,
    buildAllSeededCanonicalReadVerification,
    runCli,
};
