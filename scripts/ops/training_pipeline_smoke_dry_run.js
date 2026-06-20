#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: read-only training pipeline smoke dry-run

const PHASE = 'TRAINING_PIPELINE_SMOKE_DRY_RUN';
const TARGET_LEAGUE = 'Ligue 1';
const TARGET_SEASON = '2025/2026';
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';
const RANDOM_SEED = 20260619;
const TEST_RATIO = 0.25;

const FEATURE_COLUMNS = Object.freeze([
    'league_name',
    'season',
    'home_team',
    'away_team',
    'match_date',
]);

const EXCLUDED_FEATURE_COLUMNS = Object.freeze([
    'venue',
    'referee',
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

const LABEL_COLUMN = 'actual_result';
const VALID_LABELS = Object.freeze(['home_win', 'draw', 'away_win']);
const VALID_LABEL_SET = new Set(VALID_LABELS);
const EXPECTED_SAMPLE_COUNT = 58;
const EXPECTED_LABEL_DISTRIBUTION = Object.freeze({
    home_win: 23,
    draw: 17,
    away_win: 18,
});
const DISALLOWED_FEATURE_COLUMNS = new Set([...EXCLUDED_FEATURE_COLUMNS, LABEL_COLUMN]);

const SCAN_SQL = `
SELECT
    m.league_name,
    m.season,
    m.home_team,
    m.away_team,
    m.match_date,
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
        '  node scripts/ops/training_pipeline_smoke_dry_run.js [--json]',
        '',
        'Safety:',
        '  只读 smoke dry-run。不会写库，不会生成正式模型文件，不会做预测。',
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

async function scanTrainingRows(dependencies = {}) {
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

function buildOrderedLabelDistribution(rows) {
    const distribution = { home_win: 0, draw: 0, away_win: 0 };

    for (const row of rows) {
        if (VALID_LABEL_SET.has(row.actual_result)) {
            distribution[row.actual_result] += 1;
        }
    }

    return distribution;
}

function detectLeakageColumns(featureColumns = FEATURE_COLUMNS) {
    return featureColumns.filter(column => DISALLOWED_FEATURE_COLUMNS.has(column));
}

function normalizeText(value) {
    return String(value || '').trim();
}

function normalizeMatchDateToken(value) {
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) {
        throw new Error(`Invalid match_date value: ${value}`);
    }

    const dayOfWeek = date.getUTCDay();
    const month = date.getUTCMonth() + 1;
    const hour = date.getUTCHours();
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6 ? 1 : 0;

    return `weekday_${dayOfWeek}|month_${month}|hour_${hour}|weekend_${isWeekend}`;
}

function buildFeatureRecord(row) {
    return {
        league_name: normalizeText(row.league_name),
        season: normalizeText(row.season),
        home_team: normalizeText(row.home_team),
        away_team: normalizeText(row.away_team),
        match_date: row.match_date,
    };
}

function encodeFeatureRecord(featureRecord) {
    return {
        league_name: `league_name=${normalizeText(featureRecord.league_name)}`,
        season: `season=${normalizeText(featureRecord.season)}`,
        home_team: `home_team=${normalizeText(featureRecord.home_team)}`,
        away_team: `away_team=${normalizeText(featureRecord.away_team)}`,
        match_date: `match_date=${normalizeMatchDateToken(featureRecord.match_date)}`,
    };
}

function createSeededRandom(seed) {
    let state = (seed >>> 0) || 1;
    return () => {
        state = (1664525 * state + 1013904223) >>> 0;
        return state / 0x100000000;
    };
}

function shuffleDeterministically(rows, seed) {
    const copy = [...rows];
    const random = createSeededRandom(seed);

    for (let index = copy.length - 1; index > 0; index -= 1) {
        const swapIndex = Math.floor(random() * (index + 1));
        const current = copy[index];
        copy[index] = copy[swapIndex];
        copy[swapIndex] = current;
    }

    return copy;
}

function computePerLabelTestCount(labelRows, testRatio) {
    if (labelRows.length <= 1) {
        return 0;
    }

    const rawCount = Math.round(labelRows.length * testRatio);
    return Math.max(1, Math.min(labelRows.length - 1, rawCount));
}

function stratifiedSplitRows(rows, options = {}) {
    const testRatio = options.testRatio ?? TEST_RATIO;
    const seed = options.seed ?? RANDOM_SEED;
    const grouped = new Map();

    for (const label of VALID_LABELS) {
        grouped.set(label, []);
    }

    for (const row of rows) {
        if (!VALID_LABEL_SET.has(row.actual_result)) {
            throw new Error(`Invalid label for split: ${row.actual_result}`);
        }
        grouped.get(row.actual_result).push(row);
    }

    const trainRows = [];
    const testRows = [];

    VALID_LABELS.forEach((label, labelIndex) => {
        const shuffled = shuffleDeterministically(grouped.get(label), seed + labelIndex);
        const testCount = computePerLabelTestCount(shuffled, testRatio);
        testRows.push(...shuffled.slice(0, testCount));
        trainRows.push(...shuffled.slice(testCount));
    });

    return {
        trainRows: shuffleDeterministically(trainRows, seed + 100),
        testRows: shuffleDeterministically(testRows, seed + 200),
    };
}

function computeAccuracy(actualLabels, predictedLabels) {
    if (actualLabels.length !== predictedLabels.length) {
        throw new Error('Accuracy inputs length mismatch');
    }

    if (actualLabels.length === 0) {
        return 0;
    }

    let correct = 0;
    for (let index = 0; index < actualLabels.length; index += 1) {
        if (actualLabels[index] === predictedLabels[index]) {
            correct += 1;
        }
    }

    return Number((correct / actualLabels.length).toFixed(6));
}

function getMajorityLabel(rows) {
    const distribution = buildOrderedLabelDistribution(rows);
    let bestLabel = VALID_LABELS[0];
    let bestCount = -1;

    for (const label of VALID_LABELS) {
        if (distribution[label] > bestCount) {
            bestLabel = label;
            bestCount = distribution[label];
        }
    }

    return bestLabel;
}

function fitSmokeModel(rows, featureColumns = FEATURE_COLUMNS) {
    const classCounts = {};
    const featureValueCounts = {};
    const vocabularies = {};

    for (const label of VALID_LABELS) {
        classCounts[label] = 0;
        featureValueCounts[label] = {};
    }

    for (const feature of featureColumns) {
        vocabularies[feature] = new Set();
        for (const label of VALID_LABELS) {
            featureValueCounts[label][feature] = {};
        }
    }

    for (const row of rows) {
        const encoded = encodeFeatureRecord(buildFeatureRecord(row));
        const label = row.actual_result;
        classCounts[label] += 1;

        for (const feature of featureColumns) {
            const value = encoded[feature];
            vocabularies[feature].add(value);
            const counts = featureValueCounts[label][feature];
            counts[value] = (counts[value] || 0) + 1;
        }
    }

    return {
        featureColumns: [...featureColumns],
        classCounts,
        featureValueCounts,
        vocabularies: Object.fromEntries(
            Object.entries(vocabularies).map(([feature, values]) => [feature, [...values]])
        ),
        totalSamples: rows.length,
        classCount: VALID_LABELS.length,
        encoding_summary: {
            league_name: 'categorical_token',
            season: 'categorical_token',
            home_team: 'categorical_token',
            away_team: 'categorical_token',
            match_date: 'calendar_token(weekday|month|hour|weekend)',
        },
    };
}

function predictWithSmokeModel(model, row) {
    const encoded = encodeFeatureRecord(buildFeatureRecord(row));
    const scores = {};

    for (const label of VALID_LABELS) {
        const classCount = model.classCounts[label];
        const priorNumerator = classCount + 1;
        const priorDenominator = model.totalSamples + model.classCount;
        let score = Math.log(priorNumerator / priorDenominator);

        for (const feature of model.featureColumns) {
            const counts = model.featureValueCounts[label][feature];
            const vocabularySize = model.vocabularies[feature].length || 1;
            const valueCount = counts[encoded[feature]] || 0;
            score += Math.log((valueCount + 1) / (classCount + vocabularySize));
        }

        scores[label] = score;
    }

    return VALID_LABELS.reduce((bestLabel, currentLabel) => (
        scores[currentLabel] > scores[bestLabel] ? currentLabel : bestLabel
    ), VALID_LABELS[0]);
}

function evaluateSmokeModel(model, rows) {
    const actualLabels = rows.map(row => row.actual_result);
    const predictedLabels = rows.map(row => predictWithSmokeModel(model, row));
    return {
        predictions: predictedLabels,
        accuracy: computeAccuracy(actualLabels, predictedLabels),
    };
}

function buildWarnings(baselineAccuracy, smokeModelAccuracy) {
    const warnings = [
        'smoke_only_not_formal_training',
        'sample_size_58_is_too_small_for_model_quality_assessment',
        'venue_and_referee_excluded_due_to_100_percent_missing_rate',
        'accuracy_metrics_are_connectivity_signals_only',
    ];

    if (smokeModelAccuracy <= baselineAccuracy) {
        warnings.push('smoke_model_did_not_beat_majority_baseline_on_this_split');
    }

    return warnings;
}

function buildRiskFlags() {
    return [
        'no_db_write_read_only_training_pipeline',
        'single_league_single_season_single_split',
        'categorical_naive_bayes_smoke_model_not_for_production_use',
        'no_model_artifact_committed',
        'no_prediction_or_betting_strategy_execution',
    ];
}

function sameLabelDistribution(left, right) {
    return VALID_LABELS.every(label => (left[label] || 0) === (right[label] || 0));
}

function buildDryRunPayload(rows, options = {}) {
    const featureColumns = [...FEATURE_COLUMNS];
    const excludedFeatureColumns = [...EXCLUDED_FEATURE_COLUMNS];
    const labelDistribution = buildOrderedLabelDistribution(rows);
    const leakageColumnsDetected = detectLeakageColumns(featureColumns);
    const { trainRows, testRows } = stratifiedSplitRows(rows, {
        testRatio: options.testRatio ?? TEST_RATIO,
        seed: options.seed ?? RANDOM_SEED,
    });

    const model = fitSmokeModel(trainRows, featureColumns);
    const baselineLabel = getMajorityLabel(trainRows);
    const baselinePredictions = testRows.map(() => baselineLabel);
    const baselineAccuracy = computeAccuracy(
        testRows.map(row => row.actual_result),
        baselinePredictions
    );
    const smokeEvaluation = evaluateSmokeModel(model, testRows);

    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        model_artifact_committed: false,
        model_artifact_created: false,
        prediction_executed: false,
        read_only: true,
        script: 'scripts/ops/training_pipeline_smoke_dry_run.js',
        generated_at: new Date().toISOString(),
        random_seed: options.seed ?? RANDOM_SEED,
        target_scope: {
            league_name: TARGET_LEAGUE,
            season: TARGET_SEASON,
            is_training_eligible: true,
        },
        sample_count: rows.length,
        feature_columns: featureColumns,
        excluded_feature_columns: excludedFeatureColumns,
        label_column: LABEL_COLUMN,
        label_distribution: labelDistribution,
        train_label_distribution: buildOrderedLabelDistribution(trainRows),
        test_label_distribution: buildOrderedLabelDistribution(testRows),
        x_shape: [rows.length, featureColumns.length],
        y_shape: [rows.length],
        train_size: trainRows.length,
        test_size: testRows.length,
        class_count: VALID_LABELS.length,
        baseline_label: baselineLabel,
        baseline_accuracy: baselineAccuracy,
        smoke_model_accuracy: smokeEvaluation.accuracy,
        encoding_summary: model.encoding_summary,
        leakage_columns_detected: leakageColumnsDetected,
        validation_checks: {
            expected_sample_count: EXPECTED_SAMPLE_COUNT,
            actual_sample_count: rows.length,
            sample_count_matches_expected: rows.length === EXPECTED_SAMPLE_COUNT,
            expected_label_distribution: EXPECTED_LABEL_DISTRIBUTION,
            actual_label_distribution: labelDistribution,
            label_distribution_matches_expected: sameLabelDistribution(
                labelDistribution,
                EXPECTED_LABEL_DISTRIBUTION
            ),
            expected_feature_columns: featureColumns,
            feature_columns_match_expected:
                JSON.stringify(featureColumns) === JSON.stringify(FEATURE_COLUMNS),
            expected_excluded_feature_columns_present: ['venue', 'referee'],
            venue_referee_excluded: excludedFeatureColumns.includes('venue')
                && excludedFeatureColumns.includes('referee'),
            expected_label_column: LABEL_COLUMN,
            label_column_matches_expected: LABEL_COLUMN === 'actual_result',
            leakage_columns_detected_empty: leakageColumnsDetected.length === 0,
        },
        warnings: buildWarnings(baselineAccuracy, smokeEvaluation.accuracy),
        risk_flags: buildRiskFlags(),
        recommendation:
            '本次只证明最小训练管道的读取、编码、切分、训练连通性；不要据此判断模型可用性。任何正式训练或模型产物必须等待用户确认。',
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            db_write_executed: false,
            live_fetch_allowed: false,
            live_fetch_executed: false,
            raw_payload_output_allowed: false,
            raw_payload_output_detected: false,
            model_artifact_committed: false,
            model_artifact_created: false,
            prediction_executed: false,
            read_only_transaction_used: true,
        },
    };
}

async function runDryRun(options = {}, dependencies = {}) {
    const rows = await scanTrainingRows(dependencies);
    return buildDryRunPayload(rows, options);
}

function payloadToText(payload) {
    const labelDistribution = VALID_LABELS
        .map(label => `  ${label}: ${payload.label_distribution[label] ?? 0}`)
        .join('\n');
    const warnings = payload.warnings.map(item => `  - ${item}`).join('\n');
    const riskFlags = payload.risk_flags.map(item => `  - ${item}`).join('\n');

    return [
        '[DRY-RUN] Training pipeline smoke',
        `Phase: ${payload.phase}`,
        `Mode: ${payload.mode}`,
        `Sample count: ${payload.sample_count}`,
        `Feature columns: ${payload.feature_columns.join(', ')}`,
        `Excluded feature columns: ${payload.excluded_feature_columns.join(', ')}`,
        `Label column: ${payload.label_column}`,
        `X shape: [${payload.x_shape.join(', ')}]`,
        `Y shape: [${payload.y_shape.join(', ')}]`,
        `Train/test split: ${payload.train_size}/${payload.test_size}`,
        `Baseline accuracy: ${payload.baseline_accuracy}`,
        `Smoke model accuracy: ${payload.smoke_model_accuracy}`,
        'Label distribution:',
        labelDistribution,
        `Leakage columns detected: ${payload.leakage_columns_detected.join(', ') || 'none'}`,
        'Warnings:',
        warnings,
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
        model_artifact_committed: false,
        model_artifact_created: false,
        prediction_executed: false,
        read_only: true,
        script: 'scripts/ops/training_pipeline_smoke_dry_run.js',
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
            model_artifact_committed: false,
            model_artifact_created: false,
            prediction_executed: false,
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
    FEATURE_COLUMNS,
    EXCLUDED_FEATURE_COLUMNS,
    LABEL_COLUMN,
    VALID_LABELS,
    EXPECTED_SAMPLE_COUNT,
    EXPECTED_LABEL_DISTRIBUTION,
    SCAN_SQL,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    RANDOM_SEED,
    TEST_RATIO,
    parseArgs,
    assertSelectOnlySql,
    buildOrderedLabelDistribution,
    detectLeakageColumns,
    normalizeMatchDateToken,
    stratifiedSplitRows,
    computeAccuracy,
    fitSmokeModel,
    predictWithSmokeModel,
    buildDryRunPayload,
    runDryRun,
    main,
};
