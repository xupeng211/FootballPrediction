#!/usr/bin/env node
/**
 * Safe synthetic training-feature to prediction preflight gate.
 *
 * Phase 4.48 reads the target match and existing synthetic
 * match_features_training row, then emits a prediction preview without model
 * loading, inference, training, prediction writes, or any DB writes.
 */

'use strict';

const { Pool } = require('pg');

const FORBIDDEN_SQL =
    /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|UPSERT|MERGE|GRANT|REVOKE|CREATE\s+INDEX)\b/i;
const TRUE_VALUES = new Set(['true', 't', '1', 'yes', 'y']);
const RECOMMENDED_MODEL_VERSION = 'P4_SYNTH_BASELINE';
const MODEL_VERSION_LENGTH_LIMIT = 20;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/synthetic_prediction_preflight.js --match-id <id> [--json]',
        '  node scripts/ops/synthetic_prediction_preflight.js --match-id <id> --commit',
        '',
        'Safety:',
        '  Preflight only in Phase 4.48; --commit is blocked and not wired.',
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
        } else if (token.startsWith('--match-id=')) {
            args.matchId = token.slice('--match-id='.length);
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
        throw new Error('Unsafe SQL blocked: write/schema/export verb detected');
    }
}

async function safeSelect(pool, sql, params = []) {
    assertSafeSelect(sql);
    return pool.query(sql, params);
}

function normalizeText(value) {
    return String(value ?? '')
        .replace(/\s+/g, ' ')
        .trim();
}

function asBoolean(value) {
    if (typeof value === 'boolean') return value;
    return TRUE_VALUES.has(normalizeText(value).toLowerCase());
}

function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function hasValue(value) {
    return normalizeText(value).length > 0;
}

function toIso(value) {
    return value ? new Date(value).toISOString() : null;
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
        'no_copy_export',
        'no_prediction_write',
        'no_training_feature_write',
        'no_l3_write',
        'no_raw_match_data_write',
        'no_model_training',
        'no_prediction_execution',
        'no_model_artifact_load',
        'no_external_network',
    ];
}

function buildBlockedCommitPayload() {
    return {
        mode: 'blocked-commit',
        ok: false,
        error: 'BLOCKED: synthetic prediction commit is not wired in Phase 4.48.',
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function buildTargetMatchStatus(match) {
    return {
        match_found: Boolean(match),
        match_id: match?.match_id || null,
        season: match?.season || null,
        match_date: toIso(match?.match_date),
        home_team: match?.home_team || null,
        away_team: match?.away_team || null,
        home_score: match?.home_score ?? null,
        away_score: match?.away_score ?? null,
        actual_result: match?.actual_result || null,
        status: match?.status || null,
        is_finished: match?.is_finished === true,
        has_actual_result: hasValue(match?.actual_result),
        has_score:
            match?.home_score !== null &&
            match?.home_score !== undefined &&
            match?.away_score !== null &&
            match?.away_score !== undefined,
    };
}

function buildUpstreamChainStatus(matchRow, trainingRow) {
    const adaptiveFeatures = asObject(trainingRow?.adaptive_features);

    return {
        raw_match_data_found: matchRow?.has_raw_match_data === true,
        l3_features_found: matchRow?.has_l3_features === true,
        match_features_training_found: Boolean(trainingRow),
        training_feature_version: trainingRow?.feature_version || null,
        training_feature_count: trainingRow?.feature_count ?? null,
        training_features_created_at: toIso(trainingRow?.created_at),
        training_features_updated_at: toIso(trainingRow?.updated_at),
        training_features_synthetic: asBoolean(adaptiveFeatures.synthetic),
        training_features_engineering_test_only: asBoolean(adaptiveFeatures.engineering_test_only),
        training_features_not_real_external_data: asBoolean(adaptiveFeatures.not_real_external_data),
        training_features_not_for_training: asBoolean(adaptiveFeatures.not_for_training),
        training_features_not_for_production: asBoolean(adaptiveFeatures.not_for_production),
        source_l3_feature_data_version: adaptiveFeatures.source_l3_feature_data_version || null,
        feature_data_version: adaptiveFeatures.feature_data_version || null,
        downstream_training_allowed: asBoolean(adaptiveFeatures.downstream_training_allowed),
        downstream_prediction_allowed: asBoolean(adaptiveFeatures.downstream_prediction_allowed),
    };
}

function buildPredictionStatus(predictionRows) {
    const targetModelVersionExists = predictionRows.some(row => row.model_version === RECOMMENDED_MODEL_VERSION);
    const recommendedModelVersionLength = RECOMMENDED_MODEL_VERSION.length;

    return {
        predictions_exists: predictionRows.length > 0,
        existing_predictions_count: predictionRows.length,
        existing_model_versions: predictionRows.map(row => row.model_version),
        target_model_version: RECOMMENDED_MODEL_VERSION,
        target_model_version_exists: targetModelVersionExists,
        recommended_model_version: RECOMMENDED_MODEL_VERSION,
        recommended_model_version_length: recommendedModelVersionLength,
        model_version_length_limit: MODEL_VERSION_LENGTH_LIMIT,
        model_version_length_lte_20: recommendedModelVersionLength <= MODEL_VERSION_LENGTH_LIMIT,
    };
}

function choosePreviewResult(matchRow) {
    return matchRow?.actual_result === 'home_win' ? 'home_win' : 'draw';
}

function summarizeAdaptiveFeatures(trainingRow) {
    const adaptiveFeatures = asObject(trainingRow?.adaptive_features);

    return {
        type: Array.isArray(trainingRow?.adaptive_features) ? 'array' : typeof trainingRow?.adaptive_features,
        key_count: Object.keys(adaptiveFeatures).length,
        keys: Object.keys(adaptiveFeatures).sort(),
        source: adaptiveFeatures.source || null,
        source_l3_feature_data_version: adaptiveFeatures.source_l3_feature_data_version || null,
        feature_data_version: adaptiveFeatures.feature_data_version || null,
        synthetic: asBoolean(adaptiveFeatures.synthetic),
        not_for_training: asBoolean(adaptiveFeatures.not_for_training),
        not_for_production: asBoolean(adaptiveFeatures.not_for_production),
        downstream_prediction_allowed: asBoolean(adaptiveFeatures.downstream_prediction_allowed),
    };
}

function buildPredictionPreview({ matchRow, trainingRow }) {
    const predictedResult = choosePreviewResult(matchRow);

    return {
        target_table: 'predictions',
        would_write_predictions: false,
        would_train_model: false,
        would_load_model_artifact: false,
        would_execute_real_prediction: false,
        preview_only: true,
        synthetic_input: true,
        not_real_model_output: true,
        not_for_training: true,
        not_for_production: true,
        prediction_allowed: false,
        synthetic_baseline_preview: {
            model_version: RECOMMENDED_MODEL_VERSION,
            predicted_result: predictedResult,
            preview_only: true,
            not_real_model_output: true,
            based_on_synthetic_chain: true,
            not_for_production: true,
            actual_result_used_for_engineering_preview: matchRow?.actual_result || null,
            note: 'Engineering preview only. This uses synthetic-chain context and must not be treated as a real model prediction.',
        },
        training_feature_summary: summarizeAdaptiveFeatures(trainingRow),
    };
}

function buildGatingDecision(upstreamStatus) {
    const syntheticTrainingSafetyComplete =
        upstreamStatus.training_features_synthetic === true &&
        upstreamStatus.training_features_engineering_test_only === true &&
        upstreamStatus.training_features_not_real_external_data === true &&
        upstreamStatus.training_features_not_for_training === true &&
        upstreamStatus.training_features_not_for_production === true &&
        upstreamStatus.downstream_prediction_allowed === false;

    return {
        can_write_prediction_now: false,
        reason: 'synthetic training features require separate manual authorization and cannot be treated as real model output',
        real_prediction_allowed: false,
        model_training_allowed: false,
        synthetic_training_safety_complete: syntheticTrainingSafetyComplete,
    };
}

function buildPayload({ args, matchRow, trainingRow, predictionRows }) {
    const upstreamStatus = buildUpstreamChainStatus(matchRow, trainingRow);

    return {
        mode: 'dry-run / preflight',
        phase: '4.48',
        match_id: args.matchId,
        target_match: buildTargetMatchStatus(matchRow),
        upstream_chain_status: upstreamStatus,
        prediction_status: buildPredictionStatus(predictionRows),
        prediction_preview: buildPredictionPreview({ matchRow, trainingRow }),
        gating_decision: buildGatingDecision(upstreamStatus),
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function formatText(payload) {
    return [
        `mode=${payload.mode}`,
        `phase=${payload.phase}`,
        `match_id=${payload.match_id}`,
        `match_found=${payload.target_match.match_found}`,
        `is_finished=${payload.target_match.is_finished}`,
        `has_actual_result=${payload.target_match.has_actual_result}`,
        `has_score=${payload.target_match.has_score}`,
        `raw_match_data_found=${payload.upstream_chain_status.raw_match_data_found}`,
        `l3_features_found=${payload.upstream_chain_status.l3_features_found}`,
        `match_features_training_found=${payload.upstream_chain_status.match_features_training_found}`,
        `training_features_synthetic=${payload.upstream_chain_status.training_features_synthetic}`,
        `training_features_not_for_training=${payload.upstream_chain_status.training_features_not_for_training}`,
        `training_features_not_for_production=${payload.upstream_chain_status.training_features_not_for_production}`,
        `downstream_prediction_allowed=${payload.upstream_chain_status.downstream_prediction_allowed}`,
        `predictions_exists=${payload.prediction_status.predictions_exists}`,
        `target_model_version_exists=${payload.prediction_status.target_model_version_exists}`,
        `recommended_model_version=${payload.prediction_status.recommended_model_version}`,
        `model_version_length<=20=${payload.prediction_status.model_version_length_lte_20}`,
        `would_write_predictions=${payload.prediction_preview.would_write_predictions}`,
        `would_train_model=${payload.prediction_preview.would_train_model}`,
        `would_load_model_artifact=${payload.prediction_preview.would_load_model_artifact}`,
        `would_execute_real_prediction=${payload.prediction_preview.would_execute_real_prediction}`,
        `preview_only=${payload.prediction_preview.preview_only}`,
        `synthetic_input=${payload.prediction_preview.synthetic_input}`,
        `not_real_model_output=${payload.prediction_preview.not_real_model_output}`,
        `not_for_training=${payload.prediction_preview.not_for_training}`,
        `not_for_production=${payload.prediction_preview.not_for_production}`,
        `prediction_allowed=${payload.prediction_preview.prediction_allowed}`,
        `can_write_prediction_now=${payload.gating_decision.can_write_prediction_now}`,
        `real_prediction_allowed=${payload.gating_decision.real_prediction_allowed}`,
        `model_training_allowed=${payload.gating_decision.model_training_allowed}`,
        '',
        'target_match:',
        JSON.stringify(payload.target_match, null, 2),
        '',
        'upstream_chain_status:',
        JSON.stringify(payload.upstream_chain_status, null, 2),
        '',
        'prediction_status:',
        JSON.stringify(payload.prediction_status, null, 2),
        '',
        'prediction_preview:',
        JSON.stringify(payload.prediction_preview, null, 2),
        '',
        'gating_decision:',
        JSON.stringify(payload.gating_decision, null, 2),
        '',
        'non_execution_confirmations:',
        payload.non_execution_confirmations.map(value => `  ${value}`).join('\n'),
    ].join('\n');
}

async function loadMatch(pool, matchId) {
    const sql = `
        SELECT
            m.match_id,
            m.season,
            m.match_date,
            m.home_team,
            m.away_team,
            m.home_score,
            m.away_score,
            m.actual_result,
            m.status,
            m.is_finished,
            EXISTS (SELECT 1 FROM raw_match_data r WHERE r.match_id = m.match_id) AS has_raw_match_data,
            EXISTS (SELECT 1 FROM l3_features l WHERE l.match_id = m.match_id) AS has_l3_features
        FROM matches m
        WHERE m.match_id = $1
    `;
    const result = await safeSelect(pool, sql, [matchId]);
    return result.rows[0] || null;
}

async function loadTrainingFeatures(pool, matchId) {
    const sql = `
        SELECT
            match_id,
            season,
            match_date,
            home_team,
            away_team,
            feature_version,
            feature_count,
            adaptive_features,
            created_at,
            updated_at
        FROM match_features_training
        WHERE match_id = $1
    `;
    const result = await safeSelect(pool, sql, [matchId]);
    return result.rows[0] || null;
}

async function loadPredictionRows(pool, matchId) {
    const sql = `
        SELECT
            match_id,
            model_version,
            predicted_result,
            prediction_date
        FROM predictions
        WHERE match_id = $1
        ORDER BY model_version
    `;
    const result = await safeSelect(pool, sql, [matchId]);
    return result.rows;
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
        console.log(usage());
        return;
    }
    if (args.commit) {
        console.error('BLOCKED: synthetic prediction commit is not wired in Phase 4.48.');
        console.error(JSON.stringify(buildBlockedCommitPayload(), null, 2));
        process.exitCode = 1;
        return;
    }
    if (!args.matchId) {
        console.error('ERROR: provide --match-id <id>');
        console.error(usage());
        process.exitCode = 1;
        return;
    }

    const pool = new Pool(buildDbConfig());
    try {
        const matchRow = await loadMatch(pool, args.matchId);
        const trainingRow = await loadTrainingFeatures(pool, args.matchId);
        const predictionRows = await loadPredictionRows(pool, args.matchId);
        const payload = buildPayload({ args, matchRow, trainingRow, predictionRows });

        console.log(args.json ? JSON.stringify(payload, null, 2) : formatText(payload));
    } finally {
        await pool.end();
    }
}

main().catch(error => {
    console.error(
        JSON.stringify(
            {
                mode: 'dry-run / preflight',
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
