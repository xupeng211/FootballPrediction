#!/usr/bin/env node
'use strict';

require('dotenv').config();

const os = require('os');
const path = require('path');
const { fork, spawn } = require('child_process');
const { Pool } = require('pg');

const TARGET_SEASON = process.env.L3_STITCH_SEASON || '2024/2025';
const TARGET_WORKERS = Number.parseInt(
    process.env.L3_STITCH_WORKERS
        || String(Math.min(12, os.availableParallelism ? os.availableParallelism() : os.cpus().length)),
    10
);
const PROGRESS_EVERY = Number.parseInt(process.env.L3_STITCH_PROGRESS_EVERY || '25', 10);
const FULL_RECALCULATE = String(process.env.L3_STITCH_FULL_RECALCULATE || '').toLowerCase() === 'true';

const pool = new Pool({
    host: process.env.DB_HOST || '127.0.0.1',
    port: Number.parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || '',
    max: 8
});

const WORKER_SCRIPT = path.resolve(__dirname, 'l3_stitch_worker.js');
const ELO_SCRIPT = path.resolve(__dirname, '../maintenance/recalculate_elo.js');

const CREATE_L3_SQL = `
    CREATE TABLE IF NOT EXISTS l3_features (
        match_id VARCHAR(50) PRIMARY KEY REFERENCES matches(match_id) ON DELETE CASCADE,
        external_id VARCHAR(50),
        golden_features JSONB NOT NULL DEFAULT '{}'::jsonb,
        tactical_features JSONB NOT NULL DEFAULT '{}'::jsonb,
        odds_movement_features JSONB NOT NULL DEFAULT '{}'::jsonb,
        odds_features JSONB NOT NULL DEFAULT '{}'::jsonb,
        elo_features JSONB NOT NULL DEFAULT '{}'::jsonb,
        rolling_features JSONB NOT NULL DEFAULT '{}'::jsonb,
        efficiency_features JSONB NOT NULL DEFAULT '{}'::jsonb,
        draw_features JSONB NOT NULL DEFAULT '{}'::jsonb,
        market_sentiment JSONB NOT NULL DEFAULT '{}'::jsonb,
        stitch_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
        computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_l3_features_external_id ON l3_features(external_id);
    CREATE INDEX IF NOT EXISTS idx_l3_features_computed_at ON l3_features(computed_at DESC);
    CREATE INDEX IF NOT EXISTS idx_l3_features_tactical_gin ON l3_features USING GIN(tactical_features);
`;

async function ensureL3Schema(client) {
    await client.query(CREATE_L3_SQL);
}

async function backfillFinishedScores(client) {
    const query = `
        UPDATE matches m
        SET
            home_score = COALESCE(
                m.home_score,
                NULLIF(r.raw_data->'header'->'teams'->0->>'score', '')::integer
            ),
            away_score = COALESCE(
                m.away_score,
                NULLIF(r.raw_data->'header'->'teams'->1->>'score', '')::integer
            ),
            updated_at = NOW()
        FROM raw_match_data r
        WHERE r.match_id = m.match_id
          AND m.season = $1
          AND (m.home_score IS NULL OR m.away_score IS NULL)
          AND r.raw_data->'header'->'teams'->0->>'score' IS NOT NULL
          AND r.raw_data->'header'->'teams'->1->>'score' IS NOT NULL
    `;

    const result = await client.query(query, [TARGET_SEASON]);
    return result.rowCount;
}

async function getSeedState(client) {
    const query = `
        SELECT
            COUNT(*) AS total_matches,
            COUNT(r.match_id) AS total_raw,
            COUNT(*) FILTER (
                WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
            ) AS score_seed_ready,
            COUNT(*) FILTER (
                WHERE r.raw_data ? 'content'
            ) AS content_ready,
            to_regclass('public.team_elo_ratings') IS NOT NULL AS has_team_elo_ratings
        FROM matches m
        LEFT JOIN raw_match_data r ON r.match_id = m.match_id
        WHERE m.season = $1
    `;

    const result = await client.query(query, [TARGET_SEASON]);
    return result.rows[0];
}

async function getFinalReport(client) {
    const query = `
        SELECT
            COUNT(*) AS structured_rows,
            COUNT(*) FILTER (
                WHERE COALESCE((l.stitch_summary->>'shotmap_shots')::integer, 0) > 0
            ) AS shotmap_nonempty_rows,
            COUNT(*) FILTER (
                WHERE COALESCE((l.stitch_summary->>'rating_samples')::integer, 0) > 0
            ) AS rating_rows,
            COUNT(*) FILTER (
                WHERE jsonb_array_length(COALESCE(l.stitch_summary->'conflicts', '[]'::jsonb)) > 0
            ) AS parser_conflict_rows,
            COUNT(*) FILTER (
                WHERE COALESCE((l.elo_features->>'home_elo')::numeric, 0) > 0
            ) AS elo_seeded_rows
        FROM matches m
        JOIN l3_features l ON l.match_id = m.match_id
        WHERE m.season = $1
    `;

    const result = await client.query(query, [TARGET_SEASON]);
    return result.rows[0];
}

function printSeedState(seedState) {
    console.log('Seed state:');
    console.log(`  matches=${seedState.total_matches}`);
    console.log(`  raw_match_data=${seedState.total_raw}`);
    console.log(`  score_seed_ready=${seedState.score_seed_ready}`);
    console.log(`  content_ready=${seedState.content_ready}`);
    console.log(`  team_elo_ratings=${seedState.has_team_elo_ratings}`);
}

function aggregateSnapshots(snapshots) {
    const total = {
        processed: 0,
        success: 0,
        failed: 0,
        parserConflicts: 0,
        emptyShotmap: 0,
        zeroRatings: 0,
        noOddsData: 0
    };

    for (const stats of snapshots.values()) {
        total.processed += stats.processed || 0;
        total.success += stats.success || 0;
        total.failed += stats.failed || 0;
        total.parserConflicts += stats.parserConflicts || 0;
        total.emptyShotmap += stats.emptyShotmap || 0;
        total.zeroRatings += stats.zeroRatings || 0;
        total.noOddsData += stats.noOddsData || 0;
    }

    return total;
}

function runWorkerPool(totalMatches) {
    return new Promise((resolve, reject) => {
        const workerSnapshots = new Map();
        let finishedWorkers = 0;
        let failed = false;
        const startedAt = Date.now();

        for (let index = 0; index < TARGET_WORKERS; index += 1) {
            const child = fork(WORKER_SCRIPT, [], {
                cwd: process.cwd(),
                env: {
                    ...process.env,
                    L3_STITCH_SEASON: TARGET_SEASON,
                    L3_STITCH_WORKER_INDEX: String(index),
                    L3_STITCH_SHARD_COUNT: String(TARGET_WORKERS),
                    L3_STITCH_PROGRESS_EVERY: String(PROGRESS_EVERY),
                    L3_STITCH_FULL_RECALCULATE: String(FULL_RECALCULATE)
                },
                stdio: ['inherit', 'inherit', 'inherit', 'ipc']
            });

            workerSnapshots.set(index, {
                processed: 0,
                success: 0,
                failed: 0,
                parserConflicts: 0,
                emptyShotmap: 0,
                zeroRatings: 0,
                noOddsData: 0
            });

            child.on('message', (message) => {
                if (message.type === 'worker_progress' || message.type === 'worker_done') {
                    workerSnapshots.set(message.stats.workerIndex, message.stats);
                    const totals = aggregateSnapshots(workerSnapshots);
                    const elapsedSec = Math.max(1, (Date.now() - startedAt) / 1000);
                    const throughput = (totals.success / elapsedSec).toFixed(2);

                    console.log(
                        `[L3] progress ${totals.processed}/${totalMatches} | success=${totals.success} `
                        + `failed=${totals.failed} conflicts=${totals.parserConflicts} `
                        + `shotmap_empty=${totals.emptyShotmap} ratings_zero=${totals.zeroRatings} `
                        + `odds_missing=${totals.noOddsData} | ${throughput} rows/s`
                    );
                }

                if (message.type === 'worker_error') {
                    console.error(`[L3] worker ${message.workerIndex} failed on ${message.matchId}: ${message.error}`);
                }

                if (message.type === 'worker_crash' && !failed) {
                    failed = true;
                    reject(new Error(`worker ${message.workerIndex} crashed: ${message.error}`));
                }
            });

            child.on('exit', (code) => {
                finishedWorkers += 1;
                if (code !== 0 && !failed) {
                    failed = true;
                    reject(new Error(`worker ${index} exited with code ${code}`));
                    return;
                }

                if (finishedWorkers === TARGET_WORKERS && !failed) {
                    resolve(aggregateSnapshots(workerSnapshots));
                }
            });
        }
    });
}

function runEloRecalculation() {
    return new Promise((resolve, reject) => {
        const child = spawn(process.execPath, [ELO_SCRIPT, '--incremental'], {
            cwd: process.cwd(),
            env: process.env,
            stdio: 'inherit'
        });

        child.on('exit', (code) => {
            if (code === 0) {
                resolve();
                return;
            }
            reject(new Error(`recalculate_elo exited with code ${code}`));
        });
    });
}

async function main() {
    const client = await pool.connect();

    try {
        console.log(`L3 Golden Stitching season=${TARGET_SEASON} workers=${TARGET_WORKERS}`);
        await ensureL3Schema(client);

        const scoresBackfilled = await backfillFinishedScores(client);
        console.log(`Backfilled finished scores from raw header: ${scoresBackfilled}`);

        const seedState = await getSeedState(client);
        printSeedState(seedState);

        const totalMatches = Number.parseInt(seedState.total_matches, 10);
        const stitchStats = await runWorkerPool(totalMatches);

        console.log('Running incremental Elo recalculation...');
        await runEloRecalculation();

        const finalReport = await getFinalReport(client);
        const structuredRows = Number.parseInt(finalReport.structured_rows, 10);

        console.log('Final report:');
        console.log(JSON.stringify({
            season: TARGET_SEASON,
            workers: TARGET_WORKERS,
            scoresBackfilled,
            stitchStats,
            finalReport: {
                ...finalReport,
                missing_rows: Math.max(0, totalMatches - structuredRows)
            }
        }, null, 2));
    } finally {
        client.release();
        await pool.end();
    }
}

main().catch((error) => {
    console.error(`L3 stitching failed: ${error.message}`);
    process.exit(1);
});
