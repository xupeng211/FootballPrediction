#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: read-only training eligibility dry-run for Ligue 1 2025/2026 after score backfill

const PHASE = 'TRAINING_ELIGIBILITY_AFTER_SCORE_DRY_RUN';
const CONTRACT_CARRIER = 'matches.is_training_eligible (read-only preflight)';
const TARGET_LEAGUE = 'Ligue 1';
const TARGET_SEASON = '2025/2026';
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';

const VALID_ACTUAL_RESULTS = new Set(['home_win', 'draw', 'away_win']);

const SCAN_SQL = `
SELECT
    m.match_id,
    m.external_id,
    m.league_name,
    m.season,
    m.status,
    m.pipeline_status,
    m.source_type,
    m.evidence_level,
    m.is_production_scope,
    m.is_reconciliation_eligible,
    m.is_training_eligible,
    m.pipeline_status_reason,
    m.home_score,
    m.away_score,
    m.actual_result
FROM matches m
ORDER BY
    CASE
        WHEN m.league_name = $1
         AND m.season = $2
        THEN 0
        ELSE 1
    END,
    m.league_name ASC,
    m.season ASC,
    m.match_id ASC
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/training_eligibility_after_score_dry_run.js [--json] [--allow-write]',
        '',
        'Options:',
        '  --json            JSON output',
        '  --allow-write     Execute real training eligibility write (requires --json)',
        '',
        'Safety:',
        '  Default is dry-run. Real write only with --allow-write --json.',
        '  Single transaction, strict WHERE, rollback on failure.',
        '  No migration, no schema change, no raw write, no live fetch.',
    ].join('\n');
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = { json: false, help: false, allowWrite: false };

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (arg === '--json') {
            options.json = true;
        } else if (arg === '--allow-write') {
            options.allowWrite = true;
        } else if (arg === '--help' || arg === '-h') {
            options.help = true;
        } else {
            throw new Error(`Unknown argument: ${arg}`);
        }
    }

    return options;
}

function buildDbConfig() {
    return {
        host: process.env.DB_HOST || process.env.POSTGRES_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || process.env.POSTGRES_PORT || '5432', 10),
        database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
        user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD,
        max: 1,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000,
    };
}

function createPool(dependencies = {}) {
    if (dependencies.pool) {
        return dependencies.pool;
    }
    const { Pool } = require('pg');
    return new Pool(buildDbConfig());
}

async function openReadOnlyClient(dependencies = {}) {
    if (dependencies.client) {
        return { client: dependencies.client, close: async () => {} };
    }

    const pool = createPool(dependencies);
    const ownsPool = !dependencies.pool;

    if (typeof pool.connect === 'function') {
        const client = await pool.connect();
        return {
            client,
            close: async () => {
                if (typeof client.release === 'function') { client.release(); }
                if (ownsPool && typeof pool.end === 'function') { await pool.end(); }
            },
        };
    }

    return {
        client: pool,
        close: async () => {
            if (ownsPool && typeof pool.end === 'function') { await pool.end(); }
        },
    };
}

function assertSelectOnlySql(sql) {
    const normalized = String(sql || '')
        .replace(/\s+/g, ' ')
        .trim()
        .toUpperCase();

    const allowed =
        normalized === READ_ONLY_BEGIN_SQL ||
        normalized === READ_ONLY_ROLLBACK_SQL ||
        normalized.startsWith('SELECT ') ||
        normalized.startsWith('WITH ');

    if (!allowed) {
        throw new Error(`Unsafe SQL rejected by ${PHASE}: ${normalized.slice(0, 80)}`);
    }
}

async function querySelectOnly(client, sql, params = []) {
    assertSelectOnlySql(sql);
    return client.query(sql, params);
}

function normalizeOptionalText(value) {
    const normalized = String(value ?? '').trim();
    return normalized ? normalized : null;
}

function isTargetScope(row) {
    return row.league_name === TARGET_LEAGUE && row.season === TARGET_SEASON;
}

/**
 * Evaluate whether a match row satisfies all training eligibility conditions.
 * Returns the would-be eligibility and a reason string.
 */
function evaluateRow(row) {
    const checks = [
        { key: 'target_scope', fn: () => isTargetScope(row), reason: 'excluded_non_target_scope' },
        { key: 'status_finished', fn: () => String(row.status || '').trim().toLowerCase() === 'finished', reason: 'status_not_finished' },
        { key: 'pipeline_status_harvested', fn: () => String(row.pipeline_status || '').trim().toLowerCase() === 'harvested', reason: 'pipeline_status_not_harvested' },
        { key: 'source_type_fotmob_live_fetch', fn: () => row.source_type === 'fotmob_live_fetch', reason: 'source_type_not_fotmob_live_fetch' },
        { key: 'evidence_level_strong', fn: () => row.evidence_level === 'strong', reason: 'evidence_level_not_strong' },
        { key: 'is_production_scope_true', fn: () => row.is_production_scope === true, reason: 'not_production_scope' },
        { key: 'is_reconciliation_eligible_true', fn: () => row.is_reconciliation_eligible === true, reason: 'not_reconciliation_eligible' },
        { key: 'home_score_not_null', fn: () => row.home_score !== null, reason: 'home_score_null' },
        { key: 'away_score_not_null', fn: () => row.away_score !== null, reason: 'away_score_null' },
        { key: 'actual_result_valid', fn: () => VALID_ACTUAL_RESULTS.has(normalizeOptionalText(row.actual_result)), reason: 'actual_result_invalid_or_null' },
        { key: 'pipeline_status_reason_null', fn: () => row.pipeline_status_reason === null, reason: 'pipeline_status_reason_not_null' },
        { key: 'currently_training_eligible_false', fn: () => row.is_training_eligible === false || row.is_training_eligible === null, reason: 'already_training_eligible_true' },
    ];

    const validations = {};
    const failedReasons = [];

    for (const check of checks) {
        const passed = check.fn();
        validations[check.key] = passed;
        if (!passed) {
            failedReasons.push(check.reason);
        }
    }

    return {
        would_set_true: failedReasons.length === 0,
        validations,
        skip_reasons: failedReasons,
    };
}

function countDistribution(rows, keyFn) {
    const distribution = {};
    for (const row of rows) {
        const key = keyFn(row);
        if (key === null || key === undefined || key === '') { continue; }
        distribution[key] = (distribution[key] || 0) + 1;
    }
    return distribution;
}

function countByReason(wouldKeepFalseRows) {
    const reasonCounts = {};
    for (const row of wouldKeepFalseRows) {
        for (const reason of row.skip_reasons) {
            reasonCounts[reason] = (reasonCounts[reason] || 0) + 1;
        }
    }
    return reasonCounts;
}

function formatSampleRow(row) {
    return {
        match_id: row.match_id,
        external_id: row.external_id,
        league_name: row.league_name,
        season: row.season,
        status: row.status,
        pipeline_status: row.pipeline_status,
        source_type: row.source_type,
        evidence_level: row.evidence_level,
        is_production_scope: row.is_production_scope,
        is_reconciliation_eligible: row.is_reconciliation_eligible,
        current_training_eligible: row.is_training_eligible,
        would_set_true: row.would_set_true,
        skip_reasons: row.skip_reasons,
    };
}

function buildDryRunPayload(classifiedRows) {
    const targetRows = classifiedRows.filter(row => row.is_target_scope);
    const wouldSetTrue = classifiedRows.filter(row => row.would_set_true);
    const wouldKeepFalse = classifiedRows.filter(row => !row.would_set_true);

    const byReason = countByReason(wouldKeepFalse);

    const riskFlags = [
        'dry_run_only_no_db_write',
        'real_training_eligibility_write_requires_explicit_user_authorization',
    ];

    if (wouldSetTrue.length !== targetRows.length) {
        riskFlags.push(`target_gap_detected:target=${targetRows.length}_would_set_true=${wouldSetTrue.length}`);
    }

    const excludedNoRawRows = wouldKeepFalse.filter(
        row => row.skip_reasons.includes('source_type_not_fotmob_live_fetch') &&
               row.skip_reasons.includes('evidence_level_not_strong')
    );
    if (excludedNoRawRows.length !== 2) {
        riskFlags.push(`unexpected_excluded_count:${excludedNoRawRows.length}`);
    }

    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        contract_carrier: CONTRACT_CARRIER,
        script: 'scripts/ops/training_eligibility_after_score_dry_run.js',
        generated_at: new Date().toISOString(),
        target_scope: {
            league_name: TARGET_LEAGUE,
            season: TARGET_SEASON,
            description: 'Evaluate training eligibility after score backfill write',
        },
        total_matches_scanned: classifiedRows.length,
        target_ligue1_count: targetRows.length,
        would_set_true_count: wouldSetTrue.length,
        would_keep_false_count: wouldKeepFalse.length,
        current_training_eligible_true: classifiedRows.filter(r => r.is_training_eligible === true).length,
        current_training_eligible_false: classifiedRows.filter(r => r.is_training_eligible === false || r.is_training_eligible === null).length,
        actual_result_distribution: countDistribution(
            wouldSetTrue,
            row => normalizeOptionalText(row.actual_result)
        ),
        eligibility_conditions: [
            'status=finished',
            'pipeline_status=harvested',
            'source_type=fotmob_live_fetch',
            'evidence_level=strong',
            'is_production_scope=true',
            'is_reconciliation_eligible=true',
            'home_score IS NOT NULL',
            'away_score IS NOT NULL',
            'actual_result IN (home_win, draw, away_win)',
            'pipeline_status_reason IS NULL',
            'is_training_eligible=false',
        ],
        by_reason: byReason,
        sample_true: wouldSetTrue.slice(0, 5).map(formatSampleRow),
        sample_false: wouldKeepFalse.map(formatSampleRow),
        risk_flags: riskFlags,
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            backfill_executed: false,
            live_fetch_allowed: false,
            raw_payload_output_allowed: false,
            parser_change_in_scope: false,
            training_change_in_scope: false,
            prediction_change_in_scope: false,
            read_only_transaction_used: true,
        },
    };
}

async function scanMatches(dependencies = {}) {
    const connection = await openReadOnlyClient(dependencies);
    let rolledBack = false;

    try {
        await querySelectOnly(connection.client, READ_ONLY_BEGIN_SQL);
        const result = await querySelectOnly(connection.client, SCAN_SQL, [TARGET_LEAGUE, TARGET_SEASON]);
        await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
        rolledBack = true;
        return result.rows || [];
    } finally {
        if (!rolledBack) {
            try { await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL); } catch { /* preserve original */ }
        }
        await connection.close();
    }
}

async function runDryRun(options = {}, dependencies = {}) {
    const scannedRows = await scanMatches(dependencies);
    const classifiedRows = scannedRows.map(row => ({
        ...evaluateRow(row),
        match_id: row.match_id,
        external_id: row.external_id,
        league_name: row.league_name,
        season: row.season,
        status: row.status,
        pipeline_status: row.pipeline_status,
        source_type: row.source_type,
        evidence_level: row.evidence_level,
        is_production_scope: row.is_production_scope,
        is_reconciliation_eligible: row.is_reconciliation_eligible,
        is_training_eligible: row.is_training_eligible,
        pipeline_status_reason: row.pipeline_status_reason,
        is_target_scope: isTargetScope(row),
        home_score: row.home_score,
        away_score: row.away_score,
        actual_result: normalizeOptionalText(row.actual_result),
    }));
    return buildDryRunPayload(classifiedRows);
}

function payloadToText(payload) {
    const actualResultDistribution = Object.entries(payload.actual_result_distribution || {})
        .map(([key, value]) => `  ${key}: ${value}`)
        .join('\n') || '  none';
    const byReason = Object.entries(payload.by_reason || {})
        .map(([key, value]) => `  ${key}: ${value}`)
        .join('\n') || '  none';
    const riskFlags = (payload.risk_flags || []).map(flag => `  - ${flag}`).join('\n') || '  - none';

    return [
        '[DRY-RUN] Training eligibility after score backfill preflight',
        `Phase: ${payload.phase}`,
        `Mode: ${payload.mode}`,
        `Actual update executed: ${payload.actual_update_executed}`,
        `Target scope: ${payload.target_scope.league_name} / ${payload.target_scope.season}`,
        `Total matches scanned: ${payload.total_matches_scanned}`,
        `Target Ligue 1 count: ${payload.target_ligue1_count}`,
        `Would set true count: ${payload.would_set_true_count}`,
        `Would keep false count: ${payload.would_keep_false_count}`,
        `Current training_eligible=true: ${payload.current_training_eligible_true}`,
        `Current training_eligible=false: ${payload.current_training_eligible_false}`,
        'Actual result distribution:',
        actualResultDistribution,
        'By reason:',
        byReason,
        'Risk flags:',
        riskFlags,
    ].join('\n');
}

function writePayload(payload, json, io) {
    const output = json
        ? `${JSON.stringify(payload, null, 2)}\n`
        : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

function buildFailurePayload(error, options = {}) {
    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        contract_carrier: CONTRACT_CARRIER,
        script: 'scripts/ops/training_eligibility_after_score_dry_run.js',
        target_scope: { league_name: TARGET_LEAGUE, season: TARGET_SEASON },
        errors: [error.message],
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            backfill_executed: false,
            live_fetch_allowed: false,
            raw_payload_output_allowed: false,
            parser_change_in_scope: false,
            training_change_in_scope: false,
            prediction_change_in_scope: false,
            read_only_transaction_used: true,
        },
    };
}

async function main(argv = process.argv.slice(2), io = {}) {
    const output = {
        stdout: io.stdout || (text => process.stdout.write(text)),
        stderr: io.stderr || (text => process.stderr.write(text)),
    };

    let options = { json: false, help: false, allowWrite: false };

    try {
        options = parseArgs(argv);
        if (options.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }

        if (options.allowWrite) {
            if (!options.json) {
                output.stderr('Error: --allow-write requires --json\n');
                return 1;
            }
            // Delegate to write module via child process to avoid circular dependency
            const { execFileSync } = require('child_process');
            const result = execFileSync(
                process.execPath,
                ['-e', 'require("./scripts/ops/training_eligibility_write").runWrite({json:true,allowWrite:true}).then(p=>console.log(JSON.stringify(p,null,2))).catch(e=>{console.error(e.message);process.exit(1)})'],
                { encoding: 'utf-8', timeout: 30000 }
            );
            output.stdout(result);
            return 0;
        }

        const payload = await runDryRun(options);
        writePayload(payload, options.json, output);
        return 0;
    } catch (error) {
        const payload = buildFailurePayload(error, options);
        writePayload(payload, options.json === true, output);
        return 1;
    }
}

if (require.main === module) {
    main().then(status => { process.exitCode = status; });
}

module.exports = {
    PHASE,
    CONTRACT_CARRIER,
    TARGET_LEAGUE,
    TARGET_SEASON,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    SCAN_SQL,
    parseArgs,
    buildDbConfig,
    openReadOnlyClient,
    assertSelectOnlySql,
    querySelectOnly,
    normalizeOptionalText,
    isTargetScope,
    evaluateRow,
    countDistribution,
    countByReason,
    formatSampleRow,
    buildDryRunPayload,
    scanMatches,
    runDryRun,
    payloadToText,
    buildFailurePayload,
    main,
};
