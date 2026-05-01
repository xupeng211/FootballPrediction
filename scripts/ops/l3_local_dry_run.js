#!/usr/bin/env node
/**
 * Safe local L3 dry-run gate.
 *
 * This script only reads a local fixture and performs SELECT-only DB checks.
 * It deliberately does not import FeatureSmelter, L3Writer, l3_stitch, or Elo
 * recomputation code because those paths can write database state.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

const { extractGoldenFeatures } = require('../../src/feature_engine/extractors/GoldenFeatureExtractor');
const { extractTacticalFeatures } = require('../../src/feature_engine/extractors/TacticalMomentumExtractor');
const {
    extractOddsMovementFeatures,
    extractOddsMovementFeaturesFromOddsData,
} = require('../../src/feature_engine/extractors/OddsMovementExtractor');

const FORBIDDEN_SQL = /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|UPSERT|MERGE|GRANT|REVOKE)\b/i;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l3_local_dry_run.js --fixture <path> --match-id <id> [--json]',
        '',
        'Safety:',
        '  SELECT-only DB checks; no L3 writes, no schema writes, no Elo, no network.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        fixture: null,
        matchId: null,
        json: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--fixture') {
            args.fixture = argv[index + 1];
            index += 1;
        } else if (token === '--match-id') {
            args.matchId = argv[index + 1];
            index += 1;
        } else if (token === '--json') {
            args.json = true;
        } else if (token === '--help' || token === '-h') {
            args.help = true;
        } else {
            throw new Error(`Unknown argument: ${token}`);
        }
    }

    return args;
}

function readJsonFile(filePath) {
    const resolved = path.resolve(process.cwd(), filePath);
    const raw = fs.readFileSync(resolved, 'utf8');
    return {
        resolved,
        data: JSON.parse(raw),
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

function normalizeFixtureMatchId(fixture) {
    return String(fixture.match_id || fixture.raw_data?.matchId || fixture.raw_data?.general?.matchId || '');
}

function assertFixtureRoot(fixture, expectedMatchId) {
    const actualMatchId = normalizeFixtureMatchId(fixture);

    if (!fixture || typeof fixture !== 'object') {
        throw new Error('Fixture root must be a JSON object');
    }
    if (actualMatchId !== expectedMatchId) {
        throw new Error(`Fixture match_id does not match --match-id (${actualMatchId} != ${expectedMatchId})`);
    }
}

function collectRawDataMissingFields(rawData) {
    const missing = [];

    if (!rawData || typeof rawData !== 'object' || Array.isArray(rawData)) {
        missing.push('raw_data');
    }

    const rawDataObject = rawData || {};
    if (!('matchId' in rawDataObject) && !rawDataObject.general && !rawDataObject.header) {
        missing.push('raw_data.matchId_or_general_or_header');
    }
    if (!rawDataObject.general) {
        missing.push('raw_data.general');
    }
    if (!rawDataObject.header) {
        missing.push('raw_data.header');
    }
    if (!rawDataObject.content) {
        missing.push('raw_data.content');
    }
    if (!rawDataObject.content?.lineup?.homeTeam) {
        missing.push('raw_data.content.lineup.homeTeam');
    }
    if (!rawDataObject.content?.lineup?.awayTeam) {
        missing.push('raw_data.content.lineup.awayTeam');
    }
    if (!Array.isArray(rawDataObject.content?.stats)) {
        missing.push('raw_data.content.stats[]');
    }
    if (!Array.isArray(rawDataObject.content?.shotmap?.shots)) {
        missing.push('raw_data.content.shotmap.shots[]');
    }

    return missing;
}

function validateFixture(fixture, expectedMatchId) {
    assertFixtureRoot(fixture, expectedMatchId);
    return collectRawDataMissingFields(fixture.raw_data);
}

function toPositiveNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function normalizeOddsPayload(payload, collectedAt) {
    return {
        home: toPositiveNumber(payload?.home),
        draw: toPositiveNumber(payload?.draw),
        away: toPositiveNumber(payload?.away),
        collectedAt: collectedAt ? new Date(collectedAt).toISOString() : null,
    };
}

function buildOddsDataFromHistoryRows(rows) {
    const oneX2Rows = rows.filter(row => String(row.market_type || '').toLowerCase() === '1x2');
    const opening = oneX2Rows
        .map(row => normalizeOddsPayload(row.open_odds, row.collected_at))
        .filter(point => point.home && point.draw && point.away);
    const closing = oneX2Rows
        .map(row => normalizeOddsPayload(row.close_odds, row.collected_at))
        .filter(point => point.home && point.draw && point.away);

    const initial = opening[0] || closing[0] || null;
    const current = closing[closing.length - 1] || initial;
    const history = [];

    if (initial) {
        history.push(initial);
    }
    if (
        current &&
        (!initial || current.home !== initial.home || current.draw !== initial.draw || current.away !== initial.away)
    ) {
        history.push(current);
    }

    return {
        initial,
        current,
        history,
        hasData: Boolean(initial || current || history.length > 0),
        odds_source: oneX2Rows.length > 0 ? 'bookmaker_odds_history' : 'none',
    };
}

function uniqueSorted(values) {
    return [...new Set(values.filter(Boolean))].sort((left, right) => left.localeCompare(right));
}

function summarizeFixture(rawData) {
    const shotmapShots = Array.isArray(rawData?.content?.shotmap?.shots) ? rawData.content.shotmap.shots.length : 0;
    const momentum = rawData?.content?.momentum?.data || rawData?.content?.momentum?.main?.data || [];
    const lineup = rawData?.content?.lineup || {};

    return {
        lineup_available: Boolean(lineup.homeTeam && lineup.awayTeam),
        home_starters: Array.isArray(lineup.homeTeam?.starters) ? lineup.homeTeam.starters.length : 0,
        away_starters: Array.isArray(lineup.awayTeam?.starters) ? lineup.awayTeam.starters.length : 0,
        shots_count: shotmapShots,
        momentum_points: Array.isArray(momentum) ? momentum.length : 0,
    };
}

function buildStitchSummary(rawData, oddsRows, missingFields) {
    const fixtureSummary = summarizeFixture(rawData);
    const conflicts = [];

    if (!rawData?.content) {
        conflicts.push('missing_content');
    }
    if (!fixtureSummary.lineup_available) {
        conflicts.push('missing_lineup');
    }
    if (!rawData?.content?.shotmap || !Array.isArray(rawData.content.shotmap.shots)) {
        conflicts.push('missing_shotmap');
    }
    if (oddsRows.length === 0) {
        conflicts.push('no_odds_data');
    }

    return {
        ...fixtureSummary,
        odds_history_rows: oddsRows.length,
        missing_fields: missingFields,
        conflicts,
        would_write_l3_features: false,
        would_update_matches: false,
        would_trigger_elo: false,
        would_create_index: false,
        would_create_table: false,
    };
}

function selectFeatureHighlights(goldenFeatures, tacticalFeatures, oddsMovementFeatures) {
    return {
        golden: {
            home_market_value_total: goldenFeatures.home_market_value_total,
            away_market_value_total: goldenFeatures.away_market_value_total,
            home_rating_avg: goldenFeatures.home_rating_avg,
            away_rating_avg: goldenFeatures.away_rating_avg,
            home_starters_count: goldenFeatures.home_starters_count,
            away_starters_count: goldenFeatures.away_starters_count,
        },
        tactical: {
            home_xg: tacticalFeatures.home_xg,
            away_xg: tacticalFeatures.away_xg,
            home_possession_pct: tacticalFeatures.home_possession_pct,
            away_possession_pct: tacticalFeatures.away_possession_pct,
            home_shots: tacticalFeatures.home_shots,
            away_shots: tacticalFeatures.away_shots,
            momentum_samples_count: tacticalFeatures.momentum_samples_count,
        },
        odds: {
            has_odds_data: oddsMovementFeatures.has_odds_data,
            odds_source: oddsMovementFeatures.odds_source,
            initial_home_odds: oddsMovementFeatures.initial_home_odds,
            current_home_odds: oddsMovementFeatures.current_home_odds,
            total_movement: oddsMovementFeatures.total_movement,
        },
    };
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

async function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
        console.log(usage());
        return;
    }
    if (!args.fixture || !args.matchId) {
        console.error(usage());
        process.exitCode = 1;
        return;
    }

    const { resolved, data: fixture } = readJsonFile(args.fixture);
    const missingFields = validateFixture(fixture, args.matchId);
    const rawData = fixture.raw_data;

    const pool = new Pool(buildDbConfig());
    try {
        const matchSql = `
            SELECT match_id, external_id, league_name, season, home_team, away_team,
                   match_date, status, pipeline_status
            FROM matches
            WHERE match_id = $1
        `;
        const oddsSql = `
            SELECT match_id, bookmaker_name, market_type, open_odds, close_odds, collected_at
            FROM bookmaker_odds_history
            WHERE match_id = $1
            ORDER BY bookmaker_name, market_type
        `;

        const matchResult = await safeSelect(pool, matchSql, [args.matchId]);
        if (matchResult.rowCount !== 1) {
            throw new Error(`Target match not found: ${args.matchId}`);
        }

        const oddsResult = await safeSelect(pool, oddsSql, [args.matchId]);
        const oddsRows = oddsResult.rows;

        const matchRow = matchResult.rows[0];
        const goldenExtracted = extractGoldenFeatures(rawData);
        const tacticalExtracted = extractTacticalFeatures(rawData);
        const oddsData = buildOddsDataFromHistoryRows(oddsRows);
        const oddsMovementFeatures = oddsData.hasData
            ? extractOddsMovementFeaturesFromOddsData(oddsData, tacticalExtracted)
            : extractOddsMovementFeatures(rawData, tacticalExtracted);
        const fixtureSummary = summarizeFixture(rawData);
        const stitchSummary = buildStitchSummary(rawData, oddsRows, missingFields);

        const preview = {
            mode: 'dry-run',
            match_id: args.matchId,
            fixture: {
                path: args.fixture,
                resolved_path: resolved,
                external_id: fixture.external_id || rawData.general?.matchId || null,
            },
            db: {
                match_found: true,
                odds_history_rows: oddsRows.length,
                match: {
                    match_id: matchRow.match_id,
                    external_id: matchRow.external_id,
                    league_name: matchRow.league_name,
                    season: matchRow.season,
                    home_team: matchRow.home_team,
                    away_team: matchRow.away_team,
                    match_date: matchRow.match_date ? new Date(matchRow.match_date).toISOString() : null,
                    status: matchRow.status,
                    pipeline_status: matchRow.pipeline_status,
                },
            },
            golden_features: {
                league_name: matchRow.league_name,
                season: matchRow.season,
                home_team: matchRow.home_team,
                away_team: matchRow.away_team,
                match_date: matchRow.match_date ? new Date(matchRow.match_date).toISOString() : null,
                extracted: goldenExtracted,
            },
            tactical_features: {
                shots_count: fixtureSummary.shots_count,
                momentum_points: fixtureSummary.momentum_points,
                lineup_available: fixtureSummary.lineup_available,
                extracted: tacticalExtracted,
            },
            odds_features: {
                rows: oddsRows.length,
                one_x_two_rows: oddsRows.filter(row => String(row.market_type || '').toLowerCase() === '1x2').length,
                bookmakers: uniqueSorted(oddsRows.map(row => row.bookmaker_name)),
                markets: uniqueSorted(oddsRows.map(row => row.market_type)),
                source: oddsData.hasData ? 'bookmaker_odds_history' : 'raw_fixture_or_none',
                extracted: oddsMovementFeatures,
            },
            elo_features: {
                available: false,
                reason: 'ELO not computed in local dry-run',
            },
            feature_highlights: selectFeatureHighlights(goldenExtracted, tacticalExtracted, oddsMovementFeatures),
            stitch_summary: stitchSummary,
            missing_fields: missingFields,
            warnings: oddsRows.length === 0 ? ['target_odds_history_missing'] : [],
            non_execution_confirmations: [
                'no_db_writes',
                'no_insert',
                'no_update',
                'no_delete',
                'no_create_index',
                'no_create_table',
                'no_upsert',
                'no_l3_write',
                'no_elo',
                'no_external_network',
            ],
        };

        console.log(JSON.stringify(preview, null, 2));
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
                non_execution_confirmations: ['no_db_writes', 'no_create_index', 'no_elo', 'no_external_network'],
            },
            null,
            2
        )
    );
    process.exit(1);
});
