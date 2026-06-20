#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: read-only formal training cohort inventory dry-run

const PHASE = 'FORMAL_TRAINING_COHORT_INVENTORY_DRY_RUN';
const SCRIPT_PATH = 'scripts/ops/formal_training_cohort_inventory_dry_run.js';
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';

const FORMAL_VOLUME_THRESHOLDS = Object.freeze([1500, 3000, 5000]);
const VALID_LABELS = Object.freeze(['home_win', 'draw', 'away_win']);
const VALID_LABEL_SET = new Set(VALID_LABELS);
const EXPLICIT_EXCLUDED_MATCH_IDS = Object.freeze([
    '47_20242025_900002',
    '140_20252026_4837496',
]);

const COUNTS_SQL = `
WITH formal_candidates AS (
    SELECT m.match_id
    FROM matches m
    WHERE m.status = 'finished'
      AND m.actual_result IN ('home_win', 'draw', 'away_win')
      AND m.is_training_eligible = true
      AND NOT (m.match_id = ANY($1::text[]))
)
SELECT
    (SELECT COUNT(*) FROM matches) AS total_matches,
    (SELECT COUNT(*) FROM matches WHERE status = 'finished' AND actual_result IN ('home_win', 'draw', 'away_win')) AS finished_labeled_matches,
    (SELECT COUNT(*) FROM matches WHERE is_training_eligible = true) AS training_eligible_matches,
    (SELECT COUNT(*) FROM formal_candidates) AS formal_candidate_matches,
    (SELECT COUNT(*) FROM raw_match_data) AS raw_match_data_rows,
    (SELECT COUNT(DISTINCT match_id) FROM raw_match_data) AS raw_match_data_distinct_matches,
    (SELECT COUNT(*) FROM raw_match_data WHERE data_version = 'fotmob_pageprops_v2') AS fotmob_pageprops_v2_rows,
    (SELECT COUNT(DISTINCT match_id) FROM raw_match_data WHERE data_version = 'fotmob_pageprops_v2') AS fotmob_pageprops_v2_matches,
    (SELECT COUNT(*) FROM bookmaker_odds_history) AS odds_rows,
    (SELECT COUNT(DISTINCT match_id) FROM bookmaker_odds_history) AS odds_matches,
    (SELECT COUNT(DISTINCT o.match_id)
     FROM bookmaker_odds_history o
     INNER JOIN formal_candidates c ON c.match_id = o.match_id) AS formal_candidates_with_odds,
    (SELECT COUNT(DISTINCT r.match_id)
     FROM raw_match_data r
     INNER JOIN formal_candidates c ON c.match_id = r.match_id
     WHERE r.data_version = 'fotmob_pageprops_v2') AS formal_candidates_with_pageprops_v2
`;

const LEAGUE_SEASON_SQL = `
SELECT
    league_name,
    season,
    COUNT(*) AS matches,
    COUNT(*) FILTER (WHERE status = 'finished' AND actual_result IN ('home_win', 'draw', 'away_win')) AS finished_labeled,
    COUNT(*) FILTER (WHERE is_training_eligible = true) AS training_eligible,
    COUNT(*) FILTER (
        WHERE status = 'finished'
          AND actual_result IN ('home_win', 'draw', 'away_win')
          AND is_training_eligible = true
          AND NOT (match_id = ANY($1::text[]))
    ) AS formal_candidates
FROM matches
GROUP BY league_name, season
ORDER BY matches DESC, league_name ASC, season ASC
`;

const FINISHED_LABEL_DISTRIBUTION_SQL = `
SELECT
    league_name,
    season,
    actual_result,
    COUNT(*) AS count
FROM matches
WHERE status = 'finished'
  AND actual_result IN ('home_win', 'draw', 'away_win')
GROUP BY league_name, season, actual_result
ORDER BY league_name ASC, season ASC, actual_result ASC
`;

const TRAINING_ELIGIBLE_DISTRIBUTION_SQL = `
SELECT
    league_name,
    season,
    actual_result,
    COUNT(*) AS count
FROM matches
WHERE is_training_eligible = true
GROUP BY league_name, season, actual_result
ORDER BY league_name ASC, season ASC, actual_result ASC
`;

const RAW_VERSION_SQL = `
SELECT
    COALESCE(data_version, 'unknown') AS raw_version,
    COALESCE(
        raw_data -> '_meta' ->> 'source_version',
        raw_data -> '_meta' ->> 'raw_source_version',
        raw_data -> '_meta' ->> 'payload_version',
        raw_data ->> 'source_version',
        'unknown'
    ) AS source_version,
    COALESCE(raw_data -> '_meta' ->> 'hash_strategy', 'unknown') AS hash_strategy,
    COUNT(*) AS rows,
    COUNT(DISTINCT match_id) AS distinct_matches
FROM raw_match_data
GROUP BY raw_version, source_version, hash_strategy
ORDER BY rows DESC, raw_version ASC, source_version ASC, hash_strategy ASC
`;

const MISSING_FIELDS_SQL = `
SELECT
    COUNT(*) AS total_matches,
    COUNT(*) FILTER (WHERE external_id IS NULL OR BTRIM(external_id) = '') AS external_id_missing,
    COUNT(*) FILTER (WHERE league_name IS NULL OR BTRIM(league_name) = '') AS league_name_missing,
    COUNT(*) FILTER (WHERE season IS NULL OR BTRIM(season) = '') AS season_missing,
    COUNT(*) FILTER (WHERE home_team IS NULL OR BTRIM(home_team) = '') AS home_team_missing,
    COUNT(*) FILTER (WHERE away_team IS NULL OR BTRIM(away_team) = '') AS away_team_missing,
    COUNT(*) FILTER (WHERE match_date IS NULL) AS match_date_missing,
    COUNT(*) FILTER (WHERE venue IS NULL OR BTRIM(venue) = '') AS venue_missing,
    COUNT(*) FILTER (WHERE referee IS NULL OR BTRIM(referee) = '') AS referee_missing,
    COUNT(*) FILTER (WHERE status = 'finished' AND (home_score IS NULL OR away_score IS NULL)) AS finished_score_missing,
    COUNT(*) FILTER (WHERE status = 'finished' AND actual_result IS NULL) AS finished_label_missing,
    COUNT(*) FILTER (WHERE is_training_eligible = true AND actual_result IS NULL) AS training_eligible_label_missing,
    COUNT(*) FILTER (WHERE is_training_eligible = true AND status <> 'finished') AS training_eligible_not_finished
FROM matches
`;

const MATCHES_COLUMNS_SQL = `
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'matches'
ORDER BY ordinal_position
`;

const FORMAL_CANDIDATES_SQL = `
SELECT
    m.match_id,
    m.external_id,
    m.league_name,
    m.season,
    m.home_team,
    m.away_team,
    m.match_date::text AS match_date,
    m.actual_result,
    EXISTS (
        SELECT 1 FROM raw_match_data r
        WHERE r.match_id = m.match_id
          AND r.data_version = 'fotmob_pageprops_v2'
    ) AS has_fotmob_pageprops_v2,
    EXISTS (
        SELECT 1 FROM bookmaker_odds_history o
        WHERE o.match_id = m.match_id
    ) AS has_odds
FROM matches m
WHERE m.status = 'finished'
  AND m.actual_result IN ('home_win', 'draw', 'away_win')
  AND m.is_training_eligible = true
  AND NOT (m.match_id = ANY($1::text[]))
ORDER BY m.match_date ASC NULLS LAST, m.match_id ASC
`;

const EXCLUDED_MATCHES_SQL = `
SELECT
    m.match_id,
    m.external_id,
    m.league_name,
    m.season,
    m.home_team,
    m.away_team,
    m.status,
    m.is_finished,
    m.actual_result,
    m.source_type,
    m.evidence_level,
    m.is_production_scope,
    m.is_reconciliation_eligible,
    m.is_training_eligible,
    m.pipeline_status,
    m.pipeline_status_reason,
    EXISTS (SELECT 1 FROM raw_match_data r WHERE r.match_id = m.match_id) AS has_raw,
    EXISTS (
        SELECT 1 FROM raw_match_data r
        WHERE r.match_id = m.match_id
          AND r.data_version = 'fotmob_pageprops_v2'
    ) AS has_fotmob_pageprops_v2,
    EXISTS (SELECT 1 FROM bookmaker_odds_history o WHERE o.match_id = m.match_id) AS has_odds
FROM matches m
WHERE m.match_id = ANY($1::text[])
ORDER BY m.match_id ASC
`;

function usage() {
    return [
        'Usage:',
        `  node ${SCRIPT_PATH} [--json]`,
        '',
        'Safety:',
        '  Read-only inventory only. No DB write, no live fetch, no raw payload output,',
        '  no training, no model artifact, no governance state mutation.',
    ].join('\n');
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = { json: false, help: false };
    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (arg === '--json') {
            options.json = true;
        } else if (arg === '--help' || arg === '-h') {
            options.help = true;
        } else {
            throw new Error(`Unknown argument: ${arg}`);
        }
    }
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

async function openReadOnlyClient(dependencies = {}) {
    if (dependencies.client) {
        return { client: dependencies.client, close: async () => {} };
    }

    const { Pool } = require('pg');
    const pool = new Pool(buildDbConfig());
    const client = await pool.connect();

    return {
        client,
        close: async () => {
            if (typeof client.release === 'function') {
                client.release();
            }
            await pool.end();
        },
    };
}

function assertSelectOnlySql(sql) {
    const normalized = String(sql || '').replace(/\s+/g, ' ').trim().toUpperCase();
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

function toInt(value) {
    return Number.parseInt(value ?? '0', 10) || 0;
}

function normalizeCountRow(row = {}) {
    return Object.fromEntries(Object.entries(row).map(([key, value]) => [key, toInt(value)]));
}

function normalizeLeagueSeasonRows(rows = []) {
    return rows.map(row => ({
        league_name: row.league_name,
        season: row.season,
        matches: toInt(row.matches),
        finished_labeled: toInt(row.finished_labeled),
        training_eligible: toInt(row.training_eligible),
        formal_candidates: toInt(row.formal_candidates),
    }));
}

function normalizeDistributionRows(rows = []) {
    return rows.map(row => ({
        league_name: row.league_name,
        season: row.season,
        actual_result: row.actual_result,
        count: toInt(row.count),
    }));
}

function normalizeRawVersionRows(rows = []) {
    return rows.map(row => ({
        raw_version: row.raw_version,
        source_version: row.source_version,
        hash_strategy: row.hash_strategy,
        rows: toInt(row.rows),
        distinct_matches: toInt(row.distinct_matches),
    }));
}

function normalizeColumnRows(rows = []) {
    return rows.map(row => String(row.column_name));
}

function normalizeCandidateRows(rows = []) {
    return rows.map(row => ({
        match_id: row.match_id,
        external_id: row.external_id,
        league_name: row.league_name,
        season: row.season,
        home_team: row.home_team,
        away_team: row.away_team,
        match_date: row.match_date,
        actual_result: row.actual_result,
        has_fotmob_pageprops_v2: row.has_fotmob_pageprops_v2 === true,
        has_odds: row.has_odds === true,
    }));
}

function buildExcludedRows(rows = [], explicitIds = EXPLICIT_EXCLUDED_MATCH_IDS) {
    const byId = new Map(rows.map(row => [row.match_id, row]));

    return explicitIds.map(matchId => {
        const row = byId.get(matchId);
        if (!row) {
            return {
                match_id: matchId,
                present_in_db: false,
                must_exclude: true,
                reason: 'explicit_policy_exclusion_not_present_in_current_db',
            };
        }

        return {
            match_id: row.match_id,
            external_id: row.external_id,
            league_name: row.league_name,
            season: row.season,
            home_team: row.home_team,
            away_team: row.away_team,
            status: row.status,
            actual_result: row.actual_result,
            source_type: row.source_type,
            evidence_level: row.evidence_level,
            is_production_scope: row.is_production_scope,
            is_reconciliation_eligible: row.is_reconciliation_eligible,
            is_training_eligible: row.is_training_eligible,
            pipeline_status: row.pipeline_status,
            pipeline_status_reason: row.pipeline_status_reason,
            has_raw: row.has_raw === true,
            has_fotmob_pageprops_v2: row.has_fotmob_pageprops_v2 === true,
            has_odds: row.has_odds === true,
            present_in_db: true,
            must_exclude: true,
            reason: buildExplicitExclusionReason(row),
        };
    });
}

function buildExplicitExclusionReason(row) {
    if (row.match_id === '47_20242025_900002') {
        return 'synthetic_invalid_legacy_sample_not_real_fotmob_evidence';
    }
    if (row.match_id === '140_20252026_4837496') {
        return 'scheduled_or_no_valid_outcome_with_synthetic_invalid_evidence';
    }
    if (row.evidence_level === 'synthetic_invalid' || row.source_type === 'synthetic') {
        return 'synthetic_or_invalid_evidence';
    }
    if (row.status !== 'finished') {
        return `not_finished_status_${row.status || 'unknown'}`;
    }
    if (!VALID_LABEL_SET.has(row.actual_result)) {
        return 'missing_or_invalid_label';
    }
    return 'explicit_policy_exclusion';
}

function buildThresholdGaps(candidateCount, thresholds = FORMAL_VOLUME_THRESHOLDS) {
    return thresholds.map(threshold => ({
        threshold,
        current_formal_candidate_matches: candidateCount,
        gap: Math.max(threshold - candidateCount, 0),
        reached: candidateCount >= threshold,
    }));
}

function buildSevereMissingFields(state) {
    const missing = [];
    const total = state.missing_fields.total_matches;
    const schemaMissing = [
        'home_team_id',
        'away_team_id',
        'league_id',
        'prediction_cutoff_time',
        'feature_observed_at',
    ].filter(column => !state.matches_columns.includes(column));

    for (const column of schemaMissing) {
        missing.push({
            field: column,
            layer: 'schema',
            severity: 'formal_training_blocker',
            detail: 'column_absent_from_matches',
        });
    }

    for (const [field, count] of Object.entries(state.missing_fields)) {
        if (field === 'total_matches' || count === 0) {
            continue;
        }
        const missingRate = total === 0 ? 0 : Number((count / total).toFixed(6));
        const severity = count === total ? 'complete_gap' : 'partial_gap';
        missing.push({ field, layer: 'matches', severity, missing_count: count, total_matches: total, missing_rate: missingRate });
    }

    if (state.counts.formal_candidates_with_pageprops_v2 < state.counts.formal_candidate_matches) {
        missing.push({
            field: 'fotmob_pageprops_v2_coverage',
            layer: 'raw_match_data',
            severity: 'formal_training_blocker',
            missing_count: state.counts.formal_candidate_matches - state.counts.formal_candidates_with_pageprops_v2,
            total_matches: state.counts.formal_candidate_matches,
        });
    }

    if (state.counts.formal_candidates_with_odds < state.counts.formal_candidate_matches) {
        missing.push({
            field: 'odds_coverage',
            layer: 'bookmaker_odds_history',
            severity: 'formal_training_blocker',
            missing_count: state.counts.formal_candidate_matches - state.counts.formal_candidates_with_odds,
            total_matches: state.counts.formal_candidate_matches,
        });
    }

    return missing;
}

async function collectInventoryState(dependencies = {}) {
    const connection = await openReadOnlyClient(dependencies);
    let rolledBack = false;

    try {
        await querySelectOnly(connection.client, READ_ONLY_BEGIN_SQL);

        const counts = normalizeCountRow(
            (await querySelectOnly(connection.client, COUNTS_SQL, [EXPLICIT_EXCLUDED_MATCH_IDS])).rows[0]
        );
        const leagueSeasonCoverage = normalizeLeagueSeasonRows(
            (await querySelectOnly(connection.client, LEAGUE_SEASON_SQL, [EXPLICIT_EXCLUDED_MATCH_IDS])).rows
        );
        const finishedLabelDistribution = normalizeDistributionRows(
            (await querySelectOnly(connection.client, FINISHED_LABEL_DISTRIBUTION_SQL)).rows
        );
        const trainingEligibleDistribution = normalizeDistributionRows(
            (await querySelectOnly(connection.client, TRAINING_ELIGIBLE_DISTRIBUTION_SQL)).rows
        );
        const rawVersionRows = normalizeRawVersionRows(
            (await querySelectOnly(connection.client, RAW_VERSION_SQL)).rows
        );
        const missingFields = normalizeCountRow(
            (await querySelectOnly(connection.client, MISSING_FIELDS_SQL)).rows[0]
        );
        const matchesColumns = normalizeColumnRows(
            (await querySelectOnly(connection.client, MATCHES_COLUMNS_SQL)).rows
        );
        const candidates = normalizeCandidateRows(
            (await querySelectOnly(connection.client, FORMAL_CANDIDATES_SQL, [EXPLICIT_EXCLUDED_MATCH_IDS])).rows
        );
        const excluded = buildExcludedRows(
            (await querySelectOnly(connection.client, EXCLUDED_MATCHES_SQL, [EXPLICIT_EXCLUDED_MATCH_IDS])).rows
        );

        await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
        rolledBack = true;

        return {
            counts,
            league_season_coverage: leagueSeasonCoverage,
            finished_label_distribution: finishedLabelDistribution,
            training_eligible_distribution: trainingEligibleDistribution,
            raw_version_distribution: rawVersionRows,
            missing_fields: missingFields,
            matches_columns: matchesColumns,
            formal_cohort_candidates: candidates,
            explicit_exclusions: excluded,
        };
    } finally {
        if (!rolledBack) {
            try {
                await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
            } catch {
                // Preserve the original failure.
            }
        }
        await connection.close();
    }
}

function buildPayload(state) {
    const candidateCount = state.counts.formal_candidate_matches;
    const thresholdGaps = buildThresholdGaps(candidateCount);
    const severeMissingFields = buildSevereMissingFields(state);

    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        script: SCRIPT_PATH,
        generated_at: new Date().toISOString(),
        inventory_basis:
            'formal_candidate = finished + actual_result in home_win/draw/away_win + is_training_eligible=true + explicit exclusions removed',
        volume_threshold_gaps: thresholdGaps,
        current_counts: state.counts,
        league_season_coverage: state.league_season_coverage,
        finished_labeled_distribution: state.finished_label_distribution,
        training_eligible_distribution: state.training_eligible_distribution,
        raw_match_data_versions: state.raw_version_distribution,
        coverage: {
            fotmob_pageprops_v2_matches: state.counts.fotmob_pageprops_v2_matches,
            fotmob_pageprops_v2_rows: state.counts.fotmob_pageprops_v2_rows,
            formal_candidates_with_pageprops_v2: state.counts.formal_candidates_with_pageprops_v2,
            odds_matches: state.counts.odds_matches,
            odds_rows: state.counts.odds_rows,
            formal_candidates_with_odds: state.counts.formal_candidates_with_odds,
        },
        severe_missing_fields: severeMissingFields,
        formal_cohort_candidates: {
            count: candidateCount,
            match_ids: state.formal_cohort_candidates.map(row => row.match_id),
            rows: state.formal_cohort_candidates,
        },
        must_exclude_matches: state.explicit_exclusions,
        conclusion: {
            current_58_rows_are_smoke_or_integration_only: state.counts.formal_candidate_matches === 58,
            formal_training_allowed_now: false,
            next_step_is_training: false,
            should_enter_multi_league_multi_season_expansion: candidateCount < 1500,
            recommendation:
                'Do multi-league multi-season data expansion planning next; real fetch, DB write, raw write, or model training must stop and request user authorization first.',
        },
        safety: {
            db_write_allowed: false,
            db_write_executed: false,
            live_fetch_allowed: false,
            live_fetch_executed: false,
            raw_payload_output_allowed: false,
            raw_payload_output_detected: false,
            model_training_performed: false,
            model_output_generated: false,
            governance_conclusion_changed: false,
            read_only_transaction_used: true,
        },
    };
}

function payloadToText(payload) {
    const gapLines = payload.volume_threshold_gaps
        .map(row => `  - ${row.threshold}: current=${row.current_formal_candidate_matches}, gap=${row.gap}`)
        .join('\n');
    const scopeLines = payload.league_season_coverage
        .map(row => `  - ${row.league_name} ${row.season}: matches=${row.matches}, finished_labeled=${row.finished_labeled}, training_eligible=${row.training_eligible}, formal_candidates=${row.formal_candidates}`)
        .join('\n');
    const rawLines = payload.raw_match_data_versions
        .map(row => `  - raw_version=${row.raw_version}, source_version=${row.source_version}, hash_strategy=${row.hash_strategy}, rows=${row.rows}, distinct_matches=${row.distinct_matches}`)
        .join('\n');
    const missingLines = payload.severe_missing_fields
        .map(row => `  - ${row.layer}.${row.field}: ${row.severity}, missing=${row.missing_count ?? 'n/a'}/${row.total_matches ?? 'n/a'}`)
        .join('\n');
    const exclusionLines = payload.must_exclude_matches
        .map(row => `  - ${row.match_id}: ${row.reason}`)
        .join('\n');
    const candidatePreview = payload.formal_cohort_candidates.match_ids.slice(0, 12).join(', ');

    return [
        `mode=${payload.mode}`,
        `actual_update_executed=${payload.actual_update_executed}`,
        `inventory_basis=${payload.inventory_basis}`,
        `formal_candidate_count=${payload.formal_cohort_candidates.count}`,
        'volume_threshold_gaps=',
        gapLines,
        'league_season_coverage=',
        scopeLines,
        `finished_labeled_matches=${payload.current_counts.finished_labeled_matches}`,
        `training_eligible_matches=${payload.current_counts.training_eligible_matches}`,
        'raw_match_data_versions=',
        rawLines,
        `fotmob_pageprops_v2_matches=${payload.coverage.fotmob_pageprops_v2_matches}`,
        `odds_matches=${payload.coverage.odds_matches}`,
        'severe_missing_fields=',
        missingLines,
        `formal_candidate_match_ids_preview=${candidatePreview}`,
        'must_exclude_matches=',
        exclusionLines,
        `should_enter_multi_league_multi_season_expansion=${payload.conclusion.should_enter_multi_league_multi_season_expansion}`,
        `next_step_is_training=${payload.conclusion.next_step_is_training}`,
        `recommendation=${payload.conclusion.recommendation}`,
    ].join('\n');
}

function writePayload(payload, json, io) {
    const output = json
        ? `${JSON.stringify(payload, null, 2)}\n`
        : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

function buildFailurePayload(error) {
    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        script: SCRIPT_PATH,
        errors: [error.message],
        safety: {
            db_write_allowed: false,
            db_write_executed: false,
            live_fetch_allowed: false,
            live_fetch_executed: false,
            raw_payload_output_allowed: false,
            raw_payload_output_detected: false,
            model_training_performed: false,
            model_output_generated: false,
            governance_conclusion_changed: false,
            read_only_transaction_used: true,
        },
    };
}

async function runDryRun(options = {}, dependencies = {}) {
    const state = await collectInventoryState(dependencies);
    return buildPayload(state);
}

async function main(argv = process.argv.slice(2), io = {}) {
    const output = {
        stdout: io.stdout || (text => process.stdout.write(text)),
        stderr: io.stderr || (text => process.stderr.write(text)),
    };
    let options = { json: false, help: false };

    try {
        options = parseArgs(argv);
        if (options.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }

        const payload = await runDryRun(options);
        writePayload(payload, options.json, output);
        return 0;
    } catch (error) {
        const payload = buildFailurePayload(error);
        writePayload(payload, options.json === true, output);
        return 1;
    }
}

if (require.main === module) {
    main().then(code => {
        process.exitCode = code;
    });
}

module.exports = {
    PHASE,
    SCRIPT_PATH,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    FORMAL_VOLUME_THRESHOLDS,
    VALID_LABELS,
    EXPLICIT_EXCLUDED_MATCH_IDS,
    COUNTS_SQL,
    LEAGUE_SEASON_SQL,
    FINISHED_LABEL_DISTRIBUTION_SQL,
    TRAINING_ELIGIBLE_DISTRIBUTION_SQL,
    RAW_VERSION_SQL,
    MISSING_FIELDS_SQL,
    MATCHES_COLUMNS_SQL,
    FORMAL_CANDIDATES_SQL,
    EXCLUDED_MATCHES_SQL,
    parseArgs,
    assertSelectOnlySql,
    normalizeCountRow,
    normalizeLeagueSeasonRows,
    normalizeDistributionRows,
    normalizeRawVersionRows,
    buildExcludedRows,
    buildThresholdGaps,
    buildSevereMissingFields,
    buildPayload,
    runDryRun,
};
