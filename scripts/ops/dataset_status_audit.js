#!/usr/bin/env node
/**
 * Phase 4.36 dataset status / sample audit gate.
 *
 * This script is deliberately SELECT-only. It reports training dataset
 * readiness without exporting files, training models, running prediction
 * pipelines, loading model artifacts, or calling external networks.
 */

'use strict';

const { Pool } = require('pg');

const FORBIDDEN_SQL =
    /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|UPSERT|MERGE|GRANT|REVOKE|CREATE\s+INDEX)\b/i;

const FINISHED_STATUSES = ['finished', 'completed', 'complete', 'ft', 'full_time'];
const MINIMUM_DISCUSSION_LABEL_ROWS = 200;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/dataset_status_audit.js [--json] [--match-id <id>]',
        '',
        'Safety:',
        '  SELECT-only dataset status audit. No training, prediction, DB writes, artifact loading, network calls, or file export.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        json: false,
        matchId: null,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--json') {
            args.json = true;
        } else if (token === '--match-id') {
            args.matchId = argv[index + 1];
            index += 1;
        } else if (token === '--help' || token === '-h') {
            args.help = true;
        } else {
            throw new Error(`Unknown argument: ${token}`);
        }
    }

    if (args.matchId === '') {
        throw new Error('--match-id requires a non-empty value');
    }

    return args;
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

function toInt(value) {
    if (value === null || value === undefined) return 0;
    return Number.parseInt(value, 10);
}

function normalizeCounts(row) {
    return Object.fromEntries(Object.entries(row).map(([key, value]) => [key, toInt(value)]));
}

function normalizeStatusRow(row) {
    return {
        status: row.status,
        is_finished: row.is_finished,
        actual_result_is_null: row.actual_result_is_null,
        score_complete: row.score_complete,
        rows: toInt(row.rows),
    };
}

function normalizeMatchFocus(row) {
    if (!row) return null;
    return {
        match_id: row.match_id,
        league_name: row.league_name,
        season: row.season,
        home_team: row.home_team,
        away_team: row.away_team,
        match_date: row.match_date ? new Date(row.match_date).toISOString() : null,
        status: row.status,
        is_finished: row.is_finished,
        actual_result: row.actual_result,
        scores_complete: row.scores_complete,
        has_raw_match_data: row.has_raw_match_data,
        has_l3_features: row.has_l3_features,
        has_training_features: row.has_training_features,
        has_odds_history: row.has_odds_history,
        has_prediction: row.has_prediction,
        trainable_label: row.trainable_label,
    };
}

function buildTrainingReadiness({ db, labelReadiness, featureReadiness }) {
    const trainableLabelRows = labelReadiness.trainable_label_rows;
    const fullFeatureChainRows = featureReadiness.full_feature_chain_rows;
    const enoughLabels = trainableLabelRows >= MINIMUM_DISCUSSION_LABEL_ROWS;
    const enoughFeatureChains = fullFeatureChainRows >= MINIMUM_DISCUSSION_LABEL_ROWS;
    const trainable = enoughLabels && enoughFeatureChains;

    let reason =
        `Current DB has ${trainableLabelRows} trainable labeled rows and ${fullFeatureChainRows} full feature-chain rows; ` +
        `minimum pre-training discussion threshold is ${MINIMUM_DISCUSSION_LABEL_ROWS}.`;

    if (db.matches === 1 && trainableLabelRows === 0) {
        reason = 'Current dev DB has one scheduled local sample and no finished labeled match set.';
    }

    return {
        trainable,
        reason,
        minimum_discussion_label_rows: MINIMUM_DISCUSSION_LABEL_ROWS,
        recommended_next_step: 'Build a finished-match sample audit before training.',
    };
}

function buildNonExecutionConfirmations() {
    return [
        'no_db_writes',
        'no_insert',
        'no_update',
        'no_delete',
        'no_create',
        'no_alter',
        'no_drop',
        'no_truncate',
        'no_copy',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
        'no_external_network',
        'no_file_export',
    ];
}

function formatKeyValueRows(rows) {
    return rows.map(([key, value]) => `  ${key}: ${value}`).join('\n');
}

function formatStatusDistribution(rows) {
    if (rows.length === 0) return '  none';
    return rows
        .map(
            row =>
                `  status=${row.status} is_finished=${row.is_finished} actual_result_is_null=${row.actual_result_is_null} score_complete=${row.score_complete} rows=${row.rows}`
        )
        .join('\n');
}

function formatText(payload) {
    const lines = [
        'mode=dataset-status',
        'safety=SELECT-only; no DB writes; no training; no prediction; no model artifact load; no external network; no file export',
        '',
        'DB row counts:',
        formatKeyValueRows(Object.entries(payload.db)),
        '',
        'Match status distribution:',
        formatStatusDistribution(payload.match_status_distribution),
        '',
        'Label readiness:',
        formatKeyValueRows(Object.entries(payload.label_readiness)),
        '',
        'Feature readiness:',
        formatKeyValueRows(Object.entries(payload.feature_readiness)),
        '',
        'Leakage risk flags:',
        formatKeyValueRows(Object.entries(payload.leakage_risk_flags)),
        '',
        'Training readiness:',
        formatKeyValueRows(Object.entries(payload.training_readiness)),
    ];

    if (payload.match_focus) {
        lines.push('', 'Match focus:', formatKeyValueRows(Object.entries(payload.match_focus)));
    }

    lines.push(
        '',
        'Non-execution confirmations:',
        payload.non_execution_confirmations.map(value => `  ${value}`).join('\n')
    );
    return lines.join('\n');
}

async function fetchDbCounts(pool) {
    const sql = `
        SELECT
            (SELECT COUNT(*) FROM matches) AS matches,
            (SELECT COUNT(*) FROM bookmaker_odds_history) AS bookmaker_odds_history,
            (SELECT COUNT(*) FROM raw_match_data) AS raw_match_data,
            (SELECT COUNT(*) FROM l3_features) AS l3_features,
            (SELECT COUNT(*) FROM match_features_training) AS match_features_training,
            (SELECT COUNT(*) FROM predictions) AS predictions
    `;
    const result = await safeSelect(pool, sql);
    return normalizeCounts(result.rows[0]);
}

async function fetchStatusDistribution(pool) {
    const sql = `
        SELECT
            COALESCE(status, 'unknown') AS status,
            is_finished,
            actual_result IS NULL AS actual_result_is_null,
            home_score IS NOT NULL AND away_score IS NOT NULL AS score_complete,
            COUNT(*) AS rows
        FROM matches
        GROUP BY COALESCE(status, 'unknown'), is_finished, actual_result IS NULL, home_score IS NOT NULL AND away_score IS NOT NULL
        ORDER BY rows DESC, status ASC
    `;
    const result = await safeSelect(pool, sql);
    return result.rows.map(normalizeStatusRow);
}

async function fetchLabelReadiness(pool) {
    const sql = `
        SELECT
            COUNT(*) FILTER (
                WHERE is_finished IS TRUE OR LOWER(COALESCE(status, '')) = ANY($1)
            ) AS finished_matches,
            COUNT(*) FILTER (
                WHERE actual_result IS NOT NULL AND TRIM(actual_result) <> ''
            ) AS matches_with_actual_result,
            COUNT(*) FILTER (
                WHERE home_score IS NOT NULL AND away_score IS NOT NULL
            ) AS matches_with_scores,
            COUNT(*) FILTER (
                WHERE
                    (is_finished IS TRUE OR LOWER(COALESCE(status, '')) = ANY($1))
                    AND (
                        (actual_result IS NOT NULL AND TRIM(actual_result) <> '')
                        OR (home_score IS NOT NULL AND away_score IS NOT NULL)
                    )
            ) AS trainable_label_rows,
            COUNT(*) FILTER (
                WHERE NOT (
                    (is_finished IS TRUE OR LOWER(COALESCE(status, '')) = ANY($1))
                    AND (
                        (actual_result IS NOT NULL AND TRIM(actual_result) <> '')
                        OR (home_score IS NOT NULL AND away_score IS NOT NULL)
                    )
                )
            ) AS scheduled_or_unlabeled_rows
        FROM matches
    `;
    const result = await safeSelect(pool, sql, [FINISHED_STATUSES]);
    return normalizeCounts(result.rows[0]);
}

async function fetchFeatureReadiness(pool) {
    const sql = `
        SELECT
            (SELECT COUNT(DISTINCT match_id) FROM raw_match_data) AS matches_with_raw_match_data,
            (SELECT COUNT(DISTINCT match_id) FROM l3_features) AS matches_with_l3_features,
            (SELECT COUNT(DISTINCT match_id) FROM match_features_training) AS matches_with_training_features,
            (SELECT COUNT(DISTINCT match_id) FROM bookmaker_odds_history) AS matches_with_odds_history,
            (
                SELECT COUNT(DISTINCT m.match_id)
                FROM matches m
                WHERE EXISTS (SELECT 1 FROM raw_match_data r WHERE r.match_id = m.match_id)
                  AND EXISTS (SELECT 1 FROM l3_features l3 WHERE l3.match_id = m.match_id)
                  AND EXISTS (SELECT 1 FROM match_features_training mt WHERE mt.match_id = m.match_id)
                  AND EXISTS (SELECT 1 FROM bookmaker_odds_history bo WHERE bo.match_id = m.match_id)
            ) AS full_feature_chain_rows
    `;
    const result = await safeSelect(pool, sql);
    return normalizeCounts(result.rows[0]);
}

async function fetchLeakageRiskFlags(pool) {
    const sql = `
        SELECT
            (
                SELECT COUNT(DISTINCT m.match_id)
                FROM matches m
                JOIN match_features_training mt ON mt.match_id = m.match_id
                WHERE NOT (m.is_finished IS TRUE OR LOWER(COALESCE(m.status, '')) = ANY($1))
            ) AS scheduled_matches_with_training_features,
            (
                SELECT COUNT(*)
                FROM predictions
                WHERE model_version = 'P4_LOCAL_BASELINE'
            ) AS baseline_prediction_rows,
            (SELECT COUNT(*) FROM predictions) AS prediction_rows_not_training_labels,
            (
                SELECT COUNT(*)
                FROM raw_match_data
                WHERE collected_at IS NULL
            ) AS raw_match_data_missing_collected_at,
            (
                SELECT COUNT(*)
                FROM bookmaker_odds_history
                WHERE collected_at IS NULL
            ) AS odds_history_missing_collected_at,
            (
                SELECT COUNT(*)
                FROM l3_features
                WHERE computed_at IS NULL
            ) AS l3_features_missing_computed_at,
            (
                SELECT COUNT(*)
                FROM match_features_training
                WHERE created_at IS NULL OR updated_at IS NULL
            ) AS training_features_missing_audit_timestamps
    `;
    const result = await safeSelect(pool, sql, [FINISHED_STATUSES]);
    return {
        ...normalizeCounts(result.rows[0]),
        caveat: 'Feature timing must be proven against kickoff cutoff before any real training.',
    };
}

async function fetchMatchFocus(pool, matchId) {
    if (!matchId) return null;

    const sql = `
        SELECT
            m.match_id,
            m.league_name,
            m.season,
            m.home_team,
            m.away_team,
            m.match_date,
            m.status,
            m.is_finished,
            m.actual_result,
            m.home_score IS NOT NULL AND m.away_score IS NOT NULL AS scores_complete,
            EXISTS (SELECT 1 FROM raw_match_data r WHERE r.match_id = m.match_id) AS has_raw_match_data,
            EXISTS (SELECT 1 FROM l3_features l3 WHERE l3.match_id = m.match_id) AS has_l3_features,
            EXISTS (SELECT 1 FROM match_features_training mt WHERE mt.match_id = m.match_id) AS has_training_features,
            EXISTS (SELECT 1 FROM bookmaker_odds_history bo WHERE bo.match_id = m.match_id) AS has_odds_history,
            EXISTS (SELECT 1 FROM predictions p WHERE p.match_id = m.match_id) AS has_prediction,
            (
                (m.is_finished IS TRUE OR LOWER(COALESCE(m.status, '')) = ANY($2))
                AND (
                    (m.actual_result IS NOT NULL AND TRIM(m.actual_result) <> '')
                    OR (m.home_score IS NOT NULL AND m.away_score IS NOT NULL)
                )
            ) AS trainable_label
        FROM matches m
        WHERE m.match_id = $1
    `;
    const result = await safeSelect(pool, sql, [matchId, FINISHED_STATUSES]);
    return normalizeMatchFocus(result.rows[0]);
}

async function buildAudit(pool, args) {
    const db = await fetchDbCounts(pool);
    const matchStatusDistribution = await fetchStatusDistribution(pool);
    const labelReadiness = await fetchLabelReadiness(pool);
    const featureReadiness = await fetchFeatureReadiness(pool);
    const leakageRiskFlags = await fetchLeakageRiskFlags(pool);
    const matchFocus = await fetchMatchFocus(pool, args.matchId);

    return {
        mode: 'dataset-status',
        filters: {
            match_id: args.matchId,
        },
        db,
        match_status_distribution: matchStatusDistribution,
        label_readiness: labelReadiness,
        feature_readiness: featureReadiness,
        leakage_risk_flags: leakageRiskFlags,
        training_readiness: buildTrainingReadiness({
            db,
            labelReadiness,
            featureReadiness,
        }),
        match_focus: matchFocus,
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
        console.log(usage());
        return;
    }

    const pool = new Pool(buildDbConfig());
    try {
        const payload = await buildAudit(pool, args);
        if (args.json) {
            console.log(JSON.stringify(payload, null, 2));
        } else {
            console.log(formatText(payload));
        }
    } finally {
        await pool.end();
    }
}

main().catch(error => {
    console.error(
        JSON.stringify(
            {
                mode: 'dataset-status',
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
