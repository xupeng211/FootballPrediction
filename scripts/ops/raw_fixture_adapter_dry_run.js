#!/usr/bin/env node
/**
 * Safe raw fixture adapter dry-run gate.
 *
 * Phase 4.41 validates whether a local JSON fixture can be used as raw data
 * for one finished match. It never writes DB rows, creates files, or calls
 * ingest/L3/training/prediction paths.
 */

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

const FORBIDDEN_SQL =
    /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|UPSERT|MERGE|GRANT|REVOKE|CREATE\s+INDEX)\b/i;
const FINISHED_VALUES = new Set(['finished', 'completed', 'complete', 'full_time', 'ft']);
const TRUE_VALUES = new Set(['true', 't', '1', 'yes', 'y']);

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/raw_fixture_adapter_dry_run.js --match-id <id> --fixture <path> [--json] [--allow-synthetic]',
        '  node scripts/ops/raw_fixture_adapter_dry_run.js --match-id <id> --fixture <path> --commit',
        '',
        'Safety:',
        '  Dry-run only in Phase 4.41; --commit is blocked and not wired.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        matchId: null,
        fixture: null,
        json: false,
        allowSynthetic: false,
        commit: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--match-id') {
            args.matchId = argv[index + 1];
            index += 1;
        } else if (token === '--fixture') {
            args.fixture = argv[index + 1];
            index += 1;
        } else if (token === '--json') {
            args.json = true;
        } else if (token === '--allow-synthetic') {
            args.allowSynthetic = true;
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

function normalizeStatus(value) {
    return normalizeText(value).toLowerCase();
}

function isFinishedLike(value) {
    if (typeof value === 'boolean') return value;
    const normalized = normalizeStatus(value);
    return FINISHED_VALUES.has(normalized) || TRUE_VALUES.has(normalized);
}

function toInt(value) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number.parseInt(String(value), 10);
    return Number.isFinite(parsed) ? parsed : null;
}

function pickFirst(values) {
    for (const value of values) {
        const normalized = normalizeText(value);
        if (normalized) return normalized;
    }
    return null;
}

function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function stableStringify(value) {
    if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
    if (value && typeof value === 'object') {
        return `{${Object.keys(value)
            .sort()
            .map(key => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
            .join(',')}}`;
    }
    return JSON.stringify(value);
}

function sha256(value) {
    return crypto.createHash('sha256').update(value).digest('hex');
}

function resolveFixture(rawPath) {
    if (!rawPath) throw new Error('Missing required --fixture <path>');
    const resolved = path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(process.cwd(), rawPath);
    if (!fs.existsSync(resolved)) throw new Error(`Fixture file not found: ${rawPath}`);
    if (!fs.statSync(resolved).isFile()) throw new Error(`Fixture path is not a file: ${rawPath}`);
    const data = JSON.parse(fs.readFileSync(resolved, 'utf8'));
    return { resolved, data };
}

function rootRawData(fixture) {
    return asObject(fixture.raw_data).matchId || fixture.raw_data?.general || fixture.raw_data?.header
        ? fixture.raw_data
        : fixture;
}

function scoreFromObject(value) {
    if (!value || typeof value !== 'object') return { home: null, away: null, raw: value ?? null };
    return {
        home: toInt(value.home ?? value.homeScore ?? value[0]),
        away: toInt(value.away ?? value.awayScore ?? value[1]),
        raw: value,
    };
}

function scoreFromString(value) {
    const normalized = normalizeText(value);
    const match = normalized.match(/^(\d+)\s*[-:]\s*(\d+)$/);
    if (!match) return { home: null, away: null, raw: normalized || null };
    return {
        home: toInt(match[1]),
        away: toInt(match[2]),
        raw: normalized,
    };
}

function extractScore(rawData) {
    const statusScore = rawData?.header?.status?.scoreStr || rawData?.data?.match?.status?.scoreStr;
    if (statusScore) return scoreFromString(statusScore);
    const generalScore = rawData?.general?.score || rawData?.score;
    if (typeof generalScore === 'string') return scoreFromString(generalScore);
    if (typeof generalScore === 'object') return scoreFromObject(generalScore);
    const headerTeams = rawData?.header?.teams;
    if (Array.isArray(headerTeams) && headerTeams.length >= 2) {
        return {
            home: toInt(headerTeams[0]?.score),
            away: toInt(headerTeams[1]?.score),
            raw: headerTeams.map(team => team?.score).join('-'),
        };
    }
    return { home: null, away: null, raw: null };
}

function extractStatus(rawData) {
    return pickFirst([
        rawData?.general?.status,
        rawData?.header?.status?.reason?.shortKey,
        rawData?.header?.status?.reason?.short,
        rawData?.header?.status?.finished,
        rawData?.data?.match?.status?.status,
        rawData?.data?.match?.status?.finished,
    ]);
}

function extractFixtureInfo(fixture) {
    const rawData = rootRawData(fixture);
    const score = extractScore(rawData);
    const status = extractStatus(rawData);
    const content = asObject(rawData?.content);
    const stats = content.stats || rawData?.content?.stats || rawData?.data?.match?.content?.stats;
    const lineup = content.lineup || rawData?.content?.lineup;
    const shotmap = content.shotmap || rawData?.content?.shotmap;
    const momentum = content.momentum || rawData?.content?.momentum;

    return {
        fixture_match_id: pickFirst([
            fixture?.match_id,
            fixture?.matchId,
            fixture?.raw_data?.matchId,
            fixture?.raw_data?.general?.matchId,
            rawData?.matchId,
            rawData?.general?.matchId,
            rawData?.data?.match?.id,
        ]),
        external_id: pickFirst([fixture?.external_id, rawData?.matchId, rawData?.general?.matchId]),
        home_team: pickFirst([
            fixture?.home_team,
            rawData?.general?.homeTeam?.name,
            rawData?.header?.teams?.[0]?.name,
            rawData?.content?.lineup?.homeTeam?.teamName,
            rawData?.content?.lineup?.homeTeam?.name,
            rawData?.data?.match?.homeTeam?.name,
        ]),
        away_team: pickFirst([
            fixture?.away_team,
            rawData?.general?.awayTeam?.name,
            rawData?.header?.teams?.[1]?.name,
            rawData?.content?.lineup?.awayTeam?.teamName,
            rawData?.content?.lineup?.awayTeam?.name,
            rawData?.data?.match?.awayTeam?.name,
        ]),
        score,
        status,
        status_is_finished: isFinishedLike(status),
        has_general: Boolean(rawData?.general),
        has_header: Boolean(rawData?.header),
        has_content: Boolean(rawData?.content),
        has_stats: Boolean(stats),
        has_lineup: Boolean(lineup),
        has_shotmap: Boolean(shotmap),
        has_momentum: Boolean(momentum),
        raw_data_constraint_ok: Boolean(rawData?.matchId || rawData?.general || rawData?.header),
        raw_data_not_empty: Object.keys(asObject(rawData)).length > 0,
        raw_data_hash_preview: sha256(stableStringify(rawData)),
        raw_data_top_level_keys: Object.keys(asObject(rawData)).sort(),
    };
}

function buildMatchChecks(match, fixtureInfo) {
    return {
        match_id_matches: normalizeText(fixtureInfo.fixture_match_id) === normalizeText(match.match_id),
        home_team_matches: normalizeName(fixtureInfo.home_team) === normalizeName(match.home_team),
        away_team_matches: normalizeName(fixtureInfo.away_team) === normalizeName(match.away_team),
        score_matches:
            fixtureInfo.score.home === toInt(match.home_score) && fixtureInfo.score.away === toInt(match.away_score),
        status_reasonable: fixtureInfo.status_is_finished === true,
        raw_data_constraint_ok: fixtureInfo.raw_data_constraint_ok === true && fixtureInfo.raw_data_not_empty === true,
    };
}

function buildWarnings(checks, fixtureInfo) {
    const warnings = [];
    if (!checks.match_id_matches) warnings.push('fixture_mismatch:match_id');
    if (!checks.home_team_matches) warnings.push('fixture_mismatch:home_team');
    if (!checks.away_team_matches) warnings.push('fixture_mismatch:away_team');
    if (!checks.score_matches) warnings.push('fixture_mismatch:score');
    if (!checks.status_reasonable) warnings.push('fixture_status_not_finished_or_unknown');
    if (!checks.raw_data_constraint_ok) warnings.push('fixture_raw_data_constraint_not_satisfied');
    if (!checks.match_id_matches || !checks.home_team_matches || !checks.away_team_matches || !checks.score_matches) {
        warnings.push('cannot_use_this_fixture_as_raw_data_for_target_match');
        warnings.push('do_not_impersonate_another_match');
    }
    if (!fixtureInfo.has_content) warnings.push('fixture_missing_content');
    return warnings;
}

function buildSyntheticPreview({ args, match }) {
    if (!args.allowSynthetic) return null;
    return {
        synthetic: true,
        synthetic_preview_only: true,
        engineering_test_only: true,
        not_real_external_data: true,
        not_for_training: true,
        not_production_data: true,
        would_create_fixture_file: false,
        would_insert_raw_match_data: false,
        provenance_required: {
            data_source: 'synthetic_local_fixture',
            data_version: 'PHASE4.41_SYNTHETIC_PREVIEW_ONLY',
            metadata_flags: [
                'synthetic=true',
                'engineering_test_only=true',
                'not_real_external_data=true',
                'not_for_training=true',
            ],
        },
        raw_data_shape_preview: {
            matchId: match?.match_id || args.matchId,
            general: {
                matchId: match?.match_id || args.matchId,
                homeTeam: { name: match?.home_team || null },
                awayTeam: { name: match?.away_team || null },
                finished: true,
            },
            header: {
                status: {
                    finished: true,
                    scoreStr:
                        match?.home_score !== null && match?.away_score !== null
                            ? `${match.home_score}-${match.away_score}`
                            : null,
                },
            },
        },
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
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
        'no_external_network',
        'no_file_create',
    ];
}

function buildTargetMatchPayload(match) {
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
        status: match?.status || null,
        is_finished: match?.is_finished === true,
        has_raw_match_data: match?.has_raw_match_data === true,
    };
}

function buildDecisionPayload(checks) {
    const directFixtureMatch =
        checks.match_id_matches &&
        checks.home_team_matches &&
        checks.away_team_matches &&
        checks.score_matches &&
        checks.status_reasonable &&
        checks.raw_data_constraint_ok;

    return {
        direct_fixture_match: directFixtureMatch,
        fixture_can_be_used_for_target: directFixtureMatch,
        synthetic_required: !directFixtureMatch,
        would_insert_raw_match_data: false,
        would_update_matches: false,
        would_trigger_l3: false,
    };
}

function buildPayload({ args, match, fixturePath, fixtureInfo, checks }) {
    const targetMatch = buildTargetMatchPayload(match);
    const decision = buildDecisionPayload(checks);
    const warnings = buildWarnings(checks, fixtureInfo);

    return {
        mode: 'dry-run',
        match_id: args.matchId,
        fixture_path: args.fixture,
        resolved_fixture_path: fixturePath,
        target_match: targetMatch,
        fixture: {
            exists: true,
            ...fixtureInfo,
        },
        matching_checks: checks,
        decision,
        would_insert_preview: {
            target_table: 'raw_match_data',
            match_id: args.matchId,
            external_id: fixtureInfo.external_id,
            data_version_candidate: decision.direct_fixture_match
                ? 'PHASE4.41_REAL_LOCAL_FIXTURE_DRY_RUN_ONLY'
                : 'not_available_for_mismatched_fixture',
            data_hash_preview: fixtureInfo.raw_data_hash_preview,
            would_insert_raw_match_data: false,
        },
        synthetic_preview: buildSyntheticPreview({ args, match }),
        warnings,
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function formatText(payload) {
    return [
        `mode=${payload.mode}`,
        `match_id=${payload.match_id}`,
        `fixture_path=${payload.fixture_path}`,
        `fixture.exists=${payload.fixture.exists}`,
        `match_found=${payload.target_match.match_found}`,
        `direct_fixture_match=${payload.decision.direct_fixture_match}`,
        `fixture_can_be_used_for_target=${payload.decision.fixture_can_be_used_for_target}`,
        `synthetic_required=${payload.decision.synthetic_required}`,
        `would_insert_raw_match_data=${payload.decision.would_insert_raw_match_data}`,
        `would_update_matches=${payload.decision.would_update_matches}`,
        `would_trigger_l3=${payload.decision.would_trigger_l3}`,
        '',
        'target_match:',
        JSON.stringify(payload.target_match, null, 2),
        '',
        'fixture:',
        JSON.stringify(payload.fixture, null, 2),
        '',
        'matching_checks:',
        JSON.stringify(payload.matching_checks, null, 2),
        '',
        'decision:',
        JSON.stringify(payload.decision, null, 2),
        '',
        'would_insert_preview:',
        JSON.stringify(payload.would_insert_preview, null, 2),
        '',
        'synthetic_preview:',
        payload.synthetic_preview ? JSON.stringify(payload.synthetic_preview, null, 2) : '  null',
        '',
        'warnings:',
        payload.warnings.length ? payload.warnings.map(value => `  ${value}`).join('\n') : '  none',
        '',
        'non_execution_confirmations:',
        payload.non_execution_confirmations.map(value => `  ${value}`).join('\n'),
    ].join('\n');
}

async function loadMatch(pool, matchId) {
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
            m.status,
            m.is_finished,
            EXISTS (SELECT 1 FROM raw_match_data r WHERE r.match_id = m.match_id) AS has_raw_match_data
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
        console.error('BLOCKED: raw fixture adapter commit is not wired in Phase 4.41.');
        process.exitCode = 1;
        return;
    }
    if (!args.matchId || !args.fixture) {
        console.error('ERROR: provide --match-id <id> and --fixture <path>');
        console.error(usage());
        process.exitCode = 1;
        return;
    }

    const { resolved, data: fixture } = resolveFixture(args.fixture);
    const fixtureInfo = extractFixtureInfo(fixture);
    const pool = new Pool(buildDbConfig());

    try {
        const match = await loadMatch(pool, args.matchId);
        if (!match) {
            throw new Error(`Target match not found: ${args.matchId}`);
        }
        const checks = buildMatchChecks(match, fixtureInfo);
        const payload = buildPayload({ args, match, fixturePath: resolved, fixtureInfo, checks });

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
