#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: FotMob L2 guarded reconciliation write draft only

const PHASE = 'FOTMOB_L2_GUARDED_RECONCILIATION_WRITE_DRAFT';
const CONTRACT_CARRIER = 'matches + pipeline_status';
const DATA_VERSION = 'fotmob_live_v1';
const GUARDED_TRANSITION = 'pending -> harvested';
const DEFAULT_LIMIT = 3;
const MAX_LIMIT = 3;
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const WRITE_BEGIN_SQL = 'BEGIN';
const COMMIT_SQL = 'COMMIT';
const ROLLBACK_SQL = 'ROLLBACK';

const RAW_COLUMNS_SQL = `
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'raw_match_data'
ORDER BY ordinal_position
`;

const MATCHES_COLUMNS_SQL = `
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'matches'
ORDER BY ordinal_position
`;

const CANDIDATE_ROWS_SQL_TEMPLATE = `
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

const GUARDED_UPDATE_SQL = `
UPDATE matches
SET pipeline_status = 'harvested',
    updated_at = NOW()
WHERE match_id = $1
  AND pipeline_status = 'pending'
  AND NULLIF(BTRIM(external_id), '') IS NOT NULL
  AND LOWER(COALESCE(status, '')) = 'finished'
  AND EXISTS (
    SELECT 1
    FROM raw_match_data r
    WHERE r.match_id = matches.match_id
      AND r.data_version = 'fotmob_live_v1'
  )
RETURNING
    match_id,
    external_id,
    pipeline_status AS new_pipeline_status
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_guarded_reconciliation_write.js [--limit 3] [--json] [--league "Premier League"] [--season "2025/2026"] [--status finished] [--expected-count 3] [--allow-write]',
        '',
        'Safety:',
        '  Default mode is DRY-RUN / no-op.',
        '  SQL preview path is limited to BEGIN READ ONLY, SELECT, WITH, and ROLLBACK.',
        '  No FotMob fetch, no browser, no raw retention, no raw payload output.',
        '  Write path exists behind --allow-write but is not executed by default.',
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
        expectedCount: null,
        allowWrite: false,
        help: false,
    };

    const keyMap = {
        limit: 'limit',
        json: 'json',
        league: 'league',
        season: 'season',
        status: 'status',
        'expected-count': 'expectedCount',
        'allow-write': 'allowWrite',
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

        if (['json', 'allowWrite', 'help'].includes(optionKey)) {
            options[optionKey] = normalizeBooleanFlag(value, true);
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : String(value).trim();
    }

    const parsedLimit = parseInteger(options.limit, DEFAULT_LIMIT);
    if (!Number.isInteger(parsedLimit) || parsedLimit <= 0) {
        throw new Error(`Invalid --limit value: ${options.limit}`);
    }

    const parsedExpectedCount = parseInteger(options.expectedCount, null);
    if (options.expectedCount !== null && options.expectedCount !== undefined) {
        if (!Number.isInteger(parsedExpectedCount) || parsedExpectedCount < 0) {
            throw new Error(`Invalid --expected-count value: ${options.expectedCount}`);
        }
    }

    options.limit = Math.min(parsedLimit, MAX_LIMIT);
    options.expectedCount = parsedExpectedCount;
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

async function openClient(dependencies = {}) {
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
        normalized === ROLLBACK_SQL ||
        normalized.startsWith('SELECT ') ||
        normalized.startsWith('WITH ');

    if (!allowed || buildBlockedTokenPattern().test(normalized)) {
        throw new Error(`Unsafe preview SQL rejected by ${PHASE}: ${normalized.slice(0, 80)}`);
    }
}

function assertWriteSql(sql) {
    const normalized = String(sql || '')
        .replace(/\s+/g, ' ')
        .trim();

    const allowed =
        normalized === WRITE_BEGIN_SQL ||
        normalized === COMMIT_SQL ||
        normalized === ROLLBACK_SQL ||
        /^SELECT /i.test(normalized) ||
        /^WITH /i.test(normalized) ||
        /^UPDATE /i.test(normalized);

    if (!allowed || buildBlockedTokenPattern().test(normalized.toUpperCase())) {
        throw new Error(`Unsafe write SQL rejected by ${PHASE}: ${normalized.slice(0, 80)}`);
    }
}

async function querySelectOnly(client, sql, params = []) {
    assertSelectOnlySql(sql);
    return client.query(sql, params);
}

async function queryWriteCapable(client, sql, params = []) {
    assertWriteSql(sql);
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
    const candidateRowsSql = CANDIDATE_ROWS_SQL_TEMPLATE
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
        matchesColumns: {
            sql: MATCHES_COLUMNS_SQL,
            params: [],
        },
        rows: {
            sql: candidateRowsSql,
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

function buildRowState(row = {}) {
    return {
        pipelineStatus: normalizeText(row.pipeline_status)?.toLowerCase() || 'pending',
        matchStatus: normalizeText(row.match_status)?.toLowerCase() || null,
        externalId: normalizeText(row.external_id),
        rawExternalId: normalizeText(row.raw_external_id),
        rawRowCount: Number(row.raw_row_count || 0),
        hasRawData: row.has_raw_data === true,
        hasDataHash: row.has_data_hash === true,
    };
}

function classifyNonPendingStatus(pipelineStatus) {
    const decisionMap = {
        harvested: { decision: 'excluded_status_already_harvested', reason: 'pipeline_status_already_harvested' },
        processing: { decision: 'excluded_status_processing', reason: 'pipeline_status_processing' },
        failed: { decision: 'excluded_status_failed_or_skipped', reason: 'pipeline_status_failed_or_skipped' },
        skipped: { decision: 'excluded_status_failed_or_skipped', reason: 'pipeline_status_failed_or_skipped' },
    };

    return decisionMap[pipelineStatus] || { decision: 'excluded_unknown_pipeline_status', reason: 'unknown_pipeline_status' };
}

function classifyPendingRowState(state) {
    if (state.rawRowCount <= 0) {
        return { decision: 'excluded_no_raw', reason: 'pending_without_fotmob_live_v1_raw' };
    }

    if (state.rawRowCount > 1) {
        return { decision: 'hold_duplicate_raw', reason: 'duplicate_fotmob_live_v1_raw_rows' };
    }

    if (state.matchStatus !== 'finished') {
        return { decision: 'hold_non_finished', reason: 'match_status_not_finished' };
    }

    if (state.externalId && state.rawExternalId && state.externalId !== state.rawExternalId) {
        return { decision: 'hold_external_id_mismatch', reason: 'external_id_mismatch_between_matches_and_raw' };
    }

    if (state.hasRawData !== true || state.hasDataHash !== true) {
        return { decision: 'hold_missing_hash_or_payload', reason: 'missing_raw_data_or_data_hash_signal' };
    }

    return { decision: 'would_update', reason: 'pending_with_single_complete_fotmob_live_v1_raw' };
}

function classifyRow(row = {}) {
    const state = buildRowState(row);
    if (state.pipelineStatus !== 'pending') {
        return classifyNonPendingStatus(state.pipelineStatus);
    }

    return classifyPendingRowState(state);
}

function collectPreviewContext(connectionClient, query, options, rawColumnsResult, matchesColumnsResult) {
    const rawColumns = (rawColumnsResult.rows || []).map(row => String(row.column_name || '').trim()).filter(Boolean);
    const matchesColumns = (matchesColumnsResult.rows || []).map(row => String(row.column_name || '').trim()).filter(Boolean);
    const queryBundle = buildQueryBundle(options, rawColumns);

    return query(connectionClient, queryBundle.rows.sql, queryBundle.rows.params).then(rowsResult => ({
        rawColumns,
        matchesColumns,
        queryBundle,
        rows: rowsResult.rows || [],
    }));
}

async function runDryRunFlow(connectionClient, query, options, context) {
    await query(connectionClient, ROLLBACK_SQL);
    return buildDryRunPayload(
        options,
        context.rows,
        context.rawColumns,
        context.matchesColumns,
        context.queryBundle.rawSignalMetadata,
    );
}

async function runWriteFlow(connectionClient, query, options, context) {
    validateWritePrerequisites(context.matchesColumns);
    const classifiedRows = context.rows.map(row => ({
        ...row,
        ...classifyRow(row),
    }));
    const selectedCandidates = classifiedRows.filter(row => row.decision === 'would_update').slice(0, options.limit);
    validateExpectedCount(options.expectedCount, selectedCandidates.length);

    if (selectedCandidates.length === 0) {
        throw new Error('No guarded reconciliation candidates available for write path');
    }

    const updatedRows = [];
    for (const row of selectedCandidates) {
        const updateResult = await query(connectionClient, GUARDED_UPDATE_SQL, [row.match_id]);
        const returnedRows = updateResult.rows || [];
        if (returnedRows.length !== 1) {
            throw new Error(`Guarded update count mismatch for match_id=${row.match_id}`);
        }
        updatedRows.push({
            match_id: returnedRows[0].match_id,
            external_id: returnedRows[0].external_id,
            new_pipeline_status: returnedRows[0].new_pipeline_status,
        });
    }

    if (updatedRows.length !== selectedCandidates.length) {
        throw new Error(`Updated count ${updatedRows.length} does not match selected count ${selectedCandidates.length}`);
    }

    await query(connectionClient, COMMIT_SQL);
    return buildWritePayload(
        options,
        selectedCandidates,
        updatedRows,
        context.rawColumns,
        context.matchesColumns,
        context.queryBundle.rawSignalMetadata,
    );
}

function mapCandidateRow(row = {}) {
    const classification = classifyRow(row);
    return {
        match_id: row.match_id,
        external_id: row.external_id,
        league_name: row.league_name,
        season: row.season,
        home_team: row.home_team,
        away_team: row.away_team,
        match_date: toIsoOrNull(row.match_date),
        old_pipeline_status: row.pipeline_status,
        new_pipeline_status_preview: classification.decision === 'would_update' ? 'harvested' : row.pipeline_status,
        raw_data_version: row.raw_data_version,
        raw_row_count: Number(row.raw_row_count || 0),
        decision: classification.decision,
        reason: classification.reason,
    };
}

function groupCounts(rows = [], keyName, fallbackLabel) {
    const counts = new Map();
    for (const row of rows) {
        const normalized = String(row[keyName] || '').trim() || fallbackLabel;
        counts.set(normalized, (counts.get(normalized) || 0) + 1);
    }
    return [...counts.entries()]
        .map(([label, count]) => ({ [keyName]: label, count }))
        .sort((left, right) => right.count - left.count || String(left[keyName]).localeCompare(String(right[keyName])));
}

function validateExpectedCount(expectedCount, actualCount) {
    if (expectedCount === null || expectedCount === undefined) {
        return;
    }
    if (expectedCount !== actualCount) {
        throw new Error(`Expected selected_count=${expectedCount} but found ${actualCount}`);
    }
}

function validateWritePrerequisites(matchesColumns = []) {
    const columnSet = new Set(matchesColumns);
    if (!columnSet.has('updated_at')) {
        throw new Error('Guarded write requires matches.updated_at; fail closed until schema is confirmed');
    }
}

function buildDryRunPayload(options = {}, rows = [], rawColumns = [], matchesColumns = [], rawSignalMetadata = {}) {
    const classifiedRows = rows.map(row => ({
        ...row,
        ...classifyRow(row),
    }));

    const cleanCandidates = classifiedRows.filter(row => row.decision === 'would_update');
    const selectedCandidates = cleanCandidates.slice(0, options.limit);
    const holdDuplicate = classifiedRows.filter(row => row.decision === 'hold_duplicate_raw').length;
    const holdNonFinished = classifiedRows.filter(row => row.decision === 'hold_non_finished').length;
    const holdMissingSignal = classifiedRows.filter(row => row.decision === 'hold_missing_hash_or_payload').length;
    const holdExternalMismatch = classifiedRows.filter(row => row.decision === 'hold_external_id_mismatch').length;
    const excludedNoRaw = classifiedRows.filter(row => row.decision === 'excluded_no_raw').length;

    return {
        phase: PHASE,
        contract_carrier: CONTRACT_CARRIER,
        data_version: DATA_VERSION,
        guarded_transition: GUARDED_TRANSITION,
        mode: 'dry_run',
        safety: {
            live_fetch_allowed: false,
            raw_match_data_write_allowed: false,
            raw_payload_output_allowed: false,
            db_write_allowed: false,
            pipeline_status_update_allowed: false,
            requires_allow_write: true,
            max_batch_size: MAX_LIMIT,
        },
        raw_table_columns: rawColumns,
        matches_table_columns: matchesColumns,
        raw_signal_columns: {
            external_id_available: rawSignalMetadata.hasExternalIdColumn === true,
            raw_data_available: rawSignalMetadata.hasRawDataColumn === true,
            data_hash_available: rawSignalMetadata.hasDataHashColumn === true,
        },
        summary: {
            pending_external_scope_total: classifiedRows.length,
            candidate_total: cleanCandidates.length,
            selected_count: selectedCandidates.length,
            would_update_count: selectedCandidates.length,
            hold_duplicate_raw_count: holdDuplicate,
            hold_non_finished_count: holdNonFinished,
            hold_missing_hash_or_payload_count: holdMissingSignal,
            hold_external_id_mismatch_count: holdExternalMismatch,
            excluded_no_raw_count: excludedNoRaw,
            actual_update_executed: false,
        },
        by_league: groupCounts(cleanCandidates, 'league_name', 'UNKNOWN_LEAGUE'),
        by_season: groupCounts(cleanCandidates, 'season', 'UNKNOWN_SEASON'),
        by_match_status: groupCounts(cleanCandidates, 'match_status', 'UNKNOWN_STATUS'),
        selected_candidates: selectedCandidates.map(mapCandidateRow),
    };
}

function buildWritePayload(options = {}, selectedCandidates = [], updatedRows = [], rawColumns = [], matchesColumns = [], rawSignalMetadata = {}) {
    return {
        phase: PHASE,
        contract_carrier: CONTRACT_CARRIER,
        data_version: DATA_VERSION,
        guarded_transition: GUARDED_TRANSITION,
        mode: 'write_executed',
        safety: {
            live_fetch_allowed: false,
            raw_match_data_write_allowed: false,
            raw_payload_output_allowed: false,
            db_write_allowed: true,
            pipeline_status_update_allowed: true,
            requires_allow_write: true,
            max_batch_size: MAX_LIMIT,
        },
        raw_table_columns: rawColumns,
        matches_table_columns: matchesColumns,
        raw_signal_columns: {
            external_id_available: rawSignalMetadata.hasExternalIdColumn === true,
            raw_data_available: rawSignalMetadata.hasRawDataColumn === true,
            data_hash_available: rawSignalMetadata.hasDataHashColumn === true,
        },
        summary: {
            pending_external_scope_total: selectedCandidates.length,
            candidate_total: selectedCandidates.length,
            selected_count: selectedCandidates.length,
            would_update_count: selectedCandidates.length,
            actual_update_executed: true,
            updated_count: updatedRows.length,
        },
        before_rows: selectedCandidates.map(mapCandidateRow),
        after_rows: updatedRows.map(row => ({
            match_id: row.match_id,
            external_id: row.external_id,
            old_pipeline_status: 'pending',
            new_pipeline_status_preview: row.new_pipeline_status,
            decision: 'updated',
            reason: 'guarded_reconciliation_write_executed_in_mock_or_authorized_mode',
        })),
    };
}

async function runGuardedReconciliationWrite(options = {}, dependencies = {}) {
    const connection = await openClient(dependencies);
    let finished = false;

    try {
        const query = options.allowWrite ? queryWriteCapable : querySelectOnly;
        const beginSql = options.allowWrite ? WRITE_BEGIN_SQL : READ_ONLY_BEGIN_SQL;
        await query(connection.client, beginSql);

        const rawColumnsResult = await query(connection.client, RAW_COLUMNS_SQL);
        const matchesColumnsResult = await query(connection.client, MATCHES_COLUMNS_SQL);
        const context = await collectPreviewContext(
            connection.client,
            query,
            options,
            rawColumnsResult,
            matchesColumnsResult,
        );

        const payload = options.allowWrite
            ? await runWriteFlow(connection.client, query, options, context)
            : await runDryRunFlow(connection.client, query, options, context);
        finished = true;
        return payload;
    } catch (error) {
        if (!finished) {
            try {
                const rollbackQuery = options.allowWrite ? queryWriteCapable : querySelectOnly;
                await rollbackQuery(connection.client, ROLLBACK_SQL);
            } catch {
                // preserve original error
            }
        }
        throw error;
    } finally {
        await connection.close();
    }
}

function payloadToText(payload) {
    return [
        '[DRY-RUN] FotMob L2 guarded reconciliation write draft',
        `Contract carrier: ${payload.contract_carrier}`,
        `Guarded transition: ${payload.guarded_transition}`,
        `Mode: ${payload.mode}`,
        'Safety:',
        `  live_fetch_allowed: ${payload.safety.live_fetch_allowed}`,
        `  db_write_allowed: ${payload.safety.db_write_allowed}${payload.safety.requires_allow_write ? ' unless --allow-write' : ''}`,
        `  raw_match_data_write_allowed: ${payload.safety.raw_match_data_write_allowed}`,
        `  pipeline_status_update_allowed: ${payload.safety.pipeline_status_update_allowed}${payload.safety.requires_allow_write ? ' unless --allow-write' : ''}`,
        `  raw_payload_output_allowed: ${payload.safety.raw_payload_output_allowed}`,
        `  requires_allow_write: ${payload.safety.requires_allow_write}`,
        `  max_batch_size: ${payload.safety.max_batch_size}`,
        '',
        'Summary:',
        `  candidate_total: ${payload.summary.candidate_total}`,
        `  selected_count: ${payload.summary.selected_count}`,
        `  would_update_count: ${payload.summary.would_update_count}`,
        `  actual_update_executed: ${payload.summary.actual_update_executed}`,
        '',
        'Selected candidates:',
        ...(payload.selected_candidates || []).map((row, index) => [
            `  ${index + 1}. ${row.match_id} | external_id=${row.external_id}`,
            `     ${row.league_name || 'UNKNOWN_LEAGUE'} | ${row.season || 'UNKNOWN_SEASON'} | ${row.home_team || 'UNKNOWN_HOME'} vs ${row.away_team || 'UNKNOWN_AWAY'}`,
            `     match_date=${row.match_date || 'null'} | old_pipeline_status=${row.old_pipeline_status || 'null'} | new_pipeline_status_preview=${row.new_pipeline_status_preview || 'null'}`,
            `     raw_data_version=${row.raw_data_version || 'null'} | raw_row_count=${row.raw_row_count}`,
            `     decision=${row.decision} | reason=${row.reason}`,
        ].join('\n')),
    ].join('\n');
}

function buildFailurePayload(error, options = {}) {
    return {
        phase: PHASE,
        contract_carrier: CONTRACT_CARRIER,
        data_version: DATA_VERSION,
        guarded_transition: GUARDED_TRANSITION,
        mode: options.allowWrite ? 'write_aborted' : 'dry_run_failed',
        safety: {
            live_fetch_allowed: false,
            raw_match_data_write_allowed: false,
            raw_payload_output_allowed: false,
            db_write_allowed: options.allowWrite === true,
            pipeline_status_update_allowed: options.allowWrite === true,
            requires_allow_write: true,
            max_batch_size: MAX_LIMIT,
        },
        errors: [error.message],
    };
}

function writePayload(payload, json, io) {
    const output = json ? `${JSON.stringify(payload, null, 2)}\n` : `${payloadToText(payload)}\n`;
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
        allowWrite: false,
    };

    try {
        options = parseArgs(argv);
        if (options.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }

        const payload = await runGuardedReconciliationWrite(options);
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
    GUARDED_TRANSITION,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    READ_ONLY_BEGIN_SQL,
    WRITE_BEGIN_SQL,
    COMMIT_SQL,
    ROLLBACK_SQL,
    RAW_COLUMNS_SQL,
    MATCHES_COLUMNS_SQL,
    CANDIDATE_ROWS_SQL_TEMPLATE,
    GUARDED_UPDATE_SQL,
    parseArgs,
    buildDbConfig,
    buildBaseFilters,
    buildRawSignalSql,
    buildQueryBundle,
    assertSelectOnlySql,
    assertWriteSql,
    querySelectOnly,
    queryWriteCapable,
    classifyRow,
    mapCandidateRow,
    validateExpectedCount,
    validateWritePrerequisites,
    buildDryRunPayload,
    buildWritePayload,
    runGuardedReconciliationWrite,
    payloadToText,
    buildFailurePayload,
    main,
};
