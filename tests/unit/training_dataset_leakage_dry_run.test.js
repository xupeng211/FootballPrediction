'use strict';

// lifecycle: permanent
// scope: unit safety coverage for read-only training dataset leakage dry-run

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    parseArgs,
    assertSelectOnlySql,
    countDistribution,
    buildFieldSummary,
    buildDryRunPayload,
    runDryRun,
    FIELD_CLASSIFICATION,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
} = require('../../scripts/ops/training_dataset_leakage_dry_run');

function buildEligibleRow(overrides = {}) {
    return {
        match_id: '53_20252026_4830458',
        external_id: '4830458',
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: 'Team A',
        away_team: 'Team B',
        home_score: 2,
        away_score: 1,
        actual_result: 'home_win',
        match_date: '2025-08-16T19:00:00Z',
        venue: 'Stadium A',
        status: 'finished',
        is_finished: true,
        home_corners: 5,
        away_corners: 3,
        home_yellow_cards: 2,
        away_yellow_cards: 1,
        home_red_cards: 0,
        away_red_cards: 0,
        referee: 'Ref X',
        is_training_eligible: true,
        collection_date: '2025-08-17T01:00:00Z',
        created_at: '2025-08-17T01:00:00Z',
        updated_at: '2025-08-17T01:00:00Z',
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

test('assertSelectOnlySql rejects non-select', () => {
    assert.doesNotThrow(() => assertSelectOnlySql('SELECT 1'));
    assert.doesNotThrow(() => assertSelectOnlySql('ROLLBACK'));
    assert.throws(() => assertSelectOnlySql('DROP TABLE x'));
    assert.throws(() => assertSelectOnlySql('COMMIT'));
});

test('FIELD_CLASSIFICATION covers all 32 matches columns', () => {
    const expectedFields = [
        'match_id', 'external_id', 'league_name', 'season',
        'home_team', 'away_team', 'home_score', 'away_score', 'actual_result',
        'match_date', 'venue', 'status', 'is_finished',
        'collection_date', 'created_at', 'updated_at',
        'data_version', 'data_source', 'pipeline_status',
        'home_corners', 'away_corners',
        'home_yellow_cards', 'away_yellow_cards',
        'home_red_cards', 'away_red_cards',
        'referee', 'source_type', 'evidence_level',
        'is_production_scope', 'is_reconciliation_eligible',
        'is_training_eligible', 'pipeline_status_reason',
    ];

    for (const field of expectedFields) {
        assert.ok(FIELD_CLASSIFICATION[field], `Field ${field} must be classified`);
    }

    assert.equal(Object.keys(FIELD_CLASSIFICATION).length, 32);
});

test('FIELD_CLASSIFICATION has exactly one label field', () => {
    const labels = Object.entries(FIELD_CLASSIFICATION).filter(([, c]) => c.category === 'label');
    assert.equal(labels.length, 1);
    assert.equal(labels[0][0], 'actual_result');
});

test('FIELD_CLASSIFICATION safe_pre_match fields are usable as features', () => {
    const safe = Object.entries(FIELD_CLASSIFICATION).filter(([, c]) => c.category === 'safe_pre_match');
    assert.ok(safe.length >= 6);
    for (const [, c] of safe) {
        assert.equal(c.usable_as_feature, true);
    }
});

test('FIELD_CLASSIFICATION leakage fields are NOT usable as features', () => {
    const leakage = Object.entries(FIELD_CLASSIFICATION).filter(([, c]) => c.category === 'leakage_post_match');
    assert.ok(leakage.length >= 8);
    for (const [, c] of leakage) {
        assert.equal(c.usable_as_feature, false);
    }
});

test('FIELD_CLASSIFICATION administrative fields are NOT usable as features', () => {
    const admin = Object.entries(FIELD_CLASSIFICATION).filter(([, c]) => c.category === 'administrative');
    assert.ok(admin.length >= 10);
    for (const [, c] of admin) {
        assert.equal(c.usable_as_feature, false);
    }
});

test('buildFieldSummary returns correct category counts', () => {
    const summary = buildFieldSummary();
    assert.equal(summary.label.length, 1);
    assert.ok(summary.safe_pre_match.length >= 6);
    assert.ok(summary.leakage_post_match.length >= 8);
    assert.ok(summary.administrative.length >= 10);
    assert.equal(summary.uncertain.length, 0);
});

test('buildDryRunPayload computes label distribution correctly', () => {
    const rows = [
        buildEligibleRow({ match_id: 'A', actual_result: 'home_win' }),
        buildEligibleRow({ match_id: 'B', actual_result: 'home_win' }),
        buildEligibleRow({ match_id: 'C', actual_result: 'draw' }),
        buildEligibleRow({ match_id: 'D', actual_result: 'away_win' }),
    ];

    const payload = buildDryRunPayload(rows);

    assert.equal(payload.training_eligible_count, 4);
    assert.deepEqual(payload.label_distribution, { home_win: 2, draw: 1, away_win: 1 });
    assert.equal(payload.label_validation.all_label_valid, true);
    assert.equal(payload.label_validation.valid_count, 4);
});

test('buildDryRunPayload includes required safety and recommendation fields', () => {
    const rows = [buildEligibleRow()];
    const payload = buildDryRunPayload(rows);

    assert.equal(payload.mode, 'dry_run');
    assert.equal(payload.actual_update_executed, false);
    assert.equal(payload.safety.db_write_allowed, false);
    assert.equal(payload.safety.model_training_performed, false);
    assert.equal(payload.safety.read_only_transaction_used, true);
    assert.ok(payload.risk_flags.length >= 3);
    assert.ok(payload.recommendations.length >= 4);
    assert.ok(payload.safe_feature_candidates.length >= 6);
    assert.ok(payload.leakage_feature_candidates.length >= 8);
    assert.equal(payload.field_classification_summary.uncertain_count, 0);
    assert.equal(payload.sample_rows_count, 1);
});

test('runDryRun uses read-only SQL and returns expected shape', async () => {
    const rows = [
        buildEligibleRow(),
        buildEligibleRow({
            match_id: '53_20252026_4830459',
            external_id: '4830459',
            actual_result: 'draw',
            home_score: 1,
            away_score: 1,
        }),
    ];
    const mockClient = createMockClient(rows);

    const payload = await runDryRun({}, { client: mockClient });

    assert.equal(payload.mode, 'dry_run');
    assert.equal(payload.actual_update_executed, false);
    assert.equal(payload.training_eligible_count, 2);
    assert.deepEqual(payload.label_distribution, { home_win: 1, draw: 1 });
    assert.equal(payload.safety.db_write_allowed, false);
    assert.equal(payload.safety.read_only_transaction_used, true);
    assert.equal(mockClient.calls.length, 3);
    assert.equal(mockClient.calls[0].sql.trim(), READ_ONLY_BEGIN_SQL);
    assert.match(mockClient.calls[1].sql.trim(), /^SELECT/);
    assert.match(mockClient.calls[1].sql.trim(), /is_training_eligible = true/);
    assert.equal(mockClient.calls[2].sql.trim(), READ_ONLY_ROLLBACK_SQL);
});
