#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: FotMob L2 reconciliation preview only

const PHASE = 'FOTMOB_L2_RECONCILIATION_PREVIEW';
const CONTRACT_CARRIER = 'matches + pipeline_status';
const DATA_VERSION = 'fotmob_live_v1';
const PREVIEW_TRANSITION = 'pending -> harvested';
const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 58;
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';

const RAW_COLUMNS_SQL = `
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'raw_match_data'
ORDER BY ordinal_position
`;

const PREVIEW_ROWS_SQL_TEMPLATE = `
WITH raw_version_scope AS (
    SELECT
        r.match_id,
        r.data_version AS raw_data_version,
        COUNT(*) AS raw_row_count,
        __RAW_EXTERNAL_ID_SQL__,
        __RAW_EXTERNAL_ID_DISTINCT_SQL__,
        __HAS_RAW_DATA_SQL__,
        __HAS_DATA_HASH_SQL__
    FROM raw_match_data r
    WHERE r.data_version = $1
    GROUP BY r.match_id, r.data_version
),
pending_scope AS (
    SELECT
        m.match_id,
        NULLIF(BTRIM(m.external_id), '') AS normalized_external_id,
        m.external_id,
        m.league_name,
        m.season,
        m.home_team,
        m.away_team,
        m.match_date,
        m.status AS match_status,
        LOWER(COALESCE(m.status, '')) AS normalized_match_status,
        COALESCE(m.pipeline_status, 'pending') AS pipeline_status,
        rvs.raw_data_version,
        COALESCE(rvs.raw_row_count, 0) AS raw_row_count,
        rvs.raw_external_id,
        COALESCE(rvs.raw_external_id_distinct_count, 0) AS raw_external_id_distinct_count,
        rvs.has_raw_data,
        rvs.has_data_hash
    FROM matches m
    LEFT JOIN raw_version_scope rvs ON rvs.match_id = m.match_id
    WHERE COALESCE(m.pipeline_status, 'pending') = 'pending'
      AND NULLIF(BTRIM(m.external_id), '') IS NOT NULL
      __BASE_FILTERS__
)
SELECT
    match_id,
    external_id,
    league_name,
    season,
    home_team,
    away_team,
    match_date,
    match_status,
    normalized_match_status,
    pipeline_status,
    raw_data_version,
    raw_row_count,
    raw_external_id,
    raw_external_id_distinct_count,
    has_raw_data,
    has_data_hash
FROM pending_scope
ORDER BY match_date ASC NULLS LAST, match_id ASC
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_reconciliation_preview.js [--limit 20] [--json] [--league "Premier League"] [--season "2025/2026"] [--status finished]',
        '',
        'Safety:',
        '  DRY-RUN / read-only only.',
        '  SQL is limited to BEGIN READ ONLY, SELECT, WITH, and ROLLBACK.',
        '  No FotMob fetch, no browser, no raw retention, no state change.',
    ].join('\n');
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

function normalizeOptionalText(value) {
    const normalized = String(value || '').trim();
    return normalized ? normalized : null;
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        limit: DEFAULT_LIMIT,
        json: false,
        league: null,
        season: null,
        status: null,
        help: false,
    };

    const keyMap = {
        limit: 'limit',
        json: 'json',
        league: 'league',
        season: 'season',
        status: 'status',
        help: 'help',
        h: 'help',
    };

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            throw new Error(`Unknown argument: ${arg}`);
        }

        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        if (!optionKey) {
            throw new Error(`Unknown option: --${rawKey}`);
        }

        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) {
            index += 1;
        }

        if (['json', 'help'].includes(optionKey)) {
            options[optionKey] = normalizeBooleanFlag(value, true);
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : String(value).trim();
    }

    const parsedLimit = parseInteger(options.limit, DEFAULT_LIMIT);
    if (!Number.isInteger(parsedLimit) || parsedLimit <= 0) {
        throw new Error(`Invalid --limit value: ${options.limit}`);
    }

    options.limit = Math.min(parsedLimit, MAX_LIMIT);
    options.league = normalizeOptionalText(options.league);
    options.season = normalizeOptionalText(options.season);
    options.status = normalizeOptionalText(options.status)?.toLowerCase() || null;

    return options;
}

function buildDbConfig() {
    return {
        host: process.env.DB_HOST || process.env.POSTGRES_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || process.env.POSTGRES_PORT || '5432', 10),
        database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
        user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD,
        max: 1,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000,
    };
}

function createPool(dependencies = {}) {
    if (dependencies.pool) {
        return dependencies.pool;
    }

    const { Pool } = require('pg');
    return new Pool(buildDbConfig());
}

async function openReadOnlyClient(dependencies = {}) {
    if (dependencies.client) {
        return {
            client: dependencies.client,
            close: async () => {},
        };
    }

    const pool = createPool(dependencies);
    const ownsPool = !dependencies.pool;

    if (typeof pool.connect === 'function') {
        const client = await pool.connect();
        return {
            client,
            close: async () => {
                if (typeof client.release === 'function') {
                    client.release();
                }
                if (ownsPool && typeof pool.end === 'function') {
                    await pool.end();
                }
            },
        };
    }

    return {
        client: pool,
        close: async () => {
            if (ownsPool && typeof pool.end === 'function') {
                await pool.end();
            }
        },
    };
}

function buildBlockedTokenPattern() {
    const blockedTokenGroups = [
        ['IN', 'SERT'],
        ['UP', 'DATE'],
        ['UP', 'SERT'],
        ['DELE', 'TE'],
        ['TRUN', 'CATE'],
        ['CRE', 'ATE'],
        ['AL', 'TER'],
        ['DR', 'OP'],
    ];

    const blockedTokens = blockedTokenGroups.map(parts => parts.join(''));
    return new RegExp(`\\b(${blockedTokens.join('|')})\\b`, 'i');
}

function assertSelectOnlySql(sql) {
    const normalized = String(sql || '')
        .replace(/\s+/g, ' ')
        .trim()
        .toUpperCase();

    const allowed =
        normalized === READ_ONLY_BEGIN_SQL ||
        normalized === READ_ONLY_ROLLBACK_SQL ||
        normalized.startsWith('SELECT ') ||
        normalized.startsWith('WITH ');

    if (!allowed || buildBlockedTokenPattern().test(normalized)) {
        throw new Error(`Unsafe SQL rejected by ${PHASE}: ${normalized.slice(0, 80)}`);
    }
}

async function querySelectOnly(client, sql, params = []) {
    assertSelectOnlySql(sql);
    return client.query(sql, params);
}

function buildBaseFilters(options = {}, startIndex = 2) {
    const params = [];
    const conditions = [];
    let parameterIndex = startIndex;

    if (options.league) {
        params.push(`%${options.league}%`);
        conditions.push(`AND m.league_name ILIKE $${parameterIndex}`);
        parameterIndex += 1;
    }

    if (options.season) {
        params.push(options.season);
        conditions.push(`AND m.season = $${parameterIndex}`);
        parameterIndex += 1;
    }

    if (options.status) {
        params.push(options.status);
        conditions.push(`AND LOWER(COALESCE(m.status, '')) = $${parameterIndex}`);
        parameterIndex += 1;
    }

    return {
        sql: conditions.join('\n      '),
        params,
    };
}

function buildRawSignalSql(columns = []) {
    const columnSet = new Set(columns);
    const hasExternalIdColumn = columnSet.has('external_id');
    const hasRawDataColumn = columnSet.has('raw_data');
    const hasDataHashColumn = columnSet.has('data_hash');

    return {
        hasExternalIdColumn,
        hasRawDataColumn,
        hasDataHashColumn,
        rawExternalIdSql: hasExternalIdColumn
            ? `MIN(NULLIF(BTRIM(r.external_id), '')) AS raw_external_id`
            : `NULL::text AS raw_external_id`,
        rawExternalIdDistinctSql: hasExternalIdColumn
            ? `COUNT(DISTINCT NULLIF(BTRIM(r.external_id), '')) AS raw_external_id_distinct_count`
            : `0 AS raw_external_id_distinct_count`,
        hasRawDataSql: hasRawDataColumn
            ? `BOOL_OR(r.raw_data IS NOT NULL) AS has_raw_data`
            : `NULL::boolean AS has_raw_data`,
        hasDataHashSql: hasDataHashColumn
            ? `BOOL_OR(NULLIF(BTRIM(r.data_hash), '') IS NOT NULL) AS has_data_hash`
            : `NULL::boolean AS has_data_hash`,
    };
}

function buildQueryBundle(options = {}, rawColumns = []) {
    const baseFilters = buildBaseFilters(options, 2);
    const rawSignalSql = buildRawSignalSql(rawColumns);
    const rowsSql = PREVIEW_ROWS_SQL_TEMPLATE
        .replace('__RAW_EXTERNAL_ID_SQL__', rawSignalSql.rawExternalIdSql)
        .replace('__RAW_EXTERNAL_ID_DISTINCT_SQL__', rawSignalSql.rawExternalIdDistinctSql)
        .replace('__HAS_RAW_DATA_SQL__', rawSignalSql.hasRawDataSql)
        .replace('__HAS_DATA_HASH_SQL__', rawSignalSql.hasDataHashSql)
        .replace('__BASE_FILTERS__', baseFilters.sql || '');

    return {
        rawColumns: {
            sql: RAW_COLUMNS_SQL,
            params: [],
        },
        rows: {
            sql: rowsSql,
            params: [DATA_VERSION, ...baseFilters.params],
        },
        rawSignalMetadata: rawSignalSql,
    };
}

function normalizeText(value) {
    const normalized = String(value || '').trim();
    return normalized ? normalized : null;
}

function toIsoOrNull(value) {
    if (!value) {
        return null;
    }

    const date = value instanceof Date ? value : new Date(value);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function classifyRow(row = {}) {
    const pipelineStatus = normalizeText(row.pipeline_status)?.toLowerCase() || 'pending';
    const matchStatus = normalizeText(row.match_status)?.toLowerCase() || null;
    const externalId = normalizeText(row.external_id);
    const rawExternalId = normalizeText(row.raw_external_id);
    const rawRowCount = Number(row.raw_row_count || 0);
    const rawExists = rawRowCount > 0;
    const hasRawData = row.has_raw_data === true;
    const hasDataHash = row.has_data_hash === true;

    if (pipelineStatus !== 'pending') {
        return {
            reconciliation_decision: 'excluded_not_pending',
            reconciliation_reason: 'pipeline_status_not_pending',
        };
    }

    if (!rawExists) {
        return {
            reconciliation_decision: 'excluded_no_raw',
            reconciliation_reason: 'pending_without_fotmob_live_v1_raw',
        };
    }

    if (rawRowCount > 1) {
        return {
            reconciliation_decision: 'hold_duplicate_raw',
            reconciliation_reason: 'duplicate_fotmob_live_v1_raw_rows',
        };
    }

    if (matchStatus !== 'finished') {
        return {
            reconciliation_decision: 'hold_non_finished',
            reconciliation_reason: 'match_status_not_finished',
        };
    }

    if (externalId && rawExternalId && externalId !== rawExternalId) {
        return {
            reconciliation_decision: 'hold_external_id_mismatch',
            reconciliation_reason: 'external_id_mismatch_between_matches_and_raw',
        };
    }

    if (hasRawData !== true || hasDataHash !== true) {
        return {
            reconciliation_decision: 'hold_missing_hash_or_payload',
            reconciliation_reason: 'missing_raw_data_or_data_hash_signal',
        };
    }

    return {
        reconciliation_decision: 'suggest_harvested',
        reconciliation_reason: 'pending_with_single_fotmob_live_v1_raw_and_finished_status',
    };
}

function mapPreviewRow(row = {}) {
    const classification = classifyRow(row);

    return {
        match_id: row.match_id,
        external_id: row.external_id,
        raw_external_id: normalizeText(row.raw_external_id),
        league_name: row.league_name,
        season: row.season,
        home_team: row.home_team,
        away_team: row.away_team,
        match_date: toIsoOrNull(row.match_date),
        match_status: row.match_status,
        pipeline_status: row.pipeline_status,
        raw_data_version: row.raw_data_version,
        raw_row_count: Number(row.raw_row_count || 0),
        has_raw_data: row.has_raw_data === true,
        has_data_hash: row.has_data_hash === true,
        reconciliation_decision: classification.reconciliation_decision,
        reconciliation_reason: classification.reconciliation_reason,
    };
}

function groupCounts(rows = [], keyName, fallbackLabel) {
    const counts = new Map();

    for (const row of rows) {
        const rawValue = row[keyName];
        const normalized = String(rawValue || '').trim() || fallbackLabel;
        counts.set(normalized, (counts.get(normalized) || 0) + 1);
    }

    return [...counts.entries()]
        .map(([label, count]) => ({ [keyName]: label, count }))
        .sort((left, right) => right.count - left.count || String(left[keyName]).localeCompare(String(right[keyName])));
}

function mapRawVersionCounts(rows = []) {
    const counts = new Map();

    for (const row of rows) {
        const version = normalizeText(row.raw_data_version) || 'UNKNOWN_DATA_VERSION';
        const current = counts.get(version) || { raw_data_version: version, candidate_count: 0, raw_row_count: 0 };
        current.candidate_count += 1;
        current.raw_row_count += Number(row.raw_row_count || 0);
        counts.set(version, current);
    }

    return [...counts.values()].sort((left, right) => right.candidate_count - left.candidate_count || left.raw_data_version.localeCompare(right.raw_data_version));
}

function takeClassifiedSample(rows = [], decision, limit = DEFAULT_LIMIT) {
    return rows
        .filter(row => classifyRow(row).reconciliation_decision === decision)
        .slice(0, limit)
        .map(mapPreviewRow);
}

function takeHoldSample(rows = [], limit = DEFAULT_LIMIT) {
    return rows
        .filter(row => classifyRow(row).reconciliation_decision.startsWith('hold_'))
        .slice(0, limit)
        .map(mapPreviewRow);
}

function buildPayload(options = {}, rawColumns = [], rows = [], rawSignalMetadata = {}) {
    const classifiedRows = rows.map(row => ({
        ...row,
        ...classifyRow(row),
    }));

    const candidateRows = classifiedRows.filter(row => Number(row.raw_row_count || 0) > 0);
    const suggestRows = classifiedRows.filter(row => row.reconciliation_decision === 'suggest_harvested');
    const holdDuplicateRows = classifiedRows.filter(row => row.reconciliation_decision === 'hold_duplicate_raw');
    const holdNonFinishedRows = classifiedRows.filter(row => row.reconciliation_decision === 'hold_non_finished');
    const holdMissingSignalRows = classifiedRows.filter(row => row.reconciliation_decision === 'hold_missing_hash_or_payload');
    const holdExternalMismatchRows = classifiedRows.filter(row => row.reconciliation_decision === 'hold_external_id_mismatch');
    const excludedNoRawRows = classifiedRows.filter(row => row.reconciliation_decision === 'excluded_no_raw');

    const rawRowCount = candidateRows.reduce((sum, row) => sum + Number(row.raw_row_count || 0), 0);
    const duplicateRawCount = candidateRows.filter(row => Number(row.raw_row_count || 0) > 1).length;
    const oldestMatchDate = candidateRows.length > 0 ? toIsoOrNull(candidateRows[0].match_date) : null;
    const newestMatchDate = candidateRows.length > 0 ? toIsoOrNull(candidateRows[candidateRows.length - 1].match_date) : null;

    return {
        phase: PHASE,
        contract_carrier: CONTRACT_CARRIER,
        data_version: DATA_VERSION,
        preview_transition: PREVIEW_TRANSITION,
        filters: {
            league: options.league,
            season: options.season,
            status: options.status,
            sample_limit: options.limit,
        },
        safety: {
            live_fetch_allowed: false,
            db_write_allowed: false,
            raw_match_data_write_allowed: false,
            pipeline_status_update_allowed: false,
            read_only_transaction_used: true,
            raw_payload_output_allowed: false,
        },
        raw_table_columns: rawColumns,
        raw_signal_columns: {
            external_id_available: rawSignalMetadata.hasExternalIdColumn === true,
            raw_data_available: rawSignalMetadata.hasRawDataColumn === true,
            data_hash_available: rawSignalMetadata.hasDataHashColumn === true,
        },
        summary: {
            candidate_total: candidateRows.length,
            suggest_harvested_count: suggestRows.length,
            hold_duplicate_raw_count: holdDuplicateRows.length,
            hold_non_finished_count: holdNonFinishedRows.length,
            hold_missing_hash_or_payload_count: holdMissingSignalRows.length,
            hold_external_id_mismatch_count: holdExternalMismatchRows.length,
            excluded_no_raw_count: excludedNoRawRows.length,
            raw_row_count: rawRowCount,
            duplicate_raw_count: duplicateRawCount,
            oldest_match_date: oldestMatchDate,
            newest_match_date: newestMatchDate,
        },
        by_league: groupCounts(candidateRows, 'league_name', 'UNKNOWN_LEAGUE'),
        by_season: groupCounts(candidateRows, 'season', 'UNKNOWN_SEASON'),
        by_match_status: groupCounts(candidateRows, 'match_status', 'UNKNOWN_STATUS'),
        raw_data_version_counts: mapRawVersionCounts(candidateRows),
        suggest_harvested_sample: takeClassifiedSample(rows, 'suggest_harvested', options.limit),
        hold_sample: takeHoldSample(rows, options.limit),
    };
}

async function runReconciliationPreview(options = {}, dependencies = {}) {
    const connection = await openReadOnlyClient(dependencies);
    let rolledBack = false;

    try {
        await querySelectOnly(connection.client, READ_ONLY_BEGIN_SQL);

        const rawColumnsResult = await querySelectOnly(connection.client, RAW_COLUMNS_SQL);
        const rawColumns = (rawColumnsResult.rows || []).map(row => String(row.column_name || '').trim()).filter(Boolean);
        const queryBundle = buildQueryBundle(options, rawColumns);
        const rowsResult = await querySelectOnly(connection.client, queryBundle.rows.sql, queryBundle.rows.params);

        await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
        rolledBack = true;

        return buildPayload(options, rawColumns, rowsResult.rows || [], queryBundle.rawSignalMetadata);
    } finally {
        if (!rolledBack) {
            try {
                await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
            } catch {
                // preserve original error
            }
        }
        await connection.close();
    }
}

function formatCountSection(title, rows = [], keyName) {
    if (!rows.length) {
        return [`${title}: none`];
    }

    return [
        `${title}:`,
        ...rows.map(row => `  ${row[keyName]}: ${row.count}`),
    ];
}

function formatVersionSection(rows = []) {
    if (!rows.length) {
        return ['Raw data version counts: none'];
    }

    return [
        'Raw data version counts:',
        ...rows.map(row => `  ${row.raw_data_version}: candidate_count=${row.candidate_count} raw_row_count=${row.raw_row_count}`),
    ];
}

function formatSampleSection(title, rows = []) {
    if (!rows.length) {
        return [`${title}: none`];
    }

    return [
        `${title}:`,
        ...rows.map((row, index) => [
            `  ${index + 1}. ${row.match_id} | external_id=${row.external_id} | raw_external_id=${row.raw_external_id || 'null'}`,
            `     ${row.league_name || 'UNKNOWN_LEAGUE'} | ${row.season || 'UNKNOWN_SEASON'} | ${row.home_team || 'UNKNOWN_HOME'} vs ${row.away_team || 'UNKNOWN_AWAY'}`,
            `     match_date=${row.match_date || 'null'} | match_status=${row.match_status || 'unknown'} | pipeline_status=${row.pipeline_status || 'unknown'}`,
            `     raw_data_version=${row.raw_data_version || 'null'} | raw_row_count=${row.raw_row_count} | has_raw_data=${row.has_raw_data} | has_data_hash=${row.has_data_hash}`,
            `     reconciliation_decision=${row.reconciliation_decision} | reconciliation_reason=${row.reconciliation_reason}`,
        ].join('\n')),
    ];
}

function payloadToText(payload) {
    return [
        '[DRY-RUN] FotMob L2 reconciliation preview',
        `Contract carrier: ${payload.contract_carrier}`,
        `Preview transition: ${payload.preview_transition}`,
        'Safety:',
        `  live_fetch_allowed: ${payload.safety.live_fetch_allowed}`,
        `  db_write_allowed: ${payload.safety.db_write_allowed}`,
        `  raw_match_data_write_allowed: ${payload.safety.raw_match_data_write_allowed}`,
        `  pipeline_status_update_allowed: ${payload.safety.pipeline_status_update_allowed}`,
        `  read_only_transaction_used: ${payload.safety.read_only_transaction_used}`,
        `  raw_payload_output_allowed: ${payload.safety.raw_payload_output_allowed}`,
        '',
        'Summary:',
        `  candidate_total: ${payload.summary.candidate_total}`,
        `  suggest_harvested_count: ${payload.summary.suggest_harvested_count}`,
        `  hold_duplicate_raw_count: ${payload.summary.hold_duplicate_raw_count}`,
        `  hold_non_finished_count: ${payload.summary.hold_non_finished_count}`,
        `  hold_missing_hash_or_payload_count: ${payload.summary.hold_missing_hash_or_payload_count}`,
        `  hold_external_id_mismatch_count: ${payload.summary.hold_external_id_mismatch_count}`,
        `  excluded_no_raw_count: ${payload.summary.excluded_no_raw_count}`,
        `  raw_row_count: ${payload.summary.raw_row_count}`,
        `  duplicate_raw_count: ${payload.summary.duplicate_raw_count}`,
        `  oldest_match_date: ${payload.summary.oldest_match_date || 'null'}`,
        `  newest_match_date: ${payload.summary.newest_match_date || 'null'}`,
        '',
        ...formatCountSection('By league', payload.by_league, 'league_name'),
        '',
        ...formatCountSection('By season', payload.by_season, 'season'),
        '',
        ...formatCountSection('By match status', payload.by_match_status, 'match_status'),
        '',
        ...formatVersionSection(payload.raw_data_version_counts),
        '',
        ...formatSampleSection('Suggest harvested sample', payload.suggest_harvested_sample),
        '',
        ...formatSampleSection('Hold sample', payload.hold_sample),
    ].join('\n');
}

function buildFailurePayload(error, options = {}) {
    return {
        phase: PHASE,
        contract_carrier: CONTRACT_CARRIER,
        data_version: DATA_VERSION,
        preview_transition: PREVIEW_TRANSITION,
        filters: {
            league: options.league || null,
            season: options.season || null,
            status: options.status || null,
            sample_limit: options.limit || DEFAULT_LIMIT,
        },
        safety: {
            live_fetch_allowed: false,
            db_write_allowed: false,
            raw_match_data_write_allowed: false,
            pipeline_status_update_allowed: false,
            read_only_transaction_used: true,
            raw_payload_output_allowed: false,
        },
        errors: [error.message],
    };
}

function writePayload(payload, json, io) {
    const output = json
        ? `${JSON.stringify(payload, null, 2)}\n`
        : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

async function main(argv = process.argv.slice(2), io = {}) {
    const output = {
        stdout: io.stdout || (text => process.stdout.write(text)),
        stderr: io.stderr || (text => process.stderr.write(text)),
    };

    let options = {
        limit: DEFAULT_LIMIT,
        json: false,
    };

    try {
        options = parseArgs(argv);
        if (options.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }

        const payload = await runReconciliationPreview(options);
        writePayload(payload, options.json, output);
        return 0;
    } catch (error) {
        const payload = buildFailurePayload(error, options);
        writePayload(payload, options.json === true, output);
        return 1;
    }
}

if (require.main === module) {
    main().then(status => {
        process.exitCode = status;
    });
}

module.exports = {
    PHASE,
    CONTRACT_CARRIER,
    DATA_VERSION,
    PREVIEW_TRANSITION,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    RAW_COLUMNS_SQL,
    PREVIEW_ROWS_SQL_TEMPLATE,
    parseArgs,
    buildDbConfig,
    buildBaseFilters,
    buildRawSignalSql,
    buildQueryBundle,
    assertSelectOnlySql,
    querySelectOnly,
    classifyRow,
    mapPreviewRow,
    buildPayload,
    runReconciliationPreview,
    payloadToText,
    buildFailurePayload,
    main,
};
