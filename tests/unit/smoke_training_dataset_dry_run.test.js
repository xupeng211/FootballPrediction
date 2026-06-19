'use strict';

// lifecycle: permanent
// scope: unit safety coverage for smoke training dataset builder dry-run

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    SAFE_FEATURE_COLUMNS,
    LABEL_COLUMN,
    EXPECTED_SAMPLE_COUNT,
    EXPECTED_LABEL_DISTRIBUTION,
    EXCLUDED_COLUMNS,
    SCAN_SQL,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    parseArgs,
    assertSelectOnlySql,
    buildMissingRateByFeature,
    detectLeakageColumns,
    buildMatrices,
    buildDryRunPayload,
    runDryRun,
} = require('../../scripts/ops/smoke_training_dataset_dry_run');

function buildEligibleRow(overrides = {}) {
    return {
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2025-08-16T19:00:00Z',
        venue: null,
        referee: null,
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

test('SCAN_SQL only selects 7 safe features plus label', () => {
    const normalized = SCAN_SQL.replace(/\s+/g, ' ').trim();

    for (const column of SAFE_FEATURE_COLUMNS) {
        assert.match(normalized, new RegExp(`m\\.${column}`));
    }
    assert.match(normalized, /m\.actual_result/);

    for (const forbidden of [
        'home_score',
        'away_score',
        'home_corners',
        'away_corners',
        'status',
        'is_finished',
        'pipeline_status',
        'raw_match_data',
    ]) {
        assert.doesNotMatch(normalized, new RegExp(`\\b${forbidden}\\b`));
    }
});

test('buildMatrices keeps X limited to safe features and y from actual_result only', () => {
    const rows = [
        buildEligibleRow(),
        buildEligibleRow({
            home_team: 'Team C',
            away_team: 'Team D',
            actual_result: 'draw',
        }),
    ];

    const { xRows, yRows } = buildMatrices(rows);

    assert.equal(xRows.length, 2);
    assert.deepEqual(Object.keys(xRows[0]), SAFE_FEATURE_COLUMNS);
    assert.deepEqual(yRows, ['home_win', 'draw']);
    assert.equal(Object.prototype.hasOwnProperty.call(xRows[0], LABEL_COLUMN), false);
});

test('buildMissingRateByFeature computes missing rate for nullable safe fields', () => {
    const rows = [
        buildEligibleRow({ venue: null, referee: null }),
        buildEligibleRow({ venue: 'Stadium', referee: 'Ref A' }),
        buildEligibleRow({ venue: ' ', referee: null }),
    ];

    const missingRate = buildMissingRateByFeature(rows);

    assert.equal(missingRate.league_name.missing_rate, 0);
    assert.equal(missingRate.venue.missing_count, 2);
    assert.equal(missingRate.venue.missing_rate, 0.666667);
    assert.equal(missingRate.referee.missing_count, 2);
    assert.equal(missingRate.referee.missing_rate, 0.666667);
});

test('detectLeakageColumns returns empty array for approved feature set', () => {
    assert.deepEqual(detectLeakageColumns(SAFE_FEATURE_COLUMNS), []);
});

test('buildDryRunPayload includes expected validation summary and excluded columns', () => {
    const rows = [
        buildEligibleRow({ actual_result: 'home_win' }),
        buildEligibleRow({ actual_result: 'draw' }),
        buildEligibleRow({ actual_result: 'away_win' }),
    ];

    const payload = buildDryRunPayload(rows);

    assert.equal(payload.mode, 'dry_run');
    assert.equal(payload.actual_update_executed, false);
    assert.equal(payload.sample_count, 3);
    assert.deepEqual(payload.feature_columns, SAFE_FEATURE_COLUMNS);
    assert.equal(payload.label_column, LABEL_COLUMN);
    assert.deepEqual(payload.label_distribution, { home_win: 1, draw: 1, away_win: 1 });
    assert.deepEqual(payload.x_shape, [3, 7]);
    assert.deepEqual(payload.y_shape, [3]);
    assert.deepEqual(payload.leakage_columns_detected, []);
    assert.equal(payload.validation_checks.expected_sample_count, EXPECTED_SAMPLE_COUNT);
    assert.deepEqual(
        payload.validation_checks.expected_label_distribution,
        EXPECTED_LABEL_DISTRIBUTION
    );
    assert.ok(EXCLUDED_COLUMNS.includes('raw_match_data'));
    assert.ok(EXCLUDED_COLUMNS.includes('actual_result'));
    assert.equal(payload.safety.db_write_executed, false);
    assert.equal(payload.safety.model_training_performed, false);
});

test('runDryRun uses BEGIN READ ONLY, SELECT, and ROLLBACK only', async () => {
    const rows = [
        buildEligibleRow({ actual_result: 'home_win' }),
        buildEligibleRow({ actual_result: 'draw' }),
    ];
    const mockClient = createMockClient(rows);

    const payload = await runDryRun({}, { client: mockClient });

    assert.equal(payload.sample_count, 2);
    assert.deepEqual(payload.label_distribution, { home_win: 1, draw: 1, away_win: 0 });
    assert.equal(payload.validation_checks.leakage_columns_detected_empty, true);
    assert.equal(mockClient.calls.length, 3);
    assert.equal(mockClient.calls[0].sql.trim(), READ_ONLY_BEGIN_SQL);
    assert.match(mockClient.calls[1].sql.trim(), /^SELECT/);
    assert.equal(mockClient.calls[2].sql.trim(), READ_ONLY_ROLLBACK_SQL);
});
