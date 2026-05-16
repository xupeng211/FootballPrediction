'use strict';

const RAW_MATCH_DATA_VERSIONS = Object.freeze({
    FOTMOB_PAGEPROPS_V2: 'fotmob_pageprops_v2',
    FOTMOB_HTML_HYD_V1: 'fotmob_html_hyd_v1',
    PHASE4_43_SYNTHETIC: 'PHASE4.43_SYNTHETIC',
    PHASE4_23: 'PHASE4.23',
});

const DEFAULT_CANONICAL_VERSION_PRIORITY = Object.freeze([
    RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2,
    RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1,
]);

function normalizeText(value) {
    return String(value || '').trim();
}

function normalizeVersion(value) {
    return normalizeText(value);
}

function classifyRawDataVersion(dataVersion) {
    const version = normalizeVersion(dataVersion);
    if (version === RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2) {
        return 'canonical_fotmob_pageprops';
    }
    if (version === RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1) {
        return 'canonical_fotmob_transformed';
    }
    if (version === RAW_MATCH_DATA_VERSIONS.PHASE4_43_SYNTHETIC) {
        return 'legacy_synthetic';
    }
    if (version === RAW_MATCH_DATA_VERSIONS.PHASE4_23) {
        return 'legacy_unknown';
    }
    return 'unknown';
}

function isCanonicalFotMobVersion(dataVersion) {
    const classification = classifyRawDataVersion(dataVersion);
    return classification === 'canonical_fotmob_pageprops' || classification === 'canonical_fotmob_transformed';
}

function isSyntheticOrUnknownVersion(dataVersion) {
    return !isCanonicalFotMobVersion(dataVersion);
}

function filterRowsByAllowedVersions({
    rows = [],
    allowedVersions = DEFAULT_CANONICAL_VERSION_PRIORITY,
    excludeSyntheticUnknown = true,
} = {}) {
    const allowed = new Set((allowedVersions || []).map(normalizeVersion).filter(Boolean));
    return (Array.isArray(rows) ? rows : []).filter(row => {
        const version = normalizeVersion(row?.data_version);
        if (excludeSyntheticUnknown && isSyntheticOrUnknownVersion(version)) {
            return false;
        }
        return allowed.size === 0 || allowed.has(version);
    });
}

function assertNoDuplicateMatchVersion(rows = []) {
    const seen = new Set();
    for (const row of Array.isArray(rows) ? rows : []) {
        const matchId = normalizeText(row?.match_id);
        const version = normalizeVersion(row?.data_version);
        const key = `${matchId}\u0000${version}`;
        if (seen.has(key)) {
            throw new Error(`RAW_MATCH_DATA_DUPLICATE_VERSION: duplicate match_id,data_version ${matchId},${version}`);
        }
        seen.add(key);
    }
}

function selectCanonicalRawMatchData({
    rows = [],
    allowedVersions = DEFAULT_CANONICAL_VERSION_PRIORITY,
    versionPriority = DEFAULT_CANONICAL_VERSION_PRIORITY,
    excludeSyntheticUnknown = true,
} = {}) {
    const safeRows = Array.isArray(rows) ? rows : [];
    assertNoDuplicateMatchVersion(safeRows);

    const candidates = filterRowsByAllowedVersions({
        rows: safeRows,
        allowedVersions,
        excludeSyntheticUnknown,
    });
    if (candidates.length === 0) {
        return null;
    }

    for (const version of versionPriority || []) {
        const normalizedVersion = normalizeVersion(version);
        const versionRows = candidates.filter(row => normalizeVersion(row?.data_version) === normalizedVersion);
        if (versionRows.length > 1) {
            throw new Error(`RAW_MATCH_DATA_DUPLICATE_VERSION: duplicate data_version ${normalizedVersion}`);
        }
        if (versionRows.length === 1) {
            return versionRows[0];
        }
    }

    return null;
}

function requireSingleVersionRow(rowsOrOptions = [], maybeOptions = {}) {
    const options = Array.isArray(rowsOrOptions) ? { ...maybeOptions, rows: rowsOrOptions } : rowsOrOptions || {};
    const rows = Array.isArray(options.rows) ? options.rows : [];
    const expectedMatchId = normalizeText(options.expectedMatchId);
    const expectedDataVersion = normalizeVersion(options.expectedDataVersion);

    if (rows.length === 0) {
        return {
            found: false,
            row: null,
            rows: 0,
        };
    }
    if (rows.length > 1) {
        throw new Error(`RAW_MATCH_DATA_VERSION_LOOKUP_DUPLICATE: expected <=1 row, got ${rows.length}`);
    }

    const row = rows[0];
    const rowMatchId = normalizeText(row?.match_id);
    const rowDataVersion = normalizeVersion(row?.data_version);
    if (expectedMatchId && rowMatchId !== expectedMatchId) {
        throw new Error(
            `RAW_MATCH_DATA_VERSION_LOOKUP_MISMATCH: expected match_id ${expectedMatchId}, got ${rowMatchId}`
        );
    }
    if (expectedDataVersion && rowDataVersion !== expectedDataVersion) {
        throw new Error(
            `RAW_MATCH_DATA_VERSION_LOOKUP_MISMATCH: expected data_version ${expectedDataVersion}, got ${rowDataVersion}`
        );
    }

    return {
        found: true,
        row,
        rows: 1,
    };
}

function buildVersionAwareLookupSpec({ table = 'raw_match_data', matchIdParam = '$1', dataVersionParam = '$2' } = {}) {
    return {
        table,
        where: `match_id = ${matchIdParam} AND data_version = ${dataVersionParam}`,
        order_by: 'collected_at DESC NULLS LAST, id DESC',
        conflict_target: ['match_id', 'data_version'],
        conflict_target_sql: '(match_id, data_version)',
        select_columns: ['id', 'match_id', 'external_id', 'collected_at', 'data_version', 'data_hash'],
    };
}

module.exports = {
    RAW_MATCH_DATA_VERSIONS,
    DEFAULT_CANONICAL_VERSION_PRIORITY,
    classifyRawDataVersion,
    isCanonicalFotMobVersion,
    isSyntheticOrUnknownVersion,
    filterRowsByAllowedVersions,
    selectCanonicalRawMatchData,
    requireSingleVersionRow,
    buildVersionAwareLookupSpec,
};
