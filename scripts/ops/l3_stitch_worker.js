#!/usr/bin/env node
'use strict';

require('dotenv').config();

const { Pool } = require('pg');
const { extractGoldenFeatures } = require('../../src/feature_engine/extractors/GoldenFeatureExtractor');
const { extractTacticalFeatures } = require('../../src/feature_engine/extractors/TacticalMomentumExtractor');
const { extractOddsMovementFeatures } = require('../../src/feature_engine/extractors/OddsMovementExtractor');

const WORKER_INDEX = Number.parseInt(process.env.L3_STITCH_WORKER_INDEX || '0', 10);
const SHARD_COUNT = Number.parseInt(process.env.L3_STITCH_SHARD_COUNT || '1', 10);
const PROGRESS_EVERY = Number.parseInt(process.env.L3_STITCH_PROGRESS_EVERY || '25', 10);
const TARGET_SEASON = process.env.L3_STITCH_SEASON || '2024/2025';
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
        conflicts
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
        sendMessage({ type: 'worker_start', workerIndex: WORKER_INDEX, assigned: rows.length });

        for (const row of rows) {
            try {
                const goldenFeatures = extractGoldenFeatures(row.raw_data);
                const tacticalFeatures = extractTacticalFeatures(row.raw_data);
                const oddsFeatures = extractOddsMovementFeatures(row.raw_data);
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
