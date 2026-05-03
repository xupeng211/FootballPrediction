#!/usr/bin/env node
/**
 * Safe local match_features_training write preview gate.
 *
 * Phase 4.30 deliberately keeps commit mode blocked. The script performs
 * SELECT-only DB checks and builds a future match_features_training preview
 * from the existing l3_features row without training, prediction, or writes.
 */

'use strict';

const { Pool } = require('pg');

const FORBIDDEN_SQL = /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|UPSERT|MERGE|GRANT|REVOKE|CREATE\s+INDEX)\b/i;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/match_features_training_local_write_gate.js --match-id <id> [--json]',
        '  node scripts/ops/match_features_training_local_write_gate.js --match-id <id> --commit',
        '',
        'Safety:',
        '  Dry-run only in Phase 4.30; --commit is blocked and not wired.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        matchId: null,
        json: false,
        commit: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--match-id') {
            args.matchId = argv[index + 1];
            index += 1;
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
        throw new Error('Unsafe SQL blocked: write/schema verb detected');
    }
}

async function safeSelect(pool, sql, params) {
    assertSafeSelect(sql);
    return pool.query(sql, params);
}

function buildBlockedCommitPayload() {
    return {
        mode: 'blocked-commit',
        ok: false,
        error: 'BLOCKED: match_features_training commit is not wired in Phase 4.30.',
        non_execution_confirmations: [
            'no_db_writes',
            'no_insert',
            'no_update',
            'no_delete',
            'no_training',
            'no_prediction',
            'no_model_artifact_write',
            'no_external_network',
        ],
    };
}

function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function summarizeJsonFeature(value) {
    const objectValue = asObject(value);
    return {
        type: Array.isArray(value) ? 'array' : typeof value,
        key_count: Object.keys(objectValue).length,
        keys: Object.keys(objectValue).sort().slice(0, 20),
        source: objectValue.source || objectValue.odds_source || null,
    };
}

function buildFeaturePreview({ matchId, matchRow, l3Row, trainingRows, predictionRows }) {
    const goldenFeatures = asObject(l3Row?.golden_features);
    const tacticalFeatures = asObject(l3Row?.tactical_features);
    const oddsFeatures = asObject(l3Row?.odds_features);
    const eloFeatures = asObject(l3Row?.elo_features);
    const stitchSummary = asObject(l3Row?.stitch_summary);

    return {
        mode: 'dry-run',
        match_id: matchId,
        db: {
            match_found: Boolean(matchRow),
            l3_features_found: Boolean(l3Row),
            match_features_training_exists: trainingRows.length > 0,
            match_features_training_rows: trainingRows.length,
            predictions_exists: predictionRows.length > 0,
            prediction_rows: predictionRows.length,
        },
        preview_record: {
            target_table: 'match_features_training',
            would_insert_match_features_training: false,
            match_id: matchId,
            feature_source: 'l3_features',
            candidate_required_fields: {
                season: matchRow?.season || null,
                match_date: matchRow?.match_date ? new Date(matchRow.match_date).toISOString() : null,
                home_team: matchRow?.home_team || null,
                away_team: matchRow?.away_team || null,
                feature_version: 'database_default_V25.1_when_future_commit_is_authorized',
            },
            feature_summary: {
                golden_features: summarizeJsonFeature(goldenFeatures),
                tactical_features: summarizeJsonFeature(tacticalFeatures),
                odds_features: summarizeJsonFeature(oddsFeatures),
                elo_features: summarizeJsonFeature(eloFeatures),
                stitch_summary: summarizeJsonFeature(stitchSummary),
            },
            adaptive_features_preview: {
                source: 'phase4.30_l3_features_preview',
                l3_computed_at: l3Row?.computed_at ? new Date(l3Row.computed_at).toISOString() : null,
                l3_created_at: l3Row?.created_at ? new Date(l3Row.created_at).toISOString() : null,
                golden_feature_keys: Object.keys(goldenFeatures).sort(),
                tactical_feature_keys: Object.keys(tacticalFeatures).sort(),
                odds_feature_keys: Object.keys(oddsFeatures).sort(),
                elo_available: eloFeatures.available === true,
                stitch_source: stitchSummary.source || null,
            },
            trainable: false,
            reason: 'Single scheduled match is insufficient for real model training.',
        },
        training_summary: {
            would_train_model: false,
            minimum_dataset_required: 'multi-match finished historical dataset with outcomes',
            model_artifact_policy_required: true,
        },
        prediction_summary: {
            would_write_predictions: false,
            reason: 'Prediction execution is blocked in Phase 4.30.',
        },
        non_execution_confirmations: [
            'no_db_writes',
            'no_insert',
            'no_update',
            'no_delete',
            'no_training',
            'no_prediction',
            'no_model_artifact_write',
            'no_external_network',
        ],
    };
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
        console.log(usage());
        return;
    }
    if (args.commit) {
        console.error(JSON.stringify(buildBlockedCommitPayload(), null, 2));
        process.exitCode = 1;
        return;
    }
    if (!args.matchId) {
        console.error(usage());
        process.exitCode = 1;
        return;
    }

    const pool = new Pool(buildDbConfig());
    try {
        const matchSql = `
            SELECT match_id, external_id, league_name, season, home_team, away_team,
                   match_date, status, pipeline_status
            FROM matches
            WHERE match_id = $1
        `;
        const l3Sql = `
            SELECT match_id, computed_at, created_at, updated_at,
                   golden_features, tactical_features, odds_features, elo_features, stitch_summary
            FROM l3_features
            WHERE match_id = $1
        `;
        const trainingSql = `
            SELECT match_id
            FROM match_features_training
            WHERE match_id = $1
        `;
        const predictionSql = `
            SELECT match_id
            FROM predictions
            WHERE match_id = $1
        `;

        const matchResult = await safeSelect(pool, matchSql, [args.matchId]);
        const l3Result = await safeSelect(pool, l3Sql, [args.matchId]);
        const trainingResult = await safeSelect(pool, trainingSql, [args.matchId]);
        const predictionResult = await safeSelect(pool, predictionSql, [args.matchId]);

        const preview = buildFeaturePreview({
            matchId: args.matchId,
            matchRow: matchResult.rows[0] || null,
            l3Row: l3Result.rows[0] || null,
            trainingRows: trainingResult.rows,
            predictionRows: predictionResult.rows,
        });

        console.log(JSON.stringify(preview, null, 2));

        if (!preview.db.match_found || !preview.db.l3_features_found) {
            process.exitCode = 1;
        }
    } finally {
        await pool.end();
    }
}

main().catch(error => {
    console.error(
        JSON.stringify(
            {
                mode: 'dry-run',
                ok: false,
                error: error.message,
                non_execution_confirmations: [
                    'no_db_writes',
                    'no_insert',
                    'no_update',
                    'no_delete',
                    'no_training',
                    'no_prediction',
                    'no_model_artifact_write',
                    'no_external_network',
                ],
            },
            null,
            2
        )
    );
    process.exit(1);
});
