'use strict';

// lifecycle: permanent
// scope: authorized score/result backfill write executor for Ligue 1 2025/2026
// requires explicit --allow-write --json; single transaction, strict WHERE, rollback on failure

const {
    PHASE,
    CONTRACT_CARRIER,
    TARGET_LEAGUE,
    TARGET_SEASON,
    buildDbConfig,
    scanMatchesForDryRun,
    classifyScannedMatch,
    runDryRun,
} = require('./score_backfill_dry_run');

const EXPECTED_PREFLIGHT = Object.freeze({
    total_matches_scanned: 60,
    target_ligue1_count: 58,
    would_update_count: 58,
    would_skip_count: 2,
    mismatch_count: 0,
    excluded_match_ids: ['47_20242025_900002', '140_20252026_4837496'],
    result_distribution: Object.freeze({ home_win: 23, draw: 17, away_win: 18 }),
});

const WRITE_UPDATE_SQL_PREFIX = `
UPDATE matches m SET
  home_score = v.home_score,
  away_score = v.away_score,
  actual_result = v.actual_result
FROM (VALUES
`;

const WRITE_UPDATE_SQL_SUFFIX = `
) AS v(home_score, away_score, actual_result, match_id)
WHERE m.match_id = v.match_id
  AND m.home_score IS NULL
  AND m.away_score IS NULL
  AND m.actual_result IS NULL
RETURNING m.match_id
`;

const VERIFY_UPDATED_COUNT_SQL = `
SELECT COUNT(*)::integer AS count
FROM matches
WHERE league_name = $1
  AND season = $2
  AND home_score IS NOT NULL
  AND away_score IS NOT NULL
  AND actual_result IS NOT NULL
`;

const VERIFY_TOTAL_MATCHES_SQL = 'SELECT COUNT(*)::integer AS count FROM matches';
const VERIFY_TOTAL_RAW_SQL = 'SELECT COUNT(*)::integer AS count FROM raw_match_data';

const VERIFY_PIPELINE_SQL = `
SELECT pipeline_status, COUNT(*)::integer AS count
FROM matches
GROUP BY pipeline_status
ORDER BY pipeline_status
`;

const VERIFY_TRAINING_SQL = `
SELECT is_training_eligible, COUNT(*)::integer AS count
FROM matches
GROUP BY is_training_eligible
ORDER BY is_training_eligible
`;

const VERIFY_RESULT_DISTRIBUTION_SQL = `
SELECT actual_result, COUNT(*)::integer AS count
FROM matches
WHERE league_name = $1
  AND season = $2
  AND actual_result IS NOT NULL
GROUP BY actual_result
ORDER BY actual_result
`;

const VERIFY_EXCLUDED_STILL_NULL_SQL = `
SELECT match_id, home_score, away_score, actual_result
FROM matches
WHERE match_id = ANY($1::text[])
`;

function distributionsEqual(a, b) {
    const keys = new Set([...Object.keys(a || {}), ...Object.keys(b || {})]);
    for (const key of keys) {
        if ((a[key] || 0) !== (b[key] || 0)) {
            return false;
        }
    }
    return true;
}

function buildWriteUpdateSql(updates) {
    const valueRows = updates.map((_, i) => {
        const base = i * 4;
        return `($${base + 1}::integer, $${base + 2}::integer, $${base + 3}, $${base + 4}::text)`;
    }).join(',\n  ');

    return `${WRITE_UPDATE_SQL_PREFIX}
  ${valueRows}
${WRITE_UPDATE_SQL_SUFFIX}`;
}

function flattenUpdateParams(updates) {
    const params = [];
    for (const u of updates) {
        params.push(u.proposed_home_score, u.proposed_away_score, u.proposed_actual_result, u.match_id);
    }
    return params;
}

function validatePreflight(payload) {
    const failures = [];

    if (payload.total_matches_scanned !== EXPECTED_PREFLIGHT.total_matches_scanned) {
        failures.push(`total_matches_scanned=${payload.total_matches_scanned} expected=${EXPECTED_PREFLIGHT.total_matches_scanned}`);
    }
    if (payload.target_ligue1_count !== EXPECTED_PREFLIGHT.target_ligue1_count) {
        failures.push(`target_ligue1_count=${payload.target_ligue1_count} expected=${EXPECTED_PREFLIGHT.target_ligue1_count}`);
    }
    if (payload.would_update_count !== EXPECTED_PREFLIGHT.would_update_count) {
        failures.push(`would_update_count=${payload.would_update_count} expected=${EXPECTED_PREFLIGHT.would_update_count}`);
    }
    if (payload.would_skip_count !== EXPECTED_PREFLIGHT.would_skip_count) {
        failures.push(`would_skip_count=${payload.would_skip_count} expected=${EXPECTED_PREFLIGHT.would_skip_count}`);
    }
    if (payload.score_consistency_summary.score_str_mismatch_count !== EXPECTED_PREFLIGHT.mismatch_count) {
        failures.push(`mismatch_count=${payload.score_consistency_summary.score_str_mismatch_count} expected=${EXPECTED_PREFLIGHT.mismatch_count}`);
    }

    const excludedActual = [...(payload.excluded_no_raw_match_ids || [])].sort().join(',');
    const excludedExpected = [...EXPECTED_PREFLIGHT.excluded_match_ids].sort().join(',');
    if (excludedActual !== excludedExpected) {
        failures.push(`excluded_match_ids=[${excludedActual}] expected=[${excludedExpected}]`);
    }

    if (!distributionsEqual(payload.actual_result_distribution, EXPECTED_PREFLIGHT.result_distribution)) {
        failures.push(
            `result_distribution=${JSON.stringify(payload.actual_result_distribution || {})} expected=${JSON.stringify(EXPECTED_PREFLIGHT.result_distribution)}`
        );
    }

    return { passed: failures.length === 0, failures };
}

async function openWriteClient(dependencies = {}) {
    if (dependencies.client) {
        return { client: dependencies.client, close: async () => {}, ownsPool: false };
    }

    if (dependencies.pool) {
        const client = await dependencies.pool.connect();
        return {
            client,
            close: async () => { if (typeof client.release === 'function') { client.release(); } },
            ownsPool: false,
        };
    }

    const { Pool } = require('pg');
    const pool = new Pool(buildDbConfig());
    const client = await pool.connect();
    return {
        client,
        close: async () => {
            if (typeof client.release === 'function') { client.release(); }
            await pool.end();
        },
        ownsPool: true,
    };
}

async function executeWriteTransaction(client, updates) {
    const sql = buildWriteUpdateSql(updates);
    const params = flattenUpdateParams(updates);

    await client.query('BEGIN');
    try {
        const result = await client.query(sql, params);
        const updatedCount = (result.rows || []).length;

        if (updatedCount !== updates.length) {
            const updatedIds = new Set((result.rows || []).map(r => r.match_id));
            const missing = updates.filter(u => !updatedIds.has(u.match_id)).map(u => u.match_id);
            throw new Error(
                `Write count mismatch: updated ${updatedCount} rows, expected ${updates.length}. ` +
                `Missing match_ids: ${missing.join(', ') || 'none'}`
            );
        }

        return { updatedCount };
    } catch (error) {
        await client.query('ROLLBACK');
        throw error;
    }
}

async function runPostWriteVerification(client) {
    const v = {};

    const updatedResult = await client.query(VERIFY_UPDATED_COUNT_SQL, [TARGET_LEAGUE, TARGET_SEASON]);
    v.updatedCount = updatedResult.rows[0].count;

    const totalResult = await client.query(VERIFY_TOTAL_MATCHES_SQL);
    v.totalMatches = totalResult.rows[0].count;

    const rawResult = await client.query(VERIFY_TOTAL_RAW_SQL);
    v.totalRawMatchData = rawResult.rows[0].count;

    const pipelineResult = await client.query(VERIFY_PIPELINE_SQL);
    v.pipelineStatus = {};
    for (const row of pipelineResult.rows) {
        v.pipelineStatus[row.pipeline_status] = row.count;
    }

    const trainingResult = await client.query(VERIFY_TRAINING_SQL);
    v.trainingEligible = {};
    for (const row of trainingResult.rows) {
        v.trainingEligible[String(row.is_training_eligible)] = row.count;
    }

    const distResult = await client.query(VERIFY_RESULT_DISTRIBUTION_SQL, [TARGET_LEAGUE, TARGET_SEASON]);
    v.actualResultDistribution = {};
    for (const row of distResult.rows) {
        v.actualResultDistribution[row.actual_result] = row.count;
    }

    const excludedResult = await client.query(
        VERIFY_EXCLUDED_STILL_NULL_SQL,
        [EXPECTED_PREFLIGHT.excluded_match_ids]
    );
    v.excludedStillNull = excludedResult.rows;

    return v;
}

function buildWriteVerificationPayload(preflight, writeResult, verification) {
    const updatedCount = writeResult.updatedCount;
    const writeSuccess = updatedCount === EXPECTED_PREFLIGHT.would_update_count;
    const distributionMatch = distributionsEqual(
        verification.actualResultDistribution,
        EXPECTED_PREFLIGHT.result_distribution
    );
    const excludedUnchanged = verification.excludedStillNull.every(
        row => row.home_score === null && row.away_score === null && row.actual_result === null
    );

    const allPassed =
        writeSuccess &&
        distributionMatch &&
        excludedUnchanged &&
        verification.totalMatches === EXPECTED_PREFLIGHT.total_matches_scanned &&
        verification.totalRawMatchData === 76 &&
        (verification.pipelineStatus['harvested'] || 0) === 58 &&
        (verification.pipelineStatus['pending'] || 0) === 2 &&
        (verification.trainingEligible['false'] || 0) === 60 &&
        (verification.trainingEligible['true'] || 0) === 0;

    return {
        phase: PHASE,
        mode: 'write_executed',
        actual_update_executed: true,
        read_only: false,
        contract_carrier: CONTRACT_CARRIER,
        script: 'scripts/ops/score_backfill_write.js',
        generated_at: new Date().toISOString(),
        target_scope: { league_name: TARGET_LEAGUE, season: TARGET_SEASON },
        preflight_summary: {
            total_matches_scanned: preflight.total_matches_scanned,
            target_ligue1_count: preflight.target_ligue1_count,
            would_update_count: preflight.would_update_count,
            would_skip_count: preflight.would_skip_count,
            mismatch_count: preflight.score_consistency_summary.score_str_mismatch_count,
            preflight_result_distribution: preflight.actual_result_distribution,
            excluded_no_raw_match_ids: preflight.excluded_no_raw_match_ids,
        },
        write_result: {
            success: writeSuccess,
            updated_count: updatedCount,
            expected_count: EXPECTED_PREFLIGHT.would_update_count,
        },
        post_write_verification: {
            all_passed: allPassed,
            updated_count: verification.updatedCount,
            total_matches: verification.totalMatches,
            total_raw_match_data: verification.totalRawMatchData,
            pipeline_status: verification.pipelineStatus,
            is_training_eligible: verification.trainingEligible,
            actual_result_distribution: verification.actualResultDistribution,
            expected_distribution: EXPECTED_PREFLIGHT.result_distribution,
            distribution_match: distributionMatch,
            excluded_still_null: verification.excludedStillNull,
            excluded_unchanged: excludedUnchanged,
        },
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: true,
            raw_match_data_write_allowed: false,
            backfill_executed: true,
            live_fetch_allowed: false,
            raw_payload_output_allowed: false,
            parser_change_in_scope: false,
            training_change_in_scope: false,
            prediction_change_in_scope: false,
            read_only_transaction_used: false,
            single_transaction_used: true,
            strict_where_conditions: [
                'match_id exact match via VALUES join',
                'home_score IS NULL',
                'away_score IS NULL',
                'actual_result IS NULL',
            ],
            only_fields_written: [
                'matches.home_score',
                'matches.away_score',
                'matches.actual_result',
            ],
            actual_result_encoding: 'home_win / draw / away_win',
        },
    };
}

async function runWrite(options = {}, dependencies = {}) {
    const preflight = await runDryRun(options, dependencies);

    const validation = validatePreflight(preflight);
    if (!validation.passed) {
        throw new Error(
            'Preflight validation failed. Aborting write.\n' +
            validation.failures.map(f => `  - ${f}`).join('\n')
        );
    }

    const fullScan = await scanMatchesForDryRun(dependencies);
    const fullClassified = fullScan.map(classifyScannedMatch);
    const fullUpdates = fullClassified
        .filter(row => row.would_update)
        .map(row => ({
            match_id: row.match_id,
            external_id: row.external_id,
            proposed_home_score: row.proposed_home_score,
            proposed_away_score: row.proposed_away_score,
            proposed_actual_result: row.proposed_actual_result,
        }));

    if (fullUpdates.length !== EXPECTED_PREFLIGHT.would_update_count) {
        throw new Error(
            `Write update count mismatch: ${fullUpdates.length} updates from scan, ` +
            `expected ${EXPECTED_PREFLIGHT.would_update_count}`
        );
    }

    const connection = await openWriteClient(dependencies);
    let committed = false;

    try {
        const writeResult = await executeWriteTransaction(connection.client, fullUpdates);
        const verification = await runPostWriteVerification(connection.client);
        await connection.client.query('COMMIT');
        committed = true;
        return buildWriteVerificationPayload(preflight, writeResult, verification);
    } catch (error) {
        if (!committed) {
            try { await connection.client.query('ROLLBACK'); } catch { /* preserve original error */ }
        }
        throw error;
    } finally {
        await connection.close();
    }
}

module.exports = {
    EXPECTED_PREFLIGHT,
    WRITE_UPDATE_SQL_PREFIX,
    WRITE_UPDATE_SQL_SUFFIX,
    distributionsEqual,
    buildWriteUpdateSql,
    flattenUpdateParams,
    validatePreflight,
    openWriteClient,
    executeWriteTransaction,
    runPostWriteVerification,
    buildWriteVerificationPayload,
    runWrite,
};
