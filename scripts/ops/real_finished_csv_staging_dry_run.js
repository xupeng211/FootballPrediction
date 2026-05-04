#!/usr/bin/env node
/**
 * Phase 4.52 real finished CSV staging dry-run gate.
 *
 * Reads a local source manifest and optional local CSV, then reports source,
 * integrity, schema, label, duplicate, and leakage-readiness previews only.
 * The commit path is intentionally blocked and not wired in this phase.
 */

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { Pool } = require('pg');

const FORBIDDEN_SQL =
    /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|UPSERT|MERGE|GRANT|REVOKE|CREATE\s+INDEX)\b/i;
const FINISHED_STATUSES = new Set(['finished', 'completed', 'complete', 'full_time', 'ft']);
const TRUE_VALUES = new Set(['true', 't', '1', 'yes', 'y']);
const REQUIRED_MANIFEST_FIELDS = [
    'source_name',
    'source_type',
    'source_url',
    'license_url',
    'terms_url',
    'license_type',
    'allowed_use',
    'attribution_required',
    'commercial_use_allowed',
    'redistribution_allowed',
    'data_owner',
    'downloaded_by',
    'downloaded_at',
    'original_filename',
    'sha256',
    'row_count',
    'field_dictionary',
    'mapping_version',
    'approval_status',
    'human_approval_note',
];

const DEFAULT_FIELD_ALIASES = {
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
    leagueName: ['league_name', 'league', 'Div'],
    season: ['season'],
    bookmaker: ['bookmaker_name', 'bookmaker'],
    marketType: ['market_type', 'market'],
    homeOdds: ['B365H', 'PSH', 'open_home', 'close_home', 'odds_home'],
    drawOdds: ['B365D', 'PSD', 'open_draw', 'close_draw', 'odds_draw'],
    awayOdds: ['B365A', 'PSA', 'open_away', 'close_away', 'odds_away'],
};

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/real_finished_csv_staging_dry_run.js --source-manifest <path> --audit-source [--json]',
        '  node scripts/ops/real_finished_csv_staging_dry_run.js --source-manifest <path> --sample-csv <path> [--json]',
        '  node scripts/ops/real_finished_csv_staging_dry_run.js --source-manifest <path> --sample-csv <path> --commit',
        '',
        'Safety:',
        '  Dry-run only in Phase 4.52; --commit is blocked and not wired.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        sourceManifest: null,
        sampleCsv: null,
        auditSource: false,
        json: false,
        commit: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--source-manifest') {
            args.sourceManifest = argv[index + 1];
            index += 1;
        } else if (token === '--sample-csv') {
            args.sampleCsv = argv[index + 1];
            index += 1;
        } else if (token === '--audit-source') {
            args.auditSource = true;
        } else if (token === '--json') {
            args.json = true;
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

function buildBlockedCommitPayload(sourceManifest, sampleCsv) {
    return {
        mode: 'blocked-commit',
        ok: false,
        source_manifest: sourceManifest || null,
        sample_csv: sampleCsv || null,
        error: 'BLOCKED: real finished CSV commit is not wired in Phase 4.52.',
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function resolveLocalFile(rawPath, label) {
    if (!rawPath) {
        throw new Error(`Missing required ${label}`);
    }
    const resolved = path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(process.cwd(), rawPath);
    if (!fs.existsSync(resolved)) {
        throw new Error(`${label} not found: ${rawPath}`);
    }
    const stats = fs.statSync(resolved);
    if (!stats.isFile()) {
        throw new Error(`${label} is not a file: ${rawPath}`);
    }
    return resolved;
}

function readJsonFile(resolvedPath) {
    return JSON.parse(fs.readFileSync(resolvedPath, 'utf8'));
}

function sha256File(resolvedPath) {
    return crypto.createHash('sha256').update(fs.readFileSync(resolvedPath)).digest('hex');
}

function isPresent(value) {
    if (value === null || value === undefined) return false;
    if (typeof value === 'string') return value.trim() !== '';
    if (typeof value === 'object') return Object.keys(value).length > 0;
    return true;
}

function validateManifest(manifest) {
    const missing = REQUIRED_MANIFEST_FIELDS.filter(field => !isPresent(manifest[field]));
    return {
        required_fields_complete: missing.length === 0,
        missing_required_fields: missing,
    };
}

function buildSourceAuditPayload({ args, resolvedManifestPath, manifest, validation }) {
    return {
        mode: 'source-audit',
        phase: '4.52',
        manifest_found: true,
        source_manifest: args.sourceManifest,
        resolved_source_manifest: resolvedManifestPath,
        required_fields_complete: validation.required_fields_complete,
        missing_required_fields: validation.missing_required_fields,
        source_name: manifest.source_name,
        source_type: manifest.source_type,
        source_url: manifest.source_url,
        license_type: manifest.license_type,
        allowed_use: manifest.allowed_use,
        approval_status: manifest.approval_status,
        original_filename: manifest.original_filename,
        sha256: manifest.sha256,
        row_count: manifest.row_count,
        field_dictionary_present: isPresent(manifest.field_dictionary),
        mapping_version: manifest.mapping_version,
        human_approval_note_present: isPresent(manifest.human_approval_note),
        can_use_for_db_write: false,
        dry_run_only: true,
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

function readCsvRows(resolvedPath) {
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

function normalizeText(value) {
    return String(value ?? '')
        .replace(/\s+/g, ' ')
        .trim();
}

function normalizeStatus(value) {
    return normalizeText(value).toLowerCase();
}

function normalizeAliases(aliases) {
    if (!Array.isArray(aliases)) return [];
    return aliases.map(value => String(value));
}

function buildFieldAliases(manifest) {
    const dictionary = manifest.field_dictionary || {};
    return {
        ...DEFAULT_FIELD_ALIASES,
        matchDate: [...normalizeAliases(dictionary.date), ...DEFAULT_FIELD_ALIASES.matchDate],
        homeTeam: [...normalizeAliases(dictionary.home_team), ...DEFAULT_FIELD_ALIASES.homeTeam],
        awayTeam: [...normalizeAliases(dictionary.away_team), ...DEFAULT_FIELD_ALIASES.awayTeam],
        homeScore: [...normalizeAliases(dictionary.home_score), ...DEFAULT_FIELD_ALIASES.homeScore],
        awayScore: [...normalizeAliases(dictionary.away_score), ...DEFAULT_FIELD_ALIASES.awayScore],
        actualResult: [...normalizeAliases(dictionary.result), ...DEFAULT_FIELD_ALIASES.actualResult],
        leagueName: [...normalizeAliases(dictionary.league), ...DEFAULT_FIELD_ALIASES.leagueName],
        season: [...normalizeAliases(dictionary.season), ...DEFAULT_FIELD_ALIASES.season],
    };
}

function findColumn(headers, aliases) {
    const normalizedMap = new Map(headers.map(header => [normalizeKey(header), header]));
    for (const alias of aliases) {
        const actual = normalizedMap.get(normalizeKey(alias));
        if (actual) return actual;
    }
    return null;
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

function deriveLabel({ actualResultRaw, homeScore, awayScore, finished }) {
    const directLabel = normalizeActualResult(actualResultRaw);
    if (directLabel) {
        return { label: directLabel, source: 'actual_result' };
    }
    if (!finished || homeScore === null || awayScore === null) {
        return { label: null, source: null };
    }
    if (homeScore > awayScore) return { label: 'home_win', source: 'score' };
    if (homeScore < awayScore) return { label: 'away_win', source: 'score' };
    return { label: 'draw', source: 'score' };
}

function isFinishedLike({ status, isFinishedRaw }) {
    if (FINISHED_STATUSES.has(status)) return true;
    return TRUE_VALUES.has(normalizeStatus(isFinishedRaw));
}

function buildPreviewId(row, sourceRow, manifest) {
    if (row.match_id) return row.match_id;
    const source = [
        manifest.source_name || 'unknown_source',
        row.match_date || 'unknown_date',
        row.home_team || 'unknown_home',
        row.away_team || 'unknown_away',
        sourceRow,
    ].join('|');
    return `realcsv_${crypto.createHash('sha1').update(source).digest('hex').slice(0, 12)}`;
}

function analyzeRow(record, aliases, manifest) {
    const row = record.row;
    const status = normalizeStatus(getRowValue(row, aliases.status));
    const finished = isFinishedLike({
        status,
        isFinishedRaw: getRowValue(row, aliases.isFinished),
    });
    const homeScore = parseScore(getRowValue(row, aliases.homeScore));
    const awayScore = parseScore(getRowValue(row, aliases.awayScore));
    const actualResultRaw = getRowValue(row, aliases.actualResult);
    const label = deriveLabel({ actualResultRaw, homeScore, awayScore, finished });
    const date = parseCsvDate(getRowValue(row, aliases.matchDate));
    const base = {
        row_number: record.source_row,
        source_row: record.source_row,
        match_id: getRowValue(row, aliases.matchId),
        external_id: getRowValue(row, aliases.externalId),
        match_date: date.value,
        league_name: getRowValue(row, aliases.leagueName),
        season: getRowValue(row, aliases.season),
        home_team: getRowValue(row, aliases.homeTeam),
        away_team: getRowValue(row, aliases.awayTeam),
        home_score: homeScore,
        away_score: awayScore,
        actual_result: label.label,
        label_source: label.source,
        status: status || null,
        data_source: manifest.source_name,
        data_version: manifest.mapping_version,
        would_insert_matches: false,
        would_insert_odds: false,
        db_match_exists: null,
    };
    const candidate = {
        ...base,
        generated_match_id_preview: buildPreviewId(base, record.source_row, manifest),
    };
    const warnings = buildRowWarnings(candidate, {
        date,
        finished,
        label: label.label,
        hasCompleteScore: homeScore !== null && awayScore !== null,
    });

    return {
        ...candidate,
        finished,
        trainable: finished && Boolean(label.label) && date.valid && warnings.length === 0,
        skip_reason: buildSkipReason({ finished, label: label.label, dateValid: date.valid, warnings }),
        warnings,
    };
}

function buildRowWarnings(preview, context) {
    const warnings = [];
    if (!preview.home_team) warnings.push('missing_home_team');
    if (!preview.away_team) warnings.push('missing_away_team');
    if (!preview.match_date) warnings.push('missing_match_date');
    if (preview.match_date && !context.date.valid) warnings.push('invalid_match_date');
    if (!context.finished) warnings.push('not_finished');
    if (!context.label) warnings.push('missing_label');
    if (!context.hasCompleteScore) warnings.push('missing_complete_score');
    return warnings;
}

function buildSkipReason({ finished, label, dateValid, warnings }) {
    if (!finished) return 'not_finished';
    if (!label) return 'missing_label';
    if (!dateValid) return 'invalid_match_date';
    const blockingWarning = warnings.find(warning => warning.startsWith('missing_'));
    return blockingWarning || null;
}

function detectSchema(headers, aliases) {
    const checks = {
        match_date: findColumn(headers, aliases.matchDate),
        home_team: findColumn(headers, aliases.homeTeam),
        away_team: findColumn(headers, aliases.awayTeam),
        home_score: findColumn(headers, aliases.homeScore),
        away_score: findColumn(headers, aliases.awayScore),
        result: findColumn(headers, aliases.actualResult),
        league: findColumn(headers, aliases.leagueName),
        season: findColumn(headers, aliases.season),
        bookmaker: findColumn(headers, aliases.bookmaker),
        market_type: findColumn(headers, aliases.marketType),
        home_odds: findColumn(headers, aliases.homeOdds),
        draw_odds: findColumn(headers, aliases.drawOdds),
        away_odds: findColumn(headers, aliases.awayOdds),
    };
    const required = ['match_date', 'home_team', 'away_team', 'home_score', 'away_score'];
    return {
        detected_columns: headers,
        mapping_columns_found: Object.fromEntries(Object.entries(checks).filter(([, value]) => Boolean(value))),
        mapping_columns_missing: required.filter(field => !checks[field]),
    };
}

function findDuplicateIds(previews) {
    const counts = new Map();
    for (const preview of previews) {
        const id = preview.generated_match_id_preview;
        counts.set(id, (counts.get(id) || 0) + 1);
    }
    return [...counts.entries()].filter(([, count]) => count > 1).map(([matchId]) => matchId);
}

function summarizeRows(previews) {
    const duplicateIds = findDuplicateIds(previews);
    return {
        total_rows: previews.length,
        finished_rows: previews.filter(row => row.finished).length,
        trainable_label_rows: previews.filter(row => row.trainable).length,
        skipped_rows: previews.filter(row => !row.trainable).length,
        duplicate_source_rows: duplicateIds.length,
        duplicate_match_ids: duplicateIds,
        invalid_date_rows: previews.filter(row => row.warnings.includes('invalid_match_date')).length,
        missing_team_rows: previews.filter(
            row => row.warnings.includes('missing_home_team') || row.warnings.includes('missing_away_team')
        ).length,
        missing_score_rows: previews.filter(row => row.warnings.includes('missing_complete_score')).length,
        scheduled_or_unlabeled_rows: previews.filter(
            row => row.warnings.includes('not_finished') || row.warnings.includes('missing_label')
        ).length,
        would_insert_matches: false,
        would_insert_odds: false,
    };
}

async function fetchExistingMatchIds(previews) {
    const ids = [...new Set(previews.map(row => row.generated_match_id_preview).filter(Boolean))];
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
        db_match_exists: existingIds.has(preview.generated_match_id_preview),
    }));
}

function buildLeakageGuard() {
    return {
        final_score_used_only_as_label: true,
        no_post_match_features_inserted: true,
        no_predictions_used: true,
        no_synthetic_rows_used_for_real_training: true,
        training_features_require_kickoff_cutoff_before_future_use: true,
    };
}

function buildNonExecutionConfirmations() {
    return [
        'no_db_writes',
        'no_insert',
        'no_update',
        'no_delete',
        'no_copy',
        'no_export',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
        'no_external_network',
    ];
}

function buildDryRunPayload({
    args,
    resolvedManifestPath,
    resolvedCsvPath,
    manifest,
    validation,
    fileHash,
    headers,
    previews,
    schema,
}) {
    const rowSummary = summarizeRows(previews);
    return {
        mode: 'real-finished-csv-staging-dry-run',
        phase: '4.52',
        source_manifest_summary: {
            source_manifest: args.sourceManifest,
            resolved_source_manifest: resolvedManifestPath,
            source_name: manifest.source_name,
            source_type: manifest.source_type,
            approval_status: manifest.approval_status,
            dry_run_only: true,
            can_use_for_db_write: false,
            required_fields_complete: validation.required_fields_complete,
            missing_required_fields: validation.missing_required_fields,
        },
        file_integrity: {
            sample_csv: args.sampleCsv,
            resolved_sample_csv: resolvedCsvPath,
            sample_csv_found: true,
            sha256: fileHash,
            manifest_sha256: manifest.sha256,
            sha256_matches_manifest: fileHash === manifest.sha256,
            row_count: previews.length,
            manifest_row_count: manifest.row_count,
            row_count_matches_manifest: previews.length === Number(manifest.row_count),
        },
        schema_detection: schema,
        row_classification: rowSummary,
        label_mapping: {
            direct_result_values: {
                H: 'home_win',
                D: 'draw',
                A: 'away_win',
            },
            score_derived_policy: 'score-derived label only when row is finished and scores are complete',
        },
        candidate_preview: previews,
        duplicate_check: {
            existing_matches_count: previews.filter(row => row.db_match_exists).length,
            candidates: previews.map(row => ({
                row_number: row.row_number,
                generated_match_id_preview: row.generated_match_id_preview,
                db_match_exists: row.db_match_exists,
            })),
        },
        leakage_guard: buildLeakageGuard(),
        would_insert_matches: false,
        would_insert_odds: false,
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function formatScalar(value) {
    if (Array.isArray(value)) return value.join(',');
    if (value === null || value === undefined) return '';
    return String(value);
}

function formatSourceAuditText(payload) {
    return [
        'mode=source-audit',
        'phase=4.52',
        `manifest_found=${payload.manifest_found}`,
        `required_fields_complete=${payload.required_fields_complete}`,
        `source_name=${payload.source_name}`,
        `source_type=${payload.source_type}`,
        `source_url=${payload.source_url}`,
        `license_type=${payload.license_type}`,
        `allowed_use=${payload.allowed_use}`,
        `approval_status=${payload.approval_status}`,
        `original_filename=${payload.original_filename}`,
        `sha256=${payload.sha256}`,
        `row_count=${payload.row_count}`,
        `field_dictionary_present=${payload.field_dictionary_present}`,
        `mapping_version=${payload.mapping_version}`,
        `human_approval_note_present=${payload.human_approval_note_present}`,
        `can_use_for_db_write=${payload.can_use_for_db_write}`,
        `dry_run_only=${payload.dry_run_only}`,
        '',
        'missing_required_fields:',
        payload.missing_required_fields.length
            ? payload.missing_required_fields.map(value => `  ${value}`).join('\n')
            : '  none',
        '',
        'non_execution_confirmations:',
        payload.non_execution_confirmations.map(value => `  ${value}`).join('\n'),
    ].join('\n');
}

function formatDryRunText(payload) {
    const source = payload.source_manifest_summary;
    const integrity = payload.file_integrity;
    const rows = payload.row_classification;
    const duplicate = payload.duplicate_check;
    return [
        'mode=real-finished-csv-staging-dry-run',
        'phase=4.52',
        `source_name=${source.source_name}`,
        `approval_status=${source.approval_status}`,
        `dry_run_only=${source.dry_run_only}`,
        `can_use_for_db_write=${source.can_use_for_db_write}`,
        `sample_csv_found=${integrity.sample_csv_found}`,
        `sha256_matches_manifest=${integrity.sha256_matches_manifest}`,
        `row_count_matches_manifest=${integrity.row_count_matches_manifest}`,
        `total_rows=${rows.total_rows}`,
        `finished_rows=${rows.finished_rows}`,
        `trainable_label_rows=${rows.trainable_label_rows}`,
        `skipped_rows=${rows.skipped_rows}`,
        `duplicate_source_rows=${rows.duplicate_source_rows}`,
        `invalid_date_rows=${rows.invalid_date_rows}`,
        `missing_team_rows=${rows.missing_team_rows}`,
        `missing_score_rows=${rows.missing_score_rows}`,
        `scheduled_or_unlabeled_rows=${rows.scheduled_or_unlabeled_rows}`,
        `existing_matches_count=${duplicate.existing_matches_count}`,
        `would_insert_matches=${payload.would_insert_matches}`,
        `would_insert_odds=${payload.would_insert_odds}`,
        '',
        'schema_detection:',
        JSON.stringify(payload.schema_detection, null, 2),
        '',
        'candidate_preview:',
        JSON.stringify(payload.candidate_preview, null, 2),
        '',
        'leakage_guard:',
        Object.entries(payload.leakage_guard)
            .map(([key, value]) => `  ${key}=${formatScalar(value)}`)
            .join('\n'),
        '',
        'non_execution_confirmations:',
        payload.non_execution_confirmations.map(value => `  ${value}`).join('\n'),
    ].join('\n');
}

async function buildDryRun(args, resolvedManifestPath, manifest, validation) {
    const resolvedCsvPath = resolveLocalFile(args.sampleCsv, '--sample-csv <path>');
    const fileHash = sha256File(resolvedCsvPath);
    const { headers, rows } = await readCsvRows(resolvedCsvPath);
    const aliases = buildFieldAliases(manifest);
    const previews = rows.map(row => analyzeRow(row, aliases, manifest));
    const existingIds = await fetchExistingMatchIds(previews);
    const previewsWithDb = applyDbExistence(previews, existingIds);
    return buildDryRunPayload({
        args,
        resolvedManifestPath,
        resolvedCsvPath,
        manifest,
        validation,
        fileHash,
        headers,
        previews: previewsWithDb,
        schema: detectSchema(headers, aliases),
    });
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
        console.log(usage());
        return;
    }
    if (args.commit) {
        console.error(JSON.stringify(buildBlockedCommitPayload(args.sourceManifest, args.sampleCsv), null, 2));
        process.exitCode = 1;
        return;
    }

    const resolvedManifestPath = resolveLocalFile(args.sourceManifest, '--source-manifest <path>');
    const manifest = readJsonFile(resolvedManifestPath);
    const validation = validateManifest(manifest);
    const sourcePayload = buildSourceAuditPayload({ args, resolvedManifestPath, manifest, validation });

    if (!validation.required_fields_complete) {
        console.error(args.json ? JSON.stringify(sourcePayload, null, 2) : formatSourceAuditText(sourcePayload));
        process.exitCode = 1;
        return;
    }

    if (args.auditSource) {
        console.log(args.json ? JSON.stringify(sourcePayload, null, 2) : formatSourceAuditText(sourcePayload));
        return;
    }

    if (!args.sampleCsv) {
        throw new Error('Missing required --sample-csv <path> unless --audit-source is used');
    }

    const dryRunPayload = await buildDryRun(args, resolvedManifestPath, manifest, validation);
    console.log(args.json ? JSON.stringify(dryRunPayload, null, 2) : formatDryRunText(dryRunPayload));
}

main().catch(error => {
    console.error(
        JSON.stringify(
            {
                mode: 'real-finished-csv-staging-dry-run',
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
