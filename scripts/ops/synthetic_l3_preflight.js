#!/usr/bin/env node
/**
 * Safe synthetic raw to L3 preflight gate.
 *
 * Phase 4.44 only reads the target match and its existing synthetic
 * raw_match_data row. It never writes l3_features or calls smelt/stitch paths.
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
        '  node scripts/ops/synthetic_l3_preflight.js --match-id <id> [--json]',
        '  node scripts/ops/synthetic_l3_preflight.js --match-id <id> --commit',
        '',
        'Safety:',
        '  Preflight only in Phase 4.44; --commit is blocked and not wired.',
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
        'no_l3_write',
        'no_training_feature_write',
        'no_prediction_write',
        'no_smelt',
        'no_l3_stitch',
        'no_elo',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
        'no_external_network',
    ];
}

function buildBlockedCommitPayload() {
    return {
        mode: 'blocked-commit',
        ok: false,
        error: 'BLOCKED: synthetic L3 commit is not wired in Phase 4.44.',
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function buildSyntheticMarker(source) {
    return {
        synthetic: true,
        source,
        engineering_test_only: true,
        not_for_training: true,
        not_for_production: true,
    };
}

function buildL3Preview(rawRow) {
    const source = rawRow?.data_version || 'PHASE4.43_SYNTHETIC';
    const marker = buildSyntheticMarker(source);

    return {
        target_table: 'l3_features',
        match_id: rawRow?.match_id || null,
        external_id: rawRow?.external_id || null,
        would_insert_l3_features: false,
        would_update_matches: false,
        would_trigger_elo: false,
        preview_only: true,
        synthetic_input: true,
        not_for_training: true,
        not_for_production: true,
        planned_jsonb_preview: {
            golden_features: {
                ...marker,
                match_identity_only: true,
            },
            tactical_features: {
                ...marker,
                extraction_not_run: true,
            },
            odds_features: {
                ...marker,
                odds_extraction_not_run: true,
            },
            elo_features: {
                ...marker,
                elo_not_run: true,
            },
            stitch_summary: {
                ...marker,
                source_raw_match_data_id: rawRow?.id || null,
                data_hash: rawRow?.data_hash || null,
                stitch_not_run: true,
            },
        },
    };
}

function buildTargetMatchStatus(match) {
    return {
        match_found: Boolean(match),
        match_id: match?.match_id || null,
        league_name: match?.league_name || null,
        season: match?.season || null,
        home_team: match?.home_team || null,
        away_team: match?.away_team || null,
        home_score: match?.home_score ?? null,
        away_score: match?.away_score ?? null,
        actual_result: match?.actual_result || null,
        match_date: match?.match_date ? new Date(match.match_date).toISOString() : null,
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

function buildRawStatus(rawRow) {
    const rawData = rawRow?.raw_data || {};
    const metadata = rawData.metadata || {};

    return {
        raw_match_data_found: Boolean(rawRow),
        raw_match_data_id: rawRow?.id || null,
        match_id: rawRow?.match_id || null,
        external_id: rawRow?.external_id || null,
        data_version: rawRow?.data_version || null,
        data_hash: rawRow?.data_hash || null,
        collected_at: rawRow?.collected_at ? new Date(rawRow.collected_at).toISOString() : null,
        synthetic: asBoolean(metadata.synthetic),
        engineering_test_only: asBoolean(metadata.engineering_test_only),
        not_real_external_data: asBoolean(metadata.not_real_external_data),
        not_for_training: asBoolean(metadata.not_for_training),
        not_for_production: asBoolean(metadata.not_for_production),
        has_matchId: Object.hasOwn(rawData, 'matchId'),
        has_general: Object.hasOwn(rawData, 'general'),
        has_header: Object.hasOwn(rawData, 'header'),
        has_content: Object.hasOwn(rawData, 'content'),
    };
}

function buildDownstreamStatus(statusRow) {
    return {
        l3_features_exists: statusRow?.l3_features_exists === true,
        match_features_training_exists: statusRow?.match_features_training_exists === true,
        predictions_exists: statusRow?.predictions_exists === true,
    };
}

function buildGatingDecision(rawStatus) {
    const syntheticSafetyComplete =
        rawStatus.synthetic === true &&
        rawStatus.engineering_test_only === true &&
        rawStatus.not_real_external_data === true &&
        rawStatus.not_for_training === true &&
        rawStatus.not_for_production === true;

    return {
        can_write_l3_now: false,
        reason: 'synthetic raw input requires separate manual authorization',
        real_training_allowed: false,
        synthetic_safety_complete: syntheticSafetyComplete,
    };
}

function buildPayload({ args, matchRow, rawRow, statusRow }) {
    const targetMatch = buildTargetMatchStatus(matchRow);
    const rawStatus = buildRawStatus(rawRow);

    return {
        mode: 'dry-run',
        phase: '4.44',
        match_id: args.matchId,
        target_match: targetMatch,
        raw_match_data: rawStatus,
        downstream_status: buildDownstreamStatus(statusRow),
        l3_preview: buildL3Preview(rawRow),
        gating_decision: buildGatingDecision(rawStatus),
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
        `raw_match_data_found=${payload.raw_match_data.raw_match_data_found}`,
        `synthetic=${payload.raw_match_data.synthetic}`,
        `engineering_test_only=${payload.raw_match_data.engineering_test_only}`,
        `not_real_external_data=${payload.raw_match_data.not_real_external_data}`,
        `not_for_training=${payload.raw_match_data.not_for_training}`,
        `not_for_production=${payload.raw_match_data.not_for_production}`,
        `l3_features_exists=${payload.downstream_status.l3_features_exists}`,
        `match_features_training_exists=${payload.downstream_status.match_features_training_exists}`,
        `predictions_exists=${payload.downstream_status.predictions_exists}`,
        `would_insert_l3_features=${payload.l3_preview.would_insert_l3_features}`,
        `would_update_matches=${payload.l3_preview.would_update_matches}`,
        `would_trigger_elo=${payload.l3_preview.would_trigger_elo}`,
        `preview_only=${payload.l3_preview.preview_only}`,
        `can_write_l3_now=${payload.gating_decision.can_write_l3_now}`,
        `real_training_allowed=${payload.gating_decision.real_training_allowed}`,
        '',
        'target_match:',
        JSON.stringify(payload.target_match, null, 2),
        '',
        'raw_match_data:',
        JSON.stringify(payload.raw_match_data, null, 2),
        '',
        'downstream_status:',
        JSON.stringify(payload.downstream_status, null, 2),
        '',
        'l3_preview:',
        JSON.stringify(payload.l3_preview, null, 2),
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
            league_name,
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
            id,
            match_id,
            external_id,
            raw_data,
            data_version,
            data_hash,
            collected_at
        FROM raw_match_data
        WHERE match_id = $1
        ORDER BY collected_at DESC
        LIMIT 1
    `;
    const result = await safeSelect(pool, sql, [matchId]);
    return result.rows[0] || null;
}

async function loadDownstreamStatus(pool, matchId) {
    const sql = `
        SELECT
            EXISTS (SELECT 1 FROM l3_features WHERE match_id = $1) AS l3_features_exists,
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
            script: 'synthetic_l3_preflight.js',
            tables: ['l3_features'],
            operations: ['INSERT'],
        });
        console.error('BLOCKED: synthetic L3 commit is not wired in Phase 4.44.');
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
        const statusRow = await loadDownstreamStatus(pool, args.matchId);
        const payload = buildPayload({ args, matchRow, rawRow, statusRow });

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
