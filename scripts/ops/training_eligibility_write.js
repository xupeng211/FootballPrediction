'use strict';

// lifecycle: permanent
// scope: authorized training eligibility write executor for Ligue 1 2025/2026
// requires explicit --allow-write --json; single transaction, strict WHERE, rollback on failure

// All requires from the dry-run module are lazy (inside functions) to avoid
// circular dependency when main() in the dry-run script requires this module.

const TARGET_LEAGUE = 'Ligue 1';
const TARGET_SEASON = '2025/2026';
const PHASE = 'TRAINING_ELIGIBILITY_AFTER_SCORE_DRY_RUN';
const CONTRACT_CARRIER = 'matches.is_training_eligible (read-only preflight)';

const EXPECTED_PREFLIGHT = Object.freeze({
    total_matches_scanned: 60,
    target_ligue1_count: 58,
    would_set_true_count: 58,
    would_keep_false_count: 2,
    current_training_eligible_true: 0,
    current_training_eligible_false: 60,
    result_distribution: Object.freeze({ home_win: 23, draw: 17, away_win: 18 }),
    excluded_match_ids: ['47_20242025_900002', '140_20252026_4837496'],
});

const WRITE_UPDATE_SQL = `
UPDATE matches SET is_training_eligible = true
FROM (VALUES
`;

const WRITE_UPDATE_SQL_SUFFIX = `
) AS v(match_id)
WHERE matches.match_id = v.match_id
  AND matches.is_training_eligible = false
  AND matches.status = 'finished'
  AND matches.pipeline_status = 'harvested'
  AND matches.source_type = 'fotmob_live_fetch'
  AND matches.evidence_level = 'strong'
  AND matches.is_production_scope = true
  AND matches.is_reconciliation_eligible = true
  AND matches.home_score IS NOT NULL
  AND matches.away_score IS NOT NULL
  AND matches.actual_result IN ('home_win', 'draw', 'away_win')
  AND matches.pipeline_status_reason IS NULL
RETURNING matches.match_id
`;

const VERIFY_COUNT_SQL = `
SELECT COUNT(*)::integer AS count
FROM matches
WHERE league_name = $1
  AND season = $2
  AND is_training_eligible = true
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

const VERIFY_EXCLUDED_STILL_FALSE_SQL = `
SELECT match_id, is_training_eligible
FROM matches
WHERE match_id = ANY($1::text[])
`;

const VERIFY_SCORE_DIST_SQL = `
SELECT actual_result, COUNT(*)::integer AS count
FROM matches
WHERE league_name = $1
  AND season = $2
  AND actual_result IS NOT NULL
GROUP BY actual_result
ORDER BY actual_result
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

function validatePreflight(payload) {
    const failures = [];

    if (payload.total_matches_scanned !== EXPECTED_PREFLIGHT.total_matches_scanned) {
        failures.push(`total_matches_scanned=${payload.total_matches_scanned} expected=${EXPECTED_PREFLIGHT.total_matches_scanned}`);
    }
    if (payload.target_ligue1_count !== EXPECTED_PREFLIGHT.target_ligue1_count) {
        failures.push(`target_ligue1_count=${payload.target_ligue1_count} expected=${EXPECTED_PREFLIGHT.target_ligue1_count}`);
    }
    if (payload.would_set_true_count !== EXPECTED_PREFLIGHT.would_set_true_count) {
        failures.push(`would_set_true_count=${payload.would_set_true_count} expected=${EXPECTED_PREFLIGHT.would_set_true_count}`);
    }
    if (payload.would_keep_false_count !== EXPECTED_PREFLIGHT.would_keep_false_count) {
        failures.push(`would_keep_false_count=${payload.would_keep_false_count} expected=${EXPECTED_PREFLIGHT.would_keep_false_count}`);
    }
    if (payload.current_training_eligible_true !== EXPECTED_PREFLIGHT.current_training_eligible_true) {
        failures.push(`current_true=${payload.current_training_eligible_true} expected=${EXPECTED_PREFLIGHT.current_training_eligible_true}`);
    }
    if (payload.current_training_eligible_false !== EXPECTED_PREFLIGHT.current_training_eligible_false) {
        failures.push(`current_false=${payload.current_training_eligible_false} expected=${EXPECTED_PREFLIGHT.current_training_eligible_false}`);
    }
    if (!distributionsEqual(payload.actual_result_distribution, EXPECTED_PREFLIGHT.result_distribution)) {
        failures.push('result_distribution_mismatch');
    }

    return { passed: failures.length === 0, failures };
}

function buildWriteUpdateSql(updates) {
    const valueRows = updates.map((_, i) => `($${i + 1}::text)`).join(',\n  ');
    return `${WRITE_UPDATE_SQL}
  ${valueRows}
${WRITE_UPDATE_SQL_SUFFIX}`;
}

function flattenWriteParams(updates) {
    return updates.map(u => u.match_id);
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

    const { buildDbConfig } = require('./training_eligibility_after_score_dry_run');
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
    const params = flattenWriteParams(updates);

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

    const countResult = await client.query(VERIFY_COUNT_SQL, [TARGET_LEAGUE, TARGET_SEASON]);
    v.updatedCount = countResult.rows[0].count;

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

    const scoreResult = await client.query(VERIFY_SCORE_DIST_SQL, [TARGET_LEAGUE, TARGET_SEASON]);
    v.actualResultDistribution = {};
    for (const row of scoreResult.rows) {
        v.actualResultDistribution[row.actual_result] = row.count;
    }

    const excludedResult = await client.query(
        VERIFY_EXCLUDED_STILL_FALSE_SQL,
        [EXPECTED_PREFLIGHT.excluded_match_ids]
    );
    v.excludedStillFalse = excludedResult.rows;

    return v;
}

function buildWriteVerificationPayload(preflight, writeResult, verification) {
    const updatedCount = writeResult.updatedCount;
    const writeSuccess = updatedCount === EXPECTED_PREFLIGHT.would_set_true_count;
    const distributionMatch = distributionsEqual(
        verification.actualResultDistribution,
        EXPECTED_PREFLIGHT.result_distribution
    );
    const excludedUnchanged = verification.excludedStillFalse.every(
        row => row.is_training_eligible === false
    );

    const allPassed =
        writeSuccess &&
        distributionMatch &&
        excludedUnchanged &&
        verification.totalMatches === EXPECTED_PREFLIGHT.total_matches_scanned &&
        verification.totalRawMatchData === 76 &&
        (verification.pipelineStatus['harvested'] || 0) === 58 &&
        (verification.pipelineStatus['pending'] || 0) === 2 &&
        (verification.trainingEligible['true'] || 0) === 58 &&
        (verification.trainingEligible['false'] || 0) === 2;

    return {
        phase: PHASE,
        mode: 'write_executed',
        actual_update_executed: true,
        read_only: false,
        contract_carrier: CONTRACT_CARRIER,
        script: 'scripts/ops/training_eligibility_write.js',
        generated_at: new Date().toISOString(),
        target_scope: { league_name: TARGET_LEAGUE, season: TARGET_SEASON },
        preflight_summary: {
            total_matches_scanned: preflight.total_matches_scanned,
            target_ligue1_count: preflight.target_ligue1_count,
            would_set_true_count: preflight.would_set_true_count,
            would_keep_false_count: preflight.would_keep_false_count,
            preflight_result_distribution: preflight.actual_result_distribution,
        },
        write_result: {
            success: writeSuccess,
            updated_count: updatedCount,
            expected_count: EXPECTED_PREFLIGHT.would_set_true_count,
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
            excluded_still_false: verification.excludedStillFalse,
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
            features_change_in_scope: false,
            training_change_in_scope: false,
            prediction_change_in_scope: false,
            score_fields_unchanged: true,
            read_only_transaction_used: false,
            single_transaction_used: true,
            strict_where_conditions: [
                'match_id exact match via VALUES join',
                'is_training_eligible = false',
                'status = finished',
                'pipeline_status = harvested',
                'source_type = fotmob_live_fetch',
                'evidence_level = strong',
                'is_production_scope = true',
                'is_reconciliation_eligible = true',
                'home_score IS NOT NULL',
                'away_score IS NOT NULL',
                'actual_result IN (home_win, draw, away_win)',
                'pipeline_status_reason IS NULL',
            ],
            only_fields_written: ['matches.is_training_eligible'],
        },
    };
}

async function runWrite(options = {}, dependencies = {}) {
    const dryRun = require('./training_eligibility_after_score_dry_run');
    const preflight = await dryRun.runDryRun(options, dependencies);

    const validation = validatePreflight(preflight);
    if (!validation.passed) {
        throw new Error(
            'Preflight validation failed. Aborting write.\n' +
            validation.failures.map(f => `  - ${f}`).join('\n')
        );
    }

    const scannedRows = await dryRun.scanMatches(dependencies);

    const updates = [];
    for (const row of scannedRows) {
        const evaluation = dryRun.evaluateRow(row);
        if (evaluation.would_set_true) {
            updates.push({ match_id: row.match_id });
        }
    }

    if (updates.length !== EXPECTED_PREFLIGHT.would_set_true_count) {
        throw new Error(
            `Write update count mismatch: ${updates.length} updates from scan, ` +
            `expected ${EXPECTED_PREFLIGHT.would_set_true_count}`
        );
    }

    const connection = await openWriteClient(dependencies);
    let committed = false;

    try {
        const writeResult = await executeWriteTransaction(connection.client, updates);
        const verification = await runPostWriteVerification(connection.client);
        await connection.client.query('COMMIT');
        committed = true;
        return buildWriteVerificationPayload(preflight, writeResult, verification);
    } catch (error) {
        if (!committed) {
            try { await connection.client.query('ROLLBACK'); } catch { /* preserve */ }
        }
        throw error;
    } finally {
        await connection.close();
    }
}

module.exports = {
    EXPECTED_PREFLIGHT,
    WRITE_UPDATE_SQL,
    WRITE_UPDATE_SQL_SUFFIX,
    validatePreflight,
    buildWriteUpdateSql,
    flattenWriteParams,
    openWriteClient,
    executeWriteTransaction,
    runPostWriteVerification,
    buildWriteVerificationPayload,
    runWrite,
};
