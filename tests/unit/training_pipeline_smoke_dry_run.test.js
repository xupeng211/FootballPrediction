'use strict';

// lifecycle: permanent
// scope: unit safety coverage for training pipeline smoke dry-run

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    FEATURE_COLUMNS,
    EXCLUDED_FEATURE_COLUMNS,
    LABEL_COLUMN,
    EXPECTED_SAMPLE_COUNT,
    EXPECTED_LABEL_DISTRIBUTION,
    SCAN_SQL,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    RANDOM_SEED,
    TEST_RATIO,
    parseArgs,
    assertSelectOnlySql,
    detectLeakageColumns,
    normalizeMatchDateToken,
    stratifiedSplitRows,
    computeAccuracy,
    fitSmokeModel,
    predictWithSmokeModel,
    buildDryRunPayload,
    runDryRun,
} = require('../../scripts/ops/training_pipeline_smoke_dry_run');

function buildRow(overrides = {}) {
    return {
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2025-08-16T19:00:00Z',
        actual_result: 'home_win',
        ...overrides,
    };
}

function createMockClient(rows) {
    const calls = [];

    return {
        calls,
        async query(sql, params = []) {
            calls.push({ sql: String(sql), params });
            const normalized = String(sql).replace(/\s+/g, ' ').trim();

            if (normalized === READ_ONLY_BEGIN_SQL || normalized === READ_ONLY_ROLLBACK_SQL) {
                return { rows: [] };
            }

            if (normalized.startsWith('SELECT')) {
                return { rows };
            }

            throw new Error(`Unexpected SQL in test mock: ${normalized.slice(0, 80)}`);
        },
    };
}

function buildDatasetByLabel(label, count) {
    return Array.from({ length: count }, (_, index) => buildRow({
        home_team: `${label}_home_${index}`,
        away_team: `${label}_away_${index}`,
        match_date: `2025-08-${String((index % 28) + 1).padStart(2, '0')}T19:00:00Z`,
        actual_result: label,
    }));
}

test('parseArgs supports --json and --help', () => {
    assert.equal(parseArgs(['--json']).json, true);
    assert.equal(parseArgs(['--help']).help, true);
    assert.equal(parseArgs([]).json, false);
});

test('assertSelectOnlySql rejects non-select SQL', () => {
    assert.doesNotThrow(() => assertSelectOnlySql('SELECT 1'));
    assert.doesNotThrow(() => assertSelectOnlySql('ROLLBACK'));
    assert.throws(() => assertSelectOnlySql('COMMIT'));
    assert.throws(() => assertSelectOnlySql('EXPLAIN SELECT 1'));
});

test('SCAN_SQL only selects allowed 5 feature columns plus label', () => {
    const normalized = SCAN_SQL.replace(/\s+/g, ' ').trim();

    for (const column of FEATURE_COLUMNS) {
        assert.match(normalized, new RegExp(`m\\.${column}`));
    }
    assert.match(normalized, /m\.actual_result/);

    for (const forbidden of ['venue', 'referee', 'home_score', 'away_score', 'raw_match_data']) {
        assert.doesNotMatch(normalized, new RegExp(`\\b${forbidden}\\b`));
    }
});

test('excluded feature columns include venue and referee', () => {
    assert.ok(EXCLUDED_FEATURE_COLUMNS.includes('venue'));
    assert.ok(EXCLUDED_FEATURE_COLUMNS.includes('referee'));
    assert.ok(EXCLUDED_FEATURE_COLUMNS.includes('actual_result'));
    assert.equal(detectLeakageColumns(FEATURE_COLUMNS).length, 0);
});

test('normalizeMatchDateToken converts raw date into deterministic calendar token', () => {
    assert.equal(
        normalizeMatchDateToken('2025-08-16T19:00:00Z'),
        'weekday_6|month_8|hour_19|weekend_1'
    );
});

test('stratifiedSplitRows keeps all classes in train and test with fixed seed', () => {
    const rows = [
        ...buildDatasetByLabel('home_win', 23),
        ...buildDatasetByLabel('draw', 17),
        ...buildDatasetByLabel('away_win', 18),
    ];

    const split = stratifiedSplitRows(rows, { testRatio: TEST_RATIO, seed: RANDOM_SEED });

    assert.equal(split.trainRows.length, 43);
    assert.equal(split.testRows.length, 15);

    const trainCounts = split.trainRows.reduce((acc, row) => {
        acc[row.actual_result] = (acc[row.actual_result] || 0) + 1;
        return acc;
    }, {});
    const testCounts = split.testRows.reduce((acc, row) => {
        acc[row.actual_result] = (acc[row.actual_result] || 0) + 1;
        return acc;
    }, {});

    assert.deepEqual(trainCounts, { home_win: 17, draw: 13, away_win: 13 });
    assert.deepEqual(testCounts, { home_win: 6, draw: 4, away_win: 5 });
});

test('fitSmokeModel and predictWithSmokeModel run end-to-end', () => {
    const trainRows = [
        buildRow({ home_team: 'A', away_team: 'B', actual_result: 'home_win' }),
        buildRow({ home_team: 'C', away_team: 'D', actual_result: 'draw' }),
        buildRow({ home_team: 'E', away_team: 'F', actual_result: 'away_win' }),
    ];

    const model = fitSmokeModel(trainRows, FEATURE_COLUMNS);
    const prediction = predictWithSmokeModel(model, buildRow({
        home_team: 'A',
        away_team: 'B',
        actual_result: 'home_win',
    }));

    assert.equal(model.totalSamples, 3);
    assert.equal(model.classCount, 3);
    assert.equal(prediction, 'home_win');
});

test('computeAccuracy returns fixed precision ratio', () => {
    const accuracy = computeAccuracy(
        ['home_win', 'draw', 'away_win'],
        ['home_win', 'draw', 'draw']
    );

    assert.equal(accuracy, 0.666667);
});

test('buildDryRunPayload includes required smoke training fields', () => {
    const rows = [
        ...buildDatasetByLabel('home_win', 23),
        ...buildDatasetByLabel('draw', 17),
        ...buildDatasetByLabel('away_win', 18),
    ];

    const payload = buildDryRunPayload(rows, { seed: RANDOM_SEED, testRatio: TEST_RATIO });

    assert.equal(payload.mode, 'dry_run');
    assert.equal(payload.actual_update_executed, false);
    assert.equal(payload.model_artifact_committed, false);
    assert.equal(payload.sample_count, EXPECTED_SAMPLE_COUNT);
    assert.deepEqual(payload.feature_columns, FEATURE_COLUMNS);
    assert.equal(payload.label_column, LABEL_COLUMN);
    assert.deepEqual(payload.label_distribution, EXPECTED_LABEL_DISTRIBUTION);
    assert.deepEqual(payload.x_shape, [58, 5]);
    assert.deepEqual(payload.y_shape, [58]);
    assert.equal(payload.train_size, 43);
    assert.equal(payload.test_size, 15);
    assert.equal(payload.class_count, 3);
    assert.deepEqual(payload.leakage_columns_detected, []);
    assert.equal(payload.validation_checks.venue_referee_excluded, true);
    assert.equal(payload.safety.db_write_executed, false);
    assert.equal(payload.safety.prediction_executed, false);
});

test('runDryRun uses BEGIN READ ONLY, SELECT, and ROLLBACK only', async () => {
    const rows = [
        ...buildDatasetByLabel('home_win', 23),
        ...buildDatasetByLabel('draw', 17),
        ...buildDatasetByLabel('away_win', 18),
    ];
    const mockClient = createMockClient(rows);

    const payload = await runDryRun({}, { client: mockClient });

    assert.equal(payload.sample_count, 58);
    assert.equal(payload.validation_checks.sample_count_matches_expected, true);
    assert.equal(payload.validation_checks.label_distribution_matches_expected, true);
    assert.equal(payload.validation_checks.leakage_columns_detected_empty, true);
    assert.equal(mockClient.calls.length, 3);
    assert.equal(mockClient.calls[0].sql.trim(), READ_ONLY_BEGIN_SQL);
    assert.match(mockClient.calls[1].sql.trim(), /^SELECT/);
    assert.equal(mockClient.calls[2].sql.trim(), READ_ONLY_ROLLBACK_SQL);
});
