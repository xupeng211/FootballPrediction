#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: FotMob L2 pending target selection dry-run only

const PHASE = 'FOTMOB_L2_PENDING_TARGET_SELECTION_DRY_RUN';
const CONTRACT_CARRIER = 'matches + pipeline_status';
const DEFAULT_SAMPLE_LIMIT = 10;
const MAX_SAMPLE_LIMIT = 10;
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';

const SUMMARY_SQL = `
WITH scoped_matches AS (
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
        COALESCE(m.pipeline_status, 'pending') AS pipeline_status
    FROM matches m
    WHERE 1 = 1
      __BASE_FILTERS__
)
SELECT
    COUNT(*) FILTER (WHERE pipeline_status = 'pending') AS total_pending_candidates,
    COUNT(*) FILTER (
        WHERE pipeline_status = 'pending'
          AND normalized_external_id IS NULL
    ) AS missing_external_id_count,
    COUNT(*) FILTER (
        WHERE normalized_external_id IS NOT NULL
          AND pipeline_status = ANY($1::text[])
    ) AS selected_count,
    COUNT(*) FILTER (WHERE pipeline_status = 'processing') AS already_processing_count,
    COUNT(*) FILTER (WHERE pipeline_status = 'harvested') AS already_harvested_count,
    COUNT(*) FILTER (WHERE pipeline_status = 'failed') AS failed_count,
    COUNT(*) FILTER (WHERE pipeline_status = 'skipped') AS skipped_count,
    MIN(match_date) FILTER (
        WHERE normalized_external_id IS NOT NULL
          AND pipeline_status = ANY($1::text[])
    ) AS oldest_match_date,
    MAX(match_date) FILTER (
        WHERE normalized_external_id IS NOT NULL
          AND pipeline_status = ANY($1::text[])
    ) AS newest_match_date
FROM scoped_matches
`;

const BY_LEAGUE_SQL = `
WITH scoped_matches AS (
    SELECT
        NULLIF(BTRIM(m.external_id), '') AS normalized_external_id,
        m.league_name,
        COALESCE(m.pipeline_status, 'pending') AS pipeline_status
    FROM matches m
    WHERE 1 = 1
      __BASE_FILTERS__
)
SELECT
    COALESCE(NULLIF(BTRIM(league_name), ''), 'UNKNOWN_LEAGUE') AS league_name,
    COUNT(*) AS match_count
FROM scoped_matches
WHERE normalized_external_id IS NOT NULL
  AND pipeline_status = ANY($1::text[])
GROUP BY COALESCE(NULLIF(BTRIM(league_name), ''), 'UNKNOWN_LEAGUE')
ORDER BY match_count DESC, league_name ASC
`;

const BY_SEASON_SQL = `
WITH scoped_matches AS (
    SELECT
        NULLIF(BTRIM(m.external_id), '') AS normalized_external_id,
        m.season,
        COALESCE(m.pipeline_status, 'pending') AS pipeline_status
    FROM matches m
    WHERE 1 = 1
      __BASE_FILTERS__
)
SELECT
    COALESCE(NULLIF(BTRIM(season), ''), 'UNKNOWN_SEASON') AS season,
    COUNT(*) AS match_count
FROM scoped_matches
WHERE normalized_external_id IS NOT NULL
  AND pipeline_status = ANY($1::text[])
GROUP BY COALESCE(NULLIF(BTRIM(season), ''), 'UNKNOWN_SEASON')
ORDER BY match_count DESC, season ASC
`;

const SAMPLE_SQL = `
WITH scoped_matches AS (
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
        COALESCE(m.pipeline_status, 'pending') AS pipeline_status
    FROM matches m
    WHERE 1 = 1
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
    pipeline_status
FROM scoped_matches
WHERE normalized_external_id IS NOT NULL
  AND pipeline_status = ANY($1::text[])
ORDER BY match_date ASC NULLS LAST, match_id ASC
LIMIT $2
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_pending_target_selection_dry_run.js [--limit 10] [--league "Premier League"] [--season "2025/2026"] [--status finished] [--include-failed] [--json]',
        '',
        'Safety:',
        '  DRY-RUN / read-only only.',
        '  SQL is limited to BEGIN READ ONLY, SELECT, and ROLLBACK.',
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

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        limit: DEFAULT_SAMPLE_LIMIT,
        league: null,
        season: null,
        status: null,
        includeFailed: false,
        json: false,
        help: false,
    };

    const keyMap = {
        limit: 'limit',
        league: 'league',
        season: 'season',
        status: 'status',
        'include-failed': 'includeFailed',
        include_failed: 'includeFailed',
        json: 'json',
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

        if (['includeFailed', 'json', 'help'].includes(optionKey)) {
            options[optionKey] = normalizeBooleanFlag(value, true);
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : String(value).trim();
    }

    const parsedLimit = parseInteger(options.limit, DEFAULT_SAMPLE_LIMIT);
    if (!Number.isInteger(parsedLimit) || parsedLimit <= 0) {
        throw new Error(`Invalid --limit value: ${options.limit}`);
    }

    options.limit = Math.min(parsedLimit, MAX_SAMPLE_LIMIT);
    options.league = normalizeOptionalText(options.league);
    options.season = normalizeOptionalText(options.season);
    options.status = normalizeOptionalText(options.status)?.toLowerCase() || null;

    return options;
}

function normalizeOptionalText(value) {
    const normalized = String(value || '').trim();
    return normalized ? normalized : null;
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

function buildSelectionStatuses(options = {}) {
    return options.includeFailed ? ['pending', 'failed'] : ['pending'];
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
    const selectionStatuses = buildSelectionStatuses(options);
    const baseFilters = buildBaseFilters(options, 2);
    const filterSql = baseFilters.sql || '';

    return {
        selectionStatuses,
        summary: {
            sql: SUMMARY_SQL.replace('__BASE_FILTERS__', filterSql),
            params: [selectionStatuses, ...baseFilters.params],
        },
        byLeague: {
            sql: BY_LEAGUE_SQL.replace('__BASE_FILTERS__', filterSql),
            params: [selectionStatuses, ...baseFilters.params],
        },
        bySeason: {
            sql: BY_SEASON_SQL.replace('__BASE_FILTERS__', filterSql),
            params: [selectionStatuses, ...baseFilters.params],
        },
        sample: {
            sql: SAMPLE_SQL.replace('__BASE_FILTERS__', filterSql),
            params: [selectionStatuses, options.limit, ...baseFilters.params],
        },
    };
}

function toNumber(value) {
    return Number.parseInt(String(value || '0'), 10) || 0;
}

function toIsoOrNull(value) {
    if (!value) {
        return null;
    }

    const date = value instanceof Date ? value : new Date(value);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function mapSampleTarget(row) {
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
    };
}

function mapCountRows(rows, keyField) {
    return (rows || []).map(row => ({
        [keyField]: row[keyField],
        match_count: toNumber(row.match_count),
    }));
}

function buildSelectionRule(options = {}) {
    const rules = [
        'external_id IS NOT NULL',
        `pipeline_status IN (${buildSelectionStatuses(options).join(', ')})`,
    ];

    if (options.league) {
        rules.push(`league_name ILIKE %${options.league}%`);
    }
    if (options.season) {
        rules.push(`season = ${options.season}`);
    }
    if (options.status) {
        rules.push(`status = ${options.status}`);
    }

    return rules;
}

function buildPayload(options, queryBundle, summaryRow, byLeagueRows, bySeasonRows, sampleRows) {
    return {
        phase: PHASE,
        dry_run: true,
        read_only: true,
        contract_carrier: CONTRACT_CARRIER,
        selection_statuses: queryBundle.selectionStatuses,
        selection_rule: buildSelectionRule(options),
        sample_limit: options.limit,
        filters: {
            league: options.league,
            season: options.season,
            status: options.status,
            include_failed: options.includeFailed,
        },
        total_pending_candidates: toNumber(summaryRow.total_pending_candidates),
        selected_count: toNumber(summaryRow.selected_count),
        missing_external_id_count: toNumber(summaryRow.missing_external_id_count),
        already_processing_count: toNumber(summaryRow.already_processing_count),
        already_harvested_count: toNumber(summaryRow.already_harvested_count),
        failed_count: toNumber(summaryRow.failed_count),
        skipped_count: toNumber(summaryRow.skipped_count),
        by_league: mapCountRows(byLeagueRows, 'league_name'),
        by_season: mapCountRows(bySeasonRows, 'season'),
        oldest_match_date: toIsoOrNull(summaryRow.oldest_match_date),
        newest_match_date: toIsoOrNull(summaryRow.newest_match_date),
        sample_targets: (sampleRows || []).map(mapSampleTarget),
        safety: {
            db_write_allowed: false,
            raw_match_data_write_allowed: false,
            live_fetch_allowed: false,
            browser_allowed: false,
            parser_change_in_scope: false,
            schema_change_in_scope: false,
            read_only_transaction_used: true,
        },
    };
}

async function runSelectionDryRun(options = {}, dependencies = {}) {
    const queryBundle = buildQueryBundle(options);
    const connection = await openReadOnlyClient(dependencies);
    let rolledBack = false;

    try {
        await querySelectOnly(connection.client, READ_ONLY_BEGIN_SQL);

        const summaryResult = await querySelectOnly(
            connection.client,
            queryBundle.summary.sql,
            queryBundle.summary.params
        );
        const byLeagueResult = await querySelectOnly(
            connection.client,
            queryBundle.byLeague.sql,
            queryBundle.byLeague.params
        );
        const bySeasonResult = await querySelectOnly(
            connection.client,
            queryBundle.bySeason.sql,
            queryBundle.bySeason.params
        );
        const sampleResult = await querySelectOnly(
            connection.client,
            queryBundle.sample.sql,
            queryBundle.sample.params
        );

        await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
        rolledBack = true;

        return buildPayload(
            options,
            queryBundle,
            summaryResult.rows?.[0] || {},
            byLeagueResult.rows || [],
            bySeasonResult.rows || [],
            sampleResult.rows || []
        );
    } finally {
        if (!rolledBack) {
            try {
                await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
            } catch {
                // keep the original error
            }
        }
        await connection.close();
    }
}

function formatCountLines(payload) {
    return [
        `  total_pending_candidates: ${payload.total_pending_candidates}`,
        `  selected_count: ${payload.selected_count}`,
        `  missing_external_id_count: ${payload.missing_external_id_count}`,
        `  already_processing_count: ${payload.already_processing_count}`,
        `  already_harvested_count: ${payload.already_harvested_count}`,
        `  failed_count: ${payload.failed_count}`,
        `  skipped_count: ${payload.skipped_count}`,
        `  oldest_match_date: ${payload.oldest_match_date || 'null'}`,
        `  newest_match_date: ${payload.newest_match_date || 'null'}`,
    ];
}

function formatGroupedCounts(label, rows, keyField) {
    if (!rows.length) {
        return [`${label}: none`];
    }

    return [
        `${label}:`,
        ...rows.map(row => `  ${row[keyField]}: ${row.match_count}`),
    ];
}

function formatSampleTargets(sampleTargets) {
    if (!sampleTargets.length) {
        return ['Sample targets:', '  none'];
    }

    return [
        'Sample targets:',
        ...sampleTargets.map((target, index) => {
            const fixture = `${target.home_team || 'UNKNOWN_HOME'} vs ${target.away_team || 'UNKNOWN_AWAY'}`;
            return [
                `  ${index + 1}. ${target.match_id} | external_id=${target.external_id}`,
                `     ${target.league_name || 'UNKNOWN_LEAGUE'} | ${target.season || 'UNKNOWN_SEASON'} | ${fixture}`,
                `     match_date=${target.match_date || 'null'} | status=${target.status || 'unknown'} | pipeline_status=${target.pipeline_status || 'unknown'}`,
            ].join('\n');
        }),
    ];
}

function payloadToText(payload) {
    return [
        '[DRY-RUN] FotMob L2 pending target selection',
        `Phase: ${payload.phase}`,
        `Contract carrier: ${payload.contract_carrier}`,
        'Selection rule:',
        ...payload.selection_rule.map(rule => `  ${rule}`),
        '',
        'Summary:',
        ...formatCountLines(payload),
        '',
        ...formatGroupedCounts('By league', payload.by_league, 'league_name'),
        '',
        ...formatGroupedCounts('By season', payload.by_season, 'season'),
        '',
        ...formatSampleTargets(payload.sample_targets),
    ].join('\n');
}

function writePayload(payload, json, io) {
    const output = json
        ? `${JSON.stringify(payload, null, 2)}\n`
        : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

function buildFailurePayload(error, options = {}) {
    return {
        phase: PHASE,
        dry_run: true,
        read_only: true,
        contract_carrier: CONTRACT_CARRIER,
        selection_statuses: buildSelectionStatuses(options),
        selection_rule: buildSelectionRule(options),
        sample_limit: options.limit || DEFAULT_SAMPLE_LIMIT,
        filters: {
            league: options.league || null,
            season: options.season || null,
            status: options.status || null,
            include_failed: options.includeFailed === true,
        },
        errors: [error.message],
        safety: {
            db_write_allowed: false,
            raw_match_data_write_allowed: false,
            live_fetch_allowed: false,
            browser_allowed: false,
            parser_change_in_scope: false,
            schema_change_in_scope: false,
            read_only_transaction_used: true,
        },
    };
}

async function main(argv = process.argv.slice(2), io = {}) {
    const output = {
        stdout: io.stdout || (text => process.stdout.write(text)),
        stderr: io.stderr || (text => process.stderr.write(text)),
    };

    let options = {
        limit: DEFAULT_SAMPLE_LIMIT,
        includeFailed: false,
        json: false,
    };

    try {
        options = parseArgs(argv);
        if (options.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }

        const payload = await runSelectionDryRun(options);
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
    DEFAULT_SAMPLE_LIMIT,
    MAX_SAMPLE_LIMIT,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    SUMMARY_SQL,
    BY_LEAGUE_SQL,
    BY_SEASON_SQL,
    SAMPLE_SQL,
    parseArgs,
    buildDbConfig,
    buildSelectionStatuses,
    buildBaseFilters,
    buildQueryBundle,
    assertSelectOnlySql,
    querySelectOnly,
    runSelectionDryRun,
    payloadToText,
    buildFailurePayload,
    main,
};
