#!/usr/bin/env node
'use strict';

require('dotenv').config();

const { Pool } = require('pg');
const { extractGoldenFeatures } = require('../../src/feature_engine/extractors/GoldenFeatureExtractor');
const { extractTacticalFeatures } = require('../../src/feature_engine/extractors/TacticalMomentumExtractor');
const {
    extractOddsMovementFeatures,
    extractOddsMovementFeaturesFromOddsData
} = require('../../src/feature_engine/extractors/OddsMovementExtractor');
const { resolveSeasonContext } = require('./helpers/seasonRuntimeConfig');

const WORKER_INDEX = Number.parseInt(process.env.L3_STITCH_WORKER_INDEX || '0', 10);
const SHARD_COUNT = Number.parseInt(process.env.L3_STITCH_SHARD_COUNT || '1', 10);
const PROGRESS_EVERY = Number.parseInt(process.env.L3_STITCH_PROGRESS_EVERY || '25', 10);
const { season: TARGET_SEASON } = resolveSeasonContext({
    seasonEnvVar: 'L3_STITCH_SEASON',
    seasonTagEnvVar: 'L3_STITCH_SEASON_TAG'
});
const FULL_RECALCULATE = String(process.env.L3_STITCH_FULL_RECALCULATE || '').toLowerCase() === 'true';

const pool = new Pool({
    host: process.env.DB_HOST || '127.0.0.1',
    port: Number.parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || '',
    max: 4
});

const UPSERT_SQL = `
    INSERT INTO l3_features (
        match_id,
        external_id,
        golden_features,
        tactical_features,
        odds_movement_features,
        odds_features,
        elo_features,
        rolling_features,
        efficiency_features,
        draw_features,
        market_sentiment,
        stitch_summary,
        computed_at,
        updated_at
    ) VALUES (
        $1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb, '{}'::jsonb, '{}'::jsonb,
        '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, $7::jsonb, NOW(), NOW()
    )
    ON CONFLICT (match_id) DO UPDATE SET
        external_id = EXCLUDED.external_id,
        golden_features = EXCLUDED.golden_features,
        tactical_features = EXCLUDED.tactical_features,
        odds_movement_features = EXCLUDED.odds_movement_features,
        odds_features = EXCLUDED.odds_features,
        stitch_summary = EXCLUDED.stitch_summary,
        computed_at = EXCLUDED.computed_at,
        updated_at = NOW()
`;

const FETCH_CANONICAL_ODDS_SQL = `
    SELECT
        id,
        match_id,
        bookmaker,
        home_odds,
        draw_odds,
        away_odds,
        collected_at
    FROM odds
    WHERE match_id = ANY($1::varchar[])
      AND home_odds IS NOT NULL
      AND draw_odds IS NOT NULL
      AND away_odds IS NOT NULL
    ORDER BY match_id ASC, collected_at ASC NULLS LAST, id ASC
`;

const FETCH_BOOKMAKER_HISTORY_SQL = `
    SELECT
        id,
        match_id,
        bookmaker_name,
        open_odds,
        close_odds,
        collected_at
    FROM bookmaker_odds_history
    WHERE match_id = ANY($1::varchar[])
      AND lower(market_type) = '1x2'
    ORDER BY match_id ASC, collected_at ASC NULLS LAST, id ASC
`;

function sendMessage(message) {
    if (typeof process.send === 'function') {
        process.send(message);
    } else {
        console.log(JSON.stringify(message));
    }
}

function countShotmapShots(rawData) {
    const shots = rawData?.content?.shotmap?.shots;
    return Array.isArray(shots) ? shots.length : 0;
}

function countRatingSamples(goldenFeatures) {
    return Number(goldenFeatures?.home_rating_available_count || 0)
        + Number(goldenFeatures?.away_rating_available_count || 0);
}

function buildConflictSummary(rawData, tacticalFeatures, goldenFeatures, oddsFeatures) {
    const conflicts = [];
    const hasContent = !!rawData?.content && typeof rawData.content === 'object';
    const hasLineup = !!rawData?.content?.lineup && typeof rawData.content.lineup === 'object';
    const hasShotmap = !!rawData?.content?.shotmap && typeof rawData.content.shotmap === 'object';
    const shotmapShots = countShotmapShots(rawData);
    const ratingSamples = countRatingSamples(goldenFeatures);
    const hasXgSignal = Number.isFinite(Number(tacticalFeatures?.home_xg))
        && Number.isFinite(Number(tacticalFeatures?.away_xg));

    if (!hasContent) {
        conflicts.push('missing_content');
    }
    if (!hasLineup) {
        conflicts.push('missing_lineup');
    }
    if (!hasShotmap) {
        conflicts.push('missing_shotmap');
    }
    if (!hasXgSignal) {
        conflicts.push('invalid_xg');
    }

    return {
        has_content: hasContent,
        has_lineup: hasLineup,
        has_shotmap: hasShotmap,
        shotmap_shots: shotmapShots,
        rating_samples: ratingSamples,
        has_odds_data: !!oddsFeatures?.has_odds_data,
        odds_source: oddsFeatures?._odds_source || 'none',
        conflicts
    };
}

function groupRowsByKey(rows, keyField) {
    const grouped = new Map();

    for (const row of rows) {
        const key = row?.[keyField];
        if (!key) {
            continue;
        }

        if (!grouped.has(key)) {
            grouped.set(key, []);
        }
        grouped.get(key).push(row);
    }

    return grouped;
}

function toPositiveNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function median(values) {
    if (values.length === 0) {
        return null;
    }

    const sorted = [...values].sort((left, right) => left - right);
    const middle = Math.floor(sorted.length / 2);

    if (sorted.length % 2 === 1) {
        return sorted[middle];
    }

    return (sorted[middle - 1] + sorted[middle]) / 2;
}

function aggregateOddsTriplet(points, collectedAt = null) {
    const homeValues = points.map((point) => point.home).filter(Boolean);
    const drawValues = points.map((point) => point.draw).filter(Boolean);
    const awayValues = points.map((point) => point.away).filter(Boolean);

    if (homeValues.length === 0 || drawValues.length === 0 || awayValues.length === 0) {
        return null;
    }

    return {
        home: median(homeValues),
        draw: median(drawValues),
        away: median(awayValues),
        collectedAt
    };
}

function normalizeCanonicalOddsRow(row) {
    return {
        home: toPositiveNumber(row.home_odds),
        draw: toPositiveNumber(row.draw_odds),
        away: toPositiveNumber(row.away_odds),
        collectedAt: row.collected_at ? new Date(row.collected_at).toISOString() : null
    };
}

function normalizeHistoryOddsPayload(payload, collectedAt) {
    return {
        home: toPositiveNumber(payload?.home),
        draw: toPositiveNumber(payload?.draw),
        away: toPositiveNumber(payload?.away),
        collectedAt: collectedAt ? new Date(collectedAt).toISOString() : null
    };
}

function buildOddsDataFromCanonicalRows(rows) {
    if (!rows || rows.length === 0) {
        return null;
    }

    const groupedByTimestamp = new Map();

    for (const row of rows) {
        const normalized = normalizeCanonicalOddsRow(row);
        if (!normalized.home || !normalized.draw || !normalized.away) {
            continue;
        }

        const timestampKey = normalized.collectedAt || `snapshot-${row.id}`;
        if (!groupedByTimestamp.has(timestampKey)) {
            groupedByTimestamp.set(timestampKey, []);
        }
        groupedByTimestamp.get(timestampKey).push(normalized);
    }

    const history = Array.from(groupedByTimestamp.entries())
        .map(([timestampKey, points]) => aggregateOddsTriplet(points, timestampKey.startsWith('snapshot-') ? null : timestampKey))
        .filter(Boolean);

    if (history.length === 0) {
        return null;
    }

    return {
        initial: history[0],
        current: history[history.length - 1],
        history,
        hasData: true,
        odds_source: 'odds',
        _odds_source: 'odds',
        _odds_source_rows: rows.length,
        _odds_source_points: history.length
    };
}

function buildOddsDataFromHistoricalRows(rows) {
    if (!rows || rows.length === 0) {
        return null;
    }

    const openingPoints = rows
        .map((row) => normalizeHistoryOddsPayload(row.open_odds, row.collected_at))
        .filter((point) => point.home && point.draw && point.away);

    const closingPoints = rows
        .map((row) => normalizeHistoryOddsPayload(row.close_odds, row.collected_at))
        .filter((point) => point.home && point.draw && point.away);

    const initial = aggregateOddsTriplet(openingPoints, openingPoints[0]?.collectedAt || null);
    const current = aggregateOddsTriplet(closingPoints, closingPoints[closingPoints.length - 1]?.collectedAt || null);

    if (!initial && !current) {
        return null;
    }

    const history = [];
    if (initial) {
        history.push(initial);
    }
    if (
        current
        && (
            !initial
            || initial.home !== current.home
            || initial.draw !== current.draw
            || initial.away !== current.away
        )
    ) {
        history.push(current);
    }

    return {
        initial: initial || current,
        current: current || initial,
        history,
        hasData: true,
        odds_source: 'bookmaker_odds_history',
        _odds_source: 'bookmaker_odds_history',
        _odds_source_rows: rows.length,
        _odds_source_points: history.length
    };
}

async function prefetchOddsSources(client, rows) {
    const matchIds = rows.map((row) => row.match_id).filter(Boolean);

    const canonicalRows = matchIds.length > 0
        ? (await client.query(FETCH_CANONICAL_ODDS_SQL, [matchIds])).rows
        : [];

    const historicalRows = matchIds.length > 0
        ? (await client.query(FETCH_BOOKMAKER_HISTORY_SQL, [matchIds])).rows
        : [];

    return {
        canonicalByMatchId: groupRowsByKey(canonicalRows, 'match_id'),
        historicalByMatchId: groupRowsByKey(historicalRows, 'match_id')
    };
}

function extractBestAvailableOddsFeatures(row, tacticalFeatures, oddsSources) {
    const canonicalData = buildOddsDataFromCanonicalRows(
        oddsSources.canonicalByMatchId.get(row.match_id) || []
    );

    if (canonicalData) {
        return {
            ...extractOddsMovementFeaturesFromOddsData(canonicalData, tacticalFeatures),
            odds_source: canonicalData.odds_source,
            _odds_source: canonicalData._odds_source,
            _odds_source_rows: canonicalData._odds_source_rows,
            _odds_source_points: canonicalData._odds_source_points
        };
    }

    const historicalData = buildOddsDataFromHistoricalRows(
        oddsSources.historicalByMatchId.get(row.match_id) || []
    );

    if (historicalData) {
        return {
            ...extractOddsMovementFeaturesFromOddsData(historicalData, tacticalFeatures),
            odds_source: historicalData.odds_source,
            _odds_source: historicalData._odds_source,
            _odds_source_rows: historicalData._odds_source_rows,
            _odds_source_points: historicalData._odds_source_points
        };
    }

    const rawFeatures = extractOddsMovementFeatures(row.raw_data, tacticalFeatures);
    return {
        ...rawFeatures,
        odds_source: rawFeatures.has_odds_data ? 'raw_data' : 'none',
        _odds_source: rawFeatures.has_odds_data ? 'raw_data' : 'none',
        _odds_source_rows: 0,
        _odds_source_points: Number(rawFeatures.odds_history_count || 0)
    };
}

async function fetchMatches(client) {
    const query = `
        SELECT
            m.match_id,
            m.external_id,
            m.home_team,
            m.away_team,
            m.match_date,
            r.raw_data
        FROM matches m
        INNER JOIN raw_match_data r ON r.match_id = m.match_id
        LEFT JOIN l3_features l3 ON l3.match_id = m.match_id
        WHERE m.season = $1
          AND mod(abs(hashtext(m.match_id)), $2) = $3
          AND ($4::boolean OR l3.match_id IS NULL)
        ORDER BY m.match_date ASC, m.match_id ASC
    `;

    const result = await client.query(query, [
        TARGET_SEASON,
        SHARD_COUNT,
        WORKER_INDEX,
        FULL_RECALCULATE
    ]);
    return result.rows;
}

async function run() {
    const client = await pool.connect();
    const stats = {
        workerIndex: WORKER_INDEX,
        processed: 0,
        success: 0,
        failed: 0,
        parserConflicts: 0,
        emptyShotmap: 0,
        zeroRatings: 0,
        noOddsData: 0
    };

    try {
        const rows = await fetchMatches(client);
        const oddsSources = await prefetchOddsSources(client, rows);
        sendMessage({ type: 'worker_start', workerIndex: WORKER_INDEX, assigned: rows.length });

        for (const row of rows) {
            try {
                const goldenFeatures = extractGoldenFeatures(row.raw_data);
                const tacticalFeatures = extractTacticalFeatures(row.raw_data);
                const oddsFeatures = extractBestAvailableOddsFeatures(row, tacticalFeatures, oddsSources);
                const summary = buildConflictSummary(row.raw_data, tacticalFeatures, goldenFeatures, oddsFeatures);

                if (summary.conflicts.length > 0) {
                    stats.parserConflicts += 1;
                }
                if (summary.shotmap_shots === 0) {
                    stats.emptyShotmap += 1;
                }
                if (summary.rating_samples === 0) {
                    stats.zeroRatings += 1;
                }
                if (!summary.has_odds_data) {
                    stats.noOddsData += 1;
                }

                await client.query(UPSERT_SQL, [
                    row.match_id,
                    row.external_id || row.match_id,
                    JSON.stringify(goldenFeatures),
                    JSON.stringify(tacticalFeatures),
                    JSON.stringify(oddsFeatures),
                    JSON.stringify(oddsFeatures),
                    JSON.stringify(summary)
                ]);

                stats.success += 1;
            } catch (error) {
                stats.failed += 1;
                sendMessage({
                    type: 'worker_error',
                    workerIndex: WORKER_INDEX,
                    matchId: row.match_id,
                    error: error.message
                });
            } finally {
                stats.processed += 1;
                if (stats.processed % PROGRESS_EVERY === 0 || stats.processed === rows.length) {
                    sendMessage({ type: 'worker_progress', stats: { ...stats } });
                }
            }
        }

        sendMessage({ type: 'worker_done', stats: { ...stats } });
    } finally {
        client.release();
        await pool.end();
    }
}

run().catch((error) => {
    sendMessage({
        type: 'worker_crash',
        workerIndex: WORKER_INDEX,
        error: error.message
    });
    process.exit(1);
});
