#!/usr/bin/env node
/**
 * Safe synthetic L3 to training-feature preflight gate.
 *
 * Phase 4.46 reads the target match and existing synthetic l3_features row,
 * then emits a match_features_training preview without training or writes.
 */

'use strict';

const { Pool } = require('pg');
const { assertDbWriteAllowed } = require('./helpers/db_write_guard');

const FORBIDDEN_SQL =
    /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|UPSERT|MERGE|GRANT|REVOKE|CREATE\s+INDEX)\b/i;
const TRUE_VALUES = new Set(['true', 't', '1', 'yes', 'y']);

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/synthetic_training_feature_preflight.js --match-id <id> [--json]',
        '  node scripts/ops/synthetic_training_feature_preflight.js --match-id <id> --commit',
        '',
        'Safety:',
        '  Preflight only in Phase 4.46; --commit is blocked and not wired.',
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

function buildNonExecutionConfirmations() {
    return [
        'no_db_writes',
        'no_insert',
        'no_update',
        'no_delete',
        'no_create',
        'no_alter',
        'no_training_feature_write',
        'no_prediction_write',
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
        error: 'BLOCKED: synthetic training feature commit is not wired in Phase 4.46.',
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function buildTargetMatchStatus(match) {
    return {
        match_found: Boolean(match),
        match_id: match?.match_id || null,
        season: match?.season || null,
        match_date: match?.match_date ? new Date(match.match_date).toISOString() : null,
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

function featureFlag(l3Row, featureName, key) {
    return asBoolean(asObject(l3Row?.[featureName])?.[key]);
}

function buildUpstreamStatus(rawRow, l3Row) {
    const goldenFeatures = asObject(l3Row?.golden_features);
    const stitchSummary = asObject(l3Row?.stitch_summary);

    return {
        raw_match_data_found: Boolean(rawRow),
        raw_data_version: rawRow?.data_version || null,
        raw_synthetic: asBoolean(asObject(rawRow?.raw_data)?.metadata?.synthetic),
        l3_features_found: Boolean(l3Row),
        l3_external_id: l3Row?.external_id || null,
        l3_computed_at: l3Row?.computed_at ? new Date(l3Row.computed_at).toISOString() : null,
        l3_features_synthetic:
            featureFlag(l3Row, 'golden_features', 'synthetic') &&
            featureFlag(l3Row, 'tactical_features', 'synthetic') &&
            featureFlag(l3Row, 'odds_features', 'synthetic') &&
            featureFlag(l3Row, 'elo_features', 'synthetic') &&
            featureFlag(l3Row, 'stitch_summary', 'synthetic'),
        l3_features_engineering_test_only: featureFlag(l3Row, 'golden_features', 'engineering_test_only'),
        l3_features_not_real_external_data: featureFlag(l3Row, 'golden_features', 'not_real_external_data'),
        l3_features_not_for_training: featureFlag(l3Row, 'golden_features', 'not_for_training'),
        l3_features_not_for_production: featureFlag(l3Row, 'stitch_summary', 'not_for_production'),
        l3_feature_data_version: stitchSummary.feature_data_version || goldenFeatures.feature_data_version || null,
    };
}

function buildDownstreamStatus(statusRow) {
    return {
        match_features_training_exists: statusRow?.match_features_training_exists === true,
        predictions_exists: statusRow?.predictions_exists === true,
    };
}

function summarizeFeatureGroup(value) {
    const feature = asObject(value);
    return {
        synthetic: asBoolean(feature.synthetic),
        not_for_training: asBoolean(feature.not_for_training),
        not_for_production: asBoolean(feature.not_for_production),
        feature_group: feature.feature_group || null,
        key_count: Object.keys(feature).length,
        keys: Object.keys(feature).sort(),
    };
}

function buildAdaptiveFeaturesPreview(matchId, l3Row) {
    return {
        source: 'PHASE4.45_SYNTHETIC_L3',
        feature_data_version: 'PHASE4.46_SYNTHETIC_TRAINING_PREFLIGHT',
        synthetic: true,
        engineering_test_only: true,
        not_real_external_data: true,
        not_for_training: true,
        not_for_production: true,
        target_match_id: matchId,
        golden_features: summarizeFeatureGroup(l3Row?.golden_features),
        tactical_features: summarizeFeatureGroup(l3Row?.tactical_features),
        odds_features: summarizeFeatureGroup(l3Row?.odds_features),
        elo_features: summarizeFeatureGroup(l3Row?.elo_features),
        stitch_summary: summarizeFeatureGroup(l3Row?.stitch_summary),
    };
}

function buildTrainingFeaturePreview({ matchId, matchRow, l3Row }) {
    return {
        target_table: 'match_features_training',
        would_insert_match_features_training: false,
        would_train_model: false,
        would_write_predictions: false,
        preview_only: true,
        synthetic_input: true,
        not_for_training: true,
        not_for_production: true,
        candidate_required_fields: {
            match_id: matchId,
            season: matchRow?.season || null,
            match_date: matchRow?.match_date ? new Date(matchRow.match_date).toISOString() : null,
            home_team: matchRow?.home_team || null,
            away_team: matchRow?.away_team || null,
            actual_result: matchRow?.actual_result || null,
            feature_version: 'PHASE4.46_SYNTHETIC_TRAINING_PREFLIGHT',
        },
        adaptive_features_preview: buildAdaptiveFeaturesPreview(matchId, l3Row),
    };
}

function buildGatingDecision(upstreamStatus) {
    const syntheticSafetyComplete =
        upstreamStatus.l3_features_synthetic === true &&
        upstreamStatus.l3_features_engineering_test_only === true &&
        upstreamStatus.l3_features_not_real_external_data === true &&
        upstreamStatus.l3_features_not_for_training === true &&
        upstreamStatus.l3_features_not_for_production === true;

    return {
        can_write_training_features_now: false,
        reason: 'synthetic l3_features require separate manual authorization',
        real_training_allowed: false,
        prediction_allowed: false,
        synthetic_l3_safety_complete: syntheticSafetyComplete,
    };
}

function buildPayload({ args, matchRow, rawRow, l3Row, statusRow }) {
    const upstreamStatus = buildUpstreamStatus(rawRow, l3Row);

    return {
        mode: 'dry-run',
        phase: '4.46',
        match_id: args.matchId,
        target_match: buildTargetMatchStatus(matchRow),
        upstream_chain_status: upstreamStatus,
        downstream_status: buildDownstreamStatus(statusRow),
        training_feature_preview: buildTrainingFeaturePreview({
            matchId: args.matchId,
            matchRow,
            l3Row,
        }),
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
        `l3_features_synthetic=${payload.upstream_chain_status.l3_features_synthetic}`,
        `l3_features_not_for_training=${payload.upstream_chain_status.l3_features_not_for_training}`,
        `l3_features_not_for_production=${payload.upstream_chain_status.l3_features_not_for_production}`,
        `match_features_training_exists=${payload.downstream_status.match_features_training_exists}`,
        `predictions_exists=${payload.downstream_status.predictions_exists}`,
        `would_insert_match_features_training=${payload.training_feature_preview.would_insert_match_features_training}`,
        `would_train_model=${payload.training_feature_preview.would_train_model}`,
        `would_write_predictions=${payload.training_feature_preview.would_write_predictions}`,
        `preview_only=${payload.training_feature_preview.preview_only}`,
        `synthetic_input=${payload.training_feature_preview.synthetic_input}`,
        `can_write_training_features_now=${payload.gating_decision.can_write_training_features_now}`,
        `real_training_allowed=${payload.gating_decision.real_training_allowed}`,
        `prediction_allowed=${payload.gating_decision.prediction_allowed}`,
        '',
        'target_match:',
        JSON.stringify(payload.target_match, null, 2),
        '',
        'upstream_chain_status:',
        JSON.stringify(payload.upstream_chain_status, null, 2),
        '',
        'downstream_status:',
        JSON.stringify(payload.downstream_status, null, 2),
        '',
        'training_feature_preview:',
        JSON.stringify(payload.training_feature_preview, null, 2),
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
            match_id,
            season,
            home_team,
            away_team,
            home_score,
            away_score,
            actual_result,
            match_date,
            status,
            is_finished
        FROM matches
        WHERE match_id = $1
    `;
    const result = await safeSelect(pool, sql, [matchId]);
    return result.rows[0] || null;
}

async function loadRawMatchData(pool, matchId) {
    const sql = `
        SELECT
            match_id,
            raw_data,
            data_version
        FROM raw_match_data
        WHERE match_id = $1
        ORDER BY collected_at DESC
        LIMIT 1
    `;
    const result = await safeSelect(pool, sql, [matchId]);
    return result.rows[0] || null;
}

async function loadL3Features(pool, matchId) {
    const sql = `
        SELECT
            match_id,
            external_id,
            golden_features,
            tactical_features,
            odds_features,
            elo_features,
            stitch_summary,
            computed_at
        FROM l3_features
        WHERE match_id = $1
    `;
    const result = await safeSelect(pool, sql, [matchId]);
    return result.rows[0] || null;
}

async function loadDownstreamStatus(pool, matchId) {
    const sql = `
        SELECT
            EXISTS (SELECT 1 FROM match_features_training WHERE match_id = $1) AS match_features_training_exists,
            EXISTS (SELECT 1 FROM predictions WHERE match_id = $1) AS predictions_exists
    `;
    const result = await safeSelect(pool, sql, [matchId]);
    return result.rows[0] || {};
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
        console.log(usage());
        return;
    }
    if (args.commit) {
        assertDbWriteAllowed({
            script: 'synthetic_training_feature_preflight.js',
            tables: ['match_features_training'],
            operations: ['INSERT'],
        });
        console.error('BLOCKED: synthetic training feature commit is not wired in Phase 4.46.');
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
        const rawRow = await loadRawMatchData(pool, args.matchId);
        const l3Row = await loadL3Features(pool, args.matchId);
        const statusRow = await loadDownstreamStatus(pool, args.matchId);
        const payload = buildPayload({ args, matchRow, rawRow, l3Row, statusRow });

        console.log(args.json ? JSON.stringify(payload, null, 2) : formatText(payload));
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
                non_execution_confirmations: buildNonExecutionConfirmations(),
            },
            null,
            2
        )
    );
    process.exitCode = 1;
});
