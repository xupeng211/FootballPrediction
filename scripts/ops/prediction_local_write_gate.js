#!/usr/bin/env node
/**
 * Safe local predictions write preview gate.
 *
 * Phase 4.32 deliberately keeps commit mode blocked. The script performs
 * SELECT-only DB checks and builds a future prediction write preview from the
 * existing match_features_training row without model loading, inference, or
 * writes.
 */

'use strict';

const { Pool } = require('pg');
const { assertDbWriteAllowed } = require('./helpers/db_write_guard');

const FORBIDDEN_SQL = /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|UPSERT|MERGE|GRANT|REVOKE|CREATE\s+INDEX)\b/i;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/prediction_local_write_gate.js --match-id <id> [--json]',
        '  node scripts/ops/prediction_local_write_gate.js --match-id <id> --commit',
        '',
        'Safety:',
        '  Dry-run only in Phase 4.32; --commit is blocked and not wired.',
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
        error: 'BLOCKED: prediction commit is not wired in Phase 4.32.',
        non_execution_confirmations: [
            'no_db_writes',
            'no_insert',
            'no_update',
            'no_delete',
            'no_model_training',
            'no_prediction_execution',
            'no_model_artifact_load',
            'no_external_network',
        ],
    };
}

function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function summarizeAdaptiveFeatures(value) {
    const objectValue = asObject(value);
    return {
        type: Array.isArray(value) ? 'array' : typeof value,
        key_count: Object.keys(objectValue).length,
        keys: Object.keys(objectValue).sort().slice(0, 20),
        source: objectValue.source || null,
        trainable: objectValue.trainable === true,
    };
}

function buildPredictionPreview({ matchId, matchRow, trainingRow, predictionRows }) {
    const adaptiveFeatures = asObject(trainingRow?.adaptive_features);

    return {
        mode: 'dry-run',
        match_id: matchId,
        db: {
            match_found: Boolean(matchRow),
            match_features_training_found: Boolean(trainingRow),
            predictions_exists: predictionRows.length > 0,
            prediction_rows: predictionRows.length,
        },
        preview_record: {
            target_table: 'predictions',
            would_write_predictions: false,
            match_id: matchId,
            prediction_source: 'match_features_training',
            model_available: false,
            model_artifact_used: null,
            model_version_candidate: 'phase4.32_no_model_preview',
            predicted_result_candidate: null,
            confidence_home: null,
            confidence_draw: null,
            confidence_away: null,
            final_confidence: null,
            recommended_bet: null,
            note: 'No real model prediction is executed in Phase 4.32.',
            match_context: {
                league_name: matchRow?.league_name || null,
                season: matchRow?.season || trainingRow?.season || null,
                match_date: matchRow?.match_date
                    ? new Date(matchRow.match_date).toISOString()
                    : trainingRow?.match_date
                      ? new Date(trainingRow.match_date).toISOString()
                      : null,
                home_team: matchRow?.home_team || trainingRow?.home_team || null,
                away_team: matchRow?.away_team || trainingRow?.away_team || null,
                status: matchRow?.status || null,
                pipeline_status: matchRow?.pipeline_status || null,
            },
            training_feature_summary: {
                feature_version: trainingRow?.feature_version || null,
                feature_count: trainingRow?.feature_count ?? null,
                adaptive_features: summarizeAdaptiveFeatures(adaptiveFeatures),
                adaptive_source: adaptiveFeatures.source || null,
                adaptive_trainable: adaptiveFeatures.trainable === true,
            },
        },
        prediction_summary: {
            would_train_model: false,
            would_load_model_artifact: false,
            real_prediction_available: false,
            reason: 'Prediction execution requires an approved model artifact and a dedicated authorization phase.',
        },
        non_execution_confirmations: [
            'no_db_writes',
            'no_insert',
            'no_update',
            'no_delete',
            'no_model_training',
            'no_prediction_execution',
            'no_model_artifact_load',
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
        // DB Write Safety Gate — unified guard (defense-in-depth)
        assertDbWriteAllowed({
            script: 'prediction_local_write_gate.js',
            tables: ['predictions'],
            operations: ['INSERT', 'UPDATE'],
        });
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
        const trainingSql = `
            SELECT match_id, season, match_date, home_team, away_team,
                   feature_version, feature_count, adaptive_features, created_at, updated_at
            FROM match_features_training
            WHERE match_id = $1
        `;
        const predictionSql = `
            SELECT match_id, model_version
            FROM predictions
            WHERE match_id = $1
        `;

        const matchResult = await safeSelect(pool, matchSql, [args.matchId]);
        const trainingResult = await safeSelect(pool, trainingSql, [args.matchId]);
        const predictionResult = await safeSelect(pool, predictionSql, [args.matchId]);

        const preview = buildPredictionPreview({
            matchId: args.matchId,
            matchRow: matchResult.rows[0] || null,
            trainingRow: trainingResult.rows[0] || null,
            predictionRows: predictionResult.rows,
        });

        console.log(JSON.stringify(preview, null, 2));

        if (!preview.db.match_found || !preview.db.match_features_training_found) {
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
                    'no_model_training',
                    'no_prediction_execution',
                    'no_model_artifact_load',
                    'no_external_network',
                ],
            },
            null,
            2
        )
    );
    process.exit(1);
});
