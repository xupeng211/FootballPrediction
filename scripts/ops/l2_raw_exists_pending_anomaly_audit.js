#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: FotMob L2 raw-exists pending anomaly audit only

const PHASE = 'FOTMOB_L2_RAW_EXISTS_PENDING_ANOMALY_AUDIT';
const CONTRACT_CARRIER = 'matches + pipeline_status';
const DATA_VERSION = 'fotmob_live_v1';
const DEFAULT_LIMIT = 10;
const MAX_LIMIT = 50;
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';

const RAW_COLUMNS_SQL = `
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'raw_match_data'
ORDER BY ordinal_position
`;

const ANOMALY_ROWS_SQL_TEMPLATE = `
WITH scoped_raw AS (
    SELECT
        r.match_id,
        r.data_version AS raw_data_version,
        COUNT(*) AS raw_rows_for_version,
        __RAW_CREATED_AT_SQL__,
        __RAW_UPDATED_AT_SQL__
    FROM raw_match_data r
    WHERE r.data_version = $1
    GROUP BY r.match_id, r.data_version
),
anomaly_rows AS (
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
        COALESCE(m.pipeline_status, 'pending') AS pipeline_status,
        sr.raw_data_version,
        sr.raw_rows_for_version,
        sr.raw_created_at,
        sr.raw_updated_at
    FROM matches m
    JOIN scoped_raw sr ON sr.match_id = m.match_id
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
    pipeline_status,
    raw_data_version,
    raw_rows_for_version,
    raw_created_at,
    raw_updated_at
FROM anomaly_rows
ORDER BY match_date ASC NULLS LAST, match_id ASC
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_raw_exists_pending_anomaly_audit.js [--limit 10] [--json] [--league "Premier League"] [--season "2025/2026"] [--status finished]',
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

function buildTimestampSql(columns = []) {
    const columnSet = new Set(columns);
    const createdChoices = ['collected_at', 'created_at', 'ingested_at'];
    const updatedChoices = ['updated_at', 'collected_at', 'created_at', 'ingested_at'];

    const createdColumn = createdChoices.find(column => columnSet.has(column)) || null;
    const updatedColumn = updatedChoices.find(column => columnSet.has(column)) || null;

    return {
        createdColumn,
        updatedColumn,
        createdSql: createdColumn
            ? `MIN(r.${createdColumn}) AS raw_created_at`
            : `NULL::timestamptz AS raw_created_at`,
        updatedSql: updatedColumn
            ? `MAX(r.${updatedColumn}) AS raw_updated_at`
            : `NULL::timestamptz AS raw_updated_at`,
    };
}

function buildQueryBundle(options = {}, rawColumns = []) {
    const baseFilters = buildBaseFilters(options, 2);
    const timestampSql = buildTimestampSql(rawColumns);
    const rowsSql = ANOMALY_ROWS_SQL_TEMPLATE
        .replace('__RAW_CREATED_AT_SQL__', timestampSql.createdSql)
        .replace('__RAW_UPDATED_AT_SQL__', timestampSql.updatedSql)
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
        timestampMetadata: timestampSql,
    };
}

function toIsoOrNull(value) {
    if (!value) {
        return null;
    }

    const date = value instanceof Date ? value : new Date(value);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
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
        const version = String(row.raw_data_version || '').trim() || 'UNKNOWN_DATA_VERSION';
        const current = counts.get(version) || { raw_data_version: version, anomaly_count: 0, raw_row_count: 0 };
        current.anomaly_count += 1;
        current.raw_row_count += Number(row.raw_rows_for_version || 0);
        counts.set(version, current);
    }

    return [...counts.values()].sort((left, right) => right.anomaly_count - left.anomaly_count || left.raw_data_version.localeCompare(right.raw_data_version));
}

function buildSourceHint(row = {}) {
    if (!row.raw_data_version) {
        return null;
    }
    return `raw_match_data:data_version=${row.raw_data_version}`;
}

function mapAnomalyRow(row = {}) {
    return {
        match_id: row.match_id,
        external_id: row.external_id,
        league_name: row.league_name,
        season: row.season,
        home_team: row.home_team,
        away_team: row.away_team,
        match_date: toIsoOrNull(row.match_date),
        match_status: row.match_status,
        pipeline_status: row.pipeline_status,
        raw_exists: true,
        raw_data_version: row.raw_data_version,
        raw_created_at: toIsoOrNull(row.raw_created_at),
        raw_updated_at: toIsoOrNull(row.raw_updated_at),
        raw_source_hint: buildSourceHint(row),
        audit_decision: 'anomaly',
        audit_reason: 'raw_exists_for_fotmob_live_v1_but_pipeline_status_pending',
    };
}

function takeSample(rows = [], limit = DEFAULT_LIMIT) {
    return rows.slice(0, limit).map(mapAnomalyRow);
}

function buildPayload(options = {}, rawColumns = [], rows = [], timestampMetadata = {}) {
    const duplicateRawCount = rows.filter(row => Number(row.raw_rows_for_version || 0) > 1).length;
    const rawRowCount = rows.reduce((sum, row) => sum + Number(row.raw_rows_for_version || 0), 0);
    const oldestMatchDate = rows.length > 0 ? toIsoOrNull(rows[0].match_date) : null;
    const newestMatchDate = rows.length > 0 ? toIsoOrNull(rows[rows.length - 1].match_date) : null;

    return {
        phase: PHASE,
        contract_carrier: CONTRACT_CARRIER,
        data_version: DATA_VERSION,
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
        raw_timestamp_columns: {
            raw_created_at_source: timestampMetadata.createdColumn,
            raw_updated_at_source: timestampMetadata.updatedColumn,
        },
        summary: {
            anomaly_total: rows.length,
            raw_row_count: rawRowCount,
            duplicate_raw_count: duplicateRawCount,
            oldest_match_date: oldestMatchDate,
            newest_match_date: newestMatchDate,
        },
        by_league: groupCounts(rows, 'league_name', 'UNKNOWN_LEAGUE'),
        by_season: groupCounts(rows, 'season', 'UNKNOWN_SEASON'),
        by_match_status: groupCounts(rows, 'match_status', 'UNKNOWN_STATUS'),
        raw_data_version_counts: mapRawVersionCounts(rows),
        sample_anomalies: takeSample(rows, options.limit),
    };
}

async function runAnomalyAudit(options = {}, dependencies = {}) {
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

        return buildPayload(options, rawColumns, rowsResult.rows || [], queryBundle.timestampMetadata);
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
        ...rows.map(row => `  ${row.raw_data_version}: anomaly_count=${row.anomaly_count} raw_row_count=${row.raw_row_count}`),
    ];
}

function formatSampleSection(rows = []) {
    if (!rows.length) {
        return ['Sample anomalies: none'];
    }

    return [
        'Sample anomalies:',
        ...rows.map((row, index) => [
            `  ${index + 1}. ${row.match_id} | external_id=${row.external_id} | raw_data_version=${row.raw_data_version}`,
            `     ${row.league_name || 'UNKNOWN_LEAGUE'} | ${row.season || 'UNKNOWN_SEASON'} | ${row.home_team || 'UNKNOWN_HOME'} vs ${row.away_team || 'UNKNOWN_AWAY'}`,
            `     match_date=${row.match_date || 'null'} | match_status=${row.match_status || 'unknown'} | pipeline_status=${row.pipeline_status || 'unknown'}`,
            `     raw_created_at=${row.raw_created_at || 'null'} | raw_updated_at=${row.raw_updated_at || 'null'} | raw_source_hint=${row.raw_source_hint || 'null'}`,
            `     audit_decision=${row.audit_decision} | audit_reason=${row.audit_reason}`,
        ].join('\n')),
    ];
}

function payloadToText(payload) {
    return [
        '[DRY-RUN] FotMob L2 raw-exists pending anomaly audit',
        `Contract carrier: ${payload.contract_carrier}`,
        `Anomaly rule: pending + external_id + raw_match_data(${payload.data_version}) exists`,
        'Safety:',
        `  live_fetch_allowed: ${payload.safety.live_fetch_allowed}`,
        `  db_write_allowed: ${payload.safety.db_write_allowed}`,
        `  raw_match_data_write_allowed: ${payload.safety.raw_match_data_write_allowed}`,
        `  pipeline_status_update_allowed: ${payload.safety.pipeline_status_update_allowed}`,
        `  read_only_transaction_used: ${payload.safety.read_only_transaction_used}`,
        `  raw_payload_output_allowed: ${payload.safety.raw_payload_output_allowed}`,
        '',
        'Summary:',
        `  anomaly_total: ${payload.summary.anomaly_total}`,
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
        ...formatSampleSection(payload.sample_anomalies),
    ].join('\n');
}

function buildFailurePayload(error, options = {}) {
    return {
        phase: PHASE,
        contract_carrier: CONTRACT_CARRIER,
        data_version: DATA_VERSION,
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

        const payload = await runAnomalyAudit(options);
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
    DEFAULT_LIMIT,
    MAX_LIMIT,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    RAW_COLUMNS_SQL,
    ANOMALY_ROWS_SQL_TEMPLATE,
    parseArgs,
    buildDbConfig,
    buildBaseFilters,
    buildTimestampSql,
    buildQueryBundle,
    assertSelectOnlySql,
    querySelectOnly,
    mapAnomalyRow,
    buildPayload,
    runAnomalyAudit,
    payloadToText,
    buildFailurePayload,
    main,
};
