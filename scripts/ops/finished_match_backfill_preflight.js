#!/usr/bin/env node
/**
 * Safe finished match backfill preflight gate.
 *
 * Phase 4.40 keeps all commit paths blocked. The script only performs
 * SELECT-only DB checks and local fixture read-only analysis for a finished
 * match that is missing downstream raw/L3/training/prediction records.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
const { assertDbWriteAllowed } = require('./helpers/db_write_guard');

const FORBIDDEN_SQL =
    /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|UPSERT|MERGE|GRANT|REVOKE|CREATE\s+INDEX)\b/i;
const TRUE_VALUES = new Set(['true', 't', '1', 'yes', 'y']);
const FINISHED_VALUES = new Set(['finished', 'completed', 'complete', 'full_time', 'ft']);

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/finished_match_backfill_preflight.js --match-id <id> [--json] [--fixture <path>]',
        '  node scripts/ops/finished_match_backfill_preflight.js --match-id <id> --commit',
        '',
        'Safety:',
        '  Preflight only in Phase 4.40; --commit is blocked and not wired.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        matchId: null,
        json: false,
        fixture: null,
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
        } else if (token === '--fixture') {
            args.fixture = argv[index + 1];
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

function normalizeName(value) {
    return normalizeText(value)
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase();
}

function asBoolean(value) {
    if (typeof value === 'boolean') return value;
    const normalized = normalizeText(value).toLowerCase();
    return TRUE_VALUES.has(normalized);
}

function isFinishedFlag(value) {
    if (typeof value === 'boolean') return value;
    const normalized = normalizeText(value).toLowerCase();
    return FINISHED_VALUES.has(normalized) || TRUE_VALUES.has(normalized);
}

function pickFirst(values) {
    for (const value of values) {
        const normalized = normalizeText(value);
        if (normalized) {
            return normalized;
        }
    }
    return null;
}

function readOptionalFixture(rawPath, target) {
    if (!rawPath) {
        return {
            provided: false,
            requested_path: null,
            resolved_path: null,
            exists: false,
            parse_ok: false,
            match_id_in_fixture: null,
            home_team_in_fixture: null,
            away_team_in_fixture: null,
            finished_flag_in_fixture: null,
            score_in_fixture: null,
            team_match: false,
            direct_match: false,
            available_direct_fixture: false,
            warnings: ['no_fixture_provided'],
        };
    }

    const resolvedPath = path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(process.cwd(), rawPath);
    if (!fs.existsSync(resolvedPath)) {
        return {
            provided: true,
            requested_path: rawPath,
            resolved_path: resolvedPath,
            exists: false,
            parse_ok: false,
            match_id_in_fixture: null,
            home_team_in_fixture: null,
            away_team_in_fixture: null,
            finished_flag_in_fixture: null,
            score_in_fixture: null,
            team_match: false,
            direct_match: false,
            available_direct_fixture: false,
            warnings: ['fixture_not_found'],
        };
    }

    if (!fs.statSync(resolvedPath).isFile()) {
        return {
            provided: true,
            requested_path: rawPath,
            resolved_path: resolvedPath,
            exists: true,
            parse_ok: false,
            match_id_in_fixture: null,
            home_team_in_fixture: null,
            away_team_in_fixture: null,
            finished_flag_in_fixture: null,
            score_in_fixture: null,
            team_match: false,
            direct_match: false,
            available_direct_fixture: false,
            warnings: ['fixture_not_a_file'],
        };
    }

    let fixture;
    try {
        fixture = JSON.parse(fs.readFileSync(resolvedPath, 'utf8'));
    } catch (error) {
        return {
            provided: true,
            requested_path: rawPath,
            resolved_path: resolvedPath,
            exists: true,
            parse_ok: false,
            match_id_in_fixture: null,
            home_team_in_fixture: null,
            away_team_in_fixture: null,
            finished_flag_in_fixture: null,
            score_in_fixture: null,
            team_match: false,
            direct_match: false,
            available_direct_fixture: false,
            warnings: [`fixture_parse_error:${error.message}`],
        };
    }

    const matchIdInFixture = pickFirst([
        fixture?.match_id,
        fixture?.matchId,
        fixture?.raw_data?.matchId,
        fixture?.raw_data?.general?.matchId,
        fixture?.general?.matchId,
        fixture?.data?.match?.id,
    ]);
    const homeTeamInFixture = pickFirst([
        fixture?.home_team,
        fixture?.raw_data?.general?.homeTeam?.name,
        fixture?.raw_data?.header?.teams?.[0]?.name,
        fixture?.general?.homeTeam?.name,
        fixture?.content?.lineup?.homeTeam?.teamName,
        fixture?.data?.match?.homeTeam?.name,
    ]);
    const awayTeamInFixture = pickFirst([
        fixture?.away_team,
        fixture?.raw_data?.general?.awayTeam?.name,
        fixture?.raw_data?.header?.teams?.[1]?.name,
        fixture?.general?.awayTeam?.name,
        fixture?.content?.lineup?.awayTeam?.teamName,
        fixture?.data?.match?.awayTeam?.name,
    ]);
    const finishedFlag = [
        fixture?.raw_data?.general?.finished,
        fixture?.raw_data?.header?.status?.finished,
        fixture?.general?.status?.finished,
        fixture?.general?.status,
        fixture?.data?.match?.status?.finished,
        fixture?.data?.match?.status?.status,
    ]
        .map(value => (value === undefined ? null : value))
        .find(value => value !== null);
    const scoreInFixture = pickFirst([
        fixture?.raw_data?.header?.status?.scoreStr,
        fixture?.general?.score,
        fixture?.data?.match?.status?.scoreStr,
    ]);

    const teamMatch =
        normalizeName(homeTeamInFixture) === normalizeName(target.home_team) &&
        normalizeName(awayTeamInFixture) === normalizeName(target.away_team);
    const directMatch = normalizeText(matchIdInFixture) === normalizeText(target.match_id);
    const warnings = [];

    if (!directMatch) {
        if (teamMatch) {
            warnings.push('fixture_team_match_only_not_direct_match_id');
        } else {
            warnings.push('fixture_mismatch_target_match');
        }
    }
    if (!isFinishedFlag(finishedFlag)) {
        warnings.push('fixture_not_marked_finished');
    }

    return {
        provided: true,
        requested_path: rawPath,
        resolved_path: resolvedPath,
        exists: true,
        parse_ok: true,
        match_id_in_fixture: matchIdInFixture,
        home_team_in_fixture: homeTeamInFixture,
        away_team_in_fixture: awayTeamInFixture,
        finished_flag_in_fixture: finishedFlag,
        score_in_fixture: scoreInFixture,
        team_match: teamMatch,
        direct_match: directMatch,
        available_direct_fixture: directMatch,
        warnings,
    };
}

function buildNonExecutionConfirmations() {
    return [
        'no_db_writes',
        'no_insert',
        'no_update',
        'no_delete',
        'no_raw_ingest',
        'no_l3_write',
        'no_training_feature_write',
        'no_prediction_write',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
        'no_external_network',
    ];
}

function buildBackfillPlan(chain, fixtureSummary) {
    const hasRaw = chain.has_raw_match_data === true;
    const hasL3 = chain.has_l3_features === true;
    const hasTraining = chain.has_training_features === true;

    return {
        raw_match_data: {
            required: !hasRaw,
            available_direct_fixture: fixtureSummary.available_direct_fixture === true,
            recommended_next_step: hasRaw
                ? 'raw_match_data already exists; do not schedule raw backfill unless a dedicated corrective runbook is approved.'
                : fixtureSummary.available_direct_fixture
                  ? 'Run make data-raw-dry-run SAMPLE_RAW=<fixture> MATCH_ID=<id> first; any write requires a separate authorized phase.'
                  : 'No direct raw fixture is available yet. Prepare or approve a local raw fixture for this exact match before any downstream backfill.',
        },
        l3_features: {
            blocked_until_raw: !hasRaw,
            recommended_next_step: hasRaw
                ? 'Use make data-l3-write-dry-run SAMPLE_RAW=<fixture> MATCH_ID=<id> only after confirming a matching raw fixture strategy.'
                : 'Blocked until raw_match_data exists for the target match.',
        },
        match_features_training: {
            blocked_until_l3: !hasL3,
            recommended_next_step: hasL3
                ? 'Use make data-training-feature-dry-run MATCH_ID=<id> after L3 is present and validated.'
                : 'Blocked until l3_features exists for the target match.',
        },
        predictions: {
            blocked_until_training_features: !hasTraining,
            must_not_predict_without_approved_artifact: true,
            recommended_next_step: hasTraining
                ? 'Use make data-prediction-write-dry-run MATCH_ID=<id> only after an approved model artifact policy exists.'
                : 'Blocked until match_features_training exists for the target match.',
        },
    };
}

function buildPayload({ args, chain, fixtureSummary }) {
    const chainStatus = chain
        ? {
              match_found: true,
              is_finished: chain.is_finished === true,
              has_actual_result: Boolean(chain.actual_result),
              has_score: chain.home_score !== null && chain.away_score !== null,
              has_raw_match_data: chain.has_raw_match_data === true,
              has_l3_features: chain.has_l3_features === true,
              has_training_features: chain.has_training_features === true,
              has_predictions: chain.has_predictions === true,
          }
        : {
              match_found: false,
              is_finished: false,
              has_actual_result: false,
              has_score: false,
              has_raw_match_data: false,
              has_l3_features: false,
              has_training_features: false,
              has_predictions: false,
          };

    return {
        mode: 'preflight',
        match_id: args.matchId,
        fixture_path: args.fixture || null,
        chain_status: chainStatus,
        target_match: chain
            ? {
                  match_id: chain.match_id,
                  league_name: chain.league_name,
                  season: chain.season,
                  home_team: chain.home_team,
                  away_team: chain.away_team,
                  home_score: chain.home_score,
                  away_score: chain.away_score,
                  actual_result: chain.actual_result,
                  match_date: chain.match_date ? new Date(chain.match_date).toISOString() : null,
                  status: chain.status,
                  is_finished: chain.is_finished === true,
              }
            : null,
        backfill_plan: buildBackfillPlan(chainStatus, fixtureSummary),
        fixture_candidate_summary: fixtureSummary,
        warnings: [...(chainStatus.match_found ? [] : ['match_not_found']), ...fixtureSummary.warnings],
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function formatText(payload) {
    const lines = [
        `mode=${payload.mode}`,
        `match_id=${payload.match_id}`,
        `fixture_path=${payload.fixture_path || ''}`,
        `match_found=${payload.chain_status.match_found}`,
        `is_finished=${payload.chain_status.is_finished}`,
        `has_actual_result=${payload.chain_status.has_actual_result}`,
        `has_score=${payload.chain_status.has_score}`,
        `has_raw_match_data=${payload.chain_status.has_raw_match_data}`,
        `has_l3_features=${payload.chain_status.has_l3_features}`,
        `has_training_features=${payload.chain_status.has_training_features}`,
        `has_predictions=${payload.chain_status.has_predictions}`,
        `raw_match_data.required=${payload.backfill_plan.raw_match_data.required}`,
        `raw_match_data.available_direct_fixture=${payload.backfill_plan.raw_match_data.available_direct_fixture}`,
        `l3_features.blocked_until_raw=${payload.backfill_plan.l3_features.blocked_until_raw}`,
        `match_features_training.blocked_until_l3=${payload.backfill_plan.match_features_training.blocked_until_l3}`,
        `predictions.blocked_until_training_features=${payload.backfill_plan.predictions.blocked_until_training_features}`,
        `predictions.must_not_predict_without_approved_artifact=${payload.backfill_plan.predictions.must_not_predict_without_approved_artifact}`,
        '',
        'target_match:',
        JSON.stringify(payload.target_match, null, 2),
        '',
        'fixture_candidate_summary:',
        JSON.stringify(payload.fixture_candidate_summary, null, 2),
        '',
        'warnings:',
        payload.warnings.length ? payload.warnings.map(value => `  ${value}`).join('\n') : '  none',
        '',
        'backfill_plan:',
        JSON.stringify(payload.backfill_plan, null, 2),
        '',
        'non_execution_confirmations:',
        payload.non_execution_confirmations.map(value => `  ${value}`).join('\n'),
    ];

    return lines.join('\n');
}

async function loadChain(pool, matchId) {
    const sql = `
        SELECT
            m.match_id,
            m.league_name,
            m.season,
            m.home_team,
            m.away_team,
            m.home_score,
            m.away_score,
            m.actual_result,
            m.match_date,
            m.status,
            m.is_finished,
            EXISTS (SELECT 1 FROM raw_match_data r WHERE r.match_id = m.match_id) AS has_raw_match_data,
            EXISTS (SELECT 1 FROM l3_features l WHERE l.match_id = m.match_id) AS has_l3_features,
            EXISTS (SELECT 1 FROM match_features_training t WHERE t.match_id = m.match_id) AS has_training_features,
            EXISTS (SELECT 1 FROM predictions p WHERE p.match_id = m.match_id) AS has_predictions
        FROM matches m
        WHERE m.match_id = $1
    `;

    const result = await safeSelect(pool, sql, [matchId]);
    return result.rows[0] || null;
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
        console.log(usage());
        return;
    }
    if (args.commit) {
        assertDbWriteAllowed({
            script: 'finished_match_backfill_preflight.js',
            tables: ['raw_match_data', 'matches', 'l3_features', 'match_features_training', 'predictions'],
            operations: ['INSERT', 'UPDATE'],
        });
        console.error('BLOCKED: finished match backfill commit is not wired in Phase 4.40.');
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
        const chain = await loadChain(pool, args.matchId);
        const fixtureSummary = readOptionalFixture(args.fixture, {
            match_id: args.matchId,
            home_team: chain?.home_team || '',
            away_team: chain?.away_team || '',
        });
        const payload = buildPayload({ args, chain, fixtureSummary });

        console.log(args.json ? JSON.stringify(payload, null, 2) : formatText(payload));
    } finally {
        await pool.end();
    }
}

main().catch(error => {
    console.error(
        JSON.stringify(
            {
                mode: 'preflight',
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
