#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: FotMob L2 pending transition preview only

const PHASE = 'FOTMOB_L2_PENDING_TRANSITION_PREVIEW';
const CONTRACT_CARRIER = 'matches + pipeline_status';
const PREVIEW_TRANSITION = 'pending -> processing';
const DATA_VERSION = 'fotmob_live_v1';
const DEFAULT_LIMIT = 3;
const MAX_LIMIT = 10;
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';

const PREVIEW_ROWS_SQL = `
WITH pending_scope AS (
    SELECT
        m.match_id,
        NULLIF(BTRIM(m.external_id), '') AS normalized_external_id,
        m.external_id,
        m.league_name,
        m.season,
        m.home_team,
        m.away_team,
        m.match_date,
        m.status,
        COALESCE(m.pipeline_status, 'pending') AS pipeline_status,
        LOWER(COALESCE(m.status, '')) AS normalized_status,
        EXISTS (
            SELECT 1
            FROM raw_match_data r
            WHERE r.match_id = m.match_id
              AND r.data_version = $1
        ) AS raw_exists
    FROM matches m
    WHERE COALESCE(m.pipeline_status, 'pending') = 'pending'
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
    status,
    pipeline_status,
    normalized_external_id,
    normalized_status,
    raw_exists
FROM pending_scope
ORDER BY match_date ASC NULLS LAST, match_id ASC
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_pending_transition_preview.js [--limit 3] [--json] [--league "Premier League"] [--season "2025/2026"] [--status finished]',
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

    if (!allowed) {
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

function buildQueryBundle(options = {}) {
    const baseFilters = buildBaseFilters(options, 2);
    const filterSql = baseFilters.sql || '';

    return {
        rows: {
            sql: PREVIEW_ROWS_SQL.replace('__BASE_FILTERS__', filterSql),
            params: [DATA_VERSION, ...baseFilters.params],
        },
    };
}

function toIsoOrNull(value) {
    if (!value) {
        return null;
    }

    const date = value instanceof Date ? value : new Date(value);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function normalizeStatus(value) {
    return String(value || '').trim().toLowerCase();
}

function hasExternalId(row = {}) {
    return Boolean(String(row.normalized_external_id || row.external_id || '').trim());
}

function classifyRow(row = {}) {
    if (!hasExternalId(row)) {
        return {
            preview_decision: 'excluded',
            preview_reason: 'missing_external_id',
        };
    }

    if (row.raw_exists === true) {
        return {
            preview_decision: 'anomaly',
            preview_reason: 'raw_exists_for_fotmob_live_v1_but_pipeline_status_pending',
        };
    }

    if (normalizeStatus(row.normalized_status || row.status) !== 'finished') {
        return {
            preview_decision: 'caution',
            preview_reason: 'non_finished_pending',
        };
    }

    return {
        preview_decision: 'would_claim',
        preview_reason: 'pending_with_external_id_and_no_fotmob_live_v1_raw',
    };
}

function mapPreviewRow(row = {}) {
    const classification = classifyRow(row);

    return {
        match_id: row.match_id,
        external_id: row.external_id,
        league_name: row.league_name,
        season: row.season,
        home_team: row.home_team,
        away_team: row.away_team,
        match_date: toIsoOrNull(row.match_date),
        status: row.status,
        pipeline_status: row.pipeline_status,
        raw_exists: row.raw_exists === true,
        preview_decision: classification.preview_decision,
        preview_reason: classification.preview_reason,
    };
}

function takeSample(rows = [], limit = DEFAULT_LIMIT) {
    return rows.slice(0, limit).map(mapPreviewRow);
}

function buildSummary(rows = [], limit = DEFAULT_LIMIT) {
    const pendingWithExternalIdRows = rows.filter(row => hasExternalId(row));
    const wouldClaimRows = rows.filter(row => classifyRow(row).preview_decision === 'would_claim');
    const anomalyRows = rows.filter(
        row => classifyRow(row).preview_reason === 'raw_exists_for_fotmob_live_v1_but_pipeline_status_pending'
    );
    const missingExternalIdRows = rows.filter(
        row => classifyRow(row).preview_reason === 'missing_external_id'
    );
    const nonFinishedRows = rows.filter(
        row => classifyRow(row).preview_reason === 'non_finished_pending'
    );

    return {
        summary: {
            pending_with_external_id: pendingWithExternalIdRows.length,
            would_claim_count: wouldClaimRows.length,
            anomaly_raw_exists_but_pending_count: anomalyRows.length,
            missing_external_id_count: missingExternalIdRows.length,
            non_finished_pending_count: nonFinishedRows.length,
        },
        would_claim_sample: takeSample(wouldClaimRows, limit),
        anomaly_sample: takeSample(anomalyRows, limit),
        non_finished_sample: takeSample(nonFinishedRows, limit),
        missing_external_id_sample: takeSample(missingExternalIdRows, limit),
    };
}

function buildPayload(options = {}, rows = []) {
    const preview = buildSummary(rows, options.limit);

    return {
        phase: PHASE,
        contract_carrier: CONTRACT_CARRIER,
        preview_transition: PREVIEW_TRANSITION,
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
        },
        summary: preview.summary,
        would_claim_sample: preview.would_claim_sample,
        anomaly_sample: preview.anomaly_sample,
        non_finished_sample: preview.non_finished_sample,
        missing_external_id_sample: preview.missing_external_id_sample,
    };
}

async function runTransitionPreview(options = {}, dependencies = {}) {
    const queryBundle = buildQueryBundle(options);
    const connection = await openReadOnlyClient(dependencies);
    let rolledBack = false;

    try {
        await querySelectOnly(connection.client, READ_ONLY_BEGIN_SQL);
        const rowsResult = await querySelectOnly(connection.client, queryBundle.rows.sql, queryBundle.rows.params);
        await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
        rolledBack = true;

        return buildPayload(options, rowsResult.rows || []);
    } finally {
        if (!rolledBack) {
            try {
                await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
            } catch {
                // keep original error
            }
        }
        await connection.close();
    }
}

function formatSampleSection(title, rows = []) {
    if (!rows.length) {
        return [`${title}: none`];
    }

    return [
        `${title}:`,
        ...rows.map((row, index) => [
            `  ${index + 1}. ${row.match_id} | external_id=${row.external_id} | raw_exists=${row.raw_exists}`,
            `     ${row.league_name || 'UNKNOWN_LEAGUE'} | ${row.season || 'UNKNOWN_SEASON'} | ${row.home_team || 'UNKNOWN_HOME'} vs ${row.away_team || 'UNKNOWN_AWAY'}`,
            `     match_date=${row.match_date || 'null'} | status=${row.status || 'unknown'} | pipeline_status=${row.pipeline_status || 'unknown'}`,
            `     preview_decision=${row.preview_decision} | preview_reason=${row.preview_reason}`,
        ].join('\n')),
    ];
}

function payloadToText(payload) {
    return [
        '[DRY-RUN] FotMob L2 pending transition preview',
        `Contract carrier: ${payload.contract_carrier}`,
        `Preview transition: ${payload.preview_transition}`,
        'Safety:',
        `  live_fetch_allowed: ${payload.safety.live_fetch_allowed}`,
        `  db_write_allowed: ${payload.safety.db_write_allowed}`,
        `  raw_match_data_write_allowed: ${payload.safety.raw_match_data_write_allowed}`,
        `  pipeline_status_update_allowed: ${payload.safety.pipeline_status_update_allowed}`,
        `  read_only_transaction_used: ${payload.safety.read_only_transaction_used}`,
        '',
        'Summary:',
        `  pending_with_external_id: ${payload.summary.pending_with_external_id}`,
        `  would_claim_count: ${payload.summary.would_claim_count}`,
        `  anomaly_raw_exists_but_pending_count: ${payload.summary.anomaly_raw_exists_but_pending_count}`,
        `  missing_external_id_count: ${payload.summary.missing_external_id_count}`,
        `  non_finished_pending_count: ${payload.summary.non_finished_pending_count}`,
        '',
        ...formatSampleSection('Would-claim sample', payload.would_claim_sample),
        '',
        ...formatSampleSection('Anomaly sample', payload.anomaly_sample),
        '',
        ...formatSampleSection('Non-finished sample', payload.non_finished_sample),
    ].join('\n');
}

function buildFailurePayload(error, options = {}) {
    return {
        phase: PHASE,
        contract_carrier: CONTRACT_CARRIER,
        preview_transition: PREVIEW_TRANSITION,
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

        const payload = await runTransitionPreview(options);
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
    PREVIEW_TRANSITION,
    DATA_VERSION,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    PREVIEW_ROWS_SQL,
    parseArgs,
    buildDbConfig,
    buildBaseFilters,
    buildQueryBundle,
    assertSelectOnlySql,
    querySelectOnly,
    classifyRow,
    mapPreviewRow,
    buildSummary,
    buildPayload,
    runTransitionPreview,
    payloadToText,
    buildFailurePayload,
    main,
};
