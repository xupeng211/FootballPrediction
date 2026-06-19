#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: read-only smoke training dataset builder dry-run

const PHASE = 'SMOKE_TRAINING_DATASET_DRY_RUN';
const TARGET_LEAGUE = 'Ligue 1';
const TARGET_SEASON = '2025/2026';
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';

const SAFE_FEATURE_COLUMNS = Object.freeze([
    'league_name',
    'season',
    'home_team',
    'away_team',
    'match_date',
    'venue',
    'referee',
]);

const LABEL_COLUMN = 'actual_result';
const VALID_LABELS = Object.freeze(['home_win', 'draw', 'away_win']);
const VALID_LABEL_SET = new Set(VALID_LABELS);

const EXPECTED_SAMPLE_COUNT = 58;
const EXPECTED_LABEL_DISTRIBUTION = Object.freeze({
    home_win: 23,
    draw: 17,
    away_win: 18,
});

const EXCLUDED_COLUMNS = Object.freeze([
    'actual_result',
    'home_score',
    'away_score',
    'home_corners',
    'away_corners',
    'home_yellow_cards',
    'away_yellow_cards',
    'home_red_cards',
    'away_red_cards',
    'status',
    'is_finished',
    'pipeline_status',
    'source_type',
    'evidence_level',
    'is_training_eligible',
    'raw_match_data',
    'pipeline_status_reason',
    'data_source',
    'data_version',
    'is_production_scope',
    'is_reconciliation_eligible',
    'collection_date',
    'created_at',
    'updated_at',
    'match_id',
    'external_id',
]);

const DISALLOWED_FEATURE_COLUMNS = new Set(EXCLUDED_COLUMNS);

const SCAN_SQL = `
SELECT
    m.league_name,
    m.season,
    m.home_team,
    m.away_team,
    m.match_date,
    m.venue,
    m.referee,
    m.actual_result
FROM matches m
WHERE m.is_training_eligible = true
  AND m.league_name = $1
  AND m.season = $2
ORDER BY m.match_id
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/smoke_training_dataset_dry_run.js [--json]',
        '',
        'Safety:',
        '  只读 dry-run。不会训练模型，不会写库，不会输出 raw payload。',
    ].join('\n');
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = { json: false, help: false };
    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (arg === '--json') {
            options.json = true;
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

async function openReadOnlyClient(dependencies = {}) {
    if (dependencies.client) {
        return { client: dependencies.client, close: async () => {} };
    }

    const { Pool } = require('pg');
    const pool = new Pool(buildDbConfig());
    const client = await pool.connect();

    return {
        client,
        close: async () => {
            if (typeof client.release === 'function') {
                client.release();
            }
            await pool.end();
        },
    };
}

function assertSelectOnlySql(sql) {
    const normalized = String(sql || '').replace(/\s+/g, ' ').trim().toUpperCase();
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

async function scanTrainingEligibleRows(dependencies = {}) {
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
            try {
                await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
            } catch {
                // 保留原始错误
            }
        }
        await connection.close();
    }
}

function isMissingValue(value) {
    if (value === null || value === undefined) {
        return true;
    }
    if (typeof value === 'string') {
        return value.trim() === '';
    }
    return false;
}

function buildOrderedLabelDistribution(rows) {
    const distribution = {
        home_win: 0,
        draw: 0,
        away_win: 0,
    };

    for (const row of rows) {
        if (VALID_LABEL_SET.has(row.actual_result)) {
            distribution[row.actual_result] += 1;
        }
    }

    return distribution;
}

function buildMissingRateByFeature(rows, featureColumns = SAFE_FEATURE_COLUMNS) {
    const totalCount = rows.length;
    const missingRateByFeature = {};

    for (const feature of featureColumns) {
        const missingCount = rows.filter(row => isMissingValue(row[feature])).length;
        missingRateByFeature[feature] = {
            missing_count: missingCount,
            total_count: totalCount,
            missing_rate: totalCount === 0 ? 0 : Number((missingCount / totalCount).toFixed(6)),
        };
    }

    return missingRateByFeature;
}

function detectLeakageColumns(featureColumns = SAFE_FEATURE_COLUMNS) {
    return featureColumns.filter(column => DISALLOWED_FEATURE_COLUMNS.has(column) || column === LABEL_COLUMN);
}

function buildMatrices(rows, featureColumns = SAFE_FEATURE_COLUMNS, labelColumn = LABEL_COLUMN) {
    const xRows = rows.map(row => {
        const record = {};
        for (const column of featureColumns) {
            record[column] = row[column];
        }
        return record;
    });

    const yRows = rows.map(row => row[labelColumn]);

    return { xRows, yRows };
}

function sameLabelDistribution(left, right) {
    return VALID_LABELS.every(label => (left[label] || 0) === (right[label] || 0));
}

function buildRiskFlags({ sampleCount, missingRateByFeature, invalidLabelValues }) {
    const riskFlags = [
        'dry_run_only_no_training_executed',
        'read_only_select_only_no_db_write',
        `small_sample_size_${sampleCount}_smoke_only_not_for_production_training`,
        'categorical_encoding_required_for_team_and_context_fields',
    ];

    for (const feature of SAFE_FEATURE_COLUMNS) {
        const missingRate = missingRateByFeature[feature]?.missing_rate ?? 0;
        if (missingRate > 0) {
            riskFlags.push(`${feature}_missing_rate_${missingRate}`);
        }
    }

    if (invalidLabelValues.length > 0) {
        riskFlags.push(`invalid_label_values_detected_${invalidLabelValues.join('|')}`);
    }

    return riskFlags;
}

function buildDryRunPayload(rows) {
    const sampleCount = rows.length;
    const featureColumns = [...SAFE_FEATURE_COLUMNS];
    const labelDistribution = buildOrderedLabelDistribution(rows);
    const missingRateByFeature = buildMissingRateByFeature(rows, featureColumns);
    const leakageColumnsDetected = detectLeakageColumns(featureColumns);
    const { xRows, yRows } = buildMatrices(rows, featureColumns, LABEL_COLUMN);
    const invalidLabelValues = [...new Set(
        rows
            .map(row => row.actual_result)
            .filter(value => !VALID_LABEL_SET.has(value))
            .map(value => String(value))
    )];

    const validationChecks = {
        expected_sample_count: EXPECTED_SAMPLE_COUNT,
        actual_sample_count: sampleCount,
        sample_count_matches_expected: sampleCount === EXPECTED_SAMPLE_COUNT,
        expected_label_distribution: EXPECTED_LABEL_DISTRIBUTION,
        actual_label_distribution: labelDistribution,
        label_distribution_matches_expected: sameLabelDistribution(
            labelDistribution,
            EXPECTED_LABEL_DISTRIBUTION
        ),
        expected_feature_columns: featureColumns,
        feature_columns_match_expected:
            JSON.stringify(featureColumns) === JSON.stringify(SAFE_FEATURE_COLUMNS),
        expected_label_column: LABEL_COLUMN,
        label_column_matches_expected: LABEL_COLUMN === 'actual_result',
        leakage_columns_detected_empty: leakageColumnsDetected.length === 0,
        invalid_label_values: invalidLabelValues,
    };

    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        script: 'scripts/ops/smoke_training_dataset_dry_run.js',
        generated_at: new Date().toISOString(),
        target_scope: {
            league_name: TARGET_LEAGUE,
            season: TARGET_SEASON,
            is_training_eligible: true,
        },
        sample_count: sampleCount,
        feature_columns: featureColumns,
        label_column: LABEL_COLUMN,
        label_distribution: labelDistribution,
        missing_rate_by_feature: missingRateByFeature,
        x_shape: [xRows.length, featureColumns.length],
        y_shape: [yRows.length],
        leakage_columns_detected: leakageColumnsDetected,
        excluded_columns: [...EXCLUDED_COLUMNS],
        validation_checks: validationChecks,
        risk_flags: buildRiskFlags({
            sampleCount,
            missingRateByFeature,
            invalidLabelValues,
        }),
        recommendation:
            '58 条样本仅适合 smoke/integration dataset dry-run；正式训练、导出或模型产出必须等待用户再次确认。',
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            db_write_executed: false,
            live_fetch_allowed: false,
            live_fetch_executed: false,
            raw_payload_output_allowed: false,
            raw_payload_output_detected: false,
            model_training_performed: false,
            model_output_generated: false,
            read_only_transaction_used: true,
        },
    };
}

async function runDryRun(options = {}, dependencies = {}) {
    const rows = await scanTrainingEligibleRows(dependencies);
    return buildDryRunPayload(rows);
}

function payloadToText(payload) {
    const labelDistribution = VALID_LABELS
        .map(label => `  ${label}: ${payload.label_distribution[label] ?? 0}`)
        .join('\n');
    const missingRates = SAFE_FEATURE_COLUMNS
        .map(feature => {
            const stats = payload.missing_rate_by_feature[feature];
            return `  ${feature}: missing=${stats.missing_count}/${stats.total_count} rate=${stats.missing_rate}`;
        })
        .join('\n');
    const leakageColumns = payload.leakage_columns_detected.length > 0
        ? payload.leakage_columns_detected.map(column => `  - ${column}`).join('\n')
        : '  - none';
    const excludedColumns = payload.excluded_columns.map(column => `  - ${column}`).join('\n');
    const riskFlags = payload.risk_flags.map(flag => `  - ${flag}`).join('\n');

    return [
        '[DRY-RUN] Smoke training dataset builder',
        `Phase: ${payload.phase}`,
        `Mode: ${payload.mode}`,
        `Sample count: ${payload.sample_count}`,
        `Feature columns: ${payload.feature_columns.join(', ')}`,
        `Label column: ${payload.label_column}`,
        `X shape: [${payload.x_shape.join(', ')}]`,
        `Y shape: [${payload.y_shape.join(', ')}]`,
        'Label distribution:',
        labelDistribution,
        'Missing rate by feature:',
        missingRates,
        'Leakage columns detected:',
        leakageColumns,
        'Excluded columns:',
        excludedColumns,
        'Risk flags:',
        riskFlags,
        `Recommendation: ${payload.recommendation}`,
    ].join('\n');
}

function writePayload(payload, json, io) {
    const output = json
        ? `${JSON.stringify(payload, null, 2)}\n`
        : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

function buildFailurePayload(error) {
    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        script: 'scripts/ops/smoke_training_dataset_dry_run.js',
        target_scope: {
            league_name: TARGET_LEAGUE,
            season: TARGET_SEASON,
            is_training_eligible: true,
        },
        errors: [error.message],
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            db_write_executed: false,
            live_fetch_allowed: false,
            live_fetch_executed: false,
            raw_payload_output_allowed: false,
            raw_payload_output_detected: false,
            model_training_performed: false,
            model_output_generated: false,
            read_only_transaction_used: true,
        },
    };
}

async function main(argv = process.argv.slice(2), io = {}) {
    const output = {
        stdout: io.stdout || (text => process.stdout.write(text)),
        stderr: io.stderr || (text => process.stderr.write(text)),
    };

    let options = { json: false, help: false };

    try {
        options = parseArgs(argv);
        if (options.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }

        const payload = await runDryRun(options);
        writePayload(payload, options.json, output);
        return 0;
    } catch (error) {
        const payload = buildFailurePayload(error);
        writePayload(payload, options.json === true, output);
        return 1;
    }
}

if (require.main === module) {
    main().then(code => {
        process.exitCode = code;
    });
}

module.exports = {
    SAFE_FEATURE_COLUMNS,
    LABEL_COLUMN,
    VALID_LABELS,
    EXPECTED_SAMPLE_COUNT,
    EXPECTED_LABEL_DISTRIBUTION,
    EXCLUDED_COLUMNS,
    SCAN_SQL,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    parseArgs,
    assertSelectOnlySql,
    buildOrderedLabelDistribution,
    buildMissingRateByFeature,
    detectLeakageColumns,
    buildMatrices,
    buildDryRunPayload,
    runDryRun,
    main,
};
