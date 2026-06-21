#!/usr/bin/env node
/**
 * Phase 4.38 local finished CSV dry-run gate.
 *
 * Reads a local CSV and reports match / label readiness preview only. The
 * commit path is intentionally blocked and not wired in this phase.
 */

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { Pool } = require('pg');
const { assertDbWriteAllowed } = require('./helpers/db_write_guard');

const FORBIDDEN_SQL =
    /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|UPSERT|MERGE|GRANT|REVOKE|CREATE\s+INDEX)\b/i;
const FINISHED_STATUSES = new Set(['finished', 'completed', 'complete', 'full_time', 'ft']);
const TRUE_VALUES = new Set(['true', 't', '1', 'yes', 'y']);

const FIELD_ALIASES = {
    matchId: ['match_id', 'matchid', 'matchId', 'id'],
    externalId: ['external_id', 'externalId'],
    matchDate: ['match_date', 'date', 'Date'],
    homeTeam: ['home_team', 'HomeTeam', 'home', 'homeTeam'],
    awayTeam: ['away_team', 'AwayTeam', 'away', 'awayTeam'],
    homeScore: ['home_score', 'FTHG', 'home_goals'],
    awayScore: ['away_score', 'FTAG', 'away_goals'],
    actualResult: ['actual_result', 'FTR', 'result'],
    status: ['status'],
    isFinished: ['is_finished', 'finished'],
    leagueName: ['league_name', 'league'],
    season: ['season'],
};

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/finished_csv_local_dry_run.js --csv <path> [--json] [--limit <n>]',
        '  node scripts/ops/finished_csv_local_dry_run.js --csv <path> --commit',
        '',
        'Safety:',
        '  Dry-run only in Phase 4.38; --commit is blocked and not wired.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        csvPath: null,
        json: false,
        limit: null,
        commit: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--csv') {
            args.csvPath = argv[index + 1];
            index += 1;
        } else if (token === '--json') {
            args.json = true;
        } else if (token === '--limit') {
            args.limit = parseLimit(argv[index + 1]);
            index += 1;
        } else if (token === '--commit') {
            args.commit = true;
        } else if (token === '--help' || token === '-h') {
            args.help = true;
        } else {
            throw new Error(`Unknown argument: ${token}`);
        }
    }

    return args;
}

function parseLimit(value) {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        throw new Error('--limit must be a positive integer');
    }
    return parsed;
}

function buildBlockedCommitPayload(csvPath) {
    return {
        mode: 'blocked-commit',
        ok: false,
        csv_path: csvPath || null,
        error: 'BLOCKED: finished CSV commit is not wired in Phase 4.38.',
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function buildDbConfig() {
    return {
        host: process.env.DB_HOST || process.env.POSTGRES_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || process.env.POSTGRES_PORT || '5432', 10),
        database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
        user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD,
        max: 2,
        connectionTimeoutMillis: 5000,
        idleTimeoutMillis: 5000,
    };
}

function assertSafeSelect(sql) {
    if (!/^\s*SELECT\b/i.test(sql)) {
        throw new Error('Unsafe SQL blocked: query must start with SELECT');
    }
    if (FORBIDDEN_SQL.test(sql)) {
        throw new Error('Unsafe SQL blocked: write/schema/export verb detected');
    }
}

async function safeSelect(pool, sql, params = []) {
    assertSafeSelect(sql);
    return pool.query(sql, params);
}

function resolveLocalCsvPath(rawPath) {
    if (!rawPath) {
        throw new Error('Missing required --csv <path>');
    }
    const resolved = path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(process.cwd(), rawPath);
    if (!fs.existsSync(resolved)) {
        throw new Error(`CSV file not found: ${rawPath}`);
    }
    const stats = fs.statSync(resolved);
    if (!stats.isFile()) {
        throw new Error(`CSV path is not a file: ${rawPath}`);
    }
    return resolved;
}

function readCsvRows(resolvedPath, limit) {
    return new Promise((resolve, reject) => {
        const rows = [];
        const headers = [];
        let sourceRow = 1;

        fs.createReadStream(resolvedPath)
            .pipe(csv())
            .on('headers', parsedHeaders => {
                headers.push(...parsedHeaders);
            })
            .on('data', row => {
                if (limit && rows.length >= limit) {
                    return;
                }
                sourceRow += 1;
                rows.push({
                    source_row: sourceRow,
                    row,
                });
            })
            .on('error', reject)
            .on('end', () => resolve({ headers, rows }));
    });
}

function normalizeKey(value) {
    return String(value || '')
        .replace(/[^a-z0-9]/gi, '')
        .toLowerCase();
}

function getRowValue(row, aliases) {
    const normalizedMap = new Map(Object.keys(row).map(key => [normalizeKey(key), key]));
    for (const alias of aliases) {
        const actualKey = normalizedMap.get(normalizeKey(alias));
        if (actualKey) {
            const value = normalizeText(row[actualKey]);
            if (value !== '') {
                return value;
            }
        }
    }
    return null;
}

function normalizeText(value) {
    return String(value ?? '')
        .replace(/\s+/g, ' ')
        .trim();
}

function normalizeStatus(value) {
    return normalizeText(value).toLowerCase();
}

function parseScore(value) {
    const normalized = normalizeText(value);
    if (normalized === '') return null;
    const parsed = Number.parseInt(normalized, 10);
    return Number.isFinite(parsed) ? parsed : null;
}

function parseCsvDate(value) {
    const normalized = normalizeText(value);
    if (!normalized) {
        return { value: null, valid: false };
    }
    const parsed = new Date(normalized);
    if (Number.isNaN(parsed.getTime())) {
        return { value: normalized, valid: false };
    }
    return { value: parsed.toISOString(), valid: true };
}

function normalizeActualResult(value) {
    const normalized = normalizeText(value).toLowerCase();
    if (!normalized) return null;
    if (['h', 'home', 'home_win', 'home win', '1'].includes(normalized)) return 'home_win';
    if (['d', 'draw', 'x'].includes(normalized)) return 'draw';
    if (['a', 'away', 'away_win', 'away win', '2'].includes(normalized)) return 'away_win';
    return null;
}

function deriveLabel({ actualResultRaw, homeScore, awayScore }) {
    const directLabel = normalizeActualResult(actualResultRaw);
    if (directLabel) {
        return { label: directLabel, source: 'actual_result' };
    }
    if (homeScore === null || awayScore === null) {
        return { label: null, source: null };
    }
    if (homeScore > awayScore) return { label: 'home_win', source: 'score' };
    if (homeScore < awayScore) return { label: 'away_win', source: 'score' };
    return { label: 'draw', source: 'score' };
}

function isFinishedLike({ status, isFinishedRaw, hasCompleteScore, label }) {
    if (FINISHED_STATUSES.has(status)) return true;
    if (TRUE_VALUES.has(normalizeStatus(isFinishedRaw))) return true;
    return hasCompleteScore && Boolean(label);
}

function buildPreviewId(row, sourceRow) {
    const source = [
        row.match_date || 'unknown_date',
        row.home_team || 'unknown_home',
        row.away_team || 'unknown_away',
        sourceRow,
    ].join('|');
    return `csv_${crypto.createHash('sha1').update(source).digest('hex').slice(0, 12)}`;
}

function analyzeRow(record) {
    const row = record.row;
    const homeScore = parseScore(getRowValue(row, FIELD_ALIASES.homeScore));
    const awayScore = parseScore(getRowValue(row, FIELD_ALIASES.awayScore));
    const actualResultRaw = getRowValue(row, FIELD_ALIASES.actualResult);
    const label = deriveLabel({ actualResultRaw, homeScore, awayScore });
    const status = normalizeStatus(getRowValue(row, FIELD_ALIASES.status));
    const date = parseCsvDate(getRowValue(row, FIELD_ALIASES.matchDate));
    const previewBase = buildPreviewBase(record, { homeScore, awayScore, label, status, date });
    const hasCompleteScore = homeScore !== null && awayScore !== null;
    const finished = isFinishedLike({
        status,
        isFinishedRaw: getRowValue(row, FIELD_ALIASES.isFinished),
        hasCompleteScore,
        label: label.label,
    });
    const warnings = buildRowWarnings(previewBase, { date, finished, label: label.label, hasCompleteScore });

    return {
        ...previewBase,
        finished,
        trainable: finished && Boolean(label.label) && date.valid,
        skip_reason: buildSkipReason({ finished, label: label.label, dateValid: date.valid }),
        warnings,
    };
}

function buildPreviewBase(record, derived) {
    const row = record.row;
    const base = {
        source_row: record.source_row,
        match_id_preview: getRowValue(row, FIELD_ALIASES.matchId),
        external_id: getRowValue(row, FIELD_ALIASES.externalId),
        match_date: derived.date.value,
        league_name: getRowValue(row, FIELD_ALIASES.leagueName),
        season: getRowValue(row, FIELD_ALIASES.season),
        home_team: getRowValue(row, FIELD_ALIASES.homeTeam),
        away_team: getRowValue(row, FIELD_ALIASES.awayTeam),
        home_score: derived.homeScore,
        away_score: derived.awayScore,
        actual_result: derived.label.label,
        label_source: derived.label.source,
        status: derived.status || null,
        db_match_exists: null,
    };
    return {
        ...base,
        match_id_preview: base.match_id_preview || buildPreviewId(base, record.source_row),
    };
}

function buildRowWarnings(preview, context) {
    const warnings = [];
    if (!preview.match_id_preview) warnings.push('missing_match_id_preview');
    if (!preview.home_team) warnings.push('missing_home_team');
    if (!preview.away_team) warnings.push('missing_away_team');
    if (!preview.match_date) warnings.push('missing_match_date');
    if (preview.match_date && !context.date.valid) warnings.push('invalid_match_date');
    if (!context.finished) warnings.push('not_finished');
    if (!context.label) warnings.push('missing_label');
    if (!context.hasCompleteScore) warnings.push('missing_complete_score');
    return warnings;
}

function buildSkipReason({ finished, label, dateValid }) {
    if (!finished) return 'not_finished';
    if (!label) return 'missing_label';
    if (!dateValid) return 'invalid_match_date';
    return null;
}

function summarizePreviews(previews) {
    const mappingWarnings = [];
    const duplicateIds = findDuplicateIds(previews);
    for (const matchId of duplicateIds) {
        mappingWarnings.push(`duplicate_match_id_preview:${matchId}`);
    }
    for (const preview of previews) {
        for (const warning of preview.warnings) {
            mappingWarnings.push(`row_${preview.source_row}:${warning}`);
        }
    }

    return {
        total_rows: previews.length,
        finished_rows: previews.filter(row => row.finished).length,
        trainable_label_rows: previews.filter(row => row.trainable).length,
        skipped_rows: previews.filter(row => !row.trainable).length,
        would_insert_matches: false,
        would_update_matches: false,
        would_write_db: false,
        mapping_warnings: mappingWarnings,
    };
}

function findDuplicateIds(previews) {
    const counts = new Map();
    for (const preview of previews) {
        counts.set(preview.match_id_preview, (counts.get(preview.match_id_preview) || 0) + 1);
    }
    return [...counts.entries()].filter(([, count]) => count > 1).map(([matchId]) => matchId);
}

async function fetchExistingMatchIds(previews) {
    const ids = [...new Set(previews.map(row => row.match_id_preview).filter(Boolean))];
    if (ids.length === 0) return new Set();

    const pool = new Pool(buildDbConfig());
    try {
        const sql = `
            SELECT match_id
            FROM matches
            WHERE match_id = ANY($1)
        `;
        const result = await safeSelect(pool, sql, [ids]);
        return new Set(result.rows.map(row => row.match_id));
    } finally {
        await pool.end();
    }
}

function applyDbExistence(previews, existingIds) {
    return previews.map(preview => ({
        ...preview,
        db_match_exists: existingIds.has(preview.match_id_preview),
    }));
}

function buildNonExecutionConfirmations() {
    return [
        'no_db_writes',
        'no_insert',
        'no_update',
        'no_delete',
        'no_copy',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
        'no_external_network',
        'no_file_export',
    ];
}

function buildPayload({ args, resolvedCsvPath, headers, previews }) {
    const summary = summarizePreviews(previews);
    return {
        mode: 'dry-run',
        csv_path: args.csvPath,
        resolved_csv_path: resolvedCsvPath,
        columns: headers,
        limit: args.limit,
        ...summary,
        label_mapping: {
            direct_result_fields: FIELD_ALIASES.actualResult,
            score_fields: [...FIELD_ALIASES.homeScore, ...FIELD_ALIASES.awayScore],
            result_values: {
                H: 'home_win',
                D: 'draw',
                A: 'away_win',
                score_home_gt_away: 'home_win',
                score_equal: 'draw',
                score_home_lt_away: 'away_win',
            },
        },
        candidate_preview: previews,
        db_existing_rows: previews.filter(row => row.db_match_exists).length,
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function formatText(payload) {
    return [
        'mode=dry-run',
        `csv_path=${payload.csv_path}`,
        `total_rows=${payload.total_rows}`,
        `finished_rows=${payload.finished_rows}`,
        `trainable_label_rows=${payload.trainable_label_rows}`,
        `skipped_rows=${payload.skipped_rows}`,
        `would_insert_matches=${payload.would_insert_matches}`,
        `would_update_matches=${payload.would_update_matches}`,
        `would_write_db=${payload.would_write_db}`,
        `db_existing_rows=${payload.db_existing_rows}`,
        '',
        'candidate_preview:',
        JSON.stringify(payload.candidate_preview, null, 2),
        '',
        'mapping_warnings:',
        payload.mapping_warnings.length ? payload.mapping_warnings.map(value => `  ${value}`).join('\n') : '  none',
        '',
        'non_execution_confirmations:',
        payload.non_execution_confirmations.map(value => `  ${value}`).join('\n'),
    ].join('\n');
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
        console.log(usage());
        return;
    }
    if (args.commit) {
        assertDbWriteAllowed({
            script: 'finished_csv_local_dry_run.js',
            tables: ['matches'],
            operations: ['INSERT'],
        });
        console.error(JSON.stringify(buildBlockedCommitPayload(args.csvPath), null, 2));
        process.exitCode = 1;
        return;
    }
    const resolvedCsvPath = resolveLocalCsvPath(args.csvPath);
    const { headers, rows } = await readCsvRows(resolvedCsvPath, args.limit);
    const previews = rows.map(analyzeRow);
    const existingIds = await fetchExistingMatchIds(previews);
    const payload = buildPayload({
        args,
        resolvedCsvPath,
        headers,
        previews: applyDbExistence(previews, existingIds),
    });

    console.log(args.json ? JSON.stringify(payload, null, 2) : formatText(payload));
}

main().catch(error => {
    console.error(
        JSON.stringify(
            {
                mode: 'dry-run',
                ok: false,
                error: error.message,
                non_execution_confirmations: buildNonExecutionConfirmations(),
            },
            null,
            2
        )
    );
    process.exitCode = 1;
});
