#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: read-only score/result backfill dry-run for Ligue 1 2025/2026 only

const PHASE = 'SCORE_BACKFILL_DRY_RUN';
const CONTRACT_CARRIER = 'matches.home_score + matches.away_score + matches.actual_result';
const TARGET_LEAGUE = 'Ligue 1';
const TARGET_SEASON = '2025/2026';
const TARGET_SOURCE_TYPE = 'fotmob_live_fetch';
const TARGET_EVIDENCE_LEVEL = 'strong';
const TARGET_DATA_VERSION = 'fotmob_live_v1';
const DEFAULT_SAMPLE_LIMIT = 5;
const MAX_SAMPLE_LIMIT = 10;
const { assertDbWriteAllowed } = require('./helpers/db_write_guard');
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';
const VALID_ACTUAL_RESULTS = new Set(['home_win', 'draw', 'away_win']);
const HDA_BY_RESULT = Object.freeze({
    home_win: 'H',
    draw: 'D',
    away_win: 'A',
});

const SCAN_SQL = `
WITH fotmob_live_raw AS (
    SELECT
        rd.match_id,
        COUNT(*) FILTER (WHERE rd.data_version = 'fotmob_live_v1') AS fotmob_live_v1_count,
        MAX(CASE WHEN rd.data_version = 'fotmob_live_v1' THEN rd.data_version END) AS fotmob_live_v1_data_version,
        MAX(CASE WHEN rd.data_version = 'fotmob_live_v1' THEN rd.raw_data #>> '{header,status,scoreStr}' END) AS raw_score_str,
        MAX(CASE WHEN rd.data_version = 'fotmob_live_v1' THEN rd.raw_data #>> '{header,teams,0,score}' END) AS raw_home_score_text,
        MAX(CASE WHEN rd.data_version = 'fotmob_live_v1' THEN rd.raw_data #>> '{header,teams,1,score}' END) AS raw_away_score_text
    FROM raw_match_data rd
    GROUP BY rd.match_id
)
SELECT
    m.match_id,
    m.external_id,
    m.league_name,
    m.season,
    m.status,
    m.pipeline_status,
    m.source_type,
    m.evidence_level,
    m.home_score,
    m.away_score,
    m.actual_result,
    COALESCE(fr.fotmob_live_v1_count, 0) AS fotmob_live_v1_count,
    fr.fotmob_live_v1_data_version,
    fr.raw_score_str,
    fr.raw_home_score_text,
    fr.raw_away_score_text
FROM matches m
LEFT JOIN fotmob_live_raw fr
  ON fr.match_id = m.match_id
ORDER BY
    CASE
        WHEN m.league_name = $1
         AND m.season = $2
        THEN 0
        ELSE 1
    END,
    m.league_name ASC,
    m.season ASC,
    m.match_id ASC
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/score_backfill_dry_run.js [--json] [--sample-limit 5] [--allow-write]',
        '',
        'Options:',
        '  --json            JSON output',
        '  --sample-limit N  Number of sample rows (max 10)',
        '  --allow-write     Execute real score backfill write (requires --json)',
        '',
        'Safety:',
        '  Default is dry-run. Real write only with --allow-write --json.',
        '  Single transaction, strict WHERE, rollback on failure.',
        '  No migration, no schema change, no raw write, no live fetch.',
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

function parseIntegerOption(value, fallback = null) {
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
        json: false,
        help: false,
        sampleLimit: DEFAULT_SAMPLE_LIMIT,
        allowWrite: false,
    };

    const keyMap = {
        json: 'json',
        help: 'help',
        h: 'help',
        'sample-limit': 'sampleLimit',
        sample_limit: 'sampleLimit',
        'allow-write': 'allowWrite',
        allow_write: 'allowWrite',
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

        if (optionKey === 'json' || optionKey === 'help' || optionKey === 'allowWrite') {
            options[optionKey] = true;
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : String(value).trim();
    }

    const parsedSampleLimit = parseIntegerOption(options.sampleLimit, DEFAULT_SAMPLE_LIMIT);
    if (!Number.isInteger(parsedSampleLimit) || parsedSampleLimit <= 0) {
        throw new Error(`Invalid --sample-limit value: ${options.sampleLimit}`);
    }

    options.sampleLimit = Math.min(parsedSampleLimit, MAX_SAMPLE_LIMIT);
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

function toIntegerOrNull(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }

    if (typeof value === 'number' && Number.isInteger(value)) {
        return value;
    }

    const normalized = String(value).trim();
    if (!/^-?\d+$/.test(normalized)) {
        return null;
    }

    return Number.parseInt(normalized, 10);
}

function normalizeOptionalText(value) {
    const normalized = String(value ?? '').trim();
    return normalized ? normalized : null;
}

function parseScoreStr(scoreStr) {
    const normalized = normalizeOptionalText(scoreStr);
    if (!normalized) {
        return null;
    }

    const match = normalized.match(/(\d+)\s*[-:–]\s*(\d+)/);
    if (!match) {
        return null;
    }

    return {
        home: Number.parseInt(match[1], 10),
        away: Number.parseInt(match[2], 10),
    };
}

function deriveActualResult(homeScore, awayScore) {
    if (!Number.isInteger(homeScore) || !Number.isInteger(awayScore)) {
        return null;
    }
    if (homeScore > awayScore) {
        return 'home_win';
    }
    if (homeScore < awayScore) {
        return 'away_win';
    }
    return 'draw';
}

function mapActualResultToHda(actualResult) {
    return HDA_BY_RESULT[actualResult] || null;
}

function isTargetScope(row) {
    return row.league_name === TARGET_LEAGUE && row.season === TARGET_SEASON;
}

function isAllCurrentScoreFieldsNull(row) {
    return row.home_score === null && row.away_score === null && normalizeOptionalText(row.actual_result) === null;
}

function buildMatchValidations(row, derived) {
    const teamScoresAvailable =
        Number.isInteger(derived.proposedHomeScore) &&
        Number.isInteger(derived.proposedAwayScore);

    return {
        target_scope: derived.targetScope,
        status_finished: String(row.status || '').trim().toLowerCase() === 'finished',
        pipeline_status_harvested: String(row.pipeline_status || '').trim().toLowerCase() === 'harvested',
        source_type_fotmob_live_fetch: row.source_type === TARGET_SOURCE_TYPE,
        evidence_level_strong: row.evidence_level === TARGET_EVIDENCE_LEVEL,
        current_score_fields_null: isAllCurrentScoreFieldsNull(row),
        raw_single: derived.fotmobLiveV1Count === 1,
        raw_data_version_fotmob_live_v1: row.fotmob_live_v1_data_version === TARGET_DATA_VERSION,
        raw_score_str_available: derived.rawScoreFromScoreStr !== null,
        raw_team_scores_available: teamScoresAvailable,
        score_str_matches_team_scores:
            derived.rawScoreFromScoreStr !== null &&
            teamScoresAvailable &&
            derived.rawScoreFromScoreStr.home === derived.proposedHomeScore &&
            derived.rawScoreFromScoreStr.away === derived.proposedAwayScore,
        proposed_scores_non_null: teamScoresAvailable,
        proposed_actual_result_valid: VALID_ACTUAL_RESULTS.has(derived.proposedActualResult),
    };
}

function buildSkipReasons(validations, fotmobLiveV1Count) {
    const skipReasons = [];

    const simpleFailures = [
        ['target_scope', 'excluded_non_target_scope'],
        ['status_finished', 'status_not_finished'],
        ['pipeline_status_harvested', 'pipeline_status_not_harvested'],
        ['source_type_fotmob_live_fetch', 'source_type_not_fotmob_live_fetch'],
        ['evidence_level_strong', 'evidence_level_not_strong'],
        ['current_score_fields_null', 'current_scores_already_present'],
        ['raw_data_version_fotmob_live_v1', 'raw_data_version_not_fotmob_live_v1'],
        ['raw_score_str_available', 'raw_score_str_unavailable'],
        ['raw_team_scores_available', 'raw_team_scores_unavailable'],
        ['proposed_actual_result_valid', 'proposed_actual_result_invalid'],
    ];

    for (const [validationKey, reason] of simpleFailures) {
        if (!validations[validationKey]) {
            skipReasons.push(reason);
        }
    }

    if (!validations.raw_single) {
        skipReasons.push(
            fotmobLiveV1Count === 0
                ? 'missing_fotmob_live_v1_raw'
                : 'unexpected_fotmob_live_v1_row_count'
        );
    }

    if (
        validations.raw_score_str_available &&
        validations.raw_team_scores_available &&
        !validations.score_str_matches_team_scores
    ) {
        skipReasons.push('score_str_mismatch');
    }

    return skipReasons;
}

function classifyScannedMatch(row) {
    const rawScoreFromTeams = {
        home: toIntegerOrNull(row.raw_home_score_text),
        away: toIntegerOrNull(row.raw_away_score_text),
    };
    const proposedHomeScore = rawScoreFromTeams.home;
    const proposedAwayScore = rawScoreFromTeams.away;
    const proposedActualResult = deriveActualResult(proposedHomeScore, proposedAwayScore);
    const derived = {
        fotmobLiveV1Count: toIntegerOrNull(row.fotmob_live_v1_count) || 0,
        rawScoreFromScoreStr: parseScoreStr(row.raw_score_str),
        proposedHomeScore,
        proposedAwayScore,
        proposedActualResult,
        targetScope: isTargetScope(row),
    };
    const validations = buildMatchValidations(row, derived);
    const wouldUpdate = Object.values(validations).every(Boolean);
    const skipReasons = buildSkipReasons(validations, derived.fotmobLiveV1Count);

    return {
        match_id: row.match_id,
        external_id: normalizeOptionalText(row.external_id),
        league_name: row.league_name,
        season: row.season,
        status: row.status,
        pipeline_status: row.pipeline_status,
        source_type: row.source_type,
        evidence_level: row.evidence_level,
        current_home_score: row.home_score,
        current_away_score: row.away_score,
        current_actual_result: normalizeOptionalText(row.actual_result),
        fotmob_live_v1_count: derived.fotmobLiveV1Count,
        raw_data_version: normalizeOptionalText(row.fotmob_live_v1_data_version),
        raw_score_str_available: validations.raw_score_str_available,
        raw_team_scores_available: validations.raw_team_scores_available,
        target_scope: derived.targetScope,
        proposed_home_score: proposedHomeScore,
        proposed_away_score: proposedAwayScore,
        proposed_actual_result: proposedActualResult,
        proposed_actual_result_hda: mapActualResultToHda(proposedActualResult),
        validations,
        would_update: wouldUpdate,
        skip_reasons: skipReasons,
    };
}

function countDistribution(rows, keyFn) {
    const distribution = {};
    for (const row of rows) {
        const key = keyFn(row);
        if (key === null || key === undefined || key === '') {
            continue;
        }
        distribution[key] = (distribution[key] || 0) + 1;
    }
    return distribution;
}

function countValidation(rows, key) {
    return rows.filter(row => row.validations?.[key] === true).length;
}

function selectSampleRows(rows, limit) {
    return rows.slice(0, Math.max(0, limit));
}

function formatSampleUpdate(row) {
    return {
        match_id: row.match_id,
        external_id: row.external_id,
        proposed_home_score: row.proposed_home_score,
        proposed_away_score: row.proposed_away_score,
        proposed_actual_result: row.proposed_actual_result,
    };
}

function formatSampleSkip(row) {
    return {
        match_id: row.match_id,
        external_id: row.external_id,
        league_name: row.league_name,
        season: row.season,
        status: row.status,
        pipeline_status: row.pipeline_status,
        skip_reasons: row.skip_reasons,
    };
}

function buildRiskFlags({ targetRows, wouldUpdateRows, skipRows, scoreConsistencySummary }) {
    const flags = [
        'dry_run_only_no_db_write',
        'real_score_backfill_requires_explicit_user_authorization',
        'actual_result_encoding_locked_to_home_win_draw_away_win',
    ];

    if (wouldUpdateRows.length !== targetRows.length) {
        flags.push(`target_gap_detected:${targetRows.length - wouldUpdateRows.length}`);
    }

    const noRawExcludedCount = skipRows.filter(row => row.skip_reasons.includes('missing_fotmob_live_v1_raw')).length;
    if (noRawExcludedCount !== 2) {
        flags.push(`unexpected_missing_raw_skip_count:${noRawExcludedCount}`);
    }

    if (scoreConsistencySummary.score_str_mismatch_count > 0) {
        flags.push(`score_str_mismatch_detected:${scoreConsistencySummary.score_str_mismatch_count}`);
    }

    return flags;
}

function buildDryRunPayload(classifiedRows, options = {}) {
    const targetRows = classifiedRows.filter(row => row.target_scope);
    const wouldUpdateRows = classifiedRows.filter(row => row.would_update);
    const skipRows = classifiedRows.filter(row => !row.would_update);
    const excludedNoRawRows = skipRows.filter(row => row.skip_reasons.includes('missing_fotmob_live_v1_raw'));

    const targetValidationSummary = {
        target_count: targetRows.length,
        status_finished_count: countValidation(targetRows, 'status_finished'),
        pipeline_status_harvested_count: countValidation(targetRows, 'pipeline_status_harvested'),
        source_type_fotmob_live_fetch_count: countValidation(targetRows, 'source_type_fotmob_live_fetch'),
        evidence_level_strong_count: countValidation(targetRows, 'evidence_level_strong'),
        current_score_fields_null_count: countValidation(targetRows, 'current_score_fields_null'),
        raw_single_count: countValidation(targetRows, 'raw_single'),
        raw_data_version_fotmob_live_v1_count: countValidation(targetRows, 'raw_data_version_fotmob_live_v1'),
        raw_score_str_available_count: countValidation(targetRows, 'raw_score_str_available'),
        raw_team_scores_available_count: countValidation(targetRows, 'raw_team_scores_available'),
        score_str_matches_team_scores_count: countValidation(targetRows, 'score_str_matches_team_scores'),
        proposed_scores_non_null_count: countValidation(targetRows, 'proposed_scores_non_null'),
        proposed_actual_result_valid_count: countValidation(targetRows, 'proposed_actual_result_valid'),
    };

    const scoreConsistencySummary = {
        target_rows_checked: targetRows.length,
        raw_single_count: targetValidationSummary.raw_single_count,
        score_str_available_count: targetValidationSummary.raw_score_str_available_count,
        team_score_available_count: targetValidationSummary.raw_team_scores_available_count,
        score_str_matches_team_scores_count: targetValidationSummary.score_str_matches_team_scores_count,
        score_str_mismatch_count:
            targetRows.length - targetValidationSummary.score_str_matches_team_scores_count,
    };

    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        contract_carrier: CONTRACT_CARRIER,
        script: 'scripts/ops/score_backfill_dry_run.js',
        generated_at: new Date().toISOString(),
        target_scope: {
            league_name: TARGET_LEAGUE,
            season: TARGET_SEASON,
        },
        total_matches_scanned: classifiedRows.length,
        target_ligue1_count: targetRows.length,
        would_update_count: wouldUpdateRows.length,
        would_skip_count: skipRows.length,
        excluded_no_raw_count: excludedNoRawRows.length,
        score_source_paths: [
            'raw_data.header.teams[0].score',
            'raw_data.header.teams[1].score',
            'raw_data.header.status.scoreStr',
        ],
        target_validation_summary: targetValidationSummary,
        score_consistency_summary: scoreConsistencySummary,
        actual_result_distribution: countDistribution(
            wouldUpdateRows,
            row => row.proposed_actual_result
        ),
        auxiliary_result_distribution_hda: countDistribution(
            wouldUpdateRows,
            row => row.proposed_actual_result_hda
        ),
        sample_updates: selectSampleRows(wouldUpdateRows, options.sampleLimit || DEFAULT_SAMPLE_LIMIT)
            .map(formatSampleUpdate),
        sample_skips: selectSampleRows(skipRows, options.sampleLimit || DEFAULT_SAMPLE_LIMIT)
            .map(formatSampleSkip),
        excluded_no_raw_match_ids: excludedNoRawRows.map(row => row.match_id),
        risk_flags: buildRiskFlags({
            targetRows,
            wouldUpdateRows,
            skipRows,
            scoreConsistencySummary,
        }),
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            raw_match_data_write_allowed: false,
            backfill_executed: false,
            live_fetch_allowed: false,
            raw_payload_output_allowed: false,
            parser_change_in_scope: false,
            training_change_in_scope: false,
            prediction_change_in_scope: false,
            read_only_transaction_used: true,
        },
    };
}

async function scanMatchesForDryRun(dependencies = {}) {
    const connection = await openReadOnlyClient(dependencies);
    let rolledBack = false;

    try {
        await querySelectOnly(connection.client, READ_ONLY_BEGIN_SQL);
        const result = await querySelectOnly(connection.client, SCAN_SQL, [TARGET_LEAGUE, TARGET_SEASON]);
        await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
        rolledBack = true;
        return result.rows || [];
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

async function runDryRun(options = {}, dependencies = {}) {
    const scannedRows = await scanMatchesForDryRun(dependencies);
    const classifiedRows = scannedRows.map(classifyScannedMatch);
    return buildDryRunPayload(classifiedRows, options);
}

function payloadToText(payload) {
    const actualResultDistribution = Object.entries(payload.actual_result_distribution || {})
        .map(([key, value]) => `  ${key}: ${value}`)
        .join('\n') || '  none';
    const riskFlags = (payload.risk_flags || []).map(flag => `  - ${flag}`).join('\n') || '  - none';

    return [
        '[DRY-RUN] Score backfill preflight',
        `Phase: ${payload.phase}`,
        `Mode: ${payload.mode}`,
        `Actual update executed: ${payload.actual_update_executed}`,
        `Target scope: ${payload.target_scope.league_name} / ${payload.target_scope.season}`,
        `Total matches scanned: ${payload.total_matches_scanned}`,
        `Target Ligue 1 count: ${payload.target_ligue1_count}`,
        `Would update count: ${payload.would_update_count}`,
        `Would skip count: ${payload.would_skip_count}`,
        'Actual result distribution:',
        actualResultDistribution,
        'Risk flags:',
        riskFlags,
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
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        contract_carrier: CONTRACT_CARRIER,
        script: 'scripts/ops/score_backfill_dry_run.js',
        target_scope: {
            league_name: TARGET_LEAGUE,
            season: TARGET_SEASON,
        },
        sample_limit: options.sampleLimit || DEFAULT_SAMPLE_LIMIT,
        errors: [error.message],
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            raw_match_data_write_allowed: false,
            backfill_executed: false,
            live_fetch_allowed: false,
            raw_payload_output_allowed: false,
            parser_change_in_scope: false,
            training_change_in_scope: false,
            prediction_change_in_scope: false,
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
        json: false,
        help: false,
        sampleLimit: DEFAULT_SAMPLE_LIMIT,
        allowWrite: false,
    };

    try {
        options = parseArgs(argv);
        if (options.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }

        if (options.allowWrite) {
            if (!options.json) {
                output.stderr('Error: --allow-write requires --json\n');
                return 1;
            }
            assertDbWriteAllowed({
                script: 'score_backfill_dry_run.js',
                tables: ['matches'],
                operations: ['UPDATE'],
            });
            // Lazy-require write module — only loaded when explicitly authorized
            const { runWrite } = require('./score_backfill_write');
            const payload = await runWrite(options);
            writePayload(payload, true, output);
            return 0;
        }

        const payload = await runDryRun(options);
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
    TARGET_LEAGUE,
    TARGET_SEASON,
    TARGET_SOURCE_TYPE,
    TARGET_EVIDENCE_LEVEL,
    TARGET_DATA_VERSION,
    DEFAULT_SAMPLE_LIMIT,
    MAX_SAMPLE_LIMIT,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    SCAN_SQL,
    parseArgs,
    buildDbConfig,
    openReadOnlyClient,
    assertSelectOnlySql,
    querySelectOnly,
    toIntegerOrNull,
    normalizeOptionalText,
    parseScoreStr,
    deriveActualResult,
    mapActualResultToHda,
    isTargetScope,
    isAllCurrentScoreFieldsNull,
    classifyScannedMatch,
    countDistribution,
    countValidation,
    selectSampleRows,
    formatSampleUpdate,
    formatSampleSkip,
    buildRiskFlags,
    buildDryRunPayload,
    scanMatchesForDryRun,
    runDryRun,
    payloadToText,
    buildFailurePayload,
    main,
};
